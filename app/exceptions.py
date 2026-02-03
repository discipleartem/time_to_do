"""
Кастомные исключения для приложения
"""

from typing import Any

from fastapi import HTTPException, status


class BaseAPIException(Exception):
    """Базовое исключение API"""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    @property
    def code(self) -> str | None:
        """Получение кода ошибки из details"""
        return self.details.get("code")


class ValidationError(BaseAPIException):
    """Ошибка валидации"""

    def __init__(self, message: str, field: str | None = None):
        details = {"field": field} if field else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details=details,
        )


class NotFoundError(BaseAPIException):
    """Ресурс не найден"""

    def __init__(self, resource: str, identifier: str | None = None):
        message = f"{resource} не найден"
        if identifier:
            message += f" (ID: {identifier})"

        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": identifier},
        )


class PermissionError(BaseAPIException):
    """Ошибка доступа"""

    def __init__(self, action: str, resource: str | None = None):
        message = f"Недостаточно прав для действия: {action}"
        if resource:
            message += f" над ресурсом: {resource}"

        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details={"action": action, "resource": resource},
        )


class AuthenticationError(BaseAPIException):
    """Ошибка аутентификации"""

    def __init__(self, message: str = "Ошибка аутентификации"):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(BaseAPIException):
    """Ошибка авторизации"""

    def __init__(self, message: str = "Недостаточно прав доступа"):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN)


class ConflictError(BaseAPIException):
    """Конфликт данных"""

    def __init__(self, message: str, field: str | None = None):
        details = {"field": field} if field else {}
        super().__init__(
            message=message, status_code=status.HTTP_409_CONFLICT, details=details
        )


class RateLimitError(BaseAPIException):
    """Превышен лимит запросов"""

    def __init__(self, limit: int, window: int):
        message = f"Превышен лимит запросов: {limit} за {window} секунд"
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"limit": limit, "window": window},
        )


class QuotaExceededError(BaseAPIException):
    """Превышена квота"""

    def __init__(self, quota_type: str, current: int, limit: int):
        message = f"Превышена квота {quota_type}: {current}/{limit}"
        super().__init__(
            message=message,
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            details={"quota_type": quota_type, "current": current, "limit": limit},
        )


class BusinessLogicError(BaseAPIException):
    """Ошибка бизнес-логики"""

    def __init__(self, message: str, code: str | None = None):
        details = {"code": code} if code else {}
        super().__init__(
            message=message, status_code=status.HTTP_400_BAD_REQUEST, details=details
        )


class ExternalServiceError(BaseAPIException):
    """Ошибка внешнего сервиса"""

    def __init__(self, service: str, message: str = "Ошибка внешнего сервиса"):
        super().__init__(
            message=f"{service}: {message}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service},
        )


