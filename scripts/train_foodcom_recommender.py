from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.foodcom_recommender_model import FoodComRecommender, save_model


DEFAULT_DATASET_DIR = Path("datasets/archive")
DEFAULT_OUTPUT_DIR = Path("artifacts/recommender")


@dataclass
class EvaluationMetrics:
    rmse: float
    mae: float
    coverage: float
    count: int


def load_interactions(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=["u", "i", "rating", "recipe_id"])
    df = df[df["rating"] > 0].copy()
    df["u"] = df["u"].astype(int)
    df["i"] = df["i"].astype(int)
    df["rating"] = df["rating"].astype(float)
    df["recipe_id"] = df["recipe_id"].astype(int)
    return df


def load_recipe_titles(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=["id", "name"])
    df["id"] = df["id"].astype(int)
    df["name"] = df["name"].fillna("").astype(str)
    return df


def compute_biases(
    interactions: pd.DataFrame,
    n_users: int,
    n_items: int,
    reg: float,
) -> tuple[float, np.ndarray, np.ndarray]:
    global_mean = float(interactions["rating"].mean())

    user_sums = np.bincount(
        interactions["u"].to_numpy(),
        weights=interactions["rating"].to_numpy() - global_mean,
        minlength=n_users,
    )
    user_counts = np.bincount(interactions["u"].to_numpy(), minlength=n_users)
    user_biases = user_sums / (user_counts + reg)

    adjusted = (
        interactions["rating"].to_numpy()
        - global_mean
        - user_biases[interactions["u"].to_numpy()]
    )
    item_sums = np.bincount(
        interactions["i"].to_numpy(),
        weights=adjusted,
        minlength=n_items,
    )
    item_counts = np.bincount(interactions["i"].to_numpy(), minlength=n_items)
    item_biases = item_sums / (item_counts + reg)

    return global_mean, user_biases, item_biases


def build_sparse_residual_matrix(
    interactions: pd.DataFrame,
    n_users: int,
    n_items: int,
    global_mean: float,
    user_biases: np.ndarray,
    item_biases: np.ndarray,
) -> csr_matrix:
    users = interactions["u"].to_numpy()
    items = interactions["i"].to_numpy()
    residuals = (
        interactions["rating"].to_numpy()
        - global_mean
        - user_biases[users]
        - item_biases[items]
    )
    return csr_matrix((residuals, (users, items)), shape=(n_users, n_items))


def train_model(
    train_df: pd.DataFrame,
    recipes_df: pd.DataFrame,
    n_components: int,
    regularization: float,
    random_state: int,
) -> FoodComRecommender:
    n_users = int(train_df["u"].max()) + 1
    n_items = int(train_df["i"].max()) + 1

    global_mean, user_biases, item_biases = compute_biases(
        train_df,
        n_users=n_users,
        n_items=n_items,
        reg=regularization,
    )
    residual_matrix = build_sparse_residual_matrix(
        train_df,
        n_users=n_users,
        n_items=n_items,
        global_mean=global_mean,
        user_biases=user_biases,
        item_biases=item_biases,
    )

    svd = TruncatedSVD(n_components=n_components, random_state=random_state)
    user_factors = svd.fit_transform(residual_matrix).astype(np.float32)
    item_factors = svd.components_.T.astype(np.float32)

    item_popularity = np.bincount(
        train_df["i"].to_numpy(),
        weights=train_df["rating"].to_numpy(),
        minlength=n_items,
    ).astype(np.float32)

    recipe_lookup = recipes_df.rename(columns={"id": "recipe_id", "name": "title"})
    item_lookup = (
        train_df[["i", "recipe_id"]]
        .drop_duplicates(subset=["i"])
        .merge(recipe_lookup, on="recipe_id", how="left")
        .sort_values("i")
    )

    recipe_ids_by_item_index = np.full(n_items, -1, dtype=np.int64)
    recipe_titles_by_item_index = np.full(n_items, "", dtype=object)
    recipe_ids_by_item_index[item_lookup["i"].to_numpy()] = item_lookup[
        "recipe_id"
    ].to_numpy()
    recipe_titles_by_item_index[item_lookup["i"].to_numpy()] = item_lookup[
        "title"
    ].fillna("").to_numpy()

    return FoodComRecommender(
        global_mean=global_mean,
        user_biases=user_biases.astype(np.float32),
        item_biases=item_biases.astype(np.float32),
        user_factors=user_factors,
        item_factors=item_factors,
        item_popularity=item_popularity,
        recipe_ids_by_item_index=recipe_ids_by_item_index,
        recipe_titles_by_item_index=recipe_titles_by_item_index,
    )


