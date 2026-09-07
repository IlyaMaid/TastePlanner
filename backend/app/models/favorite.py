from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.models import _legacy_stubs  # noqa: F401  (registers recipes FK target)


class FavoriteRecipe(Base):
    __tablename__ = "favorite_recipes"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    recipe_id = Column(
        BigInteger,
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
