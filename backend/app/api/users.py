from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.profile import Profile
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/me/profile", response_model=ProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()

    if not profile:
        profile = Profile(user_id=current_user.id, updated_at=datetime.utcnow())
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile


@router.put("/me/profile", response_model=ProfileResponse)
def update_my_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()

    if not profile:
        profile = Profile(user_id=current_user.id, updated_at=datetime.utcnow())
        db.add(profile)

    for field, value in profile_data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    profile.updated_at = datetime.utcnow()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректные значения профиля для текущей схемы базы данных",
        )

    db.refresh(profile)
    return profile
