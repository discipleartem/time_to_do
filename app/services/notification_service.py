"""
Сервис для управления уведомлениями
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


# Временные классы для уведомлений (позже создадим модели)
class NotificationType(str):
    """Типы уведомлений"""

    TASK_ASSIGNED = "task_assigned"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    COMMENT_ADDED = "comment_added"
    PROJECT_INVITED = "project_invited"
    PROJECT_UPDATED = "project_updated"
    SPRINT_STARTED = "sprint_started"
    SPRINT_COMPLETED = "sprint_completed"


class Notification:
    """Временный класс уведомления"""

    def __init__(
        self,
        id: str,
        user_id: str,
        type: NotificationType,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
        is_read: bool = False,
        created_at: datetime | None = None,
    ):
        self.id = id
        self.user_id = user_id
        self.type = type
        self.title = title
        self.message = message
        self.data = data or {}
        self.is_read = is_read
        self.created_at = created_at or datetime.now(UTC)


class NotificationService:
    """Сервис для работы с уведомлениями"""

    async def create_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> Notification:
        """Создание уведомления"""
        # Временная реализация - в реальном проекте здесь будет сохранение в БД
        notification = Notification(
            id=str(uuid4()),
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            data=data,
        )

        # TODO: сохранить в базу данных

        return notification

    async def get_user_notifications(
        self, user_id: str, unread_only: bool = False, limit: int = 50
    ) -> list[Notification]:
        """Получение уведомлений пользователя"""
        # Временная реализация
        return []

    async def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """Отметить уведомление как прочитанное"""
        # Временная реализация
        return True

    async def mark_all_notifications_read(self, user_id: str) -> int:
        """Отметить все уведомления как прочитанные"""
        # Временная реализация
        return 0

    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Удалить уведомление"""
        # Временная реализация
        return True

    async def get_unread_count(self, user_id: str) -> int:
        """Получить количество непрочитанных уведомлений"""
        # Временная реализация
        return 0

    # Методы для создания специфических уведомлений

    async def notify_task_assigned(
        self, task_id: str, task_title: str, assignee_id: str, assigner_name: str
    ) -> Notification:
        """Уведомление о назначении задачи"""
        return await self.create_notification(
            user_id=assignee_id,
            notification_type=NotificationType(NotificationType.TASK_ASSIGNED),
            title="Новая задача",
            message=f"{assigner_name} назначил(а) вам задачу: {task_title}",
            data={
                "task_id": task_id,
                "task_title": task_title,
                "assigner_name": assigner_name,
            },
        )

    async def notify_task_updated(
        self, task_id: str, task_title: str, updated_by_name: str, changes: list[str]
    ) -> list[Notification]:
        """Уведомление об обновлении задачи"""
        notifications: list[Notification] = []

        # Получаем участников задачи
        # TODO: получить участников задачи из базы данных

        message = f"{updated_by_name} обновил(а) задачу: {task_title}"
        if changes:
            message += f" ({', '.join(changes)})"

        # Временная реализация
        return notifications

    async def notify_task_completed(
        self, task_id: str, task_title: str, completed_by_name: str
    ) -> list[Notification]:
        """Уведомление о завершении задачи"""
        notifications: list[Notification] = []

        # Получаем создателя и других участников
        # TODO: получить участников задачи из базы данных

        # Временная реализация
        return notifications

    async def notify_comment_added(
        self,
        task_id: str,
        task_title: str,
        comment_content: str,
        author_name: str,
        exclude_user_id: str,
    ) -> list[Notification]:
        """Уведомление о добавлении комментария"""
        notifications: list[Notification] = []

        # Получаем участников задачи, кроме автора комментария
        # TODO: получить участников задачи из базы данных

        # Временная реализация
        return notifications

    async def notify_project_invited(
        self,
        project_id: str,
        project_name: str,
        invited_user_id: str,
        inviter_name: str,
    ) -> Notification:
        """Уведомление о приглашении в проект"""
        return await self.create_notification(
            user_id=invited_user_id,
            notification_type=NotificationType(NotificationType.PROJECT_INVITED),
            title="Приглашение в проект",
            message=f"{inviter_name} пригласил(а) вас в проект: {project_name}",
            data={
                "project_id": project_id,
                "project_name": project_name,
                "inviter_name": inviter_name,
            },
        )

    async def notify_sprint_started(
        self, sprint_id: str, sprint_name: str, project_id: str, project_name: str
    ) -> list[Notification]:
        """Уведомление о начале спринта"""
        notifications: list[Notification] = []

        # Получаем всех участников проекта
        # TODO: получить участников проекта из базы данных

        # Временная реализация
        return notifications

    async def notify_sprint_completed(
        self, sprint_id: str, sprint_name: str, project_id: str, project_name: str
    ) -> list[Notification]:
        """Уведомление о завершении спринта"""
        notifications: list[Notification] = []

        # Получаем всех участников проекта
        # TODO: получить участников проекта из базы данных

        # Временная реализация
        return notifications

    async def send_bulk_notifications(
        self, notifications: list[dict[str, Any]]
    ) -> list[Notification]:
        """Массовая отправка уведомлений"""
        created_notifications = []

        for notification_data in notifications:
            notification = await self.create_notification(
                user_id=notification_data["user_id"],
                notification_type=NotificationType(notification_data["type"]),
                title=notification_data["title"],
                message=notification_data["message"],
                data=notification_data.get("data"),
            )
            created_notifications.append(notification)

        return created_notifications

    async def cleanup_old_notifications(
        self, days_old: int = 30, read_only: bool = True
    ) -> int:
        """Очистка старых уведомлений"""
        # Временная реализация
        return 0

    async def get_notification_preferences(self, user_id: str) -> dict[str, bool]:
        """Получение настроек уведомлений пользователя"""
        # Временная реализация - по умолчанию все включены
        return {
            "task_assigned": True,
            "task_updated": True,
            "task_completed": True,
            "comment_added": True,
            "project_invited": True,
            "project_updated": True,
            "sprint_started": True,
            "sprint_completed": True,
        }

    async def update_notification_preferences(
        self, user_id: str, preferences: dict[str, bool]
    ) -> dict[str, bool]:
        """Обновление настроек уведомлений пользователя"""
        # Временная реализация
        return preferences

    async def should_send_notification(
        self, user_id: str, notification_type: NotificationType
    ) -> bool:
        """Проверка, следует ли отправлять уведомление"""
        preferences = await self.get_notification_preferences(user_id)
        return preferences.get(str(notification_type), True)


# Глобальный экземпляр сервиса
notification_service = NotificationService()
