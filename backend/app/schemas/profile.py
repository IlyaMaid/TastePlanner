from uuid import UUID
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProfileBase(BaseModel):
    sex: Optional[Literal["male", "female"]] = None
    age: Optional[int] = Field(default=None, ge=0, le=120)
    height_cm: Optional[float] = Field(default=None, ge=0)
    weight_kg: Optional[float] = Field(default=None, ge=0)
    goal: Optional[Literal["lose_weight", "maintain", "gain_weight"]] = None
    activity_level: Optional[Literal["low", "moderate", "high"]] = None
    region_code: Optional[str] = None
    daily_calorie_target: Optional[float] = Field(default=None, ge=0)
    daily_budget_rub: Optional[float] = Field(default=None, ge=0)
    weekly_budget_rub: Optional[float] = Field(default=None, ge=0)
    meals_per_day: Optional[int] = Field(default=None, ge=1, le=6)
    favorite_products_json: list[str] = Field(default_factory=list)
    disliked_products_json: list[str] = Field(default_factory=list)
    allergies_json: list[str] = Field(default_factory=list)


class ProfileUpdate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    user_id: UUID

    model_config = {"from_attributes": True}
