"""
Валидаторы бизнес-правил
"""

import re
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session_context
from app.exceptions import (
    BusinessLogicError,
    NotFoundError,
    PermissionError,
    ValidationError,
)
from app.models.project import Project, ProjectMember, ProjectRole
from app.models.sprint import Sprint, SprintStatus
from app.models.task import Task, TaskStatus
from app.models.user import User


class BaseValidator:
    """Базовый класс валидаторов"""

    @staticmethod
    def validate_uuid(uuid_string: str, field_name: str = "ID") -> str:
        """Валидация UUID"""
        try:
            UUID(uuid_string)
            return uuid_string
        except ValueError as err:
            raise ValidationError(
                f"Некорректный формат {field_name}", field_name
            ) from err

    @staticmethod
    def validate_email(email: str) -> str:
        """Валидация email"""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_pattern, email):
            raise ValidationError("Некорректный формат email", "email")

        if len(email) > 255:
            raise ValidationError(
                "Email слишком длинный (максимум 255 символов)", "email"
            )

        return email.lower()

    @staticmethod
    def validate_username(username: str) -> str:
        """Валидация username"""
        if not username:
            return username

        username_pattern = r"^[a-zA-Z0-9_-]{3,30}$"

        if not re.match(username_pattern, username):
            raise ValidationError(
                "Username должен содержать только буквы, цифры, _ и - (3-30 символов)",
                "username",
            )

        return username

    @staticmethod
    def validate_password(password: str) -> str:
        """Валидация пароля"""
        if len(password) < 8:
            raise ValidationError(
                "Пароль должен содержать минимум 8 символов", "password"
            )

        if len(password) > 100:
            raise ValidationError(
                "Пароль слишком длинный (максимум 100 символов)", "password"
            )

        # Проверка на сложность (хотя бы одна буква и одна цифра)
        if not re.search(r"[a-zA-Z]", password):
            raise ValidationError(
                "Пароль должен содержать хотя бы одну букву", "password"
            )

        if not re.search(r"\d", password):
            raise ValidationError(
                "Пароль должен содержать хотя бы одну цифру", "password"
            )

        return password

    @staticmethod
    def validate_project_name(name: str) -> str:
        """Валидация названия проекта"""
        if not name or not name.strip():
            raise ValidationError("Название проекта не может быть пустым", "name")

        if len(name.strip()) > 255:
            raise ValidationError(
                "Название проекта слишком длинное (максимум 255 символов)", "name"
            )

        return name.strip()

    @staticmethod
    def validate_task_title(title: str) -> str:
        """Валидация названия задачи"""
        if not title or not title.strip():
            raise ValidationError("Название задачи не может быть пустым", "title")

        if len(title.strip()) > 255:
            raise ValidationError(
                "Название задачи слишком длинное (максимум 255 символов)", "title"
            )

        return title.strip()

    @staticmethod
    def validate_date_string(date_string: str, field_name: str = "date") -> str:
        """Валидация строки даты в формате YYYY-MM-DD"""
        if not date_string:
            return date_string

        try:
            datetime.strptime(date_string, "%Y-%m-%d")
            return date_string
        except ValueError as err:
            raise ValidationError(
                f"Некорректный формат даты для поля {field_name}. Ожидается YYYY-MM-DD",
                field_name,
            ) from err

    @staticmethod
    def validate_positive_integer(value: int, field_name: str) -> int:
        """Валидация положительного целого числа"""
        if value is not None and value < 0:
            raise ValidationError(
                f"{field_name} должно быть положительным числом", field_name
            )

        return value

    @staticmethod
    def validate_story_point(story_point: str) -> str:
        """Валидация Story Point"""
        valid_points = ["1", "2", "3", "5", "8", "13", "21", "unknown"]

        if story_point not in valid_points:
            raise ValidationError(
                f"Story Point должен быть одним из: {', '.join(valid_points)}",
                "story_point",
            )

        return story_point


