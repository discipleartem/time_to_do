"""Модель уведомлений для системы Time to DO."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Notification(BaseModel):
    """Модель уведомлений пользователей."""

    __tablename__ = "notifications"

    # Поля модели
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID пользователя",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Заголовок уведомления",
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Сообщение уведомления",
    )

    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Тип уведомления",
    )

    # Статус и метаданные
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Прочитано ли уведомление",
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время прочтения",
    )

    # Связанные сущности
    project_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="ID проекта",
    )

    task_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="ID задачи",
    )

    sprint_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sprints.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="ID спринта",
    )

    # Автор уведомления
    sender_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID отправителя",
    )

    # URL для перехода по клику на уведомление
    action_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL для действия",
    )

    # Метаданные для расширения функциональности
    metadata_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Метаданные в JSON",
    )

    # Отношения
    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")

    project = relationship("Project", back_populates="notifications")

    task = relationship("Task", back_populates="notifications")

    sprint = relationship("Sprint", back_populates="notifications")

    sender = relationship(
        "User",
        foreign_keys=[sender_id],
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
