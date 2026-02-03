"""
Схемы для задач и комментариев
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Для mypy - определяем Literal типы
TaskStatusLiteral = Literal["todo", "in_progress", "in_review", "done", "blocked"]
TaskPriorityLiteral = Literal["low", "medium", "high", "urgent"]
StoryPointLiteral = Literal["none", "1", "2", "3", "5", "8", "13", "21", "unknown"]


class TaskBase(BaseModel):
    """Базовая схема задачи"""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    status: str = Field(default="todo")
    priority: str = Field(default="medium")
    story_point: str = Field(default="unknown")
    due_date: str | None = None
    estimated_hours: int | None = Field(None, ge=0, le=40)
    parent_task_id: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Валидация заголовка задачи"""
        if not v or not v.strip():
            raise ValueError("Заголовок задачи не может быть пустым")
        if len(v.strip()) != len(v):
            raise ValueError(
                "Заголовок задачи не должен содержать только пробельные символы"
            )
        return v.strip()


class TaskCreate(TaskBase):
    """Создание задачи"""

    project_id: str
    assignee_id: str | None = None

    # @field_validator('project_id', 'assignee_id', mode='before')
    # @classmethod
    # def convert_str_to_uuid(cls, v):
    #     """Конвертирует строку в UUID"""
    #     if v is None:
    #         return None
    #     if isinstance(v, uuid.UUID):
    #         return v
    #     return uuid.UUID(str(v))

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Новая задача",
                "description": "Описание задачи",
                "status": "todo",
                "priority": "medium",
                "story_point": "5",
                "project_id": "uuid-project-id",
                "assignee_id": "uuid-user-id",
                "due_date": "2024-12-31",
                "estimated_hours": 8,
            }
        }
    )


class TaskUpdate(BaseModel):
    """Обновление задачи"""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    story_point: str | None = None
    assignee_id: str | None = None
    due_date: str | None = None
    estimated_hours: int | None = Field(None, ge=0)
    is_archived: bool | None = None


class TaskMove(BaseModel):
    """Перемещение задачи (для Kanban)"""

    status: str
    order: int | None = 0

    model_config = ConfigDict(
        json_schema_extra={"example": {"status": "in_progress", "order": 1}}
    )


class TaskReorder(BaseModel):
    """Изменение порядка задач"""

    order: int = Field(..., ge=0)

    model_config = ConfigDict(json_schema_extra={"example": {"order": 3}})


class Task(TaskBase):
    """Схема задачи для API"""

    id: str
    project_id: str
    creator_id: str
    assignee_id: str | None = None
    order: int = 0
    actual_hours: int = 0
    is_archived: bool = False
    story_points: int = 0  # Числовое значение Story Points
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "project_id", "creator_id", "assignee_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Конвертирует UUID в строку"""
        return str(v) if v is not None else None


class TaskWithDetails(Task):
    """Задача с дополнительной информацией"""

    project: dict[str, Any] | None = None
    creator: dict[str, Any] | None = None
    assignee: dict[str, Any] | None = None
    parent_task: dict[str, Any] | None = None
    subtasks: list[dict[str, Any]] = []
    comments_count: int = 0
    time_entries_count: int = 0
    total_time_spent: int = 0
    has_subtasks: bool = False
    completion_percentage: float = 0.0
    is_overdue: bool = False

    model_config = ConfigDict(from_attributes=True)


class CommentBase(BaseModel):
    """Базовая схема комментария"""

    content: str = Field(..., min_length=1)


class CommentCreate(CommentBase):
    """Создание комментария"""

    # task_id убрано, т.к. он берется из URL параметра

    model_config = ConfigDict(
        json_schema_extra={"example": {"content": "Текст комментария"}}
    )


class CommentUpdate(BaseModel):
    """Обновление комментария"""

    content: str = Field(..., min_length=1)


class Comment(CommentBase):
    """Схема комментария для API"""

    id: str
    task_id: str
    author_id: str
    is_edited: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "task_id", "author_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Конвертирует UUID в строку"""
        return str(v) if v is not None else None


class CommentWithDetails(Comment):
    """Комментарий с деталями автора"""

    author: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskBulkUpdate(BaseModel):
    """Массовое обновление задач"""

    task_ids: list[str] = Field(...)
    updates: TaskUpdate

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_ids": ["uuid-1", "uuid-2", "uuid-3"],
                "updates": {"status": "done", "priority": "low"},
            }
        }
    )


class TaskFilter(BaseModel):
    """Фильтры для задач"""

    status: str | None = None
    priority: str | None = None
    assignee_id: str | None = None
    creator_id: str | None = None
    story_point: str | None = None
    is_archived: bool | None = False
    due_date_from: str | None = None
    due_date_to: str | None = None
    search: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "in_progress",
                "priority": "high",
                "assignee_id": "uuid-user-id",
                "search": "критическая задача",
            }
        }
    )


class TaskStats(BaseModel):
    """Статистика по задачам"""

    total: int = 0
    todo: int = 0
    in_progress: int = 0
    in_review: int = 0
    done: int = 0
    blocked: int = 0
    overdue: int = 0

    model_config = ConfigDict(from_attributes=True)


class KanbanColumn(BaseModel):
    """Колонка Kanban доски"""

    status: str
    title: str
    tasks: list[TaskWithDetails] = []
    count: int = 0

    model_config = ConfigDict(from_attributes=True)


class KanbanBoard(BaseModel):
    """Kanban доска"""

    project_id: str
    project_name: str
    columns: list[KanbanColumn] = []
    total_tasks: int = 0

    model_config = ConfigDict(from_attributes=True)
