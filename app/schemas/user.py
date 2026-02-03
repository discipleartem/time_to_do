"""
Схемы для пользователей
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.constants import EXAMPLE_PASSWORD


class UserBase(BaseModel):
    """Базовая схема пользователя"""

    email: EmailStr
    username: str | None = None
    full_name: str | None = None
    avatar_url: str | None = None
    is_active: bool = True
    role: str = Field(default="USER")


class UserCreate(UserBase):
    """Создание пользователя"""

    password: str = Field(..., min_length=8, max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "password": EXAMPLE_PASSWORD,
            }
        }
    )


class UserUpdate(BaseModel):
    """Обновление пользователя"""

    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None
    avatar_url: str | None = None
    is_active: bool | None = None
    role: str | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v):
        """Проверяет, что имя не пустое"""
        if v is not None and v.strip() == "":
            raise ValueError("Имя не может быть пустым")
        return v

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v):
        """Проверяет корректность URL"""
        if v is not None and v.strip() != "":
            from urllib.parse import urlparse

            parsed = urlparse(v)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Некорректный URL")
        return v


class UserInDB(UserBase):
    """Пользователь в базе данных"""

    id: str
    created_at: datetime
    updated_at: datetime
    is_verified: bool = False
    github_id: str | None = None
    github_username: str | None = None
    hashed_password: str | None = None


class User(UserBase):
    """Схема пользователя для API"""

    id: str
    created_at: datetime
    updated_at: datetime
    is_verified: bool
    github_id: str | None = None
    github_username: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Конвертирует UUID в строку"""
        return str(v) if v is not None else None


class UserProfile(User):
    """Профиль пользователя с дополнительной информацией"""

    project_count: int = 0
    task_count: int = 0
    completed_task_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class GitHubUserInfo(BaseModel):
    """Информация от GitHub OAuth"""

    id: int
    login: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    location: str | None = None
    company: str | None = None
    blog: str | None = None


class GitHubAuthRequest(BaseModel):
    """Запрос на аутентификацию через GitHub"""

    code: str
    state: str | None = None


class PublicUser(BaseModel):
    """Публичная информация о пользователе"""

    id: str
    username: str | None = None
    full_name: str | None = None
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)
