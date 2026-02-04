"""
Модели SCRUM спринтов
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class SprintStatus(str):
    """Статусы спринта"""

    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Создаем ENUM для SQLAlchemy
SprintStatusEnum = ENUM(
    SprintStatus.PLANNING,
    SprintStatus.ACTIVE,
    SprintStatus.COMPLETED,
    SprintStatus.CANCELLED,
    name="sprintstatus",
    create_type=True,  # Создаем тип автоматически
)


class Sprint(BaseModel):
    """Модель спринта"""

    __tablename__ = "sprints"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Название спринта",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Описание спринта",
    )

    goal: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Цель спринта",
    )

    status: Mapped[SprintStatus] = mapped_column(
        SprintStatusEnum,
        default=SprintStatus.PLANNING,
        nullable=False,
        comment="Статус спринта",
    )

    start_date: Mapped[datetime | None] = mapped_column(
        Date,
        nullable=True,
        comment="Дата начала спринта",
    )

    end_date: Mapped[datetime | None] = mapped_column(
        Date,
        nullable=True,
        comment="Дата окончания спринта",
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False,
        comment="ID проекта",
    )

    capacity_hours: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Емкость спринта в часах",
    )

    velocity_points: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Планируемая скорость в Story Points",
    )

    completed_points: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Выполненные Story Points",
    )

    # Отношения
    project = relationship(
        "Project",
        back_populates="sprints",
    )

    sprint_tasks = relationship(
        "SprintTask",
        back_populates="sprint",
        cascade="all, delete-orphan",
    )

    notifications = relationship(
        "Notification",
        back_populates="sprint",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Sprint(name={self.name}, status={self.status})>"

    @property
    def duration_days(self) -> int:
        """Длительность спринта в днях"""
        if not self.start_date or not self.end_date:
            return 0
        return (self.end_date - self.start_date).days + 1

    @property
    def is_active(self) -> bool:
        """Активен ли спринт"""
        return self.status == SprintStatus.ACTIVE

    @property
    def completion_percentage(self) -> float:
        """Процент выполнения спринта"""
        if self.velocity_points is None or self.velocity_points == 0:
            return 0.0
        return (self.completed_points / self.velocity_points) * 100

    @property
    def task_count(self) -> int:
        """Количество задач в спринте"""
        return len(self.sprint_tasks)

    @property
    def completed_task_count(self) -> int:
        """Количество выполненных задач в спринте"""
        return len([st for st in self.sprint_tasks if st.task.status == "done"])


class SprintTask(BaseModel):
    """Связь между спринтом и задачей"""

    __tablename__ = "sprint_tasks"

    sprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sprints.id"),
        nullable=False,
        comment="ID спринта",
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id"),
        nullable=False,
        comment="ID задачи",
    )

    order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Порядок задачи в спринте",
    )

    is_added_mid_sprint: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Добавлена ли задача в середине спринта",
    )

    # Отношения
    sprint = relationship(
        "Sprint",
        back_populates="sprint_tasks",
    )

    task = relationship(
        "Task",
        back_populates="sprint_tasks",
    )

    def __repr__(self) -> str:
        return f"<SprintTask(sprint_id={self.sprint_id}, task_id={self.task_id})>"
