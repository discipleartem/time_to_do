"""
Схемы для аутентификации
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, EmailStr, field_validator

if TYPE_CHECKING:
    from app.schemas.user import User


def update_auth_forward_refs():
    """Обновляет forward references для auth схем"""
    # Импортируем User здесь для разрешения circular import
    from app.schemas.user import User

    # Обновляем forward references с правильным контекстом
    LoginResponse.model_rebuild(_types_namespace={"User": User})
    Token.model_rebuild()


class Token(BaseModel):
    """JWT токен"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Данные токена"""

    email: str | None = None
    user_id: str | None = None


class LoginRequest(BaseModel):
    """Запрос на вход"""

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Ответ на вход"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "User"


class RegisterRequest(BaseModel):
    """Запрос на регистрацию"""

    email: EmailStr
    password: str
    username: str | None = None
    full_name: str | None = None
    role: str | None = None  # Опциональное поле роли для тестов

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Валидация пароля"""
        if len(v) < 6:
            raise ValueError("Пароль должен содержать минимум 6 символов")
        if len(v) > 128:
            raise ValueError("Пароль не должен превышать 128 символов")
        return v


class RefreshTokenRequest(BaseModel):
    """Запрос на обновление токена"""

    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Запрос на сброс пароля"""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Подтверждение сброса пароля"""

    token: str
    new_password: str


class PasswordChange(BaseModel):
    """Изменение пароля"""

    current_password: str
    new_password: str
