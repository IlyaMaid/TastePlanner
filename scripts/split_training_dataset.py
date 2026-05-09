from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "artifacts/training/tasteplanner_training_dataset.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts/training"


def stable_bucket(user_id: str, recipe_id: str) -> float:
    digest = hashlib.sha256(f"{user_id}:{recipe_id}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def split_dataset(input_path: Path, output_dir: Path) -> dict[str, int]:
    df = pd.read_csv(input_path)
    if df.empty:
        raise SystemExit(f"Training dataset is empty: {input_path}")

    buckets = df.apply(
        lambda row: stable_bucket(str(row["user_id"]), str(row["recipe_id"])),
        axis=1,
    )

    train = df[buckets < 0.8].copy()
    validation = df[(buckets >= 0.8) & (buckets < 0.9)].copy()
    test = df[buckets >= 0.9].copy()

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "train": output_dir / "tasteplanner_train.csv",
        "validation": output_dir / "tasteplanner_validation.csv",
        "test": output_dir / "tasteplanner_test.csv",
    }
    train.to_csv(paths["train"], index=False, encoding="utf-8")
    validation.to_csv(paths["validation"], index=False, encoding="utf-8")
    test.to_csv(paths["test"], index=False, encoding="utf-8")

    summary = {
        "input": str(input_path),
        "rows": int(len(df)),
        "train_rows": int(len(train)),
        "validation_rows": int(len(validation)),
        "test_rows": int(len(test)),
        "outputs": {name: str(path) for name, path in paths.items()},
    }
    (output_dir / "tasteplanner_split.metadata.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create deterministic train/validation/test splits for TastePlanner training."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = split_dataset(args.input, args.output_dir)
    print(
        "Split "
        f"{summary['rows']} rows: "
        f"train={summary['train_rows']}, "
        f"validation={summary['validation_rows']}, "
        f"test={summary['test_rows']}"
    )


if __name__ == "__main__":
    main()
