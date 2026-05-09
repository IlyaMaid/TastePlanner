from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_recipe_features import ensure_schema as ensure_recipe_features_schema
from scripts.build_recipe_features import refresh_recipe_features

DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "artifacts/training/tasteplanner_training_dataset.csv"


def resolve_db_url(db_url: Optional[str]) -> str:
    if db_url:
        return db_url

    env_db_url = os.getenv("DATABASE_URL")
    if env_db_url:
        return env_db_url

    backend_env_path = PROJECT_ROOT / "backend/.env"
    if backend_env_path.exists():
        for line in backend_env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip()

    raise SystemExit(
        "--db-url is required unless DATABASE_URL is available in the environment "
        "or backend/.env"
    )


def ensure_schema(conn, refresh_features: bool = True) -> None:
    for migration_name in (
        "profile_budget_migration.sql",
        "feedback_training_signals_migration.sql",
    ):
        migration_path = PROJECT_ROOT / "postgress" / migration_name
        if migration_path.exists():
            conn.execute(text(migration_path.read_text(encoding="utf-8")))
    ensure_recipe_features_schema(conn)
    if refresh_features:
        refresh_recipe_features(conn)


def json_for_csv(value) -> str:
    if value is None:
        return "[]"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def export_training_dataset(
    db_url: str,
    output_path: Path,
    limit: Optional[int],
    refresh_features: bool = True,
) -> int:
    engine = create_engine(db_url)
    limit_clause = "LIMIT :limit" if limit else ""

    query = text(
        f"""
        WITH event_features AS (
            SELECT
                user_id,
                recipe_id,
                COUNT(*) AS event_count,
                COUNT(*) FILTER (WHERE event_type = 'recipe_open') AS open_count,
                COUNT(*) FILTER (WHERE event_type = 'favorite_toggle') AS favorite_toggle_count,
                COUNT(*) FILTER (WHERE event_type = 'shopping_item_toggle') AS shopping_toggle_count,
                MAX(created_at) AS last_event_at
            FROM user_events
            WHERE recipe_id IS NOT NULL
            GROUP BY user_id, recipe_id
        ),
        profile_features AS (
            SELECT
                up.*,
                CASE
                    WHEN up.daily_budget_rub IS NOT NULL THEN up.daily_budget_rub
                    WHEN up.weekly_budget_rub IS NOT NULL THEN ROUND(up.weekly_budget_rub / 7, 2)
                    ELSE NULL
                END AS effective_daily_budget_rub,
                CASE
                    WHEN up.meals_per_day IS NULL OR up.meals_per_day <= 0 THEN NULL
                    WHEN up.daily_budget_rub IS NOT NULL THEN ROUND(up.daily_budget_rub / up.meals_per_day, 2)
                    WHEN up.weekly_budget_rub IS NOT NULL THEN ROUND(up.weekly_budget_rub / 7 / up.meals_per_day, 2)
                    ELSE NULL
                END AS budget_per_meal_rub,
                CASE
                    WHEN up.meals_per_day IS NULL OR up.meals_per_day <= 0 THEN NULL
                    WHEN up.daily_calorie_target IS NOT NULL THEN ROUND(up.daily_calorie_target / up.meals_per_day, 2)
                    ELSE NULL
                END AS calorie_target_per_meal
            FROM user_profiles up
        )
        SELECT
            urf.user_id::text AS user_id,
            CASE WHEN u.email LIKE 'bootstrap.%@tasteplanner.local' THEN TRUE ELSE FALSE END AS is_bootstrap_user,
            urf.recipe_id,
            CASE
                WHEN urf.rating IS NOT NULL THEN urf.rating::float
                WHEN urf.liked IS TRUE THEN 5.0
                WHEN urf.liked IS FALSE THEN 1.0
                ELSE NULL
            END AS target_rating,
            urf.liked AS target_liked,
            urf.reason AS feedback_reason,
            urf.too_expensive,
            urf.too_long,
            urf.contains_disliked,
            urf.too_many_calories,
            urf.not_enough_calories,
            urf.updated_at AS feedback_updated_at,
            pf.sex,
            pf.age,
            pf.height_cm,
            pf.weight_kg,
            pf.activity_level,
            pf.goal,
            pf.region_code,
            pf.daily_calorie_target,
            pf.daily_budget_rub,
            pf.weekly_budget_rub,
            pf.effective_daily_budget_rub,
            pf.budget_per_meal_rub,
            pf.calorie_target_per_meal,
            pf.meals_per_day,
            pf.favorite_products_json,
            pf.disliked_products_json,
            pf.allergies_json,
            rf.source,
            rf.source_recipe_id,
            rf.title AS recipe_title,
            rf.total_minutes,
            rf.calories,
            rf.protein,
            rf.fat,
            rf.carbs,
            rf.source_rating,
            rf.ingredient_count,
            rf.priced_ingredient_count,
            rf.price_coverage,
            rf.estimated_cost_rub,
            rf.canonical_ingredients_json,
            rf.product_categories_json,
            rf.has_meat,
            rf.has_fish,
            rf.has_dairy,
            rf.has_grains,
            rf.has_vegetables,
            rf.has_fruit,
            rf.has_legumes,
            rf.has_nuts,
            rf.has_pantry,
            rf.budget_tier,
            rf.time_tier,
            rf.calorie_tier,
            rf.protein_tier,
            rf.seasonal_months_json,
            rf.seasonal_ingredient_count,
            EXTRACT(MONTH FROM CURRENT_DATE)::int AS current_month,
            CASE
                WHEN rf.seasonal_months_json
                    @> to_jsonb(EXTRACT(MONTH FROM CURRENT_DATE)::int)
                THEN TRUE
                ELSE FALSE
            END AS is_seasonal_now,
            CASE
                WHEN pf.budget_per_meal_rub IS NULL OR rf.estimated_cost_rub IS NULL THEN NULL
                ELSE ROUND(rf.estimated_cost_rub / NULLIF(pf.budget_per_meal_rub, 0), 4)
            END AS cost_to_budget_ratio,
            CASE
                WHEN pf.calorie_target_per_meal IS NULL OR rf.calories IS NULL THEN NULL
                ELSE ROUND(rf.calories / NULLIF(pf.calorie_target_per_meal, 0), 4)
            END AS calorie_to_target_ratio,
            COALESCE(ef.event_count, 0) AS event_count,
            COALESCE(ef.open_count, 0) AS open_count,
            COALESCE(ef.favorite_toggle_count, 0) AS favorite_toggle_count,
            COALESCE(ef.shopping_toggle_count, 0) AS shopping_toggle_count,
            ef.last_event_at
        FROM user_recipe_feedback urf
        JOIN recipe_features rf ON rf.recipe_id = urf.recipe_id
        LEFT JOIN users u ON u.id = urf.user_id
        LEFT JOIN profile_features pf ON pf.user_id = urf.user_id
        LEFT JOIN event_features ef
            ON ef.user_id = urf.user_id
           AND ef.recipe_id = urf.recipe_id
        WHERE rf.is_user_facing = TRUE
        ORDER BY urf.updated_at DESC NULLS LAST, urf.recipe_id
        {limit_clause}
        """
    )

    with engine.begin() as conn:
        ensure_schema(conn, refresh_features=refresh_features)
        df = pd.read_sql_query(query, conn, params={"limit": limit} if limit else None)

    for column in (
        "favorite_products_json",
        "disliked_products_json",
        "allergies_json",
        "canonical_ingredients_json",
        "product_categories_json",
        "seasonal_months_json",
    ):
        if column in df.columns:
            df[column] = df[column].apply(json_for_csv)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")

    metadata_path = output_path.with_suffix(".metadata.json")
    metadata_path.write_text(
        json.dumps(
            {
                "rows": int(len(df)),
                "columns": list(df.columns),
                "output": str(output_path),
                "bootstrap_rows": int(
                    df["is_bootstrap_user"].fillna(False).sum()
                    if "is_bootstrap_user" in df.columns
                    else 0
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return len(df)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export TastePlanner user feedback and recipe features for model training."
    )
    parser.add_argument("--db-url", default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--no-refresh-features",
        action="store_true",
        help="Do not rebuild recipe_features before exporting.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_url = resolve_db_url(args.db_url)
    rows = export_training_dataset(
        db_url,
        args.output,
        args.limit,
        refresh_features=not args.no_refresh_features,
    )
    print(f"Exported {rows} rows to {args.output}")


if __name__ == "__main__":
    main()
