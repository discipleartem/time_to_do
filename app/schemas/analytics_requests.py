"""
Pydantic модели для валидации данных аналитики.

Следует Глобальным правилам:
- Type-safe (строгая типизация)
- Russian language для описаний
- Explicit > Implicit (явная валидация)
- Security (валидация на входе)
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, validator


class EventCreateRequest(BaseModel):
    """Запрос на создание события аналитики."""

    event_type: str = Field(..., description="Тип события", min_length=1, max_length=50)
    event_category: str = Field(
        ..., description="Категория события", min_length=1, max_length=50
    )
    entity_type: str | None = Field(None, description="Тип сущности", max_length=50)
    entity_id: UUID | None = Field(None, description="ID сущности")
    event_data: dict[str, Any] | None = Field(None, description="Данные события")
    session_id: str | None = Field(None, description="ID сессии", max_length=100)
    ip_address: str | None = Field(None, description="IP адрес", max_length=45)
    user_agent: str | None = Field(None, description="User Agent", max_length=500)

    @validator("event_type")
    def validate_event_type(cls, v: str) -> str:
        """Валидация типа события."""
        allowed_types = {
            "login",
            "logout",
            "task_created",
            "task_completed",
            "task_updated",
            "project_created",
            "project_updated",
            "sprint_created",
            "sprint_completed",
            "file_uploaded",
            "file_downloaded",
            "search_query",
            "dashboard_view",
        }
        if v not in allowed_types:
            raise ValueError(f"Недопустимый тип события. Разрешенные: {allowed_types}")
        return v

    @validator("event_category")
    def validate_event_category(cls, v: str) -> str:
        """Валидация категории события."""
        allowed_categories = {
            "user_action",
            "system_event",
            "business_metric",
            "ui_interaction",
        }
        if v not in allowed_categories:
            raise ValueError(
                f"Недопустимая категория. Разрешенные: {allowed_categories}"
            )
        return v


class MetricsQueryRequest(BaseModel):
    """Запрос на получение метрик."""

    metric_type: str = Field(..., description="Тип метрики")
    scope_type: Literal["global", "project", "user", "sprint"] = Field(
        ..., description="Тип области"
    )
    scope_id: UUID | None = Field(None, description="ID области")
    period_type: Literal["daily", "weekly", "monthly"] = Field(
        "daily", description="Тип периода"
    )
    start_date: datetime | None = Field(None, description="Начальная дата")
    end_date: datetime | None = Field(None, description="Конечная дата")
    filters: dict[str, Any] | None = Field(None, description="Фильтры")

    @validator("end_date")
    def validate_date_range(
        cls, v: datetime | None, values: dict[str, Any]
    ) -> datetime | None:
        """Валидация диапазона дат."""
        if v and "start_date" in values and values["start_date"]:
            if v <= values["start_date"]:
                raise ValueError("Конечная дата должна быть после начальной")
        return v

    @validator("scope_id")
    def validate_scope_id(cls, v: UUID | None, values: dict[str, Any]) -> UUID | None:
        """Валидация ID области."""
        if values.get("scope_type") in ["project", "user", "sprint"] and not v:
            raise ValueError("ID области обязателен для указанного типа области")
        return v


class DashboardWidgetConfig(BaseModel):
    """Конфигурация виджета дашборда."""

    id: str = Field(..., description="ID виджета", min_length=1, max_length=50)
    type: Literal["chart", "metric", "table", "text"] = Field(
        ..., description="Тип виджета"
    )
    title: str = Field(..., description="Заголовок", min_length=1, max_length=100)
    position: dict[str, int] = Field(..., description="Позиция (x, y, w, h)")
    config: dict[str, Any] = Field(..., description="Конфигурация виджета")
    refresh_interval: int | None = Field(
        None, description="Интервал обновления в секундах", ge=30
    )

    @validator("position")
    def validate_position(cls, v: dict[str, int]) -> dict[str, int]:
        """Валидация позиции виджета."""
        required_keys = {"x", "y", "w", "h"}
        if not all(key in v for key in required_keys):
            raise ValueError(f"Позиция должна содержать ключи: {required_keys}")

        if any(v[key] < 0 for key in ["x", "y", "w", "h"]):
            raise ValueError("Координаты и размеры должны быть положительными")

        return v


class DashboardCreateRequest(BaseModel):
    """Запрос на создание дашборда."""

    name: str = Field(
        ..., description="Название дашборда", min_length=1, max_length=200
    )
    description: str | None = Field(None, description="Описание", max_length=500)
    is_default: bool = Field(False, description="Дашборд по умолчанию")
    is_public: bool = Field(False, description="Публичный дашборд")
    layout_config: dict[str, Any] = Field(..., description="Конфигурация layout")
    widgets: list[DashboardWidgetConfig] = Field(..., description="Виджеты")
    filters: dict[str, Any] | None = Field(None, description="Фильтры")
    refresh_interval: int | None = Field(None, description="Интервал обновления", ge=30)

    @validator("widgets")
    def validate_widgets(
        cls, v: list[DashboardWidgetConfig]
    ) -> list[DashboardWidgetConfig]:
        """Валидация виджетов."""
        if len(v) == 0:
            raise ValueError("Дашборд должен содержать хотя бы один виджет")

        if len(v) > 20:
            raise ValueError("Дашборд не может содержать более 20 виджетов")

        # Проверка уникальности ID виджетов
        widget_ids = [widget.id for widget in v]
        if len(widget_ids) != len(set(widget_ids)):
            raise ValueError("ID виджетов должны быть уникальными")

        return v


class AnalyticsFilterRequest(BaseModel):
    """Запрос фильтрации данных аналитики."""

    event_types: list[str] | None = Field(None, description="Типы событий")
    event_categories: list[str] | None = Field(None, description="Категории событий")
    entity_types: list[str] | None = Field(None, description="Типы сущностей")
    user_ids: list[UUID] | None = Field(None, description="ID пользователей")
    project_ids: list[UUID] | None = Field(None, description="ID проектов")
    start_date: datetime | None = Field(None, description="Начальная дата")
    end_date: datetime | None = Field(None, description="Конечная дата")
    limit: int = Field(100, description="Лимит записей", ge=1, le=1000)

    @validator("limit")
    def validate_limit(cls, v: int) -> int:
        """Валидация лимита."""
        if v > 1000:
            raise ValueError("Лимит не может превышать 1000 записей")
        return v
