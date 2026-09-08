import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    return _create_token(
        data=data,
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=expires_delta,
    )


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    return _create_token(
        data=data,
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=expires_delta or timedelta(days=7),
    )


def _create_token(
    data: dict,
    token_type: str,
    expires_delta: timedelta | None = None,
) -> str:
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire, "type": token_type})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str):
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except JWTError:
        return None


def decode_access_token(token: str):
    payload = decode_token(token)
    if payload is None or payload.get("type") != ACCESS_TOKEN_TYPE:
        return None
    return payload


def decode_refresh_token(token: str):
    payload = decode_token(token)
    if payload is None or payload.get("type") != REFRESH_TOKEN_TYPE:
        return None
    return payload


def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
