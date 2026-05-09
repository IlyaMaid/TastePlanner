from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Iterable

import requests
from deep_translator import GoogleTranslator, MyMemoryTranslator
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIMIT = 100
DEFAULT_BATCH_SIZE = 20
DEFAULT_SLEEP_SECONDS = 0.2
DEFAULT_RETRIES = 3
DEFAULT_CACHE_PATH = PROJECT_ROOT / "artifacts" / "translation_cache_ru.json"
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
TRANSLATION_DELIMITER = "\n<<<TASTEPLANNER_TRANSLATION_SPLIT>>>\n"


def resolve_db_url(db_url: str | None) -> str:
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
        "--db-url is required unless DATABASE_URL is available in the environment or backend/.env"
    )


def normalize_translation(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def load_cache(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_cache(path: Path, cache: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def unique_missing_texts(values: Iterable[str | None], cache: dict[str, str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalize_translation(value)
        if not normalized or normalized in cache or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def chunked(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def translate_batch_with_fallback(
    translators,
    values: list[str],
    retries: int,
) -> dict[str, str]:
    translated: dict[str, str] = {}
    if values:
        for _ in range(retries):
            try:
                joined = TRANSLATION_DELIMITER.join(values)
                response = requests.get(
                    GOOGLE_TRANSLATE_URL,
                    params={
                        "client": "gtx",
                        "sl": "en",
                        "tl": "ru",
                        "dt": "t",
                        "q": joined,
                    },
                    timeout=30,
                )
                response.raise_for_status()
                fragments = response.json()[0] or []
                translated_joined = "".join(fragment[0] for fragment in fragments)
                translated_values = [
                    normalize_translation(item)
                    for item in translated_joined.split(TRANSLATION_DELIMITER)
                ]
                if len(translated_values) == len(values) and all(translated_values):
                    return {
                        source_text: translated_text
                        for source_text, translated_text in zip(values, translated_values)
                        if translated_text
                    }
            except Exception:
                time.sleep(0.5)

    for translator in translators:
        remaining = [value for value in values if value not in translated]
        if not remaining:
            break

        for _ in range(retries):
            try:
                batch_result = translator.translate_batch(remaining)
                for source_text, translated_text in zip(remaining, batch_result):
                    normalized = normalize_translation(translated_text)
                    if normalized:
                        translated[source_text] = normalized
                break
            except Exception:
                time.sleep(0.5)

        remaining = [value for value in remaining if value not in translated]
        for value in remaining:
            for _ in range(retries):
                try:
                    translated_text = normalize_translation(translator.translate(value))
                    if translated_text:
                        translated[value] = translated_text
                        break
                except Exception:
                    time.sleep(0.5)

    return translated


def translate_missing_texts(
    *,
    translators,
    values: Iterable[str | None],
    cache: dict[str, str],
    cache_path: Path,
    batch_size: int,
    sleep_seconds: float,
    retries: int,
) -> None:
    missing = unique_missing_texts(values, cache)
    for batch_index, batch in enumerate(chunked(missing, batch_size), start=1):
        translated = translate_batch_with_fallback(translators, batch, retries)
        for source_text in batch:
            cache[source_text] = translated.get(source_text, source_text)
        if batch_index % 10 == 0:
            save_cache(cache_path, cache)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    save_cache(cache_path, cache)


def extract_recipe_texts(row) -> list[str | None]:
    return [
        row["title"],
        row["description"],
        *list(row["ingredients"] or []),
        *list(row["steps"] or []),
    ]


def translate_foodcom_rows(conn, rows, args, translators, cache, cache_path: Path) -> int:
    all_texts: list[str | None] = []
    for row in rows:
        all_texts.extend(extract_recipe_texts(row))

    translate_missing_texts(
        translators=translators,
        values=all_texts,
        cache=cache,
        cache_path=cache_path,
        batch_size=args.batch_size,
        sleep_seconds=args.sleep_seconds,
        retries=args.retries,
    )

    translated_count = 0
    for row in rows:
        ingredients = list(row["ingredients"] or [])
        translated_ingredients = [
            cache.get(ingredient, ingredient)
            for ingredient in ingredients
            if normalize_translation(ingredient)
        ]
        steps = list(row["steps"] or [])
        translated_steps = [
            cache.get(step, step)
            for step in steps
            if normalize_translation(step)
        ]

        conn.execute(
            text(
                """
                UPDATE recipes
                SET
                    translated_title = :translated_title,
                    translated_description = :translated_description,
                    translated_ingredients_json = CAST(:translated_ingredients_json AS jsonb),
                    translated_steps_json = CAST(:translated_steps_json AS jsonb)
                WHERE id = :recipe_id
                """
            ),
            {
                "recipe_id": row["id"],
                "translated_title": cache.get(row["title"], row["title"]),
                "translated_description": (
                    cache.get(row["description"], row["description"])
                    if row["description"]
                    else None
                ),
                "translated_ingredients_json": json.dumps(
                    translated_ingredients,
                    ensure_ascii=False,
                ),
                "translated_steps_json": json.dumps(
                    translated_steps,
                    ensure_ascii=False,
                ),
            },
        )
        conn.commit()
        translated_count += 1
        print(f"Translated recipe {row['id']}: {row['title'][:70]}")

    return translated_count


def mark_povarenok_rows_as_russian(conn) -> int:
    rows = conn.execute(
        text(
            """
            SELECT
                r.id,
                r.title,
                r.description,
                COALESCE(r.steps_json, '[]'::jsonb) AS steps,
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
            WHERE r.source = 'povarenok'
                  AND (
                      r.translated_title IS NULL
                      OR r.translated_ingredients_json IS NULL
                      OR r.translated_steps_json IS NULL
                  )
            ORDER BY r.id
            """
        )
    ).mappings().all()

    for row in rows:
        conn.execute(
            text(
                """
                UPDATE recipes
                SET
                    translated_title = :translated_title,
                    translated_description = :translated_description,
                    translated_ingredients_json = CAST(:translated_ingredients_json AS jsonb),
                    translated_steps_json = CAST(:translated_steps_json AS jsonb)
                WHERE id = :recipe_id
                """
            ),
            {
                "recipe_id": row["id"],
                "translated_title": row["title"],
                "translated_description": row["description"],
                "translated_ingredients_json": json.dumps(
                    list(row["ingredients"] or []),
                    ensure_ascii=False,
                ),
                "translated_steps_json": json.dumps(
                    list(row["steps"] or []),
                    ensure_ascii=False,
                ),
            },
        )
    conn.commit()
    return len(rows)


def fetch_foodcom_rows(conn, args):
    params: dict[str, object] = {}
    limit_clause = ""
    if not args.all:
        limit_clause = "LIMIT :limit"
        params["limit"] = args.limit

    if args.recipe_db_ids:
        recipe_ids = [
            int(item.strip())
            for item in args.recipe_db_ids.split(",")
            if item.strip()
        ]
        params["recipe_ids"] = recipe_ids
        where_clause = "r.source = 'foodcom' AND r.id = ANY(:recipe_ids)"
    else:
        where_clause = """
            r.source = 'foodcom'
            AND (
                r.translated_title IS NULL
                OR r.translated_description IS NULL
                OR r.translated_ingredients_json IS NULL
                OR r.translated_steps_json IS NULL
            )
        """

    return conn.execute(
        text(
            f"""
            SELECT
                r.id,
                r.title,
                r.description,
                COALESCE(r.steps_json, '[]'::jsonb) AS steps,
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
            WHERE {where_clause}
            ORDER BY r.id
            {limit_clause}
            """
        ),
        params,
    ).mappings().all()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate imported recipes into Russian UI fields"
    )
    parser.add_argument("--db-url", help="SQLAlchemy PostgreSQL URL")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="How many untranslated Food.com recipes to process unless --all is used",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Translate all untranslated Food.com recipes",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="How many text fragments to translate per external translator batch",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help="Pause between translated batches to reduce rate-limit pressure",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="How many times to retry a failed external translation request",
    )
    parser.add_argument(
        "--recipe-db-ids",
        help="Comma-separated Food.com recipe ids from the local DB to translate first",
    )
    parser.add_argument(
        "--skip-povarenok",
        action="store_true",
        help="Do not mark already-Russian Povarenok recipes as translated",
    )
    parser.add_argument(
        "--cache",
        default=str(DEFAULT_CACHE_PATH),
        help="Path to JSON translation cache",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = create_engine(resolve_db_url(args.db_url))
    cache_path = Path(args.cache)
    cache = load_cache(cache_path)
    translators = [
        GoogleTranslator(source="en", target="ru"),
        MyMemoryTranslator(source="en-US", target="ru-RU"),
    ]

    with engine.connect() as conn:
        povarenok_count = 0 if args.skip_povarenok else mark_povarenok_rows_as_russian(conn)
        rows = fetch_foodcom_rows(conn, args)
        foodcom_count = translate_foodcom_rows(
            conn,
            rows,
            args,
            translators,
            cache,
            cache_path,
        )

    print(
        f"Marked {povarenok_count} Povarenok recipes as Russian. "
        f"Translated {foodcom_count} Food.com recipes."
    )


if __name__ == "__main__":
    main()
