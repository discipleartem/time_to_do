"""
Тесты сервисного слоя
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.user import UserCreate, UserUpdate
from app.services.project_service import ProjectService
from app.services.user_service import UserService


class TestUserService:
    """Тесты пользовательского сервиса"""

    @pytest.fixture
    def user_service(self, db_session: AsyncSession):
        """Создание экземпляра UserService"""
        return UserService(db_session)

    async def test_create_user(self, user_service: UserService, async_user_factory):
        """Тест создания пользователя"""
        user = await async_user_factory()

        assert user.email is not None
        assert user.username is not None
        assert user.full_name is not None
        assert user.is_active is True
        assert user.hashed_password is not None
        assert user.hashed_password != "password123"

    async def test_get_user_by_email(
        self, user_service: UserService, async_user_factory
    ):
        """Тест получения пользователя по email"""
        created_user = await async_user_factory()

        retrieved_user = await user_service.get_user_by_email(created_user.email)

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email

    async def test_get_user_by_id(self, user_service: UserService, async_user_factory):
        """Тест получения пользователя по ID"""
        created_user = await async_user_factory()

        retrieved_user = await user_service.get_user_by_id(created_user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id

    async def test_create_duplicate_email(
        self, user_service: UserService, async_user_factory
    ):
        """Тест создания пользователя с дублирующим email"""
        user = await async_user_factory()

        user_data = UserCreate(
            email=user.email,  # Тот же email
            username="different_user",
            full_name="Different User",
            password="password123",
        )

        with pytest.raises(
            ValueError, match=".*Пользователь с таким email уже существует.*"
        ):  # Должна быть ошибка дублирования
            await user_service.create_user(user_data)

    async def test_update_user(self, user_service: UserService, async_user_factory):
        """Тест обновления пользователя"""
        user = await async_user_factory()

        update_data = UserUpdate(full_name="Updated Name", username="updated_username")

        updated_user = await user_service.update_user(user.id, update_data)

        assert updated_user.full_name == "Updated Name"
        assert updated_user.username == "updated_username"

    async def test_get_user_by_email_not_found(self, user_service: UserService):
        """Тест получения несуществующего пользователя по email"""
        user = await user_service.get_user_by_email("nonexistent@example.com")
        assert user is None

    async def test_authenticate_user_success(
        self, user_service: UserService, async_user_factory
    ):
        """Тест успешной аутентификации пользователя"""
        user = await async_user_factory()

        # Аутентифицируем
        authenticated_user = await user_service.authenticate_user(
            user.email, "password123"  # Стандартный пароль из factory
        )

        assert authenticated_user is not None
        assert authenticated_user.email == user.email

    async def test_authenticate_user_wrong_password(
        self, user_service: UserService, async_user_factory
    ):
        """Тест аутентификации с неверным паролем"""
        user = await async_user_factory()

        # Аутентификация с неверным паролем
        authenticated_user = await user_service.authenticate_user(
            user.email, "wrongpassword"
        )

        assert authenticated_user is None


class TestProjectService:
    """Тесты сервисного слоя задач"""

    @pytest.fixture
    def project_service(self, db_session: AsyncSession):
        """Создание экземпляра ProjectService"""
        return ProjectService(db_session)

    async def test_create_project(
        self,
        project_service: ProjectService,
        test_user_data: dict,
        test_project_data: dict,
    ):
        """Тест создания проекта"""
        # Используем уникальный email
        unique_user_data = test_user_data.copy()
        unique_user_data["email"] = f"test_{uuid.uuid4().hex[:8]}@example.com"
        unique_user_data["username"] = f"testuser_{uuid.uuid4().hex[:8]}"

        # Создаем пользователя
        user_service = UserService(project_service.db)
        user = await user_service.create_user(unique_user_data)

        # Создаем проект
        project = await project_service.create_project(test_project_data, user.id)

        assert project.name == test_project_data["name"]
        assert project.description == test_project_data["description"]
        assert project.owner_id == user.id
        assert project.is_public == test_project_data["is_public"]

    async def test_get_user_projects(
        self,
        project_service: ProjectService,
        test_user_data: dict,
        test_project_data: dict,
        num_projects: int = 3,
    ):
        """Тест получения проектов пользователя"""
        # Используем уникальный email
        unique_user_data = test_user_data.copy()
        unique_user_data["email"] = f"test_{uuid.uuid4().hex[:8]}@example.com"
        unique_user_data["username"] = f"testuser_{uuid.uuid4().hex[:8]}"

        # Создаем пользователя
        user_service = UserService(project_service.db)
        user = await user_service.create_user(unique_user_data)

        # Создаем несколько проектов
        for _ in range(num_projects):
            project_data = test_project_data.copy()
            project_data["name"] = f"Project {_}"
            await project_service.create_project(project_data, user.id)

        # Получаем проекты
        projects = await project_service.get_user_projects(user.id)
        assert len(projects) == num_projects
        assert len(projects) == 3

    async def test_add_project_member(
        self,
        project_service: ProjectService,
        test_user_data: dict,
        test_project_data: dict,
    ):
        """Тест добавления участника в проект"""
        # Создаем двух пользователей
        user_service = UserService(project_service.db)

        # Уникальные данные для владельца
        owner_data = test_user_data.copy()
        owner_data["email"] = f"owner_{uuid.uuid4().hex[:8]}@example.com"
        owner_data["username"] = f"owner_{uuid.uuid4().hex[:8]}"
        owner = await user_service.create_user(owner_data)

        # Уникальные данные для участника
        member_data = test_user_data.copy()
        member_data["email"] = f"member_{uuid.uuid4().hex[:8]}@example.com"
        member_data["username"] = f"member_{uuid.uuid4().hex[:8]}"
        member = await user_service.create_user(member_data)

        # Создаем проект
        project = await project_service.create_project(test_project_data, owner.id)

        # Добавляем участника
        project_member = await project_service.add_project_member(
            project.id, member.id, "member"
        )

        assert project_member.project_id == project.id
        assert project_member.user_id == member.id
        assert project_member.role == "MEMBER"

    async def test_check_project_access_owner(
        self,
        project_service: ProjectService,
        test_user_data: dict,
        test_project_data: dict,
    ):
        """Тест проверки доступа владельца к проекту"""
        # Создаем пользователя и проект
        user_service = UserService(project_service.db)

        unique_data = test_user_data.copy()
        unique_data["email"] = f"owner_{uuid.uuid4().hex[:8]}@example.com"
        unique_data["username"] = f"owner_{uuid.uuid4().hex[:8]}"

        user = await user_service.create_user(unique_data)
        project = await project_service.create_project(test_project_data, user.id)

        # Проверяем доступ
        has_access = await project_service.check_project_access(project.id, user.id)
        assert has_access is True

    async def test_check_project_access_member(
        self,
        project_service: ProjectService,
        test_user_data: dict,
        test_project_data: dict,
    ):
        """Тест проверки доступа участника к проекту"""
        # Создаем пользователей и проект
        user_service = UserService(project_service.db)

        # Уникальные данные для владельца
        owner_data = test_user_data.copy()
        owner_data["email"] = f"owner_{uuid.uuid4().hex[:8]}@example.com"
        owner_data["username"] = f"owner_{uuid.uuid4().hex[:8]}"
        owner_create = UserCreate(**owner_data)
        owner = await user_service.create_user(owner_create)

        # Уникальные данные для участника
        member_data = test_user_data.copy()
        member_data["email"] = f"member_{uuid.uuid4().hex[:8]}@example.com"
        member_data["username"] = f"member_{uuid.uuid4().hex[:8]}"
        member_create = UserCreate(**member_data)
        member = await user_service.create_user(member_create)

        project_create = ProjectCreate(**test_project_data)
        project = await project_service.create_project(project_create, owner.id)
        await project_service.add_project_member(project.id, member.id, "member")

        # Проверяем доступ участника
        has_access = await project_service.check_project_access(project.id, member.id)
        assert has_access is True

    async def test_check_project_access_no_access(
        self,
        project_service: ProjectService,
        test_user_data: dict,
        test_project_data: dict,
    ):
        """Тест проверки доступа пользователя без прав к проекту"""
        # Создаем пользователей и проект
        user_service = UserService(project_service.db)

        # Уникальные данные для владельца
        owner_data = test_user_data.copy()
        owner_data["email"] = f"owner_{uuid.uuid4().hex[:8]}@example.com"
        owner_data["username"] = f"owner_{uuid.uuid4().hex[:8]}"
        owner_create = UserCreate(**owner_data)
        owner = await user_service.create_user(owner_create)

        # Уникальные данные для постороннего
        stranger_data = test_user_data.copy()
        stranger_data["email"] = f"stranger_{uuid.uuid4().hex[:8]}@example.com"
        stranger_data["username"] = f"stranger_{uuid.uuid4().hex[:8]}"
        stranger_create = UserCreate(**stranger_data)
        stranger = await user_service.create_user(stranger_create)

        project_create = ProjectCreate(**test_project_data)
        project = await project_service.create_project(project_create, owner.id)

        # Проверяем доступ постороннего пользователя
        has_access = await project_service.check_project_access(project.id, stranger.id)
        assert has_access is False

    async def test_update_project(
        self,
        project_service: ProjectService,
        test_user_data: dict,
        test_project_data: dict,
    ):
        """Тест обновления проекта"""
        # Создаем пользователя и проект
        user_service = UserService(project_service.db)

        unique_data = test_user_data.copy()
        unique_data["email"] = f"owner_{uuid.uuid4().hex[:8]}@example.com"
        unique_data["username"] = f"owner_{uuid.uuid4().hex[:8]}"
        user_create = UserCreate(**unique_data)

        user = await user_service.create_user(user_create)

        project_create = ProjectCreate(**test_project_data)
        project = await project_service.create_project(project_create, user.id)

        # Обновляем проект
        update_data = ProjectUpdate(
            name="Updated Project",
            description="Updated description",
        )
        updated_project = await project_service.update_project(
            project.id, update_data, user.id
        )

        assert updated_project.name == "Updated Project"
        assert updated_project.description == "Updated description"

    async def test_delete_project(
        self,
        project_service: ProjectService,
        test_user_data: dict,
        test_project_data: dict,
    ):
        """Тест удаления проекта"""
        # Создаем пользователя и проект
        user_service = UserService(project_service.db)

        unique_data = test_user_data.copy()
        unique_data["email"] = f"owner_{uuid.uuid4().hex[:8]}@example.com"
        unique_data["username"] = f"owner_{uuid.uuid4().hex[:8]}"
        user_create = UserCreate(**unique_data)

        user = await user_service.create_user(user_create)

        project_create = ProjectCreate(**test_project_data)
        project = await project_service.create_project(project_create, user.id)

        # Удаляем проект
        await project_service.delete_project(project.id, user.id)

        # Проверяем, что проект удален
        deleted_project = await project_service.get_project_by_id(project.id)
        assert deleted_project is None
