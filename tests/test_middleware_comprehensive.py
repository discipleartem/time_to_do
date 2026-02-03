"""
Комплексные тесты для middleware
"""

import time
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
from app.middleware import (
    DatabaseErrorHandlingMiddleware,
    ErrorHandlingMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)


class TestErrorHandlingMiddleware:
    """Тесты middleware для обработки ошибок"""

    @pytest.fixture
    def middleware(self):
        """Создание middleware"""
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

    @pytest.mark.asyncio
    async def test_successful_request(self, middleware, mock_request, mock_call_next):
        """Тест успешного запроса"""
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response == mock_call_next.return_value
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_base_api_exception_handling(self, middleware, mock_request):
        """Тест обработки BaseAPIException"""
        exc = ValidationError("Invalid data", "field")
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

    @pytest.mark.asyncio
    async def test_not_found_exception_handling(self, middleware, mock_request):
        """Тест обработки NotFoundError"""
        exc = NotFoundError("Проект", "123")
        mock_call_next = AsyncMock(side_effect=exc)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_starlette_http_exception_handling(self, middleware, mock_request):
        """Тест обработки Starlette HTTPException"""
        exc = StarletteHTTPException(status_code=404, detail="Not found")
        mock_call_next = AsyncMock(side_effect=exc)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_database_exception_handling(self, middleware, mock_request):
        """Тест обработки исключений базы данных"""
        exc = DatabaseError("Connection failed")
        mock_call_next = AsyncMock(side_effect=exc)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_generic_exception_handling_debug_mode(
        self, middleware, mock_request
    ):
        """Тест обработки генерических исключений в debug режиме"""
        exc = ValueError("Unexpected error")
        mock_call_next = AsyncMock(side_effect=exc)

        with patch("app.middleware.settings.DEBUG", True):
            response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        # В debug режиме должна быть детальная информация
        import json

        content = json.loads(response.body.decode())
        assert content["message"] == "Unexpected error"
        assert content["details"]["type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_generic_exception_handling_production_mode(
        self, middleware, mock_request
    ):
        """Тест обработки генерических исключений в production режиме"""
        exc = ValueError("Unexpected error")
        mock_call_next = AsyncMock(side_effect=exc)

        with patch("app.middleware.settings.DEBUG", False):
            response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        # В production режиме скрываем детали
        import json

        content = json.loads(response.body.decode())
        assert content["message"] == "Внутренняя ошибка сервера"
        assert content["details"] == {}

    @pytest.mark.asyncio
    async def test_exception_logging_with_details(self, middleware, mock_request):
        """Тест логирования с деталями исключения"""
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


