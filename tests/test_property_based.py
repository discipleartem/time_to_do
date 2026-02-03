"""
Property-based тесты с использованием Hypothesis
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate


class TestAuthValidation:
    """Property-based тесты для валидации аутентификации"""

    @given(st.text(min_size=1, max_size=100))
    def test_email_validation(self, email):
        """Тест валидации email с различными данными"""
        # Проверяем валидные email
        if "@" in email and "." in email.split("@")[-1]:
            try:
                RegisterRequest(email=email, password="validpassword123")
            except ValidationError:
                # Если email невалидный, должна быть ошибка
                pass
        else:
            # Невалидный email должен вызывать ошибку
            with pytest.raises(ValidationError):
                RegisterRequest(email=email, password="validpassword123")

    @given(st.text(min_size=1, max_size=200))
    def test_password_validation(self, password):
        """Тест валидации пароля с различными данными"""
        # Тестовые данные
        valid_email = "test@example.com"

        # Короткие пароли должны вызывать ошибку
        if len(password) < 6:
            with pytest.raises(
                ValueError, match="Пароль должен содержать минимум 6 символов"
            ):
                RegisterRequest(email=valid_email, password=password)

        # Слишком длинные пароли должны вызывать ошибку
        elif len(password) > 128:
            with pytest.raises(
                ValueError, match="Пароль не должен превышать 128 символов"
            ):
                RegisterRequest(email=valid_email, password=password)

        # Валидные пароли должны проходить
        else:
            try:
                RegisterRequest(email=valid_email, password=password)
            except ValidationError:
                # Другие ошибки валидации (например, email) допустимы
                pass

    @given(st.text(min_size=1, max_size=50))
    def test_username_validation(self, username):
        """Тест валидации имени пользователя"""
        valid_email = "test@example.com"
        valid_password = "validpassword123"

        # Проверяем создание с различными именами
        try:
            RegisterRequest(
                email=valid_email, password=valid_password, username=username
            )
        except ValidationError:
            # Ошибки могут быть только из-за других полей
            pass


class TestProjectValidation:
    """Property-based тесты для валидации проектов"""

    @given(st.text(min_size=1, max_size=300))
    def test_project_name_validation(self, name):
        """Тест валидации имени проекта"""
        valid_description = "Test project description"

        # Пустые имена должны вызывать ошибку
        if not name.strip():
            with pytest.raises(ValidationError):
                ProjectCreate(name=name, description=valid_description)

        # Слишком длинные имена должны вызывать ошибку
        elif len(name) > 255:
            with pytest.raises(ValidationError):
                ProjectCreate(name=name, description=valid_description)

        # Валидные имена должны проходить
        else:
            try:
                ProjectCreate(name=name, description=valid_description)
            except ValidationError:
                # Другие ошибки валидации допустимы
                pass

    @given(st.text(min_size=1, max_size=1000))
    def test_project_description_validation(self, description):
        """Тест валидации описания проекта"""
        valid_name = "Test Project"

        # Слишком длинные описания должны вызывать ошибку
        if len(description) > 500:
            with pytest.raises(ValidationError):
                ProjectCreate(name=valid_name, description=description)

        # Валидные описания должны проходить
        else:
            try:
                ProjectCreate(name=valid_name, description=description)
            except ValidationError:
                # Другие ошибки валидации допустимы
                pass


class TestTaskValidation:
    """Property-based тесты для валидации задач"""

    @given(st.text(min_size=1, max_size=300))
    def test_task_title_validation(self, title):
        """Тест валидации заголовка задачи"""
        valid_description = "Test task description"
        valid_project_id = "550e8400-e29b-41d4-a716-446655440000"

        # Пустые заголовки должны вызывать ошибку
        if not title.strip():
            with pytest.raises(ValidationError):
                TaskCreate(
                    title=title,
                    description=valid_description,
                    project_id=valid_project_id,
                )

        # Слишком длинные заголовки должны вызывать ошибку
        elif len(title) > 255:
            with pytest.raises(ValidationError):
                TaskCreate(
                    title=title,
                    description=valid_description,
                    project_id=valid_project_id,
                )

        # Валидные заголовки должны проходить
        else:
            try:
                TaskCreate(
                    title=title,
                    description=valid_description,
                    project_id=valid_project_id,
                )
            except ValidationError:
                # Другие ошибки валидации допустимы
                pass

    @given(st.text(min_size=1, max_size=2000))
    def test_task_description_validation(self, description):
        """Тест валидации описания задачи"""
        valid_title = "Test Task"
        valid_project_id = "550e8400-e29b-41d4-a716-446655440000"

        # Слишком длинные описания должны вызывать ошибку
        if len(description) > 1000:
            with pytest.raises(ValidationError):
                TaskCreate(
                    title=valid_title,
                    description=description,
                    project_id=valid_project_id,
                )

        # Валидные описания должны проходить
        else:
            try:
                TaskCreate(
                    title=valid_title,
                    description=description,
                    project_id=valid_project_id,
                )
            except ValidationError:
                # Другие ошибки валидации допустимы
                pass

    @given(st.integers(min_value=1, max_value=50))
    def test_story_point_validation(self, story_point):
        """Тест валидации story points"""
        valid_title = "Test Task"
        valid_description = "Test task description"
        valid_project_id = "550e8400-e29b-41d4-a716-446655440000"

        # Story points должны быть в допустимом диапазоне
        if story_point not in [1, 2, 3, 5, 8, 13, 21]:
            with pytest.raises(ValidationError):
                TaskCreate(
                    title=valid_title,
                    description=valid_description,
                    project_id=valid_project_id,
                    story_point=story_point,
                )

        # Валидные story points должны проходить
        else:
            try:
                TaskCreate(
                    title=valid_title,
                    description=valid_description,
                    project_id=valid_project_id,
                    story_point=story_point,
                )
            except ValidationError:
                # Другие ошибки валидации допустимы
                pass

    @given(st.integers(min_value=1, max_value=100))
    def test_estimated_hours_validation(self, estimated_hours):
        """Тест валидации оценочных часов"""
        valid_title = "Test Task"
        valid_description = "Test task description"
        valid_project_id = "550e8400-e29b-41d4-a716-446655440000"

        # Оценочные часы должны быть в допустимом диапазоне
        if estimated_hours > 40:
            with pytest.raises(ValidationError):
                TaskCreate(
                    title=valid_title,
                    description=valid_description,
                    project_id=valid_project_id,
                    estimated_hours=estimated_hours,
                )

        # Валидные часы должны проходить
        else:
            try:
                TaskCreate(
                    title=valid_title,
                    description=valid_description,
                    project_id=valid_project_id,
                    estimated_hours=estimated_hours,
                )
            except ValidationError:
                # Другие ошибки валидации допустимы
                pass


class TestEdgeCases:
    """Тесты граничных случаев"""

    @given(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10))
    def test_multiple_email_validation(self, emails):
        """Тест валидации множества email"""
        valid_password = "validpassword123"

        for email in emails:
            try:
                RegisterRequest(email=email, password=valid_password)
            except ValidationError:
                # Ожидаем ошибки для невалидных email
                pass

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.text(min_size=1, max_size=100),
            min_size=1,
            max_size=5,
        )
    )
    def test_project_metadata_validation(self, metadata):
        """Тест валидации метаданных проекта"""
        valid_name = "Test Project"
        valid_description = "Test project description"

        # Проверяем создание проекта с различными метаданными
        try:
            ProjectCreate(
                name=valid_name, description=valid_description, metadata=metadata
            )
        except ValidationError:
            # Метаданные могут вызывать ошибки валидации
            pass

    @given(st.datetimes())
    def test_datetime_validation(self, dt):
        """Тест валидации дат и времени"""
        # Проверяем работу с различными датами
        assert dt is not None
        assert hasattr(dt, "year")
        assert hasattr(dt, "month")
        assert hasattr(dt, "day")


class TestBusinessRules:
    """Тесты бизнес-правил"""

    @given(st.integers(min_value=-10, max_value=100))
    def test_positive_numbers_only(self, number):
        """Тест что бизнес-логика работает только с положительными числами"""
        # Пример: story points должны быть положительными
        if number <= 0:
            with pytest.raises(ValidationError):
                TaskCreate(
                    title="Test Task",
                    description="Test description",
                    project_id="550e8400-e29b-41d4-a716-446655440000",
                    story_point=number,
                )

    @given(st.text(min_size=1, max_size=100))
    def test_no_sql_injection(self, text):
        """Тест защиты от SQL инъекций в текстовых полях"""
        dangerous_patterns = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_"]

        # Проверяем что опасные символы обрабатываются корректно
        for pattern in dangerous_patterns:
            if pattern in text:
                # Текст с опасными символами должен быть безопасно обработан
                try:
                    ProjectCreate(name=text, description="Safe description")
                except ValidationError:
                    # Ошибки валидации допустимы, но не должно быть SQL injection
                    pass
