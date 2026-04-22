from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.recommendations import (
    MealSwapRequest,
    RecommendationFeedbackRequest,
)
from app.services.recommender import (
    generate_meal_plan,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return generate_meal_plan(
        db=db,
        user_id=current_user.id,
        limit=limit,
    )


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
            INSERT INTO user_recipe_feedback (user_id, recipe_id, liked, rating)
            VALUES (:user_id, :recipe_id, :liked, :rating)
            ON CONFLICT (user_id, recipe_id)
            DO UPDATE SET
                liked = EXCLUDED.liked,
                rating = EXCLUDED.rating
            """
        ),
        {
            "user_id": current_user.id,
            "recipe_id": payload.recipe_id,
            "liked": payload.liked,
            "rating": payload.rating,
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
