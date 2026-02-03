"""
Тесты для исключений приложения
"""

from fastapi import HTTPException, status

from app.exceptions import (
    ActiveTimerExistsError,
    AuthenticationError,
    BaseAPIException,
    BusinessLogicError,
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    NotFoundError,
    PermissionError,
    ProjectAccessDeniedError,
    ProjectMemberLimitError,
    ProjectNotFoundError,
    QuotaExceededError,
    RateLimitError,
    SprintAlreadyStartedError,
    TaskHasSubtasksError,
    TaskNotFoundError,
    UserAlreadyExistsError,
    ValidationError,
    exception_to_http_exception,
    handle_database_error,
)


class TestBaseAPIException:
    """Тесты базового исключения API"""

    def test_base_exception_creation(self):
        """Создание базового исключения"""
        exc = BaseAPIException("Test message", 400, {"key": "value"})
        assert exc.message == "Test message"
        assert exc.status_code == 400
        assert exc.details == {"key": "value"}

    def test_base_exception_defaults(self):
        """Значения по умолчанию"""
        exc = BaseAPIException("Test message")
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.details == {}

    def test_base_exception_str_representation(self):
        """Строковое представление"""
        exc = BaseAPIException("Test message")
        assert str(exc) == "Test message"


class TestValidationError:
    """Тесты ошибок валидации"""

    def test_validation_error_without_field(self):
        """Ошибка валидации без указания поля"""
        exc = ValidationError("Invalid data")
        assert exc.message == "Invalid data"
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert exc.details == {}

    def test_validation_error_with_field(self):
        """Ошибка валидации с указанием поля"""
        exc = ValidationError("Invalid email", "email")
        assert exc.details == {"field": "email"}


class TestNotFoundError:
    """Тесты ошибок 'не найдено'"""

    def test_not_found_without_identifier(self):
        """Ресурс не найден без идентификатора"""
        exc = NotFoundError("Проект")
        assert "Проект не найден" in exc.message
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert exc.details["resource"] == "Проект"

    def test_not_found_with_identifier(self):
        """Ресурс не найден с идентификатором"""
        exc = NotFoundError("Проект", "123")
        assert "ID: 123" in exc.message
        assert exc.details["identifier"] == "123"


class TestPermissionError:
    """Тесты ошибок доступа"""

    def test_permission_error_without_resource(self):
        """Ошибка доступа без указания ресурса"""
        exc = PermissionError("delete")
        assert "Недостаточно прав для действия: delete" in exc.message
        assert exc.status_code == status.HTTP_403_FORBIDDEN

    def test_permission_error_with_resource(self):
        """Ошибка доступа с указанием ресурса"""
        exc = PermissionError("delete", "проект")
        assert "над ресурсом: проект" in exc.message


class TestAuthenticationError:
    """Тесты ошибок аутентификации"""

    def test_authentication_error_default(self):
        """Ошибка аутентификации с сообщением по умолчанию"""
        exc = AuthenticationError()
        assert exc.message == "Ошибка аутентификации"
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authentication_error_custom(self):
        """Ошибка аутентификации с кастомным сообщением"""
        exc = AuthenticationError("Неверный токен")
        assert exc.message == "Неверный токен"


class TestRateLimitError:
    """Тесты ошибок превышения лимита"""

    def test_rate_limit_error(self):
        """Ошибка превышения лимита запросов"""
        exc = RateLimitError(100, 60)
        assert "100 за 60 секунд" in exc.message
        assert exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exc.details["limit"] == 100
        assert exc.details["window"] == 60


class TestQuotaExceededError:
    """Тесты ошибок превышения квоты"""

    def test_quota_exceeded_error(self):
        """Ошибка превышения квоты"""
        exc = QuotaExceededError("projects", 5, 10)
        assert "5/10" in exc.message
        assert exc.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert exc.details["quota_type"] == "projects"
        assert exc.details["current"] == 5
        assert exc.details["limit"] == 10


class TestBusinessLogicError:
    """Тесты ошибок бизнес-логики"""

    def test_business_logic_error_without_code(self):
        """Ошибка бизнес-логики без кода"""
        exc = BusinessLogicError("Invalid operation")
        assert exc.message == "Invalid operation"
        assert exc.details == {}

    def test_business_logic_error_with_code(self):
        """Ошибка бизнес-логики с кодом"""
        exc = BusinessLogicError("Invalid operation", "INVALID_OP")
        assert exc.details["code"] == "INVALID_OP"


class TestExternalServiceError:
    """Тесты ошибок внешних сервисов"""

    def test_external_service_error_default(self):
        """Ошибка внешнего сервиса с сообщением по умолчанию"""
        exc = ExternalServiceError("GitHub")
        assert "GitHub: Ошибка внешнего сервиса" in exc.message
        assert exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_external_service_error_custom(self):
        """Ошибка внешнего сервиса с кастомным сообщением"""
        exc = ExternalServiceError("GitHub", "API limit exceeded")
        assert "GitHub: API limit exceeded" in exc.message


