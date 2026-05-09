from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SUMMARY_PATH = PROJECT_ROOT / "artifacts" / "recommender" / "retrain_summary.json"


def run_step(name: str, args: list[str]) -> dict[str, Any]:
    command = [sys.executable, *args]
    print(f"\n[{name}] {' '.join(command)}")
    started_at = datetime.now(timezone.utc)
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    finished_at = datetime.now(timezone.utc)

    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)

    step = {
        "name": name,
        "command": command,
        "returncode": result.returncode,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }

    if result.returncode != 0:
        raise RuntimeError(f"Step failed: {name}")

    return step


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full TastePlanner recommender retraining pipeline."
    )
    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="Do not refresh the curated Russian recipe dataset in the database.",
    )
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Do not regenerate deterministic bootstrap feedback.",
    )
    parser.add_argument(
        "--model",
        choices=["auto", "catboost", "xgboost", "sklearn"],
        default="auto",
        help="Prediction model used by train_content_based_ranker.py.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    steps: list[dict[str, Any]] = []
    started_at = datetime.now(timezone.utc)

    try:
        if not args.skip_import:
            steps.append(
                run_step(
                    "import_curated_ru_recipes",
                    [str(SCRIPTS_DIR / "import_curated_ru_recipes.py")],
                )
            )

        steps.append(
            run_step(
                "build_recipe_features",
                [str(SCRIPTS_DIR / "build_recipe_features.py")],
            )
        )

        if not args.skip_bootstrap:
            steps.append(
                run_step(
                    "seed_training_bootstrap",
                    [str(SCRIPTS_DIR / "seed_training_bootstrap.py")],
                )
            )

        steps.extend(
            [
                run_step(
                    "export_training_dataset",
                    [str(SCRIPTS_DIR / "export_training_dataset.py")],
                ),
                run_step(
                    "split_training_dataset",
                    [str(SCRIPTS_DIR / "split_training_dataset.py")],
                ),
                run_step(
                    "train_content_based_ranker",
                    [
                        str(SCRIPTS_DIR / "train_content_based_ranker.py"),
                        "--model",
                        args.model,
                    ],
                ),
                run_step(
                    "evaluate_baseline",
                    [str(SCRIPTS_DIR / "evaluate_baseline.py")],
                ),
                run_step(
                    "generate_training_plots",
                    [str(SCRIPTS_DIR / "generate_training_plots.py")],
                ),
                run_step(
                    "data_quality_report",
                    [str(SCRIPTS_DIR / "data_quality_report.py")],
                ),
            ]
        )

        summary = {
            "status": "success",
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "model": args.model,
            "steps": steps,
        }
        SUMMARY_PATH.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nRetraining pipeline completed. Summary: {SUMMARY_PATH}")
    except Exception as exc:
        summary = {
            "status": "failed",
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "model": args.model,
            "error": str(exc),
            "steps": steps,
        }
        SUMMARY_PATH.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nRetraining pipeline failed. Summary: {SUMMARY_PATH}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
