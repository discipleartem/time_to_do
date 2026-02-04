"""Модель уведомлений для системы Time to DO."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Notification(BaseModel):
    """Модель уведомлений пользователей."""

    __tablename__ = "notifications"

    # Поля модели
    user_id: UUID = Column(  # type: ignore[assignment]
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: str = Column(String(255), nullable=False)  # type: ignore[assignment]
    message: str = Column(Text, nullable=False)  # type: ignore[assignment]
    notification_type: str = Column(String(50), nullable=False, index=True)  # type: ignore[assignment]

    # Статус и метаданные
    is_read: bool = Column(Boolean, default=False, nullable=False, index=True)  # type: ignore[assignment]
    read_at: datetime | None = Column(DateTime(timezone=True))  # type: ignore[assignment]

    # Связанные сущности
    project_id: UUID | None = Column(  # type: ignore[assignment]
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    task_id: UUID | None = Column(  # type: ignore[assignment]
        Uuid(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    sprint_id: UUID | None = Column(  # type: ignore[assignment]
        Uuid(as_uuid=True),
        ForeignKey("sprints.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Автор уведомления
    sender_id: UUID | None = Column(  # type: ignore[assignment]
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # URL для перехода по клику на уведомление
    action_url: str | None = Column(String(500))  # type: ignore[assignment]

    # Метаданные для расширения функциональности
    metadata_json: str | None = Column(Text)  # type: ignore[assignment]

    # Временные метки
    created_at: datetime = Column(  # type: ignore[assignment]
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: datetime = Column(  # type: ignore[assignment]
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Отношения
    user = relationship(
        "User", foreign_keys="notifications.user_id", back_populates="notifications"
    )
    project = relationship("Project", back_populates="notifications")
    task = relationship("Task", back_populates="notifications")
    sprint = relationship("Sprint", back_populates="notifications")
    sender = relationship(
        "User",
        foreign_keys="notifications.sender_id",
        back_populates="sent_notifications",
    )

    def __repr__(self) -> str:
        """Строковое представление уведомления."""
        status = "прочитано" if self.is_read else "непрочитано"
        return f"Notification(id={self.id}, title='{self.title}', status={status})"

    def mark_as_read(self) -> None:
        """Отметить уведомление как прочитанное."""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()

    def mark_as_unread(self) -> None:
        """Отметить уведомление как непрочитанное."""
        self.is_read = False
        self.read_at = None

    @property
    def is_pending(self) -> bool:
        """Ожидает прочтения пользователем."""
        return not self.is_read

    @property
    def is_recent(self) -> bool:
        """Проверить, является ли уведомление недавним (менее 24 часов)."""
        if not self.created_at:
            return False
        return (datetime.now(UTC) - self.created_at).total_seconds() < 86400

    def to_dict(self) -> dict:
        """Преобразовать уведомление в словарь."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "project_id": str(self.project_id) if self.project_id else None,
            "task_id": str(self.task_id) if self.task_id else None,
            "sprint_id": str(self.sprint_id) if self.sprint_id else None,
            "action_url": self.action_url,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_recent": self.is_recent,
        }


# Константы для типов уведомлений
class NotificationType:
    """Типы уведомлений в системе."""

    # Задачи
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_OVERDUE = "task_overdue"
    TASK_MOVED = "task_moved"
    TASK_COMMENT_ADDED = "task_comment_added"

    # Проекты
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_MEMBER_ADDED = "project_member_added"
    PROJECT_MEMBER_REMOVED = "project_member_removed"

    # Спринты
    SPRINT_STARTED = "sprint_started"
    SPRINT_COMPLETED = "sprint_completed"
    SPRINT_TASK_ASSIGNED = "sprint_task_assigned"

    # Система
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    WELCOME = "welcome"
    DEADLINE_REMINDER = "deadline_reminder"

    @classmethod
    def get_all_types(cls) -> list[str]:
        """Получить список всех типов уведомлений."""
        return [
            value
            for key, value in cls.__dict__.items()
            if not key.startswith("_") and isinstance(value, str)
        ]

    @classmethod
    def is_valid_type(cls, notification_type: str) -> bool:
        """Проверить, является ли тип уведомления валидным."""
        return notification_type in cls.get_all_types()
