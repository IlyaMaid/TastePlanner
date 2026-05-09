from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional

import joblib
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.regional_food_zones import get_region_food_zone


ARTIFACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "artifacts"
    / "recommender"
    / "foodcom_svd_recommender.joblib"
)
CONTENT_RANKER_PATH = (
    Path(__file__).resolve().parents[3]
    / "artifacts"
    / "recommender"
    / "tasteplanner_content_ranker.joblib"
)

CONTENT_NUMERIC_COLUMNS = [
    "age",
    "height_cm",
    "weight_kg",
    "daily_budget_rub",
    "weekly_budget_rub",
    "effective_daily_budget_rub",
    "budget_per_meal_rub",
    "meals_per_day",
    "total_minutes",
    "calories",
    "protein",
    "fat",
    "carbs",
    "source_rating",
    "ingredient_count",
    "priced_ingredient_count",
    "price_coverage",
    "estimated_cost_rub",
    "seasonal_ingredient_count",
    "current_month",
    "cost_to_budget_ratio",
    "favorite_match_count",
    "disliked_match_count",
    "allergy_match_count",
    "has_any_favorite_match",
    "has_any_disliked_match",
    "has_any_allergy_match",
    "is_within_budget",
    "is_seasonal_now",
    "has_meat",
    "has_fish",
    "has_dairy",
    "has_grains",
    "has_vegetables",
    "has_fruit",
    "has_legumes",
    "has_nuts",
    "has_pantry",
]

CONTENT_CATEGORICAL_COLUMNS = [
    "sex",
    "activity_level",
    "goal",
    "region_code",
    "source",
    "budget_tier",
    "time_tier",
    "calorie_tier",
    "protein_tier",
]

MONTH_NAMES_RU = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "октябрь",
    11: "ноябрь",
    12: "декабрь",
}


def _current_month() -> int:
    return datetime.now().month


def _seasonality_score(recipe: dict) -> int:
    if recipe.get("is_seasonal_now"):
        return 35
    if recipe.get("seasonal_ingredient_count"):
        return 5
    return 0


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


