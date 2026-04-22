from __future__ import annotations

import argparse
import ast
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
from sqlalchemy import create_engine, text


INGREDIENT_CLEAN_RE = re.compile(r"[^a-zA-Zа-яА-ЯёЁ0-9\s\-]+")
MULTISPACE_RE = re.compile(r"\s+")
POVARENOK_ID_RE = re.compile(r"/show/(\d+)/?")
DEFAULT_DATASET_CANDIDATES = [
    Path("datasets/povarenok_recipes_2021_06_16.csv"),
    Path("datasets/raw/povarenok_recipes_2021_06_16.csv"),
]


@dataclass
class ParsedIngredient:
    raw_name: str
    canonical_name: str
    raw_amount: Optional[str]


@dataclass
class ParsedRecipe:
    source_recipe_id: str
    title: str
    source_url: str
    ingredients: list[ParsedIngredient]


def clean_text(value: str) -> str:
    value = value.strip().lower()
    value = INGREDIENT_CLEAN_RE.sub(" ", value)
    value = MULTISPACE_RE.sub(" ", value)
    return value.strip()


def canonicalize_ingredient(raw: str) -> str:
    return clean_text(raw)


def parse_ingredients(value: object) -> list[ParsedIngredient]:
    if pd.isna(value):
        return []

    try:
        parsed = ast.literal_eval(value) if isinstance(value, str) else value
    except (ValueError, SyntaxError):
        return []

    if not isinstance(parsed, dict):
        return []

    result: list[ParsedIngredient] = []
    for raw_name, raw_amount in parsed.items():
        raw_name = str(raw_name).strip()
        canonical_name = canonicalize_ingredient(raw_name)
        if not canonical_name:
            continue
        result.append(
            ParsedIngredient(
                raw_name=raw_name,
                canonical_name=canonical_name,
                raw_amount=(
                    str(raw_amount).strip()
                    if raw_amount is not None and str(raw_amount).strip()
                    else None
                ),
            )
        )
    return result


def extract_source_recipe_id(url: str) -> str:
    match = POVARENOK_ID_RE.search(url)
    if match:
        return match.group(1)
    return url.strip()


def parse_row(row: pd.Series) -> ParsedRecipe:
    url = str(row.get("url", "")).strip()
    title = str(row.get("name", "")).strip()
    return ParsedRecipe(
        source_recipe_id=extract_source_recipe_id(url),
        title=title,
        source_url=url,
        ingredients=parse_ingredients(row.get("ingredients")),
    )


def get_or_create_ingredient(conn, canonical_name: str) -> int:
    row = conn.execute(
        text("SELECT id FROM ingredients WHERE canonical_name = :name"),
        {"name": canonical_name},
    ).fetchone()
    if row:
        return int(row[0])

    row = conn.execute(
        text(
            """
            INSERT INTO ingredients (canonical_name)
            VALUES (:name)
            RETURNING id
            """
        ),
        {"name": canonical_name},
    ).fetchone()
    return int(row[0])


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


def insert_recipe(conn, recipe: ParsedRecipe) -> int:
    row = conn.execute(
        text(
            """
            INSERT INTO recipes (
                source,
                source_recipe_id,
                title,
                description,
                steps_json
            )
            VALUES (
                'povarenok',
                :source_recipe_id,
                :title,
                :description,
                CAST(:steps_json AS JSONB)
            )
            ON CONFLICT (source, source_recipe_id)
            DO UPDATE SET
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                steps_json = EXCLUDED.steps_json
            RETURNING id
            """
        ),
        {
            "source_recipe_id": recipe.source_recipe_id,
            "title": recipe.title,
            "description": f"Источник: {recipe.source_url}" if recipe.source_url else None,
            "steps_json": json.dumps([], ensure_ascii=False),
        },
    ).fetchone()
    return int(row[0])


def replace_recipe_ingredients(
    conn,
    recipe_id: int,
    ingredients: Iterable[ParsedIngredient],
) -> None:
    conn.execute(
        text("DELETE FROM recipe_ingredients WHERE recipe_id = :recipe_id"),
        {"recipe_id": recipe_id},
    )
    for ingredient in ingredients:
        ingredient_id = get_or_create_ingredient(conn, ingredient.canonical_name)
        ensure_alias(conn, ingredient_id, ingredient.raw_name)
        conn.execute(
            text(
                """
                INSERT INTO recipe_ingredients (
                    recipe_id,
                    ingredient_id,
                    raw_text,
                    unit
                )
                VALUES (
                    :recipe_id,
                    :ingredient_id,
                    :raw_text,
                    :unit
                )
                """
            ),
            {
                "recipe_id": recipe_id,
                "ingredient_id": ingredient_id,
                "raw_text": (
                    f"{ingredient.raw_name} - {ingredient.raw_amount}"
                    if ingredient.raw_amount
                    else ingredient.raw_name
                ),
                "unit": ingredient.raw_amount,
            },
        )


def import_povarenok(csv_path: str, db_url: str, limit: Optional[int] = None) -> None:
    df = pd.read_csv(csv_path)
    if limit:
        df = df.head(limit)

    engine = create_engine(db_url)
    inserted = 0

    with engine.begin() as conn:
        for _, row in df.iterrows():
            recipe = parse_row(row)
            if not recipe.title or not recipe.source_recipe_id:
                continue
            recipe_id = insert_recipe(conn, recipe)
            replace_recipe_ingredients(conn, recipe_id, recipe.ingredients)
            inserted += 1

    print(f"Imported {inserted} recipes into PostgreSQL.")


def resolve_csv_path(csv_path: Optional[str]) -> Path:
    if csv_path:
        path = Path(csv_path)
        if not path.exists():
            raise SystemExit(f"CSV file not found: {path}")
        return path

    for candidate in DEFAULT_DATASET_CANDIDATES:
        if candidate.exists():
            return candidate

    raise SystemExit(
        "Dataset CSV not found. Place povarenok_recipes_2021_06_16.csv in datasets/ "
        "or pass an explicit path with --csv."
    )


def resolve_db_url(db_url: Optional[str]) -> str:
    if db_url:
        return db_url

    env_db_url = os.getenv("DATABASE_URL")
    if env_db_url:
        return env_db_url

    backend_env_path = Path("backend/.env")
    if backend_env_path.exists():
        for line in backend_env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip()

    raise SystemExit(
        "--db-url is required unless DATABASE_URL is available in the environment "
        "or backend/.env"
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import Povarenok recipes into TastePlanner database"
    )
    parser.add_argument("--csv", help="Path to povarenok CSV")
    parser.add_argument("--db-url", help="SQLAlchemy PostgreSQL URL")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional row limit for test imports",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    import_povarenok(str(resolve_csv_path(args.csv)), resolve_db_url(args.db_url), args.limit)


if __name__ == "__main__":
    main()
