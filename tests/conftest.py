"""
Упрощенная конфигурация pytest для тестов
"""

import asyncio
from collections.abc import Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.main import app
from app.models.base import Base

# Тестовая база данных
TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/timeto_do_test"
)

# Создание тестового движка
engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={
        "server_settings": {
            "application_name": "timeto_do_test",
            "jit": "off",  # Отключаем JIT для стабильности
        },
        "prepared_statement_cache_size": 0,  # Отключаем кэш prepared statements
    },
)

# Создание тестовой сессии
TestingSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Создание event loop для тестов"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Создание тестового движка для всей сессии"""
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        poolclass=None,  # Отключаем пул для тестов
        connect_args={
            "server_settings": {
                "application_name": "timeto_do_test",
                "jit": "off",  # Отключаем JIT для стабильности
            },
            "prepared_statement_cache_size": 0,  # Отключаем кэш prepared statements
        },
    )

    # Инициализация БД один раз за сессию
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Создание тестовой сессии базы данных с изолированной транзакцией"""
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
        connect_args={
            "server_settings": {
                "application_name": "timeto_do_test",
                "jit": "off",  # Отключаем JIT для стабильности
            },
            "prepared_statement_cache_size": 0,  # Отключаем кэш prepared statements
        },
    )

    TestingSessionLocal = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Создаем таблицы если их нет (checkfirst=True предотвращает ошибку дублирования)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    # Используем транзакцию для изоляции
    async with test_engine.begin() as conn:
        async with TestingSessionLocal(bind=conn) as session:
            try:
                yield session
            finally:
                await session.rollback()

    await test_engine.dispose()


@pytest.fixture
def override_get_db(db_session: AsyncSession):
    """Переопределение зависимости get_db для тестов"""

    async def _override_get_db():
        print("DEBUG: Using test database session!")
        yield db_session

    return _override_get_db


@pytest_asyncio.fixture
async def client(override_get_db):
    """Создание тестового клиента"""
    from app.schemas.auth import update_auth_forward_refs

    # Обновляем forward references для Pydantic
    update_auth_forward_refs()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def auth_headers(db_session: AsyncSession):
    """Создание пользователя и заголовков аутентификации для тестов"""
    from app.auth.service import AuthService
    from app.core.security import create_access_token
    from app.schemas.auth import RegisterRequest

    auth_service = AuthService(db_session)
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    user_data = RegisterRequest(
        email=f"test_{unique_suffix}@example.com",
        username=f"testuser_{unique_suffix}",
        full_name="Test User",
        password="testpassword123",
    )

    try:
        user, access_token, _ = await auth_service.register(user_data)
        await db_session.commit()
    except Exception:
        user = await auth_service.get_user_by_email(f"test_{unique_suffix}@example.com")
        if user:
            access_token = create_access_token(subject=user.email)
        else:
            raise

    return {"Authorization": f"Bearer {access_token}", "access_token": access_token}


@pytest_asyncio.fixture(scope="function")
async def test_user_token(auth_headers):
    """Fixture для получения токена пользователя"""
    return auth_headers["access_token"]


@pytest_asyncio.fixture
async def test_project_with_user(auth_headers, db_session: AsyncSession):
    """Создает тестовый проект с пользователем"""
    from app.auth.service import AuthService
    from app.core.security import verify_token
    from app.models.project import Project

    token = auth_headers["access_token"]
    user_email = verify_token(token)  # verify_token возвращает email (string)

    if not user_email:
        raise ValueError("Could not extract user email from token")

    # Получаем пользователя по email из токена
    auth_service = AuthService(db_session)
    user = await auth_service.get_user_by_email(user_email)

    if not user:
        raise ValueError(f"User not found for email: {user_email}")

    project = Project(
        name="Test Project",
        description="Test project description",
        status="ACTIVE",
        is_public=False,
        allow_external_sharing=True,
        max_members="5",
        owner_id=user.id,
    )

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    return project


@pytest.fixture
def test_user_data():
    """Данные тестового пользователя"""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    return {
        "email": f"test_{unique_suffix}@example.com",
        "username": f"testuser_{unique_suffix}",
        "full_name": "Test User",
        "password": "testpassword123",
    }


@pytest.fixture
def test_project_data():
    """Данные тестового проекта"""
    return {
        "name": "Test Project",
        "description": "Test project description",
        "status": "ACTIVE",  # Используем значение из Python enum ProjectStatus
        "is_public": False,
        "allow_external_sharing": True,
        "max_members": "5",
    }


# Async factory fixtures для работы с базой данных
@pytest_asyncio.fixture
async def async_user_factory(db_session: AsyncSession):
    """Асинхронная фабрика пользователей с сохранением в БД"""
    from tests.factories import UserFactory

    async def create_user(**kwargs):
        user = UserFactory(**kwargs)
        db_session.add(user)
        await db_session.flush()
        return user

    return create_user


@pytest_asyncio.fixture
async def async_project_factory(db_session: AsyncSession):
    """Асинхронная фабрика проектов с сохранением в БД"""
    from tests.factories import ProjectFactory

    async def create_project(**kwargs):
        project = ProjectFactory(**kwargs)
        db_session.add(project)
        await db_session.flush()
        return project

    return create_project


@pytest_asyncio.fixture
async def async_task_factory(db_session: AsyncSession):
    """Асинхронная фабрика задач с сохранением в БД"""
    from tests.factories import TaskFactory

    async def create_task(**kwargs):
        task = TaskFactory(**kwargs)
        db_session.add(task)
        await db_session.flush()
        return task

    return create_task


@pytest_asyncio.fixture
async def async_file_factory(db_session: AsyncSession):
    """Асинхронная фабрика файлов с сохранением в БД"""
    from tests.factories import FileFactory

    async def create_file(**kwargs):
        file = FileFactory(**kwargs)
        db_session.add(file)
        await db_session.flush()
        return file

    return create_file


# Тестовые сущности
@pytest_asyncio.fixture
async def test_user(async_user_factory):
    """Тестовый пользователь"""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    return await async_user_factory(
        username=f"testuser_{unique_suffix}",
        email=f"test_{unique_suffix}@example.com",
        full_name="Test User",
    )


@pytest_asyncio.fixture
async def other_user(async_user_factory):
    """Другой тестовый пользователь"""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    return await async_user_factory(
        username=f"otheruser_{unique_suffix}",
        email=f"other_{unique_suffix}@example.com",
        full_name="Other User",
    )


@pytest_asyncio.fixture
async def test_project(async_project_factory, test_user, db_session: AsyncSession):
    """Тестовый проект"""
    # Сначала получим user из той же сессии
    from sqlalchemy import select

    from app.models.user import User

    stmt = select(User).where(User.id == test_user.id)
    result = await db_session.execute(stmt)
    user = result.scalar_one()

    project = await async_project_factory(
        name="Test Project",
        description="Test project description",
        owner_id=user.id,
    )

    # Коммитим изменения, чтобы они были видны в тестах
    await db_session.commit()
    return project


@pytest_asyncio.fixture
async def test_task(
    async_task_factory, test_project, test_user, db_session: AsyncSession
):
    """Тестовая задача"""
    task = await async_task_factory(
        title="Test Task",
        description="Test task description",
        project_id=test_project.id,
        creator_id=test_user.id,
        assignee_id=test_user.id,
    )

    # Убедимся, что задача сохранена в той же сессии
    await db_session.commit()
    return task


@pytest_asyncio.fixture
async def test_file(async_file_factory, test_user):
    """Тестовый файл"""
    return await async_file_factory(
        filename="test_file.txt",
        original_filename="test_file.txt",
        file_path="/tmp/test_file.txt",
        file_size=1024,
        mime_type="text/plain",
        uploader_id=test_user.id,
    )


@pytest_asyncio.fixture
async def authenticated_user(test_user, db_session: AsyncSession):
    """Фикстура для аутентифицированного пользователя"""
    from app.core.security import create_access_token

    access_token = create_access_token(subject=test_user.email)
    return {
        "user": test_user,
        "headers": {"Authorization": f"Bearer {access_token}"},
        "db": db_session,  # Используем ту же сессию, что и другие фикстуры
    }


@pytest_asyncio.fixture
async def other_user_auth(other_user, db_session: AsyncSession):
    """Фикстура для другого аутентифицированного пользователя"""
    from app.core.security import create_access_token

    access_token = create_access_token(subject=other_user.email)
    return {
        "user": other_user,
        "headers": {"Authorization": f"Bearer {access_token}"},
        "db": db_session,
    }


@pytest.fixture
def test_task_data(test_project_with_user):
    """Данные тестовой задачи"""
    return {
        "title": "Test Task",
        "description": "Test task description",
        "status": "todo",  # Используем значение из Python enum TaskStatus
        "priority": "medium",  # Используем значение из Python enum TaskPriority
        "story_point": "3",  # Используем значение из Python enum StoryPoint
        "estimated_hours": 8,
        "project_id": str(test_project_with_user.id),  # Добавляем project_id
    }
