import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    generate_password_reset_token,
    hash_password,
    hash_password_reset_token,
    verify_password,
)
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.email import send_password_reset_email

router = APIRouter()
logger = logging.getLogger("tasteplanner.auth")


def build_token_response(user: User) -> Token:
    return Token(
        access_token=create_access_token(data={"sub": user.email}),
        refresh_token=create_refresh_token(data={"sub": user.email}),
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
def register(request: Request, user_data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует",
        )

    new_user = User(
        email=user_data.email,
        display_name=user_data.name,
        password_hash=hash_password(user_data.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return build_token_response(new_user)


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()

    if not user or not verify_password(user_data.password, str(user.password_hash)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    return build_token_response(user)


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
def login_for_docs(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    login_data = UserLogin(email=form_data.username, password=form_data.password)
    return login(request, login_data, db)


@router.post("/refresh", response_model=Token)
@limiter.limit("20/hour")
def refresh_tokens(
    request: Request,
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    token_payload = decode_refresh_token(payload.refresh_token)
    if token_payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh token",
        )

    email = token_payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    return build_token_response(user)


GENERIC_FORGOT_PASSWORD_MESSAGE = (
    "Если такой email зарегистрирован, мы отправили на него ссылку "
    "для восстановления пароля."
)


@router.post("/forgot-password")
@limiter.limit("5/hour")
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()

    if user is not None:
        raw_token = generate_password_reset_token()
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_password_reset_token(raw_token),
            expires_at=datetime.utcnow()
            + timedelta(minutes=settings.password_reset_token_expire_minutes),
        )
        db.add(reset_token)
        db.commit()

        reset_url = f"{settings.frontend_base_url}/reset-password?token={raw_token}"
        try:
            send_password_reset_email(user.email, reset_url)
        except Exception:
            logger.exception("Failed to send password reset email to %s", user.email)

    return {"message": GENERIC_FORGOT_PASSWORD_MESSAGE}


@router.post("/reset-password")
@limiter.limit("10/hour")
def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    token_hash = hash_password_reset_token(payload.token)
    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.utcnow(),
        )
        .first()
    )

    if reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ссылка для восстановления пароля недействительна или истекла",
        )

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ссылка для восстановления пароля недействительна или истекла",
        )

    user.password_hash = hash_password(payload.new_password)
    reset_token.used_at = datetime.utcnow()
    db.commit()

    return {"message": "Пароль успешно изменен"}
