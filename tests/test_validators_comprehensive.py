"""
Комплексные тесты для валидаторов бизнес-правил
"""

from datetime import date
from uuid import uuid4

import pytest

from app.exceptions import (
    NotFoundError,
    ValidationError,
)
from app.validators import (
    BaseValidator,
    CommentValidator,
    ProjectTaskValidator,
    SprintValidator,
)


class TestBaseValidator:
    """Тесты базового валидатора"""

    def test_validate_uuid_success(self):
        """Тест валидации корректного UUID"""
        valid_uuid = str(uuid4())
        result = BaseValidator.validate_uuid(valid_uuid)
        assert result == valid_uuid

    def test_validate_uuid_invalid_format(self):
        """Тест валидации некорректного UUID"""
        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_uuid("invalid-uuid")

        assert "Некорректный формат ID" in str(exc_info.value)
        assert exc_info.value.details["field"] == "ID"

    def test_validate_uuid_custom_field_name(self):
        """Тест валидации UUID с именем поля"""
        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_uuid("invalid", "project_id")

        assert "project_id" in str(exc_info.value)
        assert exc_info.value.details["field"] == "project_id"

    def test_validate_email_success(self):
        """Тест валидации корректного email"""
        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "user123@test-domain.org",
        ]

        for email in valid_emails:
            result = BaseValidator.validate_email(email)
            assert result == email.lower()

    def test_validate_email_invalid_format(self):
        """Тест валидации некорректного email"""
        # Проверяем только действительно невалидные email
        invalid_emails = [
            "invalid-email",  # без @
            "@domain.com",  # без пользователя
            "user@",  # без домена
            "user@domain",  # нет TLD
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError) as exc_info:
                BaseValidator.validate_email(email)

            assert "Некорректный формат email" in str(exc_info.value)
            assert exc_info.value.details["field"] == "email"

    def test_validate_email_too_long(self):
        """Тест валидации слишком длинного email"""
        long_email = "a" * 250 + "@example.com"  # 256 символов

        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_email(long_email)

        assert "Email слишком длинный" in str(exc_info.value)

    def test_validate_username_success(self):
        """Тест валидации корректного username"""
        valid_usernames = [
            "user123",
            "test_user",
            "user-name",
            "123",
            "abc",  # минимальная длина 3
        ]

        for username in valid_usernames:
            result = BaseValidator.validate_username(username)
            assert result == username

    def test_validate_username_empty(self):
        """Тест валидации пустого username"""
        result = BaseValidator.validate_username("")
        assert result == ""

        result = BaseValidator.validate_username(None)
        assert result is None

    def test_validate_username_invalid_format(self):
        """Тест валидации некорректного username"""
        invalid_usernames = [
            "us",  # слишком короткий
            "user@name",  # недопустимый символ
            "user name",  # пробел
            "user" * 10,  # слишком длинный
        ]

        for username in invalid_usernames:
            with pytest.raises(ValidationError) as exc_info:
                BaseValidator.validate_username(username)

            assert "Username должен содержать" in str(exc_info.value)
            assert exc_info.value.details["field"] == "username"

    def test_validate_password_success(self):
        """Тест валидации корректного пароля"""
        valid_passwords = [
            "password123",
            "MyPassword1",
            "test123456",
            "Abcdefgh1",
        ]

        for password in valid_passwords:
            result = BaseValidator.validate_password(password)
            assert result == password

    def test_validate_password_too_short(self):
        """Тест валидации слишком короткого пароля"""
        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_password("short")

        assert "минимум 8 символов" in str(exc_info.value)
        assert exc_info.value.details["field"] == "password"

    def test_validate_password_too_long(self):
        """Тест валидации слишком длинного пароля"""
        long_password = "a" * 101

        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_password(long_password)

        assert "Пароль слишком длинный" in str(exc_info.value)

    def test_validate_password_no_letters(self):
        """Тест пароля без букв"""
        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_password("12345678")

        assert "хотя бы одну букву" in str(exc_info.value)

    def test_validate_password_no_digits(self):
        """Тест пароля без цифр"""
        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_password("password")

        assert "хотя бы одну цифру" in str(exc_info.value)

    def test_validate_project_name_success(self):
        """Тест валидации корректного названия проекта"""
        valid_names = [
            "My Project",
            "Проект 123",
            "Test",
            "A" * 255,
        ]

        for name in valid_names:
            result = BaseValidator.validate_project_name(name)
            assert result == name.strip()

    def test_validate_project_name_empty(self):
        """Тест валидации пустого названия проекта"""
        invalid_names = ["", "   ", None]

        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                BaseValidator.validate_project_name(name)

            assert "Название проекта не может быть пустым" in str(exc_info.value)

    def test_validate_project_name_too_long(self):
        """Тест валидации слишком длинного названия проекта"""
        long_name = "A" * 256

        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_project_name(long_name)

        assert "Название проекта слишком длинное" in str(exc_info.value)

    def test_validate_task_title_success(self):
        """Тест валидации корректного названия задачи"""
        valid_titles = [
            "Task title",
            "Задача 123",
            "Fix bug",
            "A" * 255,
        ]

        for title in valid_titles:
            result = BaseValidator.validate_task_title(title)
            assert result == title.strip()

    def test_validate_task_title_empty(self):
        """Тест валидации пустого названия задачи"""
        invalid_titles = ["", "   ", None]

        for title in invalid_titles:
            with pytest.raises(ValidationError) as exc_info:
                BaseValidator.validate_task_title(title)

            assert "Название задачи не может быть пустым" in str(exc_info.value)

    def test_validate_date_string_success(self):
        """Тест валидации корректной даты"""
        valid_dates = ["2024-01-01", "2024-12-31", "2023-02-28"]

        for date_str in valid_dates:
            result = BaseValidator.validate_date_string(date_str)
            assert result == date_str

    def test_validate_date_string_empty(self):
        """Тест валидации пустой даты"""
        result = BaseValidator.validate_date_string("")
        assert result == ""

        result = BaseValidator.validate_date_string(None)
        assert result is None

    def test_validate_date_string_invalid_format(self):
        """Тест валидации некорректного формата даты"""
        invalid_dates = ["01-01-2024", "2024/01/01", "2024-13-01", "invalid"]

        for date_str in invalid_dates:
            with pytest.raises(ValidationError) as exc_info:
                BaseValidator.validate_date_string(date_str)

            assert "Некорректный формат даты" in str(exc_info.value)

    def test_validate_date_string_custom_field(self):
        """Тест валидации даты с именем поля"""
        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_date_string("invalid", "start_date")

        assert "start_date" in str(exc_info.value)

    def test_validate_positive_integer_success(self):
        """Тест валидации положительного числа"""
        result = BaseValidator.validate_positive_integer(5, "test_field")
        assert result == 5

        result = BaseValidator.validate_positive_integer(0, "test_field")
        assert result == 0

        result = BaseValidator.validate_positive_integer(None, "test_field")
        assert result is None

    def test_validate_positive_integer_negative(self):
        """Тест валидации отрицательного числа"""
        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_positive_integer(-5, "test_field")

        assert "test_field должно быть положительным числом" in str(exc_info.value)
        assert exc_info.value.details["field"] == "test_field"

    def test_validate_story_point_success(self):
        """Тест валидации корректного Story Point"""
        valid_points = ["1", "2", "3", "5", "8", "13", "21", "unknown"]

        for point in valid_points:
            result = BaseValidator.validate_story_point(point)
            assert result == point

    def test_validate_story_point_invalid(self):
        """Тест валидации некорректного Story Point"""
        invalid_points = ["4", "6", "7", "9", "10", "invalid", ""]

        for point in invalid_points:
            with pytest.raises(ValidationError) as exc_info:
                BaseValidator.validate_story_point(point)

            assert "Story Point должен быть одним из" in str(exc_info.value)
            assert exc_info.value.details["field"] == "story_point"