class ProjectValidator(BaseValidator):
    """Валидатор для проектов"""

    @staticmethod
    async def validate_project_exists(project_id: str) -> Project:
        """Проверка существования проекта"""
        BaseValidator.validate_uuid(project_id, "project_id")

        async with get_db_session_context() as session:
            project = await session.get(Project, project_id)

            if not project:
                raise NotFoundError("Проект", project_id)

            return project

    @staticmethod
    async def validate_project_access(
        project_id: str,
        user_id: str,
        can_edit: bool = False,
        must_be_owner: bool = False,
    ) -> Project:
        """Проверка доступа к проекту"""
        BaseValidator.validate_uuid(project_id, "project_id")
        BaseValidator.validate_uuid(user_id, "user_id")

        async with get_db_session_context() as session:
            # Получаем проект с участниками
            result = await session.execute(
                select(Project)
                .options(selectinload(Project.members))
                .where(Project.id == project_id)
            )

            project = result.scalar_one_or_none()

            if not project:
                raise NotFoundError("Проект", project_id)

            # Ищем участника
            member = None
            for m in project.members:
                if m.user_id == user_id and m.is_active:
                    member = m
                    break

            if not member:
                raise PermissionError("доступ к проекту", "проект")

            if must_be_owner and member.role != ProjectRole.OWNER:
                raise PermissionError("управление проектом", "проект")

            if can_edit and not member.can_edit_tasks:
                raise PermissionError("редактирование задач", "проект")

            return project

    @staticmethod
    async def validate_member_limit(project_id: str) -> None:
        """Проверка лимита участников проекта"""
        async with get_db_session_context() as session:
            project = await session.get(Project, project_id)

            if not project:
                raise NotFoundError("Проект", project_id)

            if project.is_at_member_limit:
                from app.exceptions import ProjectMemberLimitError

                raise ProjectMemberLimitError(
                    project.member_count, int(project.max_members)
                )

    @staticmethod
    async def validate_user_not_member(project_id: str, user_id: str) -> None:
        """Проверка, что пользователь не является участником проекта"""
        async with get_db_session_context() as session:
            existing_member = await session.execute(
                select(ProjectMember).where(
                    and_(
                        ProjectMember.project_id == project_id,
                        ProjectMember.user_id == user_id,
                    )
                )
            )

            if existing_member.scalar_one_or_none():
                raise BusinessLogicError(
                    "Пользователь уже является участником проекта",
                    code="USER_ALREADY_MEMBER",
                )


