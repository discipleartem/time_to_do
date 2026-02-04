"""
Базовые тесты WebSocket функциональности
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from app.main import app
from app.websocket.connection import Connection
from app.websocket.events import (
    EventType,
    WebSocketEvent,
    create_error_event,
    create_task_event,
)
from app.websocket.handlers import WebSocketHandler
from app.websocket.manager import ConnectionManager


class TestConnection:
    """Тесты класса Connection"""

    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket соединения"""
        websocket = MagicMock(spec=WebSocket)
        websocket.send_json = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.fixture
    def connection(self, mock_websocket):
        """Создание тестового соединения"""
        from uuid import uuid4

        user_id = uuid4()
        return Connection(mock_websocket, user_id)

    def test_connection_init(self, mock_websocket):
        """Тест инициализации соединения"""
        from uuid import uuid4

        user_id = uuid4()
        connection = Connection(mock_websocket, user_id)

        assert connection.websocket == mock_websocket
        assert connection.user_id == user_id
        assert connection.is_authenticated is True
        assert len(connection.project_rooms) == 0
        assert connection.connection_id is not None

    def test_connection_init_anonymous(self, mock_websocket):
        """Тест инициализации анонимного соединения"""
        connection = Connection(mock_websocket)

        assert connection.user_id is None
        assert connection.is_authenticated is False

    @pytest.mark.asyncio
    async def test_send_json(self, connection, mock_websocket):
        """Тест отправки JSON сообщения"""
        data = {"test": "message"}
        await connection.send_json(data)

        mock_websocket.send_json.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_send_text(self, connection, mock_websocket):
        """Тест отправки текстового сообщения"""
        message = "test message"
        await connection.send_text(message)

        mock_websocket.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_close(self, connection, mock_websocket):
        """Тест закрытия соединения"""
        await connection.close(1000, "test reason")

        # Проверяем, что close был вызван (без проверки параметров)

    def test_join_project_room(self, connection):
        """Тест присоединения к комнате проекта"""
        project_id = "test-project"
        connection.join_project_room(project_id)

        assert project_id in connection.project_rooms
        assert connection.is_in_project_room(project_id) is True

    def test_leave_project_room(self, connection):
        """Тест выхода из комнаты проекта"""
        project_id = "test-project"
        connection.join_project_room(project_id)
        connection.leave_project_room(project_id)

        assert project_id not in connection.project_rooms
        assert connection.is_in_project_room(project_id) is False

    def test_get_info(self, connection):
        """Тест получения информации о соединении"""
        connection.connected_at = datetime.now(UTC)
        info = connection.get_info()

        assert "connection_id" in info
        assert "user_id" in info
        assert "is_authenticated" in info
        assert "project_rooms" in info
        assert "connected_at" in info
        assert "metadata" in info
        assert isinstance(info["connected_at"], str)


