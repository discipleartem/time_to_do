"""
Сервис для управления задачами
"""

import uuid
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session_context
from app.models.project import Project, ProjectMember
from app.models.search import SearchableType
from app.models.task import Comment, Task, TaskStatus
from app.schemas.task import (
    TaskCreate,
    TaskFilter,
    TaskMove,
    TaskStats,
    TaskUpdate,
)
from app.services.search_decorators import auto_index, auto_index_delete


class TaskService:
    """Сервис для работы с задачами"""

    def __init__(self, db: AsyncSession):
        """Инициализация сервиса с сессией базы данных"""
        self.db = db

    @auto_index(SearchableType.TASK)
    async def create_task(
        self, task_data: TaskCreate | dict, project_id: str, creator_id: str
    ) -> Task:
        """
        Создание новой задачи с оптимизированными async паттернами

        Следует лучшим практикам:
        - Оптимизированные запросы с selectinload
        - Правильная обработка ошибок
        - Эффективное использование сессии БД
        """
        # Конвертируем TaskCreate в dict если необходимо
        if hasattr(task_data, "model_dump"):
            data = task_data.model_dump()
        else:
            data = task_data

        # Удаляем project_id из данных, если он там есть (будет установлен из параметра)
        if "project_id" in data:
            data = data.copy()
            del data["project_id"]

        # Проверяем доступ к проекту с оптимизированным запросом
        from uuid import UUID

        project_uuid = UUID(project_id) if isinstance(project_id, str) else project_id
        user_uuid = UUID(creator_id) if isinstance(creator_id, str) else creator_id

        # ✅ Оптимизированный запрос с selectinload
        project = await self.db.execute(
            select(Project)
            .options(selectinload(Project.members))
            .where(Project.id == project_uuid)
        )
        project_result = project.scalar_one_or_none()

        if not project_result:
            raise ValueError("Проект не найден")

        # ✅ Проверка доступа к проекту
        user_has_access = any(
            member.user_id == user_uuid and member.is_active
            for member in project_result.members
        )

        if not user_has_access and project_result.owner_id != user_uuid:
            raise ValueError("Нет доступа к проекту")

        # ✅ Оптимизированная проверка исполнителя
        if data.get("assignee_id"):
            assignee_id = data["assignee_id"]
            assignee_is_member = any(
                member.user_id == assignee_id and member.is_active
                for member in project_result.members
            )

            if not assignee_is_member:
                raise ValueError("Исполнитель не является участником проекта")

        # ✅ Оптимизированный запрос для получения максимального порядка
        max_order_result = await self.db.execute(
            select(func.coalesce(func.max(Task.order), 0)).where(
                and_(
                    Task.project_id == project_id,
                    Task.status == data["status"],
                )
            )
        )
        next_order = (max_order_result.scalar() or 0) + 1

        # ✅ Создаем задачу с правильными полями
        task = Task(
            title=data["title"],
            description=data.get("description"),
            status=data["status"],
            priority=data["priority"],
            story_point=data.get("story_point"),
            due_date=data.get("due_date"),
            estimated_hours=data.get("estimated_hours"),
            parent_task_id=data.get("parent_task_id"),
            assignee_id=data.get("assignee_id"),
            project_id=project_id,
            creator_id=creator_id,
            order=next_order,
        )

        self.db.add(task)
        await self.db.flush()  # Получаем ID без commit

        # ✅ Оптимизированная загрузка связанных данных
        await self.db.refresh(task, ["project", "creator", "assignee", "parent_task"])

        # commit будет выполнен автоматически через get_db()
        return task

    async def get_task_by_id(
        self, task_id: str, user_id: str | None = None
    ) -> Task | None:
        """Получение задачи по ID с проверкой доступа"""
        query = select(Task).where(Task.id == task_id)

        # Если указан user_id, проверяем доступ к проекту
        if user_id:
            query = (
                query.join(Project)
                .join(ProjectMember)
                .where(
                    and_(
                        ProjectMember.user_id == user_id,
                        ProjectMember.is_active,
                    )
                )
            )

        result = await self.db.execute(query)
        task = result.scalar_one_or_none()

        if task:
            await self.db.refresh(
                task,
                [
                    "project",
                    "creator",
                    "assignee",
                    "parent_task",
                    "subtasks",
                    "comments",
                    "time_entries",
                ],
            )

        return task

    async def get_project_tasks(
        self,
        project_id: str,
        user_id: str | None = None,
        filters: TaskFilter | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """Получение задач проекта"""
        # Проверяем доступ к проекту, если указан user_id
        if user_id:
            from uuid import UUID

            project_uuid = (
                UUID(project_id) if isinstance(project_id, str) else project_id
            )
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            project = await self._get_project_with_access_check(project_uuid, user_uuid)
            if not project:
                return []
        else:
            # Если user_id не указан, просто получаем проект
            from app.models.project import Project

            project = await self.db.get(Project, project_id)
            if not project:
                return []

        # Строим запрос
        query = select(Task).where(Task.project_id == project_id)

        # Применяем фильтры
        if filters:
            if filters.status:
                query = query.where(Task.status == filters.status)
            if filters.priority:
                query = query.where(Task.priority == filters.priority)
            if filters.assignee_id:
                query = query.where(Task.assignee_id == filters.assignee_id)
            if filters.creator_id:
                query = query.where(Task.creator_id == filters.creator_id)
            if filters.story_point:
                query = query.where(Task.story_point == filters.story_point)
            if filters.is_archived is not None:
                query = query.where(Task.is_archived == filters.is_archived)
            if filters.search:
                search_term = f"%{filters.search}%"
                query = query.where(
                    or_(
                        Task.title.ilike(search_term),
                        Task.description.ilike(search_term),
                    )
                )

        query = query.order_by(Task.order.asc(), Task.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        tasks = result.scalars().all()

        # Загружаем связи
        for task in tasks:
            await self.db.refresh(task, ["creator", "assignee", "subtasks"])

        return list(tasks)

    @auto_index(SearchableType.TASK)
    async def update_task(
        self, task_id: str, task_data: TaskUpdate, user_id: str
    ) -> Task | None:
        """Обновление задачи"""
        # Проверяем доступ к задаче
        from uuid import UUID

        task_uuid = UUID(task_id) if isinstance(task_id, str) else task_id
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        task = await self._get_task_with_access_check(
            task_uuid, user_uuid, can_edit=True
        )

        if not task:
            return None

        # Обновляем поля
        if hasattr(task_data, "model_dump"):
            update_data: dict[str, Any] = task_data.model_dump(exclude_unset=True)
        else:
            update_data = dict(task_data)  # Явное преобразование в словарь
        for field, value in update_data.items():
            setattr(task, field, value)

        await self.db.commit()
        await self.db.refresh(
            task,
            [
                "project",
                "creator",
                "assignee",
                "parent_task",
                "subtasks",
                "comments",
                "time_entries",
            ],
        )

        return task

    async def move_task_kanban(
        self, task_id: str, move_data: TaskMove | dict, user_id: str
    ) -> Task | None:
        """Перемещение задачи между колонками Kanban"""
        # Конвертируем TaskMove в dict если необходимо
        if hasattr(move_data, "model_dump"):
            data = move_data.model_dump()
        else:
            data = move_data

        # Проверяем доступ к задаче
        from uuid import UUID

        task_uuid = UUID(task_id) if isinstance(task_id, str) else task_id
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        task = await self._get_task_with_access_check(
            task_uuid, user_uuid, can_edit=True
        )

        if not task:
            return None

        old_status = task.status
        new_status = data["status"]

        # Если статус изменился, обновляем порядок
        if old_status != new_status:
            # Получаем максимальный порядок в новой колонке
            max_order = await self.db.execute(
                select(func.coalesce(func.max(Task.order), 0)).where(
                    and_(
                        Task.project_id == task.project_id,
                        Task.status == new_status,
                        Task.id != task_id,
                    )
                )
            )

            next_order = (max_order.scalar() or 0) + 1

            # SQLAlchemy 2.0: используем строковые значения для enum полей
            task.status = new_status  # type: ignore[assignment] # SQLAlchemy Enum field limitation
            task.order = next_order  # type: ignore[assignment] # SQLAlchemy Integer field limitation
        else:
            # Если тот же статус, обновляем только порядок
            if data.get("order") is not None:
                task.order = data["order"]  # type: ignore[assignment] # SQLAlchemy Integer field limitation

        await self.db.commit()
        await self.db.refresh(task, ["project", "creator", "assignee"])

        return task

    @auto_index_delete(SearchableType.TASK)
    async def delete_task(self, task_id: str, user_id: str) -> bool:
        """Удаление задачи"""
        # Проверяем доступ к задаче с подзадачами
        from uuid import UUID

        task_uuid = UUID(task_id) if isinstance(task_id, str) else task_id
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        task = await self._get_task_with_access_check(
            task_uuid, user_uuid, can_edit=True
        )

        if not task:
            return False

        # Загружаем подзадачи для проверки
        await self.db.refresh(task, ["subtasks"])

        # Проверяем, нет ли подзадач
        if task.has_subtasks:
            raise ValueError("Нельзя удалить задачу с подзадачами")

        await self.db.delete(task)
        await self.db.commit()

        return True

    async def bulk_update_tasks(
        self, task_ids: list[str], updates: TaskUpdate, user_id: str
    ) -> list[Task]:
        """Массовое обновление задач"""
        async with get_db_session_context():
            updated_tasks = []

            for task_id in task_ids:
                task = await self.update_task(task_id, updates, user_id)
                if task:
                    updated_tasks.append(task)

            return updated_tasks

    @auto_index(SearchableType.COMMENT)
    async def add_comment(self, task_id: str, user_id: str, content: str) -> Comment:
        """Добавление комментария к задаче"""
        # Проверяем доступ к задаче
        from uuid import UUID

        task_uuid = UUID(task_id) if isinstance(task_id, str) else task_id
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        task = await self._get_task_with_access_check(task_uuid, user_uuid)

        if not task:
            raise ValueError("Нет доступа к задаче")

        # Создаем комментарий
        comment = Comment(
            content=content,
            task_id=task_id,
            author_id=user_id,
        )

        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment, ["task", "author"])

        return comment

    @auto_index(SearchableType.COMMENT)
    async def update_comment(
        self, comment_id: uuid.UUID, user_id: uuid.UUID, content: str
    ) -> Comment | None:
        """Обновление комментария"""
        # Получаем комментарий
        comment = await self.db.get(Comment, comment_id)

        if not comment:
            return None

        # Проверяем, что автор комментария
        if comment.author_id != user_id:
            raise ValueError("Можно редактировать только свои комментарии")

        # Обновляем контент
        comment.content = content  # type: ignore[assignment] # SQLAlchemy Text field limitation
        comment.is_edited = True  # type: ignore[assignment] # SQLAlchemy Boolean field limitation

        await self.db.commit()
        await self.db.refresh(comment, ["task", "author"])

        return comment

    @auto_index_delete(SearchableType.COMMENT)
    async def delete_comment(self, comment_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Удаление комментария"""
        # Получаем комментарий
        comment = await self.db.get(Comment, comment_id)

        if not comment:
            return False

        # Проверяем, что автор комментария или доступ к задаче
        from uuid import UUID

        task_uuid = (
            UUID(comment.task_id)
            if isinstance(comment.task_id, str)
            else comment.task_id
        )
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        task_access = await self._get_task_with_access_check(task_uuid, user_uuid)

        if not task_access and comment.author_id != user_id:
            raise ValueError("Нет доступа к комментарию")

        await self.db.delete(comment)
        await self.db.commit()

        return True

    async def get_task_comments(
        self, task_id: str, user_id: str, skip: int = 0, limit: int = 50
    ) -> list[Comment]:
        """Получение комментариев задачи"""
        # Проверяем доступ к задаче
        from uuid import UUID

        task_uuid = UUID(task_id) if isinstance(task_id, str) else task_id
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        task = await self._get_task_with_access_check(task_uuid, user_uuid)

        if not task:
            return []

        query = (
            select(Comment)
            .where(Comment.task_id == task_id)
            .options(selectinload(Comment.author))
            .order_by(Comment.created_at.asc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        comments = result.scalars().all()

        return list(comments)

    async def get_task_stats(self, project_id: str, user_id: str) -> TaskStats:
        """Получение статистики по задачам проекта"""
        # Проверяем доступ к проекту
        from uuid import UUID

        project_uuid = UUID(project_id) if isinstance(project_id, str) else project_id
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        project = await self._get_project_with_access_check(project_uuid, user_uuid)

        if not project:
            raise ValueError("Нет доступа к проекту")

        # Получаем статистику
        stats = await self.db.execute(
            select(
                func.count(Task.id).label("total"),
                func.sum(func.case((Task.status == TaskStatus.TODO, 1), else_=0)).label(
                    "todo"
                ),
                func.sum(
                    func.case((Task.status == TaskStatus.IN_PROGRESS, 1), else_=0)
                ).label("in_progress"),
                func.sum(
                    func.case((Task.status == TaskStatus.IN_REVIEW, 1), else_=0)
                ).label("in_review"),
                func.sum(func.case((Task.status == TaskStatus.DONE, 1), else_=0)).label(
                    "done"
                ),
                func.sum(
                    func.case((Task.status == TaskStatus.BLOCKED, 1), else_=0)
                ).label("blocked"),
            ).where(and_(Task.project_id == project_id, Task.is_archived.is_(False)))
        )

        task_stats = stats.first()

        # Считаем просроченные задачи
        overdue_count = await self.db.execute(
            select(func.count(Task.id)).where(
                and_(
                    Task.project_id == project_id,
                    Task.due_date.isnot(None),
                    Task.status != TaskStatus.DONE,
                    Task.is_archived.is_(False),
                    # TODO: добавить проверку даты
                )
            )
        )

        return TaskStats(
            total=task_stats.total or 0,
            todo=task_stats.todo or 0,
            in_progress=task_stats.in_progress or 0,
            in_review=task_stats.in_review or 0,
            done=task_stats.done or 0,
            blocked=task_stats.blocked or 0,
            overdue=overdue_count.scalar() or 0,
        )

    async def _get_project_with_access_check(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> Project | None:
        """Проверка доступа к проекту"""
        result = await self.db.execute(
            select(Project)
            .join(ProjectMember)
            .where(
                and_(
                    Project.id == project_id,
                    ProjectMember.user_id == user_id,
                    ProjectMember.is_active,
                )
            )
        )

        return result.scalar_one_or_none()

    async def _get_task_with_access_check(
        self, task_id: uuid.UUID, user_id: uuid.UUID, can_edit: bool = False
    ) -> Task | None:
        """Проверка доступа к задаче"""
        query = select(Task).where(Task.id == task_id)

        # Если нужно проверить доступ
        if user_id:
            query = (
                query.join(Project)
                .join(ProjectMember)
                .where(
                    and_(
                        ProjectMember.user_id == user_id,
                        ProjectMember.is_active,
                    )
                )
            )

        result = await self.db.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            return None

        # Загружаем связи для проверки прав
        await self.db.refresh(task, ["project"])

        # Загружаем членов проекта отдельно
        if task.project:
            await self.db.refresh(task.project, ["members"])

        # Если нужно проверить права редактирования
        if can_edit and user_id:
            member = next(
                (
                    m
                    for m in task.project.members
                    if m.user_id == user_id and m.is_active
                ),
                None,
            )

            if not member or not member.can_edit_tasks:
                return None

        return task

    async def get_comment_by_id(self, comment_id: uuid.UUID) -> Comment | None:
        """Получение комментария по ID"""
        return await self.db.get(Comment, comment_id)

    async def move_task(
        self, task_id: uuid.UUID, new_order: int, user_id: uuid.UUID
    ) -> Task | None:
        """Перемещение задачи (изменение порядка)"""
        # Проверяем доступ к задаче
        from uuid import UUID

        task_uuid = UUID(task_id) if isinstance(task_id, str) else task_id
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        task = await self._get_task_with_access_check(
            task_uuid, user_uuid, can_edit=True
        )

        if not task:
            return None

        old_order = task.order

        # Если порядок не изменился, ничего не делаем
        if old_order == new_order:
            return task

        # Получаем все задачи проекта с их текущим порядком
        result = await self.db.execute(
            select(Task)
            .where(Task.project_id == task.project_id, Task.id != task_id)
            .order_by(Task.order)
        )
        other_tasks = result.scalars().all()

        # Перестраиваем порядок
        if new_order < old_order:
            # Двигаем задачу вверх (уменьшаем порядок)
            for other_task in other_tasks:
                if other_task.order >= new_order and other_task.order < old_order:
                    other_task.order += 1
        else:
            # Двигаем задачу вниз (увеличиваем порядок)
            for other_task in other_tasks:
                if other_task.order > old_order and other_task.order <= new_order:
                    other_task.order -= 1

        # Устанавливаем новый порядок для перемещаемой задачи
        task.order = new_order  # type: ignore[assignment] # SQLAlchemy Integer field limitation

        await self.db.commit()
        await self.db.refresh(task, ["project", "creator", "assignee"])

        return task

    async def assign_task(
        self, task_id: str, assignee_id: str, user_id: str
    ) -> Task | None:
        """Назначение исполнителя задачи"""
        # Проверяем доступ к задаче
        from uuid import UUID

        task_uuid = UUID(task_id) if isinstance(task_id, str) else task_id
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        task = await self._get_task_with_access_check(
            task_uuid, user_uuid, can_edit=True
        )

        if not task:
            return None

        # Проверяем, что исполнитель является участником проекта
        assignee_exists = await self.db.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == task.project_id,
                    ProjectMember.user_id == assignee_id,
                    ProjectMember.is_active,
                )
            )
        )

        if not assignee_exists.scalar_one_or_none():
            raise ValueError("Исполнитель не является участником проекта")

        task.assignee_id = uuid.UUID(assignee_id)
        await self.db.commit()
        await self.db.refresh(task, ["project", "creator", "assignee"])

        return task

    async def get_tasks_by_status(self, project_id: str, status: str) -> list[Task]:
        """Получение задач по статусу"""
        query = (
            select(Task)
            .where(and_(Task.project_id == project_id, Task.status == status))
            .order_by(Task.order.asc())
        )

        result = await self.db.execute(query)
        tasks = result.scalars().all()

        return list(tasks)
