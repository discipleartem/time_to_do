"""
Модели задач и комментариев
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class TaskStatus(str):
    """Статусы задач"""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"


class TaskPriority(str):
    """Приоритеты задач"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class StoryPoint(str):
    """Story Points для оценки задач"""

    ONE = "1"
    TWO = "2"
    THREE = "3"
    FIVE = "5"
    EIGHT = "8"
    THIRTEEN = "13"
    TWENTY_ONE = "21"
    UNKNOWN = "unknown"


# Создаем ENUM для SQLAlchemy
TaskStatusEnum = ENUM(
    TaskStatus.TODO,
    TaskStatus.IN_PROGRESS,
    TaskStatus.IN_REVIEW,
    TaskStatus.DONE,
    TaskStatus.BLOCKED,
    name="taskstatus",
    create_type=True,  # Создаем тип автоматически
)

TaskPriorityEnum = ENUM(
    TaskPriority.LOW,
    TaskPriority.MEDIUM,
    TaskPriority.HIGH,
    TaskPriority.URGENT,
    name="taskpriority",
    create_type=True,  # Создаем тип автоматически
)

StoryPointEnum = ENUM(
    StoryPoint.ONE,
    StoryPoint.TWO,
    StoryPoint.THREE,
    StoryPoint.FIVE,
    StoryPoint.EIGHT,
    StoryPoint.THIRTEEN,
    StoryPoint.TWENTY_ONE,
    StoryPoint.UNKNOWN,
    name="storypoint",
    create_type=True,  # Создаем тип автоматически
)


class Task(BaseModel):
    """Модель задачи"""

    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Название задачи",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Описание задачи",
    )

    status: Mapped[TaskStatus] = mapped_column(
        TaskStatusEnum,
        default=TaskStatus.TODO,
        nullable=False,
        comment="Статус задачи",
    )

    priority: Mapped[TaskPriority] = mapped_column(
        TaskPriorityEnum,
        default=TaskPriority.MEDIUM,
        nullable=False,
        comment="Приоритет задачи",
    )

    story_point: Mapped[StoryPoint] = mapped_column(
        StoryPointEnum,
        default=StoryPoint.UNKNOWN,
        nullable=False,
        comment="Оценка в Story Points",
    )

    order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Порядок в колонке Kanban",
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False,
        comment="ID проекта",
    )

    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="ID создателя задачи",
    )

    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="ID исполнителя задачи",
    )

    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id"),
        nullable=True,
        comment="ID родительской задачи",
    )

    due_date: Mapped[str | None] = mapped_column(
        String(20),  # ISO date string
        nullable=True,
        comment="Срок выполнения",
    )

    estimated_hours: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Оценка времени в часах",
    )

    actual_hours: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Фактическое время в часах",
    )

    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Архивирована ли задача",
    )

    # Отношения
    project = relationship(
        "Project",
        back_populates="tasks",
    )

    creator = relationship(
        "User",
        foreign_keys=[creator_id],
        back_populates="created_tasks",
    )

    assignee = relationship(
        "User",
        foreign_keys=[assignee_id],
        back_populates="assigned_tasks",
    )

    parent_task = relationship(
        "Task",
        remote_side="Task.id",
        backref="subtasks",
    )

    comments = relationship(
        "Comment",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    time_entries = relationship(
        "TimeEntry",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    sprint_tasks = relationship(
        "SprintTask",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Task(title={self.title}, status={self.status})>"

    @property
    def has_subtasks(self) -> bool:
        """Есть ли подзадачи"""
        # Используем backref relationship для mypy
        subtasks = getattr(self, "subtasks", [])
        return len(subtasks) > 0

    @property
    def completion_percentage(self) -> float:
        """Процент выполнения"""
        if not self.has_subtasks:
            return 100.0 if self.status == TaskStatus.DONE else 0.0

        completed_subtasks = sum(
            1
            for subtask in getattr(self, "subtasks", [])
            if subtask.status == TaskStatus.DONE
        )
        subtasks_list = getattr(self, "subtasks", [])
        return (completed_subtasks / len(subtasks_list)) * 100 if subtasks_list else 0.0

    @property
    def is_overdue(self) -> bool:
        """Просрочена ли задача"""
        if not self.due_date or self.status == TaskStatus.DONE:
            return False
        # TODO: добавить проверку даты
        return False


class Comment(BaseModel):
    """Модель комментария к задаче"""

    __tablename__ = "comments"

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Содержание комментария",
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id"),
        nullable=False,
        comment="ID задачи",
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="ID автора",
    )

    is_edited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Отредактирован ли комментарий",
    )

    # Отношения
    task = relationship(
        "Task",
        back_populates="comments",
    )

    author = relationship(
        "User",
        back_populates="comments",
    )

    def __repr__(self) -> str:
        return f"<Comment(task_id={self.task_id}, author_id={self.author_id})>"
