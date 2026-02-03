"""
Тестовая конфигурация
"""

from pydantic_settings import BaseSettings


class ConfigSettings(BaseSettings):
    """Настройки для тестов"""

    # Используем отдельную тестовую базу
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/timeto_do_test"
    )

    # Отключаем Redis для тестов
    REDIS_URL: str = "redis://localhost:6379/1"  # Отдельная база Redis

    # Тестовые настройки безопасности
    SECRET_KEY: str = "test-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Отключаем CORS для тестов
    BACKEND_CORS_ORIGINS: list = []

    model_config = {"case_sensitive": True}


config_settings = ConfigSettings()
