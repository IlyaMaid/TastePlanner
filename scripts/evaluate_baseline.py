from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "artifacts/training/tasteplanner_training_dataset.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts/training/tasteplanner_baseline_evaluation.json"


def normalize_series(series: pd.Series, default: float = 0.0) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() == 0:
        return pd.Series(default, index=series.index)
    min_value = numeric.min()
    max_value = numeric.max()
    if min_value == max_value:
        return pd.Series(default, index=series.index)
    return (numeric - min_value) / (max_value - min_value)


def baseline_score(df: pd.DataFrame) -> pd.Series:
    score = pd.Series(0.0, index=df.index)

    score += normalize_series(df.get("source_rating", pd.Series(index=df.index)), 0.5) * 0.15
    score += (pd.to_numeric(df.get("price_coverage", 0), errors="coerce").fillna(0) * 0.1)
    score += (df.get("time_tier", "") == "very_fast").astype(float) * 0.08
    score += (df.get("time_tier", "") == "fast").astype(float) * 0.05
    score += (df.get("protein_tier", "") == "high").astype(float) * 0.1
    score += (df.get("calorie_tier", "") == "balanced").astype(float) * 0.08
    score += (df.get("calorie_tier", "") == "light").astype(float) * 0.04

    cost_ratio = pd.to_numeric(df.get("cost_to_budget_ratio", 1), errors="coerce")
    score -= cost_ratio.fillna(1).clip(lower=1).sub(1).clip(upper=2) * 0.18
    score += (cost_ratio.fillna(99) <= 1).astype(float) * 0.1

    calorie_ratio = pd.to_numeric(df.get("calorie_to_target_ratio", 1), errors="coerce")
    score -= (calorie_ratio.fillna(1) - 1).abs().clip(upper=2) * 0.08

    return score


def roc_auc(labels: pd.Series, scores: pd.Series) -> float | None:
    pairs = pd.DataFrame({"label": labels.astype(bool), "score": scores}).dropna()
    positives = pairs[pairs["label"]]
    negatives = pairs[~pairs["label"]]
    if positives.empty or negatives.empty:
        return None

    wins = 0.0
    total = 0
    negative_scores = negatives["score"].tolist()
    for positive_score in positives["score"].tolist():
        for negative_score in negative_scores:
            if positive_score > negative_score:
                wins += 1
            elif positive_score == negative_score:
                wins += 0.5
            total += 1
    return round(wins / total, 4) if total else None


def evaluate_frame(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"rows": 0}

    scores = baseline_score(df)
    labels = df["target_liked"].astype(str).str.lower().isin(["true", "1", "yes"])
    threshold = scores.median()
    predicted = scores >= threshold
    accuracy = (predicted == labels).mean()

    return {
        "rows": int(len(df)),
        "positive_rows": int(labels.sum()),
        "negative_rows": int((~labels).sum()),
        "baseline_accuracy_at_median": round(float(accuracy), 4),
        "baseline_auc": roc_auc(labels, scores),
        "avg_positive_score": round(float(scores[labels].mean()), 4) if labels.any() else None,
        "avg_negative_score": round(float(scores[~labels].mean()), 4) if (~labels).any() else None,
    }


def evaluate(input_path: Path, output_path: Path) -> dict:
    base_dir = input_path.parent
    datasets = {"all": input_path}
    for name in ("train", "validation", "test"):
        path = base_dir / f"tasteplanner_{name}.csv"
        if path.exists():
            datasets[name] = path

    report = {}
    for name, path in datasets.items():
        report[name] = evaluate_frame(pd.read_csv(path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a rule-based baseline before ML training."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = evaluate(args.input, args.output)
    validation = report.get("validation") or report.get("all")
    print(
        "Baseline evaluated: "
        f"rows={report['all']['rows']}, "
        f"validation_auc={validation.get('baseline_auc')}"
    )


if __name__ == "__main__":
    main()
