from __future__ import annotations

import argparse
import ast
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
from sqlalchemy import create_engine, text


INGREDIENT_CLEAN_RE = re.compile(r"[^a-zA-Zа-яА-Я0-9\s\-]+")
MULTISPACE_RE = re.compile(r"\s+")
DEFAULT_DATASET_CANDIDATES = [
    Path("datasets/raw/RAW_recipes.csv"),
    Path("datasets/raw/recipes.csv"),
    Path("datasets/RAW_recipes.csv"),
    Path("datasets/recipes.csv"),
]


@dataclass
class ParsedRecipe:
    source_recipe_id: str
    title: str
    description: Optional[str]
    total_minutes: Optional[int]
    steps: List[str]
    ingredients: List[str]
    calories: Optional[float]
    fat: Optional[float]
    carbs: Optional[float]
    protein: Optional[float]


def safe_eval(value) -> list:
    if pd.isna(value):
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = ast.literal_eval(value)
        return parsed if isinstance(parsed, list) else []
    except (ValueError, SyntaxError):
        return []


def clean_text(value: str) -> str:
    value = value.strip().lower()
    value = INGREDIENT_CLEAN_RE.sub(" ", value)
    value = MULTISPACE_RE.sub(" ", value)
    return value.strip()


def canonicalize_ingredient(raw: str) -> str:
    value = clean_text(raw)
    replacements = {
        "extra virgin olive oil": "olive oil",
        "black pepper": "pepper",
        "sea salt": "salt",
        "kosher salt": "salt",
    }
    return replacements.get(value, value)


def to_optional_int(value) -> Optional[int]:
    if pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_optional_float(value) -> Optional[float]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_nutrition(values: list) -> dict:
    return {
        "calories": to_optional_float(values[0]) if len(values) > 0 else None,
        "fat": to_optional_float(values[1]) if len(values) > 1 else None,
        "protein": to_optional_float(values[4]) if len(values) > 4 else None,
        "carbs": to_optional_float(values[6]) if len(values) > 6 else None,
    }


def parse_row(row: pd.Series) -> ParsedRecipe:
    ingredients = safe_eval(row.get("ingredients"))
    steps = safe_eval(row.get("steps"))
    nutrition = parse_nutrition(safe_eval(row.get("nutrition")))

    normalized_ingredients = [
        canonicalize_ingredient(x) for x in ingredients if clean_text(str(x))
    ]
    normalized_steps = [str(x).strip() for x in steps if str(x).strip()]

    return ParsedRecipe(
        source_recipe_id=str(row.get("id")),
        title=str(row.get("name", "")).strip(),
        description=(
            str(row.get("description")).strip()
            if pd.notna(row.get("description"))
            else None
        ),
        total_minutes=to_optional_int(row.get("minutes")),
        steps=normalized_steps,
        ingredients=normalized_ingredients,
        calories=nutrition["calories"],
        fat=nutrition["fat"],
        carbs=nutrition["carbs"],
        protein=nutrition["protein"],
    )


def export_clean_json(df: pd.DataFrame, output_json: str) -> None:
    parsed = [parse_row(row).__dict__ for _, row in df.iterrows()]
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)


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
                steps_json,
                total_minutes,
                calories,
                protein,
                fat,
                carbs
            )
            VALUES (
                'foodcom',
                :source_recipe_id,
                :title,
                :description,
                CAST(:steps_json AS JSONB),
                :total_minutes,
                :calories,
                :protein,
                :fat,
                :carbs
            )
            ON CONFLICT (source, source_recipe_id)
            DO UPDATE SET
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                steps_json = EXCLUDED.steps_json,
                total_minutes = EXCLUDED.total_minutes,
                calories = EXCLUDED.calories,
                protein = EXCLUDED.protein,
                fat = EXCLUDED.fat,
                carbs = EXCLUDED.carbs
            RETURNING id
            """
        ),
        {
            "source_recipe_id": recipe.source_recipe_id,
            "title": recipe.title,
            "description": recipe.description,
            "steps_json": json.dumps(recipe.steps, ensure_ascii=False),
            "total_minutes": recipe.total_minutes,
            "calories": recipe.calories,
            "protein": recipe.protein,
            "fat": recipe.fat,
            "carbs": recipe.carbs,
        },
    ).fetchone()
    return int(row[0])


def replace_recipe_ingredients(
    conn,
    recipe_id: int,
    ingredient_names: Iterable[str],
) -> None:
    conn.execute(
        text("DELETE FROM recipe_ingredients WHERE recipe_id = :recipe_id"),
        {"recipe_id": recipe_id},
    )
    for raw_name in ingredient_names:
        canonical_name = canonicalize_ingredient(raw_name)
        if not canonical_name:
            continue
        ingredient_id = get_or_create_ingredient(conn, canonical_name)
        ensure_alias(conn, ingredient_id, raw_name)
        conn.execute(
            text(
                """
                INSERT INTO recipe_ingredients (recipe_id, ingredient_id, raw_text)
                VALUES (:recipe_id, :ingredient_id, :raw_text)
                """
            ),
            {
                "recipe_id": recipe_id,
                "ingredient_id": ingredient_id,
                "raw_text": raw_name,
            },
        )


def import_foodcom(csv_path: str, db_url: str, limit: Optional[int] = None) -> None:
    df = pd.read_csv(csv_path)
    if limit:
        df = df.head(limit)

    engine = create_engine(db_url)
    inserted = 0

    with engine.begin() as conn:
        for _, row in df.iterrows():
            recipe = parse_row(row)
            if not recipe.title:
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
        "Dataset CSV not found. Place RAW_recipes.csv in datasets/raw/ "
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
        description="Import Food.com recipes into TastePlanner database"
    )
    parser.add_argument("--csv", help="Path to RAW_recipes.csv")
    parser.add_argument("--db-url", help="SQLAlchemy PostgreSQL URL")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional row limit for test imports",
    )
    parser.add_argument(
        "--output-json",
        help="Optional path to export cleaned recipes as JSON instead of DB import",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    csv_path = resolve_csv_path(args.csv)
    df = pd.read_csv(csv_path)

    if args.output_json:
        if args.limit:
            df = df.head(args.limit)
        export_clean_json(df, args.output_json)
        print(f"Saved cleaned JSON to {args.output_json}")
        return

    import_foodcom(str(csv_path), resolve_db_url(args.db_url), args.limit)


if __name__ == "__main__":
    main()
