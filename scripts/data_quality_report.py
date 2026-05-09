from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "artifacts/training/tasteplanner_training_dataset.csv"
DEFAULT_JSON = PROJECT_ROOT / "artifacts/training/tasteplanner_data_quality_report.json"
DEFAULT_MD = PROJECT_ROOT / "artifacts/training/tasteplanner_data_quality_report.md"


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


def db_stats(db_url: str) -> dict:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        recipe = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) AS recipe_features_count,
                    COUNT(*) FILTER (WHERE price_coverage > 0) AS recipes_with_any_price,
                    ROUND(AVG(price_coverage), 4) AS avg_price_coverage,
                    COUNT(*) FILTER (WHERE time_tier <> 'unknown') AS recipes_with_time,
                    COUNT(*) FILTER (WHERE calorie_tier <> 'unknown') AS recipes_with_calories,
                    COUNT(*) FILTER (WHERE protein_tier <> 'unknown') AS recipes_with_protein
                FROM recipe_features
                """
            )
        ).mappings().first()
        feedback = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) AS feedback_count,
                    COUNT(*) FILTER (WHERE liked IS TRUE) AS liked_count,
                    COUNT(*) FILTER (WHERE liked IS FALSE) AS disliked_count,
                    COUNT(*) FILTER (WHERE reason IS NOT NULL AND reason <> '') AS reasoned_count
                FROM user_recipe_feedback
                """
            )
        ).mappings().first()
        bootstrap = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) AS bootstrap_users,
                    (
                        SELECT COUNT(*)
                        FROM user_recipe_feedback urf
                        JOIN users u ON u.id = urf.user_id
                        WHERE u.email LIKE 'bootstrap.%@tasteplanner.local'
                    ) AS bootstrap_feedback
                FROM users
                WHERE email LIKE 'bootstrap.%@tasteplanner.local'
                """
            )
        ).mappings().first()
        aliases = conn.execute(text("SELECT COUNT(*) FROM ingredient_aliases")).scalar()

    return {
        "recipe_features": dict(recipe),
        "feedback": dict(feedback),
        "bootstrap": dict(bootstrap),
        "ingredient_aliases_count": int(aliases or 0),
    }


def dataset_stats(dataset_path: Path) -> dict:
    if not dataset_path.exists():
        return {"exists": False}

    df = pd.read_csv(dataset_path)
    missing = {
        column: round(float(df[column].isna().mean()), 4)
        for column in df.columns
        if df[column].isna().any()
    }
    liked = df["target_liked"].astype(str).str.lower().isin(["true", "1", "yes"])
    return {
        "exists": True,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "positive_rows": int(liked.sum()),
        "negative_rows": int((~liked).sum()),
        "bootstrap_rows": int(df.get("is_bootstrap_user", False).astype(bool).sum()),
        "missing_rate": missing,
    }


def split_stats(dataset_path: Path) -> dict:
    base_dir = dataset_path.parent
    result = {}
    for name in ("train", "validation", "test"):
        path = base_dir / f"tasteplanner_{name}.csv"
        if path.exists():
            df = pd.read_csv(path)
            liked = df["target_liked"].astype(str).str.lower().isin(["true", "1", "yes"])
            result[name] = {
                "rows": int(len(df)),
                "positive_rows": int(liked.sum()),
                "negative_rows": int((~liked).sum()),
            }
    return result


def readiness_score(report: dict) -> int:
    score = 0
    recipe = report["database"]["recipe_features"]
    feedback = report["database"]["feedback"]
    dataset = report["dataset"]

    if recipe["recipe_features_count"] >= 3000:
        score += 20
    if float(recipe["avg_price_coverage"] or 0) >= 0.2:
        score += 15
    if recipe["recipes_with_calories"] >= 2500:
        score += 15
    if feedback["feedback_count"] >= 250:
        score += 20
    elif feedback["feedback_count"] >= 100:
        score += 12
    if feedback["disliked_count"] > 0 and feedback["liked_count"] > 0:
        score += 10
    if dataset.get("exists") and dataset.get("rows", 0) >= 100:
        score += 10
    if report["splits"]:
        score += 10
    return min(score, 100)


def write_markdown(report: dict, output_path: Path) -> None:
    recipe = report["database"]["recipe_features"]
    feedback = report["database"]["feedback"]
    dataset = report["dataset"]
    lines = [
        "# TastePlanner Data Quality Report",
        "",
        f"- Readiness score: {report['readiness_score']} / 100",
        f"- Recipe features: {recipe['recipe_features_count']}",
        f"- Average price coverage: {recipe['avg_price_coverage']}",
        f"- Feedback rows: {feedback['feedback_count']}",
        f"- Likes / dislikes: {feedback['liked_count']} / {feedback['disliked_count']}",
        f"- Ingredient aliases: {report['database']['ingredient_aliases_count']}",
        f"- Training rows: {dataset.get('rows', 0)}",
        f"- Bootstrap rows: {dataset.get('bootstrap_rows', 0)}",
        "",
        "## Splits",
    ]
    for name, stats in report["splits"].items():
        lines.append(
            f"- {name}: {stats['rows']} rows "
            f"({stats['positive_rows']} positive, {stats['negative_rows']} negative)"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_report(db_url: str, dataset_path: Path, json_path: Path, md_path: Path) -> dict:
    report = {
        "database": db_stats(db_url),
        "dataset": dataset_stats(dataset_path),
        "splits": split_stats(dataset_path),
    }
    report["readiness_score"] = readiness_score(report)

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    write_markdown(report, md_path)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a data quality report before model training."
    )
    parser.add_argument("--db-url", default=None)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        resolve_db_url(args.db_url),
        args.dataset,
        args.json_output,
        args.md_output,
    )
    print(f"Data readiness score: {report['readiness_score']} / 100")


if __name__ == "__main__":
    main()