class TaskValidator(BaseValidator):
    """Валидатор для задач"""

    @staticmethod
    async def validate_task_exists(task_id: str) -> Task:
        """Проверка существования задачи"""
        BaseValidator.validate_uuid(task_id, "task_id")

        async with get_db_session_context() as session:
            task = await session.get(Task, task_id)

            if not task:
                raise NotFoundError("Задача", task_id)

            return task

    @staticmethod
    async def validate_task_access(
        task_id: str, user_id: str, can_edit: bool = False
    ) -> Task:
        """Проверка доступа к задаче"""
        BaseValidator.validate_uuid(task_id, "task_id")
        BaseValidator.validate_uuid(user_id, "user_id")

        async with get_db_session_context() as session:
            # Получаем задачу с проектом и участниками
            result = await session.execute(
                select(Task)
                .options(
                    selectinload(Task.project).selectinload(Project.members),
                    selectinload(Task.assignee),
                    selectinload(Task.creator),
                )
                .where(Task.id == task_id)
            )

            task = result.scalar_one_or_none()

            if not task:
                raise NotFoundError("Задача", task_id)

            # Проверяем доступ к проекту
            member = None
            for m in task.project.members:
                if m.user_id == user_id and m.is_active:
                    member = m
                    break

            if not member:
                raise PermissionError("доступ к задаче", "задача")

            if can_edit and not member.can_edit_tasks:
                raise PermissionError("редактирование задачи", "задача")

            return task

    @staticmethod
    async def validate_task_transition(task: Task, new_status: TaskStatus) -> None:
        """Проверка допустимости перехода статуса задачи"""
        # Определяем допустимые переходы
        allowed_transitions = {
            TaskStatus.TODO: [
                TaskStatus.IN_PROGRESS,
                TaskStatus.DONE,
                TaskStatus.BLOCKED,
            ],
            TaskStatus.IN_PROGRESS: [
                TaskStatus.TODO,
                TaskStatus.IN_REVIEW,
                TaskStatus.DONE,
                TaskStatus.BLOCKED,
            ],
            TaskStatus.IN_REVIEW: [
                TaskStatus.IN_PROGRESS,
                TaskStatus.DONE,
                TaskStatus.BLOCKED,
            ],
            TaskStatus.DONE: [
                TaskStatus.TODO,
                TaskStatus.IN_PROGRESS,
                TaskStatus.BLOCKED,
            ],
            TaskStatus.BLOCKED: [TaskStatus.TODO, TaskStatus.IN_PROGRESS],
        }

        if new_status not in allowed_transitions.get(task.status, []):  # type: ignore
            raise BusinessLogicError(
                f"Недопустимый переход статуса: {task.status} -> {new_status}",
                code="INVALID_STATUS_TRANSITION",
            )

    @staticmethod
    async def validate_task_hierarchy(task_id: str, parent_task_id: str | None) -> None:
        """Проверка иерархии задач (нет циклов)"""
        if not parent_task_id:
            return

        BaseValidator.validate_uuid(parent_task_id, "parent_task_id")

        # Нельзя сделать задачу родителем самой себя
        if task_id == parent_task_id:
            raise BusinessLogicError(
                "Задача не может быть родителем самой себя", code="SELF_PARENT"
            )

        # TODO: добавить проверку на циклические зависимости

    @staticmethod
    async def validate_task_deletion(task_id: str) -> Task:
        """Проверка возможности удаления задачи"""
        task = await TaskValidator.validate_task_exists(task_id)

        if task.has_subtasks:
            from app.exceptions import TaskHasSubtasksError

            raise TaskHasSubtasksError(task_id)

        return task


class UserValidator(BaseValidator):
    """Валидатор для пользователей"""

    @staticmethod
    async def validate_user_exists(user_id: str) -> User:
        """Проверка существования пользователя"""
        BaseValidator.validate_uuid(user_id, "user_id")

        async with get_db_session_context() as session:
            user = await session.get(User, user_id)

            if not user:
                raise NotFoundError("Пользователь", user_id)

            return user

    @staticmethod
    async def validate_user_unique_email(
        email: str, exclude_user_id: str | None = None
    ) -> None:
        """Проверка уникальности email"""
        email = BaseValidator.validate_email(email)

        async with get_db_session_context() as session:
            query = select(User).where(User.email == email)

            if exclude_user_id:
                query = query.where(User.id != exclude_user_id)

            existing_user = await session.execute(query)

            if existing_user.scalar_one_or_none():
                from app.exceptions import UserAlreadyExistsError

                raise UserAlreadyExistsError("email", email)

    @staticmethod
    async def validate_user_unique_username(
        username: str, exclude_user_id: str | None = None
    ) -> None:
        """Проверка уникальности username"""
        if not username:
            return

        username = BaseValidator.validate_username(username)

        async with get_db_session_context() as session:
            query = select(User).where(User.username == username)

            if exclude_user_id:
                query = query.where(User.id != exclude_user_id)

            existing_user = await session.execute(query)

            if existing_user.scalar_one_or_none():
                from app.exceptions import UserAlreadyExistsError

                raise UserAlreadyExistsError("username", username)

    @staticmethod
    async def validate_user_active(user_id: str) -> User:
        """Проверка, что пользователь активен"""
        user = await UserValidator.validate_user_exists(user_id)

        if not user.is_active:
            raise BusinessLogicError("Пользователь неактивен", code="USER_INACTIVE")

        return user


