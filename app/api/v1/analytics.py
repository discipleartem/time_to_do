"""
API эндпоинты для системы аналитики
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.analytics import (
    AnalyticsEvent as AnalyticsEventModel,
)
from app.models.analytics import (
    Dashboard as DashboardModel,
)
from app.models.analytics import (
    ProjectMetrics as ProjectMetricsModel,
)
from app.models.analytics import (
    SprintMetrics as SprintMetricsModel,
)
from app.models.analytics import (
    UserMetrics as UserMetricsModel,
)
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsEvent,
    AnalyticsEventCreate,
    AnalyticsQuery,
    AnalyticsResponse,
    Dashboard,
    DashboardCreate,
    DashboardUpdate,
    ProjectMetrics,
    SprintMetrics,
    UserMetrics,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


# === Функции конвертации моделей в схемы ===


def convert_analytics_event(model: AnalyticsEventModel) -> AnalyticsEvent:
    """Конвертирует модель AnalyticsEvent в схему."""
    return AnalyticsEvent(
        id=model.id,
        event_type=model.event_type,
        event_category=model.event_category,
        entity_type=model.entity_type,
        entity_id=model.entity_id,
        event_data=model.event_data,
        session_id=model.session_id,
        ip_address=model.ip_address,
        user_agent=model.user_agent,
        user_id=model.user_id,
        timestamp=model.timestamp,
    )


def convert_project_metrics(model: ProjectMetricsModel) -> ProjectMetrics:
    """Конвертирует модель ProjectMetrics в схему."""
    return ProjectMetrics(
        id=model.id,
        project_id=model.project_id,
        date=model.date,
        period_type=model.period_type,
        total_tasks=model.total_tasks,
        completed_tasks=model.completed_tasks,
        new_tasks=model.new_tasks,
        total_time_logged=model.total_time_logged,
        average_task_duration=model.average_task_duration,
        active_users=model.active_users,
        comments_count=model.comments_count,
        files_uploaded=model.files_uploaded,
        custom_metrics=model.custom_metrics,
        created_at=model.created_at,
    )


def convert_user_metrics(model: UserMetricsModel) -> UserMetrics:
    """Конвертирует модель UserMetrics в схему."""
    return UserMetrics(
        id=model.id,
        user_id=model.user_id,
        date=model.date,
        period_type=model.period_type,
        tasks_completed=model.tasks_completed,
        tasks_created=model.tasks_created,
        time_logged=model.time_logged,
        login_count=model.login_count,
        comments_posted=model.comments_posted,
        files_uploaded=model.files_uploaded,
        projects_active=model.projects_active,
        sprints_participated=model.sprints_participated,
        custom_metrics=model.custom_metrics,
        created_at=model.created_at,
    )


def convert_sprint_metrics(model: SprintMetricsModel) -> SprintMetrics:
    """Конвертирует модель SprintMetrics в схему."""
    return SprintMetrics(
        id=model.id,
        sprint_id=model.sprint_id,
        planned_story_points=model.planned_story_points,
        completed_story_points=model.completed_story_points,
        velocity=model.velocity,
        total_tasks=model.total_tasks,
        completed_tasks=model.completed_tasks,
        incomplete_tasks=model.incomplete_tasks,
        planned_duration=model.planned_duration,
        actual_duration=model.actual_duration,
        on_time_completion=model.on_time_completion,
        team_size=model.team_size,
        average_task_completion_time=model.average_task_completion_time,
        burndown_data=model.burndown_data,
        retrospective_summary=model.retrospective_summary,
        created_at=model.created_at,
    )


def convert_dashboard(model: DashboardModel) -> Dashboard:
    """Конвертирует модель Dashboard в схему."""
    return Dashboard(
        id=model.id,
        user_id=model.user_id,
        name=model.name,
        description=model.description,
        is_default=model.is_default,
        is_public=model.is_public,
        layout_config=model.layout_config,
        widgets=model.widgets,
        filters=model.filters,
        refresh_interval=model.refresh_interval,
        created_at=model.created_at,
        updated_at=model.updated_at,
        last_viewed=model.last_viewed,
        view_count=model.view_count,
    )


# === События аналитики ===


@router.post("/events", response_model=AnalyticsEvent)
async def track_event(
    event_data: AnalyticsEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsEvent:
    """Записывает событие аналитики"""
    analytics_service = AnalyticsService(db)

    event = await analytics_service.track_event(
        event_type=event_data.event_type,
        event_category=event_data.event_category,
        user_id=current_user.id,
        entity_type=event_data.entity_type,
        entity_id=event_data.entity_id,
        event_data=event_data.event_data,
        session_id=event_data.session_id,
        ip_address=event_data.ip_address,
        user_agent=event_data.user_agent,
    )

    return convert_analytics_event(event)


@router.get("/events", response_model=list[AnalyticsEvent])
async def get_events(
    event_type: str | None = Query(None, description="Тип события"),
    event_category: str | None = Query(None, description="Категория события"),
    entity_type: str | None = Query(None, description="Тип сущности"),
    start_date: datetime | None = Query(None, description="Начальная дата"),
    end_date: datetime | None = Query(None, description="Конечная дата"),
    limit: int = Query(100, ge=1, le=1000, description="Лимит записей"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AnalyticsEvent]:
    """Получает события аналитики"""
    analytics_service = AnalyticsService(db)

    events = await analytics_service.get_events(
        user_id=current_user.id,
        event_type=event_type,
        event_category=event_category,
        entity_type=entity_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )

    return [convert_analytics_event(event) for event in events]


# === Метрики проектов ===


@router.get("/projects/{project_id}/metrics", response_model=list[ProjectMetrics])
async def get_project_metrics(
    project_id: UUID,
    period_type: str = Query("daily", description="Тип периода"),
    start_date: datetime | None = Query(None, description="Начальная дата"),
    end_date: datetime | None = Query(None, description="Конечная дата"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectMetrics]:
    """Получает метрики проекта"""
    analytics_service = AnalyticsService(db)

    # TODO: Проверить права доступа к проекту

    metrics = await analytics_service.get_project_metrics(
        project_id=project_id,
        period_type=period_type,
        start_date=start_date,
        end_date=end_date,
    )

    return [convert_project_metrics(metric) for metric in metrics]


@router.post("/projects/{project_id}/metrics/calculate", response_model=ProjectMetrics)
async def calculate_project_metrics(
    project_id: UUID,
    date: datetime | None = Query(None, description="Дата расчета"),
    period_type: str = Query("daily", description="Тип периода"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectMetrics:
    """Рассчитывает метрики проекта"""
    analytics_service = AnalyticsService(db)

    # TODO: Проверить права доступа к проекту

    if not date:
        date = datetime.utcnow()

    metrics = await analytics_service.calculate_project_metrics(
        project_id=project_id,
        date=date,
        period_type=period_type,
    )

    return convert_project_metrics(metrics)


@router.get("/projects/{project_id}/summary", response_model=dict[str, Any])
async def get_project_summary(
    project_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Количество дней"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Получает сводную информацию по проекту"""
    analytics_service = AnalyticsService(db)

    # TODO: Проверить права доступа к проекту

    summary = await analytics_service.get_project_summary(
        project_id=project_id,
        days=days,
    )

    return summary


