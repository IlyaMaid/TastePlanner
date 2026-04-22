from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID

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
    meals_per_day = Column(Integer, nullable=True)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
