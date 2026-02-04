"""
Модель публичных ссылок для External Sharing
"""

from datetime import UTC, datetime

# Импортируем для type hints, но избегаем циклических импортов
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class ShareableType(str):
    """Типы объектов для шаринга"""

    PROJECT = "project"
    TASK = "task"
    SPRINT = "sprint"


class SharePermission(str):
    """Уровни доступа для публичных ссылок"""

    VIEW = "view"  # Только просмотр
    COMMENT = "comment"  # Просмотр и комментарии


# Создаем ENUM для SQLAlchemy
ShareableTypeEnum = ENUM(
    ShareableType.PROJECT,
    ShareableType.TASK,
    ShareableType.SPRINT,
    name="shareabletype",
    create_type=True,
)

SharePermissionEnum = ENUM(
    SharePermission.VIEW,
    SharePermission.COMMENT,
    name="sharepermission",
    create_type=True,
)


class ShareLink(BaseModel):
    """Публичная ссылка для доступа к объектам системы"""

    __tablename__ = "share_links"

    # Основные поля
    token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    shareable_type: Mapped[str] = mapped_column(ShareableTypeEnum, nullable=False)
    shareable_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Настройки доступа
    permission: Mapped[str] = mapped_column(
        SharePermissionEnum, nullable=False, default=SharePermission.VIEW
    )
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Ограничения
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    max_views: Mapped[int | None] = mapped_column(nullable=True)
    current_views: Mapped[int] = mapped_column(default=0, nullable=False)

    # Статус
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Метаданные
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Отношения
    creator: Mapped["User"] = relationship("User", back_populates="created_share_links")

    @property
    def is_expired(self) -> bool:
        """Проверить, истекла ли ссылка."""
        if not self.expires_at:
            return False
        return datetime.now(UTC) > self.expires_at

    @property
    def is_view_limit_exceeded(self) -> bool:
        """Проверить, превышен ли лимит просмотров."""
        if not self.max_views:
            return False
        return self.current_views >= self.max_views

    @property
    def is_accessible(self) -> bool:
        """Проверить, доступна ли ссылка."""
        return (
            self.is_active and not self.is_expired and not self.is_view_limit_exceeded
        )

    def increment_views(self) -> None:
        """Увеличить счетчик просмотров."""
        self.current_views += 1

    def can_access(self, password: str | None = None) -> bool:
        """Проверить, можно ли получить доступ по ссылке."""
        if not self.is_accessible:
            return False

        if self.password and password != self.password:
            return False

        return True

    def get_public_url(self, base_url: str = "") -> str:
        """Получить публичную URL для ссылки."""
        return f"{base_url}/shared/{self.token}"

    def to_dict(self) -> dict:
        """Преобразовать в словарь."""
        return {
            "id": str(self.id),
            "token": self.token,
            "shareable_type": self.shareable_type,
            "shareable_id": str(self.shareable_id),
            "permission": self.permission,
            "has_password": bool(self.password),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "max_views": self.max_views,
            "current_views": self.current_views,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "is_view_limit_exceeded": self.is_view_limit_exceeded,
            "is_accessible": self.is_accessible,
            "title": self.title,
            "description": self.description,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "public_url": self.get_public_url(),
        }
