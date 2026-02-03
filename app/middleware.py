"""
Middleware для обработки ошибок и rate limiting
"""

import logging
import time
from collections.abc import Callable
from typing import Any

import redis.asyncio as redis
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.exceptions import (
    BaseAPIException,
    exception_to_http_exception,
    handle_database_error,
)

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware для обработки ошибок"""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> JSONResponse | Response:
        try:
            response = await call_next(request)
            return response
        except BaseAPIException as exc:
            # Обработка кастомных исключений API
            logger.warning(
                f"API Exception: {exc.__class__.__name__}: {exc.message}",
                extra={"details": exc.details, "path": request.url.path},
            )

            http_exc = exception_to_http_exception(exc)
            return JSONResponse(
                status_code=http_exc.status_code, content=http_exc.detail
            )

        except StarletteHTTPException as exc:
            # Обработка HTTP исключений Starlette
            logger.warning(
                f"HTTP Exception: {exc.status_code} - {exc.detail}",
                extra={"path": request.url.path},
            )

            return JSONResponse(
                status_code=exc.status_code,
                content={"message": exc.detail, "details": {}, "type": "HTTPException"},
            )

        except Exception as exc:
            # Обработка неожиданных ошибок
            logger.error(
                f"Unexpected error: {exc.__class__.__name__}: {str(exc)}",
                extra={"path": request.url.path},
                exc_info=True,
            )

            # В development режиме показываем детальную информацию
            if settings.DEBUG:
                return JSONResponse(
                    status_code=500,
                    content={
                        "message": str(exc),
                        "details": {"type": exc.__class__.__name__},
                        "type": "InternalServerError",
                    },
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content={
                        "message": "Внутренняя ошибка сервера",
                        "details": {},
                        "type": "InternalServerError",
                    },
                )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware для rate limiting"""

    def __init__(self, app: ASGIApp, redis_client: redis.Redis | None = None) -> None:
        super().__init__(app)
        self.redis_client = redis_client
        self.limits = {
            # Эндпоинты: (запросов, окно в секундах)
            "/api/v1/auth/login": (5, 300),  # 5 запросов за 5 минут
            "/api/v1/auth/register": (3, 3600),  # 3 запроса за час
            "/api/v1/auth/github": (10, 60),  # 10 запросов за минуту
            "/api/v1/projects": (100, 3600),  # 100 запросов за час
            "/api/v1/tasks": (200, 3600),  # 200 запросов за час
            "default": (1000, 3600),  # 1000 запросов за час по умолчанию
        }

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> JSONResponse | Response:
        # Получаем IP адрес клиента
        client_ip = self._get_client_ip(request)

        # Получаем лимиты для эндпоинта
        path = request.url.path
        limit, window = self._get_limit_for_path(path)

        # Проверяем лимит
        if self.redis_client:
            limited = await self._check_redis_limit(client_ip, path, limit, window)
        else:
            limited = self._check_memory_limit(client_ip, path, limit, window)

        if limited:
            from app.exceptions import RateLimitError

            exc = RateLimitError(limit, window)
            http_exc = exception_to_http_exception(exc)

            return JSONResponse(
                status_code=http_exc.status_code,
                content=http_exc.detail,
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + window),
                },
            )

        # Добавляем заголовки с информацией о лимитах
        response = await call_next(request)

        if self.redis_client:
            remaining = await self._get_remaining_requests(client_ip, path, limit)
        else:
            remaining = max(0, limit - self._get_memory_count(client_ip, path))

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Получение IP адреса клиента"""
        # Проверяем заголовки от прокси
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _get_limit_for_path(self, path: str) -> tuple[int, int]:
        """Получение лимитов для пути"""
        for pattern, (limit, window) in self.limits.items():
            if pattern != "default" and path.startswith(pattern):
                return limit, window

        return self.limits["default"]

    async def _check_redis_limit(
        self, client_ip: str, path: str, limit: int, window: int
    ) -> bool:
        """Проверка лимита через Redis"""
        key = f"rate_limit:{client_ip}:{path}"

        try:
            if self.redis_client is None:
                return False
            current = await self.redis_client.incr(key)

            if current == 1:
                await self.redis_client.expire(key, window)

            return current > limit
        except Exception as exc:
            logger.error(f"Redis rate limit error: {exc}")
            # В случае ошибки Redis, пропускаем запрос
            return False

    def _check_memory_limit(
        self, client_ip: str, path: str, limit: int, window: int
    ) -> bool:
        """Проверка лимита в памяти (fallback)"""
        # Простая реализация в памяти для разработки
        if not hasattr(self, "_memory_limits"):
            self._memory_limits: dict[str, dict[str, int]] = {}

        key = f"{client_ip}:{path}"
        now = int(time.time())

        if key not in self._memory_limits:
            self._memory_limits[key] = {"count": 0, "reset_time": now + window}

        # Сброс счетчика если прошло время
        if now > self._memory_limits[key]["reset_time"]:
            self._memory_limits[key] = {"count": 0, "reset_time": now + window}

        self._memory_limits[key]["count"] += 1

        return self._memory_limits[key]["count"] > limit

    async def _get_remaining_requests(
        self, client_ip: str, path: str, limit: int
    ) -> int:
        """Получение оставшихся запросов"""
        key = f"rate_limit:{client_ip}:{path}"

        try:
            if self.redis_client is None:
                return limit
            current = await self.redis_client.get(key)
            if current:
                return max(0, limit - int(current))
            return limit
        except Exception:
            return limit

    def _get_memory_count(self, client_ip: str, path: str) -> int:
        """Получение текущего счетчика из памяти"""
        if not hasattr(self, "_memory_limits"):
            return 0

        key = f"{client_ip}:{path}"
        if key in self._memory_limits:
            return self._memory_limits[key]["count"]
        return 0


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления security заголовков"""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        response = await call_next(request)

        # Security заголовки
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # CORS заголовки (если нужно)
        if hasattr(settings, "ALLOW_CORS") and settings.ALLOW_CORS:
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, DELETE, OPTIONS"
            )
            response.headers["Access-Control-Allow-Headers"] = "*"

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования запросов"""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        start_time = time.time()

        # Логируем начало запроса
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": self._get_client_ip(request),
            },
        )

        response = await call_next(request)

        # Логируем завершение запроса
        process_time = time.time() - start_time
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": process_time,
            },
        )

        response.headers["X-Process-Time"] = str(process_time)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Получение IP адреса клиента"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"


class DatabaseErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware для обработки ошибок базы данных"""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> JSONResponse | Response:
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Проверяем, является ли ошибка ошибкой базы данных
            if self._is_database_error(exc):
                api_exc = handle_database_error(exc)
                http_exc = exception_to_http_exception(api_exc)

                logger.error(
                    f"Database error: {exc.__class__.__name__}: {str(exc)}",
                    extra={"path": request.url.path},
                    exc_info=True,
                )

                return JSONResponse(
                    status_code=http_exc.status_code, content=http_exc.detail
                )

            # Если это не ошибка БД, передаем дальше
            raise exc

    def _is_database_error(self, exc: Exception) -> bool:
        """Проверка, является ли ошибка ошибкой базы данных"""
        error_message = str(exc).lower()

        # SQLAlchemy ошибки
        if "sqlalchemy" in exc.__class__.__module__:
            return True

        # PostgreSQL ошибки
        if any(
            keyword in error_message
            for keyword in [
                "duplicate key",
                "unique constraint",
                "foreign key constraint",
                "not null constraint",
                "check constraint",
                "database error",
            ]
        ):
            return True

        return False
