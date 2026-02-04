"""
Pydantic схемы для публичных ссылок
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SharePermission(str, Enum):
    """Уровни доступа для публичных ссылок"""

    VIEW = "view"
    COMMENT = "comment"


class ShareableType(str, Enum):
    """Типы объектов для шаринга"""

    PROJECT = "project"
    TASK = "task"
    SPRINT = "sprint"


class ShareLinkBase(BaseModel):
    """Базовая схема публичной ссылки."""

    title: str | None = Field(None, max_length=255, description="Заголовок ссылки")
    description: str | None = Field(None, description="Описание ссылки")
    permission: SharePermission = Field(
        default=SharePermission.VIEW, description="Уровень доступа"
    )
    password: str | None = Field(None, max_length=255, description="Пароль для доступа")
    expires_at: datetime | None = Field(None, description="Время истечения ссылки")
    max_views: int | None = Field(
        None, ge=1, description="Максимальное количество просмотров"
    )

    @field_validator("permission")
    @classmethod
    def validate_permission(cls, v: str) -> str:
        """Валидация уровня доступа."""
        if v not in [SharePermission.VIEW, SharePermission.COMMENT]:
            raise ValueError(
                f"Уровень доступа должен быть одним из: {SharePermission.VIEW}, {SharePermission.COMMENT}"
            )
        return v


class ShareLinkCreate(ShareLinkBase):
    """Схема для создания публичной ссылки."""

    shareable_type: ShareableType = Field(..., description="Тип объекта")
    shareable_id: UUID = Field(..., description="ID объекта")


class ShareLinkUpdate(BaseModel):
    """Схема для обновления публичной ссылки."""

    title: str | None = Field(None, max_length=255)
    description: str | None = Field(None)
    permission: SharePermission | None = Field(None)
    password: str | None = Field(None, max_length=255)
    expires_at: datetime | None = Field(None)
    max_views: int | None = Field(None, ge=1)
    is_active: bool | None = Field(None, description="Активность ссылки")


class ShareLinkResponse(ShareLinkBase):
    """Схема ответа с информацией о публичной ссылке."""

    id: UUID = Field(..., description="ID ссылки")
    token: str = Field(..., description="Токен доступа")
    shareable_type: ShareableType = Field(..., description="Тип объекта")
    shareable_id: UUID = Field(..., description="ID объекта")
    current_views: int = Field(..., description="Текущее количество просмотров")
    is_active: bool = Field(..., description="Активность ссылки")
    created_by: UUID = Field(..., description="ID создателя")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")
    public_url: str = Field(..., description="Публичный URL")
    is_expired: bool = Field(..., description="Истекла ли ссылка")
    is_view_limit_exceeded: bool = Field(
        ..., description="Превышен ли лимит просмотров"
    )
    is_accessible: bool = Field(..., description="Доступна ли ссылка")
    has_password: bool = Field(..., description="Требуется ли пароль")


class ShareLinkAccess(BaseModel):
    """Схема для доступа к публичной ссылке."""

    token: str = Field(..., description="Токен ссылки")
    password: str | None = Field(None, description="Пароль (если требуется)")


class ShareLinkStats(BaseModel):
    """Статистика публичной ссылки."""

    total_links: int = Field(..., description="Всего ссылок")
    active_links: int = Field(..., description="Активных ссылок")
    expired_links: int = Field(..., description="Истекших ссылок")
    total_views: int = Field(..., description="Всего просмотров")
    most_viewed: list[ShareLinkResponse] = Field(
        ..., description="Самые просматриваемые"
    )


class SharedContentResponse(BaseModel):
    """Ответ с контентом по публичной ссылке."""

    share_link: ShareLinkResponse = Field(..., description="Информация о ссылке")
    content: dict = Field(..., description="Контент объекта")
    can_comment: bool = Field(..., description="Можно ли оставлять комментарии")
    access_granted: bool = Field(..., description="Предоставлен ли доступ")
