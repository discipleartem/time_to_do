"""
Схемы для отслеживания времени
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TimeEntryBase(BaseModel):
    """Базовая схема записи времени"""

    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_minutes: int | None = Field(None, ge=0)
    is_active: bool = False


class TimeEntryCreate(TimeEntryBase):
    """Создание записи времени"""

    task_id: str

    # @field_validator('task_id', mode='before')
    # @classmethod
    # def convert_str_to_uuid(cls, v):
    #     """Конвертирует строку в UUID"""
    #     if v is None:
    #         return None
    #     if isinstance(v, uuid.UUID):
    #         return v
    #     return uuid.UUID(str(v))

    @model_validator(mode="after")
    def validate_time_fields(self):
        """Проверяет, что указаны либо start_time+end_time, либо duration_minutes, либо только start_time для таймера"""
        data = self.model_dump()

        start_time = data.get("start_time")
        end_time = data.get("end_time")
        duration_minutes = data.get("duration_minutes")

        has_times = start_time is not None and end_time is not None
        has_duration = duration_minutes is not None
        has_start_only = (
            start_time is not None and end_time is None and duration_minutes is None
        )

        if not (has_times or has_duration or has_start_only):
            raise ValueError(
                "Необходимо указать либо start_time и end_time, либо duration_minutes, либо только start_time для таймера"
            )

        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Работа над функцией X",
                "task_id": "uuid-task-id",
                "start_time": "2024-01-01T10:00:00Z",
                "end_time": "2024-01-01T12:00:00Z",
                "duration_minutes": 120,
            }
        }
    )


class TimeEntryUpdate(BaseModel):
    """Обновление записи времени"""

    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_minutes: int | None = Field(None, ge=0)


class TimeEntryManualCreate(BaseModel):
    """Создание записи времени вручную"""

    task_id: str
    description: str | None = None
    duration_minutes: int = Field(..., gt=0)
    date: str = Field(..., description="Дата в формате YYYY-MM-DD")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "uuid-task-id",
                "description": "Анализ требований",
                "duration_minutes": 90,
                "date": "2024-01-01",
            }
        }
    )


class TimeEntryStart(BaseModel):
    """Запуск таймера"""

    task_id: str
    description: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "uuid-task-id",
                "description": "Начинаю работу над задачей",
            }
        }
    )


class TimeEntryStop(BaseModel):
    """Остановка таймера"""

    description: str | None = None

    model_config = ConfigDict(
        json_schema_extra={"example": {"description": "Завершил работу над функцией"}}
    )


class TimeEntry(TimeEntryBase):
    """Схема записи времени для API"""

    id: str
    user_id: str
    task_id: str
    created_at: datetime
    updated_at: datetime

    @field_validator("id", "user_id", "task_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Конвертирует UUID в строку"""
        return str(v) if v is not None else None

    model_config = ConfigDict(from_attributes=True)


class TimeEntryWithDetails(TimeEntry):
    """Запись времени с дополнительной информацией"""

    user: dict[str, Any] | None = None
    task: dict[str, Any] | None = None
    duration_hours: float = 0.0
    formatted_duration: str = "00:00"

    model_config = ConfigDict(from_attributes=True)


class ActiveTimer(BaseModel):
    """Активный таймер пользователя"""

    id: str
    task_id: str
    task_title: str
    description: str | None = None
    start_time: datetime
    duration_minutes: int

    model_config = ConfigDict(from_attributes=True)


class TimeEntryFilter(BaseModel):
    """Фильтры для записей времени"""

    task_id: str | None = None
    user_id: str | None = None
    project_id: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    is_active: bool | None = None
    search: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date_from": "2024-01-01",
                "date_to": "2024-01-31",
                "task_id": "uuid-task-id",
                "search": "функция X",
            }
        }
    )


class TimeStats(BaseModel):
    """Статистика по времени"""

    total_minutes: int = 0
    total_hours: float = 0.0
    total_entries: int = 0
    active_entries: int = 0
    average_session_minutes: float = 0.0
    formatted_total_time: str = "00:00"

    model_config = ConfigDict(from_attributes=True)


class DailyTimeStats(BaseModel):
    """Ежедневная статистика времени"""

    date: str
    total_minutes: int = 0
    total_hours: float = 0.0
    entries_count: int = 0
    formatted_time: str = "00:00"

    model_config = ConfigDict(from_attributes=True)


class TaskTimeStats(BaseModel):
    """Статистика времени по задаче"""

    task_id: str
    task_title: str
    total_minutes: int = 0
    total_hours: float = 0.0
    entries_count: int = 0
    formatted_time: str = "00:00"
    last_worked_on: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectTimeStats(BaseModel):
    """Статистика времени по проекту"""

    project_id: str
    project_name: str
    total_minutes: int = 0
    total_hours: float = 0.0
    entries_count: int = 0
    tasks_count: int = 0
    formatted_time: str = "00:00"

    model_config = ConfigDict(from_attributes=True)


class UserTimeStats(BaseModel):
    """Статистика времени пользователя"""

    user_id: str
    total_minutes: int = 0
    total_hours: float = 0.0
    entries_count: int = 0
    active_timer: ActiveTimer | None = None
    today_minutes: int = 0
    this_week_minutes: int = 0
    this_month_minutes: int = 0

    model_config = ConfigDict(from_attributes=True)


class TimeReport(BaseModel):
    """Отчет по времени"""

    period: str
    date_from: str
    date_to: str
    total_stats: TimeStats
    daily_stats: list[DailyTimeStats] = []
    task_stats: list[TaskTimeStats] = []
    project_stats: list[ProjectTimeStats] = []

    model_config = ConfigDict(from_attributes=True)
