from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
    for migration_name in ("recipe_quality_migration.sql", "recipe_features_migration.sql"):
        migration_path = PROJECT_ROOT / "postgress" / migration_name
        conn.execute(text(migration_path.read_text(encoding="utf-8")))


def refresh_recipe_features(conn) -> int:
    result = conn.execute(
        text(
            """
            WITH ingredient_features AS (
                SELECT
                    ri.recipe_id,
                    COUNT(*)::int AS ingredient_count,
                    COUNT(*) FILTER (WHERE i.price_per_100g_rub IS NOT NULL)::int AS priced_ingredient_count,
                    ROUND(
                        SUM(
                            CASE
                                WHEN ri.quantity IS NOT NULL
                                  AND ri.unit = 'g'
                                  AND i.price_per_100g_rub IS NOT NULL
                                THEN ri.quantity * i.price_per_100g_rub / 100
                                ELSE i.price_per_100g_rub
                            END
                        ),
                        2
                    ) AS estimated_cost_rub,
                    jsonb_agg(
                        DISTINCT COALESCE(i.display_name_ru, i.canonical_name)
                    ) FILTER (WHERE i.id IS NOT NULL) AS canonical_ingredients_json,
                    jsonb_agg(
                        DISTINCT COALESCE(i.category, 'unknown')
                    ) FILTER (WHERE i.id IS NOT NULL) AS product_categories_json,
                    BOOL_OR(
                        i.category = 'meat'
                        OR i.canonical_name ILIKE ANY(ARRAY['%chicken%', '%beef%', '%pork%', '%meat%'])
                        OR COALESCE(i.display_name_ru, '') ILIKE ANY(ARRAY['%кур%', '%говя%', '%свин%', '%мяс%'])
                    ) AS has_meat,
                    BOOL_OR(
                        i.category = 'fish'
                        OR i.canonical_name ILIKE ANY(ARRAY['%fish%', '%salmon%', '%cod%', '%seafood%'])
                        OR COALESCE(i.display_name_ru, '') ILIKE ANY(ARRAY['%рыб%', '%лосос%', '%треск%', '%морепродукт%'])
                    ) AS has_fish,
                    BOOL_OR(
                        i.category = 'dairy_eggs'
                        OR i.canonical_name ILIKE ANY(ARRAY['%milk%', '%cheese%', '%yogurt%', '%cream%', '%egg%'])
                        OR COALESCE(i.display_name_ru, '') ILIKE ANY(ARRAY['%молок%', '%сыр%', '%йогурт%', '%творог%', '%сметан%', '%яйц%'])
                    ) AS has_dairy,
                    BOOL_OR(
                        i.category = 'grains'
                        OR i.canonical_name ILIKE ANY(ARRAY['%rice%', '%oat%', '%buckwheat%', '%pasta%', '%bread%', '%flour%'])
                        OR COALESCE(i.display_name_ru, '') ILIKE ANY(ARRAY['%рис%', '%греч%', '%овся%', '%макарон%', '%хлеб%', '%мук%'])
                    ) AS has_grains,
                    BOOL_OR(
                        i.category = 'vegetables'
                        OR i.canonical_name ILIKE ANY(ARRAY['%tomato%', '%potato%', '%carrot%', '%pepper%', '%onion%', '%cabbage%'])
                        OR COALESCE(i.display_name_ru, '') ILIKE ANY(ARRAY['%помид%', '%томат%', '%карто%', '%морков%', '%перец%', '%лук%', '%капуст%'])
                    ) AS has_vegetables,
                    BOOL_OR(
                        i.category = 'fruit'
                        OR i.canonical_name ILIKE ANY(ARRAY['%apple%', '%banana%', '%orange%', '%lemon%', '%berry%'])
                        OR COALESCE(i.display_name_ru, '') ILIKE ANY(ARRAY['%яблок%', '%банан%', '%апельс%', '%лимон%', '%ягод%'])
                    ) AS has_fruit,
                    BOOL_OR(
                        i.category = 'legumes'
                        OR i.canonical_name ILIKE ANY(ARRAY['%bean%', '%pea%', '%lentil%'])
                        OR COALESCE(i.display_name_ru, '') ILIKE ANY(ARRAY['%фасол%', '%горох%', '%чечев%'])
                    ) AS has_legumes,
                    BOOL_OR(
                        i.category = 'nuts'
                        OR i.canonical_name ILIKE ANY(ARRAY['%nut%', '%almond%'])
                        OR COALESCE(i.display_name_ru, '') ILIKE ANY(ARRAY['%орех%', '%миндал%'])
                    ) AS has_nuts,
                    BOOL_OR(
                        i.category IN ('pantry', 'sweets')
                        OR i.canonical_name ILIKE ANY(ARRAY['%oil%', '%salt%', '%sugar%', '%honey%', '%sauce%', '%chocolate%'])
                        OR COALESCE(i.display_name_ru, '') ILIKE ANY(ARRAY['%масло%', '%соль%', '%сахар%', '%мед%', '%мёд%', '%соус%', '%шоколад%'])
                    ) AS has_pantry,
                    COALESCE(
                        jsonb_agg(DISTINCT seasonal_month.month_value)
                            FILTER (WHERE seasonal_month.month_value IS NOT NULL),
                        '[]'::jsonb
                    ) AS seasonal_months_json,
                    COUNT(DISTINCT i.id)
                        FILTER (WHERE seasonal_month.month_value IS NOT NULL)
                        AS seasonal_ingredient_count
                FROM recipe_ingredients ri
                LEFT JOIN ingredients i ON i.id = ri.ingredient_id
                LEFT JOIN LATERAL unnest(
                    CASE
                        WHEN i.canonical_name IN ('tomato', 'cucumber', 'pepper', 'zucchini', 'eggplant', 'berries')
                          OR COALESCE(i.display_name_ru, '') ILIKE ANY(ARRAY['%помид%', '%огур%', '%перец%', '%кабач%', '%баклаж%', '%ягод%'])
                        THEN ARRAY[6, 7, 8, 9]
                        WHEN i.canonical_name IN ('pumpkin', 'mushroom', 'apple')
                          OR COALESCE(i.display_name_ru, '') ILIKE ANY(ARRAY['%тыкв%', '%гриб%', '%шампин%', '%яблок%'])
                        THEN ARRAY[8, 9, 10, 11]
                        WHEN i.canonical_name IN ('potato', 'carrot', 'beet', 'cabbage')
                          OR COALESCE(i.display_name_ru, '') ILIKE ANY(ARRAY['%карто%', '%морков%', '%свек%', '%свёк%', '%капуст%'])
                        THEN ARRAY[1, 2, 9, 10, 11, 12]
                        WHEN i.canonical_name IN ('herbs', 'spinach', 'broccoli', 'cauliflower')
                          OR COALESCE(i.display_name_ru, '') ILIKE ANY(ARRAY['%зелень%', '%укроп%', '%петруш%', '%шпин%', '%брокк%', '%цветная капуст%'])
                        THEN ARRAY[4, 5, 6, 7]
                        ELSE ARRAY[]::int[]
                    END
                ) AS seasonal_month(month_value) ON TRUE
                GROUP BY ri.recipe_id
            )
            INSERT INTO recipe_features (
                recipe_id,
                source,
                source_recipe_id,
                title,
                language,
                is_user_facing,
                quality_score,
                tags_json,
                total_minutes,
                calories,
                protein,
                fat,
                carbs,
                source_rating,
                ingredient_count,
                priced_ingredient_count,
                price_coverage,
                estimated_cost_rub,
                canonical_ingredients_json,
                product_categories_json,
                has_meat,
                has_fish,
                has_dairy,
                has_grains,
                has_vegetables,
                has_fruit,
                has_legumes,
                has_nuts,
                has_pantry,
                budget_tier,
                time_tier,
                calorie_tier,
                protein_tier,
                seasonal_months_json,
                seasonal_ingredient_count,
                updated_at
            )
            SELECT
                r.id AS recipe_id,
                r.source,
                r.source_recipe_id,
                COALESCE(r.translated_title, r.title) AS title,
                COALESCE(r.language, 'unknown') AS language,
                r.is_user_facing,
                r.quality_score,
                COALESCE(r.tags_json, '[]'::jsonb) AS tags_json,
                r.total_minutes,
                r.calories,
                r.protein,
                r.fat,
                r.carbs,
                r.rating AS source_rating,
                COALESCE(f.ingredient_count, 0) AS ingredient_count,
                COALESCE(f.priced_ingredient_count, 0) AS priced_ingredient_count,
                CASE
                    WHEN COALESCE(f.ingredient_count, 0) = 0 THEN 0
                    ELSE ROUND(f.priced_ingredient_count::numeric / f.ingredient_count, 4)
                END AS price_coverage,
                f.estimated_cost_rub,
                COALESCE(f.canonical_ingredients_json, '[]'::jsonb),
                COALESCE(f.product_categories_json, '[]'::jsonb),
                COALESCE(f.has_meat, FALSE),
                COALESCE(f.has_fish, FALSE),
                COALESCE(f.has_dairy, FALSE),
                COALESCE(f.has_grains, FALSE),
                COALESCE(f.has_vegetables, FALSE),
                COALESCE(f.has_fruit, FALSE),
                COALESCE(f.has_legumes, FALSE),
                COALESCE(f.has_nuts, FALSE),
                COALESCE(f.has_pantry, FALSE),
                CASE
                    WHEN f.estimated_cost_rub IS NULL THEN 'unknown'
                    WHEN f.estimated_cost_rub <= 150 THEN 'low'
                    WHEN f.estimated_cost_rub <= 350 THEN 'medium'
                    ELSE 'high'
                END AS budget_tier,
                CASE
                    WHEN r.total_minutes IS NULL THEN 'unknown'
                    WHEN r.total_minutes <= 20 THEN 'very_fast'
                    WHEN r.total_minutes <= 45 THEN 'fast'
                    WHEN r.total_minutes <= 90 THEN 'medium'
                    ELSE 'long'
                END AS time_tier,
                CASE
                    WHEN r.calories IS NULL THEN 'unknown'
                    WHEN r.calories <= 300 THEN 'light'
                    WHEN r.calories <= 650 THEN 'balanced'
                    ELSE 'high'
                END AS calorie_tier,
                CASE
                    WHEN r.protein IS NULL THEN 'unknown'
                    WHEN r.protein >= 25 THEN 'high'
                    WHEN r.protein >= 12 THEN 'medium'
                    ELSE 'low'
                END AS protein_tier,
                COALESCE(f.seasonal_months_json, '[]'::jsonb),
                COALESCE(f.seasonal_ingredient_count, 0),
                NOW()
            FROM recipes r
            LEFT JOIN ingredient_features f ON f.recipe_id = r.id
            ON CONFLICT (recipe_id)
            DO UPDATE SET
                source = EXCLUDED.source,
                source_recipe_id = EXCLUDED.source_recipe_id,
                title = EXCLUDED.title,
                language = EXCLUDED.language,
                is_user_facing = EXCLUDED.is_user_facing,
                quality_score = EXCLUDED.quality_score,
                tags_json = EXCLUDED.tags_json,
                total_minutes = EXCLUDED.total_minutes,
                calories = EXCLUDED.calories,
                protein = EXCLUDED.protein,
                fat = EXCLUDED.fat,
                carbs = EXCLUDED.carbs,
                source_rating = EXCLUDED.source_rating,
                ingredient_count = EXCLUDED.ingredient_count,
                priced_ingredient_count = EXCLUDED.priced_ingredient_count,
                price_coverage = EXCLUDED.price_coverage,
                estimated_cost_rub = EXCLUDED.estimated_cost_rub,
                canonical_ingredients_json = EXCLUDED.canonical_ingredients_json,
                product_categories_json = EXCLUDED.product_categories_json,
                has_meat = EXCLUDED.has_meat,
                has_fish = EXCLUDED.has_fish,
                has_dairy = EXCLUDED.has_dairy,
                has_grains = EXCLUDED.has_grains,
                has_vegetables = EXCLUDED.has_vegetables,
                has_fruit = EXCLUDED.has_fruit,
                has_legumes = EXCLUDED.has_legumes,
                has_nuts = EXCLUDED.has_nuts,
                has_pantry = EXCLUDED.has_pantry,
                budget_tier = EXCLUDED.budget_tier,
                time_tier = EXCLUDED.time_tier,
                calorie_tier = EXCLUDED.calorie_tier,
                protein_tier = EXCLUDED.protein_tier,
                seasonal_months_json = EXCLUDED.seasonal_months_json,
                seasonal_ingredient_count = EXCLUDED.seasonal_ingredient_count,
                updated_at = NOW()
            """
        )
    )
    return result.rowcount or 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build stable recipe-level features for TastePlanner training."
    )
    parser.add_argument("--db-url", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = create_engine(resolve_db_url(args.db_url))
    with engine.begin() as conn:
        ensure_schema(conn)
        rows = refresh_recipe_features(conn)
    print(f"Refreshed recipe features for {rows} recipes")


if __name__ == "__main__":
    main()
