from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from deep_translator import GoogleTranslator, MyMemoryTranslator
from sqlalchemy import create_engine, text


DEFAULT_LIMIT = 100
DEFAULT_SLEEP_SECONDS = 0.25
DEFAULT_RETRIES = 3


def resolve_db_url(db_url: str | None) -> str:
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
        "--db-url is required unless DATABASE_URL is available in the environment or backend/.env"
    )


def normalize_translation(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def translate_text(translators, value: str | None, retries: int) -> str | None:
    value = normalize_translation(value)
    if not value:
        return None

    last_error = None
    for translator in translators:
        for _ in range(retries):
            try:
                return normalize_translation(translator.translate(value))
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                time.sleep(0.5)

    if last_error is not None:
        print(f"Translation fallback failed for: {value[:80]!r} -> {last_error}")
    return None


def translate_ingredients(
    translators,
    ingredients: list[str] | None,
    retries: int,
) -> list[str]:
    if not ingredients:
        return []
    translated: list[str] = []
    for ingredient in ingredients:
        translated_value = translate_text(translators, ingredient, retries)
        translated.append(translated_value or ingredient)
    return translated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate imported Food.com recipes into Russian UI fields"
    )
    parser.add_argument("--db-url", help="SQLAlchemy PostgreSQL URL")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="How many untranslated Food.com recipes to process",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help="Pause between translated recipes to reduce rate-limit pressure",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="How many times to retry a failed external translation request",
    )
    parser.add_argument(
        "--recipe-db-ids",
        help="Comma-separated recipe ids from the local DB to translate first",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = create_engine(resolve_db_url(args.db_url))
    translators = [
        GoogleTranslator(source="en", target="ru"),
        MyMemoryTranslator(source="en-US", target="ru-RU"),
    ]

    with engine.connect() as conn:
        if args.recipe_db_ids:
            recipe_ids = [
                int(item.strip())
                for item in args.recipe_db_ids.split(",")
                if item.strip()
            ]
            rows = conn.execute(
                text(
                    """
                    SELECT
                        r.id,
                        r.title,
                        r.description,
                        COALESCE(
                            (
                                SELECT json_agg(ingredient_row.raw_text ORDER BY ingredient_row.id)
                                FROM (
                                    SELECT ri.id, ri.raw_text
                                    FROM recipe_ingredients ri
                                    WHERE ri.recipe_id = r.id
                                    ORDER BY ri.id
                                    LIMIT 8
                                ) AS ingredient_row
                            ),
                            '[]'::json
                        ) AS ingredients
                    FROM recipes r
                    WHERE r.source = 'foodcom'
                      AND r.id = ANY(:recipe_ids)
                    ORDER BY r.id
                    """
                ),
                {"recipe_ids": recipe_ids},
            ).mappings().all()
        else:
            rows = conn.execute(
                text(
                    """
                    SELECT
                        r.id,
                        r.title,
                        r.description,
                        COALESCE(
                            (
                                SELECT json_agg(ingredient_row.raw_text ORDER BY ingredient_row.id)
                                FROM (
                                    SELECT ri.id, ri.raw_text
                                    FROM recipe_ingredients ri
                                    WHERE ri.recipe_id = r.id
                                    ORDER BY ri.id
                                    LIMIT 8
                                ) AS ingredient_row
                            ),
                            '[]'::json
                        ) AS ingredients
                    FROM recipes r
                    WHERE r.source = 'foodcom'
                      AND (
                          r.translated_title IS NULL
                          OR r.translated_ingredients_json IS NULL
                      )
                    ORDER BY r.id
                    LIMIT :limit
                    """
                ),
                {"limit": args.limit},
            ).mappings().all()

        translated_count = 0
        for row in rows:
            translated_title = translate_text(translators, row["title"], args.retries)
            translated_description = translate_text(
                translators,
                row["description"],
                args.retries,
            )
            translated_ingredients = translate_ingredients(
                translators,
                list(row["ingredients"] or []),
                args.retries,
            )

            conn.execute(
                text(
                    """
                    UPDATE recipes
                    SET
                        translated_title = :translated_title,
                        translated_description = :translated_description,
                        translated_ingredients_json = CAST(:translated_ingredients_json AS jsonb)
                    WHERE id = :recipe_id
                    """
                ),
                {
                    "recipe_id": row["id"],
                    "translated_title": translated_title,
                    "translated_description": translated_description,
                    "translated_ingredients_json": json.dumps(
                        translated_ingredients,
                        ensure_ascii=False,
                    ),
                },
            )
            conn.commit()
            translated_count += 1
            if args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)

    print(f"Translated {translated_count} Food.com recipes.")


if __name__ == "__main__":
    main()
