from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

import joblib
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session


ARTIFACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "artifacts"
    / "recommender"
    / "foodcom_svd_recommender.joblib"
)


@dataclass
class FoodComArtifact:
    global_mean: float
    user_biases: np.ndarray
    item_biases: np.ndarray
    user_factors: np.ndarray
    item_factors: np.ndarray
    item_popularity: np.ndarray
    recipe_ids_by_item_index: np.ndarray
    recipe_titles_by_item_index: np.ndarray

    @classmethod
    def load(cls, path: Path) -> "FoodComArtifact":
        payload = joblib.load(path)
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

    @property
    def recipe_id_to_item_index(self) -> dict[int, int]:
        return {
            int(recipe_id): index
            for index, recipe_id in enumerate(self.recipe_ids_by_item_index.tolist())
            if int(recipe_id) >= 0
        }


@lru_cache(maxsize=1)
def get_foodcom_artifact() -> FoodComArtifact:
    if not ARTIFACT_PATH.exists():
        raise FileNotFoundError(f"Recommender artifact not found: {ARTIFACT_PATH}")
    return FoodComArtifact.load(ARTIFACT_PATH)


def _score_for_pseudo_user(
    artifact: FoodComArtifact,
    item_indices: list[int],
    weights: Optional[list[float]] = None,
) -> np.ndarray:
    if not item_indices:
        return np.clip(artifact.global_mean + artifact.item_biases, 1.0, 5.0)

    valid_indices = np.array(
        [idx for idx in item_indices if 0 <= idx < artifact.item_factors.shape[0]],
        dtype=np.int64,
    )
    if valid_indices.size == 0:
        return np.clip(artifact.global_mean + artifact.item_biases, 1.0, 5.0)

    if weights:
        weight_array = np.array(weights[: len(valid_indices)], dtype=np.float32)
        if weight_array.shape[0] != valid_indices.shape[0]:
            weight_array = np.ones(valid_indices.shape[0], dtype=np.float32)
    else:
        weight_array = np.ones(valid_indices.shape[0], dtype=np.float32)

    weighted_factors = artifact.item_factors[valid_indices] * weight_array[:, None]
    pseudo_user_vector = weighted_factors.sum(axis=0) / max(weight_array.sum(), 1.0)
    scores = artifact.global_mean + artifact.item_biases + (
        artifact.item_factors @ pseudo_user_vector
    )
    return np.clip(scores, 1.0, 5.0)


def get_feedback_item_indices(
    db: Session,
    user_id,
    artifact: FoodComArtifact,
) -> tuple[list[int], list[float]]:
    rows = db.execute(
        text(
            """
            SELECT
                r.source_recipe_id,
                COALESCE(urf.rating, CASE WHEN urf.liked IS TRUE THEN 5 ELSE NULL END) AS weight
            FROM user_recipe_feedback urf
            JOIN recipes r ON r.id = urf.recipe_id
            WHERE urf.user_id = :user_id
              AND r.source = 'foodcom'
              AND (
                  urf.rating IS NOT NULL
                  OR urf.liked IS TRUE
              )
            """
        ),
        {"user_id": user_id},
    ).fetchall()

    item_indices: list[int] = []
    weights: list[float] = []
    for source_recipe_id, weight in rows:
        try:
            recipe_id = int(source_recipe_id)
        except (TypeError, ValueError):
            continue
        item_index = artifact.recipe_id_to_item_index.get(recipe_id)
        if item_index is None:
            continue
        item_indices.append(item_index)
        weights.append(float(weight or 5.0))
    return item_indices, weights


