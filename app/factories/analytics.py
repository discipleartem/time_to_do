"""
Factory и dependency injection для системы аналитики.

Следует Глобальным правилам:
- Dependency injection для тестируемости
- Explicit configuration
- Single Responsibility Principle
- Type-safe конфигурация
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.logging.analytics import analytics_logger
from app.services.analytics_service import AnalyticsService


class AnalyticsConfiguration:
    """Конфигурация системы аналитики."""

    def __init__(
        self,
        enable_event_tracking: bool = True,
        enable_metrics_calculation: bool = True,
        enable_dashboard_creation: bool = True,
        cache_ttl_seconds: int = 300,
        max_events_per_batch: int = 100,
        metrics_retention_days: int = 365,
        enable_real_time_updates: bool = True,
        performance_threshold_ms: float = 1000.0,
    ) -> None:
        self.enable_event_tracking = enable_event_tracking
        self.enable_metrics_calculation = enable_metrics_calculation
        self.enable_dashboard_creation = enable_dashboard_creation
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_events_per_batch = max_events_per_batch
        self.metrics_retention_days = metrics_retention_days
        self.enable_real_time_updates = enable_real_time_updates
        self.performance_threshold_ms = performance_threshold_ms

    @classmethod
    def from_settings(cls) -> "AnalyticsConfiguration":
        """Создание конфигурации из настроек приложения."""
        return cls(
            enable_event_tracking=getattr(settings, "ANALYTICS_ENABLE_EVENTS", True),
            enable_metrics_calculation=getattr(
                settings, "ANALYTICS_ENABLE_METRICS", True
            ),
            enable_dashboard_creation=getattr(
                settings, "ANALYTICS_ENABLE_DASHBOARDS", True
            ),
            cache_ttl_seconds=getattr(settings, "ANALYTICS_CACHE_TTL", 300),
            max_events_per_batch=getattr(settings, "ANALYTICS_MAX_BATCH_SIZE", 100),
            metrics_retention_days=getattr(settings, "ANALYTICS_RETENTION_DAYS", 365),
            enable_real_time_updates=getattr(settings, "ANALYTICS_REAL_TIME", True),
            performance_threshold_ms=getattr(
                settings, "ANALYTICS_PERFORMANCE_THRESHOLD", 1000.0
            ),
        )


class AnalyticsServiceFactory:
    """Factory для создания сервисов аналитики с dependency injection."""

    def __init__(self, config: AnalyticsConfiguration | None = None) -> None:
        self.config = config or AnalyticsConfiguration.from_settings()
        self._services: dict[str, AnalyticsService] = {}

    def create_service(self, db_session: AsyncSession) -> AnalyticsService:
        """Создание сервиса аналитики с внедрением зависимостей."""
        # Создаем сервис с конфигурацией и логированием
        service = AnalyticsService(db_session)

        # Внедряем конфигурацию
        service._config = self.config  # type: ignore

        # Внедряем логгер
        service._logger = analytics_logger  # type: ignore

        return service

    def get_cached_service(
        self, session_id: str, db_session: AsyncSession
    ) -> AnalyticsService:
        """Получение кэшированного сервиса для сессии."""
        if session_id not in self._services:
            self._services[session_id] = self.create_service(db_session)
        return self._services[session_id]

    def clear_cache(self, session_id: str | None = None) -> None:
        """Очистка кэша сервисов."""
        if session_id:
            self._services.pop(session_id, None)
        else:
            self._services.clear()


class AnalyticsPermissionChecker:
    """Проверка прав доступа для аналитики."""

    @staticmethod
    def can_access_project_metrics(
        user_id: UUID, project_id: UUID, db_session: AsyncSession
    ) -> bool:
        """Проверка доступа к метрикам проекта."""
        # TODO: Реализовать проверку членства в проекте
        # Пока возвращаем True для демонстрации
        return True

    @staticmethod
    def can_access_user_metrics(requester_id: UUID, target_user_id: UUID) -> bool:
        """Проверка доступа к метрикам пользователя."""
        # Пользователь может смотреть свои метрики
        if requester_id == target_user_id:
            return True

        # TODO: Реализовать проверку прав администратора
        return False

    @staticmethod
    def can_create_dashboard(user_id: UUID, is_public: bool = False) -> bool:
        """Проверка прав на создание дашборда."""
        # TODO: Реализовать проверку лимитов подписки
        return True

    @staticmethod
    def can_access_global_analytics(user_id: UUID) -> bool:
        """Проверка доступа к глобальной аналитике."""
        # TODO: Реализовать проверку прав администратора
        return False


class AnalyticsValidator:
    """Валидатор данных аналитики."""

    @staticmethod
    def validate_date_range(
        start_date: datetime | None, end_date: datetime | None
    ) -> None:
        """Валидация диапазона дат."""
        if start_date and end_date:
            if end_date <= start_date:
                raise ValueError("Конечная дата должна быть после начальной")

            # Проверка, что диапазон не слишком большой
            max_days = 365
            if (end_date - start_date).days > max_days:
                raise ValueError(f"Диапазон дат не может превышать {max_days} дней")

    @staticmethod
    def validate_period_type(period_type: str) -> None:
        """Валидация типа периода."""
        allowed_periods = {"daily", "weekly", "monthly"}
        if period_type not in allowed_periods:
            raise ValueError(
                f"Недопустимый тип периода. Разрешенные: {allowed_periods}"
            )

    @staticmethod
    def validate_scope_type(scope_type: str) -> None:
        """Валидация типа области."""
        allowed_scopes = {"global", "project", "user", "sprint"}
        if scope_type not in allowed_scopes:
            raise ValueError(f"Недопустимый тип области. Разрешенные: {allowed_scopes}")


# Глобальные экземпляры для dependency injection
analytics_factory = AnalyticsServiceFactory()
analytics_permission_checker = AnalyticsPermissionChecker()
analytics_validator = AnalyticsValidator()
