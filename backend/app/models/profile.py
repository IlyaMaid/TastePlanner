from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Profile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    sex = Column(Text, nullable=True)
    age = Column(Integer, nullable=True)
    height_cm = Column(Numeric, nullable=True)
    weight_kg = Column(Numeric, nullable=True)
    activity_level = Column(Text, nullable=True)
    goal = Column(Text, nullable=True)
    region_code = Column(Text, nullable=True)
    daily_calorie_target = Column(Numeric, nullable=True)
    daily_budget_rub = Column(Numeric, nullable=True)
    weekly_budget_rub = Column(Numeric, nullable=True)
    meals_per_day = Column(Integer, nullable=True)
    favorite_products_json = Column(JSONB, nullable=False, default=list)
    disliked_products_json = Column(JSONB, nullable=False, default=list)
    allergies_json = Column(JSONB, nullable=False, default=list)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
