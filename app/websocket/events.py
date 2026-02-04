"""
WebSocket события - типы и структура событий
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer


class EventType(str, Enum):
    """Типы WebSocket событий"""

    # Task события
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_MOVED = "task_moved"
    TASK_DELETED = "task_deleted"
    TASK_ASSIGNED = "task_assigned"

    # Comment события
    COMMENT_ADDED = "comment_added"
    COMMENT_UPDATED = "comment_updated"
    COMMENT_DELETED = "comment_deleted"

    # Project события
    PROJECT_UPDATED = "project_updated"
    PROJECT_MEMBER_ADDED = "project_member_added"
    PROJECT_MEMBER_REMOVED = "project_member_removed"

    # Sprint события
    SPRINT_STARTED = "sprint_started"
    SPRINT_COMPLETED = "sprint_completed"
    SPRINT_UPDATED = "sprint_updated"

    # Time tracking события
    TIMER_STARTED = "timer_started"
    TIMER_STOPPED = "timer_stopped"
    TIME_ENTRY_ADDED = "time_entry_added"

    # User события
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"

    # System события
    ERROR = "error"
    NOTIFICATION = "notification"
    PING = "ping"
    PONG = "pong"


class WebSocketEvent(BaseModel):
    """Базовая модель WebSocket события"""

    event_type: EventType = Field(..., description="Тип события")
    data: dict[str, Any] = Field(default_factory=dict, description="Данные события")
    project_id: str | None = Field(None, description="ID проекта (если применимо)")
    user_id: UUID | None = Field(None, description="ID пользователя (если применимо)")
    timestamp: str | None = Field(None, description="Временная метка ISO 8601")

    @field_serializer("user_id")
    def serialize_user_id(self, value: UUID | None) -> str | None:
        return str(value) if value is not None else None


class TaskEvent(BaseModel):
    """Событие связанное с задачей"""

    task_id: UUID = Field(..., description="ID задачи")
    project_id: str = Field(..., description="ID проекта")
    title: str = Field(..., description="Название задачи")
    status: str | None = Field(None, description="Статус задачи")
    assignee_id: UUID | None = Field(None, description="ID исполнителя")
    story_points: int | None = Field(None, description="Story points")

    @field_serializer("task_id", "assignee_id")
    def serialize_uuids(self, value: UUID | None) -> str | None:
        return str(value) if value is not None else None


class CommentEvent(BaseModel):
    """Событие связанное с комментарием"""

    comment_id: UUID = Field(..., description="ID комментария")
    task_id: UUID = Field(..., description="ID задачи")
    project_id: str = Field(..., description="ID проекта")
    content: str = Field(..., description="Содержание комментария")
    author_id: UUID = Field(..., description="ID автора")

    @field_serializer("comment_id", "task_id", "author_id")
    def serialize_uuids(self, value: UUID) -> str:
        return str(value)


class ProjectEvent(BaseModel):
    """Событие связанное с проектом"""

    project_id: str = Field(..., description="ID проекта")
    name: str = Field(..., description="Название проекта")
    description: str | None = Field(None, description="Описание проекта")


class SprintEvent(BaseModel):
    """Событие связанное со спринтом"""

    sprint_id: UUID = Field(..., description="ID спринта")
    project_id: str = Field(..., description="ID проекта")
    name: str = Field(..., description="Название спринта")
    status: str = Field(..., description="Статус спринта")

    @field_serializer("sprint_id")
    def serialize_sprint_id(self, value: UUID) -> str:
        return str(value)


class TimeEvent(BaseModel):
    """Событие связанное с временем"""

    task_id: UUID = Field(..., description="ID задачи")
    project_id: str = Field(..., description="ID проекта")
    duration_seconds: int | None = Field(None, description="Длительность в секундах")
    user_id: UUID = Field(..., description="ID пользователя")

    @field_serializer("task_id", "user_id")
    def serialize_uuids(self, value: UUID) -> str:
        return str(value)


class UserEvent(BaseModel):
    """Событие связанное с пользователем"""

    user_id: UUID = Field(..., description="ID пользователя")
    username: str = Field(..., description="Имя пользователя")
    status: str = Field(..., description="Статус (online/offline)")

    @field_serializer("user_id")
    def serialize_user_id(self, value: UUID) -> str:
        return str(value)


class ErrorEvent(BaseModel):
    """Событие ошибки"""

    error_code: str = Field(..., description="Код ошибки")
    message: str = Field(..., description="Сообщение об ошибке")
    details: dict[str, Any] | None = Field(None, description="Детали ошибки")


class NotificationEvent(BaseModel):
    """Событие уведомления"""

    title: str = Field(..., description="Заголовок уведомления")
    message: str = Field(..., description="Сообщение уведомления")
    notification_type: str = Field(..., description="Тип уведомления")
    action_url: str | None = Field(None, description="URL для действия")


# Фабрики событий
def create_task_event(
    event_type: EventType, task_data: dict[str, Any], user_id: UUID | None = None
) -> WebSocketEvent:
    """
    Создание события задачи

    Args:
        event_type: Тип события
        task_data: Данные задачи
        user_id: ID пользователя

    Returns:
        WebSocketEvent: Событие
    """
    task_event = TaskEvent(**task_data)

    return WebSocketEvent(
        event_type=event_type,
        data=task_event.model_dump(),
        project_id=task_event.project_id,
        user_id=user_id,
        timestamp=datetime.now(UTC).isoformat(),
    )


def create_comment_event(
    event_type: EventType, comment_data: dict[str, Any], user_id: UUID | None = None
) -> WebSocketEvent:
    """
    Создание события комментария

    Args:
        event_type: Тип события
        comment_data: Данные комментария
        user_id: ID пользователя

    Returns:
        WebSocketEvent: Событие
    """
    comment_event = CommentEvent(**comment_data)

    return WebSocketEvent(
        event_type=event_type,
        data=comment_event.model_dump(),
        project_id=comment_event.project_id,
        user_id=user_id,
        timestamp=datetime.now(UTC).isoformat(),
    )


def create_project_event(
    event_type: EventType, project_data: dict[str, Any], user_id: UUID | None = None
) -> WebSocketEvent:
    """
    Создание события проекта

    Args:
        event_type: Тип события
        project_data: Данные проекта
        user_id: ID пользователя

    Returns:
        WebSocketEvent: Событие
    """
    project_event = ProjectEvent(**project_data)

    return WebSocketEvent(
        event_type=event_type,
        data=project_event.model_dump(),
        project_id=project_event.project_id,
        user_id=user_id,
        timestamp=datetime.now(UTC).isoformat(),
    )


def create_sprint_event(
    event_type: EventType, sprint_data: dict[str, Any], user_id: UUID | None = None
) -> WebSocketEvent:
    """
    Создание события спринта

    Args:
        event_type: Тип события
        sprint_data: Данные спринта
        user_id: ID пользователя

    Returns:
        WebSocketEvent: Событие
    """
    sprint_event = SprintEvent(**sprint_data)

    return WebSocketEvent(
        event_type=event_type,
        data=sprint_event.model_dump(),
        project_id=sprint_event.project_id,
        user_id=user_id,
        timestamp=datetime.now(UTC).isoformat(),
    )


def create_time_event(
    event_type: EventType, time_data: dict[str, Any], user_id: UUID | None = None
) -> WebSocketEvent:
    """
    Создание события времени

    Args:
        event_type: Тип события
        time_data: Данные времени
        user_id: ID пользователя

    Returns:
        WebSocketEvent: Событие
    """
    time_event = TimeEvent(**time_data)

    return WebSocketEvent(
        event_type=event_type,
        data=time_event.model_dump(),
        project_id=time_event.project_id,
        user_id=user_id or time_event.user_id,
        timestamp=datetime.now(UTC).isoformat(),
    )


def create_user_event(
    event_type: EventType, user_data: dict[str, Any]
) -> WebSocketEvent:
    """
    Создание события пользователя

    Args:
        event_type: Тип события
        user_data: Данные пользователя

    Returns:
        WebSocketEvent: Событие
    """
    user_event = UserEvent(**user_data)

    return WebSocketEvent(
        event_type=event_type,
        data=user_event.model_dump(),
        project_id=None,
        user_id=user_event.user_id,
        timestamp=datetime.now(UTC).isoformat(),
    )


def create_error_event(
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
    project_id: str | None = None,
    user_id: UUID | None = None,
) -> WebSocketEvent:
    """
    Создание события ошибки

    Args:
        error_code: Код ошибки
        message: Сообщение об ошибке
        details: Детали ошибки
        project_id: ID проекта
        user_id: ID пользователя

    Returns:
        WebSocketEvent: Событие
    """
    error_event = ErrorEvent(error_code=error_code, message=message, details=details)

    return WebSocketEvent(
        event_type=EventType.ERROR,
        data=error_event.model_dump(),
        project_id=project_id,
        user_id=user_id,
        timestamp=datetime.now(UTC).isoformat(),
    )


def create_notification_event(
    title: str,
    message: str,
    notification_type: str,
    action_url: str | None = None,
    project_id: str | None = None,
    user_id: UUID | None = None,
) -> WebSocketEvent:
    """
    Создание события уведомления

    Args:
        title: Заголовок уведомления
        message: Сообщение уведомления
        notification_type: Тип уведомления
        action_url: URL для действия
        project_id: ID проекта
        user_id: ID пользователя

    Returns:
        WebSocketEvent: Событие
    """
    notification_event = NotificationEvent(
        title=title,
        message=message,
        notification_type=notification_type,
        action_url=action_url,
    )

    return WebSocketEvent(
        event_type=EventType.NOTIFICATION,
        data=notification_event.model_dump(),
        project_id=project_id,
        user_id=user_id,
        timestamp=datetime.now(UTC).isoformat(),
    )
