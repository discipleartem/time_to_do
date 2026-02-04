"""
Базовые тесты для системы уведомлений
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.services.notification_service import NotificationService


@pytest.mark.asyncio
class TestNotificationModel:
    """Тесты модели Notification"""

    async def test_notification_creation(self, db_session):
        """Тест создания уведомления"""
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

        assert notification.id is not None
        assert notification.user_id == user.id
        assert notification.title == "Test Notification"
        assert notification.message == "Test message"
        assert notification.notification_type == NotificationType.TASK_ASSIGNED
        assert notification.is_read is False
        assert notification.read_at is None
        assert notification.created_at is not None

    async def test_notification_mark_as_read(self, db_session):
        """Тест отметки уведомления как прочитанного"""
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

        # Отмечаем как прочитанное
        notification.mark_as_read()
        await db_session.commit()

        assert notification.is_read is True
        assert notification.read_at is not None

    async def test_notification_mark_as_unread(self, db_session):
        """Тест отметки уведомления как непрочитанного"""
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
            is_read=True,
            read_at=datetime.utcnow(),
        )
        db_session.add(notification)
        await db_session.commit()
        await db_session.refresh(notification)

        # Отмечаем как непрочитанное
        notification.mark_as_unread()
        await db_session.commit()

        assert notification.is_read is False
        assert notification.read_at is None

    async def test_notification_is_pending(self, db_session):
        """Тест свойства is_pending"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Непрочитанное уведомление
        notification_unread = Notification(
            user_id=user.id,
            title="Unread Notification",
            message="Unread message",
            notification_type=NotificationType.TASK_ASSIGNED,
            is_read=False,
        )
        db_session.add(notification_unread)

        # Прочитанное уведомление
        notification_read = Notification(
            user_id=user.id,
            title="Read Notification",
            message="Read message",
            notification_type=NotificationType.TASK_COMPLETED,
            is_read=True,
        )
        db_session.add(notification_read)
        await db_session.commit()

        assert notification_unread.is_pending is True
        assert notification_read.is_pending is False

    async def test_notification_is_recent(self, db_session):
        """Тест свойства is_recent"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Недавнее уведомление
        recent_notification = Notification(
            user_id=user.id,
            title="Recent Notification",
            message="Recent message",
            notification_type=NotificationType.TASK_ASSIGNED,
            created_at=datetime.now(UTC),
        )
        db_session.add(recent_notification)

        # Старое уведомление
        old_notification = Notification(
            user_id=user.id,
            title="Old Notification",
            message="Old message",
            notification_type=NotificationType.TASK_COMPLETED,
            created_at=datetime.now(UTC) - timedelta(days=2),
        )
        db_session.add(old_notification)
        await db_session.commit()

        assert recent_notification.is_recent is True
        assert old_notification.is_recent is False

    async def test_notification_to_dict(self, db_session):
        """Тест преобразования в словарь"""
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

        notification_dict = notification.to_dict()

        assert isinstance(notification_dict, dict)
        assert notification_dict["id"] == str(notification.id)
        assert notification_dict["user_id"] == str(user.id)
        assert notification_dict["title"] == "Test Notification"
        assert notification_dict["message"] == "Test message"
        assert notification_dict["notification_type"] == NotificationType.TASK_ASSIGNED
        assert notification_dict["action_url"] == "/test-url"
        assert notification_dict["is_read"] is False
        assert "created_at" in notification_dict
        assert "updated_at" in notification_dict


@pytest.mark.asyncio
class TestNotificationService:
    """Тесты сервиса уведомлений"""

    async def test_create_notification(self, db_session):
        """Тест создания уведомления через сервис"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        service = NotificationService(db_session)

        notification = await service.create_user_notification(
            user_id=user.id,
            title="Service Notification",
            message="Service message",
            notification_type=NotificationType.TASK_ASSIGNED,
        )

        assert notification.id is not None
        assert notification.user_id == user.id
        assert notification.title == "Service Notification"
        assert notification.message == "Service message"
        assert notification.notification_type == NotificationType.TASK_ASSIGNED

    async def test_get_user_notifications(self, db_session):
        """Тест получения уведомлений пользователя"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        service = NotificationService(db_session)

        # Создаем несколько уведомлений
        for i in range(5):
            await service.create_user_notification(
                user_id=user.id,
                title=f"Notification {i}",
                message=f"Message {i}",
                notification_type=NotificationType.TASK_ASSIGNED,
            )

        # Получаем все уведомления
        notifications = await service.get_user_notifications(user_id=user.id)
        assert len(notifications) == 5

        # Получаем только непрочитанные
        unread_notifications = await service.get_user_notifications(
            user_id=user.id, unread_only=True
        )
        assert len(unread_notifications) == 5

        # Отмечаем первое как прочитанное
        await service.mark_notification_read(notifications[0].id, user.id)

        # Проверяем количество непрочитанных
        unread_notifications = await service.get_user_notifications(
            user_id=user.id, unread_only=True
        )
        assert len(unread_notifications) == 4

    async def test_get_unread_count(self, db_session):
        """Тест получения количества непрочитанных уведомлений"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        service = NotificationService(db_session)

        # Создаем уведомления
        for i in range(3):
            await service.create_user_notification(
                user_id=user.id,
                title=f"Notification {i}",
                message=f"Message {i}",
                notification_type=NotificationType.PROJECT_MEMBER_ADDED,
            )

        # Проверяем количество непрочитанных
        count = await service.get_unread_count(user.id)
        assert count == 3

        # Отмечаем одно как прочитанное
        notifications = await service.get_user_notifications(user_id=user.id)
        await service.mark_notification_read(notifications[0].id, user.id)

        # Проверяем количество непрочитанных
        count = await service.get_unread_count(user.id)
        assert count == 2

    async def test_mark_all_as_read(self, db_session):
        """Тест отметки всех уведомлений как прочитанных"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        service = NotificationService(db_session)

        # Создаем уведомления
        for i in range(5):
            await service.create_user_notification(
                user_id=user.id,
                title=f"Notification {i}",
                message=f"Message {i}",
                notification_type=NotificationType.SPRINT_STARTED,
            )

        # Отмечаем все как прочитанные
        count = await service.mark_all_notifications_read(user.id)
        assert count == 5

        # Проверяем, что все прочитаны
        unread_count = await service.get_unread_count(user.id)
        assert unread_count == 0

    async def test_delete_notification(self, db_session):
        """Тест удаления уведомления"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        service = NotificationService(db_session)

        # Создаем уведомление
        notification = await service.create_user_notification(
            user_id=user.id,
            title="Test Notification",
            message="Test message",
            notification_type=NotificationType.TASK_COMPLETED,
        )

        # Удаляем уведомление
        success = await service.delete_notification(notification.id, user.id)
        assert success is True

        # Проверяем, что уведомление удалено
        deleted_notification = await service.get_notification_by_id(
            notification.id, user.id
        )
        assert deleted_notification is None

    async def test_delete_notification_wrong_user(self, db_session):
        """Тест удаления уведомления другим пользователем"""
        user1 = User(
            email="test1@example.com",
            username="testuser1",
            hashed_password="hashed_password",
        )
        user2 = User(
            email="test2@example.com",
            username="testuser2",
            hashed_password="hashed_password",
        )
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        service = NotificationService(db_session)

        # Создаем уведомление для user1
        notification = await service.create_user_notification(
            user_id=user1.id,
            title="Test Notification",
            message="Test message",
            notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
        )

        # Пытаемся удалить уведомление user2
        success = await service.delete_notification(notification.id, user2.id)
        assert success is False


