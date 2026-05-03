from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional

import joblib
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.regional_food_zones import get_region_food_zone


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
                COALESCE(r.translated_steps_json, r.steps_json, '[]'::jsonb) AS cooking_steps,
                r.total_minutes,
                r.calories,
                r.protein,
                r.fat,
                r.carbs,
                (
                    SELECT ROUND(SUM(i.price_per_100g_rub), 2)
                    FROM recipe_ingredients ri
                    JOIN ingredients i ON i.id = ri.ingredient_id
                    WHERE ri.recipe_id = r.id
                      AND i.price_per_100g_rub IS NOT NULL
                ) AS estimated_cost_rub,
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
                ) AS ingredients,
                COALESCE(
                    CAST((
                        SELECT json_agg(
                            json_build_object(
                                'raw_text', ingredient_row.raw_text,
                                'name_ru', ingredient_row.name_ru,
                                'calories_per_100g', ingredient_row.calories_per_100g,
                                'price_per_100g_rub', ingredient_row.price_per_100g_rub
                            )
                            ORDER BY ingredient_row.id
                        )
                        FROM (
                            SELECT
                                ri.id,
                                ri.raw_text,
                                COALESCE(i.display_name_ru, i.canonical_name) AS name_ru,
                                i.calories_per_100g,
                                i.price_per_100g_rub
                            FROM recipe_ingredients ri
                            JOIN ingredients i ON i.id = ri.ingredient_id
                            WHERE ri.recipe_id = r.id
                            ORDER BY ri.id
                            LIMIT 8
                        ) AS ingredient_row
                    ) AS jsonb),
                    '[]'::jsonb
                ) AS ingredient_details
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
            "cooking_steps": list(row["cooking_steps"] or []),
            "total_minutes": row["total_minutes"],
            "calories": float(row["calories"]) if row["calories"] is not None else None,
            "protein": float(row["protein"]) if row["protein"] is not None else None,
            "fat": float(row["fat"]) if row["fat"] is not None else None,
            "carbs": float(row["carbs"]) if row["carbs"] is not None else None,
            "estimated_cost_rub": (
                float(row["estimated_cost_rub"])
                if row["estimated_cost_rub"] is not None
                else None
            ),
            "ingredients": list(row["ingredients"] or []),
            "ingredient_details": list(row["ingredient_details"] or []),
        }
        for row in rows
    }


def _fetch_fallback_recipe_rows(
    db: Session,
    excluded_recipe_ids: Iterable[int],
    limit: int,
) -> list[dict]:
    excluded_ids = list({int(recipe_id) for recipe_id in excluded_recipe_ids})
    rows = db.execute(
        text(
            """
            SELECT
                r.id,
                r.source,
                r.source_recipe_id,
                COALESCE(r.translated_title, r.title) AS title,
                COALESCE(r.translated_description, r.description) AS description,
                COALESCE(r.translated_steps_json, r.steps_json, '[]'::jsonb) AS cooking_steps,
                r.total_minutes,
                r.calories,
                r.protein,
                r.fat,
                r.carbs,
                (
                    SELECT ROUND(SUM(i.price_per_100g_rub), 2)
                    FROM recipe_ingredients ri
                    JOIN ingredients i ON i.id = ri.ingredient_id
                    WHERE ri.recipe_id = r.id
                      AND i.price_per_100g_rub IS NOT NULL
                ) AS estimated_cost_rub,
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
                ) AS ingredients,
                COALESCE(
                    CAST((
                        SELECT json_agg(
                            json_build_object(
                                'raw_text', ingredient_row.raw_text,
                                'name_ru', ingredient_row.name_ru,
                                'calories_per_100g', ingredient_row.calories_per_100g,
                                'price_per_100g_rub', ingredient_row.price_per_100g_rub
                            )
                            ORDER BY ingredient_row.id
                        )
                        FROM (
                            SELECT
                                ri.id,
                                ri.raw_text,
                                COALESCE(i.display_name_ru, i.canonical_name) AS name_ru,
                                i.calories_per_100g,
                                i.price_per_100g_rub
                            FROM recipe_ingredients ri
                            JOIN ingredients i ON i.id = ri.ingredient_id
                            WHERE ri.recipe_id = r.id
                            ORDER BY ri.id
                            LIMIT 8
                        ) AS ingredient_row
                    ) AS jsonb),
                    '[]'::jsonb
                ) AS ingredient_details
            FROM recipes r
            WHERE (:has_excluded = FALSE OR r.id <> ALL(:excluded_recipe_ids))
            ORDER BY
                CASE WHEN r.calories IS NULL THEN 1 ELSE 0 END,
                r.rating DESC NULLS LAST,
                r.id DESC
            LIMIT :limit
            """
        ),
        {
            "excluded_recipe_ids": excluded_ids or [0],
            "has_excluded": bool(excluded_ids),
            "limit": limit,
        },
    ).mappings()

    return [
        {
            "id": row["id"],
            "source": row["source"],
            "source_recipe_id": row["source_recipe_id"],
            "title": row["title"],
            "description": row["description"],
            "cooking_steps": list(row["cooking_steps"] or []),
            "total_minutes": row["total_minutes"],
            "calories": float(row["calories"]) if row["calories"] is not None else None,
            "protein": float(row["protein"]) if row["protein"] is not None else None,
            "fat": float(row["fat"]) if row["fat"] is not None else None,
            "carbs": float(row["carbs"]) if row["carbs"] is not None else None,
            "estimated_cost_rub": (
                float(row["estimated_cost_rub"])
                if row["estimated_cost_rub"] is not None
                else None
            ),
            "ingredients": list(row["ingredients"] or []),
            "ingredient_details": list(row["ingredient_details"] or []),
            "predicted_rating": None,
            "model_item_index": None,
        }
        for row in rows
    ]


