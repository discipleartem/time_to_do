"""
Настройка базы данных и SQLAlchemy
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.base import Base

T = TypeVar("T")

# Создание асинхронного движка базы данных
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "server_settings": {
            "application_name": "timeto_do",
            "jit": "off",  # Отключаем JIT для стабильности
        },
        "prepared_statement_cache_size": 0,  # Отключаем кэш prepared statements
    },
)

# Создание фабрики сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """
    Получение асинхронной сессии базы данных с правильным управлением транзакциями

    Следует лучшим практикам:
    - Автоматический commit при успехе
    - Rollback при ошибке
    - Гарантированное закрытие сессии

    Yields:
        AsyncSession: Сессия базы данных
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncSession:
    """
    Получение асинхронной сессии базы данных для валидаторов

    Returns:
        AsyncSession: Сессия базы данных
    """
    return AsyncSessionLocal()


@asynccontextmanager
async def get_db_session_context() -> AsyncGenerator[AsyncSession]:
    """
    Контекстный менеджер для сессии базы данных

    Yields:
        AsyncSession: Сессия базы данных
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Инициализация базы данных - создание всех таблиц"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Закрытие соединения с базой данных"""
    await engine.dispose()
