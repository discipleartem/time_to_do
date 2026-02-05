"""
Сервис для работы с аналитикой и метриками
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analytics import (
    AnalyticsEvent,
    Dashboard,
    ProjectMetrics,
    SprintMetrics,
    UserMetrics,
)
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.task import Task
from app.models.time_entry import TimeEntry
from app.models.user import User

if TYPE_CHECKING:
    pass


class AnalyticsService:
    """Сервис для сбора и обработки аналитических данных"""

    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    # === Сбор событий аналитики ===

    async def track_event(
        self,
        event_type: str,
        event_category: str,
        user_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        event_data: dict[str, Any] | None = None,
        session_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AnalyticsEvent:
        """Записывает событие аналитики"""
        event = AnalyticsEvent(
            event_type=event_type,
            event_category=event_category,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_data=event_data,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db_session.add(event)
        await self.db_session.commit()
        await self.db_session.refresh(event)

        return event

    async def get_events(
        self,
        user_id: UUID | None = None,
        event_type: str | None = None,
        event_category: str | None = None,
        entity_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[AnalyticsEvent]:
        """Получает события аналитики с фильтрами"""
        query = select(AnalyticsEvent)

        if user_id:
            query = query.where(AnalyticsEvent.user_id == user_id)
        if event_type:
            query = query.where(AnalyticsEvent.event_type == event_type)
        if event_category:
            query = query.where(AnalyticsEvent.event_category == event_category)
        if entity_type:
            query = query.where(AnalyticsEvent.entity_type == entity_type)
        if start_date:
            query = query.where(AnalyticsEvent.timestamp >= start_date)
        if end_date:
            query = query.where(AnalyticsEvent.timestamp <= end_date)

        query = query.order_by(desc(AnalyticsEvent.timestamp)).limit(limit)

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    # === Метрики проектов ===

    async def calculate_project_metrics(
        self,
        project_id: UUID,
        date: datetime,
        period_type: str = "daily",
    ) -> ProjectMetrics:
        """Рассчитывает метрики проекта за указанный период"""

        # Определяем временные рамки периода
        if period_type == "daily":
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        elif period_type == "weekly":
            start_date = date - timedelta(days=date.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=7)
        elif period_type == "monthly":
            start_date = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if date.month == 12:
                end_date = start_date.replace(year=date.year + 1, month=1)
            else:
                end_date = start_date.replace(month=date.month + 1)
        else:
            raise ValueError(f"Unsupported period_type: {period_type}")

        # Получаем статистику по задачам
        tasks_query = select(Task).where(Task.project_id == project_id)
        if period_type == "daily":
            tasks_query = tasks_query.where(
                and_(Task.created_at >= start_date, Task.created_at < end_date)
            )
        else:
            # Для недельных и месячных метрик учитываем все задачи проекта
            pass

        tasks_result = await self.db_session.execute(tasks_query)
        tasks = list(tasks_result.scalars().all())

        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == "DONE"])
        new_tasks = len(
            [t for t in tasks if t.created_at >= start_date and t.created_at < end_date]
        )

        # Получаем статистику по времени
        time_query = select(TimeEntry).where(
            and_(
                TimeEntry.project_id == project_id,
                TimeEntry.start_time >= start_date,
                TimeEntry.start_time < end_date,
            )
        )
        time_result = await self.db_session.execute(time_query)
        time_entries = list(time_result.scalars().all())

        total_time_logged = sum(
            entry.duration for entry in time_entries if entry.duration is not None
        )

        average_task_duration = (
            total_time_logged / completed_tasks if completed_tasks > 0 else None
        )

        # Получаем статистику по активным пользователям
        active_users_query = select(func.count(func.distinct(TimeEntry.user_id))).where(
            and_(
                TimeEntry.project_id == project_id,
                TimeEntry.start_time >= start_date,
                TimeEntry.start_time < end_date,
            )
        )
        active_users_result = await self.db_session.execute(active_users_query)
        active_users = active_users_result.scalar() or 0

        # Получаем количество комментариев и файлов
        comments_count = 0  # TODO: реализовать когда будет модель комментариев
        files_uploaded = 0  # TODO: реализовать когда будет модель файлов

        # Создаем или обновляем метрики
        metrics = ProjectMetrics(
            project_id=project_id,
            date=date,
            period_type=period_type,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            new_tasks=new_tasks,
            total_time_logged=total_time_logged,
            average_task_duration=average_task_duration,
            active_users=active_users,
            comments_count=comments_count,
            files_uploaded=files_uploaded,
        )

        self.db_session.add(metrics)
        await self.db_session.commit()
        await self.db_session.refresh(metrics)

        return metrics

    async def get_project_metrics(
        self,
        project_id: UUID,
        period_type: str = "daily",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[ProjectMetrics]:
        """Получает метрики проекта за период"""
        query = select(ProjectMetrics).where(ProjectMetrics.project_id == project_id)

        if period_type:
            query = query.where(ProjectMetrics.period_type == period_type)
        if start_date:
            query = query.where(ProjectMetrics.date >= start_date)
        if end_date:
            query = query.where(ProjectMetrics.date <= end_date)

        query = query.order_by(ProjectMetrics.date)

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    # === Метрики пользователей ===

    async def calculate_user_metrics(
        self,
        user_id: UUID,
        date: datetime,
        period_type: str = "daily",
    ) -> UserMetrics:
        """Рассчитывает метрики пользователя за указанный период"""

        # Определяем временные рамки периода
        if period_type == "daily":
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        elif period_type == "weekly":
            start_date = date - timedelta(days=date.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=7)
        elif period_type == "monthly":
            start_date = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if date.month == 12:
                end_date = start_date.replace(year=date.year + 1, month=1)
            else:
                end_date = start_date.replace(month=date.month + 1)
        else:
            raise ValueError(f"Unsupported period_type: {period_type}")

        # Получаем статистику по задачам
        tasks_query = select(Task).where(Task.assignee_id == user_id)
        if period_type == "daily":
            tasks_query = tasks_query.where(
                and_(Task.created_at >= start_date, Task.created_at < end_date)
            )
        else:
            # Для недельных и месячных метрик учитываем все задачи пользователя
            pass

        tasks_result = await self.db_session.execute(tasks_query)
        tasks = list(tasks_result.scalars().all())

        tasks_completed = len([t for t in tasks if t.status == "DONE"])
        tasks_created = len(
            [t for t in tasks if t.created_at >= start_date and t.created_at < end_date]
        )

        # Получаем статистику по времени
        time_query = select(TimeEntry).where(
            and_(
                TimeEntry.user_id == user_id,
                TimeEntry.start_time >= start_date,
                TimeEntry.start_time < end_date,
            )
        )
        time_result = await self.db_session.execute(time_query)
        time_entries = list(time_result.scalars().all())

        time_logged = sum(
            entry.duration for entry in time_entries if entry.duration is not None
        )

        # Получаем количество логинов (из событий аналитики)
        login_events_query = select(func.count(AnalyticsEvent.id)).where(
            and_(
                AnalyticsEvent.user_id == user_id,
                AnalyticsEvent.event_type == "login",
                AnalyticsEvent.timestamp >= start_date,
                AnalyticsEvent.timestamp < end_date,
            )
        )
        login_result = await self.db_session.execute(login_events_query)
        login_count = login_result.scalar() or 0

        # Получаем статистику по проектам
        projects_query = select(func.count(func.distinct(TimeEntry.project_id))).where(
            and_(
                TimeEntry.user_id == user_id,
                TimeEntry.start_time >= start_date,
                TimeEntry.start_time < end_date,
            )
        )
        projects_result = await self.db_session.execute(projects_query)
        projects_active = projects_result.scalar() or 0

        # Создаем метрики
        metrics = UserMetrics(
            user_id=user_id,
            date=date,
            period_type=period_type,
            tasks_completed=tasks_completed,
            tasks_created=tasks_created,
            time_logged=time_logged,
            login_count=login_count,
            comments_posted=0,  # TODO: реализовать с моделью комментариев
            files_uploaded=0,  # TODO: реализовать с моделью файлов
            projects_active=projects_active,
            sprints_participated=0,  # TODO: реализовать со спринтами
        )

        self.db_session.add(metrics)
        await self.db_session.commit()
        await self.db_session.refresh(metrics)

        return metrics

    # === Метрики спринтов ===

    async def calculate_sprint_metrics(self, sprint_id: UUID) -> SprintMetrics:
        """Рассчитывает метрики спринта"""

        # Получаем спринт с задачами
        sprint_query = (
            select(Sprint)
            .options(selectinload(Sprint.tasks))
            .where(Sprint.id == sprint_id)
        )
        sprint_result = await self.db_session.execute(sprint_query)
        sprint = sprint_result.scalar_one_or_none()

        if not sprint:
            raise ValueError(f"Sprint not found: {sprint_id}")

        tasks = sprint.tasks or []
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == "DONE"])
        incomplete_tasks = total_tasks - completed_tasks

        # Рассчитываем velocity
        planned_story_points = sum((t.story_points or 0) for t in tasks)
        completed_story_points = sum(
            (t.story_points or 0) for t in tasks if t.status == "DONE"
        )
        velocity = completed_story_points if completed_story_points > 0 else None

        # Рассчитываем длительность
        if sprint.start_date and sprint.end_date:
            planned_duration = (sprint.end_date - sprint.start_date).days
        else:
            planned_duration = 0

        if sprint.actual_end_date:
            actual_duration = (sprint.actual_end_date - sprint.start_date).days
            on_time_completion = actual_duration <= planned_duration
        else:
            actual_duration = None
            on_time_completion = None

        # Рассчитываем среднее время выполнения задач
        completed_task_times = []
        for task in tasks:
            if task.status == "DONE" and task.created_at and task.updated_at:
                completion_time = (task.updated_at - task.created_at).days
                completed_task_times.append(completion_time)

        average_task_completion_time = (
            sum(completed_task_times) / len(completed_task_times)
            if completed_task_times
            else None
        )

        # Получаем размер команды
        team_size = len({t.assignee_id for t in tasks if t.assignee_id})

        # Создаем метрики
        metrics = SprintMetrics(
            sprint_id=sprint_id,
            planned_story_points=planned_story_points,
            completed_story_points=completed_story_points,
            velocity=velocity,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            incomplete_tasks=incomplete_tasks,
            planned_duration=planned_duration,
            actual_duration=actual_duration,
            on_time_completion=on_time_completion,
            team_size=team_size,
            average_task_completion_time=average_task_completion_time,
        )

        self.db_session.add(metrics)
        await self.db_session.commit()
        await self.db_session.refresh(metrics)

        return metrics

    # === Дашборды и отчеты ===

    async def create_dashboard(
        self,
        user_id: UUID,
        name: str,
        description: str | None = None,
        layout_config: dict[str, Any] | None = None,
        widgets: dict[str, Any] | None = None,
        is_default: bool = False,
        is_public: bool = False,
    ) -> Dashboard:
        """Создает дашборд"""

        if not layout_config:
            layout_config = {"grid": {"cols": 12, "rows": 8}}

        if not widgets:
            widgets = {}

        dashboard = Dashboard(
            name=name,
            description=description,
            user_id=user_id,
            is_default=is_default,
            is_public=is_public,
            layout_config=layout_config,
            widgets=widgets,
        )

        self.db_session.add(dashboard)
        await self.db_session.commit()
        await self.db_session.refresh(dashboard)

        return dashboard

    async def get_user_dashboards(self, user_id: UUID) -> list[Dashboard]:
        """Получает дашборды пользователя"""
        query = (
            select(Dashboard)
            .where(Dashboard.user_id == user_id)
            .order_by(Dashboard.is_default.desc(), Dashboard.name)
        )

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def update_dashboard_view(self, dashboard_id: UUID) -> None:
        """Обновляет статистику просмотра дашборда"""
        query = select(Dashboard).where(Dashboard.id == dashboard_id)
        result = await self.db_session.execute(query)
        dashboard = result.scalar_one_or_none()

        if dashboard:
            dashboard.last_viewed = datetime.utcnow()
            dashboard.view_count += 1
            dashboard.updated_at = datetime.utcnow()
            await self.db_session.commit()

    # === Агрегированная аналитика ===

    async def get_project_summary(
        self, project_id: UUID, days: int = 30
    ) -> dict[str, Any]:
        """Получает сводную информацию по проекту"""

        start_date = datetime.utcnow() - timedelta(days=days)

        # Получаем базовую информацию о проекте
        project_query = select(Project).where(Project.id == project_id)
        project_result = await self.db_session.execute(project_query)
        project = project_result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project not found: {project_id}")

        # Получаем метрики за период
        metrics = await self.get_project_metrics(
            project_id, "daily", start_date, datetime.utcnow()
        )

        # Получаем статистику по задачам
        tasks_query = select(Task).where(Task.project_id == project_id)
        tasks_result = await self.db_session.execute(tasks_query)
        tasks = list(tasks_result.scalars().all())

        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == "DONE"])
        in_progress_tasks = len([t for t in tasks if t.status == "IN_PROGRESS"])
        todo_tasks = len([t for t in tasks if t.status == "TODO"])

        # Получаем активных пользователей
        active_users_query = select(func.count(func.distinct(Task.assignee_id))).where(
            Task.project_id == project_id
        )
        active_users_result = await self.db_session.execute(active_users_query)
        active_users = active_users_result.scalar() or 0

        return {
            "project": {
                "id": str(project.id),
                "name": project.name,
                "status": project.status,
                "created_at": project.created_at.isoformat(),
            },
            "tasks": {
                "total": total_tasks,
                "completed": completed_tasks,
                "in_progress": in_progress_tasks,
                "todo": todo_tasks,
                "completion_rate": (
                    (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                ),
            },
            "users": {
                "active": active_users,
            },
            "metrics": [
                {
                    "date": metric.date.isoformat(),
                    "completed_tasks": metric.completed_tasks,
                    "time_logged": metric.total_time_logged,
                    "active_users": metric.active_users,
                }
                for metric in metrics[-7:]  # Последние 7 дней
            ],
        }

    async def get_user_summary(self, user_id: UUID, days: int = 30) -> dict[str, Any]:
        """Получает сводную информацию по пользователю"""

        start_date = datetime.utcnow() - timedelta(days=days)

        # Получаем базовую информацию о пользователе
        user_query = select(User).where(User.id == user_id)
        user_result = await self.db_session.execute(user_query)
        user = user_result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User not found: {user_id}")

        # Получаем метрики за период
        metrics_query = (
            select(UserMetrics)
            .where(
                and_(
                    UserMetrics.user_id == user_id,
                    UserMetrics.date >= start_date,
                    UserMetrics.period_type == "daily",
                )
            )
            .order_by(desc(UserMetrics.date))
        )
        metrics_result = await self.db_session.execute(metrics_query)
        metrics = list(metrics_result.scalars().all())

        # Получаем статистику по задачам
        tasks_query = select(Task).where(Task.assignee_id == user_id)
        tasks_result = await self.db_session.execute(tasks_query)
        tasks = list(tasks_result.scalars().all())

        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == "DONE"])
        in_progress_tasks = len([t for t in tasks if t.status == "IN_PROGRESS"])

        # Получаем активные проекты
        active_projects_query = select(
            func.count(func.distinct(Task.project_id))
        ).where(Task.assignee_id == user_id)
        active_projects_result = await self.db_session.execute(active_projects_query)
        active_projects = active_projects_result.scalar() or 0

        return {
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
            },
            "tasks": {
                "total": total_tasks,
                "completed": completed_tasks,
                "in_progress": in_progress_tasks,
                "completion_rate": (
                    (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                ),
            },
            "projects": {
                "active": active_projects,
            },
            "metrics": [
                {
                    "date": metric.date.isoformat(),
                    "tasks_completed": metric.tasks_completed,
                    "time_logged": metric.time_logged,
                    "login_count": metric.login_count,
                }
                for metric in metrics[:7]  # Последние 7 дней
            ],
        }

    async def get_user_metrics(
        self,
        user_id: UUID,
        period_type: str = "daily",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[UserMetrics]:
        """Получает метрики пользователя за период"""
        query = select(UserMetrics).where(UserMetrics.user_id == user_id)

        if period_type:
            query = query.where(UserMetrics.period_type == period_type)
        if start_date:
            query = query.where(UserMetrics.date >= start_date)
        if end_date:
            query = query.where(UserMetrics.date <= end_date)

        query = query.order_by(UserMetrics.date)

        result = await self.db_session.execute(query)
        return list(result.scalars().all())
