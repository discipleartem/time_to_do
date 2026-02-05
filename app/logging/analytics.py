"""
Конфигурация логирования для системы аналитики.

Следует Глобальным правилам:
- Russian language для сообщений
- Explicit logging вместо print
- Structured logging с контекстом
- Разные уровни для разных операций
"""

import logging
from typing import Any
from uuid import UUID

from app.exceptions.analytics import AnalyticsError


class AnalyticsLogger:
    """Специализированный логгер для системы аналитики."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("app.analytics")
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Настройка логгера."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_event_tracked(
        self,
        event_type: str,
        user_id: UUID | None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
    ) -> None:
        """Логирование отслеживания события."""
        context = {
            "event_type": event_type,
            "user_id": str(user_id) if user_id else None,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id else None,
        }
        self.logger.info(f"Событие отслежено: {event_type}", extra=context)

    def log_metrics_calculation(
        self,
        metric_type: str,
        scope_type: str,
        scope_id: UUID | None,
        period: str,
        duration_ms: float,
    ) -> None:
        """Логирование расчета метрик."""
        context = {
            "metric_type": metric_type,
            "scope_type": scope_type,
            "scope_id": str(scope_id) if scope_id else None,
            "period": period,
            "duration_ms": duration_ms,
        }
        self.logger.info(
            f"Метрики рассчитаны: {metric_type} за {period}", extra=context
        )

    def log_dashboard_created(
        self, dashboard_id: UUID, user_id: UUID, widget_count: int
    ) -> None:
        """Логирование создания дашборда."""
        context = {
            "dashboard_id": str(dashboard_id),
            "user_id": str(user_id),
            "widget_count": widget_count,
        }
        self.logger.info(f"Дашборд создан с {widget_count} виджетами", extra=context)

    def log_analytics_error(self, error: AnalyticsError, operation: str) -> None:
        """Логирование ошибки аналитики."""
        context = {
            "operation": operation,
            "error_code": error.error_code,
            "error_details": error.details,
        }
        self.logger.error(
            f"Ошибка аналитики в операции '{operation}': {error.message}", extra=context
        )

    def log_permission_denied(self, user_id: UUID, resource: str, action: str) -> None:
        """Логирование отказа в доступе."""
        context = {"user_id": str(user_id), "resource": resource, "action": action}
        self.logger.warning(
            f"Доступ запрещен: пользователь {user_id} пытался {action} для {resource}",
            extra=context,
        )

    def log_validation_error(self, field: str, value: Any, reason: str) -> None:
        """Логирование ошибки валидации."""
        context = {"field": field, "value": str(value), "reason": reason}
        self.logger.warning(f"Ошибка валидации поля '{field}': {reason}", extra=context)

    def log_data_access(self, user_id: UUID, data_type: str, record_count: int) -> None:
        """Логирование доступа к данным."""
        context = {
            "user_id": str(user_id),
            "data_type": data_type,
            "record_count": record_count,
        }
        self.logger.info(
            f"Доступ к данным: {data_type} ({record_count} записей)", extra=context
        )

    def log_performance_warning(
        self, operation: str, duration_ms: float, threshold_ms: float = 1000
    ) -> None:
        """Логирование предупреждения о производительности."""
        context = {
            "operation": operation,
            "duration_ms": duration_ms,
            "threshold_ms": threshold_ms,
        }
        self.logger.warning(
            f"Медленная операция: {operation} заняла {duration_ms:.2f}мс (порог: {threshold_ms}мс)",
            extra=context,
        )

    def log_cache_hit(self, cache_key: str, operation: str) -> None:
        """Логирование попадания в кэш."""
        context = {"cache_key": cache_key, "operation": operation}
        self.logger.debug(f"Попадание в кэш: {operation}", extra=context)

    def log_cache_miss(self, cache_key: str, operation: str) -> None:
        """Логирование промаха кэша."""
        context = {"cache_key": cache_key, "operation": operation}
        self.logger.debug(f"Промах кэша: {operation}", extra=context)


# Глобальный экземпляр логгера
analytics_logger = AnalyticsLogger()