class TestSprintValidator:
    """Тесты валидатора спринтов"""

    @pytest.mark.asyncio
    async def test_validate_sprint_dates_success(self):
        """Тест валидации корректных дат спринта"""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 15)

        # Не должно вызывать исключений
        await SprintValidator.validate_sprint_dates(start_date, end_date)

    @pytest.mark.asyncio
    async def test_validate_sprint_dates_invalid_order(self):
        """Тест валидации дат в неправильном порядке"""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 1)

        with pytest.raises(ValidationError) as exc_info:
            await SprintValidator.validate_sprint_dates(start_date, end_date)

        assert "Дата начала должна быть раньше даты окончания" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_sprint_dates_too_long(self):
        """Тест валидации слишком длинного спринта"""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 2, 1)  # 31 день

        with pytest.raises(ValidationError) as exc_info:
            await SprintValidator.validate_sprint_dates(start_date, end_date)

        assert "Спринт не может быть длиннее 4 недель" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_sprint_dates_exactly_4_weeks(self):
        """Тест валидации спринта ровно в 4 недели"""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 29)  # 28 дней

        # Не должно вызывать исключений
        await SprintValidator.validate_sprint_dates(start_date, end_date)


class TestCommentValidator:
    """Тесты валидатора комментариев"""

    def test_validate_comment_content_success(self):
        """Тест валидации корректного комментария"""
        valid_contents = [
            "This is a comment",
            "Комментарий на русском",
            "A" * 10000,
        ]

        for content in valid_contents:
            result = CommentValidator.validate_comment_content(content)
            assert result == content.strip()

    def test_validate_comment_content_empty(self):
        """Тест валидации пустого комментария"""
        invalid_contents = ["", "   ", None]

        for content in invalid_contents:
            with pytest.raises(ValidationError) as exc_info:
                CommentValidator.validate_comment_content(content)

            assert "Содержание комментария не может быть пустым" in str(exc_info.value)

    def test_validate_comment_content_too_long(self):
        """Тест валидации слишком длинного комментария"""
        long_content = "A" * 10001

        with pytest.raises(ValidationError) as exc_info:
            CommentValidator.validate_comment_content(long_content)

        assert "Комментарий слишком длинный" in str(exc_info.value)