class TestNotificationType:
    """Тесты типов уведомлений"""

    def test_notification_type_constants(self):
        """Тест констант типов уведомлений"""
        assert NotificationType.TASK_ASSIGNED == "task_assigned"
        assert NotificationType.TASK_COMPLETED == "task_completed"
        assert NotificationType.TASK_OVERDUE == "task_overdue"
        assert NotificationType.PROJECT_CREATED == "project_created"
        assert NotificationType.SPRINT_STARTED == "sprint_started"
        assert NotificationType.SYSTEM_ANNOUNCEMENT == "system_announcement"

    def test_notification_type_get_all_types(self):
        """Тест получения всех типов уведомлений"""
        all_types = NotificationType.get_all_types()

        assert isinstance(all_types, list)
        assert len(all_types) > 0
        assert NotificationType.TASK_ASSIGNED in all_types
        assert NotificationType.TASK_COMPLETED in all_types

    def test_notification_type_is_valid_type(self):
        """Тест валидации типа уведомления"""
        # Валидные типы
        assert NotificationType.is_valid_type(NotificationType.TASK_ASSIGNED) is True
        assert NotificationType.is_valid_type(NotificationType.TASK_COMPLETED) is True

        # Невалидные типы
        assert NotificationType.is_valid_type("invalid_type") is False
        assert NotificationType.is_valid_type("") is False
        assert NotificationType.is_valid_type(None) is False