# === Метрики пользователей ===


@router.get("/users/{user_id}/metrics", response_model=list[UserMetrics])
async def get_user_metrics(
    user_id: UUID,
    period_type: str = Query("daily", description="Тип периода"),
    start_date: datetime | None = Query(None, description="Начальная дата"),
    end_date: datetime | None = Query(None, description="Конечная дата"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserMetrics]:
    """Получает метрики пользователя"""
    analytics_service = AnalyticsService(db)

    # Пользователь может смотреть только свои метрики (или если админ)
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied")

    metrics = await analytics_service.get_user_metrics(
        user_id=user_id,
        period_type=period_type,
        start_date=start_date,
        end_date=end_date,
    )

    return [convert_user_metrics(metric) for metric in metrics]


@router.post("/users/{user_id}/metrics/calculate", response_model=UserMetrics)
async def calculate_user_metrics(
    user_id: UUID,
    date: datetime | None = Query(None, description="Дата расчета"),
    period_type: str = Query("daily", description="Тип периода"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserMetrics:
    """Рассчитывает метрики пользователя"""
    analytics_service = AnalyticsService(db)

    # Пользователь может рассчитывать только свои метрики (или если админ)
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied")

    if not date:
        date = datetime.utcnow()

    metrics = await analytics_service.calculate_user_metrics(
        user_id=user_id,
        date=date,
        period_type=period_type,
    )

    return convert_user_metrics(metrics)


@router.get("/users/{user_id}/summary", response_model=dict[str, Any])
async def get_user_summary(
    user_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Количество дней"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Получает сводную информацию по пользователю"""
    analytics_service = AnalyticsService(db)

    # Пользователь может смотреть только свою сводку (или если админ)
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied")

    summary = await analytics_service.get_user_summary(
        user_id=user_id,
        days=days,
    )

    return summary


# === Метрики спринтов ===


@router.get("/sprints/{sprint_id}/metrics", response_model=SprintMetrics)
async def get_sprint_metrics(
    sprint_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SprintMetrics:
    """Получает метрики спринта"""
    analytics_service = AnalyticsService(db)

    # TODO: Проверить права доступа к спринту

    metrics = await analytics_service.calculate_sprint_metrics(sprint_id=sprint_id)

    return convert_sprint_metrics(metrics)


@router.post("/sprints/{sprint_id}/metrics/calculate", response_model=SprintMetrics)
async def calculate_sprint_metrics(
    sprint_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SprintMetrics:
    """Рассчитывает метрики спринта"""
    analytics_service = AnalyticsService(db)

    # TODO: Проверить права доступа к спринту

    metrics = await analytics_service.calculate_sprint_metrics(sprint_id=sprint_id)

    return convert_sprint_metrics(metrics)


# === Дашборды ===


@router.post("/dashboards", response_model=Dashboard)
async def create_dashboard(
    dashboard_data: DashboardCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dashboard:
    """Создает дашборд"""
    analytics_service = AnalyticsService(db)

    dashboard = await analytics_service.create_dashboard(
        user_id=current_user.id,
        name=dashboard_data.name,
        description=dashboard_data.description,
        layout_config=dashboard_data.layout_config,
        widgets=dashboard_data.widgets,
        is_default=dashboard_data.is_default,
        is_public=dashboard_data.is_public,
    )

    return convert_dashboard(dashboard)


@router.get("/dashboards", response_model=list[Dashboard])
async def get_user_dashboards(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Dashboard]:
    """Получает дашборды пользователя"""
    analytics_service = AnalyticsService(db)

    dashboards = await analytics_service.get_user_dashboards(user_id=current_user.id)

    return [convert_dashboard(dashboard) for dashboard in dashboards]


@router.get("/dashboards/{dashboard_id}", response_model=Dashboard)
async def get_dashboard(
    dashboard_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dashboard:
    """Получает дашборд по ID"""
    analytics_service = AnalyticsService(db)

    # TODO: Получить дашборд и проверить права доступа

    # Обновляем статистику просмотра
    await analytics_service.update_dashboard_view(dashboard_id=dashboard_id)

    # TODO: Вернуть дашборд
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.put("/dashboards/{dashboard_id}", response_model=Dashboard)
async def update_dashboard(
    dashboard_id: UUID,
    dashboard_data: DashboardUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dashboard:
    """Обновляет дашборд"""
    # TODO: Реализовать обновление дашборда
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete("/dashboards/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Удаляет дашборд"""
    # TODO: Реализовать удаление дашборда
    raise HTTPException(status_code=501, detail="Not implemented yet")


# === Общая аналитика ===


@router.post("/query", response_model=AnalyticsResponse)
async def query_analytics(
    query: AnalyticsQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsResponse:
    """Выполняет запрос к аналитике"""
    # TODO: Реализовать универсальный запрос к аналитике
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/overview")
async def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Получает обзор аналитики для пользователя"""
    analytics_service = AnalyticsService(db)

    # Получаем сводку по пользователю за последние 30 дней
    user_summary = await analytics_service.get_user_summary(
        user_id=current_user.id,
        days=30,
    )

    # TODO: Добавить больше данных для обзора

    return {
        "user_summary": user_summary,
        "recent_activity": [],  # TODO: Получить последние события
        "quick_stats": {
            "tasks_completed_today": 0,  # TODO: Посчитать задачи за сегодня
            "time_logged_today": 0,  # TODO: Посчитать время за сегодня
            "active_projects": user_summary.get("projects", {}).get("active", 0),
        },
    }


# === Автоматический сбор метрик ===


@router.post("/metrics/collect")
async def trigger_metrics_collection(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Запускает сбор метрик (только для админов)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    # TODO: Реализовать фоновую задачу для сбора метрик
    # Пока просто вернем успешный ответ

    return {"status": "collection_triggered", "message": "Metrics collection started"}
