from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.favorite import FavoriteRecipe
from app.models.user import User
from app.services.recipe_queries import RECIPE_SELECT_SQL, map_recipe_row

router = APIRouter()


@router.get("")
def list_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_month = datetime.now().month

    rows = db.execute(
        text(
            f"""
            {RECIPE_SELECT_SQL}
            JOIN favorite_recipes fav ON fav.recipe_id = r.id
            WHERE fav.user_id = :user_id
            ORDER BY fav.created_at DESC
            """
        ),
        {"user_id": current_user.id, "current_month": current_month},
    ).mappings()

    return {"items": [map_recipe_row(row) for row in rows]}


@router.post("/{recipe_id}", status_code=status.HTTP_201_CREATED)
def add_favorite(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe_exists = db.execute(
        text("SELECT 1 FROM recipes WHERE id = :recipe_id"),
        {"recipe_id": recipe_id},
    ).first()
    if recipe_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Рецепт не найден",
        )

    existing = (
        db.query(FavoriteRecipe)
        .filter(
            FavoriteRecipe.user_id == current_user.id,
            FavoriteRecipe.recipe_id == recipe_id,
        )
        .first()
    )
    if existing is None:
        db.add(FavoriteRecipe(user_id=current_user.id, recipe_id=recipe_id))
        db.commit()

    return {"message": "Рецепт добавлен в избранное", "recipe_id": recipe_id}


@router.delete("/{recipe_id}")
def remove_favorite(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(FavoriteRecipe).filter(
        FavoriteRecipe.user_id == current_user.id,
        FavoriteRecipe.recipe_id == recipe_id,
    ).delete()
    db.commit()

    return {"message": "Рецепт удален из избранного", "recipe_id": recipe_id}