class DatabaseError(BaseAPIException):
    """Ошибка базы данных"""

    def __init__(self, message: str = "Ошибка базы данных"):
        super().__init__(
            message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ConfigurationError(BaseAPIException):
    """Ошибка конфигурации"""

    def __init__(self, message: str = "Ошибка конфигурации"):
        super().__init__(
            message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Специфические исключения для доменной области


class ProjectError(BusinessLogicError):
    """Ошибка связанная с проектами"""

    def __init__(self, message: str, project_id: str | None = None):
        details = {"project_id": project_id} if project_id else {}
        super().__init__(message, code="PROJECT_ERROR")
        self.details.update(details)


class ProjectNotFoundError(NotFoundError):
    """Проект не найден"""

    def __init__(self, project_id: str):
        super().__init__("Проект", project_id)


class ProjectAccessDeniedError(PermissionError):
    """Доступ к проекту запрещен"""

    def __init__(self, action: str = "доступ", project_id: str | None = None):
        message = "Доступ к проекту запрещен"
        if project_id:
            message += f" (ID: {project_id})"

        super().__init__(action, "проект")
        self.message = message


class ProjectMemberLimitError(BusinessLogicError):
    """Превышен лимит участников проекта"""

    def __init__(self, current: int, limit: int):
        message = f"Превышен лимит участников проекта: {current}/{limit}"
        super().__init__(message, code="MEMBER_LIMIT_EXCEEDED")
        self.details.update({"current": current, "limit": limit})


class TaskError(BusinessLogicError):
    """Ошибка связанная с задачами"""

    def __init__(self, message: str, task_id: str | None = None):
        details = {"task_id": task_id} if task_id else {}
        super().__init__(message, code="TASK_ERROR")
        self.details.update(details)


class TaskNotFoundError(NotFoundError):
    """Задача не найдена"""

    def __init__(self, task_id: str):
        super().__init__("Задача", task_id)


class TaskAccessDeniedError(PermissionError):
    """Доступ к задаче запрещен"""

    def __init__(self, action: str = "доступ", task_id: str | None = None):
        message = "Доступ к задаче запрещен"
        if task_id:
            message += f" (ID: {task_id})"

        super().__init__(action, "задача")
        self.message = message


class TaskHasSubtasksError(BusinessLogicError):
    """Попытка удалить задачу с подзадачами"""

    def __init__(self, task_id: str):
        message = "Нельзя удалить задачу, у которой есть подзадачи"
        super().__init__(message, code="TASK_HAS_SUBTASKS")
        self.details.update({"task_id": task_id})


class UserError(BusinessLogicError):
    """Ошибка связанная с пользователями"""

    def __init__(self, message: str, user_id: str | None = None):
        details = {"user_id": user_id} if user_id else {}
        super().__init__(message, code="USER_ERROR")
        self.details.update(details)


class UserNotFoundError(NotFoundError):
    """Пользователь не найден"""

    def __init__(self, user_id: str):
        super().__init__("Пользователь", user_id)


class UserAlreadyExistsError(ConflictError):
    """Пользователь уже существует"""

    def __init__(self, field: str, value: str):
        message = f"Пользователь с {field} '{value}' уже существует"
        super().__init__(message, field)


class SprintError(BusinessLogicError):
    """Ошибка связанная со спринтами"""

    def __init__(self, message: str, sprint_id: str | None = None):
        details = {"sprint_id": sprint_id} if sprint_id else {}
        super().__init__(message, code="SPRINT_ERROR")
        self.details.update(details)


class SprintNotFoundError(NotFoundError):
    """Спринт не найден"""

    def __init__(self, sprint_id: str):
        super().__init__("Спринт", sprint_id)


class SprintAlreadyStartedError(BusinessLogicError):
    """Спринт уже запущен"""

    def __init__(self, sprint_id: str):
        message = "Спринт уже запущен и не может быть изменен"
        super().__init__(message, code="SPRINT_ALREADY_STARTED")
        self.details.update({"sprint_id": sprint_id})


class TimeEntryError(BusinessLogicError):
    """Ошибка связанная с записями времени"""

    def __init__(self, message: str, entry_id: str | None = None):
        details = {"entry_id": entry_id} if entry_id else {}
        super().__init__(message, code="TIME_ENTRY_ERROR")
        self.details.update(details)


class ActiveTimerExistsError(BusinessLogicError):
    """У пользователя уже есть активный таймер"""

    def __init__(self, user_id: str):
        message = "У пользователя уже есть активный таймер"
        super().__init__(message, code="ACTIVE_TIMER_EXISTS")
        self.details.update({"user_id": user_id})


class CommentError(BusinessLogicError):
    """Ошибка связанная с комментариями"""

    def __init__(self, message: str, comment_id: str | None = None):
        details = {"comment_id": comment_id} if comment_id else {}
        super().__init__(message, code="COMMENT_ERROR")
        self.details.update(details)


class CommentNotFoundError(NotFoundError):
    """Комментарий не найден"""

    def __init__(self, comment_id: str):
        super().__init__("Комментарий", comment_id)


class CommentAccessDeniedError(PermissionError):
    """Доступ к комментарию запрещен"""

    def __init__(self, action: str = "доступ", comment_id: str | None = None):
        message = "Доступ к комментарию запрещен"
        if comment_id:
            message += f" (ID: {comment_id})"

        super().__init__(action, "комментарий")
        self.message = message


# Функции для преобразования исключений в HTTP ответы
def exception_to_http_exception(exc: BaseAPIException) -> HTTPException:
    """Преобразование кастомного исключения в HTTPException"""
    return HTTPException(
        status_code=exc.status_code,
        detail={
            "message": exc.message,
            "details": exc.details,
            "type": exc.__class__.__name__,
        },
    )


def handle_database_error(exc: Exception) -> BaseAPIException:
    """Обработка ошибок базы данных"""
    error_message = str(exc).lower()

    if "unique constraint" in error_message or "duplicate key" in error_message:
        return ConflictError("Запись уже существует")

    if "foreign key constraint" in error_message:
        return ValidationError("Связанная запись не найдена")

    if "not null constraint" in error_message:
        return ValidationError("Обязательное поле не указано")

    return DatabaseError(f"Ошибка базы данных: {exc}")
