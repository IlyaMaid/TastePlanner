from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AliasGroup:
    category: str
    aliases: list[str]


ALIAS_GROUPS = [
    AliasGroup("vegetables", ["помидор", "помидоры", "томат", "томаты", "tomato", "tomatoes"]),
    AliasGroup("vegetables", ["картофель", "картошка", "potato", "potatoes"]),
    AliasGroup("vegetables", ["морковь", "морковка", "carrot", "carrots"]),
    AliasGroup("vegetables", ["лук", "лук репчатый", "onion", "onions"]),
    AliasGroup("vegetables", ["чеснок", "garlic"]),
    AliasGroup("vegetables", ["капуста", "cabbage"]),
    AliasGroup("vegetables", ["перец", "болгарский перец", "pepper", "bell pepper"]),
    AliasGroup("vegetables", ["грибы", "шампиньоны", "mushroom", "mushrooms"]),
    AliasGroup("meat", ["курица", "куриная грудка", "chicken", "chicken breast"]),
    AliasGroup("meat", ["говядина", "beef"]),
    AliasGroup("meat", ["свинина", "pork"]),
    AliasGroup("fish", ["рыба", "fish"]),
    AliasGroup("fish", ["лосось", "семга", "salmon"]),
    AliasGroup("fish", ["треска", "cod"]),
    AliasGroup("fish", ["креветки", "shrimp", "prawn", "prawns"]),
    AliasGroup("dairy_eggs", ["молоко", "milk"]),
    AliasGroup("dairy_eggs", ["сыр", "cheese"]),
    AliasGroup("dairy_eggs", ["творог", "cottage cheese"]),
    AliasGroup("dairy_eggs", ["йогурт", "yogurt", "yoghurt"]),
    AliasGroup("dairy_eggs", ["сметана", "sour cream"]),
    AliasGroup("dairy_eggs", ["яйцо", "яйца", "egg", "eggs"]),
    AliasGroup("grains", ["рис", "rice"]),
    AliasGroup("grains", ["гречка", "гречневая крупа", "buckwheat"]),
    AliasGroup("grains", ["овсянка", "овсяные хлопья", "oats", "oatmeal"]),
    AliasGroup("grains", ["макароны", "паста", "pasta", "macaroni"]),
    AliasGroup("grains", ["мука", "пшеничная мука", "flour"]),
    AliasGroup("grains", ["хлеб", "bread"]),
    AliasGroup("fruit", ["яблоко", "яблоки", "apple", "apples"]),
    AliasGroup("fruit", ["банан", "бананы", "banana", "bananas"]),
    AliasGroup("fruit", ["апельсин", "апельсины", "orange", "oranges"]),
    AliasGroup("fruit", ["лимон", "лимоны", "lemon", "lemons"]),
    AliasGroup("legumes", ["фасоль", "beans", "bean"]),
    AliasGroup("legumes", ["горох", "peas", "pea"]),
    AliasGroup("legumes", ["чечевица", "lentil", "lentils"]),
    AliasGroup("nuts", ["орехи", "грецкий орех", "walnut", "walnuts", "nuts"]),
    AliasGroup("nuts", ["миндаль", "almond", "almonds"]),
    AliasGroup("pantry", ["масло", "растительное масло", "подсолнечное масло", "oil"]),
    AliasGroup("pantry", ["оливковое масло", "olive oil"]),
    AliasGroup("pantry", ["сахар", "sugar"]),
    AliasGroup("pantry", ["соль", "salt"]),
    AliasGroup("pantry", ["мед", "мёд", "honey"]),
    AliasGroup("pantry", ["майонез", "mayonnaise", "mayo"]),
    AliasGroup("sweets", ["шоколад", "chocolate"]),
]


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
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS ingredient_aliases (
                id BIGSERIAL PRIMARY KEY,
                ingredient_id BIGINT REFERENCES ingredients(id) ON DELETE CASCADE,
                alias TEXT UNIQUE NOT NULL
            )
            """
        )
    )


def find_ingredient_id(conn, aliases: list[str]):
    for alias in aliases:
        row = conn.execute(
            text(
                """
                SELECT id
                FROM ingredients
                WHERE canonical_name ILIKE :pattern
                   OR display_name_ru ILIKE :pattern
                ORDER BY
                    CASE
                        WHEN canonical_name ILIKE :exact OR display_name_ru ILIKE :exact THEN 0
                        ELSE 1
                    END,
                    id
                LIMIT 1
                """
            ),
            {
                "pattern": f"%{alias}%",
                "exact": alias,
            },
        ).first()
        if row:
            return row[0]
    return None


def seed_aliases(db_url: str) -> dict[str, int]:
    engine = create_engine(db_url)
    inserted = 0
    categorized = 0
    skipped = 0

    with engine.begin() as conn:
        ensure_schema(conn)
        for group in ALIAS_GROUPS:
            ingredient_id = find_ingredient_id(conn, group.aliases)
            if ingredient_id is None:
                skipped += len(group.aliases)
                continue

            result = conn.execute(
                text(
                    """
                    UPDATE ingredients
                    SET category = COALESCE(category, :category)
                    WHERE id = :ingredient_id
                      AND category IS NULL
                    """
                ),
                {"ingredient_id": ingredient_id, "category": group.category},
            )
            categorized += result.rowcount or 0

            for alias in group.aliases:
                result = conn.execute(
                    text(
                        """
                        INSERT INTO ingredient_aliases (ingredient_id, alias)
                        VALUES (:ingredient_id, :alias)
                        ON CONFLICT (alias) DO NOTHING
                        """
                    ),
                    {
                        "ingredient_id": ingredient_id,
                        "alias": alias.casefold(),
                    },
                )
                inserted += result.rowcount or 0

    return {
        "inserted_aliases": inserted,
        "categorized_ingredients": categorized,
        "skipped_aliases": skipped,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed ingredient aliases for stable product matching."
    )
    parser.add_argument("--db-url", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = seed_aliases(resolve_db_url(args.db_url))
    print(
        "Seeded "
        f"{summary['inserted_aliases']} aliases, "
        f"categorized {summary['categorized_ingredients']} ingredients, "
        f"skipped {summary['skipped_aliases']} aliases"
    )


if __name__ == "__main__":
    main()