def _normalize_preference_values(values) -> list[str]:
    if not values:
        return []
    return [
        str(value).strip().casefold()
        for value in values
        if str(value).strip()
    ]


def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _fetch_user_food_preferences(db: Session, user_id) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT
                favorite_products_json,
                disliked_products_json,
                allergies_json,
                daily_budget_rub,
                weekly_budget_rub,
                daily_calorie_target,
                meals_per_day
            FROM user_profiles
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).mappings().first()

    if row is None:
        return {
            "favorite_products": [],
            "disliked_products": [],
            "allergies": [],
            "daily_budget_rub": None,
            "weekly_budget_rub": None,
            "daily_calorie_target": None,
            "meals_per_day": None,
        }

    return {
        "favorite_products": _normalize_preference_values(row["favorite_products_json"]),
        "disliked_products": _normalize_preference_values(row["disliked_products_json"]),
        "allergies": _normalize_preference_values(row["allergies_json"]),
        "daily_budget_rub": _safe_float(row["daily_budget_rub"]),
        "weekly_budget_rub": _safe_float(row["weekly_budget_rub"]),
        "daily_calorie_target": _safe_float(row["daily_calorie_target"]),
        "meals_per_day": int(row["meals_per_day"]) if row["meals_per_day"] else None,
    }


def _recipe_text_for_matching(recipe: dict) -> str:
    values = [
        recipe.get("title"),
        recipe.get("description"),
        *(recipe.get("ingredients") or []),
    ]
    for ingredient in recipe.get("ingredient_details") or []:
        if isinstance(ingredient, dict):
            values.extend([ingredient.get("raw_text"), ingredient.get("name_ru")])
    return " ".join(str(value) for value in values if value).casefold()


def _preference_score(recipe: dict, preferences: dict[str, Any]) -> int:
    text_value = _recipe_text_for_matching(recipe)
    if any(value in text_value for value in preferences["allergies"]):
        return -10_000
    if any(value in text_value for value in preferences["disliked_products"]):
        return -1_000
    if any(value in text_value for value in preferences["favorite_products"]):
        return 100
    return 0


def _budget_per_recipe(preferences: dict[str, Any]) -> Optional[float]:
    meals_per_day = int(preferences.get("meals_per_day") or 3)
    meals_per_day = max(1, min(meals_per_day, 6))

    daily_budget = preferences.get("daily_budget_rub")
    if daily_budget:
        return round(float(daily_budget) / meals_per_day, 2)

    weekly_budget = preferences.get("weekly_budget_rub")
    if weekly_budget:
        return round(float(weekly_budget) / 7 / meals_per_day, 2)

    return None


def _has_any_match(recipe: dict, values: list[str]) -> bool:
    if not values:
        return False
    text_value = _recipe_text_for_matching(recipe)
    return any(value in text_value for value in values)


