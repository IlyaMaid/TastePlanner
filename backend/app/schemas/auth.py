import re
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

PASSWORD_LETTER_RE = re.compile(r"[A-Za-zА-Яа-яЁё]")
PASSWORD_DIGIT_RE = re.compile(r"\d")


class AuthCredentialsBase(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class UserRegister(AuthCredentialsBase):
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Введите имя")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        password = value.strip()
        if len(password) < 8:
            raise ValueError("Пароль должен быть не короче 8 символов")
        if not PASSWORD_LETTER_RE.search(password):
            raise ValueError("Пароль должен содержать хотя бы одну букву")
        if not PASSWORD_DIGIT_RE.search(password):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        return password


class UserLogin(AuthCredentialsBase):
    password: str = Field(min_length=1, max_length=128)

    @field_validator("password")
    @classmethod
    def normalize_password(cls, value: str) -> str:
        password = value.strip()
        if not password:
            raise ValueError("Введите пароль")
        return password


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str | None = None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    sub: str
    type: str