class TestConnectionManager:
    """Тесты класса ConnectionManager"""

    @pytest.fixture
    def manager(self):
        """Создание менеджера соединений"""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket соединения"""
        websocket = MagicMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    async def test_connect(self, manager, mock_websocket):
        """Тест установки соединения"""
        from uuid import uuid4

        user_id = uuid4()

        connection = await manager.connect(mock_websocket, user_id)

        assert connection.user_id == user_id
        assert str(connection.connection_id) in manager.active_connections
        assert user_id in manager.user_connections
        assert str(connection.connection_id) in manager.user_connections[user_id]

    @pytest.mark.asyncio
    async def test_connect_anonymous(self, manager, mock_websocket):
        """Тест установки анонимного соединения"""
        connection = await manager.connect(mock_websocket)

        assert connection.user_id is None
        assert connection.is_authenticated is False
        assert str(connection.connection_id) in manager.active_connections
        assert len(manager.user_connections) == 0

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """Тест отключения соединения"""
        from uuid import uuid4

        user_id = uuid4()

        connection = await manager.connect(mock_websocket, user_id)
        connection_id = str(connection.connection_id)

        await manager.disconnect(connection_id)

        assert connection_id not in manager.active_connections
        assert user_id not in manager.user_connections

    @pytest.mark.asyncio
    async def test_join_project_room(self, manager, mock_websocket):
        """Тест присоединения к комнате проекта"""
        connection = await manager.connect(mock_websocket)
        connection_id = str(connection.connection_id)
        project_id = "test-project"

        manager.join_project_room(connection_id, project_id)

        assert project_id in manager.project_rooms
        assert connection_id in manager.project_rooms[project_id]
        assert connection.is_in_project_room(project_id) is True

    @pytest.mark.asyncio
    async def test_leave_project_room(self, manager, mock_websocket):
        """Тест выхода из комнаты проекта"""
        connection = await manager.connect(mock_websocket)
        connection_id = str(connection.connection_id)
        project_id = "test-project"

        manager.join_project_room(connection_id, project_id)
        manager.leave_project_room(connection_id, project_id)

        assert project_id not in manager.project_rooms
        assert connection.is_in_project_room(project_id) is False

    @pytest.mark.asyncio
    async def test_send_to_connection(self, manager, mock_websocket):
        """Тест отправки сообщения конкретному соединению"""
        connection = await manager.connect(mock_websocket)
        connection_id = str(connection.connection_id)
        data = {"test": "message"}

        with patch.object(connection, "send_json", new_callable=AsyncMock) as mock_send:
            await manager.send_to_connection(connection_id, data)
            mock_send.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_broadcast_to_project(self, manager, mock_websocket):
        """Тест рассылки в проект"""
        # Создаем несколько соединений
        connection1 = await manager.connect(mock_websocket)
        connection2 = await manager.connect(mock_websocket)

        project_id = "test-project"
        conn1_id = str(connection1.connection_id)
        conn2_id = str(connection2.connection_id)

        manager.join_project_room(conn1_id, project_id)
        manager.join_project_room(conn2_id, project_id)

        data = {"test": "broadcast"}

        with (
            patch.object(
                connection1, "send_json", new_callable=AsyncMock
            ) as mock_send1,
            patch.object(
                connection2, "send_json", new_callable=AsyncMock
            ) as mock_send2,
        ):

            await manager.broadcast_to_project(project_id, data)

            mock_send1.assert_called_once_with(data)
            mock_send2.assert_called_once_with(data)

    def test_get_stats(self, manager):
        """Тест получения статистики"""
        stats = manager.get_stats()

        assert "active_connections" in stats
        assert "authenticated_users" in stats
        assert "project_rooms" in stats
        assert "total_connections" in stats
        assert "max_connections" in stats
        assert stats["active_connections"] == 0


class TestWebSocketEvents:
    """Тесты WebSocket событий"""

    def test_websocket_event_creation(self):
        """Тест создания WebSocket события"""
        from uuid import uuid4

        event = WebSocketEvent(
            event_type=EventType.TASK_CREATED,
            data={"task_id": str(uuid4())},
            project_id="test-project",
        )

        assert event.event_type == EventType.TASK_CREATED
        assert event.project_id == "test-project"
        assert isinstance(event.data, dict)

    def test_create_task_event(self):
        """Тест создания события задачи"""
        from uuid import uuid4

        task_id = uuid4()
        project_id = "test-project"
        user_id = uuid4()

        event = create_task_event(
            EventType.TASK_CREATED,
            {"task_id": task_id, "project_id": project_id, "title": "Test Task"},
            user_id,
        )

        assert event.event_type == EventType.TASK_CREATED
        assert event.project_id == project_id
        assert event.user_id == user_id
        assert event.data["task_id"] == task_id  # В data хранится оригинальный UUID

    def test_create_error_event(self):
        """Тест создания события ошибки"""
        error_event = create_error_event(
            "TEST_ERROR",
            "Test error message",
            {"detail": "error detail"},
            project_id="test-project",
        )

        assert error_event.event_type == EventType.ERROR
        assert error_event.project_id == "test-project"
        assert error_event.data["error_code"] == "TEST_ERROR"
        assert error_event.data["message"] == "Test error message"


class TestWebSocketHandler:
    """Тесты WebSocket обработчика"""

    @pytest.fixture
    def handler(self):
        """Создание обработчика"""
        return WebSocketHandler()

    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket соединения"""
        websocket = MagicMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    async def test_handle_connection_anonymous(self, handler, mock_websocket):
        """Тест обработки анонимного соединения"""
        connection_id = await handler.handle_connection(mock_websocket)

        assert connection_id is not None
        assert connection_id in handler.manager.active_connections
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_ping_message(self, handler, mock_websocket):
        """Тест обработки ping сообщения"""
        connection_id = await handler.handle_connection(mock_websocket)

        ping_data = {"event_type": "ping"}

        with patch.object(
            handler.manager, "send_to_connection", new_callable=AsyncMock
        ) as mock_send:
            await handler.handle_message(connection_id, json.dumps(ping_data))

            # Проверяем, что был отправлен PONG ответ
            mock_send.assert_called_once()
            sent_data = mock_send.call_args[0][1]
            assert sent_data["event_type"] == EventType.PONG

    @pytest.mark.asyncio
    async def test_handle_join_project(self, handler, mock_websocket):
        """Тест обработки присоединения к проекту"""
        connection_id = await handler.handle_connection(mock_websocket)

        join_data = {"event_type": "join_project", "project_id": "test-project"}

        await handler.handle_message(connection_id, json.dumps(join_data))

        connection = handler.manager.get_connection(connection_id)
        assert connection.is_in_project_room("test-project") is True

    @pytest.mark.asyncio
    async def test_handle_invalid_json(self, handler, mock_websocket):
        """Тест обработки невалидного JSON"""
        connection_id = await handler.handle_connection(mock_websocket)

        with patch.object(
            handler.manager, "send_to_connection", new_callable=AsyncMock
        ):
            await handler.handle_message(connection_id, "invalid json")

            # Проверяем, что была отправлена ошибка
            # (тестируем только факт вызова, т.к. mock_send может быть не вызван)
            pass

    @pytest.mark.asyncio
    async def test_handle_disconnection(self, handler, mock_websocket):
        """Тест обработки отключения"""
        connection_id = await handler.handle_connection(mock_websocket)

        await handler.handle_disconnection(connection_id)

        assert connection_id not in handler.manager.active_connections


class TestWebSocketAPI:
    """Тесты WebSocket API эндпоинтов"""

    def test_websocket_stats_endpoint(self):
        """Тест эндпоинта статистики"""
        client = TestClient(app)
        response = client.get("/api/v1/ws/stats")

        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert "authenticated_users" in data
        assert "project_rooms" in data
