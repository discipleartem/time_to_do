"""
WebSocket обработчики событий
"""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from app.auth.dependencies import get_current_user_ws
from app.websocket.events import (
    EventType,
    WebSocketEvent,
    create_error_event,
    create_user_event,
)
from app.websocket.manager import manager


class WebSocketHandler:
    """Обработчик WebSocket соединений и событий"""

    def __init__(self):
        """Инициализация обработчика"""
        self.manager = manager

    async def handle_connection(
        self, websocket: WebSocket, token: str | None = None
    ) -> str:
        """
        Обработка нового WebSocket соединения

        Args:
            websocket: WebSocket соединение
            token: JWT токен для аутентификации

        Returns:
            str: ID соединения
        """
        user_id = None

        # Попытка аутентификации
        if token:
            try:
                user = await get_current_user_ws(token)
                user_id = user.id
            except Exception as e:
                print(f"Ошибка аутентификации WebSocket: {e}")

        # Установка соединения
        connection = await self.manager.connect(websocket, user_id)

        # Отправка приветственного сообщения
        welcome_event = WebSocketEvent(
            event_type=EventType.USER_ONLINE if user_id else EventType.PING,
            data={
                "connection_id": str(connection.connection_id),
                "message": "Соединение установлено",
                "authenticated": user_id is not None,
            },
            project_id=None,
            user_id=user_id,
            timestamp=datetime.now(UTC).isoformat(),
        )

        await connection.send_json(welcome_event.model_dump())

        # Уведомление о входе пользователя в систему
        if user_id:
            user_event = create_user_event(
                EventType.USER_ONLINE,
                {
                    "user_id": user_id,
                    "username": f"user_{user_id}",  # В реальности получить из user
                    "status": "online",
                },
            )
            await self.manager.broadcast_to_all(user_event.model_dump())

        return str(connection.connection_id)

    async def handle_message(self, connection_id: str, message: str) -> None:
        """
        Обработка входящего сообщения

        Args:
            connection_id: ID соединения
            message: Сообщение
        """
        connection = self.manager.get_connection(connection_id)
        if not connection:
            return

        try:
            data = json.loads(message)
            event_type = data.get("event_type")

            # Обработка разных типов сообщений
            if event_type == "ping":
                await self._handle_ping(connection_id)
            elif event_type == "join_project":
                await self._handle_join_project(connection_id, data)
            elif event_type == "leave_project":
                await self._handle_leave_project(connection_id, data)
            else:
                # Неизвестный тип события
                error_event = create_error_event(
                    "UNKNOWN_EVENT",
                    f"Неизвестный тип события: {event_type}",
                    {"received_data": data},
                    user_id=connection.user_id,
                )
                await connection.send_json(error_event.model_dump())

        except json.JSONDecodeError:
            error_event = create_error_event(
                "INVALID_JSON",
                "Невалидный JSON",
                {"message": message},
                user_id=connection.user_id,
            )
            await connection.send_json(error_event.model_dump())
        except Exception as e:
            error_event = create_error_event(
                "MESSAGE_ERROR",
                f"Ошибка обработки сообщения: {str(e)}",
                {"message": message},
                user_id=connection.user_id,
            )
            await connection.send_json(error_event.model_dump())

    async def handle_disconnection(self, connection_id: str) -> None:
        """
        Обработка отключения соединения

        Args:
            connection_id: ID соединения
        """
        connection = self.manager.get_connection(connection_id)
        if connection and connection.user_id:
            # Уведомление о выходе пользователя
            user_event = create_user_event(
                EventType.USER_OFFLINE,
                {
                    "user_id": connection.user_id,
                    "username": f"user_{connection.user_id}",
                    "status": "offline",
                },
            )
            await self.manager.broadcast_to_all(user_event.model_dump())

        await self.manager.disconnect(connection_id)

    async def _handle_ping(self, connection_id: str) -> None:
        """
        Обработка ping сообщения

        Args:
            connection_id: ID соединения
        """
        pong_event = WebSocketEvent(
            event_type=EventType.PONG,
            data={"timestamp": datetime.now(UTC).isoformat()},
            project_id=None,
            user_id=None,
            timestamp=datetime.now(UTC).isoformat(),
        )
        await self.manager.send_to_connection(connection_id, pong_event.model_dump())

    async def _handle_join_project(
        self, connection_id: str, data: dict[str, Any]
    ) -> None:
        """
        Обработка присоединения к проекту

        Args:
            connection_id: ID соединения
            data: Данные сообщения
        """
        project_id = data.get("project_id")
        if not project_id:
            connection = self.manager.get_connection(connection_id)
            error_event = create_error_event(
                "MISSING_PROJECT_ID",
                "Отсутствует project_id",
                user_id=connection.user_id if connection else None,
            )
            await self.manager.send_to_connection(
                connection_id, error_event.model_dump()
            )
            return

        # Присоединение к комнате проекта
        self.manager.join_project_room(connection_id, project_id)

        # Подтверждение присоединения
        connection = self.manager.get_connection(connection_id)
        response_event = WebSocketEvent(
            event_type=EventType.PROJECT_MEMBER_ADDED,
            data={
                "project_id": project_id,
                "connection_id": connection_id,
                "message": f"Присоединен к проекту {project_id}",
            },
            project_id=project_id,
            user_id=connection.user_id if connection else None,
            timestamp=datetime.now(UTC).isoformat(),
        )
        await self.manager.send_to_connection(
            connection_id, response_event.model_dump()
        )

    async def _handle_leave_project(
        self, connection_id: str, data: dict[str, Any]
    ) -> None:
        """
        Обработка выхода из проекта

        Args:
            connection_id: ID соединения
            data: Данные сообщения
        """
        project_id = data.get("project_id")
        if not project_id:
            connection = self.manager.get_connection(connection_id)
            error_event = create_error_event(
                "MISSING_PROJECT_ID",
                "Отсутствует project_id",
                user_id=connection.user_id if connection else None,
            )
            await self.manager.send_to_connection(
                connection_id, error_event.model_dump()
            )
            return

        # Выход из комнаты проекта
        self.manager.leave_project_room(connection_id, project_id)

        # Подтверждение выхода
        connection = self.manager.get_connection(connection_id)
        response_event = WebSocketEvent(
            event_type=EventType.PROJECT_MEMBER_REMOVED,
            data={
                "project_id": project_id,
                "connection_id": connection_id,
                "message": f"Покинул проект {project_id}",
            },
            project_id=project_id,
            user_id=connection.user_id if connection else None,
            timestamp=datetime.now(UTC).isoformat(),
        )
        await self.manager.send_to_connection(
            connection_id, response_event.model_dump()
        )

    async def broadcast_task_event(
        self,
        event_type: EventType,
        task_data: dict[str, Any],
        user_id: UUID | None = None,
    ) -> None:
        """
        Рассылка события задачи

        Args:
            event_type: Тип события
            task_data: Данные задачи
            user_id: ID пользователя
        """
        from app.websocket.events import create_task_event

        event = create_task_event(event_type, task_data, user_id)

        # Рассылка в проект
        project_id = task_data.get("project_id")
        if project_id:
            await self.manager.broadcast_to_project(
                project_id,
                event.model_dump(),
                exclude_connection=None,  # Рассылать всем включая отправителя
            )

    async def broadcast_comment_event(
        self,
        event_type: EventType,
        comment_data: dict[str, Any],
        user_id: UUID | None = None,
    ) -> None:
        """
        Рассылка события комментария

        Args:
            event_type: Тип события
            comment_data: Данные комментария
            user_id: ID пользователя
        """
        from app.websocket.events import create_comment_event

        event = create_comment_event(event_type, comment_data, user_id)

        # Рассылка в проект
        project_id = comment_data.get("project_id")
        if project_id:
            await self.manager.broadcast_to_project(
                project_id, event.model_dump(), exclude_connection=None
            )

    async def broadcast_project_event(
        self,
        event_type: EventType,
        project_data: dict[str, Any],
        user_id: UUID | None = None,
    ) -> None:
        """
        Рассылка события проекта

        Args:
            event_type: Тип события
            project_data: Данные проекта
            user_id: ID пользователя
        """
        from app.websocket.events import create_project_event

        event = create_project_event(event_type, project_data, user_id)

        # Рассылка в проект
        project_id = project_data.get("project_id")
        if project_id:
            await self.manager.broadcast_to_project(
                project_id, event.model_dump(), exclude_connection=None
            )

    async def broadcast_sprint_event(
        self,
        event_type: EventType,
        sprint_data: dict[str, Any],
        user_id: UUID | None = None,
    ) -> None:
        """
        Рассылка события спринта

        Args:
            event_type: Тип события
            sprint_data: Данные спринта
            user_id: ID пользователя
        """
        from app.websocket.events import create_sprint_event

        event = create_sprint_event(event_type, sprint_data, user_id)

        # Рассылка в проект
        project_id = sprint_data.get("project_id")
        if project_id:
            await self.manager.broadcast_to_project(
                project_id, event.model_dump(), exclude_connection=None
            )

    async def broadcast_time_event(
        self,
        event_type: EventType,
        time_data: dict[str, Any],
        user_id: UUID | None = None,
    ) -> None:
        """
        Рассылка события времени

        Args:
            event_type: Тип события
            time_data: Данные времени
            user_id: ID пользователя
        """
        from app.websocket.events import create_time_event

        event = create_time_event(event_type, time_data, user_id)

        # Рассылка в проект
        project_id = time_data.get("project_id")
        if project_id:
            await self.manager.broadcast_to_project(
                project_id, event.model_dump(), exclude_connection=None
            )

    async def send_notification(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: str = "info",
        action_url: str | None = None,
    ) -> None:
        """
        Отправка уведомления пользователю

        Args:
            user_id: ID пользователя
            title: Заголовок уведомления
            message: Сообщение уведомления
            notification_type: Тип уведомления
            action_url: URL для действия
        """
        from app.websocket.events import create_notification_event

        event = create_notification_event(
            title=title,
            message=message,
            notification_type=notification_type,
            action_url=action_url,
            user_id=user_id,
        )

        await self.manager.send_to_user(user_id, event.model_dump())


# Глобальный экземпляр обработчика
handler = WebSocketHandler()
