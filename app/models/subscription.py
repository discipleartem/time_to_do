"""
Модели для системы подписок и монетизации
"""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import UUID, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class SubscriptionPlan(str, Enum):
    """Тарифные планы"""

    FREE = "free"
    STARTER = "starter"
    TEAM = "team"
    BUSINESS = "business"


class AddOnType(str, Enum):
    """Типы дополнений"""

    STORAGE = "storage"
    VIDEO_AUDIO = "video_audio"
    USERS = "users"
    PROJECTS = "projects"
    FEATURES = "features"
    COMBO = "combo"


class UserSubscription(BaseModel):
    """Подписка пользователя"""

    __tablename__ = "user_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan: Mapped[SubscriptionPlan] = mapped_column(String(20), nullable=False)

    # Лимиты плана
    storage_limit: Mapped[int] = mapped_column(Integer, nullable=False)  # в байтах
    file_count_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    max_file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # в байтах
    allowed_file_types: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    projects_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    users_limit: Mapped[int] = mapped_column(Integer, nullable=False)

    # Статус
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC), nullable=False
    )

    # Отношения
    if TYPE_CHECKING:
        user: Mapped["User"] = relationship("User", back_populates="subscription")
    else:
        user: Mapped[any] = relationship("User", back_populates="subscription")

    def __repr__(self) -> str:
        return f"<UserSubscription(user_id={self.user_id}, plan={self.plan})>"


class AddOnPackage(BaseModel):
    """Пакеты дополнений"""

    __tablename__ = "addon_packages"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[AddOnType] = mapped_column(String(20), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)  # в центах
    billing_cycle: Mapped[str] = mapped_column(
        String(20), default="monthly", nullable=False
    )
    features: Mapped[str] = mapped_column(Text, nullable=False)  # JSON с параметрами
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(UTC), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AddOnPackage(name={self.name}, type={self.type}, price=${self.price/100})>"


class UserAddOn(BaseModel):
    """Купленные пакеты пользователей"""

    __tablename__ = "user_addons"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("addon_packages.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Статус покупки
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(UTC), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Использование
    usage_data: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # JSON с текущим использованием
    last_usage_update: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Отношения
    if TYPE_CHECKING:
        user: Mapped["User"] = relationship("User")
        package: Mapped[AddOnPackage] = relationship("AddOnPackage")
    else:
        user: Mapped[any] = relationship("User")
        package: Mapped[any] = relationship("AddOnPackage")

    def __repr__(self) -> str:
        return f"<UserAddOn(user_id={self.user_id}, package_id={self.package_id})>"


class UsageTracker(BaseModel):
    """Трекер использования ресурсов"""

    __tablename__ = "usage_tracker"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Использование ресурсов
    storage_used: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # байты
    files_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    projects_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    users_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    api_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    video_uploads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    audio_uploads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Метаданные
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Отношения
    if TYPE_CHECKING:
        user: Mapped["User"] = relationship("User")
    else:
        user: Mapped[any] = relationship("User")

    def __repr__(self) -> str:
        return f"<UsageTracker(user_id={self.user_id}, date={self.date})>"


class BillingTransaction(BaseModel):
    """Транзакции биллинга"""

    __tablename__ = "billing_transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    transaction_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )

    # Детали транзакции
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # в центах
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # pending, completed, failed
    payment_method: Mapped[str] = mapped_column(String(50), nullable=True)

    # Тип операции
    operation_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # subscription, addon, upgrade
    reference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )  # subscription_id, addon_id

    # Время
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(UTC), nullable=False
    )
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Отношения
    if TYPE_CHECKING:
        user: Mapped["User"] = relationship("User")
    else:
        user: Mapped[any] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<BillingTransaction(id={self.transaction_id}, amount=${self.amount/100})>"
        )
