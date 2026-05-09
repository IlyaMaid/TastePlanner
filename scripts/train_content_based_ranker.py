from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRAINING_DIR = PROJECT_ROOT / "artifacts/training"
DEFAULT_TRAIN_PATH = TRAINING_DIR / "tasteplanner_train.csv"
DEFAULT_VALIDATION_PATH = TRAINING_DIR / "tasteplanner_validation.csv"
DEFAULT_TEST_PATH = TRAINING_DIR / "tasteplanner_test.csv"
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT / "artifacts/recommender/tasteplanner_content_ranker.joblib"
)
DEFAULT_REPORT_PATH = (
    PROJECT_ROOT / "artifacts/recommender/tasteplanner_content_ranker_report.json"
)

NUMERIC_COLUMNS = [
    "age",
    "height_cm",
    "weight_kg",
    "daily_budget_rub",
    "weekly_budget_rub",
    "effective_daily_budget_rub",
    "budget_per_meal_rub",
    "meals_per_day",
    "total_minutes",
    "calories",
    "protein",
    "fat",
    "carbs",
    "source_rating",
    "ingredient_count",
    "priced_ingredient_count",
    "price_coverage",
    "estimated_cost_rub",
    "seasonal_ingredient_count",
    "current_month",
    "cost_to_budget_ratio",
    "favorite_match_count",
    "disliked_match_count",
    "allergy_match_count",
    "has_any_favorite_match",
    "has_any_disliked_match",
    "has_any_allergy_match",
    "is_within_budget",
    "is_seasonal_now",
]

CATEGORICAL_COLUMNS = [
    "sex",
    "activity_level",
    "goal",
    "region_code",
    "source",
    "budget_tier",
    "time_tier",
    "calorie_tier",
    "protein_tier",
]

BOOLEAN_COLUMNS = [
    "has_meat",
    "has_fish",
    "has_dairy",
    "has_grains",
    "has_vegetables",
    "has_fruit",
    "has_legumes",
    "has_nuts",
    "has_pantry",
]


def parse_json_list(value: Any) -> list[str]:
    if value is None or pd.isna(value):
        return []
    if isinstance(value, list):
        values = value
    else:
        try:
            values = json.loads(str(value))
        except json.JSONDecodeError:
            return []
    return [str(item).strip().casefold() for item in values if str(item).strip()]


def text_contains_any(text_value: str, values: list[str]) -> int:
    if not values:
        return 0
    return sum(1 for value in values if value and value in text_value)


def build_recipe_text(row: pd.Series) -> str:
    values = [row.get("recipe_title", "")]
    values.extend(parse_json_list(row.get("canonical_ingredients_json")))
    values.extend(parse_json_list(row.get("product_categories_json")))
    return " ".join(str(value) for value in values if value).casefold()


def add_match_features(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    recipe_text = frame.apply(build_recipe_text, axis=1)
    favorites = frame.get("favorite_products_json", pd.Series("[]", index=frame.index))
    disliked = frame.get("disliked_products_json", pd.Series("[]", index=frame.index))
    allergies = frame.get("allergies_json", pd.Series("[]", index=frame.index))

    frame["favorite_match_count"] = [
        text_contains_any(text, parse_json_list(values))
        for text, values in zip(recipe_text, favorites, strict=False)
    ]
    frame["disliked_match_count"] = [
        text_contains_any(text, parse_json_list(values))
        for text, values in zip(recipe_text, disliked, strict=False)
    ]
    frame["allergy_match_count"] = [
        text_contains_any(text, parse_json_list(values))
        for text, values in zip(recipe_text, allergies, strict=False)
    ]
    frame["has_any_favorite_match"] = (frame["favorite_match_count"] > 0).astype(int)
    frame["has_any_disliked_match"] = (frame["disliked_match_count"] > 0).astype(int)
    frame["has_any_allergy_match"] = (frame["allergy_match_count"] > 0).astype(int)

    cost_ratio = pd.to_numeric(frame.get("cost_to_budget_ratio"), errors="coerce")
    frame["is_within_budget"] = (cost_ratio <= 1).fillna(False).astype(int)

    for column in BOOLEAN_COLUMNS + ["is_seasonal_now"]:
        if column in frame.columns:
            frame[column] = (
                frame[column]
                .astype(str)
                .str.lower()
                .isin(["true", "1", "yes"])
                .astype(int)
            )

    return frame


def target_series(df: pd.DataFrame) -> pd.Series:
    return df["target_liked"].astype(str).str.lower().isin(["true", "1", "yes"]).astype(int)


def build_classifier(preferred_model: str = "auto"):
    if preferred_model in {"auto", "catboost"}:
        try:
            from catboost import CatBoostClassifier

            return (
                "catboost_classifier",
                CatBoostClassifier(
                    iterations=250,
                    depth=4,
                    learning_rate=0.05,
                    loss_function="Logloss",
                    verbose=False,
                    random_seed=42,
                ),
            )
        except ImportError:
            if preferred_model == "catboost":
                raise SystemExit("CatBoost is not installed in the current environment.")

    if preferred_model in {"auto", "xgboost"}:
        try:
            from xgboost import XGBClassifier

            return (
                "xgboost_classifier",
                XGBClassifier(
                    n_estimators=250,
                    max_depth=3,
                    learning_rate=0.05,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    eval_metric="logloss",
                    random_state=42,
                ),
            )
        except ImportError:
            if preferred_model == "xgboost":
                raise SystemExit("XGBoost is not installed in the current environment.")

    return (
        "sklearn_hist_gradient_boosting",
        HistGradientBoostingClassifier(
            learning_rate=0.06,
            max_iter=180,
            max_leaf_nodes=15,
            l2_regularization=0.05,
            random_state=42,
        ),
    )


def build_pipeline(
    numeric_columns: list[str],
    categorical_columns: list[str],
    preferred_model: str = "auto",
) -> tuple[str, Pipeline]:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_columns),
            ("categorical", categorical_pipeline, categorical_columns),
        ],
        sparse_threshold=0,
    )
    model_name, classifier = build_classifier(preferred_model)
    return (
        model_name,
        Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("model", classifier),
            ]
        ),
    )


