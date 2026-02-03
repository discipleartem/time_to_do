"""
Улучшенные тесты для Task Service согласно лучшим практикам
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMember
from app.models.task import TaskPriority, TaskStatus
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

        user = User(**test_user_data)
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

        # Данные для создания задачи
        task_data = TaskCreate(
            title="Test Task",
            description="Test Description",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            story_point="5",
            project_id=str(project.id),
        )

        # ✅ Выполняем тестируемую операцию
        task = await task_service.create_task(
            task_data=task_data, project_id=str(project.id), creator_id=str(user.id)
        )

        # ✅ Правильные проверки
        assert task is not None
        assert task.title == "Test Task"
        assert task.description == "Test Description"
        assert task.status == TaskStatus.TODO
        assert task.priority == TaskPriority.MEDIUM
        assert task.story_point == "5"
        assert str(task.project_id) == str(project.id)
        assert str(task.creator_id) == str(user.id)
        assert task.order == 1  # Первая задача в колонке

    async def test_create_task_unauthorized_user(
        self, db: AsyncSession, sample_user: User, sample_project: Project
    ):
        """
        ✅ Тест проверки авторизации с правильной обработкой исключений
        """
        task_service = TaskService(db)

        # НЕ добавляем пользователя в проект
        task_data = TaskCreate(
            title="Unauthorized Task", status=TaskStatus.TODO, priority=TaskPriority.LOW
        )

        # ✅ Правильная проверка исключения
        with pytest.raises(ValueError, match="Нет доступа к проекту"):
            await task_service.create_task(
                task_data=task_data,
                project_id=str(sample_project.id),
                creator_id=str(sample_user.id),
            )

    async def test_create_task_invalid_assignee(
        self, db: AsyncSession, sample_user: User, sample_project: Project
    ):
        """
        ✅ Тест валидации исполнителя
        """
        task_service = TaskService(db)

        # Добавляем пользователя как member
        member = ProjectMember(
            project_id=sample_project.id,
            user_id=sample_user.id,
            role="MEMBER",
            is_active=True,
        )
        db.add(member)
        await db.commit()

        # Создаем другого пользователя для назначения
        other_user = User(
            email="other@example.com", username="otheruser", full_name="Other User"
        )
        db.add(other_user)
        await db.commit()

        task_data = TaskCreate(
            title="Task with Invalid Assignee",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee_id=str(other_user.id),  # Не является участником
        )

        # ✅ Проверка валидации исполнителя
        with pytest.raises(
            ValueError, match="Исполнитель не является участником проекта"
        ):
            await task_service.create_task(
                task_data=task_data,
                project_id=str(sample_project.id),
                creator_id=str(sample_user.id),
            )

    async def test_create_task_order_increment(
        self, db: AsyncSession, sample_user: User, sample_project: Project
    ):
        """
        ✅ Тест правильного порядка задач
        """
        task_service = TaskService(db)

        # Добавляем пользователя в проект
        member = ProjectMember(
            project_id=sample_project.id,
            user_id=sample_user.id,
            role="member",
            is_active=True,
        )
        db.add(member)
        await db.commit()

        # Создаем первую задачу
        task_data1 = TaskCreate(
            title="First Task", status=TaskStatus.TODO, priority=TaskPriority.LOW
        )

        task1 = await task_service.create_task(
            task_data=task_data1,
            project_id=str(sample_project.id),
            creator_id=str(sample_user.id),
        )

        # Создаем вторую задачу в том же статусе
        task_data2 = TaskCreate(
            title="Second Task", status=TaskStatus.TODO, priority=TaskPriority.LOW
        )

        task2 = await task_service.create_task(
            task_data=task_data2,
            project_id=str(sample_project.id),
            creator_id=str(sample_user.id),
        )

        # ✅ Проверяем правильный порядок
        assert task1.order == 1
        assert task2.order == 2

    async def test_create_task_with_parent(
        self, db: AsyncSession, sample_user: User, sample_project: Project
    ):
        """
        ✅ Тест создания подзадачи
        """
        task_service = TaskService(db)

        # Добавляем пользователя в проект
        member = ProjectMember(
            project_id=sample_project.id,
            user_id=sample_user.id,
            role="member",
            is_active=True,
        )
        db.add(member)
        await db.commit()

        # Создаем родительскую задачу
        parent_task_data = TaskCreate(
            title="Parent Task", status=TaskStatus.TODO, priority=TaskPriority.HIGH
        )

        parent_task = await task_service.create_task(
            task_data=parent_task_data,
            project_id=str(sample_project.id),
            creator_id=str(sample_user.id),
        )

        # Создаем дочернюю задачу
        child_task_data = TaskCreate(
            title="Child Task",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            parent_task_id=str(parent_task.id),
        )

        child_task = await task_service.create_task(
            task_data=child_task_data,
            project_id=str(sample_project.id),
            creator_id=str(sample_user.id),
        )

        # ✅ Проверяем иерархию
        assert child_task.parent_task_id == parent_task.id
        assert child_task.order == 2  # Вторая задача в колонке

    async def test_create_task_optimized_queries(
        self, db: AsyncSession, sample_user: User, sample_project: Project
    ):
        """
        ✅ Тест оптимизации запросов с selectinload
        """
        task_service = TaskService(db)

        # Добавляем пользователя в проект
        member = ProjectMember(
            project_id=sample_project.id,
            user_id=sample_user.id,
            role="member",
            is_active=True,
        )
        db.add(member)
        await db.commit()

        task_data = TaskCreate(
            title="Optimized Task",
            description="Task with optimized queries",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            story_point=8,
        )

        # ✅ Выполняем операцию
        task = await task_service.create_task(
            task_data=task_data,
            project_id=str(sample_project.id),
            creator_id=str(sample_user.id),
        )

        # ✅ Проверяем, что связанные данные загружены (благодаря selectinload)
        assert task.project is not None
        assert task.creator is not None
        assert task.project.id == sample_project.id
        assert task.creator.id == sample_user.id

    @pytest.mark.parametrize(
        "status", [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW]
    )
    async def test_create_task_different_statuses(
        self,
        db: AsyncSession,
        sample_user: User,
        sample_project: Project,
        status: TaskStatus,
    ):
        """
        ✅ Параметризованный тест для разных статусов
        """
        task_service = TaskService(db)

        # Добавляем пользователя в проект
        member = ProjectMember(
            project_id=sample_project.id,
            user_id=sample_user.id,
            role="member",
            is_active=True,
        )
        db.add(member)
        await db.commit()

        task_data = TaskCreate(
            title=f"Task in {status.value}", status=status, priority=TaskPriority.MEDIUM
        )

        task = await task_service.create_task(
            task_data=task_data,
            project_id=str(sample_project.id),
            creator_id=str(sample_user.id),
        )

        # ✅ Проверяем статус
        assert task.status == status
        assert task.order == 1  # Первая задача в каждой колонке статуса
