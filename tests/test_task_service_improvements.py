"""
Улучшенные тесты для Task Service согласно лучшим практикам
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMember
from app.models.user import User
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService


@pytest.mark.asyncio
class TestTaskServiceSkills:
    """
    Тесты для TaskService с лучшими практиками:
    - Async тестирование с правильной изоляцией
    - Оптимизированные фикстуры
    - Правильная проверка исключений
    - Эффективное использование БД
    """

    async def test_create_task_success(
        self, db_session: AsyncSession, test_user_data: dict, test_project_data: dict
    ):
        """
        ✅ Правильный async тест для создания задачи
        Следует лучшим практикам
        """
        # Создаем пользователя и проект
        from app.core.security import get_password_hash

        user_data = test_user_data.copy()
        user_data["hashed_password"] = get_password_hash(user_data.pop("password"))

        user = User(**user_data)
        db_session.add(user)
        await db_session.flush()

        project = Project(**test_project_data, owner_id=user.id)
        db_session.add(project)
        await db_session.flush()

        # Создаем сервис
        task_service = TaskService(db_session)

        # Добавляем пользователя в проект
        member = ProjectMember(
            project_id=project.id, user_id=user.id, role="MEMBER", is_active=True
        )
        db_session.add(member)
        await db_session.commit()

        # Создаем задачу
        task_data = TaskCreate(
            title="Test Task",
            description="Test Description",
            status="todo",
            priority="medium",
            story_point="5",
            project_id=str(project.id),
        )

        task = await task_service.create_task(
            task_data=task_data,
            project_id=str(project.id),
            creator_id=str(user.id),
        )

        # ✅ Проверяем данные задачи
        assert task.title == "Test Task"
        assert task.description == "Test Description"
        assert task.status == "todo"
        assert task.priority == "medium"
        assert task.story_point == "5"
        assert str(task.project_id) == str(project.id)
        assert str(task.creator_id) == str(user.id)
        assert task.order == 1  # Первая задача в колонке

    async def test_create_task_unauthorized_user(
        self, db_session: AsyncSession, test_user_data: dict, test_project_data: dict
    ):
        """
        ✅ Тест проверки авторизации с правильной обработкой исключений
        """
        from app.core.security import get_password_hash

        # Создаем владельца проекта
        owner_data = test_user_data.copy()
        owner_data["email"] = "owner@example.com"
        owner_data["username"] = "owner"
        owner_data["hashed_password"] = get_password_hash(owner_data.pop("password"))

        owner = User(**owner_data)
        db_session.add(owner)
        await db_session.flush()

        # Создаем обычного пользователя (не владелец)
        user_data = test_user_data.copy()
        user_data["email"] = "unauthorized@example.com"
        user_data["username"] = "unauthorized"
        user_data["hashed_password"] = get_password_hash(user_data.pop("password"))

        user = User(**user_data)
        db_session.add(user)
        await db_session.flush()

        # Создаем проект с владельцем
        project = Project(**test_project_data, owner_id=owner.id)
        db_session.add(project)
        await db_session.flush()

        task_service = TaskService(db_session)

        # НЕ добавляем пользователя в проект
        task_data = TaskCreate(
            title="Unauthorized Task",
            status="todo",
            priority="low",
            project_id=str(project.id),
        )

        # ✅ Правильная проверка исключения
        with pytest.raises(ValueError, match="Нет доступа к проекту"):
            await task_service.create_task(
                task_data=task_data,
                project_id=str(project.id),
                creator_id=str(user.id),  # Обычный пользователь, не владелец
            )

    async def test_create_task_invalid_assignee(
        self, db_session: AsyncSession, test_user_data: dict, test_project_data: dict
    ):
        """
        Тест валидации исполнителя
        """
        from app.core.security import get_password_hash

        # Создаем пользователя и проект
        user_data = test_user_data.copy()
        user_data["hashed_password"] = get_password_hash(user_data.pop("password"))

        user = User(**user_data)
        db_session.add(user)
        await db_session.flush()

        project = Project(**test_project_data, owner_id=user.id)
        db_session.add(project)
        await db_session.flush()

        task_service = TaskService(db_session)

        # Добавляем пользователя в проект
        member = ProjectMember(
            project_id=project.id,
            user_id=user.id,
            role="MEMBER",
            is_active=True,
        )
        db_session.add(member)
        await db_session.commit()

        # Создаем другого пользователя для назначения
        other_user = User(
            email="other@example.com",
            username="otheruser",
            full_name="Other User",
            hashed_password=get_password_hash("password123"),
        )
        db_session.add(other_user)
        await db_session.commit()

        task_data = TaskCreate(
            title="Task with Invalid Assignee",
            status="todo",
            priority="medium",
            project_id=str(project.id),
            assignee_id=str(other_user.id),  # Не является участником
        )

        # Проверка валидации исполнителя
        with pytest.raises(
            ValueError, match="Исполнитель не является участником проекта"
        ):
            await task_service.create_task(
                task_data=task_data,
                project_id=str(project.id),
                creator_id=str(user.id),
            )

    async def test_create_task_order_increment(
        self, db_session: AsyncSession, test_user_data: dict, test_project_data: dict
    ):
        """
        Тест правильного порядка задач
        """
        from app.core.security import get_password_hash

        # Создаем пользователя и проект
        user_data = test_user_data.copy()
        user_data["hashed_password"] = get_password_hash(user_data.pop("password"))

        user = User(**user_data)
        db_session.add(user)
        await db_session.flush()

        project = Project(**test_project_data, owner_id=user.id)
        db_session.add(project)
        await db_session.flush()

        task_service = TaskService(db_session)

        # Добавляем пользователя в проект
        member = ProjectMember(
            project_id=project.id,
            user_id=user.id,
            role="MEMBER",
            is_active=True,
        )
        db_session.add(member)
        await db_session.commit()

        # Создаем первую задачу
        task_data1 = TaskCreate(
            title="First Task",
            status="todo",
            priority="low",
            project_id=str(project.id),
        )

        task1 = await task_service.create_task(
            task_data=task_data1,
            project_id=str(project.id),
            creator_id=str(user.id),
        )

        # Создаем вторую задачу в том же статусе
        task_data2 = TaskCreate(
            title="Second Task",
            status="todo",
            priority="low",
            project_id=str(project.id),
        )

        task2 = await task_service.create_task(
            task_data=task_data2,
            project_id=str(project.id),
            creator_id=str(user.id),
        )

        # Проверяем правильный порядок
        assert task1.order == 1
        assert task2.order == 2

    async def test_create_task_with_parent(
        self, db_session: AsyncSession, test_user_data: dict, test_project_data: dict
    ):
        """
        Тест создания подзадачи
        """
        from app.core.security import get_password_hash

        # Создаем пользователя и проект
        user_data = test_user_data.copy()
        user_data["hashed_password"] = get_password_hash(user_data.pop("password"))

        user = User(**user_data)
        db_session.add(user)
        await db_session.flush()

        project = Project(**test_project_data, owner_id=user.id)
        db_session.add(project)
        await db_session.flush()

        task_service = TaskService(db_session)

        # Добавляем пользователя в проект
        member = ProjectMember(
            project_id=project.id,
            user_id=user.id,
            role="MEMBER",
            is_active=True,
        )
        db_session.add(member)
        await db_session.commit()

        # Создаем родительскую задачу
        parent_task_data = TaskCreate(
            title="Parent Task",
            status="todo",
            priority="high",
            project_id=str(project.id),
        )

        parent_task = await task_service.create_task(
            task_data=parent_task_data,
            project_id=str(project.id),
            creator_id=str(user.id),
        )

        # Создаем дочернюю задачу
        child_task_data = TaskCreate(
            title="Child Task",
            status="todo",
            priority="medium",
            project_id=str(project.id),
            parent_task_id=str(parent_task.id),
        )

        child_task = await task_service.create_task(
            task_data=child_task_data,
            project_id=str(project.id),
            creator_id=str(user.id),
        )

        # ✅ Проверяем иерархию
        assert child_task.parent_task_id == str(parent_task.id)
        assert child_task.order == 2  # Вторая задача в колонке

    async def test_create_task_optimized_queries(
        self, db_session: AsyncSession, test_user_data: dict, test_project_data: dict
    ):
        """
        ✅ Тест оптимизации запросов с selectinload
        """
        from app.core.security import get_password_hash

        # Создаем пользователя и проект
        user_data = test_user_data.copy()
        user_data["hashed_password"] = get_password_hash(user_data.pop("password"))

        user = User(**user_data)
        db_session.add(user)
        await db_session.flush()

        project = Project(**test_project_data, owner_id=user.id)
        db_session.add(project)
        await db_session.flush()

        task_service = TaskService(db_session)

        # Добавляем пользователя в проект
        member = ProjectMember(
            project_id=project.id,
            user_id=user.id,
            role="MEMBER",
            is_active=True,
        )
        db_session.add(member)
        await db_session.commit()

        task_data = TaskCreate(
            title="Optimized Task",
            description="Task with optimized queries",
            status="in_progress",
            priority="high",
            story_point="8",
            project_id=str(project.id),
        )

        # ✅ Выполняем операцию
        task = await task_service.create_task(
            task_data=task_data,
            project_id=str(project.id),
            creator_id=str(user.id),
        )

        # ✅ Проверяем, что связанные данные загружены (благодаря selectinload)
        assert task.project is not None
        assert task.creator is not None
        assert task.project.id == project.id
        assert task.creator.id == user.id

    @pytest.mark.parametrize("status", ["todo", "in_progress", "in_review"])
    async def test_create_task_different_statuses(
        self,
        db_session: AsyncSession,
        test_user_data: dict,
        test_project_data: dict,
        status: str,
    ):
        """
        ✅ Параметризованный тест для разных статусов
        """
        from app.core.security import get_password_hash

        # Создаем пользователя и проект
        user_data = test_user_data.copy()
        user_data["hashed_password"] = get_password_hash(user_data.pop("password"))

        user = User(**user_data)
        db_session.add(user)
        await db_session.flush()

        project = Project(**test_project_data, owner_id=user.id)
        db_session.add(project)
        await db_session.flush()

        task_service = TaskService(db_session)

        # Добавляем пользователя в проект
        member = ProjectMember(
            project_id=project.id,
            user_id=user.id,
            role="MEMBER",
            is_active=True,
        )
        db_session.add(member)
        await db_session.commit()

        task_data = TaskCreate(
            title=f"Task in {status}",
            status=status,
            priority="medium",
            project_id=str(project.id),
        )

        task = await task_service.create_task(
            task_data=task_data,
            project_id=str(project.id),
            creator_id=str(user.id),
        )

        # ✅ Проверяем статус
        assert task.status == status
        assert task.order == 1  # Первая задача в каждой колонке статуса