def _build_recommendation_reasons(
    recipe: dict,
    preferences: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []

    if _has_any_match(recipe, preferences.get("favorite_products", [])):
        reasons.append("Есть любимые продукты")

    if preferences.get("allergies") and not _has_any_match(
        recipe,
        preferences["allergies"],
    ):
        reasons.append("Не найдено выбранных аллергенов")

    if preferences.get("disliked_products") and not _has_any_match(
        recipe,
        preferences["disliked_products"],
    ):
        reasons.append("Без нелюбимых продуктов")

    budget_per_recipe = _budget_per_recipe(preferences)
    estimated_cost = recipe.get("estimated_cost_rub")
    if budget_per_recipe and estimated_cost is not None:
        if float(estimated_cost) <= budget_per_recipe:
            reasons.append("Вписывается в бюджет")
        else:
            reasons.append("Выше бюджета, но близко по вкусу")

    daily_calorie_target = preferences.get("daily_calorie_target")
    meals_per_day = int(preferences.get("meals_per_day") or 3)
    recipe_calories = recipe.get("calories")
    if daily_calorie_target and recipe_calories is not None:
        target_per_recipe = float(daily_calorie_target) / max(meals_per_day, 1)
        if abs(float(recipe_calories) - target_per_recipe) <= target_per_recipe * 0.35:
            reasons.append("Близко к цели по калориям")

    total_minutes = recipe.get("total_minutes")
    if total_minutes is not None and int(total_minutes) <= 30:
        reasons.append("Быстро готовится")

    if recipe.get("protein") is not None and float(recipe["protein"]) >= 20:
        reasons.append("Хороший источник белка")

    predicted_rating = recipe.get("predicted_rating")
    if predicted_rating is not None and float(predicted_rating) >= 4:
        reasons.append("Высокая прогнозная оценка")

    return reasons[:4]


def _apply_food_preferences(items: list[dict], preferences: dict[str, Any]) -> list[dict]:
    scored_items = []
    for item in items:
        score = _preference_score(item, preferences)
        if score <= -10_000:
            continue
        scored_items.append((score, item))

    scored_items.sort(
        key=lambda pair: (
            pair[0],
            pair[1].get("predicted_rating") or 0,
            -(pair[1].get("calories") or 0),
        ),
        reverse=True,
    )
    personalized_items = [item for _, item in scored_items]
    for item in personalized_items:
        item["recommendation_reasons"] = _build_recommendation_reasons(
            item,
            preferences,
        )
    return personalized_items


def get_recommendations(
    db: Session,
    user_id,
    limit: int,
    demo_user_index: Optional[int] = None,
) -> dict:
    artifact = get_foodcom_artifact()
    preferences = _fetch_user_food_preferences(db, user_id)

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
        if len(items) >= max(limit * 3, limit):
            break

    items = _apply_food_preferences(items, preferences)[:limit]

    return {
        "strategy": strategy,
        "items": items,
        "count": len(items),
        "preference_profile": preferences,
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
    meals_per_day_override: Optional[int] = None,
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
                meals_per_day,
                region_code
            FROM user_profiles
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).fetchone()

    meals_per_day = (
        meals_per_day_override
        if meals_per_day_override is not None
        else int(profile.meals_per_day)
        if profile and profile.meals_per_day
        else limit
    )
    meals_per_day = max(1, min(meals_per_day, 6))

    recommendation_payload = get_recommendations(
        db=db,
        user_id=user_id,
        limit=max(meals_per_day * 6, 24),
    )
    candidates = recommendation_payload["items"]
    if len(candidates) < meals_per_day:
        existing_candidate_ids = [candidate["id"] for candidate in candidates]
        candidates = _apply_food_preferences(
            [
            *candidates,
            *_fetch_fallback_recipe_rows(
                db=db,
                excluded_recipe_ids=existing_candidate_ids,
                limit=max(meals_per_day * 4, 12),
            ),
            ],
            _fetch_user_food_preferences(db, user_id),
        )
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
            fallback_recipes = _apply_food_preferences(
                _fetch_fallback_recipe_rows(
                    db=db,
                    excluded_recipe_ids=used_recipe_ids,
                    limit=6,
                ),
                _fetch_user_food_preferences(db, user_id),
            )
            best_recipe = fallback_recipes[0] if fallback_recipes else None

        if best_recipe is None:
            continue

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
        "estimated_cost_rub": round(
            sum(meal["recipe"].get("estimated_cost_rub") or 0 for meal in meals),
            1,
        ),
    }

    return {
        "strategy": recommendation_payload["strategy"],
        "daily_target_calories": daily_target,
        "regional_food_zone": get_region_food_zone(profile.region_code if profile else None),
        "preference_profile": _fetch_user_food_preferences(db, user_id),
        "meals_per_day": meals_per_day,
        "meals": meals,
        "totals": totals,
    }


