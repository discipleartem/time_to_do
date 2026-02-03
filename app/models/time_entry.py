"""
Модель для отслеживания времени
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class TimeEntry(BaseModel):
    """Модель записи времени"""

    __tablename__ = "time_entries"

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Описание работы",
    )

    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),  # Добавляем поддержку timezone
        nullable=True,
        comment="Время начала",
    )

    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),  # Добавляем поддержку timezone
        nullable=True,
        comment="Время окончания",
    )

    duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Длительность в минутах",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Активна ли запись",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="ID пользователя",
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id"),
        nullable=False,
        comment="ID задачи",
    )

    # Отношения
    user = relationship(
        "User",
        back_populates="time_entries",
    )

    task = relationship(
        "Task",
        back_populates="time_entries",
    )

    def __repr__(self) -> str:
        return f"<TimeEntry(user_id={self.user_id}, task_id={self.task_id}, duration={self.duration_minutes})>"

    @property
    def duration_hours(self) -> float:
        """Длительность в часах"""
        if self.duration_minutes is None:
            return 0.0
        return self.duration_minutes / 60.0  # type: ignore

    @property
    def formatted_duration(self) -> str:
        """Форматированная длительность"""
        if self.duration_minutes is None:
            return "00:00"

        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    def stop_timer(self) -> None:
        """Остановить таймер"""
        if self.is_active and self.end_time is None:
            from datetime import datetime

            self.end_time = datetime.now(UTC)
            if self.start_time:
                duration = self.end_time - self.start_time
                self.duration_minutes = int(duration.total_seconds() / 60)
            self.is_active = False