def evaluate_split(model: Pipeline, df: pd.DataFrame, split_name: str) -> dict[str, Any]:
    if df.empty:
        return {"split": split_name, "rows": 0}

    y_true = target_series(df)
    y_score = model.predict_proba(df)[:, 1]
    y_pred = (y_score >= 0.5).astype(int)
    metrics: dict[str, Any] = {
        "split": split_name,
        "rows": int(len(df)),
        "positive_rows": int(y_true.sum()),
        "negative_rows": int((1 - y_true).sum()),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "avg_positive_score": (
            round(float(pd.Series(y_score)[y_true.astype(bool).to_numpy()].mean()), 4)
            if y_true.sum() > 0
            else None
        ),
        "avg_negative_score": (
            round(float(pd.Series(y_score)[~y_true.astype(bool).to_numpy()].mean()), 4)
            if (1 - y_true).sum() > 0
            else None
        ),
    }
    if y_true.nunique() == 2:
        metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_score)), 4)
        metrics["average_precision"] = round(
            float(average_precision_score(y_true, y_score)),
            4,
        )
    else:
        metrics["roc_auc"] = None
        metrics["average_precision"] = None
    return metrics


def load_split(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"Dataset split not found: {path}")
    return add_match_features(pd.read_csv(path))


def train_model(
    train_path: Path,
    validation_path: Path,
    test_path: Path,
    output_path: Path,
    report_path: Path,
    preferred_model: str = "auto",
) -> dict[str, Any]:
    train_df = load_split(train_path)
    validation_df = load_split(validation_path)
    test_df = load_split(test_path)

    available_numeric = [
        column
        for column in [*NUMERIC_COLUMNS, *BOOLEAN_COLUMNS]
        if column in train_df.columns
    ]
    available_categorical = [
        column for column in CATEGORICAL_COLUMNS if column in train_df.columns
    ]

    model_name, model = build_pipeline(
        available_numeric,
        available_categorical,
        preferred_model=preferred_model,
    )
    y_train = target_series(train_df)
    model.fit(train_df, y_train)

    report = {
        "model_type": f"content_based_{model_name}",
        "target": "target_liked",
        "features": {
            "numeric": available_numeric,
            "categorical": available_categorical,
        },
        "splits": {
            "train": evaluate_split(model, train_df, "train"),
            "validation": evaluate_split(model, validation_df, "validation"),
            "test": evaluate_split(model, test_df, "test"),
        },
        "artifacts": {
            "model": str(output_path),
            "report": str(report_path),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "model_type": f"content_based_{model_name}",
            "numeric_columns": available_numeric,
            "categorical_columns": available_categorical,
            "boolean_columns": BOOLEAN_COLUMNS,
            "target": "target_liked",
            "report": report,
        },
        output_path,
    )
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a content-based TastePlanner recommendation ranker."
    )
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN_PATH)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION_PATH)
    parser.add_argument("--test", type=Path, default=DEFAULT_TEST_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument(
        "--model",
        choices=["auto", "catboost", "xgboost", "sklearn"],
        default="auto",
        help="Prediction model. auto tries CatBoost, then XGBoost, then sklearn boosting.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = train_model(
        train_path=args.train,
        validation_path=args.validation,
        test_path=args.test,
        output_path=args.output,
        report_path=args.report,
        preferred_model=args.model,
    )
    validation = report["splits"]["validation"]
    print(
        "Content-based ranker trained: "
        f"train_rows={report['splits']['train']['rows']}, "
        f"validation_auc={validation.get('roc_auc')}, "
        f"validation_ap={validation.get('average_precision')}, "
        f"model={args.output}"
    )


if __name__ == "__main__":
    main()
