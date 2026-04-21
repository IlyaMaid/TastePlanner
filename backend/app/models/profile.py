from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    age = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)  # см
    weight = Column(Integer, nullable=True)  # кг
    gender = Column(String, nullable=True)   # male / female
    goal = Column(String, nullable=True)     # lose / maintain / gain
    activity_level = Column(String, nullable=True)  # low / medium / high

    user = relationship("User", backref="profile")