"""
Тесты для middleware
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import (
    DatabaseError,
    NotFoundError,
    ValidationError,
)
from app.middleware import ErrorHandlingMiddleware


class TestErrorHandlingMiddleware:
    """Тесты middleware для обработки ошибок"""

    @pytest.fixture
    def middleware(self):
        """Создание экземпляра middleware"""
        app = MagicMock()
        return ErrorHandlingMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Мок запроса"""
        request = MagicMock(spec=Request)
        request.url.path = "/test/path"
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Мок функции call_next"""
        response = MagicMock(spec=Response)
        call_next = AsyncMock(return_value=response)
        return call_next

    async def test_successful_request(self, middleware, mock_request, mock_call_next):
        """Успешный запрос без ошибок"""
        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once_with(mock_request)
        assert response == mock_call_next.return_value

    async def test_base_api_exception_handling(self, middleware, mock_request):
        """Обработка BaseAPIException"""
        exc = ValidationError("Invalid data", "email")
        mock_call_next = AsyncMock(side_effect=exc)

        with patch("app.middleware.logger") as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 422

        # Проверка логирования
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "API Exception" in call_args[0][0]
        assert "ValidationError" in call_args[0][0]

    async def test_not_found_exception_handling(self, middleware, mock_request):
        """Обработка NotFoundError"""
        exc = NotFoundError("Проект", "123")
        mock_call_next = AsyncMock(side_effect=exc)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

        # Проверка содержимого ответа
        import json

        content = json.loads(response.body.decode())
        assert content["message"] == "Проект не найден (ID: 123)"
        assert content["type"] == "NotFoundError"

    async def test_starlette_http_exception_handling(self, middleware, mock_request):
        """Обработка Starlette HTTPException"""
        exc = StarletteHTTPException(status_code=404, detail="Not found")
        mock_call_next = AsyncMock(side_effect=exc)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

    async def test_database_exception_handling(self, middleware, mock_request):
        """Обработка исключений базы данных"""
        exc = DatabaseError("Connection failed")
        mock_call_next = AsyncMock(side_effect=exc)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

    async def test_generic_exception_handling(self, middleware, mock_request):
        """Обработка генерических исключений"""
        exc = ValueError("Unexpected error")
        mock_call_next = AsyncMock(side_effect=exc)

        with patch("app.middleware.logger") as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

        # Проверка логирования ошибки
        mock_logger.error.assert_called_once()

    async def test_exception_logging_with_details(self, middleware, mock_request):
        """Проверка логирования с деталями исключения"""
        exc = ValidationError("Invalid data", "email")
        exc.details = {"field": "email", "value": "invalid"}
        mock_call_next = AsyncMock(side_effect=exc)

        with patch("app.middleware.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)

        # Проверка аргументов логирования
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "details" in call_args[1]["extra"]
        assert "path" in call_args[1]["extra"]
        assert call_args[1]["extra"]["path"] == "/test/path"

    async def test_multiple_exception_types(self, middleware, mock_request):
        """Тест обработки различных типов исключений"""
        exceptions = [
            ValidationError("Validation error"),
            NotFoundError("Resource", "123"),
            DatabaseError("DB error"),
        ]

        for exc in exceptions:
            mock_call_next = AsyncMock(side_effect=exc)

            with patch("app.middleware.logger"):
                response = await middleware.dispatch(mock_request, mock_call_next)

            assert isinstance(response, JSONResponse)
            assert response.status_code in [422, 404, 500]

    async def test_middleware_chain_integrity(self, middleware, mock_request):
        """Проверка целостности цепочки middleware"""
        # Создаем мок ответа
        mock_response = MagicMock(spec=Response)
        mock_call_next = AsyncMock(return_value=mock_response)

        with patch("app.middleware.logger"):
            response = await middleware.dispatch(mock_request, mock_call_next)

        # Проверяем, что call_next был вызван один раз
        mock_call_next.assert_called_once_with(mock_request)
        assert response == mock_response

    async def test_request_context_preservation(self, middleware, mock_request):
        """Сохранение контекста запроса при ошибке"""
        mock_request.url.path = "/api/v1/projects/123"
        mock_request.method = "GET"

        exc = NotFoundError("Проект", "123")
        mock_call_next = AsyncMock(side_effect=exc)

        with patch("app.middleware.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)

        # Проверяем, что путь запроса сохранен в логах
        call_args = mock_logger.warning.call_args
        assert call_args[1]["extra"]["path"] == "/api/v1/projects/123"
