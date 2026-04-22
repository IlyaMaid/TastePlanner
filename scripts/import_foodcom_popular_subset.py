from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from import_foodcom import import_foodcom, resolve_db_url


DEFAULT_INTERACTIONS_PATH = Path("datasets/archive/interactions_train.csv")
DEFAULT_RECIPES_PATH = Path("datasets/archive/RAW_recipes.csv")
DEFAULT_TEMP_EXPORT_PATH = Path("artifacts/recommender/top_foodcom_subset.csv")


def build_top_recipe_id_set(interactions_path: Path, top_n: int) -> set[int]:
    interactions = pd.read_csv(interactions_path, usecols=["recipe_id", "rating"])
    interactions = interactions[interactions["rating"] > 0]
    popularity = (
        interactions.groupby("recipe_id")["rating"]
        .agg(["count", "mean"])
        .reset_index()
        .sort_values(["count", "mean", "recipe_id"], ascending=[False, False, True])
    )
    return set(popularity.head(top_n)["recipe_id"].astype(int).tolist())


def export_subset_csv(recipes_path: Path, recipe_ids: set[int], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    chunks = []
    for chunk in pd.read_csv(recipes_path, chunksize=5000):
        filtered = chunk[chunk["id"].isin(recipe_ids)]
        if not filtered.empty:
            chunks.append(filtered)

    if not chunks:
        raise SystemExit("No matching Food.com recipes found for the selected subset.")

    subset_df = pd.concat(chunks, ignore_index=True)
    subset_df.to_csv(output_path, index=False)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a popular Food.com subset into TastePlanner database"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5000,
        help="How many most popular Food.com recipes to import",
    )
    parser.add_argument(
        "--interactions-csv",
        default=str(DEFAULT_INTERACTIONS_PATH),
        help="Path to Food.com interactions train split",
    )
    parser.add_argument(
        "--recipes-csv",
        default=str(DEFAULT_RECIPES_PATH),
        help="Path to Food.com RAW_recipes.csv",
    )
    parser.add_argument(
        "--temp-csv",
        default=str(DEFAULT_TEMP_EXPORT_PATH),
        help="Temporary CSV path for the filtered subset",
    )
    parser.add_argument("--db-url", help="SQLAlchemy PostgreSQL URL")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    recipe_ids = build_top_recipe_id_set(Path(args.interactions_csv), args.top_n)
    subset_csv = export_subset_csv(
        Path(args.recipes_csv),
        recipe_ids,
        Path(args.temp_csv),
    )
    import_foodcom(
        csv_path=str(subset_csv),
        db_url=resolve_db_url(args.db_url),
        limit=None,
    )
    print(f"Imported top {args.top_n} popular Food.com recipes from {subset_csv}")


if __name__ == "__main__":
    main()
