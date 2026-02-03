"""
Настройка Redis для кэширования и сессий
"""

import json
from typing import Any

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings

# Создание Redis клиента
redis_client: Redis = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    max_connections=10,
)


async def get_redis() -> Redis:
    """
    Получение Redis клиента

    Returns:
        Redis: Асинхронный Redis клиент
    """
    return redis_client


class RedisService:
    """Сервис для работы с Redis"""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def set(self, key: str, value: Any, expire: int | None = None) -> bool:
        """
        Сохранение значения в Redis

        Args:
            key: Ключ
            value: Значение (будет сериализовано в JSON)
            expire: Время жизни в секундах

        Returns:
            bool: True если успешно
        """
        try:
            serialized_value = json.dumps(value, default=str)
            return await self.redis.set(key, serialized_value, ex=expire)
        except Exception:
            return False

    async def get(self, key: str) -> Any | None:
        """
        Получение значения из Redis

        Args:
            key: Ключ

        Returns:
            Optional[Any]: Десериализованное значение или None
        """
        try:
            value = await self.redis.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception:
            return None

    async def delete(self, key: str) -> bool:
        """
        Удаление ключа из Redis

        Args:
            key: Ключ

        Returns:
            bool: True если успешно
        """
        try:
            return bool(await self.redis.delete(key))
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        """
        Проверка существования ключа

        Args:
            key: Ключ

        Returns:
            bool: True если ключ существует
        """
        try:
            return bool(await self.redis.exists(key))
        except Exception:
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """
        Установка времени жизни для ключа

        Args:
            key: Ключ
            seconds: Время жизни в секундах

        Returns:
            bool: True если успешно
        """
        try:
            return bool(await self.redis.expire(key, seconds))
        except Exception:
            return False

    async def incr(self, key: str) -> int | None:
        """
        Инкремент счетчика

        Args:
            key: Ключ

        Returns:
            Optional[int]: Новое значение или None
        """
        try:
            return await self.redis.incr(key)
        except Exception:
            return None

    async def lpush(self, key: str, *values: Any) -> int | None:
        """
        Добавление элементов в начало списка

        Args:
            key: Ключ списка
            *values: Значения для добавления

        Returns:
            Optional[int]: Длина списка после добавления
        """
        try:
            serialized_values = [json.dumps(v, default=str) for v in values]
            return await self.redis.lpush(key, *serialized_values)  # type: ignore[misc] # Redis library lacks complete typing for variadic args
        except Exception:
            return None

    async def rpop(self, key: str) -> Any | None:
        """
        Получение и удаление элемента из конца списка

        Args:
            key: Ключ списка

        Returns:
            Optional[Any]: Значение или None
        """
        try:
            value = await self.redis.rpop(key)  # type: ignore[misc] # Redis library typing doesn't distinguish None vs empty string
            if value is None:
                return None
            return json.loads(value)
        except Exception:
            return None


# Создание экземпляра сервиса
redis_service = RedisService(redis_client)


async def init_redis() -> None:
    """Инициализация Redis - проверка соединения"""
    try:
        await redis_client.ping()
        print("✅ Redis подключен успешно")
    except Exception as e:
        print(f"❌ Ошибка подключения к Redis: {e}")


async def close_redis() -> None:
    """Закрытие соединения с Redis"""
    await redis_client.close()
