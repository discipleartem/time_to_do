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

from app.core.database import Base, get_db
from app.main import app

# Тестовая база данных
TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/timeto_do_test"
)

# Создание тестового движка
engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
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
    )

    # Инициализация БД один раз за сессию
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Создание тестовой сессии базы данных с изолированным engine"""
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )

    TestingSessionLocal = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    await test_engine.dispose()


@pytest.fixture
def override_get_db(db_session: AsyncSession):
    """Переопределение зависимости get_db для тестов"""

    def _override_get_db():
        return db_session

    return _override_get_db


@pytest_asyncio.fixture
async def client(override_get_db):
    """Создание тестового клиента"""
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
    user_data = RegisterRequest(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        password="testpassword123",
    )

    try:
        user, access_token, _ = await auth_service.register(user_data)
        await db_session.commit()
    except Exception:
        user = await auth_service.get_user_by_email("test@example.com")
        if user:
            access_token = create_access_token(subject=user.email)
        else:
            raise

    return {"Authorization": f"Bearer {access_token}", "access_token": access_token}


@pytest_asyncio.fixture
async def test_project_with_user(auth_headers, db_session: AsyncSession):
    """Создает тестовый проект с пользователем"""
    from app.auth.service import AuthService
    from app.models.project import Project

    # Получаем пользователя из auth_headers
    auth_service = AuthService(db_session)
    user = await auth_service.get_user_by_email("test@example.com")

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
    return {
        "email": "test@example.com",
        "username": "testuser",
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