class TestRateLimitMiddleware:
    """Тесты middleware для rate limiting"""

    @pytest.fixture
    def middleware(self):
        """Создание middleware без Redis"""
        app = MagicMock()
        return RateLimitMiddleware(app, redis_client=None)

    @pytest.fixture
    def mock_request(self):
        """Мок запроса"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/auth/login"
        request.client.host = "127.0.0.1"
        request.headers = {}
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Мок функции call_next"""
        response = MagicMock(spec=Response)
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        return call_next

    @pytest.mark.asyncio
    async def test_get_client_ip_from_forwarded_header(self, middleware):
        """Тест получения IP из X-Forwarded-For"""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_get_client_ip_from_real_ip_header(self, middleware):
        """Тест получения IP из X-Real-IP"""
        request = MagicMock(spec=Request)
        request.headers = {"X-Real-IP": "192.168.1.1"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_get_client_ip_from_client(self, middleware):
        """Тест получения IP из client.host"""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client.host = "127.0.0.1"

        ip = middleware._get_client_ip(request)
        assert ip == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_get_client_ip_unknown(self, middleware):
        """Тест получения IP когда неизвестен"""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "unknown"

    def test_get_limit_for_path_specific(self, middleware):
        """Тест получения лимитов для конкретного пути"""
        limit, window = middleware._get_limit_for_path("/api/v1/auth/login")
        assert limit == 5
        assert window == 300

    def test_get_limit_for_path_default(self, middleware):
        """Тест получения лимитов по умолчанию"""
        limit, window = middleware._get_limit_for_path("/unknown/path")
        assert limit == 1000
        assert window == 3600

    @pytest.mark.asyncio
    async def test_memory_limit_not_exceeded(
        self, middleware, mock_request, mock_call_next
    ):
        """Тест проверки лимита в памяти - не превышен"""
        # Первый запрос
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response == mock_call_next.return_value
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    @pytest.mark.asyncio
    async def test_memory_limit_exceeded(self, middleware, mock_request):
        """Тест проверки лимита в памяти - превышен"""
        # Делаем 6 запросов (лимит 5 для /api/v1/auth/login)
        for i in range(6):
            mock_call_next = AsyncMock()
            if i < 5:
                # Первые 5 должны пройти
                response = await middleware.dispatch(mock_request, mock_call_next)
                assert response.status_code != 429
            else:
                # 6-й должен быть заблокирован
                response = await middleware.dispatch(mock_request, mock_call_next)
                assert isinstance(response, JSONResponse)
                assert response.status_code == 429
                assert "X-RateLimit-Limit" in response.headers
                assert response.headers["X-RateLimit-Remaining"] == "0"

    @pytest.mark.asyncio
    async def test_memory_limit_reset_after_window(
        self, middleware, mock_request, mock_call_next
    ):
        """Тест сброса лимита после окончания окна"""
        # Первый запрос
        await middleware.dispatch(mock_request, mock_call_next)

        # Мокаем время, чтобы окно закончилось
        with patch("time.time", return_value=time.time() + 301):
            # Следующий запрос должен сбросить счетчик
            await middleware.dispatch(mock_request, mock_call_next)

        # Счетчик должен быть сброшен
        assert middleware._get_memory_count("127.0.0.1", "/api/v1/auth/login") == 1

    @pytest.mark.asyncio
    async def test_redis_limit_success(self, mock_request, mock_call_next):
        """Тест проверки лимита через Redis - успех"""
        # Мокаем Redis клиент
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 1
        mock_redis.get.return_value = "1"

        middleware = RateLimitMiddleware(MagicMock(), redis_client=mock_redis)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response == mock_call_next.return_value
        mock_redis.incr.assert_called_once()
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_limit_exceeded(self, mock_request):
        """Тест проверки лимита через Redis - превышен"""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 6  # Превышает лимит 5

        middleware = RateLimitMiddleware(MagicMock(), redis_client=mock_redis)

        response = await middleware.dispatch(mock_request, AsyncMock())

        assert isinstance(response, JSONResponse)
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_redis_error_fallback(self, mock_request, mock_call_next):
        """Тест ошибки Redis - fallback к пропуску"""
        mock_redis = AsyncMock()
        mock_redis.incr.side_effect = Exception("Redis error")

        middleware = RateLimitMiddleware(MagicMock(), redis_client=mock_redis)

        with patch("app.middleware.logger") as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)

        assert response == mock_call_next.return_value
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_remaining_requests_redis(self, middleware):
        """Тест получения оставшихся запросов из Redis"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "3"

        middleware.redis_client = mock_redis

        remaining = await middleware._get_remaining_requests("127.0.0.1", "/path", 5)
        assert remaining == 2  # 5 - 3

    @pytest.mark.asyncio
    async def test_get_remaining_requests_no_current(self, middleware):
        """Тест получения оставшихся запросов - нет текущих"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        middleware.redis_client = mock_redis

        remaining = await middleware._get_remaining_requests("127.0.0.1", "/path", 5)
        assert remaining == 5

    def test_get_memory_count(self, middleware):
        """Тест получения счетчика из памяти"""
        # Инициализируем счетчик
        middleware._memory_limits = {"127.0.0.1:/path": {"count": 3}}

        count = middleware._get_memory_count("127.0.0.1", "/path")
        assert count == 3

    def test_get_memory_count_no_limits(self, middleware):
        """Тест получения счетчика - нет лимитов"""
        count = middleware._get_memory_count("127.0.0.1", "/path")
        assert count == 0


