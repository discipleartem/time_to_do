"""
WebSocket соединение - управление индивидуальным подключением
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import WebSocket


class Connection:
    """Класс для управления WebSocket соединением"""

    def __init__(self, websocket: WebSocket, user_id: UUID | None = None):
        """
        Инициализация соединения

        Args:
            websocket: WebSocket соединение
            user_id: ID пользователя (если аутентифицирован)
        """
        self.websocket = websocket
        self.connection_id = uuid4()
        self.user_id = user_id
        self.project_rooms: set[str] = set()  # Комнаты проектов
        self.is_authenticated = user_id is not None
        self.metadata: dict[str, Any] = {}
        self.connected_at: datetime | None = None

    async def send_json(self, data: dict[str, Any]) -> None:
        """
        Отправка JSON сообщения

        Args:
            data: Данные для отправки
        """
        try:
            await self.websocket.send_json(data)
        except Exception as e:
            # Логирование ошибки отправки
            print(f"Ошибка отправки сообщения {self.connection_id}: {e}")

    async def send_text(self, message: str) -> None:
        """
        Отправка текстового сообщения

        Args:
            message: Текстовое сообщение
        """
        try:
            await self.websocket.send_text(message)
        except Exception as e:
            # Логирование ошибки отправки
            print(f"Ошибка отправки текста {self.connection_id}: {e}")

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """
        Закрытие соединения

        Args:
            code: Код закрытия
            reason: Причина закрытия
        """
        try:
            await self.websocket.close(code=code, reason=reason)
        except Exception as e:
            # Логирование ошибки закрытия
            print(f"Ошибка закрытия соединения {self.connection_id}: {e}")

    def join_project_room(self, project_id: str) -> None:
        """
        Присоединение к комнате проекта

        Args:
            project_id: ID проекта
        """
        self.project_rooms.add(project_id)

    def leave_project_room(self, project_id: str) -> None:
        """
        Выход из комнаты проекта

        Args:
            project_id: ID проекта
        """
        self.project_rooms.discard(project_id)

    def is_in_project_room(self, project_id: str) -> bool:
        """
        Проверка нахождения в комнате проекта

        Args:
            project_id: ID проекта

        Returns:
            bool: True если в комнате
        """
        return project_id in self.project_rooms

    def get_info(self) -> dict[str, Any]:
        """
        Получение информации о соединении

        Returns:
            Dict[str, Any]: Информация о соединении
        """
        return {
            "connection_id": str(self.connection_id),
            "user_id": str(self.user_id) if self.user_id else None,
            "is_authenticated": self.is_authenticated,
            "project_rooms": list(self.project_rooms),
            "connected_at": (
                self.connected_at.isoformat() if self.connected_at else None
            ),
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """Строковое представление"""
        user_info = f"user:{self.user_id}" if self.user_id else "anonymous"
        return f"Connection({self.connection_id}, {user_info})"

    def __repr__(self) -> str:
        """Детальное строковое представление"""
        return (
            f"Connection(id={self.connection_id}, user_id={self.user_id}, "
            f"authenticated={self.is_authenticated}, rooms={len(self.project_rooms)})"
        )
