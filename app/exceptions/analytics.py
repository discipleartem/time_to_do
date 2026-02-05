"""
Кастомные исключения для системы аналитики.

Следует Глобальным правилам:
- Explicit > Implicit (явные исключения)
- Russian language для сообщений об ошибках
- Type-safe (строгая типизация)
"""

from typing import Any


class AnalyticsError(Exception):
    """Базовое исключение для системы аналитики."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class AnalyticsValidationError(AnalyticsError):
    """Ошибка валидации данных аналитики."""

    def __init__(
        self, message: str, field: str | None = None, value: Any | None = None
    ) -> None:
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(
            message=message, error_code="VALIDATION_ERROR", details=details
        )
        self.field = field
        self.value = value


class AnalyticsPermissionError(AnalyticsError):
    """Ошибка доступа к данным аналитики."""

    def __init__(
        self,
        message: str,
        user_id: str | None = None,
        resource: str | None = None,
    ) -> None:
        details = {}
        if user_id:
            details["user_id"] = user_id
        if resource:
            details["resource"] = resource

        super().__init__(
            message=message, error_code="PERMISSION_DENIED", details=details
        )
        self.user_id = user_id
        self.resource = resource


class MetricsCalculationError(AnalyticsError):
    """Ошибка расчета метрик."""

    def __init__(
        self,
        message: str,
        metric_type: str | None = None,
        period: str | None = None,
    ) -> None:
        details = {}
        if metric_type:
            details["metric_type"] = metric_type
        if period:
            details["period"] = period

        super().__init__(
            message=message, error_code="CALCULATION_ERROR", details=details
        )
        self.metric_type = metric_type
        self.period = period


class DashboardConfigurationError(AnalyticsError):
    """Ошибка конфигурации дашборда."""

    def __init__(
        self,
        message: str,
        dashboard_id: str | None = None,
        widget_type: str | None = None,
    ) -> None:
        details = {}
        if dashboard_id:
            details["dashboard_id"] = dashboard_id
        if widget_type:
            details["widget_type"] = widget_type

        super().__init__(
            message=message, error_code="DASHBOARD_CONFIG_ERROR", details=details
        )
        self.dashboard_id = dashboard_id
        self.widget_type = widget_type


class AnalyticsDataError(AnalyticsError):
    """Ошибка обработки данных аналитики."""

    def __init__(
        self,
        message: str,
        data_source: str | None = None,
        operation: str | None = None,
    ) -> None:
        details = {}
        if data_source:
            details["data_source"] = data_source
        if operation:
            details["operation"] = operation

        super().__init__(message=message, error_code="DATA_ERROR", details=details)
        self.data_source = data_source
        self.operation = operation
