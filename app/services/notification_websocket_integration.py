"""
Интеграция системы уведомлений с WebSocket
"""

from typing import TYPE_CHECKING
from uuid import UUID

from app.websocket.handlers import WebSocketHandler
from app.websocket.manager import manager

if TYPE_CHECKING:
    from app.models.notification import Notification


class NotificationWebSocketIntegration:
    """Интеграция уведомлений с WebSocket для real-time доставки"""

    def __init__(self):
        self.websocket_handler = WebSocketHandler()

    async def send_notification_to_user(self, notification: "Notification") -> None:
        """
        Отправить уведомление пользователю через WebSocket

        Args:
            notification: Объект уведомления
        """
        try:
            # Отправляем через существующий обработчик
            await self.websocket_handler.send_notification(
                user_id=notification.user_id,
                title=notification.title,
                message=notification.message,
                notification_type=notification.notification_type,
                action_url=notification.action_url,
            )
        except Exception as e:
            print(f"Ошибка отправки уведомления через WebSocket: {e}")

    async def broadcast_notification_to_project(
        self,
        project_id: UUID,
        title: str,
        message: str,
        notification_type: str = "info",
        exclude_user_id: UUID | None = None,
    ) -> None:
        """
        Отправить уведомление всем участникам проекта

        Args:
            project_id: ID проекта
            title: Заголовок уведомления
            message: Сообщение уведомления
            notification_type: Тип уведомления
            exclude_user_id: ID пользователя, которому не отправлять
        """
        try:
            # Получаем все соединения для проекта
            project_connections = manager.get_project_connections(str(project_id))

            for connection in project_connections:
                # Исключаем указанного пользователя
                if exclude_user_id and connection.user_id == exclude_user_id:
                    continue

                # Отправляем уведомление
                await self.websocket_handler.send_notification(
                    user_id=connection.user_id,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                )
        except Exception as e:
            print(f"Ошибка рассылки уведомления проекту: {e}")

    async def send_system_notification(
        self, title: str, message: str, user_ids: list[UUID] | None = None
    ) -> None:
        """
        Отправить системное уведомление

        Args:
            title: Заголовок уведомления
            message: Сообщение уведомления
            user_ids: Список ID пользователей (если None, всем)
        """
        try:
            if user_ids:
                # Отправляем указанным пользователям
                for user_id in user_ids:
                    await self.websocket_handler.send_notification(
                        user_id=user_id,
                        title=title,
                        message=message,
                        notification_type="system",
                    )
            else:
                # Отправляем всем подключенным пользователям
                await manager.broadcast_to_all(
                    {
                        "type": "notification",
                        "title": title,
                        "message": message,
                        "notification_type": "system",
                    }
                )
        except Exception as e:
            print(f"Ошибка отправки системного уведомления: {e}")


# Глобальный экземпляр интеграции
notification_ws_integration = NotificationWebSocketIntegration()


# Удобные функции для использования в других частях приложения


async def notify_user_websocket(notification: "Notification") -> None:
    """
    Отправить уведомление пользователю через WebSocket

    Args:
        notification: Объект уведомления
    """
    await notification_ws_integration.send_notification_to_user(notification)


async def notify_project_websocket(
    project_id: UUID,
    title: str,
    message: str,
    notification_type: str = "info",
    exclude_user_id: UUID | None = None,
) -> None:
    """
    Отправить уведомление всем участникам проекта

    Args:
        project_id: ID проекта
        title: Заголовок уведомления
        message: Сообщение уведомления
        notification_type: Тип уведомления
        exclude_user_id: ID пользователя, которому не отправлять
    """
    await notification_ws_integration.broadcast_notification_to_project(
        project_id=project_id,
        title=title,
        message=message,
        notification_type=notification_type,
        exclude_user_id=exclude_user_id,
    )


async def notify_system_websocket(
    title: str,
    message: str,
    user_ids: list[UUID] | None = None,
) -> None:
    """
    Отправить системное уведомление

    Args:
        title: Заголовок уведомления
        message: Сообщение уведомления
        user_ids: Список ID пользователей (если None, всем)
    """
    await notification_ws_integration.send_system_notification(
        title=title,
        message=message,
        user_ids=user_ids,
    )
