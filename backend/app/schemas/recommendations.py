from typing import Optional

from pydantic import BaseModel, Field


class RecommendationFeedbackRequest(BaseModel):
    recipe_id: int = Field(gt=0)
    liked: Optional[bool] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)


class MealSwapRequest(BaseModel):
    slot: str = Field(min_length=1)
    current_recipe_id: int = Field(gt=0)
    target_calories: Optional[float] = Field(default=None, ge=0)
    excluded_recipe_ids: list[int] = Field(default_factory=list)
