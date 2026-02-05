"""
Middleware для проверки подписок и лимитов
"""

import uuid
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.subscription_service import SubscriptionService


class SubscriptionMiddleware(BaseHTTPMiddleware):
    """Middleware для проверки подписок пользователей"""

    def __init__(self, app: Any, exclude_paths: list[str] | None = None) -> None:
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
            "/static/",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/subscription/plans",
            "/api/v1/subscription/packages",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Пропускаем исключенные пути
        if self._should_exclude(request.url.path):
            return await call_next(request)

        # Получаем пользователя из заголовка (если есть)
        user_id = self._extract_user_id(request)

        if user_id:
            # Проверяем подписку для аутентифицированных пользователей
            await self._check_subscription_limits(request, user_id)

        return await call_next(request)

    def _should_exclude(self, path: str) -> bool:
        """Проверить, нужно ли исключить путь из проверки"""
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False

    def _extract_user_id(self, request: Request) -> uuid.UUID | None:
        """Извлечь ID пользователя из запроса"""
        # TODO: Реализовать извлечение пользователя из JWT токена
        # Пока возвращаем None для демонстрации
        return None

    async def _check_subscription_limits(
        self, request: Request, user_id: uuid.UUID
    ) -> None:
        """Проверить лимиты подписки"""
        try:
            # TODO: Получить сессию БД из dependency injection
            from app.core.database import get_db_session_context

            async with get_db_session_context() as db:
                subscription_service = SubscriptionService(db)

                # Проверяем для эндпоинтов загрузки файлов
                if request.url.path.startswith("/api/v1/files/upload"):
                    limits = await subscription_service.get_user_limits(user_id)

                    # Добавляем информацию о лимитах в заголовки ответа
                    request.state.limits = limits

                    # Проверяем критические лимиты
                    storage_usage = await subscription_service.get_storage_usage(
                        user_id
                    )
                    files_count = await subscription_service.get_files_count(user_id)

                    storage_usage_percent = (
                        (storage_usage / limits["storage_limit"]) * 100
                        if limits["storage_limit"] > 0
                        else 0
                    )
                    files_usage_percent = (
                        (files_count / limits["file_count_limit"]) * 100
                        if limits["file_count_limit"] > 0
                        else 0
                    )

                    # Добавляем предупреждения в заголовки
                    if storage_usage_percent > 90:
                        request.state.storage_warning = (
                            f"Storage usage: {storage_usage_percent:.1f}%"
                        )
                    if files_usage_percent > 90:
                        request.state.files_warning = (
                            f"Files usage: {files_usage_percent:.1f}%"
                        )

                    # Блокируем при превышении лимитов
                    if storage_usage_percent >= 100:
                        raise HTTPException(
                            status_code=403,
                            detail="Storage limit exceeded. Please upgrade your plan.",
                        )
                    if files_usage_percent >= 100:
                        raise HTTPException(
                            status_code=403,
                            detail="Files limit exceeded. Please upgrade your plan.",
                        )

        except HTTPException:
            raise
        except Exception as e:
            # Логируем ошибки, но не блокируем запрос
            print(f"Subscription middleware error: {e}")


class SubscriptionInfoMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления информации о подписке в ответ"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Добавляем информацию о подписке в заголовки ответа
        if hasattr(request.state, "limits"):
            limits = request.state.limits
            response.headers["X-Storage-Limit"] = str(limits["storage_limit"])
            response.headers["X-Files-Limit"] = str(limits["file_count_limit"])
            response.headers["X-Max-File-Size"] = str(limits["max_file_size"])
            response.headers["X-Allowed-File-Types"] = ",".join(
                limits["allowed_file_types"]
            )

        if hasattr(request.state, "storage_warning"):
            response.headers["X-Storage-Warning"] = request.state.storage_warning

        if hasattr(request.state, "files_warning"):
            response.headers["X-Files-Warning"] = request.state.files_warning

        return response
