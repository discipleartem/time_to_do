"""
Сервис для управления SCRUM спринтами
"""

import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sprint import Sprint, SprintStatus, SprintTask
from app.models.task import TaskStatus
from app.schemas.sprint import (
    BurndownData,
    SprintBurndown,
    SprintCreate,
    SprintStats,
    SprintUpdate,
    TeamVelocity,
    VelocityData,
)


class SprintService:
    """Сервис для управления спринтами"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_sprint(self, sprint_data: SprintCreate) -> Sprint:
        """Создание нового спринта"""
        sprint = Sprint(
            name=sprint_data.name,
            description=sprint_data.description,
            goal=sprint_data.goal,
            project_id=uuid.UUID(sprint_data.project_id),
            capacity_hours=sprint_data.capacity_hours,
            velocity_points=sprint_data.velocity_points,
        )

        self.db.add(sprint)
        await self.db.commit()
        await self.db.refresh(sprint)
        return sprint

    async def get_sprint_by_id(self, sprint_id: str) -> Sprint | None:
        """Получение спринта по ID"""
        result = await self.db.execute(
            select(Sprint)
            .options(selectinload(Sprint.sprint_tasks).selectinload(SprintTask.task))
            .where(Sprint.id == uuid.UUID(sprint_id))
        )
        return result.scalar_one_or_none()

    async def get_project_sprints(
        self, project_id: str, include_completed: bool = True
    ) -> list[Sprint]:
        """Получение спринтов проекта"""
        query = select(Sprint).where(Sprint.project_id == uuid.UUID(project_id))

        if not include_completed:
            query = query.where(Sprint.status != SprintStatus.COMPLETED)

        query = query.order_by(Sprint.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_sprint(
        self, sprint_id: str, sprint_data: SprintUpdate
    ) -> Sprint | None:
        """Обновление спринта"""
        sprint = await self.get_sprint_by_id(sprint_id)
        if not sprint:
            return None

        update_data = sprint_data.model_dump(exclude_unset=True)

        # Конвертируем даты если они есть
        if "start_date" in update_data and update_data["start_date"]:
            update_data["start_date"] = datetime.strptime(
                update_data["start_date"], "%Y-%m-%d"
            ).date()

        if "end_date" in update_data and update_data["end_date"]:
            update_data["end_date"] = datetime.strptime(
                update_data["end_date"], "%Y-%m-%d"
            ).date()

        for field, value in update_data.items():
            setattr(sprint, field, value)

        await self.db.commit()
        await self.db.refresh(sprint)
        return sprint

    async def start_sprint(
        self,
        sprint_id: str,
        start_date: date,
        end_date: date,
        capacity_hours: int | None = None,
        velocity_points: int | None = None,
    ) -> Sprint | None:
        """Запуск спринта"""
        sprint = await self.get_sprint_by_id(sprint_id)
        if not sprint:
            return None

        if sprint.status != SprintStatus.PLANNING:
            raise ValueError("Можно запустить только спринт в статусе planning")

        # SQLAlchemy 2.0: используем константы enum напрямую
        sprint.status = "active"  # type: ignore[assignment] # SQLAlchemy Enum field limitation
        sprint.start_date = start_date  # type: ignore[assignment] # SQLAlchemy Date field limitation
        sprint.end_date = end_date  # type: ignore[assignment] # SQLAlchemy Date field limitation

        if capacity_hours is not None:
            sprint.capacity_hours = capacity_hours
        if velocity_points is not None:
            sprint.velocity_points = velocity_points

        await self.db.commit()
        await self.db.refresh(sprint)
        return sprint

    async def complete_sprint(
        self,
        sprint_id: str,
        completed_points: int | None = None,
        retrospective_notes: str | None = None,
    ) -> Sprint | None:
        """Завершение спринта"""
        sprint = await self.get_sprint_by_id(sprint_id)
        if not sprint:
            return None

        if sprint.status != SprintStatus.ACTIVE:
            raise ValueError("Можно завершить только активный спринт")

        sprint.status = "completed"  # type: ignore[assignment] # SQLAlchemy Enum field limitation

        if completed_points is not None:
            sprint.completed_points = completed_points
        else:
            # Автоматический расчет выполненных очков
            sprint.completed_points = await self._calculate_completed_points(sprint_id)

        await self.db.commit()
        await self.db.refresh(sprint)
        return sprint

    async def cancel_sprint(self, sprint_id: str) -> Sprint | None:
        """Отмена спринта"""
        sprint = await self.get_sprint_by_id(sprint_id)
        if not sprint:
            return None

        if sprint.status == SprintStatus.COMPLETED:
            raise ValueError("Нельзя отменить завершенный спринт")

        sprint.status = "cancelled"  # type: ignore[assignment] # SQLAlchemy Enum field limitation
        await self.db.commit()
        await self.db.refresh(sprint)
        return sprint

    async def add_task_to_sprint(
        self,
        sprint_id: str,
        task_id: str,
        order: int = 0,
        is_added_mid_sprint: bool = False,
    ) -> SprintTask:
        """Добавление задачи в спринт"""
        # Проверяем, что задача не уже в спринте
        existing = await self.db.execute(
            select(SprintTask).where(
                and_(
                    SprintTask.sprint_id == uuid.UUID(sprint_id),
                    SprintTask.task_id == uuid.UUID(task_id),
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Задача уже добавлена в спринт")

        sprint_task = SprintTask(
            sprint_id=uuid.UUID(sprint_id),
            task_id=uuid.UUID(task_id),
            order=order,
            is_added_mid_sprint=is_added_mid_sprint,
        )

        self.db.add(sprint_task)
        await self.db.commit()
        await self.db.refresh(sprint_task)
        return sprint_task

    async def remove_task_from_sprint(self, sprint_id: str, task_id: str) -> bool:
        """Удаление задачи из спринта"""
        result = await self.db.execute(
            select(SprintTask).where(
                and_(
                    SprintTask.sprint_id == uuid.UUID(sprint_id),
                    SprintTask.task_id == uuid.UUID(task_id),
                )
            )
        )
        sprint_task = result.scalar_one_or_none()

        if sprint_task:
            await self.db.delete(sprint_task)
            await self.db.commit()
            return True
        return False

    async def get_sprint_tasks(self, sprint_id: str) -> list[SprintTask]:
        """Получение задач спринта"""
        result = await self.db.execute(
            select(SprintTask)
            .options(selectinload(SprintTask.task))
            .where(SprintTask.sprint_id == uuid.UUID(sprint_id))
            .order_by(SprintTask.order)
        )
        return list(result.scalars().all())

    async def get_sprint_stats(self, sprint_id: str) -> SprintStats:
        """Получение статистики спринта"""
        result = await self.db.execute(
            select(SprintTask)
            .options(selectinload(SprintTask.task))
            .where(SprintTask.sprint_id == uuid.UUID(sprint_id))
        )
        sprint_tasks = result.scalars().all()

        stats = SprintStats()
        stats.total_tasks = len(sprint_tasks)

        for sprint_task in sprint_tasks:
            task = sprint_task.task
            if not task:
                continue

            # Считаем задачи по статусам
            if task.status == TaskStatus.TODO:
                stats.todo_tasks += 1
            elif task.status == TaskStatus.IN_PROGRESS:
                stats.in_progress_tasks += 1
            elif task.status == TaskStatus.DONE:
                stats.done_tasks += 1
                stats.completed_tasks += 1
            elif task.status == TaskStatus.BLOCKED:
                stats.blocked_tasks += 1

            # Считаем story points
            story_points = getattr(task, "story_points", 0) or 0
            stats.total_story_points += story_points

            if task.status == TaskStatus.DONE:
                stats.completed_story_points += story_points
            else:
                stats.remaining_story_points += story_points

        # Процент выполнения
        if stats.total_story_points > 0:
            stats.completion_percentage = (
                stats.completed_story_points / stats.total_story_points
            ) * 100

        return stats

    async def get_burndown_data(self, sprint_id: str) -> SprintBurndown:
        """Получение данных для burndown chart"""
        sprint = await self.get_sprint_by_id(sprint_id)
        if not sprint or not sprint.start_date or not sprint.end_date:
            raise ValueError("Спринт не найден или не имеет дат начала/окончания")

        stats = await self.get_sprint_stats(sprint_id)

        burndown = SprintBurndown(
            sprint_id=sprint_id,
            sprint_name=sprint.name,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            total_story_points=stats.total_story_points,
        )

        # Генерируем данные для каждого дня спринта
        current_date = sprint.start_date
        total_points = stats.total_story_points

        while current_date <= sprint.end_date:
            # Идеальное оставшееся (линейное снижение)
            days_total = (sprint.end_date - sprint.start_date).days + 1
            days_passed = (current_date - sprint.start_date).days
            ideal_remaining = max(0, total_points * (1 - days_passed / days_total))

            # Фактическое оставшееся (упрощенно - берем текущее состояние)
            actual_remaining: float
            if current_date <= date.today():
                actual_remaining = stats.remaining_story_points
            else:
                actual_remaining = (
                    ideal_remaining  # В будущем предполагаем идеальный сценарий
                )

            burndown.data.append(
                BurndownData(
                    date=current_date,
                    ideal_remaining=ideal_remaining,
                    actual_remaining=actual_remaining,
                )
            )

            current_date += timedelta(days=1)

        return burndown

    async def get_team_velocity(self, project_id: str, limit: int = 10) -> TeamVelocity:
        """Получение velocity команды"""
        # Получаем завершенные спринты проекта
        result = await self.db.execute(
            select(Sprint)
            .where(
                and_(
                    Sprint.project_id == uuid.UUID(project_id),
                    Sprint.status == SprintStatus.COMPLETED,
                )
            )
            .order_by(Sprint.created_at.desc())
            .limit(limit)
        )
        completed_sprints = result.scalars().all()

        velocity_data = []
        total_velocity = 0
        count = 0

        for i, sprint in enumerate(reversed(completed_sprints)):
            planned = sprint.velocity_points or 0
            completed = sprint.completed_points

            completion_percentage = 0
            if planned > 0:
                completion_percentage = int((completed / planned) * 100)

            velocity_data.append(
                VelocityData(
                    sprint_number=i + 1,
                    sprint_name=sprint.name,
                    planned_points=planned,
                    completed_points=completed,
                    completion_percentage=completion_percentage,
                )
            )

            total_velocity += completed
            count += 1

        average_velocity = total_velocity / count if count > 0 else 0

        return TeamVelocity(
            project_id=project_id,
            average_velocity=average_velocity,
            last_sprints=list(reversed(velocity_data)),
        )

    async def _calculate_completed_points(self, sprint_id: str) -> int:
        """Расчет выполненных story points для спринта"""
        result = await self.db.execute(
            select(SprintTask)
            .options(selectinload(SprintTask.task))
            .where(SprintTask.sprint_id == uuid.UUID(sprint_id))
        )
        sprint_tasks = result.scalars().all()

        completed_points = 0
        for sprint_task in sprint_tasks:
            task = sprint_task.task
            if task and task.status == TaskStatus.DONE:
                story_points = getattr(task, "story_points", 0) or 0
                completed_points += story_points

        return completed_points

    async def get_active_sprint(self, project_id: str) -> Sprint | None:
        """Получение активного спринта проекта"""
        result = await self.db.execute(
            select(Sprint)
            .options(selectinload(Sprint.sprint_tasks).selectinload(SprintTask.task))
            .where(
                and_(
                    Sprint.project_id == uuid.UUID(project_id),
                    Sprint.status == SprintStatus.ACTIVE,
                )
            )
        )
        return result.scalar_one_or_none()

    async def bulk_add_tasks_to_sprint(
        self, sprint_id: str, task_ids: list[str], is_added_mid_sprint: bool = False
    ) -> list[SprintTask]:
        """Массовое добавление задач в спринт"""
        sprint_tasks = []

        for order, task_id in enumerate(task_ids):
            try:
                sprint_task = await self.add_task_to_sprint(
                    sprint_id=sprint_id,
                    task_id=task_id,
                    order=order,
                    is_added_mid_sprint=is_added_mid_sprint,
                )
                sprint_tasks.append(sprint_task)
            except ValueError:
                # Пропускаем задачи, которые уже в спринте
                continue

        return sprint_tasks
