"""
Тесты интеграции уведомлений с WebSocket
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.services.notification_websocket_integration import (
    NotificationWebSocketIntegration,
    notify_project_websocket,
    notify_system_websocket,
    notify_user_websocket,
)


@pytest.mark.asyncio
class TestNotificationWebSocketIntegration:
    """Тесты интеграции уведомлений с WebSocket"""

    async def test_send_notification_to_user(self, db_session):
        """Тест отправки уведомления пользователю"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        notification = Notification(
            user_id=user.id,
            title="Test Notification",
            message="Test message",
            notification_type=NotificationType.TASK_ASSIGNED,
            action_url="/test-url",
        )
        db_session.add(notification)
        await db_session.commit()
        await db_session.refresh(notification)

        integration = NotificationWebSocketIntegration()

        # Мокаем метод отправки
        with patch.object(
            integration.websocket_handler, "send_notification", new_callable=AsyncMock
        ) as mock_send:
            await integration.send_notification_to_user(notification)

            # Проверяем, что метод был вызван с правильными параметрами
            mock_send.assert_called_once_with(
                user_id=user.id,
                title="Test Notification",
                message="Test message",
                notification_type=NotificationType.TASK_ASSIGNED,
                action_url="/test-url",
            )

    async def test_send_notification_to_user_error_handling(self, db_session):
        """Тест обработки ошибок при отправке уведомления"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        notification = Notification(
            user_id=user.id,
            title="Test Notification",
            message="Test message",
            notification_type=NotificationType.TASK_ASSIGNED,
        )
        db_session.add(notification)
        await db_session.commit()
        await db_session.refresh(notification)

        integration = NotificationWebSocketIntegration()

        # Мокаем метод отправки с исключением
        with patch.object(
            integration.websocket_handler, "send_notification", new_callable=AsyncMock
        ) as mock_send:
            mock_send.side_effect = Exception("WebSocket error")

            # Не должно вызывать исключение
            await integration.send_notification_to_user(notification)

            # Проверяем, что метод был вызван
            mock_send.assert_called_once()

    @patch("app.services.notification_websocket_integration.manager")
    async def test_broadcast_notification_to_project(self, mock_manager, db_session):
        """Тест рассылки уведомления участникам проекта"""
        from uuid import uuid4

        project_id = uuid4()
        user1_id = uuid4()
        user2_id = uuid4()

        # Мокаем соединения
        mock_connection1 = AsyncMock()
        mock_connection1.user_id = user1_id
        mock_connection2 = AsyncMock()
        mock_connection2.user_id = user2_id

        mock_manager.get_project_connections.return_value = [
            mock_connection1,
            mock_connection2,
        ]

        integration = NotificationWebSocketIntegration()

        with patch.object(
            integration.websocket_handler, "send_notification", new_callable=AsyncMock
        ) as mock_send:
            await integration.broadcast_notification_to_project(
                project_id=project_id,
                title="Project Notification",
                message="Project message",
                notification_type="info",
            )

            # Проверяем, что уведомление отправлено обоим пользователям
            assert mock_send.call_count == 2
            mock_send.assert_any_call(
                user_id=user1_id,
                title="Project Notification",
                message="Project message",
                notification_type="info",
            )
            mock_send.assert_any_call(
                user_id=user2_id,
                title="Project Notification",
                message="Project message",
                notification_type="info",
            )

    @patch("app.services.notification_websocket_integration.manager")
    async def test_broadcast_notification_exclude_user(self, mock_manager, db_session):
        """Тест исключения пользователя из рассылки"""
        from uuid import uuid4

        project_id = uuid4()
        user1_id = uuid4()
        user2_id = uuid4()
        exclude_user_id = user1_id

        # Мокаем соединения
        mock_connection1 = AsyncMock()
        mock_connection1.user_id = user1_id
        mock_connection2 = AsyncMock()
        mock_connection2.user_id = user2_id

        mock_manager.get_project_connections.return_value = [
            mock_connection1,
            mock_connection2,
        ]

        integration = NotificationWebSocketIntegration()

        with patch.object(
            integration.websocket_handler, "send_notification", new_callable=AsyncMock
        ) as mock_send:
            await integration.broadcast_notification_to_project(
                project_id=project_id,
                title="Project Notification",
                message="Project message",
                exclude_user_id=exclude_user_id,
            )

            # Проверяем, что уведомление отправлено только user2
            assert mock_send.call_count == 1
            mock_send.assert_called_once_with(
                user_id=user2_id,
                title="Project Notification",
                message="Project message",
                notification_type="info",
            )

    @patch("app.services.notification_websocket_integration.manager")
    async def test_send_system_notification_all_users(self, mock_manager):
        """Тест отправки системного уведомления всем пользователям"""
        from uuid import uuid4

        user1_id = uuid4()
        user2_id = uuid4()

        # Мокаем соединения
        mock_connection1 = AsyncMock()
        mock_connection1.user_id = user1_id
        mock_connection2 = AsyncMock()
        mock_connection2.user_id = user2_id

        mock_manager.get_all_connections.return_value = [
            mock_connection1,
            mock_connection2,
        ]

        integration = NotificationWebSocketIntegration()

        with patch.object(
            integration.websocket_handler, "send_notification", new_callable=AsyncMock
        ) as mock_send:
            await integration.send_system_notification(
                title="System Notification", message="System message"
            )

            # Проверяем, что уведомление отправлено обоим пользователям
            assert mock_send.call_count == 2
            mock_send.assert_any_call(
                user_id=user1_id,
                title="System Notification",
                message="System message",
                notification_type="system",
            )
            mock_send.assert_any_call(
                user_id=user2_id,
                title="System Notification",
                message="System message",
                notification_type="system",
            )

    @patch("app.services.notification_websocket_integration.manager")
    async def test_send_system_notification_specific_users(self, mock_manager):
        """Тест отправки системного уведомления конкретным пользователям"""
        from uuid import uuid4

        user1_id = uuid4()
        user3_id = uuid4()

        integration = NotificationWebSocketIntegration()

        with patch.object(
            integration.websocket_handler, "send_notification", new_callable=AsyncMock
        ) as mock_send:
            await integration.send_system_notification(
                title="System Notification",
                message="System message",
                user_ids=[user1_id, user3_id],
            )

            # Проверяем, что уведомление отправлено только указанным пользователям
            assert mock_send.call_count == 2
            mock_send.assert_any_call(
                user_id=user1_id,
                title="System Notification",
                message="System message",
                notification_type="system",
            )
            mock_send.assert_any_call(
                user_id=user3_id,
                title="System Notification",
                message="System message",
                notification_type="system",
            )


@pytest.mark.asyncio
class TestNotificationWebSocketFunctions:
    """Тесты удобных функций"""

    @patch(
        "app.services.notification_websocket_integration.notification_ws_integration"
    )
    async def test_notify_user_websocket(self, mock_integration):
        """Тест функции notify_user_websocket"""
        from uuid import uuid4

        user_id = uuid4()

        notification = Notification(
            user_id=user_id,
            title="Test Notification",
            message="Test message",
            notification_type=NotificationType.TASK_ASSIGNED,
        )

        # Настраиваем mock как AsyncMock для всего объекта
        mock_integration.send_notification_to_user = AsyncMock()

        await notify_user_websocket(notification)

        mock_integration.send_notification_to_user.assert_called_once_with(notification)

    @patch(
        "app.services.notification_websocket_integration.notification_ws_integration"
    )
    async def test_notify_project_websocket(self, mock_integration):
        """Тест функции notify_project_websocket"""
        from uuid import uuid4

        project_id = uuid4()
        title = "Project Title"
        message = "Project Message"
        exclude_user_id = uuid4()

        # Настраиваем mock как AsyncMock
        mock_integration.broadcast_notification_to_project = AsyncMock()

        await notify_project_websocket(
            project_id=project_id,
            title=title,
            message=message,
            notification_type="info",
            exclude_user_id=exclude_user_id,
        )

        mock_integration.broadcast_notification_to_project.assert_called_once_with(
            project_id=project_id,
            title=title,
            message=message,
            notification_type="info",
            exclude_user_id=exclude_user_id,
        )

    @patch(
        "app.services.notification_websocket_integration.notification_ws_integration"
    )
    async def test_notify_system_websocket(self, mock_integration):
        """Тест функции notify_system_websocket"""
        from uuid import uuid4

        title = "System Title"
        message = "System Message"
        user_ids = [uuid4(), uuid4()]

        # Настраиваем mock как AsyncMock
        mock_integration.send_system_notification = AsyncMock()

        await notify_system_websocket(title=title, message=message, user_ids=user_ids)

        mock_integration.send_system_notification.assert_called_once_with(
            title=title, message=message, user_ids=user_ids
        )