class TestProjectTaskValidator:
    """Тесты композитного валидатора проектов и задач"""

    @pytest.mark.asyncio
    async def test_validate_bulk_task_operations_empty_list(self):
        """Тест валидации пустого списка задач"""
        with pytest.raises(ValidationError) as exc_info:
            await ProjectTaskValidator.validate_bulk_task_operations([], "user_id")

        assert "Список задач не может быть пустым" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_bulk_task_operations_too_many(self):
        """Тест валидации слишком большого списка задач"""
        task_ids = [str(uuid4()) for _ in range(101)]

        with pytest.raises(ValidationError) as exc_info:
            await ProjectTaskValidator.validate_bulk_task_operations(
                task_ids, "user_id"
            )

        assert "Нельзя обрабатывать более 100 задач" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_bulk_task_operations_max_allowed(self):
        """Тест валидации максимального разрешенного количества задач"""
        task_ids = [str(uuid4()) for _ in range(100)]
        user_id = str(uuid4())  # Используем валидный UUID

        # Должно пройти без исключений (но упадет на валидации доступа к задачам)
        with pytest.raises(
            NotFoundError
        ):  # Ожидаемая ошибка, т.к. задачи не существуют
            await ProjectTaskValidator.validate_bulk_task_operations(task_ids, user_id)


class TestValidatorEdgeCases:
    """Тесты граничных случаев валидаторов"""

    def test_email_case_insensitive(self):
        """Тест приведения email к нижнему регистру"""
        email = "Test@EXAMPLE.COM"
        result = BaseValidator.validate_email(email)
        assert result == "test@example.com"

    def test_username_with_underscore_and_dash(self):
        """Тест username с подчеркиваниями и дефисами"""
        valid_usernames = ["test_user", "test-user", "user_123", "123-user"]

        for username in valid_usernames:
            result = BaseValidator.validate_username(username)
            assert result == username

    def test_password_complexity_edge_cases(self):
        """Тест граничных случаев сложности пароля"""
        # Минимально валидный пароль
        result = BaseValidator.validate_password("a1bbbbbb")
        assert result == "a1bbbbbb"

        # Максимально валидный пароль
        max_password = "A" * 50 + "1" * 50  # 100 символов
        result = BaseValidator.validate_password(max_password)
        assert result == max_password

    def test_project_name_whitespace_handling(self):
        """Тест обработки пробелов в названии проекта"""
        name = "  My Project  "
        result = BaseValidator.validate_project_name(name)
        assert result == "My Project"

    def test_story_point_all_valid_values(self):
        """Тест всех допустимых значений Story Point"""
        valid_points = ["1", "2", "3", "5", "8", "13", "21", "unknown"]

        for point in valid_points:
            result = BaseValidator.validate_story_point(point)
            assert result == point

    @pytest.mark.asyncio
    async def test_sprint_dates_edge_cases(self):
        """Тест граничных случаев дат спринта"""
        # Минимально допустимая длительность (1 день)
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 2)

        await SprintValidator.validate_sprint_dates(start_date, end_date)

        # Максимально допустимая длительность (28 дней)
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 29)

        await SprintValidator.validate_sprint_dates(start_date, end_date)

    def test_comment_content_whitespace_handling(self):
        """Тест обработки пробелов в комментарии"""
        content = "  This is a comment  "
        result = CommentValidator.validate_comment_content(content)
        assert result == "This is a comment"

    def test_uuid_validation_with_real_uuid(self):
        """Тест валидации с реальными UUID"""
        import uuid

        # UUID v4
        uuid_v4 = str(uuid.uuid4())
        result = BaseValidator.validate_uuid(uuid_v4)
        assert result == uuid_v4

        # UUID v1
        uuid_v1 = str(uuid.uuid1())
        result = BaseValidator.validate_uuid(uuid_v1)
        assert result == uuid_v1

    def test_date_string_parsing_edge_cases(self):
        """Тест граничных случаев парсинга даты"""
        # Високосный год
        result = BaseValidator.validate_date_string("2024-02-29")
        assert result == "2024-02-29"

        # Невисокосный год (должна быть ошибка)
        with pytest.raises(ValidationError):
            BaseValidator.validate_date_string("2023-02-29")

    def test_positive_integer_zero_value(self):
        """Тест валидации нулевого значения"""
        result = BaseValidator.validate_positive_integer(0, "test")
        assert result == 0

    def test_field_names_in_error_messages(self):
        """Тест имен полей в сообщениях об ошибках"""
        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_uuid("invalid", "custom_field")

        assert exc_info.value.details["field"] == "custom_field"
        assert "custom_field" in str(exc_info.value)
