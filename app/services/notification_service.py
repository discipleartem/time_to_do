"""Сервис для управления уведомлениями."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.notification import Notification, NotificationType
from app.models.project import ProjectMember
from app.models.task import Task
from app.schemas.notification import (
    NotificationCreate,
    NotificationFactory,
    NotificationPreferences,
    NotificationStats,
    ProjectMemberAddedNotification,
    SprintCompletedNotification,
    SprintStartedNotification,
    TaskAssignedNotification,
    TaskCompletedNotification,
)
from app.services.notification_websocket_integration import notify_user_websocket


class NotificationService:
    """Сервис для работы с уведомлениями."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        notification_data: NotificationCreate,
    ) -> Notification:
        """Создание уведомления."""
        notification = Notification(**notification_data.model_dump())
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        # Отправляем уведомление через WebSocket
        try:
            await notify_user_websocket(notification)
        except Exception as e:
            # Логируем ошибку, но не прерываем создание уведомления
            print(f"Ошибка отправки уведомления через WebSocket: {e}")

        return notification

    async def create_user_notification(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: str,
        project_id: UUID | None = None,
        task_id: UUID | None = None,
        sprint_id: UUID | None = None,
        action_url: str | None = None,
        metadata_json: dict | None = None,
    ) -> Notification:
        """Создание уведомления пользователя с удобными параметрами."""
        import json

        notification_data = NotificationCreate(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            project_id=project_id,
            task_id=task_id,
            sprint_id=sprint_id,
            action_url=action_url,
            metadata_json=json.dumps(metadata_json) if metadata_json else None,
        )
        return await self.create_notification(notification_data)

    async def get_user_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
        notification_type: str | None = None,
    ) -> list[Notification]:
        """Получение уведомлений пользователя."""
        query = select(Notification).where(Notification.user_id == user_id)  # type: ignore[arg-type]

        if unread_only:
            query = query.where(Notification.is_read == False)  # type: ignore[arg-type]

        if notification_type:
            query = query.where(Notification.notification_type == notification_type)  # type: ignore[arg-type]

        query = query.order_by(desc(Notification.created_at))  # type: ignore[arg-type]
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_notification_by_id(
        self, notification_id: UUID, user_id: UUID
    ) -> Notification | None:
        """Получение уведомления по ID."""
        query = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,  # type: ignore[arg-type]
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def mark_notification_read(
        self, notification_id: UUID, user_id: UUID
    ) -> Notification | None:
        """Отметить уведомление как прочитанное."""
        notification = await self.get_notification_by_id(notification_id, user_id)
        if notification:
            notification.mark_as_read()
            await self.db.commit()
            await self.db.refresh(notification)
        return notification

    async def mark_notifications_unread(
        self, notification_ids: list[UUID], user_id: UUID
    ) -> list[Notification]:
        """Отметить уведомления как непрочитанные."""
        query = select(Notification).where(
            Notification.id.in_(notification_ids),
            Notification.user_id == user_id,  # type: ignore[arg-type]
        )
        result = await self.db.execute(query)
        notifications = result.scalars().all()

        for notification in notifications:
            notification.mark_as_unread()

        await self.db.commit()
        return list(notifications)

    async def mark_all_notifications_read(self, user_id: UUID) -> int:
        """Отметить все уведомления как прочитанные."""
        query = (
            select(Notification)
            .where(
                Notification.user_id == user_id,  # type: ignore[arg-type]
                Notification.is_read == False,  # type: ignore[arg-type]
            )
            .with_for_update()
        )
        result = await self.db.execute(query)
        notifications = result.scalars().all()

        for notification in notifications:
            notification.mark_as_read()

        await self.db.commit()
        return len(notifications)

    async def delete_notification(self, notification_id: UUID, user_id: UUID) -> bool:
        """Удалить уведомление."""
        notification = await self.get_notification_by_id(notification_id, user_id)
        if notification:
            await self.db.delete(notification)
            await self.db.commit()
            return True
        return False

    async def delete_notifications_bulk(
        self, notification_ids: list[UUID], user_id: UUID
    ) -> int:
        """Массовое удаление уведомлений."""
        query = select(Notification).where(
            Notification.id.in_(notification_ids),
            Notification.user_id == user_id,  # type: ignore[arg-type]
        )
        result = await self.db.execute(query)
        notifications = result.scalars().all()

        for notification in notifications:
            await self.db.delete(notification)

        await self.db.commit()
        return len(notifications)

    async def get_unread_count(self, user_id: UUID) -> int:
        """Получить количество непрочитанных уведомлений."""
        query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,  # type: ignore[arg-type]
            Notification.is_read == False,  # type: ignore[arg-type]
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_notification_stats(self, user_id: UUID) -> NotificationStats:
        """Получить статистику уведомлений пользователя."""
        # Общая статистика
        total_query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id  # type: ignore[arg-type]
        )
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0

        # Непрочитанные
        unread_query = (
            select(Notification)
            .where(
                Notification.user_id == user_id,  # type: ignore[arg-type]
                Notification.is_read == False,  # type: ignore[arg-type]
            )
            .with_for_update()
        )
        unread_result = await self.db.execute(unread_query)
        unread = len(unread_result.scalars().all()) or 0

        # Недавние (менее 24 часов)
        recent_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24)
        recent_query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,  # type: ignore[arg-type]
            Notification.created_at >= recent_time,  # type: ignore[arg-type]
        )
        recent_result = await self.db.execute(recent_query)
        recent = recent_result.scalar() or 0

        # По типам
        task_types = [
            NotificationType.TASK_ASSIGNED,
            NotificationType.TASK_COMPLETED,
            NotificationType.TASK_OVERDUE,
            NotificationType.TASK_MOVED,
            NotificationType.TASK_COMMENT_ADDED,
        ]
        task_query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,  # type: ignore[arg-type]
            Notification.notification_type.in_(task_types),  # type: ignore[attr-defined]
        )
        task_result = await self.db.execute(task_query)
        task_notifications = task_result.scalar() or 0

        project_types = [
            NotificationType.PROJECT_CREATED,
            NotificationType.PROJECT_UPDATED,
            NotificationType.PROJECT_MEMBER_ADDED,
            NotificationType.PROJECT_MEMBER_REMOVED,
        ]
        project_query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,  # type: ignore[arg-type]
            Notification.notification_type.in_(project_types),  # type: ignore[attr-defined]
        )
        project_result = await self.db.execute(project_query)
        project_notifications = project_result.scalar() or 0

        sprint_types = [
            NotificationType.SPRINT_STARTED,
            NotificationType.SPRINT_COMPLETED,
            NotificationType.SPRINT_TASK_ASSIGNED,
        ]
        sprint_query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,  # type: ignore[arg-type]
            Notification.notification_type.in_(sprint_types),  # type: ignore[attr-defined]
        )
        sprint_result = await self.db.execute(sprint_query)
        sprint_notifications = sprint_result.scalar() or 0

        system_types = [
            NotificationType.SYSTEM_ANNOUNCEMENT,
            NotificationType.WELCOME,
            NotificationType.DEADLINE_REMINDER,
        ]
        system_query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,  # type: ignore[arg-type]
            Notification.notification_type.in_(system_types),  # type: ignore[attr-defined]
        )
        system_result = await self.db.execute(system_query)
        system_notifications = system_result.scalar() or 0

        return NotificationStats(
            total=total,
            unread=unread,
            recent=recent,
            task_notifications=task_notifications,
            project_notifications=project_notifications,
            sprint_notifications=sprint_notifications,
            system_notifications=system_notifications,
        )

    async def get_notification_preferences(
        self, user_id: UUID
    ) -> NotificationPreferences:
        """Получение настроек уведомлений пользователя."""
        # TODO: В будущем хранить настройки в БД
        return NotificationPreferences(
            task_assigned=True,
            task_completed=True,
            task_overdue=True,
            task_comment_added=True,
            project_created=True,
            project_member_added=True,
            project_updated=True,
            sprint_started=True,
            sprint_completed=True,
            system_announcements=True,
            deadline_reminders=True,
            in_app_notifications=True,
            browser_notifications=False,
            email_notifications=False,
        )

    async def update_notification_preferences(
        self, user_id: UUID, preferences: NotificationPreferences
    ) -> NotificationPreferences:
        """Обновление настроек уведомлений пользователя."""
        # TODO: В будущем сохранять настройки в БД
        return preferences

    async def should_send_notification(
        self, user_id: UUID, notification_type: str
    ) -> bool:
        """Проверка, следует ли отправлять уведомление."""
        preferences = await self.get_notification_preferences(user_id)

        # Маппинг типов уведомлений на поля настроек
        type_mapping = {
            NotificationType.TASK_ASSIGNED: preferences.task_assigned,
            NotificationType.TASK_COMPLETED: preferences.task_completed,
            NotificationType.TASK_OVERDUE: preferences.task_overdue,
            NotificationType.TASK_COMMENT_ADDED: preferences.task_comment_added,
            NotificationType.PROJECT_CREATED: preferences.project_created,
            NotificationType.PROJECT_MEMBER_ADDED: preferences.project_member_added,
            NotificationType.PROJECT_UPDATED: preferences.project_updated,
            NotificationType.SPRINT_STARTED: preferences.sprint_started,
            NotificationType.SPRINT_COMPLETED: preferences.sprint_completed,
            NotificationType.SYSTEM_ANNOUNCEMENT: preferences.system_announcements,
            NotificationType.DEADLINE_REMINDER: preferences.deadline_reminders,
        }

        return type_mapping.get(notification_type, True)

    # Методы для создания специфических уведомлений

    async def notify_task_assigned(
        self, task_id: UUID, assignee_id: UUID, assigner_id: UUID
    ) -> Notification | None:
        """Уведомление о назначении задачи."""
        # Проверяем настройки пользователя
        if not await self.should_send_notification(
            assignee_id, NotificationType.TASK_ASSIGNED
        ):
            return None

        # Получаем информацию о задаче
        task_query = select(Task).where(Task.id == task_id)
        task_result = await self.db.execute(task_query)
        task = task_result.scalar_one_or_none()

        if not task:
            return None

        notification_data = NotificationFactory.task_assigned(
            TaskAssignedNotification(
                task_id=task_id,
                assignee_id=assignee_id,
                assigner_id=assigner_id,
            )
        )

        notification_data.title = f"Новая задача: {task.title}"
        notification_data.message = f"Вам назначена задачу: {task.title}"

        return await self.create_notification(notification_data)

    async def notify_task_completed(
        self, task_id: UUID, completer_id: UUID
    ) -> list[Notification]:
        """Уведомление о завершении задачи."""
        notifications: list[Notification] = []

        # Получаем информацию о задаче
        task_query = select(Task).where(Task.id == task_id)
        task_result = await self.db.execute(task_query)
        task = task_result.scalar_one_or_none()

        if not task:
            return list(notifications)

        # Уведомляем создателя задачи (если это не тот же пользователь)
        if task.creator_id != completer_id:
            if await self.should_send_notification(
                task.creator_id, NotificationType.TASK_COMPLETED
            ):
                notification_data = NotificationFactory.task_completed(
                    TaskCompletedNotification(
                        task_id=task_id,
                        completer_id=completer_id,
                        project_id=task.project_id,
                    )
                )
                notification_data.user_id = task.creator_id
                notification_data.title = f"Задача завершена: {task.title}"
                notification_data.message = f"Задача '{task.title}' была завершена"

                notification = await self.create_notification(notification_data)
                notifications.append(notification)

        return list(notifications)

    async def notify_project_member_added(
        self, project_id: UUID, member_id: UUID, inviter_id: UUID
    ) -> Notification | None:
        """Уведомление о добавлении участника проекта."""
        # Проверяем настройки пользователя
        if not await self.should_send_notification(
            member_id, NotificationType.PROJECT_MEMBER_ADDED
        ):
            return None

        notification_data = NotificationFactory.project_member_added(
            ProjectMemberAddedNotification(
                project_id=project_id,
                member_id=member_id,
                inviter_id=inviter_id,
            )
        )

        return await self.create_notification(notification_data)

    async def notify_sprint_started(
        self, sprint_id: UUID, project_id: UUID
    ) -> list[Notification]:
        """Уведомление о начале спринта."""
        notifications: list[Notification] = []

        # Получаем всех участников проекта
        members_query = select(ProjectMember).where(
            ProjectMember.project_id == project_id,  # type: ignore[arg-type]
            ProjectMember.is_active == True,  # type: ignore[arg-type]
        )
        members_result = await self.db.execute(members_query)
        members = members_result.scalars().all()

        for member in members:
            if await self.should_send_notification(
                member.user_id, NotificationType.SPRINT_STARTED
            ):
                notification_data = NotificationFactory.sprint_started(
                    SprintStartedNotification(
                        sprint_id=sprint_id,
                        project_id=project_id,
                    )
                )
                notification_data.user_id = member.user_id

                notification = await self.create_notification(notification_data)
                notifications.append(notification)

        return list(notifications)

    async def notify_sprint_completed(
        self, sprint_id: UUID, project_id: UUID
    ) -> list[Notification]:
        """Уведомление о завершении спринта."""
        notifications: list[Notification] = []

        # Получаем всех участников проекта
        members_query = select(ProjectMember).where(
            ProjectMember.project_id == project_id,  # type: ignore[arg-type]
            ProjectMember.is_active == True,  # type: ignore[arg-type]
        )
        members_result = await self.db.execute(members_query)
        members = members_result.scalars().all()

        for member in members:
            if await self.should_send_notification(
                member.user_id, NotificationType.SPRINT_COMPLETED
            ):
                notification_data = NotificationFactory.sprint_completed(
                    SprintCompletedNotification(
                        sprint_id=sprint_id,
                        project_id=project_id,
                    )
                )
                notification_data.user_id = member.user_id

                notification = await self.create_notification(notification_data)
                notifications.append(notification)

        return list(notifications)

    async def cleanup_old_notifications(
        self, days_old: int = 30, read_only: bool = True
    ) -> int:
        """Очистка старых уведомлений."""
        cutoff_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_old)

        query = select(Notification).where(Notification.created_at < cutoff_date)  # type: ignore[arg-type]

        if read_only:
            query = query.where(Notification.is_read == True)  # type: ignore[arg-type]

        result = await self.db.execute(query)
        notifications = result.scalars().all()

        for notification in notifications:
            await self.db.delete(notification)

        await self.db.commit()
        return len(notifications)
