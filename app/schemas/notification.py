"""Pydantic схемы для уведомлений."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.notification import NotificationType


class NotificationBase(BaseModel):
    """Базовая схема уведомления."""

    title: str = Field(
        ..., min_length=1, max_length=255, description="Заголовок уведомления"
    )
    message: str = Field(..., min_length=1, description="Сообщение уведомления")
    notification_type: str = Field(..., description="Тип уведомления")
    action_url: str | None = Field(None, max_length=500, description="URL для перехода")
    metadata_json: str | None = Field(
        None, description="Дополнительные метаданные в JSON"
    )

    @field_validator("notification_type")
    @classmethod
    def validate_notification_type(cls, v: str) -> str:
        """Валидация типа уведомления."""
        if not NotificationType.is_valid_type(v):
            allowed_types = ", ".join(NotificationType.get_all_types())
            raise ValueError(f"Тип уведомления должен быть одним из: {allowed_types}")
        return v


class NotificationCreate(NotificationBase):
    """Схема для создания уведомления."""

    user_id: UUID = Field(..., description="ID пользователя")
    project_id: UUID | None = Field(None, description="ID проекта")
    task_id: UUID | None = Field(None, description="ID задачи")
    sprint_id: UUID | None = Field(None, description="ID спринта")


class NotificationUpdate(BaseModel):
    """Схема для обновления уведомления."""

    title: str | None = Field(None, min_length=1, max_length=255)
    message: str | None = Field(None, min_length=1)
    notification_type: str | None = Field(None)
    action_url: str | None = Field(None, max_length=500)
    metadata_json: str | None = Field(None)

    @field_validator("notification_type")
    @classmethod
    def validate_notification_type(cls, v: str | None) -> str | None:
        """Валидация типа уведомления при обновлении."""
        if v is not None and not NotificationType.is_valid_type(v):
            allowed_types = ", ".join(NotificationType.get_all_types())
            raise ValueError(f"Тип уведомления должен быть одним из: {allowed_types}")
        return v


class NotificationRead(NotificationBase):
    """Схема для чтения уведомления."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="ID уведомления")
    user_id: UUID = Field(..., description="ID пользователя")
    project_id: UUID | None = Field(None, description="ID проекта")
    task_id: UUID | None = Field(None, description="ID задачи")
    sprint_id: UUID | None = Field(None, description="ID спринта")
    is_read: bool = Field(..., description="Прочитано ли уведомление")
    read_at: datetime | None = Field(None, description="Время прочтения")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")
    is_recent: bool = Field(..., description="Является ли уведомление недавним")


class NotificationMarkRead(BaseModel):
    """Схема для отметки уведомления как прочитанного."""

    is_read: bool = Field(True, description="Статус прочтения")