def _fetch_available_foodcom_rows(
    db: Session,
    source_recipe_ids: Iterable[int],
) -> dict[int, dict]:
    recipe_ids = [str(recipe_id) for recipe_id in source_recipe_ids]
    if not recipe_ids:
        return {}

    rows = db.execute(
        text(
            """
            SELECT
                r.id,
                r.source_recipe_id,
                COALESCE(r.translated_title, r.title) AS title,
                COALESCE(r.translated_description, r.description) AS description,
                r.total_minutes,
                r.calories,
                r.protein,
                r.fat,
                r.carbs,
                COALESCE(
                    r.translated_ingredients_json,
                    CAST((
                        SELECT json_agg(ingredient_row.raw_text ORDER BY ingredient_row.id)
                        FROM (
                            SELECT ri.id, ri.raw_text
                            FROM recipe_ingredients ri
                            WHERE ri.recipe_id = r.id
                            ORDER BY ri.id
                            LIMIT 8
                        ) AS ingredient_row
                    ) AS jsonb),
                    '[]'::jsonb
                ) AS ingredients
            FROM recipes r
            WHERE r.source = 'foodcom'
              AND r.source_recipe_id = ANY(:source_recipe_ids)
            """
        ),
        {"source_recipe_ids": recipe_ids},
    ).mappings()

    return {
        int(row["source_recipe_id"]): {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "total_minutes": row["total_minutes"],
            "calories": float(row["calories"]) if row["calories"] is not None else None,
            "protein": float(row["protein"]) if row["protein"] is not None else None,
            "fat": float(row["fat"]) if row["fat"] is not None else None,
            "carbs": float(row["carbs"]) if row["carbs"] is not None else None,
            "ingredients": list(row["ingredients"] or []),
        }
        for row in rows
    }


def get_recommendations(
    db: Session,
    user_id,
    limit: int,
    demo_user_index: Optional[int] = None,
) -> dict:
    artifact = get_foodcom_artifact()

    if demo_user_index is not None:
        scores = artifact.global_mean + artifact.item_biases + (
            artifact.item_factors @ artifact.user_factors[demo_user_index]
        )
        strategy = "model_demo_user"
        seen_item_indices: list[int] = []
    else:
        seen_item_indices, weights = get_feedback_item_indices(db, user_id, artifact)
        scores = _score_for_pseudo_user(artifact, seen_item_indices, weights)
        strategy = "personalized_feedback" if seen_item_indices else "cold_start_popularity"

    if seen_item_indices:
        valid_seen = np.array(seen_item_indices, dtype=np.int64)
        valid_seen = valid_seen[
            (valid_seen >= 0) & (valid_seen < artifact.item_factors.shape[0])
        ]
        scores[valid_seen] = -np.inf

    top_pool = min(max(limit * 30, 200), scores.shape[0])
    candidate_indices = np.argpartition(scores, -top_pool)[-top_pool:]
    candidate_indices = candidate_indices[np.argsort(scores[candidate_indices])[::-1]]

    source_recipe_ids = [
        int(artifact.recipe_ids_by_item_index[item_index])
        for item_index in candidate_indices
        if int(artifact.recipe_ids_by_item_index[item_index]) >= 0
    ]
    available_rows = _fetch_available_foodcom_rows(db, source_recipe_ids)

    items = []
    for item_index in candidate_indices:
        source_recipe_id = int(artifact.recipe_ids_by_item_index[item_index])
        recipe = available_rows.get(source_recipe_id)
        if recipe is None:
            continue
        items.append(
            {
                **recipe,
                "source": "foodcom",
                "source_recipe_id": str(source_recipe_id),
                "predicted_rating": float(np.clip(scores[item_index], 1.0, 5.0)),
                "model_item_index": int(item_index),
            }
        )
        if len(items) >= limit:
            break

    return {
        "strategy": strategy,
        "items": items,
        "count": len(items),
    }


def _estimate_daily_calorie_target(profile_row) -> Optional[float]:
    if profile_row is None:
        return None

    if profile_row.daily_calorie_target is not None:
        return float(profile_row.daily_calorie_target)

    if not all(
        [
            profile_row.sex,
            profile_row.age is not None,
            profile_row.height_cm is not None,
            profile_row.weight_kg is not None,
        ]
    ):
        return None

    weight = float(profile_row.weight_kg)
    height = float(profile_row.height_cm)
    age = int(profile_row.age)

    if profile_row.sex == "male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    activity_multiplier = {
        "low": 1.2,
        "moderate": 1.55,
        "high": 1.725,
    }.get(profile_row.activity_level or "", 1.2)

    calories = bmr * activity_multiplier
    if profile_row.goal == "lose_weight":
        calories -= 300
    elif profile_row.goal == "gain_weight":
        calories += 300

    return round(max(calories, 1200), 0)


def _get_meal_labels(meals_per_day: int) -> list[str]:
    predefined = {
        2: ["Завтрак", "Ужин"],
        3: ["Завтрак", "Обед", "Ужин"],
        4: ["Завтрак", "Обед", "Ужин", "Перекус"],
        5: ["Завтрак", "Перекус", "Обед", "Полдник", "Ужин"],
        6: ["Завтрак", "Перекус", "Обед", "Полдник", "Ужин", "Перекус 2"],
    }
    return predefined.get(
        meals_per_day,
        [f"Прием пищи {index}" for index in range(1, meals_per_day + 1)],
    )


