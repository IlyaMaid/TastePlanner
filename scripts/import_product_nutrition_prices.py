from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text


DEFAULT_DATASET_PATH = Path("datasets/russian_product_nutrition_prices.csv")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_dataset_path(csv_path: Optional[str]) -> Path:
    if csv_path:
        path = Path(csv_path)
        if not path.exists():
            raise SystemExit(f"CSV file not found: {path}")
        return path

    default_path = PROJECT_ROOT / DEFAULT_DATASET_PATH
    if default_path.exists():
        return default_path

    raise SystemExit(
        "Product dataset not found. Place russian_product_nutrition_prices.csv "
        "in datasets/ or pass an explicit path with --csv."
    )


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


def optional_float(value):
    if pd.isna(value) or value == "":
        return None
    return float(value)


def optional_text(value):
    if pd.isna(value):
        return None
    normalized = str(value).strip()
    return normalized or None


def split_aliases(value) -> list[str]:
    normalized = optional_text(value)
    if not normalized:
        return []
    return [item.strip() for item in normalized.split(";") if item.strip()]


def ensure_schema(conn) -> None:
    migration_path = PROJECT_ROOT / "postgress/ingredient_prices_migration.sql"
    if migration_path.exists():
        conn.execute(text(migration_path.read_text(encoding="utf-8")))


def ensure_alias(conn, ingredient_id: int, alias: str) -> None:
    conn.execute(
        text(
            """
            INSERT INTO ingredient_aliases (ingredient_id, alias)
            VALUES (:ingredient_id, :alias)
            ON CONFLICT (alias) DO NOTHING
            """
        ),
        {"ingredient_id": ingredient_id, "alias": alias},
    )


def import_products(csv_path: str, db_url: str) -> None:
    dataframe = pd.read_csv(csv_path)
    engine = create_engine(db_url)
    imported = 0

    with engine.begin() as conn:
        ensure_schema(conn)
        for _, row in dataframe.iterrows():
            canonical_name = optional_text(row.get("canonical_name"))
            if not canonical_name:
                continue

            ingredient = conn.execute(
                text(
                    """
                    INSERT INTO ingredients (
                        canonical_name,
                        display_name_ru,
                        category,
                        calories_per_100g,
                        protein_per_100g,
                        fat_per_100g,
                        carbs_per_100g,
                        price_per_100g_rub,
                        price_source,
                        price_updated_at
                    )
                    VALUES (
                        :canonical_name,
                        :display_name_ru,
                        :category,
                        :calories_per_100g,
                        :protein_per_100g,
                        :fat_per_100g,
                        :carbs_per_100g,
                        :price_per_100g_rub,
                        :price_source,
                        :price_updated_at
                    )
                    ON CONFLICT (canonical_name)
                    DO UPDATE SET
                        display_name_ru = EXCLUDED.display_name_ru,
                        category = EXCLUDED.category,
                        calories_per_100g = EXCLUDED.calories_per_100g,
                        protein_per_100g = EXCLUDED.protein_per_100g,
                        fat_per_100g = EXCLUDED.fat_per_100g,
                        carbs_per_100g = EXCLUDED.carbs_per_100g,
                        price_per_100g_rub = EXCLUDED.price_per_100g_rub,
                        price_source = EXCLUDED.price_source,
                        price_updated_at = EXCLUDED.price_updated_at
                    RETURNING id
                    """
                ),
                {
                    "canonical_name": canonical_name,
                    "display_name_ru": optional_text(row.get("display_name_ru")),
                    "category": optional_text(row.get("category")),
                    "calories_per_100g": optional_float(row.get("calories_per_100g")),
                    "protein_per_100g": optional_float(row.get("protein_per_100g")),
                    "fat_per_100g": optional_float(row.get("fat_per_100g")),
                    "carbs_per_100g": optional_float(row.get("carbs_per_100g")),
                    "price_per_100g_rub": optional_float(row.get("price_per_100g_rub")),
                    "price_source": optional_text(row.get("price_source")),
                    "price_updated_at": optional_text(row.get("price_updated_at")),
                },
            ).fetchone()

            ingredient_id = int(ingredient[0])
            for alias in [canonical_name, optional_text(row.get("display_name_ru"))]:
                if alias:
                    ensure_alias(conn, ingredient_id, alias)
            for alias in split_aliases(row.get("aliases_ru")):
                ensure_alias(conn, ingredient_id, alias)

            imported += 1

    print(f"Imported {imported} products into PostgreSQL.")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import Russian product nutrition and price dataset into TastePlanner"
    )
    parser.add_argument("--csv", help="Path to product nutrition and price CSV")
    parser.add_argument("--db-url", help="SQLAlchemy PostgreSQL URL")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    import_products(str(resolve_dataset_path(args.csv)), resolve_db_url(args.db_url))


if __name__ == "__main__":
    main()
