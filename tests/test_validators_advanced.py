"""
Продвинутые тесты для валидаторов - охват сложных сценариев и database-валидаторов
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.exceptions import (
    BusinessLogicError,
    NotFoundError,
    PermissionError,
    ValidationError,
)
from app.validators import (
    BaseValidator,
    CommentValidator,
    ProjectValidator,
    SprintValidator,
    TaskValidator,
    UserValidator,
)


class TestProjectValidatorAdvanced:
    """Продвинутые тесты валидатора проектов"""

    @pytest.mark.asyncio
    async def test_validate_project_exists_success(self):
        """Тест успешной проверки существования проекта"""
        project_id = str(uuid4())

        # Мокаем базу данных
        mock_project = AsyncMock()
        mock_project.id = project_id

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_session.get.return_value = mock_project
            mock_context.return_value.__aenter__.return_value = mock_session

            result = await ProjectValidator.validate_project_exists(project_id)

            assert result == mock_project
            mock_session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_project_exists_not_found(self):
        """Тест проверки несуществующего проекта"""
        project_id = str(uuid4())

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_session.get.return_value = None
            mock_context.return_value.__aenter__.return_value = mock_session

            with pytest.raises(NotFoundError) as exc_info:
                await ProjectValidator.validate_project_exists(project_id)

            assert "Проект не найден" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_project_access_success(self):
        """Тест успешной проверки доступа к проекту"""
        project_id = str(uuid4())
        user_id = str(uuid4())

        # Мокаем проект с участниками
        mock_project = MagicMock()
        mock_project.id = project_id

        mock_member = MagicMock()
        mock_member.user_id = user_id
        mock_member.is_active = True
        mock_member.can_edit_tasks = True
        mock_member.role = "member"

        mock_project.members = [mock_member]

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            # Создаем mock_result который будет возвращать проект
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_project
            # session.execute асинхронный, должен возвращать корутину с mock_result
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_context.return_value.__aenter__.return_value = mock_session

            result = await ProjectValidator.validate_project_access(
                project_id, user_id, can_edit=True
            )

            assert result == mock_project

    @pytest.mark.asyncio
    async def test_validate_project_access_no_member(self):
        """Тест проверки доступа для неучастника проекта"""
        project_id = str(uuid4())
        user_id = str(uuid4())

        mock_project = MagicMock()  # Используем MagicMock вместо AsyncMock
        mock_project.id = project_id
        mock_project.members = []  # Нет участников

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_result = MagicMock()  # Используем MagicMock для результата
            mock_result.scalar_one_or_none.return_value = mock_project
            mock_session.execute.return_value = mock_result
            mock_context.return_value.__aenter__.return_value = mock_session

            with pytest.raises(PermissionError) as exc_info:
                await ProjectValidator.validate_project_access(project_id, user_id)

            assert "доступ к проекту" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_project_access_owner_required(self):
        """Тест проверки доступа с требованием владельца"""
        project_id = str(uuid4())
        user_id = str(uuid4())

        mock_project = MagicMock()  # Используем MagicMock вместо AsyncMock
        mock_project.id = project_id

        mock_member = MagicMock()  # Используем MagicMock вместо AsyncMock
        mock_member.user_id = user_id
        mock_member.is_active = True
        mock_member.role = "member"  # Не владелец

        mock_project.members = [mock_member]

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_result = MagicMock()  # Используем MagicMock для результата
            mock_result.scalar_one_or_none.return_value = mock_project
            mock_session.execute.return_value = mock_result
            mock_context.return_value.__aenter__.return_value = mock_session

            with pytest.raises(PermissionError) as exc_info:
                await ProjectValidator.validate_project_access(
                    project_id, user_id, must_be_owner=True
                )

            assert "управление проектом" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_member_limit_exceeded(self):
        """Тест проверки лимита участников"""
        project_id = str(uuid4())

        mock_project = AsyncMock()
        mock_project.member_count = 10
        mock_project.max_members = 10
        mock_project.is_at_member_limit = True

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_session.get.return_value = mock_project
            mock_context.return_value.__aenter__.return_value = mock_session

            with pytest.raises(BusinessLogicError) as exc_info:
                await ProjectValidator.validate_member_limit(project_id)

            assert "MEMBER_LIMIT_EXCEEDED" in str(exc_info.value.code)

    @pytest.mark.asyncio
    async def test_validate_user_not_member_already_member(self):
        """Тест проверки пользователя, который уже является участником"""
        project_id = str(uuid4())
        user_id = str(uuid4())

        mock_member = AsyncMock()

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_result = MagicMock()  # Не AsyncMock!
            mock_result.scalar_one_or_none.return_value = mock_member
            mock_session.execute.return_value = mock_result
            mock_context.return_value.__aenter__.return_value = mock_session

            with pytest.raises(BusinessLogicError) as exc_info:
                await ProjectValidator.validate_user_not_member(project_id, user_id)

            assert "USER_ALREADY_MEMBER" in str(exc_info.value.code)


class TestTaskValidatorAdvanced:
    """Продвинутые тесты валидатора задач"""

    @pytest.mark.asyncio
    async def test_validate_task_exists_success(self):
        """Тест успешной проверки существования задачи"""
        task_id = str(uuid4())

        mock_task = AsyncMock()
        mock_task.id = task_id

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_session.get.return_value = mock_task
            mock_context.return_value.__aenter__.return_value = mock_session

            result = await TaskValidator.validate_task_exists(task_id)

            assert result == mock_task

    @pytest.mark.asyncio
    async def test_validate_task_access_success(self):
        """Тест успешной проверки доступа к задаче"""
        task_id = str(uuid4())
        user_id = str(uuid4())

        # Мокаем сложную структуру: задача -> проект -> участники
        mock_member = MagicMock()  # Используем MagicMock вместо AsyncMock
        mock_member.user_id = user_id
        mock_member.is_active = True
        mock_member.can_edit_tasks = True

        mock_project = MagicMock()  # Используем MagicMock вместо AsyncMock
        mock_project.members = [mock_member]

        mock_task = MagicMock()  # Используем MagicMock вместо AsyncMock
        mock_task.id = task_id
        mock_task.project = mock_project

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_result = MagicMock()  # Используем MagicMock для результата
            mock_result.scalar_one_or_none.return_value = mock_task
            mock_session.execute.return_value = mock_result
            mock_context.return_value.__aenter__.return_value = mock_session

            result = await TaskValidator.validate_task_access(
                task_id, user_id, can_edit=True
            )

            assert result == mock_task

    @pytest.mark.asyncio
    async def test_validate_task_transition_valid(self):
        """Тест валидации допустимого перехода статуса"""
        from app.models.task import TaskStatus

        mock_task = AsyncMock()
        mock_task.status = TaskStatus.TODO

        # Допустимый переход
        await TaskValidator.validate_task_transition(mock_task, TaskStatus.IN_PROGRESS)

        # Не должно вызывать исключений

    @pytest.mark.asyncio
    async def test_validate_task_transition_invalid(self):
        """Тест валидации недопустимого перехода статуса"""
        from app.models.task import TaskStatus

        mock_task = AsyncMock()
        mock_task.status = TaskStatus.BLOCKED

        # Недопустимый переход (из BLOCKED в DONE не должно быть разрешено)
        with pytest.raises(BusinessLogicError) as exc_info:
            await TaskValidator.validate_task_transition(mock_task, TaskStatus.DONE)

        assert "INVALID_STATUS_TRANSITION" in str(exc_info.value.code)

    @pytest.mark.asyncio
    async def test_validate_task_hierarchy_self_parent(self):
        """Тест проверки иерархии - задача не может быть родителем самой себя"""
        task_id = str(uuid4())

        with pytest.raises(BusinessLogicError) as exc_info:
            await TaskValidator.validate_task_hierarchy(task_id, task_id)

        assert "SELF_PARENT" in str(exc_info.value.code)

    @pytest.mark.asyncio
    async def test_validate_task_hierarchy_valid(self):
        """Тест проверки иерархии - валидный случай"""
        task_id = str(uuid4())
        parent_id = str(uuid4())

        # Не должно вызывать исключений
        await TaskValidator.validate_task_hierarchy(task_id, parent_id)

    @pytest.mark.asyncio
    async def test_validate_task_deletion_with_subtasks(self):
        """Тест проверки удаления задачи с подзадачами"""
        task_id = str(uuid4())

        mock_task = AsyncMock()
        mock_task.has_subtasks = True

        with patch(
            "app.validators.TaskValidator.validate_task_exists"
        ) as mock_validate:
            mock_validate.return_value = mock_task

            with pytest.raises(BusinessLogicError) as exc_info:
                await TaskValidator.validate_task_deletion(task_id)

            assert "TaskHasSubtasksError" in str(type(exc_info.value).__name__)


class TestUserValidatorAdvanced:
    """Продвинутые тесты валидатора пользователей"""

    @pytest.mark.asyncio
    async def test_validate_user_exists_success(self):
        """Тест успешной проверки существования пользователя"""
        user_id = str(uuid4())

        mock_user = AsyncMock()
        mock_user.id = user_id

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_session.get.return_value = mock_user
            mock_context.return_value.__aenter__.return_value = mock_session

            result = await UserValidator.validate_user_exists(user_id)

            assert result == mock_user

    @pytest.mark.asyncio
    async def test_validate_user_unique_email_conflict(self):
        """Тест проверки уникальности email - конфликт"""
        email = "test@example.com"

        mock_user = MagicMock()  # Не AsyncMock!

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_result = MagicMock()  # Не AsyncMock!
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_session.execute.return_value = mock_result
            mock_context.return_value.__aenter__.return_value = mock_session

            with pytest.raises(Exception) as exc_info:  # UserAlreadyExistsError
                await UserValidator.validate_user_unique_email(email)

            assert "UserAlreadyExistsError" in str(type(exc_info.value).__name__)

    @pytest.mark.asyncio
    async def test_validate_user_unique_email_with_exclusion(self):
        """Тест проверки уникальности email с исключением"""
        email = "test@example.com"
        exclude_user_id = str(uuid4())

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_result = MagicMock()  # Не AsyncMock!
            mock_result.scalar_one_or_none.return_value = (
                None  # Нет других пользователей
            )
            mock_session.execute.return_value = mock_result
            mock_context.return_value.__aenter__.return_value = mock_session

            # Не должно вызывать исключений
            result = await UserValidator.validate_user_unique_email(
                email, exclude_user_id
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_validate_user_unique_username_conflict(self):
        """Тест проверки уникальности username - конфликт"""
        username = "testuser"

        mock_user = MagicMock()  # Не AsyncMock!

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_result = MagicMock()  # Не AsyncMock!
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_session.execute.return_value = mock_result
            mock_context.return_value.__aenter__.return_value = mock_session

            with pytest.raises(Exception) as exc_info:  # UserAlreadyExistsError
                await UserValidator.validate_user_unique_username(username)

            assert "UserAlreadyExistsError" in str(type(exc_info.value).__name__)

    @pytest.mark.asyncio
    async def test_validate_user_active_inactive(self):
        """Тест проверки активного пользователя - неактивный"""
        user_id = str(uuid4())

        mock_user = AsyncMock()
        mock_user.is_active = False

        with patch(
            "app.validators.UserValidator.validate_user_exists"
        ) as mock_validate:
            mock_validate.return_value = mock_user

            with pytest.raises(BusinessLogicError) as exc_info:
                await UserValidator.validate_user_active(user_id)

            assert "USER_INACTIVE" in str(exc_info.value.code)


class TestSprintValidatorAdvanced:
    """Продвинутые тесты валидатора спринтов"""

    @pytest.mark.asyncio
    async def test_validate_sprint_exists_success(self):
        """Тест успешной проверки существования спринта"""
        sprint_id = str(uuid4())

        mock_sprint = AsyncMock()
        mock_sprint.id = sprint_id

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_session.get.return_value = mock_sprint
            mock_context.return_value.__aenter__.return_value = mock_session

            result = await SprintValidator.validate_sprint_exists(sprint_id)

            assert result == mock_sprint

    @pytest.mark.asyncio
    async def test_validate_sprint_modification_active(self):
        """Тест проверки изменения активного спринта"""
        from app.models.sprint import SprintStatus

        mock_sprint = AsyncMock()
        mock_sprint.status = SprintStatus.ACTIVE
        mock_sprint.id = str(uuid4())

        with pytest.raises(BusinessLogicError) as exc_info:
            await SprintValidator.validate_sprint_modification(mock_sprint)

        assert "SprintAlreadyStartedError" in str(type(exc_info.value).__name__)

    @pytest.mark.asyncio
    async def test_validate_sprint_modification_planned(self):
        """Тест изменения планируемого спринта"""
        from app.models.sprint import SprintStatus

        mock_sprint = AsyncMock()
        mock_sprint.status = SprintStatus.PLANNING

        # Не должно вызывать исключений
        await SprintValidator.validate_sprint_modification(mock_sprint)


class TestCommentValidatorAdvanced:
    """Продвинутые тесты валидатора комментариев"""

    @pytest.mark.asyncio
    async def test_validate_comment_access_success(self):
        """Тест успешной проверки доступа к комментарию"""
        comment_id = str(uuid4())
        user_id = str(uuid4())

        # Мокаем сложную структуру: комментарий -> задача -> проект -> участники
        mock_member = MagicMock()  # Используем MagicMock вместо AsyncMock
        mock_member.user_id = user_id
        mock_member.is_active = True

        mock_project = MagicMock()  # Используем MagicMock вместо AsyncMock
        mock_project.members = [mock_member]

        mock_task = MagicMock()  # Используем MagicMock вместо AsyncMock
        mock_task.project = mock_project

        mock_comment = MagicMock()  # Используем MagicMock вместо AsyncMock
        mock_comment.id = comment_id
        mock_comment.task = mock_task
        mock_comment.author_id = str(uuid4())  # Другой автор

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_result = MagicMock()  # Используем MagicMock для результата
            mock_result.scalar_one_or_none.return_value = mock_comment
            mock_session.execute.return_value = mock_result
            mock_context.return_value.__aenter__.return_value = mock_session

            # Не должно вызывать исключений (доступ через проект)
            await CommentValidator.validate_comment_access(comment_id, user_id)

    @pytest.mark.asyncio
    async def test_validate_comment_access_author(self):
        """Тест доступа автора к комментарию"""
        comment_id = str(uuid4())
        user_id = str(uuid4())

        mock_comment = MagicMock()  # Используем MagicMock вместо AsyncMock
        mock_comment.id = comment_id
        mock_comment.author_id = user_id  # Автор комментария

        # Мокаем задачу и проект
        mock_task = MagicMock()  # Используем MagicMock вместо AsyncMock
        mock_project = MagicMock()  # Используем MagicMock вместо AsyncMock
        mock_project.members = []  # Не участник проекта

        mock_comment.task = mock_task
        mock_task.project = mock_project

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_result = MagicMock()  # Используем MagicMock для результата
            mock_result.scalar_one_or_none.return_value = mock_comment
            mock_session.execute.return_value = mock_result
            mock_context.return_value.__aenter__.return_value = mock_session

            # Не должно вызывать исключений (доступ как автор)
            await CommentValidator.validate_comment_access(comment_id, user_id)

    @pytest.mark.asyncio
    async def test_validate_comment_access_denied(self):
        """Тест отказа в доступе к комментарию"""
        comment_id = str(uuid4())
        user_id = str(uuid4())

        mock_comment = MagicMock()  # Не AsyncMock!
        mock_comment.id = comment_id
        mock_comment.author_id = str(uuid4())  # Другой автор

        # Мокаем задачу и проект без доступа
        mock_task = MagicMock()  # Не AsyncMock!
        mock_project = MagicMock()  # Не AsyncMock!
        mock_project.members = []  # Нет участников

        mock_comment.task = mock_task
        mock_task.project = mock_project

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_result = MagicMock()  # Не AsyncMock!
            mock_result.scalar_one_or_none.return_value = mock_comment
            mock_session.execute.return_value = mock_result
            mock_context.return_value.__aenter__.return_value = mock_session

            with pytest.raises(PermissionError) as exc_info:
                await CommentValidator.validate_comment_access(comment_id, user_id)

            assert "доступ к комментарию" in str(exc_info.value)


class TestValidatorErrorHandling:
    """Тесты обработки ошибок в валидаторах"""

    @pytest.mark.asyncio
    async def test_database_error_handling(self):
        """Тест обработки ошибок базы данных"""
        project_id = str(uuid4())

        with patch("app.validators.get_db_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_session.get.side_effect = Exception("Database connection failed")
            mock_context.return_value.__aenter__.return_value = mock_session

            with pytest.raises(Exception) as exc_info:
                await ProjectValidator.validate_project_exists(project_id)

            assert "Database connection failed" in str(exc_info.value)

    def test_validation_error_chaining(self):
        """Тест цепочки исключений валидации"""
        with pytest.raises(ValidationError) as exc_info:
            BaseValidator.validate_uuid("invalid-uuid")

        # Проверяем, что ошибка содержит исходную информацию
        assert exc_info.value.message
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_concurrent_validation(self):
        """Тест одновременной валидации"""
        import asyncio

        project_ids = [str(uuid4()) for _ in range(5)]

        async def validate_single(project_id):
            with patch("app.validators.get_db_session_context") as mock_context:
                mock_session = AsyncMock()
                mock_session.get.return_value = None
                mock_context.return_value.__aenter__.return_value = mock_session

                with pytest.raises(NotFoundError):
                    await ProjectValidator.validate_project_exists(project_id)

        # Запускаем несколько валидаций одновременно
        tasks = [validate_single(pid) for pid in project_ids]
        await asyncio.gather(*tasks, return_exceptions=True)
