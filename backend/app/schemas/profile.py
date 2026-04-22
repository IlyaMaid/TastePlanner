from uuid import UUID
from typing import Literal, Optional

from pydantic import BaseModel


class ProfileBase(BaseModel):
    sex: Optional[Literal["male", "female"]] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    goal: Optional[Literal["lose_weight", "maintain", "gain_weight"]] = None
    activity_level: Optional[Literal["low", "moderate", "high"]] = None
    region_code: Optional[str] = None
    daily_calorie_target: Optional[float] = None
    meals_per_day: Optional[int] = None


class ProfileUpdate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    user_id: UUID

    model_config = {"from_attributes": True}
