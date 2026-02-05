"""
API эндпоинты для управления подписками и пакетами
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_active_user
from app.core.database import get_db
from app.models.subscription import AddOnType
from app.models.user import User
from app.schemas.subscription import (
    AddOnPackageResponse,
    SubscriptionResponse,
    UpgradeSuggestionResponse,
    UserAddOnResponse,
)
from app.services.addon_service import AddOnService
from app.services.subscription_service import SubscriptionService

router = APIRouter()


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Получить текущую подписку пользователя"""
    subscription_service = SubscriptionService(db)

    subscription = await subscription_service.get_user_subscription(current_user.id)
    if not subscription:
        # Создаем подписку Free по умолчанию
        subscription = await subscription_service.create_default_subscription(
            current_user.id
        )

    return SubscriptionResponse(
        id=subscription.id,
        plan=subscription.plan,
        storage_limit=subscription.storage_limit,
        file_count_limit=subscription.file_count_limit,
        max_file_size=subscription.max_file_size,
        allowed_file_types=subscription.allowed_file_types,
        projects_limit=subscription.projects_limit,
        users_limit=subscription.users_limit,
        expires_at=subscription.expires_at,
        is_active=subscription.is_active,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
    )


@router.get("/limits")
async def get_user_limits(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Получить актуальные лимиты пользователя с учетом пакетов"""
    subscription_service = SubscriptionService(db)

    limits = await subscription_service.get_user_limits(current_user.id)
    usage = {
        "storage_used": await subscription_service.get_storage_usage(current_user.id),
        "files_count": await subscription_service.get_files_count(current_user.id),
    }

    return {
        "limits": limits,
        "usage": usage,
        "storage_usage_percent": (
            (usage["storage_used"] / limits["storage_limit"]) * 100
            if limits["storage_limit"] > 0
            else 0
        ),
        "files_usage_percent": (
            (usage["files_count"] / limits["file_count_limit"]) * 100
            if limits["file_count_limit"] > 0
            else 0
        ),
    }


@router.get("/upgrade-suggestion", response_model=UpgradeSuggestionResponse)
async def get_upgrade_suggestion(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UpgradeSuggestionResponse:
    """Получить рекомендации по апгрейду"""
    subscription_service = SubscriptionService(db)

    suggestions = await subscription_service.get_upgrade_suggestion(current_user)

    return UpgradeSuggestionResponse(
        current_plan=suggestions["current_plan"],
        current_usage=suggestions["current_usage"],
        suggestions=suggestions["suggestions"],
    )


@router.get("/packages")
async def get_available_packages(
    package_type: AddOnType | None = Query(None, description="Фильтр по типу пакета"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[AddOnPackageResponse]:
    """Получить доступные пакеты"""
    addon_service = AddOnService(db)

    packages = await addon_service.get_available_packages(package_type)

    return [
        AddOnPackageResponse(
            id=package.id,
            name=package.name,
            type=package.type,
            price=package.price,
            billing_cycle=package.billing_cycle,
            features=package.features,
            description=package.description,
            is_active=package.is_active,
        )
        for package in packages
    ]


@router.get("/packages/my")
async def get_user_packages(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserAddOnResponse]:
    """Получить пакеты пользователя"""
    addon_service = AddOnService(db)

    user_addons = await addon_service.get_user_packages(current_user.id)

    return [
        UserAddOnResponse(
            id=user_addon.id,
            package_id=user_addon.package_id,
            package_name=user_addon.package.name,
            package_type=user_addon.package.type,
            price=user_addon.package.price,
            billing_cycle=user_addon.package.billing_cycle,
            purchased_at=user_addon.purchased_at,
            expires_at=user_addon.expires_at,
            is_active=user_addon.is_active,
            auto_renew=user_addon.auto_renew,
            usage_data=user_addon.usage_data,
        )
        for user_addon in user_addons
    ]


@router.post("/packages/{package_id}/purchase")
async def purchase_package(
    package_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserAddOnResponse:
    """Купить пакет"""
    addon_service = AddOnService(db)

    try:
        user_addon = await addon_service.purchase_package(current_user.id, package_id)

        return UserAddOnResponse(
            id=user_addon.id,
            package_id=user_addon.package_id,
            package_name=user_addon.package.name,
            package_type=user_addon.package.type,
            price=user_addon.package.price,
            billing_cycle=user_addon.package.billing_cycle,
            purchased_at=user_addon.purchased_at,
            expires_at=user_addon.expires_at,
            is_active=user_addon.is_active,
            auto_renew=user_addon.auto_renew,
            usage_data=user_addon.usage_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to purchase package: {str(e)}"
        ) from e


@router.post("/packages/{package_id}/activate")
async def activate_package(
    package_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Активировать пакет (например, после оплаты)"""
    addon_service = AddOnService(db)

    success = await addon_service.activate_package(current_user.id, package_id)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to activate package")

    return {"message": "Package activated successfully"}


@router.post("/packages/{package_id}/deactivate")
async def deactivate_package(
    package_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Деактивировать пакет"""
    addon_service = AddOnService(db)

    success = await addon_service.deactivate_package(current_user.id, package_id)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to deactivate package")

    return {"message": "Package deactivated successfully"}


@router.post("/packages/{package_id}/renew")
async def renew_package(
    package_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Продлить пакет"""
    addon_service = AddOnService(db)

    success = await addon_service.renew_package(current_user.id, package_id)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to renew package")

    return {"message": "Package renewed successfully"}


@router.get("/usage")
async def get_usage_report(
    days: int = Query(30, ge=1, le=365, description="Период в днях"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Получить отчет об использовании"""
    subscription_service = SubscriptionService(db)

    report = await subscription_service.get_usage_report(current_user.id, days)

    return report


@router.post("/initialize-packages")
async def initialize_default_packages(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Инициализировать пакеты по умолчанию (только для админов)"""
    # TODO: проверка прав администратора

    addon_service = AddOnService(db)

    try:
        await addon_service.initialize_default_packages()
        return {"message": "Default packages initialized successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize packages: {str(e)}"
        ) from e