def _shopping_category_for_name(name: str) -> str:
    normalized = name.casefold()
    category_keywords = [
        ("Мясо и птица", ["кур", "говя", "свин", "мяс"]),
        ("Рыба", ["рыб", "лосос", "треск", "морепродукт"]),
        ("Молочные продукты", ["молок", "кефир", "творог", "сметан", "сыр", "йогурт", "масло слив"]),
        ("Крупы и хлеб", ["рис", "греч", "овся", "макарон", "мук", "хлеб", "паста"]),
        ("Овощи", ["карто", "морков", "лук", "чеснок", "помид", "томат", "огур", "перец", "капуст", "кабач", "баклаж", "гриб", "шамп"]),
        ("Фрукты и ягоды", ["яблок", "банан", "апельс", "лимон", "ягод"]),
        ("Бобовые и орехи", ["фасол", "горох", "чечев", "орех", "миндал"]),
        ("Бакалея и соусы", ["сахар", "соль", "масло", "майонез", "кетчуп", "мед", "мёд", "шоколад"]),
    ]
    for category, keywords in category_keywords:
        if any(keyword in normalized for keyword in keywords):
            return category
    return "Прочее"


def generate_shopping_list(
    db: Session,
    user_id,
    days: int = 7,
    meals_per_day_override: Optional[int] = None,
) -> dict:
    days = max(1, min(days, 7))
    base_plan = generate_meal_plan(
        db=db,
        user_id=user_id,
        meals_per_day_override=meals_per_day_override,
    )

    aggregated: dict[str, dict] = {}
    for day_index in range(days):
        meals = base_plan["meals"]
        if meals:
            rotated_meals = [
                {
                    **meal,
                    "recipe": meals[(index + day_index) % len(meals)]["recipe"],
                }
                for index, meal in enumerate(meals)
            ]
        else:
            rotated_meals = []

        for meal in rotated_meals:
            recipe = meal["recipe"]
            for ingredient in recipe.get("ingredient_details") or []:
                if not isinstance(ingredient, dict):
                    continue
                name = ingredient.get("name_ru") or ingredient.get("raw_text")
                if not name:
                    continue

                key = str(name).strip().casefold()
                price = ingredient.get("price_per_100g_rub")
                calories = ingredient.get("calories_per_100g")
                if key not in aggregated:
                    aggregated[key] = {
                        "id": key,
                        "name": str(name).strip(),
                        "category": _shopping_category_for_name(str(name)),
                        "quantity": "100 г",
                        "uses": 0,
                        "estimated_cost_rub": 0,
                        "calories_per_100g": calories,
                        "recipes": set(),
                    }

                aggregated[key]["uses"] += 1
                aggregated[key]["estimated_cost_rub"] += float(price or 0)
                aggregated[key]["recipes"].add(recipe["title"])

    items = []
    for item in aggregated.values():
        uses = int(item["uses"])
        items.append(
            {
                "id": item["id"],
                "name": item["name"],
                "category": item["category"],
                "quantity": f"{uses * 100} г",
                "uses": uses,
                "estimated_cost_rub": round(item["estimated_cost_rub"], 1),
                "calories_per_100g": item["calories_per_100g"],
                "recipes": sorted(item["recipes"])[:3],
            }
        )

    items.sort(key=lambda item: (item["category"], item["name"]))
    total_cost = round(sum(item["estimated_cost_rub"] for item in items), 1)

    return {
        "days": days,
        "meals_per_day": base_plan["meals_per_day"],
        "items": items,
        "total_items": len(items),
        "estimated_total_cost_rub": total_cost,
        "regional_food_zone": base_plan.get("regional_food_zone"),
        "preference_profile": base_plan.get("preference_profile"),
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
    preferences = _fetch_user_food_preferences(db, user_id)

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
        fallback_recipes = _apply_food_preferences(
            _fetch_fallback_recipe_rows(
                db=db,
                excluded_recipe_ids=excluded_ids,
                limit=6,
            ),
            preferences,
        )
        best_recipe = fallback_recipes[0] if fallback_recipes else None

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