class TestSecurityHeadersMiddleware:
    """Тесты middleware для security заголовков"""

    @pytest.fixture
    def middleware(self):
        """Создание middleware"""
        app = MagicMock()
        return SecurityHeadersMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Мок запроса"""
        request = MagicMock(spec=Request)
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Мок функции call_next"""
        response = MagicMock(spec=Response)
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        return call_next

    @pytest.mark.asyncio
    async def test_security_headers_added(
        self, middleware, mock_request, mock_call_next
    ):
        """Тест добавления security заголовков"""
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    @pytest.mark.asyncio
    async def test_cors_headers_enabled(self, middleware, mock_request, mock_call_next):
        """Тест добавления CORS заголовков когда включены"""
        with patch("app.middleware.settings", MagicMock(ALLOW_CORS=True)):
            response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert (
            "GET, POST, PUT, DELETE, OPTIONS"
            in response.headers["Access-Control-Allow-Methods"]
        )
        assert response.headers["Access-Control-Allow-Headers"] == "*"

    @pytest.mark.asyncio
    async def test_cors_headers_disabled(
        self, middleware, mock_request, mock_call_next
    ):
        """Тест отсутствия CORS заголовков когда выключены"""
        with patch("app.middleware.settings", MagicMock(ALLOW_CORS=False)):
            response = await middleware.dispatch(mock_request, mock_call_next)

        assert "Access-Control-Allow-Origin" not in response.headers
        assert "Access-Control-Allow-Methods" not in response.headers