class TestDomainSpecificExceptions:
    """Тесты специфических исключений доменной области"""

    def test_project_not_found_error(self):
        """Ошибка 'проект не найден'"""
        exc = ProjectNotFoundError("proj-123")
        assert exc.details["resource"] == "Проект"
        assert exc.details["identifier"] == "proj-123"

    def test_project_access_denied_error(self):
        """Ошибка доступа к проекту"""
        exc = ProjectAccessDeniedError("edit", "proj-123")
        assert "Доступ к проекту запрещен" in exc.message
        assert "ID: proj-123" in exc.message

    def test_project_member_limit_error(self):
        """Ошибка превышения лимита участников"""
        exc = ProjectMemberLimitError(5, 3)
        assert "5/3" in exc.message
        assert exc.details["current"] == 5
        assert exc.details["limit"] == 3

    def test_task_not_found_error(self):
        """Ошибка 'задача не найдена'"""
        exc = TaskNotFoundError("task-123")
        assert exc.details["resource"] == "Задача"
        assert exc.details["identifier"] == "task-123"

    def test_task_has_subtasks_error(self):
        """Ошибка удаления задачи с подзадачами"""
        exc = TaskHasSubtasksError("task-123")
        assert "Нельзя удалить задачу, у которой есть подзадачи" in exc.message
        assert exc.details["task_id"] == "task-123"

    def test_user_already_exists_error(self):
        """Ошибка 'пользователь уже существует'"""
        exc = UserAlreadyExistsError("email", "test@example.com")
        assert "email 'test@example.com'" in exc.message
        assert exc.details["field"] == "email"

    def test_sprint_already_started_error(self):
        """Ошибка 'спринт уже запущен'"""
        exc = SprintAlreadyStartedError("sprint-123")
        assert "Спринт уже запущен" in exc.message
        assert exc.details["sprint_id"] == "sprint-123"

    def test_active_timer_exists_error(self):
        """Ошибка 'активный таймер уже существует'"""
        exc = ActiveTimerExistsError("user-123")
        assert "У пользователя уже есть активный таймер" in exc.message
        assert exc.details["user_id"] == "user-123"


class TestExceptionHelpers:
    """Тесты вспомогательных функций для исключений"""

    def test_exception_to_http_exception(self):
        """Преобразование исключения в HTTPException"""
        exc = ValidationError("Invalid data", "email")
        http_exc = exception_to_http_exception(exc)

        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        detail = http_exc.detail
        assert detail["message"] == "Invalid data"
        assert detail["details"]["field"] == "email"
        assert detail["type"] == "ValidationError"

    def test_handle_database_error_unique_constraint(self):
        """Обработка ошибки уникального ограничения"""
        db_exc = Exception("unique constraint violation")
        api_exc = handle_database_error(db_exc)

        assert isinstance(api_exc, ConflictError)
        assert "уже существует" in api_exc.message

    def test_handle_database_error_foreign_key(self):
        """Обработка ошибки внешнего ключа"""
        db_exc = Exception("foreign key constraint violation")
        api_exc = handle_database_error(db_exc)

        assert isinstance(api_exc, ValidationError)
        assert "Связанная запись не найдена" in api_exc.message

    def test_handle_database_error_not_null(self):
        """Обработка ошибки NOT NULL ограничения"""
        db_exc = Exception("not null constraint violation")
        api_exc = handle_database_error(db_exc)

        assert isinstance(api_exc, ValidationError)
        assert "Обязательное поле не указано" in api_exc.message

    def test_handle_database_error_generic(self):
        """Обработка общей ошибки базы данных"""
        db_exc = Exception("generic database error")
        api_exc = handle_database_error(db_exc)

        assert isinstance(api_exc, DatabaseError)
        assert "generic database error" in api_exc.message


class TestExceptionInheritance:
    """Тесты наследования исключений"""

    def test_project_error_inheritance(self):
        """Наследование ProjectError"""
        from app.exceptions import ProjectError

        exc = ProjectError("Test", "proj-123")
        assert isinstance(exc, BusinessLogicError)
        assert isinstance(exc, BaseAPIException)
        assert exc.details["project_id"] == "proj-123"

    def test_task_error_inheritance(self):
        """Наследование TaskError"""
        from app.exceptions import TaskError

        exc = TaskError("Test", "task-123")
        assert isinstance(exc, BusinessLogicError)
        assert exc.details["task_id"] == "task-123"

    def test_user_error_inheritance(self):
        """Наследование UserError"""
        from app.exceptions import UserError

        exc = UserError("Test", "user-123")
        assert isinstance(exc, BusinessLogicError)
        assert exc.details["user_id"] == "user-123"
