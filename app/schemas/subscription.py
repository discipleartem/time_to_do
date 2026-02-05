"""
Pydantic схемы для подписок и пакетов
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SubscriptionResponse(BaseModel):
    """Ответ с информацией о подписке"""

    id: uuid.UUID = Field(..., description="ID подписки")
    plan: str = Field(..., description="Тарифный план")
    storage_limit: int = Field(..., description="Лимит хранилища в байтах")
    file_count_limit: int = Field(..., description="Лимит количества файлов")
    max_file_size: int = Field(..., description="Максимальный размер файла в байтах")
    allowed_file_types: str = Field(..., description="Разрешенные типы файлов (JSON)")
    projects_limit: int = Field(..., description="Лимит проектов")
    users_limit: int = Field(..., description="Лимит пользователей")
    expires_at: datetime | None = Field(None, description="Дата окончания")
    is_active: bool = Field(..., description="Активна ли подписка")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    class Config:
        from_attributes = True


class AddOnPackageResponse(BaseModel):
    """Ответ с информацией о пакете"""

    id: uuid.UUID = Field(..., description="ID пакета")
    name: str = Field(..., description="Название пакета")
    type: str = Field(..., description="Тип пакета")
    price: int = Field(..., description="Цена в центах")
    billing_cycle: str = Field(..., description="Цикл выставления счетов")
    features: str = Field(..., description="Фичи пакета (JSON)")
    description: str | None = Field(None, description="Описание")
    is_active: bool = Field(..., description="Активен ли пакет")

    class Config:
        from_attributes = True


class UserAddOnResponse(BaseModel):
    """Ответ с информацией о пакете пользователя"""

    id: uuid.UUID = Field(..., description="ID записи о покупке")
    package_id: uuid.UUID = Field(..., description="ID пакета")
    package_name: str = Field(..., description="Название пакета")
    package_type: str = Field(..., description="Тип пакета")
    price: int = Field(..., description="Цена в центах")
    billing_cycle: str = Field(..., description="Цикл выставления счетов")
    purchased_at: datetime = Field(..., description="Дата покупки")
    expires_at: datetime | None = Field(None, description="Дата окончания")
    is_active: bool = Field(..., description="Активен ли пакет")
    auto_renew: bool = Field(..., description="Автопродление")
    usage_data: str | None = Field(None, description="Данные об использовании (JSON)")

    class Config:
        from_attributes = True


class UpgradeSuggestionResponse(BaseModel):
    """Ответ с рекомендациями по апгрейду"""

    current_plan: str = Field(..., description="Текущий план")
    current_usage: dict[str, Any] = Field(..., description="Текущее использование")
    suggestions: list[dict[str, Any]] = Field(..., description="Рекомендации")


class UsageReportResponse(BaseModel):
    """Ответ с отчетом об использовании"""

    period_days: int = Field(..., description="Период в днях")
    total_storage_used: int = Field(..., description="Всего использовано хранилища")
    total_files_uploaded: int = Field(..., description="Всего загружено файлов")
    total_video_uploads: int = Field(..., description="Всего загружено видео")
    total_audio_uploads: int = Field(..., description="Всего загружено аудио")
    daily_average: dict[str, int] = Field(..., description="Средние значения в день")
    daily_breakdown: list[dict[str, Any]] = Field(
        ..., description="Ежедневная разбивка"
    )


class BillingTransactionResponse(BaseModel):
    """Ответ с информацией о транзакции"""

    id: str = Field(..., description="ID транзакции")
    amount: int = Field(..., description="Сумма в центах")
    currency: str = Field(..., description="Валюта")
    status: str = Field(..., description="Статус транзакции")
    payment_method: str | None = Field(None, description="Метод оплаты")
    operation_type: str = Field(..., description="Тип операции")
    reference_id: uuid.UUID | None = Field(None, description="ID связанной сущности")
    created_at: datetime = Field(..., description="Дата создания")
    processed_at: datetime | None = Field(None, description="Дата обработки")


class SubscriptionPlanResponse(BaseModel):
    """Ответ с информацией о тарифном плане"""

    plan: str = Field(..., description="Название плана")
    display_name: str = Field(..., description="Отображаемое название")
    description: str = Field(..., description="Описание")
    price: int = Field(..., description="Цена в центах")
    billing_cycle: str = Field(..., description="Цикл выставления счетов")
    features: dict[str, Any] = Field(..., description="Фичи плана")
    limits: dict[str, Any] = Field(..., description="Лимиты плана")
    is_popular: bool = Field(default=False, description="Популярный план")
    is_recommended: bool = Field(default=False, description="Рекомендуемый план")


class PackagePurchaseRequest(BaseModel):
    """Запрос на покупку пакета"""

    package_id: uuid.UUID = Field(..., description="ID пакета")
    billing_cycle: str = Field(default="monthly", description="Цикл выставления счетов")
    auto_renew: bool = Field(default=False, description="Автопродление")


class PackagePurchaseResponse(BaseModel):
    """Ответ на покупку пакета"""

    success: bool = Field(..., description="Успешность операции")
    message: str = Field(..., description="Сообщение")
    transaction_id: str | None = Field(None, description="ID транзакции")
    user_addon: UserAddOnResponse | None = Field(
        None, description="Информация о пакете пользователя"
    )


class SubscriptionUpgradeRequest(BaseModel):
    """Запрос на апгрейд подписки"""

    new_plan: str = Field(..., description="Новый план")
    billing_cycle: str = Field(default="monthly", description="Цикл выставления счетов")
    auto_renew: bool = Field(default=False, description="Автопродление")


class SubscriptionUpgradeResponse(BaseModel):
    """Ответ на апгрейд подписки"""

    success: bool = Field(..., description="Успешность операции")
    message: str = Field(..., description="Сообщение")
    new_subscription: SubscriptionResponse | None = Field(
        None, description="Новая подписка"
    )
    transaction_id: str | None = Field(None, description="ID транзакции")
