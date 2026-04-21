from pydantic import BaseModel
from typing import Optional


class ProfileBase(BaseModel):
    age: Optional[int] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    gender: Optional[str] = None
    goal: Optional[str] = None
    activity_level: Optional[str] = None


class ProfileUpdate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True