def evaluate_model(
    model: FoodComRecommender,
    interactions: pd.DataFrame,
) -> EvaluationMetrics:
    valid_mask = (
        interactions["u"].to_numpy() < model.user_factors.shape[0]
    ) & (interactions["i"].to_numpy() < model.item_factors.shape[0])

    covered = interactions.loc[valid_mask]
    if covered.empty:
        return EvaluationMetrics(rmse=float("nan"), mae=float("nan"), coverage=0.0, count=0)

    predictions = model.score(
        covered["u"].to_numpy(),
        covered["i"].to_numpy(),
    )
    actual = covered["rating"].to_numpy()
    errors = predictions - actual
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    mae = float(np.mean(np.abs(errors)))

    return EvaluationMetrics(
        rmse=rmse,
        mae=mae,
        coverage=float(len(covered) / len(interactions)),
        count=int(len(covered)),
    )


def write_metadata(
    output_dir: Path,
    config: dict[str, object],
    train_metrics: EvaluationMetrics,
    validation_metrics: EvaluationMetrics,
    test_metrics: EvaluationMetrics,
    sample_recommendations: list[dict[str, object]],
) -> None:
    metadata = {
        "config": config,
        "train_metrics": asdict(train_metrics),
        "validation_metrics": asdict(validation_metrics),
        "test_metrics": asdict(test_metrics),
        "sample_recommendations": sample_recommendations,
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a first collaborative Food.com recommender for TastePlanner"
    )
    parser.add_argument(
        "--dataset-dir",
        default=str(DEFAULT_DATASET_DIR),
        help="Directory with Food.com interaction splits and recipe files",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where the trained model artifact will be stored",
    )
    parser.add_argument(
        "--components",
        type=int,
        default=64,
        help="Number of latent dimensions for TruncatedSVD",
    )
    parser.add_argument(
        "--regularization",
        type=float,
        default=10.0,
        help="Regularization strength for user/item biases",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducible training",
    )
    parser.add_argument(
        "--sample-user",
        type=int,
        default=0,
        help="User index from the Food.com training split for a sample recommendation dump",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    dataset_dir = Path(args.dataset_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_df = load_interactions(dataset_dir / "interactions_train.csv")
    val_df = load_interactions(dataset_dir / "interactions_validation.csv")
    test_df = load_interactions(dataset_dir / "interactions_test.csv")
    recipes_df = load_recipe_titles(dataset_dir / "RAW_recipes.csv")

    model = train_model(
        train_df=train_df,
        recipes_df=recipes_df,
        n_components=args.components,
        regularization=args.regularization,
        random_state=args.random_state,
    )

    train_metrics = evaluate_model(model, train_df)
    validation_metrics = evaluate_model(model, val_df)
    test_metrics = evaluate_model(model, test_df)

    sample_seen_items = train_df.loc[train_df["u"] == args.sample_user, "i"].tolist()
    sample_recommendations = model.recommend_for_user(
        user_index=args.sample_user,
        seen_item_indices=sample_seen_items,
        top_k=10,
    )

    save_model(model, output_dir / "foodcom_svd_recommender.joblib")

    config = {
        "dataset_dir": str(dataset_dir),
        "components": args.components,
        "regularization": args.regularization,
        "random_state": args.random_state,
        "sample_user": args.sample_user,
        "n_train_rows": int(len(train_df)),
        "n_validation_rows": int(len(val_df)),
        "n_test_rows": int(len(test_df)),
        "n_users": int(train_df["u"].max()) + 1,
        "n_items": int(train_df["i"].max()) + 1,
    }
    write_metadata(
        output_dir=output_dir,
        config=config,
        train_metrics=train_metrics,
        validation_metrics=validation_metrics,
        test_metrics=test_metrics,
        sample_recommendations=sample_recommendations,
    )

    print("Training finished.")
    print(f"Model saved to: {output_dir / 'foodcom_svd_recommender.joblib'}")
    print(f"Metrics saved to: {output_dir / 'metrics.json'}")
    print(f"Validation RMSE: {validation_metrics.rmse:.4f}")
    print(f"Validation MAE: {validation_metrics.mae:.4f}")
    print(f"Test RMSE: {test_metrics.rmse:.4f}")
    print(f"Test MAE: {test_metrics.mae:.4f}")


if __name__ == "__main__":
    main()
