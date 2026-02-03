"""
Тесты для валидаторов бизнес-правил
"""

from uuid import uuid4

import pytest

from app.exceptions import ValidationError
from app.validators import BaseValidator


class TestBaseValidator:
    """Тесты базового валидатора"""

    def test_validate_uuid_valid(self):
        """Валидация корректного UUID"""
        valid_uuid = str(uuid4())
        result = BaseValidator.validate_uuid(valid_uuid)
        assert result == valid_uuid

    def test_validate_uuid_invalid_format(self):
        """Валидация некорректного UUID"""
        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_uuid("invalid-uuid")

        assert "Некорректный формат ID" in str(exc_info.value)
        assert exc_info.value.details["field"] == "ID"

    def test_validate_uuid_custom_field_name(self):
        """Валидация UUID с кастомным именем поля"""
        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_uuid("invalid", "project_id")

        assert "project_id" in str(exc_info.value)
        assert exc_info.value.details["field"] == "project_id"

    def test_validate_email_valid(self):
        """Валидация корректного email"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "user123@test-domain.com",
        ]

        for email in valid_emails:
            result = BaseValidator.validate_email(email)
            assert result == email

    def test_validate_email_invalid_format(self):
        """Валидация некорректного формата email"""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user@.com",
            "test@.com",
            "a@b.c",  # слишком короткий домен
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError) as exc_info:
                BaseValidator.validate_email(email)

            assert "Некорректный формат email" in str(exc_info.value)
            assert exc_info.value.details["field"] == "email"

    def test_validate_email_too_long(self):
        """Валидация слишком длинного email"""
        long_email = "a" * 250 + "@example.com"  # 256 символов

        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_email(long_email)

        assert "Email слишком длинный" in str(exc_info.value)
        assert exc_info.value.details["field"] == "email"

    def test_validate_email_max_length(self):
        """Валидация email максимальной длины"""
        # @example.com = 12 символов
        # Email с 255 символами должен проходить
        max_email = "a" * 243 + "@example.com"  # 243 + 12 = 255

        result = BaseValidator.validate_email(max_email)
        assert result == max_email

        # Email с 256 символами должен падать
        too_long_email = "a" * 244 + "@example.com"  # 244 + 12 = 256

        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_email(too_long_email)

        assert "Email слишком длинный" in str(exc_info.value)
        assert exc_info.value.details["field"] == "email"


class TestValidatorIntegration:
    """Интеграционные тесты валидаторов"""

    def test_multiple_validations_success(self):
        """Успешная валидация нескольких полей"""
        uuid_str = str(uuid4())
        email = "test@example.com"

        validated_uuid = BaseValidator.validate_uuid(uuid_str)
        validated_email = BaseValidator.validate_email(email)

        assert validated_uuid == uuid_str
        assert validated_email == email

    def test_validation_chain_failure(self):
        """Цепочка валидации с ошибкой"""
        with pytest.raises(ValidationError):
            # Первая валидация пройдет, вторая упадет
            BaseValidator.validate_uuid(str(uuid4()))
            BaseValidator.validate_email("invalid-email")


class TestValidatorEdgeCases:
    """Тесты граничных случаев валидаторов"""

    def test_validate_uuid_empty_string(self):
        """Валидация пустой строки как UUID"""
        with pytest.raises(ValidationError):
            BaseValidator.validate_uuid("")

    def test_validate_uuid_none(self):
        """Валидация None как UUID"""
        with pytest.raises(TypeError):
            BaseValidator.validate_uuid(None)  # type: ignore

    def test_validate_email_none(self):
        """Валидация None как email"""
        with pytest.raises(TypeError):
            BaseValidator.validate_email(None)  # type: ignore

    def test_validate_email_whitespace(self):
        """Валидация email с пробелами"""
        invalid_emails = [
            " test@example.com",  # ведущий пробел
            "test@example.com ",  # завершающий пробел
            "test @example.com",  # пробел в середине
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError):
                BaseValidator.validate_email(email)

    def test_validate_email_special_characters(self):
        """Валидация email с специальными символами"""
        valid_special_emails = [
            "test.email+tag@example.com",
            "user_name@example-domain.com",
            "test123@example.co.uk",
        ]

        for email in valid_special_emails:
            result = BaseValidator.validate_email(email)
            assert result == email

    def test_validate_uuid_different_versions(self):
        """Валидация UUID разных версий"""
        import uuid

        uuids = [
            str(uuid.uuid1()),  # Version 1
            str(uuid.uuid4()),  # Version 4
        ]

        for uuid_str in uuids:
            result = BaseValidator.validate_uuid(uuid_str)
            assert result == uuid_str


class TestValidatorPerformance:
    """Тесты производительности валидаторов"""

    def test_validate_uuid_performance(self):
        """Тест производительности валидации UUID"""
        import time

        uuid_str = str(uuid4())
        iterations = 1000

        start_time = time.time()
        for _ in range(iterations):
            BaseValidator.validate_uuid(uuid_str)
        end_time = time.time()

        # Проверяем, что валидация выполняется достаточно быстро
        execution_time = end_time - start_time
        assert execution_time < 0.1  # Менее 100ms для 1000 итераций

    def test_validate_email_performance(self):
        """Тест производительности валидации email"""
        import time

        email = "test@example.com"
        iterations = 1000

        start_time = time.time()
        for _ in range(iterations):
            BaseValidator.validate_email(email)
        end_time = time.time()

        # Проверяем, что валидация выполняется достаточно быстро
        execution_time = end_time - start_time
        assert execution_time < 0.1  # Менее 100ms для 1000 итерациций
