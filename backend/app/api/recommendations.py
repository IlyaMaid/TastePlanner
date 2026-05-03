import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.recommendations import (
    MealSwapRequest,
    RecommendationFeedbackRequest,
    UserEventRequest,
)
from app.services.recommender import (
    generate_meal_plan,
    generate_shopping_list,
    get_recommendations,
    replace_meal,
)

router = APIRouter()


@router.get("")
def list_recommendations(
    limit: int = Query(default=12, ge=1, le=50),
    demo_user_index: int | None = Query(default=None, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_recommendations(
        db=db,
        user_id=current_user.id,
        limit=limit,
        demo_user_index=demo_user_index,
    )


@router.get("/meal-plan")
def get_meal_plan(
    limit: int = Query(default=4, ge=1, le=6),
    meals_per_day: int | None = Query(default=None, ge=1, le=6),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return generate_meal_plan(
        db=db,
        user_id=current_user.id,
        limit=limit,
        meals_per_day_override=meals_per_day,
    )


@router.get("/shopping-list")
def get_shopping_list(
    days: int = Query(default=7, ge=1, le=7),
    meals_per_day: int | None = Query(default=None, ge=1, le=6),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return generate_shopping_list(
        db=db,
        user_id=current_user.id,
        days=days,
        meals_per_day_override=meals_per_day,
    )


@router.get("/readiness")
def get_readiness(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
                region_code,
                meals_per_day,
                daily_budget_rub,
                weekly_budget_rub,
                favorite_products_json,
                disliked_products_json,
                allergies_json
            FROM user_profiles
            WHERE user_id = :user_id
            """
        ),
        {"user_id": current_user.id},
    ).mappings().first()

    profile_checks = {
        "basic": bool(
            profile
            and profile["sex"]
            and profile["age"] is not None
            and profile["height_cm"] is not None
            and profile["weight_kg"] is not None
        ),
        "goal": bool(profile and profile["goal"] and profile["activity_level"]),
        "region": bool(profile and profile["region_code"]),
        "budget": bool(
            profile
            and (
                profile["daily_budget_rub"] is not None
                or profile["weekly_budget_rub"] is not None
            )
        ),
        "food_preferences": bool(
            profile
            and (
                profile["favorite_products_json"]
                or profile["disliked_products_json"]
                or profile["allergies_json"]
            )
        ),
        "meal_mode": bool(profile and profile["meals_per_day"]),
    }

    feedback = db.execute(
        text(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE liked IS TRUE) AS liked_count,
                COUNT(*) FILTER (WHERE liked IS FALSE) AS disliked_count,
                COUNT(*) FILTER (WHERE rating IS NOT NULL) AS rated_count,
                COUNT(*) FILTER (WHERE reason IS NOT NULL AND reason <> '') AS reasoned_count
            FROM user_recipe_feedback
            WHERE user_id = :user_id
            """
        ),
        {"user_id": current_user.id},
    ).mappings().first()

    event_rows = db.execute(
        text(
            """
            SELECT event_type, COUNT(*) AS count
            FROM user_events
            WHERE user_id = :user_id
            GROUP BY event_type
            ORDER BY count DESC
            """
        ),
        {"user_id": current_user.id},
    ).mappings().all()

    dataset = db.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM recipes) AS recipes_count,
                (SELECT COUNT(*) FROM recipe_ingredients) AS recipe_ingredients_count,
                (SELECT COUNT(*) FROM ingredients WHERE price_per_100g_rub IS NOT NULL) AS priced_products_count,
                (SELECT COUNT(*) FROM recipes WHERE translated_title IS NOT NULL) AS localized_recipes_count
            """
        )
    ).mappings().first()

    completed_checks = sum(1 for value in profile_checks.values() if value)
    completion_percent = round(completed_checks / len(profile_checks) * 100)

    return {
        "profile_completion_percent": completion_percent,
        "profile_checks": profile_checks,
        "feedback": {
            "total": int(feedback["total"] or 0),
            "liked_count": int(feedback["liked_count"] or 0),
            "disliked_count": int(feedback["disliked_count"] or 0),
            "rated_count": int(feedback["rated_count"] or 0),
            "reasoned_count": int(feedback["reasoned_count"] or 0),
        },
        "events": {
            row["event_type"]: int(row["count"] or 0)
            for row in event_rows
        },
        "dataset": {
            "recipes_count": int(dataset["recipes_count"] or 0),
            "recipe_ingredients_count": int(dataset["recipe_ingredients_count"] or 0),
            "priced_products_count": int(dataset["priced_products_count"] or 0),
            "localized_recipes_count": int(dataset["localized_recipes_count"] or 0),
        },
    }


@router.post("/events")
def save_event(
    payload: UserEventRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.execute(
        text(
            """
            INSERT INTO user_events (
                user_id,
                event_type,
                recipe_id,
                payload_json
            )
            VALUES (
                :user_id,
                :event_type,
                :recipe_id,
                CAST(:payload_json AS jsonb)
            )
            """
        ),
        {
            "user_id": current_user.id,
            "event_type": payload.event_type,
            "recipe_id": payload.recipe_id,
            "payload_json": json.dumps(payload.payload_json, ensure_ascii=False),
        },
    )
    db.commit()

    return {"message": "Event saved", "event_type": payload.event_type}


@router.post("/feedback")
def save_feedback(
    payload: RecommendationFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe_row = db.execute(
        text("SELECT id FROM recipes WHERE id = :recipe_id"),
        {"recipe_id": payload.recipe_id},
    ).fetchone()
    if recipe_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found",
        )

    db.execute(
        text(
            """
            INSERT INTO user_recipe_feedback (
                user_id,
                recipe_id,
                liked,
                rating,
                reason,
                too_expensive,
                too_long,
                contains_disliked,
                too_many_calories,
                not_enough_calories
            )
            VALUES (
                :user_id,
                :recipe_id,
                :liked,
                :rating,
                :reason,
                :too_expensive,
                :too_long,
                :contains_disliked,
                :too_many_calories,
                :not_enough_calories
            )
            ON CONFLICT (user_id, recipe_id)
            DO UPDATE SET
                liked = EXCLUDED.liked,
                rating = EXCLUDED.rating,
                reason = EXCLUDED.reason,
                too_expensive = EXCLUDED.too_expensive,
                too_long = EXCLUDED.too_long,
                contains_disliked = EXCLUDED.contains_disliked,
                too_many_calories = EXCLUDED.too_many_calories,
                not_enough_calories = EXCLUDED.not_enough_calories,
                updated_at = NOW()
            """
        ),
        {
            "user_id": current_user.id,
            "recipe_id": payload.recipe_id,
            "liked": payload.liked,
            "rating": payload.rating,
            "reason": payload.reason,
            "too_expensive": payload.too_expensive,
            "too_long": payload.too_long,
            "contains_disliked": payload.contains_disliked,
            "too_many_calories": payload.too_many_calories,
            "not_enough_calories": payload.not_enough_calories,
        },
    )
    db.commit()

    return {
        "message": "Feedback saved",
        "recipe_id": payload.recipe_id,
        "liked": payload.liked,
        "rating": payload.rating,
    }


@router.post("/meal-plan/swap")
def swap_meal(
    payload: MealSwapRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return replace_meal(
            db=db,
            user_id=current_user.id,
            slot=payload.slot,
            current_recipe_id=payload.current_recipe_id,
            target_calories=payload.target_calories,
            excluded_recipe_ids=payload.excluded_recipe_ids,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
