"""
Сервис для управления проектами
"""

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session_context
from app.models.project import Project, ProjectMember, ProjectRole
from app.models.search import SearchableType
from app.models.task import Task
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberUpdate,
    ProjectStats,
    ProjectUpdate,
)
from app.services.search_decorators import auto_index, auto_index_delete


class ProjectService:
    """Сервис для работы с проектами"""

    def __init__(self, db: AsyncSession):
        """Инициализация сервиса с сессией базы данных"""
        self.db = db

    @auto_index(SearchableType.PROJECT)
    async def create_project(
        self, project_data: ProjectCreate | dict, owner_id: str
    ) -> Project:
        """Создание нового проекта"""
        # Конвертируем ProjectCreate в dict если необходимо
        if hasattr(project_data, "model_dump"):
            data = project_data.model_dump()
        else:
            data = project_data

        # Создаем проект
        project = Project(
            name=data["name"],
            description=data["description"],
            status=data["status"],
            is_public=data["is_public"],
            allow_external_sharing=data["allow_external_sharing"],
            max_members=data["max_members"],
            owner_id=owner_id,
        )

        self.db.add(project)
        await self.db.flush()

        # Добавляем владельца как участника с ролью OWNER
        owner_member = ProjectMember(
            project_id=project.id,
            user_id=owner_id,
            role=ProjectRole.OWNER,
            is_active=True,
        )
        self.db.add(owner_member)

        await self.db.commit()
        await self.db.refresh(project)

        # Загружаем связи для ответа
        await self.db.refresh(project, ["owner", "members"])

        return project

    async def get_project_by_id(
        self, project_id: str, user_id: str | None = None
    ) -> Project | None:
        """Получение проекта по ID с проверкой доступа"""
        query = select(Project).where(Project.id == project_id)

        # Если указан user_id, проверяем участие в проекте
        if user_id:
            query = query.join(ProjectMember).where(
                and_(
                    ProjectMember.user_id == user_id,
                    ProjectMember.is_active,
                )
            )

        result = await self.db.execute(query)
        project = result.scalar_one_or_none()

        if project:
            await self.db.refresh(project, ["owner", "members", "tasks", "sprints"])

        return project

    async def get_user_projects(
        self, user_id: str, skip: int = 0, limit: int = 100
    ) -> list[Project]:
        """Получение проектов пользователя"""
        query = (
            select(Project)
            .join(ProjectMember)
            .where(
                and_(
                    ProjectMember.user_id == user_id,
                    ProjectMember.is_active,
                )
            )
            .order_by(Project.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        projects = result.scalars().all()

        # Загружаем связи
        for project in projects:
            await self.db.refresh(project, ["owner", "members"])

        return list(projects)

    @auto_index(SearchableType.PROJECT)
    async def update_project(
        self, project_id: str, project_data: ProjectUpdate, user_id: str
    ) -> Project | None:
        """Обновление проекта"""
        # Проверяем права доступа
        project = await self._get_project_with_permission_check(
            project_id, user_id, can_edit=True
        )

        if not project:
            return None

        # Обновляем поля
        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        await self.db.commit()
        await self.db.refresh(project, ["owner", "members", "tasks", "sprints"])

        return project

    @auto_index_delete(SearchableType.PROJECT)
    async def delete_project(self, project_id: str, user_id: str) -> bool:
        """Удаление проекта"""
        # Проверяем права доступа (только владелец может удалять)
        project = await self._get_project_with_permission_check(
            project_id, user_id, must_be_owner=True
        )

        if not project:
            return False

        await self.db.delete(project)
        await self.db.commit()

        return True

    async def check_project_access(self, project_id: str, user_id: str) -> bool:
        """Проверка доступа пользователя к проекту"""
        project = await self._get_project_with_permission_check(project_id, user_id)
        return project is not None

    async def add_project_member(
        self, project_id: str, user_id: str, role: str = "member"
    ) -> ProjectMember:
        """Добавление участника в проект (упрощенный метод для тестов)"""
        # Проверяем, не является ли пользователь уже участником
        existing_member = await self.db.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                )
            )
        )

        if existing_member.scalar_one_or_none():
            raise ValueError("Пользователь уже является участником проекта")

        # Добавляем участника
        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role=getattr(ProjectRole, role.upper()),
            is_active=True,
        )

        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)

        return member

    async def add_member(
        self, project_id: str, member_data: ProjectMemberCreate, user_id: str
    ) -> ProjectMember | None:
        """Добавление участника в проект"""
        # Проверяем права доступа
        project = await self._get_project_with_permission_check(
            project_id, user_id, can_edit=True
        )

        if not project:
            return None

        # Проверяем, не достигнут ли лимит участников
        if project.is_at_member_limit:
            raise ValueError("Достигнут лимит участников проекта")

        # Проверяем, не является ли пользователь уже участником
        existing_member = await self.db.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == member_data.user_id,
                )
            )
        )

        if existing_member.scalar_one_or_none():
            raise ValueError("Пользователь уже является участником проекта")

        # Проверяем существование пользователя
        user_exists = await self.db.execute(
            select(User).where(User.id == member_data.user_id)
        )

        if not user_exists.scalar_one_or_none():
            raise ValueError("Пользователь не найден")

        # Добавляем участника
        member = ProjectMember(
            project_id=project_id,
            user_id=member_data.user_id,
            role=member_data.role,
            is_active=member_data.is_active,
            invited_by_id=user_id,
        )

        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member, ["user", "project", "invited_by"])

        return member

    async def update_member(
        self,
        project_id: str,
        member_id: str,
        member_data: ProjectMemberUpdate,
        user_id: str,
    ) -> ProjectMember | None:
        """Обновление участника проекта"""
        async with get_db_session_context() as session:
            # Проверяем права доступа
            project = await self._get_project_with_permission_check(
                project_id, user_id, can_edit=False, must_be_owner=True
            )

            if not project:
                return None

            # Получаем участника
            member = await session.get(ProjectMember, member_id)

            if not member or member.project_id != project_id:
                return None

            # Обновляем поля
            update_data = member_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(member, field, value)

            await session.commit()
            await session.refresh(member, ["user", "project", "invited_by"])

            return member

    async def remove_member(
        self, project_id: str, member_id: str, user_id: str
    ) -> bool:
        """Удаление участника из проекта"""
        async with get_db_session_context() as session:
            # Проверяем права доступа
            project = await self._get_project_with_permission_check(
                project_id, user_id, can_edit=False, must_be_owner=True
            )

            if not project:
                return False

            # Получаем участника
            member = await session.get(ProjectMember, member_id)

            if not member or member.project_id != project_id:
                return False

            # Нельзя удалить владельца проекта
            if member.role == ProjectRole.OWNER:
                raise ValueError("Нельзя удалить владельца проекта")

            await session.delete(member)
            await session.commit()

            return True

    async def get_project_members(
        self, project_id: str, user_id: str
    ) -> list[ProjectMember]:
        """Получение участников проекта"""
        async with get_db_session_context() as session:
            # Проверяем права доступа
            project = await self._get_project_with_permission_check(project_id, user_id)

            if not project:
                return []

            query = (
                select(ProjectMember)
                .where(ProjectMember.project_id == project_id)
                .options(selectinload(ProjectMember.user))
                .order_by(ProjectMember.role.desc(), ProjectMember.created_at.asc())
            )

            result = await session.execute(query)
            members = result.scalars().all()

            return list(members)

    async def get_project_stats(self, project_id: str, user_id: str) -> ProjectStats:
        """Получение статистики проекта"""
        async with get_db_session_context() as session:
            # Проверяем права доступа
            project = await self._get_project_with_permission_check(project_id, user_id)

            if not project:
                raise ValueError("Проект не найден или нет доступа")

            # Получаем статистику по задачам
            task_stats = await session.execute(
                select(
                    func.count(Task.id).label("total_tasks"),
                    func.sum(func.case((Task.status == "done", 1), else_=0)).label(
                        "completed_tasks"
                    ),
                    func.sum(func.case((Task.status == "todo", 1), else_=0)).label(
                        "todo_tasks"
                    ),
                    func.sum(
                        func.case((Task.status == "in_progress", 1), else_=0)
                    ).label("in_progress_tasks"),
                    func.sum(func.case((Task.status == "done", 1), else_=0)).label(
                        "done_tasks"
                    ),
                    func.sum(func.case((Task.status == "blocked", 1), else_=0)).label(
                        "blocked_tasks"
                    ),
                ).where(Task.project_id == project_id)
            )

            stats = task_stats.first()

            # Получаем количество участников
            member_count = await session.execute(
                select(func.count(ProjectMember.id)).where(
                    and_(
                        ProjectMember.project_id == project_id,
                        ProjectMember.is_active,
                        ProjectMember.role != ProjectRole.VIEWER,
                    )
                )
            )

            return ProjectStats(
                total_tasks=stats.total_tasks or 0,
                completed_tasks=stats.completed_tasks or 0,
                todo_tasks=stats.todo_tasks or 0,
                in_progress_tasks=stats.in_progress_tasks or 0,
                done_tasks=stats.done_tasks or 0,
                blocked_tasks=stats.blocked_tasks or 0,
                total_members=member_count.scalar() or 0,
                active_members=member_count.scalar() or 0,
            )

    async def _get_project_with_permission_check(
        self,
        project_id: str,
        user_id: str,
        can_edit: bool = False,
        must_be_owner: bool = False,
    ) -> Project | None:
        """Внутренний метод для проверки прав доступа к проекту"""

        query = select(Project).where(Project.id == project_id)

        # Если нужно проверить участие в проекте
        if user_id:
            query = query.join(ProjectMember).where(
                and_(ProjectMember.user_id == user_id, ProjectMember.is_active)
            )

        result = await self.db.execute(query)
        project = result.scalar_one_or_none()

        if not project:
            return None

        # Загружаем связи для проверки прав
        await self.db.refresh(project, ["members"])

        # Проверяем права
        if user_id:
            member = next(
                (m for m in project.members if m.user_id == user_id and m.is_active),
                None,
            )

            if not member:
                return None

            if must_be_owner and member.role != ProjectRole.OWNER:
                return None

            if can_edit and not member.can_edit_tasks:
                return None

        return project
