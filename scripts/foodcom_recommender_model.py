from __future__ import annotations

from typing import Iterable

import joblib
import numpy as np
from pathlib import Path


class FoodComRecommender:
    def __init__(
        self,
        global_mean: float,
        user_biases: np.ndarray,
        item_biases: np.ndarray,
        user_factors: np.ndarray,
        item_factors: np.ndarray,
        item_popularity: np.ndarray,
        recipe_ids_by_item_index: np.ndarray,
        recipe_titles_by_item_index: np.ndarray,
    ) -> None:
        self.global_mean = float(global_mean)
        self.user_biases = user_biases
        self.item_biases = item_biases
        self.user_factors = user_factors
        self.item_factors = item_factors
        self.item_popularity = item_popularity
        self.recipe_ids_by_item_index = recipe_ids_by_item_index
        self.recipe_titles_by_item_index = recipe_titles_by_item_index

    def score(self, user_indices: np.ndarray, item_indices: np.ndarray) -> np.ndarray:
        baseline = (
            self.global_mean
            + self.user_biases[user_indices]
            + self.item_biases[item_indices]
        )
        collaborative = np.sum(
            self.user_factors[user_indices] * self.item_factors[item_indices],
            axis=1,
        )
        return np.clip(baseline + collaborative, 1.0, 5.0)

    def recommend_for_user(
        self,
        user_index: int,
        seen_item_indices: Iterable[int],
        top_k: int = 10,
    ) -> list[dict[str, object]]:
        if user_index < 0 or user_index >= self.user_factors.shape[0]:
            return self._popular_fallback(top_k=top_k, exclude=seen_item_indices)

        seen_set = set(seen_item_indices)
        baseline = self.global_mean + self.user_biases[user_index] + self.item_biases
        collaborative = self.item_factors @ self.user_factors[user_index]
        scores = np.clip(baseline + collaborative, 1.0, 5.0)

        if seen_set:
            seen_indices = np.fromiter(seen_set, dtype=np.int64)
            valid_seen = seen_indices[
                (seen_indices >= 0) & (seen_indices < scores.shape[0])
            ]
            scores[valid_seen] = -np.inf

        top_k = min(top_k, scores.shape[0])
        top_indices = np.argpartition(scores, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        recommendations: list[dict[str, object]] = []
        for item_index in top_indices:
            score = scores[item_index]
            if not np.isfinite(score):
                continue
            recommendations.append(
                {
                    "item_index": int(item_index),
                    "recipe_id": int(self.recipe_ids_by_item_index[item_index]),
                    "title": str(self.recipe_titles_by_item_index[item_index]),
                    "score": float(score),
                }
            )
        return recommendations

    def _popular_fallback(
        self,
        top_k: int,
        exclude: Iterable[int],
    ) -> list[dict[str, object]]:
        excluded = set(exclude)
        ranked = np.argsort(self.item_popularity)[::-1]
        recommendations: list[dict[str, object]] = []
        for item_index in ranked:
            if item_index in excluded:
                continue
            recommendations.append(
                {
                    "item_index": int(item_index),
                    "recipe_id": int(self.recipe_ids_by_item_index[item_index]),
                    "title": str(self.recipe_titles_by_item_index[item_index]),
                    "score": float(self.item_popularity[item_index]),
                }
            )
            if len(recommendations) >= top_k:
                break
        return recommendations

    def to_artifact(self) -> dict[str, object]:
        return {
            "global_mean": self.global_mean,
            "user_biases": self.user_biases,
            "item_biases": self.item_biases,
            "user_factors": self.user_factors,
            "item_factors": self.item_factors,
            "item_popularity": self.item_popularity,
            "recipe_ids_by_item_index": self.recipe_ids_by_item_index,
            "recipe_titles_by_item_index": self.recipe_titles_by_item_index,
        }

    @classmethod
    def from_artifact(cls, payload: dict[str, object]) -> "FoodComRecommender":
        return cls(
            global_mean=float(payload["global_mean"]),
            user_biases=payload["user_biases"],
            item_biases=payload["item_biases"],
            user_factors=payload["user_factors"],
            item_factors=payload["item_factors"],
            item_popularity=payload["item_popularity"],
            recipe_ids_by_item_index=payload["recipe_ids_by_item_index"],
            recipe_titles_by_item_index=payload["recipe_titles_by_item_index"],
        )


def save_model(model: FoodComRecommender, path: str | Path) -> None:
    joblib.dump(model.to_artifact(), path)


def load_model(path: str | Path) -> FoodComRecommender:
    payload = joblib.load(path)
    return FoodComRecommender.from_artifact(payload)