class SprintValidator(BaseValidator):
    """Валидатор для спринтов"""

    @staticmethod
    async def validate_sprint_exists(sprint_id: str) -> Sprint:
        """Проверка существования спринта"""
        BaseValidator.validate_uuid(sprint_id, "sprint_id")

        async with get_db_session_context() as session:
            sprint = await session.get(Sprint, sprint_id)

            if not sprint:
                raise NotFoundError("Спринт", sprint_id)

            return sprint

    @staticmethod
    async def validate_sprint_dates(start_date: date, end_date: date) -> None:
        """Проверка дат спринта"""
        if start_date >= end_date:
            raise ValidationError(
                "Дата начала должна быть раньше даты окончания", "dates"
            )

        # Проверка, что спринт не слишком длинный (максимум 4 недели)
        duration = (end_date - start_date).days
        if duration > 28:
            raise ValidationError("Спринт не может быть длиннее 4 недель", "dates")

    @staticmethod
    async def validate_sprint_modification(sprint: Sprint) -> None:
        """Проверка возможности изменения спринта"""
        if sprint.status == SprintStatus.ACTIVE:
            from app.exceptions import SprintAlreadyStartedError

            raise SprintAlreadyStartedError(str(sprint.id))


class CommentValidator(BaseValidator):
    """Валидатор для комментариев"""

    @staticmethod
    def validate_comment_content(content: str) -> str:
        """Валидация содержимого комментария"""
        if not content or not content.strip():
            raise ValidationError(
                "Содержание комментария не может быть пустым", "content"
            )

        if len(content.strip()) > 10000:
            raise ValidationError(
                "Комментарий слишком длинный (максимум 10000 символов)", "content"
            )

        return content.strip()

    @staticmethod
    async def validate_comment_access(comment_id: str, user_id: str) -> None:
        """Проверка доступа к комментарию"""
        BaseValidator.validate_uuid(comment_id, "comment_id")
        BaseValidator.validate_uuid(user_id, "user_id")

        async with get_db_session_context() as session:
            from app.models.task import Comment

            # Получаем комментарий с задачей и проектом
            result = await session.execute(
                select(Comment)
                .options(
                    selectinload(Comment.task)
                    .selectinload(Task.project)
                    .selectinload(Project.members)
                )
                .where(Comment.id == comment_id)
            )

            comment = result.scalar_one_or_none()

            if not comment:
                raise NotFoundError("Комментарий", comment_id)

            # Проверяем доступ к проекту
            member = None
            for m in comment.task.project.members:
                if m.user_id == user_id and m.is_active:
                    member = m
                    break

            if not member and comment.author_id != user_id:
                raise PermissionError("доступ к комментарию", "комментарий")


# Композитные валидаторы для сложных проверок


class ProjectTaskValidator:
    """Композитный валидатор для операций с задачами в проектах"""

    @staticmethod
    async def validate_task_creation(
        project_id: str, creator_id: str, assignee_id: str | None = None
    ) -> tuple[Project, User | None]:
        """Валидация создания задачи"""
        # Проверяем доступ к проекту
        project = await ProjectValidator.validate_project_access(
            project_id, creator_id, can_edit=True
        )

        # Проверяем исполнителя, если указан
        assignee = None
        if assignee_id:
            assignee = await UserValidator.validate_user_active(assignee_id)

            # Проверяем, что исполнитель является участником проекта
            async with get_db_session_context() as session:
                member_exists = await session.execute(
                    select(ProjectMember).where(
                        and_(
                            ProjectMember.project_id == project_id,
                            ProjectMember.user_id == assignee_id,
                            ProjectMember.is_active,
                        )
                    )
                )

                if not member_exists.scalar_one_or_none():
                    raise BusinessLogicError(
                        "Исполнитель не является участником проекта",
                        code="ASSIGNEE_NOT_MEMBER",
                    )

        return project, assignee

    @staticmethod
    async def validate_bulk_task_operations(
        task_ids: list[str], user_id: str, operation: str = "update"
    ) -> list[Task]:
        """Валидация массовых операций с задачами"""
        if not task_ids:
            raise ValidationError("Список задач не может быть пустым", "task_ids")

        if len(task_ids) > 100:
            raise ValidationError(
                "Нельзя обрабатывать более 100 задач за раз", "task_ids"
            )

        tasks = []

        for task_id in task_ids:
            task = await TaskValidator.validate_task_access(
                task_id, user_id, can_edit=(operation == "update")
            )
            tasks.append(task)

        return tasks
