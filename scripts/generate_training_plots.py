from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import matplotlib
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    PrecisionRecallDisplay,
    RocCurveDisplay,
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

from train_content_based_ranker import add_match_features, target_series


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRAINING_DIR = PROJECT_ROOT / "artifacts" / "training"
RECOMMENDER_DIR = PROJECT_ROOT / "artifacts" / "recommender"
DEFAULT_OUTPUT_DIR = RECOMMENDER_DIR / "training_plots"
DEFAULT_MODEL_PATH = RECOMMENDER_DIR / "tasteplanner_content_ranker.joblib"
DEFAULT_REPORT_PATH = RECOMMENDER_DIR / "tasteplanner_content_ranker_report.json"

SPLIT_PATHS = {
    "train": TRAINING_DIR / "tasteplanner_train.csv",
    "validation": TRAINING_DIR / "tasteplanner_validation.csv",
    "test": TRAINING_DIR / "tasteplanner_test.csv",
}


def save_current_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def load_splits() -> dict[str, pd.DataFrame]:
    splits: dict[str, pd.DataFrame] = {}
    for split, path in SPLIT_PATHS.items():
        if not path.exists():
            raise FileNotFoundError(f"Training split not found: {path}")
        splits[split] = add_match_features(pd.read_csv(path))
    return splits


def predict_scores(model: Any, df: pd.DataFrame) -> np.ndarray:
    return model.predict_proba(df)[:, 1]


def plot_roc_curves(model: Any, splits: dict[str, pd.DataFrame], output_dir: Path) -> None:
    plt.figure(figsize=(8, 6))
    plt.plot([0, 1], [0, 1], linestyle="--", color="#94a3b8", label="Случайная модель")

    for split, df in splits.items():
        y_true = target_series(df)
        y_score = predict_scores(model, df)
        fpr, tpr, _ = roc_curve(y_true, y_score)
        auc = roc_auc_score(y_true, y_score)
        RocCurveDisplay(fpr=fpr, tpr=tpr, roc_auc=auc, name=split).plot(
            ax=plt.gca()
        )

    plt.title("ROC-кривая модели рекомендаций")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.grid(alpha=0.2)
    save_current_figure(output_dir / "roc_curve.png")


def plot_precision_recall_curves(
    model: Any,
    splits: dict[str, pd.DataFrame],
    output_dir: Path,
) -> None:
    plt.figure(figsize=(8, 6))

    for split, df in splits.items():
        y_true = target_series(df)
        y_score = predict_scores(model, df)
        precision, recall, _ = precision_recall_curve(y_true, y_score)
        ap = average_precision_score(y_true, y_score)
        PrecisionRecallDisplay(
            precision=precision,
            recall=recall,
            average_precision=ap,
            name=split,
        ).plot(ax=plt.gca())

    plt.title("Precision-Recall кривая")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.grid(alpha=0.2)
    save_current_figure(output_dir / "precision_recall_curve.png")


def plot_confusion_matrix(model: Any, splits: dict[str, pd.DataFrame], output_dir: Path) -> None:
    validation = splits["validation"]
    y_true = target_series(validation)
    y_pred = (predict_scores(model, validation) >= 0.5).astype(int)
    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])

    _, ax = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay(
        confusion_matrix=matrix,
        display_labels=["Не подходит", "Подходит"],
    ).plot(ax=ax, cmap="Greens", colorbar=False, values_format="d")
    ax.set_title("Confusion matrix на validation")
    save_current_figure(output_dir / "confusion_matrix_validation.png")


def plot_split_metrics(report: dict[str, Any], output_dir: Path) -> None:
    rows = []
    for split, metrics in report.get("splits", {}).items():
        rows.append(
            {
                "split": split,
                "Accuracy": metrics.get("accuracy"),
                "ROC AUC": metrics.get("roc_auc"),
                "Average Precision": metrics.get("average_precision"),
            }
        )
    metrics_df = pd.DataFrame(rows).set_index("split")

    ax = metrics_df.plot(kind="bar", figsize=(9, 5), color=["#64748b", "#10b981", "#f59e0b"])
    ax.set_title("Метрики модели по выборкам")
    ax.set_xlabel("Выборка")
    ax.set_ylabel("Значение")
    ax.set_ylim(0, 1.05)
    ax.grid(axis="y", alpha=0.2)
    ax.legend(loc="lower right")
    save_current_figure(output_dir / "split_metrics.png")


