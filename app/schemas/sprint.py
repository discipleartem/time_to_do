"""
Схемы для SCRUM спринтов
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SprintBase(BaseModel):
    """Базовая схема спринта"""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    goal: str | None = None
    status: str = Field(default="planning")
    start_date: date | None = None
    end_date: date | None = None
    capacity_hours: int | None = Field(None, ge=0)
    velocity_points: int | None = Field(None, ge=0)


class SprintCreate(SprintBase):
    """Создание спринта"""

    project_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Sprint 1",
                "description": "Первый спринт проекта",
                "goal": "Реализовать базовый функционал",
                "project_id": "uuid-project-id",
                "start_date": "2024-01-01",
                "end_date": "2024-01-14",
                "capacity_hours": 80,
                "velocity_points": 20,
            }
        }
    )


class SprintUpdate(BaseModel):
    """Обновление спринта"""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    goal: str | None = None
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    capacity_hours: int | None = Field(None, ge=0)
    velocity_points: int | None = Field(None, ge=0)


class SprintStart(BaseModel):
    """Запуск спринта"""

    start_date: date
    end_date: date
    capacity_hours: int | None = Field(None, ge=0)
    velocity_points: int | None = Field(None, ge=0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-14",
                "capacity_hours": 80,
                "velocity_points": 20,
            }
        }
    )


class SprintComplete(BaseModel):
    """Завершение спринта"""

    completed_points: int | None = Field(None, ge=0)
    retrospective_notes: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "completed_points": 18,
                "retrospective_notes": "Хороший спринт, но нужно улучшить оценку задач",
            }
        }
    )


class Sprint(SprintBase):
    """Схема спринта для API"""

    id: str
    project_id: str
    completed_points: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SprintWithDetails(Sprint):
    """Спринт с дополнительной информацией"""

    project: dict[str, Any] | None = None
    duration_days: int = 0
    is_active: bool = False
    completion_percentage: float = 0.0
    task_count: int = 0
    completed_task_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SprintTaskBase(BaseModel):
    """Базовая схема задачи спринта"""

    order: int = 0
    is_added_mid_sprint: bool = False


class SprintTaskCreate(SprintTaskBase):
    """Добавление задачи в спринт"""

    task_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "uuid-task-id",
                "order": 1,
                "is_added_mid_sprint": False,
            }
        }
    )


class SprintTaskUpdate(BaseModel):
    """Обновление задачи в спринте"""

    order: int | None = Field(None, ge=0)
    is_added_mid_sprint: bool | None = None


class SprintTask(SprintTaskBase):
    """Схема задачи спринта для API"""

    id: str
    sprint_id: str
    task_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SprintTaskWithDetails(SprintTask):
    """Задача спринта с деталями"""

    task: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class SprintBulkTaskAdd(BaseModel):
    """Массовое добавление задач в спринт"""

    task_ids: list[str] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={"example": {"task_ids": ["uuid-1", "uuid-2", "uuid-3"]}}
    )


class SprintStats(BaseModel):
    """Статистика спринта"""

    total_tasks: int = 0
    completed_tasks: int = 0
    todo_tasks: int = 0
    in_progress_tasks: int = 0
    done_tasks: int = 0
    blocked_tasks: int = 0
    total_story_points: int = 0
    completed_story_points: int = 0
    remaining_story_points: int = 0
    completion_percentage: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class BurndownData(BaseModel):
    """Данные для burndown chart"""

    date: date
    ideal_remaining: float
    actual_remaining: float

    model_config = ConfigDict(from_attributes=True)


class SprintBurndown(BaseModel):
    """Burndown chart для спринта"""

    sprint_id: str
    sprint_name: str
    start_date: date
    end_date: date
    total_story_points: int = 0
    data: list[BurndownData] = []

    model_config = ConfigDict(from_attributes=True)


class VelocityData(BaseModel):
    """Данные о velocity команды"""

    sprint_number: int
    sprint_name: str
    planned_points: int
    completed_points: int
    completion_percentage: float

    model_config = ConfigDict(from_attributes=True)


class TeamVelocity(BaseModel):
    """Velocity команды"""

    project_id: str
    average_velocity: float = 0.0
    last_sprints: list[VelocityData] = []

    model_config = ConfigDict(from_attributes=True)
