"""
Комплексные тесты для UserService
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ValidationError
from app.models.user import UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService


class TestUserServiceComprehensive:
    """Комплексные тесты для UserService"""

    @pytest.fixture
    def user_service(self, db_session: AsyncSession):
        """Создание экземпляра UserService"""
        return UserService(db_session)

    @pytest.fixture
    def test_user_data(self):
        """Тестовые данные пользователя"""
        return {
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "password": "password123",
            "role": "USER",
        }

    @pytest.fixture
    def user_create_schema(self, test_user_data):
        """UserCreate схема"""
        return UserCreate(**test_user_data)

    # Тесты создания пользователя
    @pytest.mark.asyncio
    async def test_create_user_success_dict(self, user_service, test_user_data):
        """Тест успешного создания пользователя из dict"""
        user = await user_service.create_user(test_user_data)

        assert user.email == test_user_data["email"]
        assert user.username == test_user_data["username"]
        assert user.full_name == test_user_data["full_name"]
        assert user.is_active is True
        assert user.role == UserRole.USER
        assert user.hashed_password is not None
        assert user.id is not None

    @pytest.mark.asyncio
    async def test_create_user_success_schema(self, user_service, user_create_schema):
        """Тест успешного создания пользователя из UserCreate"""
        user = await user_service.create_user(user_create_schema)

        assert user.email == user_create_schema.email
        assert user.username == user_create_schema.username
        assert user.full_name == user_create_schema.full_name

    @pytest.mark.asyncio
    async def test_create_user_email_conflict(self, user_service, test_user_data):
        """Тест создания пользователя с существующим email"""
        # Создаем первого пользователя
        await user_service.create_user(test_user_data)

        # Пытаемся создать второго с тем же email
        with pytest.raises(
            ValueError, match="Пользователь с таким email уже существует"
        ):
            await user_service.create_user(test_user_data)

    @pytest.mark.asyncio
    async def test_create_user_username_conflict(self, user_service, test_user_data):
        """Тест создания пользователя с существующим username"""
        # Создаем первого пользователя
        await user_service.create_user(test_user_data)

        # Пытаемся создать второго с тем же username
        conflicting_data = test_user_data.copy()
        conflicting_data["email"] = "different@example.com"

        with pytest.raises(
            ValueError, match="Пользователь с таким username уже существует"
        ):
            await user_service.create_user(conflicting_data)

    @pytest.mark.asyncio
    async def test_create_user_without_username(self, user_service, test_user_data):
        """Тест создания пользователя без username"""
        data = test_user_data.copy()
        del data["username"]

        user = await user_service.create_user(data)

        assert user.username is None
        assert user.email == data["email"]

    @pytest.mark.asyncio
    async def test_create_user_with_role(self, user_service, test_user_data):
        """Тест создания пользователя с ролью"""
        data = test_user_data.copy()
        data["role"] = "ADMIN"

        user = await user_service.create_user(data)

        assert user.role == UserRole.ADMIN

    # Тесты получения пользователя
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, user_service, test_user_data):
        """Тест получения пользователя по ID"""
        created_user = await user_service.create_user(test_user_data)

        found_user = await user_service.get_user_by_id(created_user.id)

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == created_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_service):
        """Тест получения несуществующего пользователя по ID"""
        fake_id = str(uuid.uuid4())

        user = await user_service.get_user_by_id(fake_id)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self, user_service, test_user_data):
        """Тест получения пользователя по email"""
        created_user = await user_service.create_user(test_user_data)

        found_user = await user_service.get_user_by_email(created_user.email)

        assert found_user is not None
        assert found_user.email == created_user.email
        assert found_user.id == created_user.id

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, user_service):
        """Тест получения несуществующего пользователя по email"""
        user = await user_service.get_user_by_email("nonexistent@example.com")

        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_username_success(self, user_service, test_user_data):
        """Тест получения пользователя по username"""
        created_user = await user_service.create_user(test_user_data)

        found_user = await user_service.get_user_by_username(created_user.username)

        assert found_user is not None
        assert found_user.username == created_user.username
        assert found_user.id == created_user.id

    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self, user_service):
        """Тест получения несуществующего пользователя по username"""
        user = await user_service.get_user_by_username("nonexistent")

        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_github_id_success(self, user_service, test_user_data):
        """Тест получения пользователя по GitHub ID"""
        data = test_user_data.copy()
        data["github_id"] = "12345"

        created_user = await user_service.create_user(data)

        found_user = await user_service.get_user_by_github_id("12345")

        assert found_user is not None
        assert found_user.github_id == "12345"
        assert found_user.id == created_user.id

    @pytest.mark.asyncio
    async def test_get_user_by_github_id_not_found(self, user_service):
        """Тест получения несуществующего пользователя по GitHub ID"""
        user = await user_service.get_user_by_github_id("nonexistent")

        assert user is None

    # Тесты аутентификации
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, user_service, test_user_data):
        """Тест успешной аутентификации"""
        user = await user_service.create_user(test_user_data)

        authenticated_user = await user_service.authenticate_user(
            user.email, "validpassword"
        )

        assert authenticated_user is not None
        assert authenticated_user.id == user.id

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, user_service, test_user_data):
        """Тест аутентификации с неверным паролем"""
        user = await user_service.create_user(test_user_data)

        authenticated_user = await user_service.authenticate_user(
            user.email, "wrongpassword"
        )

        assert authenticated_user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, user_service):
        """Тест аутентификации несуществующего пользователя"""
        authenticated_user = await user_service.authenticate_user(
            "nonexistent@example.com", "password"
        )

        assert authenticated_user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, user_service, test_user_data):
        """Тест аутентификации неактивного пользователя"""
        data = test_user_data.copy()
        data["is_active"] = False

        user = await user_service.create_user(data)

        authenticated_user = await user_service.authenticate_user(
            user.email, "validpassword"
        )

        assert authenticated_user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_empty_password(self, user_service, test_user_data):
        """Тест аутентификации с пустым паролем"""
        user = await user_service.create_user(test_user_data)

        authenticated_user = await user_service.authenticate_user(user.email, "")

        assert authenticated_user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_short_password(self, user_service, test_user_data):
        """Тест аутентификации с коротким паролем"""
        user = await user_service.create_user(test_user_data)

        authenticated_user = await user_service.authenticate_user(user.email, "ab")

        assert authenticated_user is None

    # Тесты обновления пользователя
    @pytest.mark.asyncio
    async def test_update_user_success(self, user_service, test_user_data):
        """Тест успешного обновления пользователя"""
        user = await user_service.create_user(test_user_data)

        update_data = UserUpdate(full_name="Updated Name", username="updated_username")

        updated_user = await user_service.update_user(user.id, update_data)

        assert updated_user is not None
        assert updated_user.full_name == "Updated Name"
        assert updated_user.username == "updated_username"
        assert updated_user.email == user.email  # Не изменилось

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_service):
        """Тест обновления несуществующего пользователя"""
        fake_id = uuid.uuid4()
        update_data = UserUpdate(full_name="Updated Name")

        updated_user = await user_service.update_user(fake_id, update_data)

        assert updated_user is None

    @pytest.mark.asyncio
    async def test_update_user_email_conflict(self, user_service, test_user_data):
        """Тест обновления с конфликтующим email"""
        # Создаем двух пользователей
        user1 = await user_service.create_user(test_user_data)

        user2_data = test_user_data.copy()
        user2_data["email"] = "user2@example.com"
        user2_data["username"] = "user2"
        user2 = await user_service.create_user(user2_data)

        # Пытаемся обновить email пользователя 2 на email пользователя 1
        update_data = UserUpdate(email=user1.email)

        with pytest.raises(
            ValueError, match="Пользователь с таким email уже существует"
        ):
            await user_service.update_user(user2.id, update_data)

    @pytest.mark.asyncio
    async def test_update_user_username_conflict(self, user_service, test_user_data):
        """Тест обновления с конфликтующим username"""
        # Создаем двух пользователей
        user1 = await user_service.create_user(test_user_data)

        user2_data = test_user_data.copy()
        user2_data["email"] = "user2@example.com"
        user2_data["username"] = "user2"
        user2 = await user_service.create_user(user2_data)

        # Пытаемся обновить username пользователя 2 на username пользователя 1
        update_data = UserUpdate(username=user1.username)

        with pytest.raises(
            ValueError, match="Пользователь с таким username уже существует"
        ):
            await user_service.update_user(user2.id, update_data)

    # Тесты управления паролем
    @pytest.mark.asyncio
    async def test_update_password_success(self, user_service, test_user_data):
        """Тест успешного обновления пароля"""
        user = await user_service.create_user(test_user_data)
        old_password = user.hashed_password

        result = await user_service.update_password(user.id, "newpassword123")

        assert result is True
        # Проверяем, что пароль изменился через тот же сервис
        updated_user = await user_service.get_user_by_id(str(user.id))
        assert updated_user.hashed_password != old_password

    @pytest.mark.asyncio
    async def test_update_password_user_not_found(self, user_service):
        """Тест обновления пароля несуществующего пользователя"""
        fake_id = uuid.uuid4()

        result = await user_service.update_password(fake_id, "newpassword")

        assert result is False

    # Тесты активации/деактивации
    @pytest.mark.asyncio
    async def test_deactivate_user_success(self, user_service, test_user_data):
        """Тест успешной деактивации пользователя"""
        user = await user_service.create_user(test_user_data)

        result = await user_service.deactivate_user(user.id)

        assert result is True
        # Проверяем, что пользователь деактивирован
        deactivated_user = await user_service.get_user_by_id(user.id)
        assert deactivated_user.is_active is False

    @pytest.mark.asyncio
    async def test_deactivate_user_not_found(self, user_service):
        """Тест деактивации несуществующего пользователя"""
        fake_id = uuid.uuid4()

        result = await user_service.deactivate_user(fake_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_activate_user_success(self, user_service, test_user_data):
        """Тест успешной активации пользователя"""
        data = test_user_data.copy()
        data["is_active"] = False

        user = await user_service.create_user(data)

        result = await user_service.activate_user(user.id)

        assert result is True
        # Проверяем, что пользователь активирован
        activated_user = await user_service.get_user_by_id(user.id)
        assert activated_user.is_active is True

    @pytest.mark.asyncio
    async def test_activate_user_not_found(self, user_service):
        """Тест активации несуществующего пользователя"""
        fake_id = uuid.uuid4()

        result = await user_service.activate_user(fake_id)

        assert result is False

    # Тесты верификации
    @pytest.mark.asyncio
    async def test_verify_user_success(self, user_service, test_user_data):
        """Тест успешной верификации пользователя"""
        user = await user_service.create_user(test_user_data)

        result = await user_service.verify_user(user.id)

        assert result is True
        # Проверяем, что пользователь верифицирован
        verified_user = await user_service.get_user_by_id(user.id)
        assert verified_user.is_verified is True

    @pytest.mark.asyncio
    async def test_verify_user_not_found(self, user_service):
        """Тест верификации несуществующего пользователя"""
        fake_id = uuid.uuid4()

        result = await user_service.verify_user(fake_id)

        assert result is False

    # Тесты получения профиля
    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, user_service, test_user_data):
        """Тест успешного получения профиля пользователя"""
        user = await user_service.create_user(test_user_data)

        profile = await user_service.get_user_profile(user.id)

        assert profile is not None
        assert profile.id == str(user.id)
        assert profile.email == user.email
        assert profile.username == user.username
        assert profile.project_count >= 0
        assert profile.task_count >= 0
        assert profile.completed_task_count >= 0

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self, user_service):
        """Тест получения профиля несуществующего пользователя"""
        fake_id = uuid.uuid4()

        profile = await user_service.get_user_profile(fake_id)

        assert profile is None

    # Тесты поиска пользователей
    @pytest.mark.asyncio
    async def test_search_users_by_username(self, user_service, test_user_data):
        """Тест поиска пользователей по username"""
        user = await user_service.create_user(test_user_data)

        results = await user_service.search_users("test")

        assert len(results) >= 1
        found_user = next((u for u in results if u.id == user.id), None)
        assert found_user is not None

    @pytest.mark.asyncio
    async def test_search_users_by_full_name(self, user_service, test_user_data):
        """Тест поиска пользователей по полному имени"""
        user = await user_service.create_user(test_user_data)

        results = await user_service.search_users("Test")

        assert len(results) >= 1
        found_user = next((u for u in results if u.id == user.id), None)
        assert found_user is not None

    @pytest.mark.asyncio
    async def test_search_users_by_email(self, user_service, test_user_data):
        """Тест поиска пользователей по email"""
        user = await user_service.create_user(test_user_data)

        results = await user_service.search_users("test@example")

        assert len(results) >= 1
        found_user = next((u for u in results if u.id == user.id), None)
        assert found_user is not None

    @pytest.mark.asyncio
    async def test_search_users_inactive_not_returned(
        self, user_service, test_user_data
    ):
        """Тест того, что неактивные пользователи не возвращаются в поиске"""
        data = test_user_data.copy()
        data["is_active"] = False

        user = await user_service.create_user(data)

        results = await user_service.search_users("test")

        found_user = next((u for u in results if u.id == user.id), None)
        assert found_user is None

    @pytest.mark.asyncio
    async def test_search_users_limit(self, user_service, test_user_data):
        """Тест лимита результатов поиска"""
        # Создаем несколько пользователей
        for i in range(5):
            data = test_user_data.copy()
            data["email"] = f"user{i}@example.com"
            data["username"] = f"user{i}"
            await user_service.create_user(data)

        results = await user_service.search_users("user", limit=3)

        assert len(results) <= 3

    # Тесты получения задач пользователя
    @pytest.mark.asyncio
    async def test_get_user_tasks_assigned(self, user_service, test_user_data):
        """Тест получения назначенных задач пользователя"""
        user = await user_service.create_user(test_user_data)

        tasks = await user_service.get_user_tasks(user.id, task_type="assigned")

        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_get_user_tasks_created(self, user_service, test_user_data):
        """Тест получения созданных задач пользователя"""
        user = await user_service.create_user(test_user_data)

        tasks = await user_service.get_user_tasks(user.id, task_type="created")

        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_get_user_tasks_all(self, user_service, test_user_data):
        """Тест получения всех задач пользователя"""
        user = await user_service.create_user(test_user_data)

        tasks = await user_service.get_user_tasks(user.id, task_type="all")

        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_get_user_tasks_pagination(self, user_service, test_user_data):
        """Тест пагинации задач пользователя"""
        user = await user_service.create_user(test_user_data)

        tasks = await user_service.get_user_tasks(user.id, skip=0, limit=10)

        assert isinstance(tasks, list)

    # Тесты проверки лимитов
    @pytest.mark.asyncio
    async def test_check_user_limits_success(self, user_service, test_user_data):
        """Тест проверки лимитов пользователя"""
        user = await user_service.create_user(test_user_data)

        limits = await user_service.check_user_limits(user.id)

        assert "current" in limits
        assert "limits" in limits
        assert "exceeded" in limits
        assert "owned_projects" in limits["current"]
        assert "project_memberships" in limits["current"]
        assert "created_tasks" in limits["current"]

    @pytest.mark.asyncio
    async def test_check_user_limits_user_not_found(self, user_service):
        """Тест проверки лимитов несуществующего пользователя"""
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError, match="Пользователь не найден"):
            await user_service.check_user_limits(fake_id)

    # Тесты обновления последнего входа
    @pytest.mark.asyncio
    async def test_update_last_login_success(self, user_service, test_user_data):
        """Тест успешного обновления времени последнего входа"""
        user = await user_service.create_user(test_user_data)

        result = await user_service.update_last_login(user.id)

        assert result is True
        # Проверяем, что время обновлено
        updated_user = await user_service.get_user_by_id(user.id)
        assert updated_user.last_login_at is not None
        assert isinstance(updated_user.last_login_at, datetime)

    @pytest.mark.asyncio
    async def test_update_last_login_user_not_found(self, user_service):
        """Тест обновления времени последнего входа для несуществующего пользователя"""
        fake_id = uuid.uuid4()

        result = await user_service.update_last_login(fake_id)

        assert result is False

    # Тесты получения публичной информации
    @pytest.mark.asyncio
    async def test_get_public_user_info_success(self, user_service, test_user_data):
        """Тест успешного получения публичной информации"""
        user = await user_service.create_user(test_user_data)

        public_info = await user_service.get_public_user_info(user.id)

        assert public_info is not None
        assert "id" in public_info
        assert "username" in public_info
        assert "full_name" in public_info
        assert "avatar_url" in public_info
        # Проверяем отсутствие приватных полей
        assert "email" not in public_info
        assert "is_active" not in public_info
        assert "role" not in public_info

    @pytest.mark.asyncio
    async def test_get_public_user_info_inactive(self, user_service, test_user_data):
        """Тест получения публичной информации для неактивного пользователя"""
        data = test_user_data.copy()
        data["is_active"] = False

        user = await user_service.create_user(data)

        public_info = await user_service.get_public_user_info(user.id)

        assert public_info is None

    @pytest.mark.asyncio
    async def test_get_public_user_info_not_found(self, user_service):
        """Тест получения публичной информации для несуществующего пользователя"""
        fake_id = uuid.uuid4()

        public_info = await user_service.get_public_user_info(fake_id)

        assert public_info is None

    # Тесты получения проектов пользователя
    @pytest.mark.asyncio
    async def test_get_user_projects_empty(self, user_service, test_user_data):
        """Тест получения проектов пользователя без проектов"""
        user = await user_service.create_user(test_user_data)

        projects = await user_service.get_user_projects(user.id)

        assert isinstance(projects, list)
        assert len(projects) == 0

    @pytest.mark.asyncio
    async def test_get_user_projects_pagination(self, user_service, test_user_data):
        """Тест пагинации проектов пользователя"""
        user = await user_service.create_user(test_user_data)

        projects = await user_service.get_user_projects(user.id, skip=0, limit=10)

        assert isinstance(projects, list)

    # Тесты граничных случаев
    @pytest.mark.asyncio
    async def test_create_user_minimal_data(self, user_service):
        """Тест создания пользователя с минимальными данными"""
        minimal_data = {
            "email": "minimal@example.com",
            "password": "password123",
        }

        user = await user_service.create_user(minimal_data)

        assert user.email == minimal_data["email"]
        assert user.username is None
        assert user.full_name is None
        assert user.is_active is True
        assert user.role == UserRole.USER

    @pytest.mark.asyncio
    async def test_create_user_maximal_data(self, user_service):
        """Тест создания пользователя со всеми данными"""
        maximal_data = {
            "email": "maximal@example.com",
            "username": "maximaluser",
            "full_name": "Maximal User",
            "password": "password123",
            "role": "ADMIN",
            "is_active": True,
            "avatar_url": "https://example.com/avatar.jpg",
            "github_id": "github123",
            "github_username": "githubuser",
        }

        user = await user_service.create_user(maximal_data)

        assert user.email == maximal_data["email"]
        assert user.username == maximal_data["username"]
        assert user.full_name == maximal_data["full_name"]
        assert user.role == UserRole.ADMIN
        assert user.avatar_url == maximal_data["avatar_url"]
        assert user.github_id == maximal_data["github_id"]
        assert user.github_username == maximal_data["github_username"]

    @pytest.mark.asyncio
    async def test_update_user_no_changes(self, user_service, test_user_data):
        """Тест обновления пользователя без изменений"""
        user = await user_service.create_user(test_user_data)

        update_data = UserUpdate()

        updated_user = await user_service.update_user(user.id, update_data)

        assert updated_user is not None
        assert updated_user.full_name == user.full_name
        assert updated_user.username == user.username

    # Тесты обработки ошибок
    @pytest.mark.asyncio
    async def test_create_user_invalid_email_format(self, user_service):
        """Тест создания пользователя с невалидным email"""
        invalid_data = {
            "email": "invalid-email",
            "password": "password123",
        }

        # SQLAlchemy должен обработать валидацию на уровне модели
        with pytest.raises((ValueError, ValidationError)):
            await user_service.create_user(invalid_data)

    @pytest.mark.asyncio
    async def test_create_user_missing_required_fields(self, user_service):
        """Тест создания пользователя без обязательных полей"""
        invalid_data = {
            "username": "testuser",
            # Отсутствует email и password
        }

        with pytest.raises(KeyError):
            await user_service.create_user(invalid_data)

    @pytest.mark.asyncio
    async def test_update_user_with_same_email(self, user_service, test_user_data):
        """Тест обновления пользователя тем же email"""
        user = await user_service.create_user(test_user_data)

        # Обновляем тем же email (не должно вызывать ошибку)
        update_data = UserUpdate(email=user.email)

        updated_user = await user_service.update_user(user.id, update_data)

        assert updated_user is not None
        assert updated_user.email == user.email

    @pytest.mark.asyncio
    async def test_update_user_with_same_username(self, user_service, test_user_data):
        """Тест обновления пользователя тем же username"""
        user = await user_service.create_user(test_user_data)

        # Обновляем тем же username (не должно вызывать ошибку)
        update_data = UserUpdate(username=user.username)

        updated_user = await user_service.update_user(user.id, update_data)

        assert updated_user is not None
        assert updated_user.username == user.username
