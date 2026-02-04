"""API эндпоинты для управления уведомлениями."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationBulkAction,
    NotificationList,
    NotificationMarkRead,
    NotificationPreferences,
    NotificationRead,
    NotificationStats,
)
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("/", response_model=NotificationList)
async def get_notifications(
    unread_only: bool = Query(False, description="Только непрочитанные"),
    notification_type: str = Query(None, description="Тип уведомления"),
    limit: int = Query(50, ge=1, le=100, description="Лимит записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationList:
    """Получить список уведомлений текущего пользователя."""
    service = NotificationService(db)

    notifications = await service.get_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
        notification_type=notification_type,
    )

    # Получаем общее количество для пагинации
    total = (
        len(notifications)
        if offset == 0
        else await service.get_unread_count(current_user.id) if unread_only else 100
    )  # TODO: реализовать подсчет

    return NotificationList(
        notifications=[NotificationRead.model_validate(n) for n in notifications],
        total=total,
        page=offset // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit,
    )


@router.get("/stats", response_model=NotificationStats)
async def get_notification_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationStats:
    """Получить статистику уведомлений пользователя."""
    service = NotificationService(db)
    return await service.get_notification_stats(current_user.id)


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Получить количество непрочитанных уведомлений."""
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.get("/{notification_id}", response_model=NotificationRead)
async def get_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationRead:
    """Получить уведомление по ID."""
    service = NotificationService(db)
    notification = await service.get_notification_by_id(
        notification_id, current_user.id
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Уведомление не найдено"
        )

    return NotificationRead.model_validate(notification)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: UUID,
    mark_data: NotificationMarkRead,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationRead:
    """Отметить уведомление как прочитанное/непрочитанное."""
    service = NotificationService(db)

    if mark_data.is_read:
        notification = await service.mark_notification_read(
            notification_id, current_user.id
        )
    else:
        notifications = await service.mark_notifications_unread(
            [notification_id], current_user.id
        )
        notification = notifications[0] if notifications else None

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Уведомление не найдено"
        )

    return NotificationRead.model_validate(notification)


@router.patch("/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Отметить все уведомления как прочитанные."""
    service = NotificationService(db)
    count = await service.mark_all_notifications_read(current_user.id)
    return {"marked_count": count}


@router.post("/bulk-action")
async def bulk_notification_action(
    action_data: NotificationBulkAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Массовое действие с уведомлениями."""
    service = NotificationService(db)

    if action_data.action == "mark_read":
        count = 0
        for notification_id in action_data.notification_ids:
            notification = await service.mark_notification_read(
                notification_id, current_user.id
            )
            if notification:
                count += 1
        return {"processed_count": count}

    elif action_data.action == "mark_unread":
        notifications = await service.mark_notifications_unread(
            action_data.notification_ids, current_user.id
        )
        return {"processed_count": len(notifications)}

    elif action_data.action == "delete":
        count = await service.delete_notifications_bulk(
            action_data.notification_ids, current_user.id
        )
        return {"processed_count": count}

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Неподдерживаемое действие"
        )


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Удалить уведомление."""
    service = NotificationService(db)
    success = await service.delete_notification(notification_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Уведомление не найдено"
        )

    return {"message": "Уведомление удалено"}


@router.get("/preferences/", response_model=NotificationPreferences)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferences:
    """Получить настройки уведомлений пользователя."""
    service = NotificationService(db)
    return await service.get_notification_preferences(current_user.id)


@router.put("/preferences/", response_model=NotificationPreferences)
async def update_notification_preferences(
    preferences: NotificationPreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferences:
    """Обновить настройки уведомлений пользователя."""
    service = NotificationService(db)
    return await service.update_notification_preferences(current_user.id, preferences)
