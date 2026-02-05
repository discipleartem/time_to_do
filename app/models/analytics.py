"""
Модели данных для системы аналитики
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.sprint import Sprint
    from app.models.user import User

from app.models.base import Base


class AnalyticsEvent(Base):
    """Модель для сбора событий аналитики"""

    __tablename__ = "analytics_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Пользователь и сущность
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    entity_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )
    entity_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)

    # Метаданные события
    event_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    session_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Отношения
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="analytics_events"
    )


class ProjectMetrics(Base):
    """Метрики проектов"""

    __tablename__ = "project_metrics"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )

    # Временные рамки
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    period_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # daily, weekly, monthly

    # Метрики задач
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    new_tasks: Mapped[int] = mapped_column(Integer, default=0)

    # Метрики времени
    total_time_logged: Mapped[int] = mapped_column(BigInteger, default=0)  # в секундах
    average_task_duration: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Метрики активности
    active_users: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    files_uploaded: Mapped[int] = mapped_column(Integer, default=0)

    # Дополнительные метрики
    custom_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Отношения
    project: Mapped["Project"] = relationship("Project", back_populates="metrics")


class UserMetrics(Base):
    """Метрики пользователей"""

    __tablename__ = "user_metrics"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    # Временные рамки
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    period_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # daily, weekly, monthly

    # Метрики производительности
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    tasks_created: Mapped[int] = mapped_column(Integer, default=0)
    time_logged: Mapped[int] = mapped_column(BigInteger, default=0)  # в секундах

    # Метрики активности
    login_count: Mapped[int] = mapped_column(Integer, default=0)
    comments_posted: Mapped[int] = mapped_column(Integer, default=0)
    files_uploaded: Mapped[int] = mapped_column(Integer, default=0)

    # Метрики коллаборации
    projects_active: Mapped[int] = mapped_column(Integer, default=0)
    sprints_participated: Mapped[int] = mapped_column(Integer, default=0)

    # Дополнительные метрики
    custom_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Отношения
    user: Mapped["User"] = relationship("User", back_populates="metrics")


class SprintMetrics(Base):
    """Метрики спринтов"""

    __tablename__ = "sprint_metrics"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sprint_id: Mapped[UUID] = mapped_column(
        ForeignKey("sprints.id"), nullable=False, index=True
    )

    # Основные метрики
    planned_story_points: Mapped[int] = mapped_column(Integer, default=0)
    completed_story_points: Mapped[int] = mapped_column(Integer, default=0)
    velocity: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Метрики задач
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    incomplete_tasks: Mapped[int] = mapped_column(Integer, default=0)

    # Временные метрики
    planned_duration: Mapped[int] = mapped_column(Integer, default=0)  # в днях
    actual_duration: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # в днях
    on_time_completion: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Метрики команды
    team_size: Mapped[int] = mapped_column(Integer, default=0)
    average_task_completion_time: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # в днях

    # Дополнительные данные
    burndown_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    retrospective_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Отношения
    sprint: Mapped["Sprint"] = relationship("Sprint", back_populates="metrics")


class AnalyticsReport(Base):
    """Готовые отчеты аналитики"""

    __tablename__ = "analytics_reports"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Тип и конфигурация отчета
    report_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # global, project, user
    scope_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)

    # Параметры отчета
    filters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    date_range: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metrics_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Результаты
    report_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    data_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Метаданные
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_scheduled: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Временные метки
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_accessed: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0)

    # Отношения
    creator: Mapped[Optional["User"]] = relationship(
        "User", back_populates="analytics_reports"
    )


class Dashboard(Base):
    """Пользовательские дашборды"""

    __tablename__ = "dashboards"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Владелец и доступ
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

    # Конфигурация дашборда
    layout_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    widgets: Mapped[dict] = mapped_column(JSONB, nullable=False)
    filters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    refresh_interval: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # в секундах

    # Метаданные
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_viewed: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)

    # Отношения
    user: Mapped["User"] = relationship("User", back_populates="dashboards")
