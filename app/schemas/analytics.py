"""
Pydantic схемы для системы аналитики
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AnalyticsEventBase(BaseModel):
    """Базовая схема события аналитики"""

    event_type: str = Field(..., description="Тип события")
    event_category: str = Field(..., description="Категория события")
    entity_type: str | None = Field(None, description="Тип сущности")
    entity_id: UUID | None = Field(None, description="ID сущности")
    event_data: dict[str, Any] | None = Field(None, description="Данные события")
    session_id: str | None = Field(None, description="ID сессии")
    ip_address: str | None = Field(None, description="IP адрес")
    user_agent: str | None = Field(None, description="User Agent")


class AnalyticsEventCreate(AnalyticsEventBase):
    """Схема создания события аналитики"""

    pass


class AnalyticsEvent(AnalyticsEventBase):
    """Полная схема события аналитики"""

    id: UUID = Field(..., description="ID события")
    user_id: UUID | None = Field(None, description="ID пользователя")
    timestamp: datetime = Field(..., description="Время события")

    class Config:
        from_attributes = True


class ProjectMetricsBase(BaseModel):
    """Базовая схема метрик проекта"""

    project_id: UUID = Field(..., description="ID проекта")
    date: datetime = Field(..., description="Дата метрик")
    period_type: str = Field(..., description="Тип периода (daily/weekly/monthly)")
    total_tasks: int = Field(0, description="Всего задач")
    completed_tasks: int = Field(0, description="Выполненных задач")
    new_tasks: int = Field(0, description="Новых задач")
    total_time_logged: int = Field(0, description="Общее время в секундах")
    average_task_duration: int | None = Field(
        None, description="Средняя длительность задачи"
    )
    active_users: int = Field(0, description="Активных пользователей")
    comments_count: int = Field(0, description="Комментариев")
    files_uploaded: int = Field(0, description="Загруженных файлов")
    custom_metrics: dict[str, Any] | None = Field(
        None, description="Дополнительные метрики"
    )


class ProjectMetrics(ProjectMetricsBase):
    """Полная схема метрик проекта"""

    id: UUID = Field(..., description="ID метрик")
    created_at: datetime = Field(..., description="Время создания")

    class Config:
        from_attributes = True


class UserMetricsBase(BaseModel):
    """Базовая схема метрик пользователя"""

    user_id: UUID = Field(..., description="ID пользователя")
    date: datetime = Field(..., description="Дата метрик")
    period_type: str = Field(..., description="Тип периода (daily/weekly/monthly)")
    tasks_completed: int = Field(0, description="Выполненных задач")
    tasks_created: int = Field(0, description="Созданных задач")
    time_logged: int = Field(0, description="Время работы в секундах")
    login_count: int = Field(0, description="Количество логинов")
    comments_posted: int = Field(0, description="Комментариев")
    files_uploaded: int = Field(0, description="Загруженных файлов")
    projects_active: int = Field(0, description="Активных проектов")
    sprints_participated: int = Field(0, description="Участий в спринтах")
    custom_metrics: dict[str, Any] | None = Field(
        None, description="Дополнительные метрики"
    )


class UserMetrics(UserMetricsBase):
    """Полная схема метрик пользователя"""

    id: UUID = Field(..., description="ID метрик")
    created_at: datetime = Field(..., description="Время создания")

    class Config:
        from_attributes = True


class SprintMetricsBase(BaseModel):
    """Базовая схема метрик спринта"""

    sprint_id: UUID = Field(..., description="ID спринта")
    planned_story_points: int = Field(0, description="Запланированные story points")
    completed_story_points: int = Field(0, description="Выполненные story points")
    velocity: float | None = Field(None, description="Velocity")
    total_tasks: int = Field(0, description="Всего задач")
    completed_tasks: int = Field(0, description="Выполненных задач")
    incomplete_tasks: int = Field(0, description="Невыполненных задач")
    planned_duration: int = Field(0, description="Планируемая длительность в днях")
    actual_duration: int | None = Field(
        None, description="Фактическая длительность в днях"
    )
    on_time_completion: bool | None = Field(None, description="Завершено вовремя")
    team_size: int = Field(0, description="Размер команды")
    average_task_completion_time: float | None = Field(
        None, description="Среднее время выполнения задачи"
    )
    burndown_data: dict[str, Any] | None = Field(None, description="Данные burndown")
    retrospective_summary: dict[str, Any] | None = Field(
        None, description="Сводка ретроспективы"
    )


class SprintMetrics(SprintMetricsBase):
    """Полная схема метрик спринта"""

    id: UUID = Field(..., description="ID метрик")
    created_at: datetime = Field(..., description="Время создания")

    class Config:
        from_attributes = True


class AnalyticsReportBase(BaseModel):
    """Базовая схема отчета аналитики"""

    name: str = Field(..., description="Название отчета")
    description: str | None = Field(None, description="Описание")
    report_type: str = Field(..., description="Тип отчета")
    scope_type: str = Field(..., description="Тип области (global/project/user)")
    scope_id: UUID | None = Field(None, description="ID области")
    filters: dict[str, Any] | None = Field(None, description="Фильтры")
    date_range: dict[str, Any] | None = Field(None, description="Диапазон дат")
    metrics_config: dict[str, Any] | None = Field(
        None, description="Конфигурация метрик"
    )
    is_public: bool = Field(False, description="Публичный отчет")
    is_scheduled: bool = Field(False, description="Запланированный отчет")
    schedule_config: dict[str, Any] | None = Field(
        None, description="Конфигурация расписания"
    )


class AnalyticsReportCreate(AnalyticsReportBase):
    """Схема создания отчета"""

    report_data: dict[str, Any] = Field(..., description="Данные отчета")
    data_summary: dict[str, Any] | None = Field(None, description="Сводка данных")


class AnalyticsReport(AnalyticsReportBase):
    """Полная схема отчета"""

    id: UUID = Field(..., description="ID отчета")
    report_data: dict[str, Any] = Field(..., description="Данные отчета")
    data_summary: dict[str, Any] | None = Field(None, description="Сводка данных")
    created_by: UUID | None = Field(None, description="ID создателя")
    generated_at: datetime = Field(..., description="Время генерации")
    expires_at: datetime | None = Field(None, description="Время истечения")
    last_accessed: datetime | None = Field(None, description="Последний доступ")
    access_count: int = Field(0, description="Количество доступов")

    class Config:
        from_attributes = True


class DashboardBase(BaseModel):
    """Базовая схема дашборда"""

    name: str = Field(..., description="Название дашборда")
    description: str | None = Field(None, description="Описание")
    is_default: bool = Field(False, description="Дашборд по умолчанию")
    is_public: bool = Field(False, description="Публичный дашборд")
    layout_config: dict[str, Any] = Field(..., description="Конфигурация layout")
    widgets: dict[str, Any] = Field(..., description="Виджеты")
    filters: dict[str, Any] | None = Field(None, description="Фильтры")
    refresh_interval: int | None = Field(
        None, description="Интервал обновления в секундах"
    )


class DashboardCreate(DashboardBase):
    """Схема создания дашборда"""

    pass


class Dashboard(DashboardBase):
    """Полная схема дашборда"""

    id: UUID = Field(..., description="ID дашборда")
    user_id: UUID = Field(..., description="ID пользователя")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")
    last_viewed: datetime | None = Field(None, description="Последний просмотр")
    view_count: int = Field(0, description="Количество просмотров")

    class Config:
        from_attributes = True


class DashboardUpdate(BaseModel):
    """Схема обновления дашборда"""

    name: str | None = Field(None, description="Название")
    description: str | None = Field(None, description="Описание")
    layout_config: dict[str, Any] | None = Field(
        None, description="Конфигурация layout"
    )
    widgets: dict[str, Any] | None = Field(None, description="Виджеты")
    filters: dict[str, Any] | None = Field(None, description="Фильтры")
    refresh_interval: int | None = Field(None, description="Интервал обновления")


# === Схемы для API ответов ===


class ProjectSummary(BaseModel):
    """Сводка по проекту"""

    project: dict[str, Any] = Field(..., description="Информация о проекте")
    tasks: dict[str, Any] = Field(..., description="Статистика задач")
    users: dict[str, Any] = Field(..., description="Статистика пользователей")
    metrics: list[dict[str, Any]] = Field(..., description="Метрики за период")


class UserSummary(BaseModel):
    """Сводка по пользователю"""

    user: dict[str, Any] = Field(..., description="Информация о пользователе")
    tasks: dict[str, Any] = Field(..., description="Статистика задач")
    projects: dict[str, Any] = Field(..., description="Статистика проектов")
    metrics: list[dict[str, Any]] = Field(..., description="Метрики за период")


class AnalyticsQuery(BaseModel):
    """Запрос к аналитике"""

    metric_type: str = Field(..., description="Тип метрики")
    scope_type: str = Field(..., description="Тип области")
    scope_id: UUID | None = Field(None, description="ID области")
    period_type: str = Field("daily", description="Тип периода")
    start_date: datetime | None = Field(None, description="Начальная дата")
    end_date: datetime | None = Field(None, description="Конечная дата")
    filters: dict[str, Any] | None = Field(None, description="Фильтры")


class AnalyticsResponse(BaseModel):
    """Ответ аналитики"""

    data: list[dict[str, Any]] = Field(..., description="Данные аналитики")
    summary: dict[str, Any] | None = Field(None, description="Сводка")
    metadata: dict[str, Any] = Field(..., description="Метаданные")


class WidgetConfig(BaseModel):
    """Конфигурация виджета"""

    id: str = Field(..., description="ID виджета")
    type: str = Field(..., description="Тип виджета")
    title: str = Field(..., description="Заголовок")
    position: dict[str, int] = Field(..., description="Позиция (x, y, w, h)")
    config: dict[str, Any] = Field(..., description="Конфигурация виджета")
    refresh_interval: int | None = Field(None, description="Интервал обновления")


class DashboardLayout(BaseModel):
    """Layout дашборда"""

    cols: int = Field(12, description="Количество колонок")
    rows: int = Field(8, description="Количество строк")
    gap: int = Field(1, description="Отступ")
    widgets: list[WidgetConfig] = Field(..., description="Виджеты")


# === Схемы для популярных типов виджетов ===


class ChartWidgetConfig(BaseModel):
    """Конфигурация виджета-графика"""

    chart_type: str = Field(..., description="Тип графика (line/bar/pie)")
    data_source: str = Field(..., description="Источник данных")
    x_axis: str = Field(..., description="Ось X")
    y_axis: str = Field(..., description="Ось Y")
    aggregation: str | None = Field(None, description="Агрегация")


class MetricWidgetConfig(BaseModel):
    """Конфигурация виджета-метрики"""

    metric_type: str = Field(..., description="Тип метрики")
    data_source: str = Field(..., description="Источник данных")
    format: str | None = Field(None, description="Форматирование")
    comparison: dict[str, Any] | None = Field(None, description="Сравнение")


class TableWidgetConfig(BaseModel):
    """Конфигурация виджета-таблицы"""

    data_source: str = Field(..., description="Источник данных")
    columns: list[dict[str, Any]] = Field(..., description="Колонки")
    pagination: dict[str, Any] | None = Field(None, description="Пагинация")
    sorting: dict[str, Any] | None = Field(None, description="Сортировка")