@lru_cache(maxsize=1)
def get_content_ranker_artifact() -> Optional[dict]:
    if not CONTENT_RANKER_PATH.exists():
        return None
    return joblib.load(CONTENT_RANKER_PATH)


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
                COALESCE(rf.seasonal_months_json, '[]'::jsonb) AS seasonal_months_json,
                COALESCE(rf.seasonal_ingredient_count, 0) AS seasonal_ingredient_count,
                COALESCE(rf.tags_json, '[]'::jsonb) AS tags_json,
                COALESCE(rf.canonical_ingredients_json, '[]'::jsonb) AS canonical_ingredients_json,
                COALESCE(rf.product_categories_json, '[]'::jsonb) AS product_categories_json,
                COALESCE(rf.source_rating, r.rating) AS source_rating,
                COALESCE(rf.ingredient_count, 0) AS ingredient_count,
                COALESCE(rf.priced_ingredient_count, 0) AS priced_ingredient_count,
                COALESCE(rf.price_coverage, 0) AS price_coverage,
                rf.budget_tier,
                rf.time_tier,
                rf.calorie_tier,
                rf.protein_tier,
                COALESCE(rf.has_meat, FALSE) AS has_meat,
                COALESCE(rf.has_fish, FALSE) AS has_fish,
                COALESCE(rf.has_dairy, FALSE) AS has_dairy,
                COALESCE(rf.has_grains, FALSE) AS has_grains,
                COALESCE(rf.has_vegetables, FALSE) AS has_vegetables,
                COALESCE(rf.has_fruit, FALSE) AS has_fruit,
                COALESCE(rf.has_legumes, FALSE) AS has_legumes,
                COALESCE(rf.has_nuts, FALSE) AS has_nuts,
                COALESCE(rf.has_pantry, FALSE) AS has_pantry,
                CASE
                    WHEN COALESCE(rf.seasonal_months_json, '[]'::jsonb)
                        @> to_jsonb(CAST(:current_month AS integer))
                    THEN TRUE
                    ELSE FALSE
                END AS is_seasonal_now,
                (
                    SELECT ROUND(
                        SUM(
                            CASE
                                WHEN ri.quantity IS NOT NULL
                                  AND ri.unit = 'g'
                                  AND i.price_per_100g_rub IS NOT NULL
                                THEN ri.quantity * i.price_per_100g_rub / 100
                                ELSE i.price_per_100g_rub
                            END
                        ),
                        2
                    )
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
                                'quantity', ingredient_row.quantity,
                                'unit', ingredient_row.unit,
                                'calories_per_100g', ingredient_row.calories_per_100g,
                                'price_per_100g_rub', ingredient_row.price_per_100g_rub,
                                'calories_total', ingredient_row.calories_total,
                                'estimated_cost_rub', ingredient_row.estimated_cost_rub
                            )
                            ORDER BY ingredient_row.id
                        )
                        FROM (
                            SELECT
                                ri.id,
                                ri.raw_text,
                                ri.quantity,
                                ri.unit,
                                COALESCE(i.display_name_ru, i.canonical_name) AS name_ru,
                                i.calories_per_100g,
                                i.price_per_100g_rub,
                                CASE
                                    WHEN ri.quantity IS NOT NULL
                                      AND ri.unit = 'g'
                                      AND i.calories_per_100g IS NOT NULL
                                    THEN ROUND(ri.quantity * i.calories_per_100g / 100, 1)
                                    ELSE NULL
                                END AS calories_total,
                                CASE
                                    WHEN ri.quantity IS NOT NULL
                                      AND ri.unit = 'g'
                                      AND i.price_per_100g_rub IS NOT NULL
                                    THEN ROUND(ri.quantity * i.price_per_100g_rub / 100, 2)
                                    ELSE NULL
                                END AS estimated_cost_rub
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
            LEFT JOIN recipe_features rf ON rf.recipe_id = r.id
            WHERE r.source = 'foodcom'
              AND r.source_recipe_id = ANY(:source_recipe_ids)
            """
        ),
        {"source_recipe_ids": recipe_ids, "current_month": _current_month()},
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
            "seasonal_months": list(row["seasonal_months_json"] or []),
            "seasonal_ingredient_count": int(row["seasonal_ingredient_count"] or 0),
            "tags": list(row["tags_json"] or []),
            "canonical_ingredients": list(row["canonical_ingredients_json"] or []),
            "product_categories": list(row["product_categories_json"] or []),
            "source_rating": _safe_float(row["source_rating"]),
            "ingredient_count": int(row["ingredient_count"] or 0),
            "priced_ingredient_count": int(row["priced_ingredient_count"] or 0),
            "price_coverage": _safe_float(row["price_coverage"]) or 0,
            "budget_tier": row["budget_tier"],
            "time_tier": row["time_tier"],
            "calorie_tier": row["calorie_tier"],
            "protein_tier": row["protein_tier"],
            "has_meat": bool(row["has_meat"]),
            "has_fish": bool(row["has_fish"]),
            "has_dairy": bool(row["has_dairy"]),
            "has_grains": bool(row["has_grains"]),
            "has_vegetables": bool(row["has_vegetables"]),
            "has_fruit": bool(row["has_fruit"]),
            "has_legumes": bool(row["has_legumes"]),
            "has_nuts": bool(row["has_nuts"]),
            "has_pantry": bool(row["has_pantry"]),
            "is_seasonal_now": bool(row["is_seasonal_now"]),
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
    current_month = _current_month()
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
                COALESCE(rf.seasonal_months_json, '[]'::jsonb) AS seasonal_months_json,
                COALESCE(rf.seasonal_ingredient_count, 0) AS seasonal_ingredient_count,
                COALESCE(rf.tags_json, '[]'::jsonb) AS tags_json,
                COALESCE(rf.canonical_ingredients_json, '[]'::jsonb) AS canonical_ingredients_json,
                COALESCE(rf.product_categories_json, '[]'::jsonb) AS product_categories_json,
                COALESCE(rf.source_rating, r.rating) AS source_rating,
                COALESCE(rf.ingredient_count, 0) AS ingredient_count,
                COALESCE(rf.priced_ingredient_count, 0) AS priced_ingredient_count,
                COALESCE(rf.price_coverage, 0) AS price_coverage,
                rf.budget_tier,
                rf.time_tier,
                rf.calorie_tier,
                rf.protein_tier,
                COALESCE(rf.has_meat, FALSE) AS has_meat,
                COALESCE(rf.has_fish, FALSE) AS has_fish,
                COALESCE(rf.has_dairy, FALSE) AS has_dairy,
                COALESCE(rf.has_grains, FALSE) AS has_grains,
                COALESCE(rf.has_vegetables, FALSE) AS has_vegetables,
                COALESCE(rf.has_fruit, FALSE) AS has_fruit,
                COALESCE(rf.has_legumes, FALSE) AS has_legumes,
                COALESCE(rf.has_nuts, FALSE) AS has_nuts,
                COALESCE(rf.has_pantry, FALSE) AS has_pantry,
                CASE
                    WHEN COALESCE(rf.seasonal_months_json, '[]'::jsonb)
                        @> to_jsonb(CAST(:current_month AS integer))
                    THEN TRUE
                    ELSE FALSE
                END AS is_seasonal_now,
                (
                    SELECT ROUND(
                        SUM(
                            CASE
                                WHEN ri.quantity IS NOT NULL
                                  AND ri.unit = 'g'
                                  AND i.price_per_100g_rub IS NOT NULL
                                THEN ri.quantity * i.price_per_100g_rub / 100
                                ELSE i.price_per_100g_rub
                            END
                        ),
                        2
                    )
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
                                'quantity', ingredient_row.quantity,
                                'unit', ingredient_row.unit,
                                'calories_per_100g', ingredient_row.calories_per_100g,
                                'price_per_100g_rub', ingredient_row.price_per_100g_rub,
                                'calories_total', ingredient_row.calories_total,
                                'estimated_cost_rub', ingredient_row.estimated_cost_rub
                            )
                            ORDER BY ingredient_row.id
                        )
                        FROM (
                            SELECT
                                ri.id,
                                ri.raw_text,
                                ri.quantity,
                                ri.unit,
                                COALESCE(i.display_name_ru, i.canonical_name) AS name_ru,
                                i.calories_per_100g,
                                i.price_per_100g_rub,
                                CASE
                                    WHEN ri.quantity IS NOT NULL
                                      AND ri.unit = 'g'
                                      AND i.calories_per_100g IS NOT NULL
                                    THEN ROUND(ri.quantity * i.calories_per_100g / 100, 1)
                                    ELSE NULL
                                END AS calories_total,
                                CASE
                                    WHEN ri.quantity IS NOT NULL
                                      AND ri.unit = 'g'
                                      AND i.price_per_100g_rub IS NOT NULL
                                    THEN ROUND(ri.quantity * i.price_per_100g_rub / 100, 2)
                                    ELSE NULL
                                END AS estimated_cost_rub
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
            LEFT JOIN recipe_features rf ON rf.recipe_id = r.id
            WHERE (:has_excluded = FALSE OR r.id <> ALL(:excluded_recipe_ids))
              AND COALESCE(r.is_user_facing, TRUE) = TRUE
            ORDER BY
                CASE
                    WHEN COALESCE(rf.seasonal_months_json, '[]'::jsonb)
                        @> to_jsonb(CAST(:current_month AS integer))
                    THEN 0
                    ELSE 1
                END,
                CASE WHEN r.source = 'curated_ru' THEN 0 ELSE 1 END,
                r.quality_score DESC NULLS LAST,
                CASE WHEN r.calories IS NULL THEN 1 ELSE 0 END,
                r.rating DESC NULLS LAST,
                r.id DESC
            LIMIT :limit
            """
        ),
        {
            "excluded_recipe_ids": excluded_ids or [0],
            "has_excluded": bool(excluded_ids),
            "current_month": current_month,
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
            "seasonal_months": list(row["seasonal_months_json"] or []),
            "seasonal_ingredient_count": int(row["seasonal_ingredient_count"] or 0),
            "tags": list(row["tags_json"] or []),
            "canonical_ingredients": list(row["canonical_ingredients_json"] or []),
            "product_categories": list(row["product_categories_json"] or []),
            "source_rating": _safe_float(row["source_rating"]),
            "ingredient_count": int(row["ingredient_count"] or 0),
            "priced_ingredient_count": int(row["priced_ingredient_count"] or 0),
            "price_coverage": _safe_float(row["price_coverage"]) or 0,
            "budget_tier": row["budget_tier"],
            "time_tier": row["time_tier"],
            "calorie_tier": row["calorie_tier"],
            "protein_tier": row["protein_tier"],
            "has_meat": bool(row["has_meat"]),
            "has_fish": bool(row["has_fish"]),
            "has_dairy": bool(row["has_dairy"]),
            "has_grains": bool(row["has_grains"]),
            "has_vegetables": bool(row["has_vegetables"]),
            "has_fruit": bool(row["has_fruit"]),
            "has_legumes": bool(row["has_legumes"]),
            "has_nuts": bool(row["has_nuts"]),
            "has_pantry": bool(row["has_pantry"]),
            "is_seasonal_now": bool(row["is_seasonal_now"]),
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
                sex,
                age,
                height_cm,
                weight_kg,
                activity_level,
                goal,
                region_code,
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
            "sex": None,
            "age": None,
            "height_cm": None,
            "weight_kg": None,
            "activity_level": None,
            "goal": None,
            "region_code": None,
            "daily_budget_rub": None,
            "weekly_budget_rub": None,
            "daily_calorie_target": None,
            "meals_per_day": None,
        }

    return {
        "favorite_products": _normalize_preference_values(row["favorite_products_json"]),
        "disliked_products": _normalize_preference_values(row["disliked_products_json"]),
        "allergies": _normalize_preference_values(row["allergies_json"]),
        "sex": row["sex"],
        "age": _safe_float(row["age"]),
        "height_cm": _safe_float(row["height_cm"]),
        "weight_kg": _safe_float(row["weight_kg"]),
        "activity_level": row["activity_level"],
        "goal": row["goal"],
        "region_code": row["region_code"],
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


def _match_count(recipe: dict, values: list[str]) -> int:
    if not values:
        return 0
    text_value = _recipe_text_for_matching(recipe)
    return sum(1 for value in values if value in text_value)


def _tier_score(value: Optional[str], mapping: dict[str, float]) -> float:
    return mapping.get(str(value or ""), 0.0)


def _recipe_content_vector(recipe: dict) -> np.ndarray:
    calories = float(recipe.get("calories") or 0)
    cost = float(recipe.get("estimated_cost_rub") or 0)
    minutes = float(recipe.get("total_minutes") or 0)
    protein = float(recipe.get("protein") or 0)
    return np.array(
        [
            min(calories / 700, 1.5),
            min(cost / 400, 1.5),
            min(minutes / 90, 1.5),
            min(protein / 35, 1.5),
            _tier_score(recipe.get("budget_tier"), {"low": 1.0, "medium": 0.55}),
            _tier_score(
                recipe.get("time_tier"),
                {"very_fast": 1.0, "fast": 0.75, "medium": 0.35},
            ),
            _tier_score(
                recipe.get("calorie_tier"),
                {"light": 0.85, "balanced": 1.0, "high": 0.25},
            ),
            _tier_score(recipe.get("protein_tier"), {"high": 1.0, "medium": 0.55}),
            1.0 if recipe.get("is_seasonal_now") else 0.0,
            1.0 if recipe.get("has_meat") else 0.0,
            1.0 if recipe.get("has_fish") else 0.0,
            1.0 if recipe.get("has_dairy") else 0.0,
            1.0 if recipe.get("has_grains") else 0.0,
            1.0 if recipe.get("has_vegetables") else 0.0,
            1.0 if recipe.get("has_fruit") else 0.0,
            1.0 if recipe.get("has_legumes") else 0.0,
        ],
        dtype=np.float32,
    )


def _user_content_vector(preferences: dict[str, Any]) -> np.ndarray:
    budget_per_recipe = _budget_per_recipe(preferences) or 250
    meals_per_day = float(preferences.get("meals_per_day") or 3)
    calorie_target = preferences.get("daily_calorie_target")
    if calorie_target:
        target_calories = float(calorie_target) / max(meals_per_day, 1)
    else:
        target_calories = 520

    goal = preferences.get("goal")
    wants_light = 1.0 if goal == "lose_weight" else 0.45
    wants_balanced = 1.0 if goal in {"maintain", None} else 0.65
    wants_protein = 1.0 if goal == "gain_weight" else 0.65

    favorite_text = " ".join(preferences.get("favorite_products", []))
    return np.array(
        [
            min(target_calories / 700, 1.5),
            min(float(budget_per_recipe) / 400, 1.5),
            0.45,
            wants_protein,
            1.0,
            0.85,
            max(wants_light, wants_balanced),
            wants_protein,
            0.8,
            1.0 if any(value in favorite_text for value in ("кур", "говя", "свин", "мяс")) else 0.45,
            1.0 if any(value in favorite_text for value in ("рыб", "лосос", "треск", "минтай")) else 0.45,
            1.0 if any(value in favorite_text for value in ("молок", "сыр", "творог", "йогурт")) else 0.45,
            1.0 if any(value in favorite_text for value in ("рис", "греч", "овся", "макарон", "пшено")) else 0.45,
            1.0 if any(value in favorite_text for value in ("овощ", "капуст", "помид", "огур", "брокк")) else 0.65,
            1.0 if any(value in favorite_text for value in ("яблок", "банан", "ягод")) else 0.35,
            1.0 if any(value in favorite_text for value in ("фасол", "горох", "чечев")) else 0.35,
        ],
        dtype=np.float32,
    )


def _cosine_similarity(user_vector: np.ndarray, recipe_vector: np.ndarray) -> float:
    denominator = float(np.linalg.norm(user_vector) * np.linalg.norm(recipe_vector))
    if denominator == 0:
        return 0.0
    return round(float(np.dot(user_vector, recipe_vector) / denominator), 4)


def _content_similarity_score(recipe: dict, preferences: dict[str, Any]) -> float:
    score = _cosine_similarity(
        _user_content_vector(preferences),
        _recipe_content_vector(recipe),
    )
    if _has_any_match(recipe, preferences.get("favorite_products", [])):
        score += 0.08
    if _has_any_match(recipe, preferences.get("disliked_products", [])):
        score -= 0.2
    if _has_any_match(recipe, preferences.get("allergies", [])):
        score -= 1.0
    return round(max(0.0, min(score, 1.0)), 4)


def _model_feature_row(recipe: dict, preferences: dict[str, Any]) -> dict[str, Any]:
    budget_per_recipe = _budget_per_recipe(preferences)
    estimated_cost = recipe.get("estimated_cost_rub")
    cost_to_budget_ratio = (
        round(float(estimated_cost) / budget_per_recipe, 4)
        if budget_per_recipe and estimated_cost is not None
        else None
    )
    return {
        "age": preferences.get("age"),
        "height_cm": preferences.get("height_cm"),
        "weight_kg": preferences.get("weight_kg"),
        "daily_budget_rub": preferences.get("daily_budget_rub"),
        "weekly_budget_rub": preferences.get("weekly_budget_rub"),
        "effective_daily_budget_rub": preferences.get("daily_budget_rub")
        or (
            round(float(preferences["weekly_budget_rub"]) / 7, 2)
            if preferences.get("weekly_budget_rub")
            else None
        ),
        "budget_per_meal_rub": budget_per_recipe,
        "meals_per_day": preferences.get("meals_per_day"),
        "total_minutes": recipe.get("total_minutes"),
        "calories": recipe.get("calories"),
        "protein": recipe.get("protein"),
        "fat": recipe.get("fat"),
        "carbs": recipe.get("carbs"),
        "source_rating": recipe.get("source_rating"),
        "ingredient_count": recipe.get("ingredient_count"),
        "priced_ingredient_count": recipe.get("priced_ingredient_count"),
        "price_coverage": recipe.get("price_coverage"),
        "estimated_cost_rub": estimated_cost,
        "seasonal_ingredient_count": recipe.get("seasonal_ingredient_count"),
        "current_month": _current_month(),
        "cost_to_budget_ratio": cost_to_budget_ratio,
        "favorite_match_count": _match_count(recipe, preferences.get("favorite_products", [])),
        "disliked_match_count": _match_count(recipe, preferences.get("disliked_products", [])),
        "allergy_match_count": _match_count(recipe, preferences.get("allergies", [])),
        "has_any_favorite_match": int(_has_any_match(recipe, preferences.get("favorite_products", []))),
        "has_any_disliked_match": int(_has_any_match(recipe, preferences.get("disliked_products", []))),
        "has_any_allergy_match": int(_has_any_match(recipe, preferences.get("allergies", []))),
        "is_within_budget": int(cost_to_budget_ratio is not None and cost_to_budget_ratio <= 1),
        "is_seasonal_now": int(bool(recipe.get("is_seasonal_now"))),
        "sex": preferences.get("sex"),
        "activity_level": preferences.get("activity_level"),
        "goal": preferences.get("goal"),
        "region_code": preferences.get("region_code"),
        "source": recipe.get("source"),
        "budget_tier": recipe.get("budget_tier"),
        "time_tier": recipe.get("time_tier"),
        "calorie_tier": recipe.get("calorie_tier"),
        "protein_tier": recipe.get("protein_tier"),
        "has_meat": int(bool(recipe.get("has_meat"))),
        "has_fish": int(bool(recipe.get("has_fish"))),
        "has_dairy": int(bool(recipe.get("has_dairy"))),
        "has_grains": int(bool(recipe.get("has_grains"))),
        "has_vegetables": int(bool(recipe.get("has_vegetables"))),
        "has_fruit": int(bool(recipe.get("has_fruit"))),
        "has_legumes": int(bool(recipe.get("has_legumes"))),
        "has_nuts": int(bool(recipe.get("has_nuts"))),
        "has_pantry": int(bool(recipe.get("has_pantry"))),
    }


def _model_prediction_scores(items: list[dict], preferences: dict[str, Any]) -> list[float]:
    artifact = get_content_ranker_artifact()
    if artifact is None or not items:
        return [0.5 for _ in items]
    model = artifact["model"]
    rows = [_model_feature_row(item, preferences) for item in items]
    scores = model.predict_proba(pd.DataFrame(rows))[:, 1]
    return [round(float(score), 4) for score in scores]


def _hybrid_rank_items(items: list[dict], preferences: dict[str, Any]) -> list[dict]:
    model_scores = _model_prediction_scores(items, preferences)
    ranked: list[dict] = []
    for item, model_score in zip(items, model_scores, strict=False):
        similarity = _content_similarity_score(item, preferences)
        popularity = min(float(item.get("source_rating") or 4.8) / 5, 1)
        rules = max(_preference_score(item, preferences), -1000) / 100
        final_score = (
            similarity * 0.45
            + model_score * 0.35
            + popularity * 0.10
            + _seasonality_score(item) / 100 * 0.05
            + max(rules, 0) * 0.05
        )
        item["content_similarity"] = round(similarity, 4)
        item["predicted_score"] = round(model_score, 4)
        item["predicted_rating"] = round(1 + model_score * 4, 4)
        item["final_score"] = round(final_score, 4)
        ranked.append(item)
    ranked.sort(key=lambda item: item.get("final_score") or 0, reverse=True)
    return ranked


def _build_recommendation_reasons(
    recipe: dict,
    preferences: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []

    if recipe.get("is_seasonal_now"):
        month_label = MONTH_NAMES_RU.get(_current_month(), "сейчас")
        reasons.append(f"По сезону: {month_label}")

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
    filtered_items = []
    for item in items:
        score = _preference_score(item, preferences)
        if score <= -10_000:
            continue
        filtered_items.append(item)

    personalized_items = _hybrid_rank_items(filtered_items, preferences)
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
    preferences = _fetch_user_food_preferences(db, user_id)

    curated_items = _apply_food_preferences(
        _fetch_fallback_recipe_rows(
            db=db,
            excluded_recipe_ids=[],
            limit=max(limit * 4, 24),
        ),
        preferences,
    )
    if len(curated_items) >= limit:
        items = curated_items[:limit]
        return {
            "strategy": "hybrid_content_model",
            "items": items,
            "count": len(items),
            "preference_profile": preferences,
            "seasonal_context": {
                "month": _current_month(),
                "month_label": MONTH_NAMES_RU.get(_current_month()),
            },
        }

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
        if len(items) >= max(limit * 3, limit):
            break

    items = _apply_food_preferences(items, preferences)[:limit]

    return {
        "strategy": strategy,
        "items": items,
        "count": len(items),
        "preference_profile": preferences,
        "seasonal_context": {
            "month": _current_month(),
            "month_label": MONTH_NAMES_RU.get(_current_month()),
        },
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


def _select_meals_with_optimization(
    candidates: list[dict],
    meal_labels: list[str],
    meal_shares: list[float],
    daily_target: Optional[float],
) -> list[dict]:
    if not candidates or not meal_labels:
        return []

    candidate_pool = candidates[: max(len(meal_labels) * 8, len(meal_labels))]
    cost_matrix = np.zeros((len(meal_labels), len(candidate_pool)), dtype=np.float64)

    for meal_index, _meal_label in enumerate(meal_labels):
        target_calories = (
            round(daily_target * meal_shares[meal_index], 0)
            if daily_target is not None
            else None
        )
        for recipe_index, candidate in enumerate(candidate_pool):
            final_score = float(candidate.get("final_score") or 0)
            if target_calories is not None and candidate.get("calories") is not None:
                calorie_penalty = abs(float(candidate["calories"]) - target_calories) / max(
                    target_calories,
                    1,
                )
            else:
                calorie_penalty = 0.35
            cost_matrix[meal_index, recipe_index] = calorie_penalty - final_score * 0.65

    row_indices, column_indices = linear_sum_assignment(cost_matrix)
    meals = []
    for row_index, column_index in zip(row_indices, column_indices, strict=False):
        if row_index >= len(meal_labels):
            continue
        target_calories = (
            round(daily_target * meal_shares[row_index], 0)
            if daily_target is not None
            else None
        )
        meals.append(
            {
                "slot": meal_labels[row_index],
                "target_calories": target_calories,
                "recipe": candidate_pool[column_index],
            }
        )

    meals.sort(key=lambda meal: meal_labels.index(meal["slot"]))
    return meals


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
    meals = _select_meals_with_optimization(
        candidates=candidates,
        meal_labels=meal_labels,
        meal_shares=meal_shares,
        daily_target=daily_target,
    )

    if len(meals) < meals_per_day:
        used_recipe_ids = {meal["recipe"]["id"] for meal in meals}
        fallback_recipes = _apply_food_preferences(
            _fetch_fallback_recipe_rows(
                db=db,
                excluded_recipe_ids=used_recipe_ids,
                limit=max(meals_per_day * 4, 12),
            ),
            _fetch_user_food_preferences(db, user_id),
        )
        for meal_label in meal_labels[len(meals):]:
            next_recipe = next(
                (
                    recipe
                    for recipe in fallback_recipes
                    if recipe["id"] not in used_recipe_ids
                ),
                None,
            )
            if next_recipe is None:
                break
            used_recipe_ids.add(next_recipe["id"])
            meals.append(
                {
                    "slot": meal_label,
                    "target_calories": None,
                    "recipe": next_recipe,
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
        "seasonal_context": recommendation_payload.get("seasonal_context"),
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
                quantity = ingredient.get("quantity")
                unit = ingredient.get("unit")
                quantity_g = (
                    float(quantity)
                    if quantity is not None and unit == "g"
                    else 100
                )
                ingredient_cost = ingredient.get("estimated_cost_rub")
                if ingredient_cost is None and price is not None:
                    ingredient_cost = quantity_g * float(price) / 100
                if key not in aggregated:
                    aggregated[key] = {
                        "id": key,
                        "name": str(name).strip(),
                        "category": _shopping_category_for_name(str(name)),
                        "quantity_g": 0,
                        "uses": 0,
                        "estimated_cost_rub": 0,
                        "calories_per_100g": calories,
                        "recipes": set(),
                    }

                aggregated[key]["uses"] += 1
                aggregated[key]["quantity_g"] += quantity_g
                aggregated[key]["estimated_cost_rub"] += float(ingredient_cost or 0)
                aggregated[key]["recipes"].add(recipe["title"])

    items = []
    for item in aggregated.values():
        uses = int(item["uses"])
        items.append(
            {
                "id": item["id"],
                "name": item["name"],
                "category": item["category"],
                "quantity": f"{round(item['quantity_g'])} г",
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
        "seasonal_context": base_plan.get("seasonal_context"),
    }


def replace_meal(
    db: Session,
    user_id,
    slot: str,
    current_recipe_id: int,
    target_calories: Optional[float],
    excluded_recipe_ids: list[int] | None = None,
    mode: str = "balanced",
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
        candidate_cost = candidate.get("estimated_cost_rub")
        candidate_minutes = candidate.get("total_minutes")
        final_score = candidate.get("final_score") or candidate.get("predicted_score") or 0

        if mode == "cheaper":
            score = (
                float(candidate_cost) if candidate_cost is not None else 999999,
                abs((candidate_calories or 0) - target_calories)
                if target_calories is not None
                else 0,
                -float(final_score),
            )
        elif mode == "faster":
            score = (
                float(candidate_minutes) if candidate_minutes is not None else 999999,
                float(candidate_cost) if candidate_cost is not None else 999999,
                -float(final_score),
            )
        elif mode == "lighter":
            score = (
                float(candidate_calories) if candidate_calories is not None else 999999,
                float(candidate_cost) if candidate_cost is not None else 999999,
                -float(final_score),
            )
        elif target_calories is not None and candidate_calories is not None:
            score = (
                abs(candidate_calories - target_calories),
                -float(final_score),
            )
        else:
            score = (-float(final_score),)

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
        "mode": mode,
        "meal": {
            "slot": slot,
            "target_calories": target_calories,
            "recipe": best_recipe,
        },
    }