def plot_target_distribution(splits: dict[str, pd.DataFrame], output_dir: Path) -> None:
    rows = []
    for split, df in splits.items():
        target = target_series(df)
        rows.append(
            {
                "split": split,
                "Понравилось": int(target.sum()),
                "Не понравилось": int(len(target) - target.sum()),
            }
        )
    target_df = pd.DataFrame(rows).set_index("split")

    ax = target_df.plot(kind="bar", stacked=True, figsize=(8, 5), color=["#10b981", "#f43f5e"])
    ax.set_title("Распределение целевой переменной")
    ax.set_xlabel("Выборка")
    ax.set_ylabel("Количество строк")
    ax.grid(axis="y", alpha=0.2)
    save_current_figure(output_dir / "target_distribution.png")


def plot_score_distribution(model: Any, splits: dict[str, pd.DataFrame], output_dir: Path) -> None:
    validation = splits["validation"].copy()
    validation["score"] = predict_scores(model, validation)
    validation["target"] = target_series(validation)

    plt.figure(figsize=(8, 5))
    for target_value, label, color in [
        (0, "Не понравилось", "#f43f5e"),
        (1, "Понравилось", "#10b981"),
    ]:
        values = validation.loc[validation["target"] == target_value, "score"]
        plt.hist(values, bins=10, alpha=0.65, label=label, color=color)

    plt.title("Распределение predicted_score на validation")
    plt.xlabel("Predicted score")
    plt.ylabel("Количество")
    plt.legend()
    plt.grid(axis="y", alpha=0.2)
    save_current_figure(output_dir / "score_distribution_validation.png")


def plot_feature_importance(model: Any, splits: dict[str, pd.DataFrame], output_dir: Path) -> None:
    validation = splits["validation"]
    y_true = target_series(validation)
    result = permutation_importance(
        model,
        validation,
        y_true,
        n_repeats=8,
        random_state=42,
        scoring="average_precision",
    )
    importances = (
        pd.DataFrame(
            {
                "feature": validation.columns,
                "importance": result.importances_mean,
            }
        )
        .sort_values("importance", ascending=False)
        .head(15)
    )

    plt.figure(figsize=(9, 6))
    plt.barh(importances["feature"][::-1], importances["importance"][::-1], color="#10b981")
    plt.title("Permutation importance, top-15")
    plt.xlabel("Влияние на Average Precision")
    plt.grid(axis="x", alpha=0.2)
    save_current_figure(output_dir / "feature_importance.png")


def write_summary(output_dir: Path, report: dict[str, Any]) -> None:
    summary = {
        "title": "Графики обучения модели TastePlanner",
        "model_type": report.get("model_type"),
        "plots": [
            "roc_curve.png",
            "precision_recall_curve.png",
            "confusion_matrix_validation.png",
            "split_metrics.png",
            "target_distribution.png",
            "score_distribution_validation.png",
            "feature_importance.png",
        ],
        "notes": [
            "ROC и Precision-Recall показывают качество ранжирования подходящих блюд.",
            "Confusion matrix показывает ошибки при пороге 0.5 на validation.",
            "Permutation importance показывает признаки, которые сильнее всего влияют на Average Precision.",
        ],
    }
    (output_dir / "plots_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate matplotlib plots for TastePlanner model training report."
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    artifact = joblib.load(args.model)
    model = artifact["model"]
    report = json.loads(args.report.read_text(encoding="utf-8"))
    splits = load_splits()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    plot_roc_curves(model, splits, args.output_dir)
    plot_precision_recall_curves(model, splits, args.output_dir)
    plot_confusion_matrix(model, splits, args.output_dir)
    plot_split_metrics(report, args.output_dir)
    plot_target_distribution(splits, args.output_dir)
    plot_score_distribution(model, splits, args.output_dir)
    plot_feature_importance(model, splits, args.output_dir)
    write_summary(args.output_dir, report)

    print(f"Training plots generated: {args.output_dir}")


if __name__ == "__main__":
    main()
