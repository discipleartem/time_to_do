"""
Сервис для работы с подписками и монетизацией
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.file import File, FileType
from app.models.subscription import (
    AddOnType,
    SubscriptionPlan,
    UsageTracker,
    UserAddOn,
    UserSubscription,
)
from app.models.user import User


class SubscriptionService:
    """Сервис для управления подписками и лимитами"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()

    async def get_user_subscription(
        self, user_id: uuid.UUID
    ) -> UserSubscription | None:
        """Получить подписку пользователя"""
        stmt = select(UserSubscription).where(
            UserSubscription.user_id == user_id, UserSubscription.is_active == True
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_limits(self, user_id: uuid.UUID) -> dict[str, Any]:
        """Получить лимиты пользователя с учетом пакетов"""
        subscription = await self.get_user_subscription(user_id)
        addons = await self.get_user_addons(user_id)

        # Базовые лимиты из подписки
        if subscription:
            base_limits = {
                "storage_limit": subscription.storage_limit,
                "file_count_limit": subscription.file_count_limit,
                "max_file_size": subscription.max_file_size,
                "allowed_file_types": json.loads(subscription.allowed_file_types),
                "projects_limit": subscription.projects_limit,
                "users_limit": subscription.users_limit,
            }
        else:
            # Free план по умолчанию
            base_limits = self._get_free_plan_limits()

        # Добавляем лимиты из пакетов
        for addon in addons:
            addon_features = json.loads(addon.package.features)
            if addon.package.type == AddOnType.STORAGE:
                base_limits["storage_limit"] += addon_features.get("storage_bytes", 0)
            elif addon.package.type == AddOnType.USERS:
                base_limits["users_limit"] += addon_features.get("users_count", 0)
            elif addon.package.type == AddOnType.PROJECTS:
                if addon_features.get("unlimited", False):
                    base_limits["projects_limit"] = -1  # Безлимит
                else:
                    base_limits["projects_limit"] += addon_features.get(
                        "projects_count", 0
                    )
            elif addon.package.type == AddOnType.VIDEO_AUDIO:
                # Разрешаем видео/аудио
                allowed_types = set(base_limits["allowed_file_types"])
                allowed_types.update([FileType.VIDEO.value, FileType.AUDIO.value])
                base_limits["allowed_file_types"] = list(allowed_types)

                # Увеличиваем максимальный размер для видео
                max_video_size = addon_features.get("max_video_size_bytes", 0)
                if max_video_size > base_limits["max_file_size"]:
                    base_limits["max_file_size"] = max_video_size

        return base_limits

    async def get_user_addons(self, user_id: uuid.UUID) -> list[UserAddOn]:
        """Получить активные пакеты пользователя"""
        from sqlalchemy import and_, or_

        current_time = datetime.now()
        stmt = select(UserAddOn).where(
            and_(
                UserAddOn.user_id == user_id,
                UserAddOn.is_active == True,
                or_(
                    UserAddOn.expires_at.is_(None), UserAddOn.expires_at > current_time
                ),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def can_upload_file(
        self, user: User, file_size: int, file_type: FileType
    ) -> tuple[bool, str | None]:
        """Проверить можно ли загрузить файл"""
        limits = await self.get_user_limits(user.id)

        # Проверка типа файла
        if file_type.value not in limits["allowed_file_types"]:
            return False, f"Тип файла {file_type.value} недоступен в вашем тарифе"

        # Проверка размера файла
        if file_size > limits["max_file_size"]:
            return (
                False,
                f"Размер файла превышает лимит ({limits['max_file_size']} байт)",
            )

        # Проверка общего хранилища
        current_usage = await self.get_storage_usage(user.id)
        if current_usage + file_size > limits["storage_limit"]:
            return False, "Недостаточно места в хранилище"

        # Проверка количества файлов
        current_files = await self.get_files_count(user.id)
        if current_files >= limits["file_count_limit"]:
            return False, "Достигнут лимит количества файлов"

        return True, None

    async def get_storage_usage(self, user_id: uuid.UUID) -> int:
        """Получить текущее использование хранилища"""
        stmt = select(File).where(File.uploader_id == user_id, File.is_deleted == False)
        result = await self.db.execute(stmt)
        files = result.scalars().all()
        return sum(f.file_size for f in files)

    async def get_files_count(self, user_id: uuid.UUID) -> int:
        """Получить количество файлов пользователя"""
        stmt = select(File).where(File.uploader_id == user_id, File.is_deleted == False)
        result = await self.db.execute(stmt)
        return len(result.scalars().all())

    async def track_usage(
        self, user_id: uuid.UUID, file_size: int, file_type: FileType
    ) -> None:
        """Отследить использование ресурсов"""
        today = datetime.now().date()

        # Ищем запись за сегодня
        stmt = select(UsageTracker).where(
            UsageTracker.user_id == user_id, UsageTracker.date == today
        )
        result = await self.db.execute(stmt)
        tracker = result.scalar_one_or_none()

        if tracker:
            # Обновляем существующую запись
            tracker.storage_used += file_size
            tracker.files_count += 1
            if file_type == FileType.VIDEO:
                tracker.video_uploads += 1
            elif file_type == FileType.AUDIO:
                tracker.audio_uploads += 1
            tracker.updated_at = datetime.now()
        else:
            # Создаем новую запись
            tracker = UsageTracker(
                user_id=user_id,
                date=today,
                storage_used=file_size,
                files_count=1,
                video_uploads=1 if file_type == FileType.VIDEO else 0,
                audio_uploads=1 if file_type == FileType.AUDIO else 0,
            )
            self.db.add(tracker)

        await self.db.commit()

    async def get_usage_report(
        self, user_id: uuid.UUID, days: int = 30
    ) -> dict[str, Any]:
        """Получить отчет об использовании"""
        start_date = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(UsageTracker)
            .where(UsageTracker.user_id == user_id, UsageTracker.date >= start_date)
            .order_by(UsageTracker.date.desc())
        )

        result = await self.db.execute(stmt)
        trackers = result.scalars().all()

        if not trackers:
            return {
                "period_days": days,
                "total_storage_used": 0,
                "total_files_uploaded": 0,
                "total_video_uploads": 0,
                "total_audio_uploads": 0,
                "daily_average": {
                    "storage": 0,
                    "files": 0,
                    "video": 0,
                    "audio": 0,
                },
            }

        # Агрегируем данные
        total_storage = sum(t.storage_used for t in trackers)
        total_files = sum(t.files_count for t in trackers)
        total_video = sum(t.video_uploads for t in trackers)
        total_audio = sum(t.audio_uploads for t in trackers)

        return {
            "period_days": days,
            "total_storage_used": total_storage,
            "total_files_uploaded": total_files,
            "total_video_uploads": total_video,
            "total_audio_uploads": total_audio,
            "daily_average": {
                "storage": total_storage // len(trackers),
                "files": total_files // len(trackers),
                "video": total_video // len(trackers),
                "audio": total_audio // len(trackers),
            },
            "daily_breakdown": [
                {
                    "date": t.date.isoformat(),
                    "storage_used": t.storage_used,
                    "files_count": t.files_count,
                    "video_uploads": t.video_uploads,
                    "audio_uploads": t.audio_uploads,
                }
                for t in trackers
            ],
        }

    async def get_upgrade_suggestion(self, user: User) -> dict[str, Any]:
        """Получить рекомендации по апгрейду"""
        subscription = await self.get_user_subscription(user.id)
        limits = await self.get_user_limits(user.id)
        current_usage = await self.get_storage_usage(user.id)
        current_files = await self.get_files_count(user.id)

        suggestions = []

        # Проверяем хранилище
        storage_usage_percent = (
            (current_usage / limits["storage_limit"]) * 100
            if limits["storage_limit"] > 0
            else 0
        )
        if storage_usage_percent > 80:
            suggestions.append(
                {
                    "type": "storage",
                    "priority": "high",
                    "message": f"Использовано {storage_usage_percent:.1f}% хранилища",
                    "recommended": "storage_package_5gb",
                }
            )

        # Проверяем количество файлов
        files_usage_percent = (
            (current_files / limits["file_count_limit"]) * 100
            if limits["file_count_limit"] > 0
            else 0
        )
        if files_usage_percent > 80:
            suggestions.append(
                {
                    "type": "files",
                    "priority": "high",
                    "message": f"Использовано {files_usage_percent:.1f}% лимита файлов",
                    "recommended": "upgrade_plan",
                }
            )

        # Проверяем доступные типы файлов
        if FileType.VIDEO.value not in limits["allowed_file_types"]:
            suggestions.append(
                {
                    "type": "video",
                    "priority": "medium",
                    "message": "Загрузка видео недоступна",
                    "recommended": "video_package",
                }
            )

        return {
            "current_plan": subscription.plan if subscription else "free",
            "current_usage": {
                "storage": current_usage,
                "storage_limit": limits["storage_limit"],
                "files": current_files,
                "files_limit": limits["file_count_limit"],
            },
            "suggestions": suggestions,
        }

    def _get_free_plan_limits(self) -> dict[str, Any]:
        """Лимиты бесплатного плана"""
        return {
            "storage_limit": 100 * 1024 * 1024,  # 100 МБ
            "file_count_limit": 50,
            "max_file_size": 10 * 1024 * 1024,  # 10 МБ
            "allowed_file_types": [
                FileType.IMAGE.value,
                FileType.DOCUMENT.value,
                FileType.ARCHIVE.value,
            ],
            "projects_limit": 3,
            "users_limit": 5,
        }

    async def create_default_subscription(self, user_id: uuid.UUID) -> UserSubscription:
        """Создать подписку по умолчанию (Free)"""
        limits = self._get_free_plan_limits()

        subscription = UserSubscription(
            user_id=user_id,
            plan=SubscriptionPlan.FREE,
            **limits,
            allowed_file_types=json.dumps(limits["allowed_file_types"]),
        )

        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription
