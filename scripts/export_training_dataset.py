from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
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


def ensure_schema(conn) -> None:
    for migration_name in (
        "profile_budget_migration.sql",
        "feedback_training_signals_migration.sql",
    ):
        migration_path = PROJECT_ROOT / "postgress" / migration_name
        if migration_path.exists():
            conn.execute(text(migration_path.read_text(encoding="utf-8")))


def json_for_csv(value) -> str:
    if value is None:
        return "[]"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def export_training_dataset(db_url: str, output_path: Path, limit: Optional[int]) -> int:
    engine = create_engine(db_url)
    limit_clause = "LIMIT :limit" if limit else ""

    query = text(
        f"""
        WITH recipe_costs AS (
            SELECT
                ri.recipe_id,
                COUNT(*) AS ingredient_count,
                ROUND(SUM(i.price_per_100g_rub), 2) AS estimated_cost_rub,
                COUNT(*) FILTER (WHERE i.price_per_100g_rub IS NOT NULL) AS priced_ingredient_count
            FROM recipe_ingredients ri
            LEFT JOIN ingredients i ON i.id = ri.ingredient_id
            GROUP BY ri.recipe_id
        ),
        event_features AS (
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
        )
        SELECT
            urf.user_id::text AS user_id,
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
            up.sex,
            up.age,
            up.height_cm,
            up.weight_kg,
            up.activity_level,
            up.goal,
            up.region_code,
            up.daily_calorie_target,
            up.daily_budget_rub,
            up.weekly_budget_rub,
            up.meals_per_day,
            up.favorite_products_json,
            up.disliked_products_json,
            up.allergies_json,
            r.source,
            r.source_recipe_id,
            COALESCE(r.translated_title, r.title) AS recipe_title,
            r.total_minutes,
            r.calories,
            r.protein,
            r.fat,
            r.carbs,
            r.rating AS source_rating,
            COALESCE(rc.ingredient_count, 0) AS ingredient_count,
            COALESCE(rc.priced_ingredient_count, 0) AS priced_ingredient_count,
            rc.estimated_cost_rub,
            COALESCE(ef.event_count, 0) AS event_count,
            COALESCE(ef.open_count, 0) AS open_count,
            COALESCE(ef.favorite_toggle_count, 0) AS favorite_toggle_count,
            COALESCE(ef.shopping_toggle_count, 0) AS shopping_toggle_count,
            ef.last_event_at
        FROM user_recipe_feedback urf
        JOIN recipes r ON r.id = urf.recipe_id
        LEFT JOIN user_profiles up ON up.user_id = urf.user_id
        LEFT JOIN recipe_costs rc ON rc.recipe_id = urf.recipe_id
        LEFT JOIN event_features ef
            ON ef.user_id = urf.user_id
           AND ef.recipe_id = urf.recipe_id
        ORDER BY urf.updated_at DESC NULLS LAST, urf.recipe_id
        {limit_clause}
        """
    )

    with engine.begin() as conn:
        ensure_schema(conn)
        df = pd.read_sql_query(query, conn, params={"limit": limit} if limit else None)

    for column in (
        "favorite_products_json",
        "disliked_products_json",
        "allergies_json",
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_url = resolve_db_url(args.db_url)
    rows = export_training_dataset(db_url, args.output, args.limit)
    print(f"Exported {rows} rows to {args.output}")


if __name__ == "__main__":
    main()
