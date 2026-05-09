from typing import Any, Optional

from pydantic import BaseModel, Field


class RecommendationFeedbackRequest(BaseModel):
    recipe_id: int = Field(gt=0)
    liked: Optional[bool] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    reason: Optional[str] = Field(default=None, max_length=120)
    too_expensive: bool = False
    too_long: bool = False
    contains_disliked: bool = False
    too_many_calories: bool = False
    not_enough_calories: bool = False


class MealSwapRequest(BaseModel):
    slot: str = Field(min_length=1)
    current_recipe_id: int = Field(gt=0)
    target_calories: Optional[float] = Field(default=None, ge=0)
    excluded_recipe_ids: list[int] = Field(default_factory=list)
    mode: str = Field(default="balanced", pattern="^(balanced|cheaper|faster|lighter)$")


class UserEventRequest(BaseModel):
    event_type: str = Field(min_length=2, max_length=80)
    recipe_id: Optional[int] = Field(default=None, gt=0)
    payload_json: dict[str, Any] = Field(default_factory=dict)
