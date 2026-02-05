"""
Сервис для управления пакетами дополнений
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import FileType
from app.models.subscription import AddOnPackage, AddOnType, UserAddOn


class AddOnService:
    """Сервис для управления пакетами дополнений"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_available_packages(
        self, package_type: AddOnType | None = None
    ) -> list[AddOnPackage]:
        """Получить доступные пакеты"""
        stmt = select(AddOnPackage).where(AddOnPackage.is_active == True)

        if package_type:
            stmt = stmt.where(AddOnPackage.type == package_type)

        stmt = stmt.order_by(AddOnPackage.sort_order, AddOnPackage.price)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_storage_packages(self) -> list[AddOnPackage]:
        """Получить пакеты хранилища"""
        return await self.get_available_packages(AddOnType.STORAGE)

    async def get_video_packages(self) -> list[AddOnPackage]:
        """Получить пакеты видео/аудио"""
        return await self.get_available_packages(AddOnType.VIDEO_AUDIO)

    async def get_user_packages(self, user_id: uuid.UUID) -> list[UserAddOn]:
        """Получить пакеты пользователя"""
        stmt = select(UserAddOn).where(
            UserAddOn.user_id == user_id, UserAddOn.is_active == True
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def purchase_package(
        self, user_id: uuid.UUID, package_id: uuid.UUID
    ) -> UserAddOn:
        """Купить пакет"""
        # Проверяем существование пакета
        package_stmt = select(AddOnPackage).where(
            AddOnPackage.id == package_id, AddOnPackage.is_active == True
        )
        package_result = await self.db.execute(package_stmt)
        package = package_result.scalar_one_or_none()

        if not package:
            raise HTTPException(status_code=404, detail="Пакет не найден")

        # Проверяем, нет ли уже активного пакета этого типа
        existing_stmt = select(UserAddOn).where(
            UserAddOn.user_id == user_id,
            UserAddOn.package_id == package_id,
            UserAddOn.is_active == True,
        )
        existing_result = await self.db.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        if existing:
            raise HTTPException(status_code=400, detail="У вас уже есть этот пакет")

        # Создаем запись о покупке
        expires_at = None
        if package.billing_cycle == "monthly":
            expires_at = datetime.now(UTC) + timedelta(days=30)
        elif package.billing_cycle == "yearly":
            expires_at = datetime.now(UTC) + timedelta(days=365)

        user_addon = UserAddOn(
            user_id=user_id,
            package_id=package_id,
            expires_at=expires_at,
            auto_renew=False,  # TODO: реализовать автопродление
            usage_data=json.dumps(
                {
                    "purchased_at": datetime.now(UTC).isoformat(),
                    "usage_count": 0,
                }
            ),
        )

        self.db.add(user_addon)
        await self.db.commit()
        await self.db.refresh(user_addon)

        return user_addon

    async def activate_package(self, user_id: uuid.UUID, package_id: uuid.UUID) -> bool:
        """Активировать пакет (например, после оплаты)"""
        stmt = select(UserAddOn).where(
            UserAddOn.user_id == user_id, UserAddOn.package_id == package_id
        )
        result = await self.db.execute(stmt)
        user_addon = result.scalar_one_or_none()

        if not user_addon:
            return False

        user_addon.is_active = True
        user_addon.expires_at = datetime.now(UTC) + timedelta(
            days=30
        )  # TODO: из настроек пакета
        await self.db.commit()

        return True

    async def deactivate_package(
        self, user_id: uuid.UUID, package_id: uuid.UUID
    ) -> bool:
        """Деактивировать пакет"""
        stmt = select(UserAddOn).where(
            UserAddOn.user_id == user_id, UserAddOn.package_id == package_id
        )
        result = await self.db.execute(stmt)
        user_addon = result.scalar_one_or_none()

        if not user_addon:
            return False

        user_addon.is_active = False
        await self.db.commit()

        return True

    async def renew_package(self, user_id: uuid.UUID, package_id: uuid.UUID) -> bool:
        """Продлить пакет"""
        stmt = select(UserAddOn).where(
            UserAddOn.user_id == user_id, UserAddOn.package_id == package_id
        )
        result = await self.db.execute(stmt)
        user_addon = result.scalar_one_or_none()

        if not user_addon:
            return False

        # Продлеваем на тот же период
        if user_addon.expires_at:
            extension = timedelta(days=30)  # TODO: из настроек пакета
            user_addon.expires_at += extension
        else:
            user_addon.expires_at = datetime.now(UTC) + timedelta(days=30)

        await self.db.commit()

        return True

    async def get_package_usage(
        self, user_id: uuid.UUID, package_id: uuid.UUID
    ) -> dict[str, Any]:
        """Получить статистику использования пакета"""
        stmt = select(UserAddOn).where(
            UserAddOn.user_id == user_id, UserAddOn.package_id == package_id
        )
        result = await self.db.execute(stmt)
        user_addon = result.scalar_one_or_none()

        if not user_addon:
            return {}

        usage_data = json.loads(user_addon.usage_data or "{}")

        return {
            "package_id": package_id,
            "purchased_at": user_addon.purchased_at,
            "expires_at": user_addon.expires_at,
            "is_active": user_addon.is_active,
            "usage_data": usage_data,
        }

    async def initialize_default_packages(self) -> None:
        """Инициализировать пакеты по умолчанию"""
        default_packages = [
            # Пакеты хранилища
            {
                "name": "Дополнительное хранилище 1 ГБ",
                "type": AddOnType.STORAGE,
                "price": 200,  # $2.00
                "billing_cycle": "monthly",
                "features": json.dumps(
                    {
                        "storage_bytes": 1024 * 1024 * 1024,  # 1 ГБ
                        "description": "1 ГБ дополнительного хранилища",
                    }
                ),
                "description": "Добавьте 1 ГБ к вашему лимиту хранилища",
                "sort_order": 1,
            },
            {
                "name": "Дополнительное хранилище 5 ГБ",
                "type": AddOnType.STORAGE,
                "price": 800,  # $8.00
                "billing_cycle": "monthly",
                "features": json.dumps(
                    {
                        "storage_bytes": 5 * 1024 * 1024 * 1024,  # 5 ГБ
                        "description": "5 ГБ дополнительного хранилища (скидка 20%)",
                    }
                ),
                "description": "Добавьте 5 ГБ к вашему лимиту хранилища со скидкой 20%",
                "sort_order": 2,
            },
            {
                "name": "Дополнительное хранилище 10 ГБ",
                "type": AddOnType.STORAGE,
                "price": 1500,  # $15.00
                "billing_cycle": "monthly",
                "features": json.dumps(
                    {
                        "storage_bytes": 10 * 1024 * 1024 * 1024,  # 10 ГБ
                        "description": "10 ГБ дополнительного хранилища (скидка 25%)",
                    }
                ),
                "description": "Добавьте 10 ГБ к вашему лимиту хранилища со скидкой 25%",
                "sort_order": 3,
            },
            # Пакеты видео/аудио
            {
                "name": "Видео и аудио до 100 МБ",
                "type": AddOnType.VIDEO_AUDIO,
                "price": 500,  # $5.00
                "billing_cycle": "monthly",
                "features": json.dumps(
                    {
                        "max_video_size_bytes": 100 * 1024 * 1024,  # 100 МБ
                        "allowed_types": [FileType.VIDEO.value, FileType.AUDIO.value],
                        "description": "Загрузка видео и аудио до 100 МБ",
                    }
                ),
                "description": "Разблокируйте загрузку видео и аудио файлов до 100 МБ",
                "sort_order": 10,
            },
            {
                "name": "Видео и аудио до 500 МБ",
                "type": AddOnType.VIDEO_AUDIO,
                "price": 1500,  # $15.00
                "billing_cycle": "monthly",
                "features": json.dumps(
                    {
                        "max_video_size_bytes": 500 * 1024 * 1024,  # 500 МБ
                        "allowed_types": [FileType.VIDEO.value, FileType.AUDIO.value],
                        "description": "Загрузка видео и аудио до 500 МБ",
                    }
                ),
                "description": "Разблокируйте загрузку видео и аудио файлов до 500 МБ",
                "sort_order": 11,
            },
            {
                "name": "Видео и аудио до 1 ГБ",
                "type": AddOnType.VIDEO_AUDIO,
                "price": 2500,  # $25.00
                "billing_cycle": "monthly",
                "features": json.dumps(
                    {
                        "max_video_size_bytes": 1024 * 1024 * 1024,  # 1 ГБ
                        "allowed_types": [FileType.VIDEO.value, FileType.AUDIO.value],
                        "description": "Загрузка видео и аудио до 1 ГБ",
                    }
                ),
                "description": "Разблокируйте загрузку видео и аудио файлов до 1 ГБ",
                "sort_order": 12,
            },
            # Пакеты пользователей
            {
                "name": "+5 участников команды",
                "type": AddOnType.USERS,
                "price": 1000,  # $10.00
                "billing_cycle": "monthly",
                "features": json.dumps(
                    {
                        "users_count": 5,
                        "description": "Добавьте 5 участников к вашей команде",
                    }
                ),
                "description": "Расширьте команду на 5 дополнительных участников",
                "sort_order": 20,
            },
            {
                "name": "+15 участников команды",
                "type": AddOnType.USERS,
                "price": 2500,  # $25.00
                "billing_cycle": "monthly",
                "features": json.dumps(
                    {
                        "users_count": 15,
                        "description": "Добавьте 15 участников к вашей команде (скидка 17%)",
                    }
                ),
                "description": "Расширьте команду на 15 дополнительных участников со скидкой 17%",
                "sort_order": 21,
            },
            # Пакеты проектов
            {
                "name": "+10 проектов",
                "type": AddOnType.PROJECTS,
                "price": 500,  # $5.00
                "billing_cycle": "monthly",
                "features": json.dumps(
                    {
                        "projects_count": 10,
                        "unlimited": False,
                        "description": "Добавьте 10 проектов",
                    }
                ),
                "description": "Создавайте до 10 дополнительных проектов",
                "sort_order": 30,
            },
            {
                "name": "Безлимит проектов",
                "type": AddOnType.PROJECTS,
                "price": 1500,  # $15.00
                "billing_cycle": "monthly",
                "features": json.dumps(
                    {
                        "unlimited": True,
                        "description": "Безлимитное количество проектов",
                    }
                ),
                "description": "Создавайте неограниченное количество проектов",
                "sort_order": 31,
            },
        ]

        for package_data in default_packages:
            # Проверяем, существует ли уже пакет
            existing_stmt = select(AddOnPackage).where(
                AddOnPackage.name == package_data["name"]
            )
            existing_result = await self.db.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()

            if not existing:
                package = AddOnPackage(**package_data)
                self.db.add(package)

        await self.db.commit()