class NotificationBulkAction(BaseModel):
    """Схема для массовых действий с уведомлениями."""

    notification_ids: list[UUID] = Field(
        ..., min_length=1, description="ID уведомлений"
    )
    action: str = Field(..., description="Действие (mark_read, mark_unread, delete)")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Валидация действия."""
        allowed_actions = ["mark_read", "mark_unread", "delete"]
        if v not in allowed_actions:
            raise ValueError(
                f'Действие должно быть одним из: {", ".join(allowed_actions)}'
            )
        return v


class NotificationStats(BaseModel):
    """Статистика уведомлений пользователя."""

    total: int = Field(..., description="Всего уведомлений")
    unread: int = Field(..., description="Непрочитанных")
    recent: int = Field(..., description="Недавних (менее 24 часов)")

    # По типам
    task_notifications: int = Field(..., description="Уведомлений о задачах")
    project_notifications: int = Field(..., description="Уведомлений о проектах")
    sprint_notifications: int = Field(..., description="Уведомлений о спринтах")
    system_notifications: int = Field(..., description="Системных уведомлений")


class NotificationList(BaseModel):
    """Список уведомлений с метаданными."""

    notifications: list[NotificationRead] = Field(..., description="Список уведомлений")
    total: int = Field(..., description="Всего уведомлений")
    page: int = Field(..., description="Текущая страница")
    size: int = Field(..., description="Размер страницы")
    pages: int = Field(..., description="Всего страниц")


class NotificationPreferences(BaseModel):
    """Настройки уведомлений пользователя."""

    # Уведомления о задачах
    task_assigned: bool = Field(True, description="Уведомления о назначении задач")
    task_completed: bool = Field(True, description="Уведомления о завершении задач")
    task_overdue: bool = Field(True, description="Уведомления о просроченных задачах")
    task_comment_added: bool = Field(
        True, description="Уведомления о комментариях к задачам"
    )

    # Уведомления о проектах
    project_created: bool = Field(True, description="Уведомления о создании проектов")
    project_member_added: bool = Field(
        True, description="Уведомления о добавлении участников"
    )
    project_updated: bool = Field(
        True, description="Уведомления об обновлении проектов"
    )

    # Уведомления о спринтах
    sprint_started: bool = Field(True, description="Уведомления о начале спринтов")
    sprint_completed: bool = Field(
        True, description="Уведомления о завершении спринтов"
    )

    # Системные уведомления
    system_announcements: bool = Field(True, description="Системные объявления")
    deadline_reminders: bool = Field(True, description="Напоминания о дедлайнах")

    # Настройки доставки
    in_app_notifications: bool = Field(True, description="In-app уведомления")
    browser_notifications: bool = Field(False, description="Browser уведомления")
    email_notifications: bool = Field(False, description="Email уведомления")


# Вспомогательные схемы для создания уведомлений
class TaskAssignedNotification(BaseModel):
    """Данные для уведомления о назначении задачи."""

    task_id: UUID = Field(..., description="ID задачи")
    assignee_id: UUID = Field(..., description="ID исполнителя")
    assigner_id: UUID = Field(..., description="ID назначившего")


class TaskCompletedNotification(BaseModel):
    """Данные для уведомления о завершении задачи."""

    task_id: UUID = Field(..., description="ID задачи")
    completer_id: UUID = Field(..., description="ID завершившего")
    project_id: UUID | None = Field(None, description="ID проекта")


class ProjectMemberAddedNotification(BaseModel):
    """Данные для уведомления о добавлении участника проекта."""

    project_id: UUID = Field(..., description="ID проекта")
    member_id: UUID = Field(..., description="ID нового участника")
    inviter_id: UUID = Field(..., description="ID пригласившего")


class SprintStartedNotification(BaseModel):
    """Данные для уведомления о начале спринта."""

    sprint_id: UUID = Field(..., description="ID спринта")
    project_id: UUID = Field(..., description="ID проекта")


class SprintCompletedNotification(BaseModel):
    """Данные для уведомления о завершении спринта."""

    sprint_id: UUID = Field(..., description="ID спринта")
    project_id: UUID = Field(..., description="ID проекта")


# Фабрики для создания уведомлений
class NotificationFactory:
    """Фабрика для создания уведомлений."""

    @staticmethod
    def task_assigned(data: TaskAssignedNotification) -> NotificationCreate:
        """Создать уведомление о назначении задачи."""
        return NotificationCreate(
            user_id=data.assignee_id,
            title="Новая задача",
            message=f"Вам назначена новую задачу #{data.task_id}",
            notification_type=NotificationType.TASK_ASSIGNED,
            task_id=data.task_id,
            project_id=None,
            sprint_id=None,
            action_url=f"/tasks/{data.task_id}",
            metadata_json=f'{{"assigner_id": "{data.assigner_id}"}}',
        )

    @staticmethod
    def task_completed(data: TaskCompletedNotification) -> NotificationCreate:
        """Создать уведомление о завершении задачи."""
        return NotificationCreate(
            user_id=data.completer_id,
            title="Задача завершена",
            message=f"Задача #{data.task_id} успешно завершена",
            notification_type=NotificationType.TASK_COMPLETED,
            task_id=data.task_id,
            project_id=data.project_id,
            sprint_id=None,
            action_url=f"/tasks/{data.task_id}",
            metadata_json=None,
        )

    @staticmethod
    def project_member_added(
        data: ProjectMemberAddedNotification,
    ) -> NotificationCreate:
        """Создать уведомление о добавлении участника проекта."""
        return NotificationCreate(
            user_id=data.member_id,
            title="Добавление в проект",
            message=f"Вас добавили в проект #{data.project_id}",
            notification_type=NotificationType.PROJECT_MEMBER_ADDED,
            project_id=data.project_id,
            task_id=None,
            sprint_id=None,
            action_url=f"/projects/{data.project_id}",
            metadata_json=f'{{"inviter_id": "{data.inviter_id}"}}',
        )

    @staticmethod
    def sprint_started(data: SprintStartedNotification) -> NotificationCreate:
        """Создать уведомление о начале спринта."""
        return NotificationCreate(
            user_id=data.project_id,  # Будет заменено на ID участников
            title="Начало спринта",
            message=f"Спринт #{data.sprint_id} начался",
            notification_type=NotificationType.SPRINT_STARTED,
            sprint_id=data.sprint_id,
            project_id=data.project_id,
            task_id=None,
            action_url=f"/sprints/{data.sprint_id}",
            metadata_json=None,
        )

    @staticmethod
    def sprint_completed(data: SprintCompletedNotification) -> NotificationCreate:
        """Создать уведомление о завершении спринта."""
        return NotificationCreate(
            user_id=data.project_id,  # Будет заменено на ID участников
            title="Завершение спринта",
            message=f"Спринт #{data.sprint_id} завершен",
            notification_type=NotificationType.SPRINT_COMPLETED,
            sprint_id=data.sprint_id,
            project_id=data.project_id,
            task_id=None,
            action_url=f"/sprints/{data.sprint_id}",
            metadata_json=None,
        )