def _get_meal_shares(meals_per_day: int) -> list[float]:
    predefined = {
        2: [0.45, 0.55],
        3: [0.3, 0.4, 0.3],
        4: [0.25, 0.35, 0.25, 0.15],
        5: [0.22, 0.13, 0.3, 0.13, 0.22],
        6: [0.2, 0.1, 0.25, 0.1, 0.25, 0.1],
    }
    if meals_per_day in predefined:
        return predefined[meals_per_day]
    return [round(1 / meals_per_day, 4)] * meals_per_day


def generate_meal_plan(
    db: Session,
    user_id,
    limit: int = 4,
) -> dict:
    profile = db.execute(
        text(
            """
            SELECT
                sex,
                age,
                height_cm,
                weight_kg,
                activity_level,
                goal,
                daily_calorie_target,
                meals_per_day
            FROM user_profiles
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).fetchone()

    meals_per_day = int(profile.meals_per_day) if profile and profile.meals_per_day else limit
    meals_per_day = max(1, min(meals_per_day, 6))

    recommendation_payload = get_recommendations(
        db=db,
        user_id=user_id,
        limit=max(meals_per_day * 6, 24),
    )
    candidates = recommendation_payload["items"]
    daily_target = _estimate_daily_calorie_target(profile)

    meal_labels = _get_meal_labels(meals_per_day)
    meal_shares = _get_meal_shares(meals_per_day)
    meals = []
    used_recipe_ids: set[int] = set()

    for index, meal_label in enumerate(meal_labels):
        target_calories = (
            round(daily_target * meal_shares[index], 0) if daily_target is not None else None
        )

        best_recipe = None
        best_score = None
        for candidate in candidates:
            if candidate["id"] in used_recipe_ids:
                continue

            candidate_calories = candidate.get("calories")
            if target_calories is not None and candidate_calories is not None:
                score = abs(candidate_calories - target_calories)
            else:
                score = -candidate.get("predicted_rating", 0)

            if best_score is None or score < best_score:
                best_recipe = candidate
                best_score = score

        if best_recipe is None:
            break

        used_recipe_ids.add(best_recipe["id"])
        meals.append(
            {
                "slot": meal_label,
                "target_calories": target_calories,
                "recipe": best_recipe,
            }
        )

    totals = {
        "calories": round(
            sum(meal["recipe"].get("calories") or 0 for meal in meals),
            1,
        ),
        "protein": round(
            sum(meal["recipe"].get("protein") or 0 for meal in meals),
            1,
        ),
        "fat": round(
            sum(meal["recipe"].get("fat") or 0 for meal in meals),
            1,
        ),
        "carbs": round(
            sum(meal["recipe"].get("carbs") or 0 for meal in meals),
            1,
        ),
    }

    return {
        "strategy": recommendation_payload["strategy"],
        "daily_target_calories": daily_target,
        "meals_per_day": meals_per_day,
        "meals": meals,
        "totals": totals,
    }


def replace_meal(
    db: Session,
    user_id,
    slot: str,
    current_recipe_id: int,
    target_calories: Optional[float],
    excluded_recipe_ids: list[int] | None = None,
) -> dict:
    recommendation_payload = get_recommendations(
        db=db,
        user_id=user_id,
        limit=60,
    )
    excluded_ids = set(excluded_recipe_ids or [])
    excluded_ids.add(current_recipe_id)

    best_recipe = None
    best_score = None
    for candidate in recommendation_payload["items"]:
        if candidate["id"] in excluded_ids:
            continue

        candidate_calories = candidate.get("calories")
        if target_calories is not None and candidate_calories is not None:
            score = abs(candidate_calories - target_calories)
        else:
            score = -candidate.get("predicted_rating", 0)

        if best_score is None or score < best_score:
            best_recipe = candidate
            best_score = score

    if best_recipe is None:
        raise ValueError("No replacement recipe available")

    return {
        "strategy": recommendation_payload["strategy"],
        "meal": {
            "slot": slot,
            "target_calories": target_calories,
            "recipe": best_recipe,
        },
    }
