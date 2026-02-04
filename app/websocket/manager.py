"""
WebSocket менеджер - управление всеми соединениями
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from app.websocket.connection import Connection


class ConnectionManager:
    """Менеджер WebSocket соединений"""

    def __init__(self):
        """Инициализация менеджера"""
        # Активные соединения
        self.active_connections: dict[str, Connection] = {}

        # Соединения по пользователям
        self.user_connections: dict[UUID, set[str]] = {}

        # Комнаты проектов
        self.project_rooms: dict[str, set[str]] = {}

        # Статистика
        self.total_connections = 0
        self.max_connections = 0

    async def connect(
        self, websocket: WebSocket, user_id: UUID | None = None
    ) -> Connection:
        """
        Установка нового WebSocket соединения

        Args:
            websocket: WebSocket соединение
            user_id: ID пользователя (если аутентифицирован)

        Returns:
            Connection: Объект соединения
        """
        await websocket.accept()

        # Создание объекта соединения
        connection = Connection(websocket, user_id)
        connection.connected_at = datetime.now(UTC)

        # Регистрация соединения
        self.active_connections[str(connection.connection_id)] = connection
        self.total_connections += 1
        self.max_connections = max(self.max_connections, len(self.active_connections))

        # Регистрация пользователя
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(str(connection.connection_id))

        print(f"🔗 Новое соединение: {connection}")
        return connection

    async def disconnect(self, connection_id: str) -> None:
        """
        Отключение WebSocket соединения

        Args:
            connection_id: ID соединения
        """
        if connection_id not in self.active_connections:
            return

        connection = self.active_connections[connection_id]

        # Удаление из комнат проектов
        for project_id in connection.project_rooms:
            self.leave_project_room(connection_id, project_id)

        # Удаление из пользователей
        if connection.user_id and connection.user_id in self.user_connections:
            self.user_connections[connection.user_id].discard(connection_id)
            if not self.user_connections[connection.user_id]:
                del self.user_connections[connection.user_id]

        # Удаление соединения
        del self.active_connections[connection_id]

        print(f"🔌 Соединение отключено: {connection}")

    def join_project_room(self, connection_id: str, project_id: str) -> None:
        """
        Присоединение соединения к комнате проекта

        Args:
            connection_id: ID соединения
            project_id: ID проекта
        """
        if connection_id not in self.active_connections:
            return

        connection = self.active_connections[connection_id]
        connection.join_project_room(project_id)

        # Добавление в комнату проекта
        if project_id not in self.project_rooms:
            self.project_rooms[project_id] = set()
        self.project_rooms[project_id].add(connection_id)

        print(f"📂 Соединение {connection_id} присоединилось к проекту {project_id}")

    def leave_project_room(self, connection_id: str, project_id: str) -> None:
        """
        Выход соединения из комнаты проекта

        Args:
            connection_id: ID соединения
            project_id: ID проекта
        """
        if connection_id not in self.active_connections:
            return

        connection = self.active_connections[connection_id]
        connection.leave_project_room(project_id)

        # Удаление из комнаты проекта
        if project_id in self.project_rooms:
            self.project_rooms[project_id].discard(connection_id)
            if not self.project_rooms[project_id]:
                del self.project_rooms[project_id]

        print(f"📤 Соединение {connection_id} покинуло проект {project_id}")

    async def send_to_connection(
        self, connection_id: str, data: dict[str, Any]
    ) -> None:
        """
        Отправка сообщения конкретному соединению

        Args:
            connection_id: ID соединения
            data: Данные для отправки
        """
        if connection_id not in self.active_connections:
            return

        connection = self.active_connections[connection_id]
        await connection.send_json(data)

    async def send_to_user(self, user_id: UUID, data: dict[str, Any]) -> None:
        """
        Отправка сообщения всем соединениям пользователя

        Args:
            user_id: ID пользователя
            data: Данные для отправки
        """
        if user_id not in self.user_connections:
            return

        for connection_id in self.user_connections[user_id]:
            await self.send_to_connection(connection_id, data)

    async def broadcast_to_project(
        self,
        project_id: str,
        data: dict[str, Any],
        exclude_connection: str | None = None,
    ) -> None:
        """
        Рассылка сообщения всем в комнате проекта

        Args:
            project_id: ID проекта
            data: Данные для отправки
            exclude_connection: ID соединения для исключения
        """
        if project_id not in self.project_rooms:
            return

        for connection_id in self.project_rooms[project_id]:
            if exclude_connection and connection_id == exclude_connection:
                continue
            await self.send_to_connection(connection_id, data)

    async def broadcast_to_all(
        self, data: dict[str, Any], exclude_connection: str | None = None
    ) -> None:
        """
        Рассылка сообщения всем активным соединениям

        Args:
            data: Данные для отправки
            exclude_connection: ID соединения для исключения
        """
        for connection_id in self.active_connections:
            if exclude_connection and connection_id == exclude_connection:
                continue
            await self.send_to_connection(connection_id, data)

    def get_connection(self, connection_id: str) -> Connection | None:
        """
        Получение соединения по ID

        Args:
            connection_id: ID соединения

        Returns:
            Optional[Connection]: Объект соединения или None
        """
        return self.active_connections.get(connection_id)

    def get_user_connections(self, user_id: UUID) -> list[Connection]:
        """
        Получение всех соединений пользователя

        Args:
            user_id: ID пользователя

        Returns:
            List[Connection]: Список соединений
        """
        if user_id not in self.user_connections:
            return []

        return [
            self.active_connections[conn_id]
            for conn_id in self.user_connections[user_id]
            if conn_id in self.active_connections
        ]

    def get_project_connections(self, project_id: str) -> list[Connection]:
        """
        Получение всех соединений в комнате проекта

        Args:
            project_id: ID проекта

        Returns:
            List[Connection]: Список соединений
        """
        if project_id not in self.project_rooms:
            return []

        return [
            self.active_connections[conn_id]
            for conn_id in self.project_rooms[project_id]
            if conn_id in self.active_connections
        ]

    def get_stats(self) -> dict[str, Any]:
        """
        Получение статистики менеджера

        Returns:
            Dict[str, Any]: Статистика
        """
        return {
            "active_connections": len(self.active_connections),
            "authenticated_users": len(self.user_connections),
            "project_rooms": len(self.project_rooms),
            "total_connections": self.total_connections,
            "max_connections": self.max_connections,
            "connections_per_user": {
                str(user_id): len(connections)
                for user_id, connections in self.user_connections.items()
            },
            "connections_per_project": {
                project_id: len(connections)
                for project_id, connections in self.project_rooms.items()
            },
        }

    async def cleanup_stale_connections(self) -> int:
        """
        Очистка неактивных соединений

        Returns:
            int: Количество удаленных соединений
        """
        stale_connections = []

        for connection_id, connection in self.active_connections.items():
            try:
                # Проверка активности соединения ping/pong
                # Используем send_text для ping, так как FastAPI WebSocket не имеет метода ping()
                await connection.websocket.send_text("ping")
            except Exception:
                stale_connections.append(connection_id)

        for connection_id in stale_connections:
            await self.disconnect(connection_id)

        if stale_connections:
            print(f"🧹 Очищено {len(stale_connections)} неактивных соединений")

        return len(stale_connections)


# Глобальный экземпляр менеджера
manager = ConnectionManager()