class TestRequestLoggingMiddleware:
    """Тесты middleware для логирования запросов"""

    @pytest.fixture
    def middleware(self):
        """Создание middleware"""
        app = MagicMock()
        return RequestLoggingMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Мок запроса"""
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url.path = "/test/path"
        request.query_params = {"param": "value"}
        request.headers = {}
        request.client.host = "127.0.0.1"
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Мок функции call_next"""
        response = MagicMock(spec=Response)
        response.status_code = 200
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        return call_next

    @pytest.mark.asyncio
    async def test_request_logging(self, middleware, mock_request, mock_call_next):
        """Тест логирования запроса"""
        with patch("app.middleware.logger") as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)

        assert response == mock_call_next.return_value
        assert "X-Process-Time" in response.headers

        # Проверяем, что логирование было вызвано дважды (начало и конец)
        assert mock_logger.info.call_count == 2

        # Проверяем лог начала запроса
        start_call = mock_logger.info.call_args_list[0]
        assert "Request started" in start_call[0][0]
        assert start_call[1]["extra"]["method"] == "GET"
        assert start_call[1]["extra"]["path"] == "/test/path"

        # Проверяем лог завершения запроса
        end_call = mock_logger.info.call_args_list[1]
        assert "Request completed" in end_call[0][0]
        assert end_call[1]["extra"]["status_code"] == 200
        assert "process_time" in end_call[1]["extra"]

    @pytest.mark.asyncio
    async def test_get_client_ip_forwarded(self, middleware):
        """Тест получения IP с X-Forwarded-For"""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "192.168.1.1"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_get_client_ip_real_ip(self, middleware):
        """Тест получения IP с X-Real-IP"""
        request = MagicMock(spec=Request)
        request.headers = {"X-Real-IP": "192.168.1.1"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_get_client_ip_client_host(self, middleware):
        """Тест получения IP из client.host"""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client.host = "127.0.0.1"

        ip = middleware._get_client_ip(request)
        assert ip == "127.0.0.1"


class TestDatabaseErrorHandlingMiddleware:
    """Тесты middleware для обработки ошибок базы данных"""

    @pytest.fixture
    def middleware(self):
        """Создание middleware"""
        app = MagicMock()
        return DatabaseErrorHandlingMiddleware(app)

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

    @pytest.mark.asyncio
    async def test_successful_request(self, middleware, mock_request, mock_call_next):
        """Тест успешного запроса"""
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response == mock_call_next.return_value

    @pytest.mark.asyncio
    async def test_database_error_handling(self, middleware, mock_request):
        """Тест обработки ошибки базы данных"""

        # Создаем мок класса SQLAlchemy
        class MockSQLAlchemyError(Exception):
            pass

        MockSQLAlchemyError.__module__ = "sqlalchemy.exc"
        exc = MockSQLAlchemyError("duplicate key value violates unique constraint")

        mock_call_next = AsyncMock(side_effect=exc)

        with patch("app.middleware.logger") as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        # DatabaseError может возвращать 409 (конфликт) или 500 в зависимости от типа ошибки
        assert response.status_code in [409, 500]

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Database error" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_non_database_error_passthrough(self, middleware, mock_request):
        """Тест передачи не-БД ошибок дальше"""
        exc = ValueError("Regular error")
        mock_call_next = AsyncMock(side_effect=exc)

        # Ошибка должна быть передана дальше
        with pytest.raises(ValueError, match="Regular error"):
            await middleware.dispatch(mock_request, mock_call_next)

    def test_is_database_error_sqlalchemy(self, middleware):
        """Тест определения ошибки SQLAlchemy"""

        # Создаем мок класса SQLAlchemy
        class MockSQLAlchemyError(Exception):
            pass

        MockSQLAlchemyError.__module__ = "sqlalchemy.exc"
        exc = MockSQLAlchemyError("Some error")

        assert middleware._is_database_error(exc) is True

    def test_is_database_error_postgresql_keywords(self, middleware):
        """Тест определения ошибок PostgreSQL по ключевым словам"""
        errors = [
            Exception("duplicate key value violates unique constraint"),
            Exception("unique constraint violation"),
            Exception("foreign key constraint violation"),
            Exception("not null constraint violation"),
            Exception("check constraint violation"),
            Exception("database error occurred"),
        ]

        for exc in errors:
            assert middleware._is_database_error(exc) is True

    def test_is_not_database_error(self, middleware):
        """Тест определения не-БД ошибки"""
        exc = ValueError("Regular validation error")

        assert middleware._is_database_error(exc) is False

    @pytest.mark.asyncio
    async def test_database_error_logging(self, middleware, mock_request):
        """Тест логирования ошибок базы данных"""

        # Создаем мок класса SQLAlchemy
        class MockSQLAlchemyError(Exception):
            pass

        MockSQLAlchemyError.__module__ = "sqlalchemy.exc"
        exc = MockSQLAlchemyError("duplicate key error")

        mock_call_next = AsyncMock(side_effect=exc)

        with patch("app.middleware.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)

        # Проверяем параметры логирования
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Database error" in call_args[0][0]
        assert call_args[1]["extra"]["path"] == "/test/path"
        assert call_args[1]["exc_info"] is True


class TestMiddlewareIntegration:
    """Интеграционные тесты middleware"""

    @pytest.mark.asyncio
    async def test_middleware_chain(self):
        """Тест цепочки middleware"""
        from fastapi import FastAPI

        app = FastAPI()

        # Добавляем middleware
        app.add_middleware(ErrorHandlingMiddleware)
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RequestLoggingMiddleware)

        # Создаем тестовый endpoint
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        # Тестируем запрос через цепочку middleware
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/test")

        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert "X-Process-Time" in response.headers

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_integration(self):
        """Тест интеграции rate limiting middleware"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = RateLimitMiddleware(app, redis_client=None)

        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/auth/login"
        request.client.host = "127.0.0.1"
        request.headers = {}

        # Делаем несколько запросов
        responses = []
        for _i in range(6):
            call_next = AsyncMock()
            response = await middleware.dispatch(request, call_next)
            responses.append(response)

        # Первые 5 должны пройти, 6-й должен быть заблокирован
        assert (
            sum(
                1
                for r in responses
                if not hasattr(r, "status_code") or r.status_code != 429
            )
            == 5
        )
        assert any(
            hasattr(r, "status_code") and r.status_code == 429 for r in responses
        )
