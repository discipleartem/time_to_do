"""
Фабрики для создания тестовых данных с использованием Factory Pattern
"""

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import factory
from factory import fuzzy

from app.models.project import Project, ProjectStatus
from app.models.sprint import Sprint, SprintStatus
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User, UserRole


class UserFactory(factory.Factory):
    """Фабрика для создания пользователей"""

    class Meta:
        model = User

    email = factory.LazyAttribute(lambda o: f"user_{uuid.uuid4().hex[:8]}@example.com")
    username = factory.LazyAttribute(lambda o: f"user_{uuid.uuid4().hex[:8]}")
    full_name = factory.Faker("name")
    hashed_password = factory.LazyFunction(
        lambda: bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
    )
    is_active = True
    role = UserRole.USER

    @factory.post_generation
    def with_admin_role(obj, create, extracted, **kwargs):
        """Создать пользователя с ролью администратора"""
        if extracted:
            obj.role = UserRole.ADMIN
        return obj


class ProjectFactory(factory.Factory):
    """Фабрика для создания проектов"""

    class Meta:
        model = Project

    name = factory.Faker("company")
    description = factory.Faker("text", max_nb_chars=200)
    status = ProjectStatus.ACTIVE
    is_public = False
    allow_external_sharing = True
    max_members = 10
    owner = factory.SubFactory(UserFactory)

    @factory.post_generation
    def with_members(obj, create, extracted, **kwargs):
        """Добавить участников в проект"""
        if extracted:
            for _ in range(extracted):
                member = UserFactory()
                obj.members.append(member)
        return obj


class TaskFactory(factory.Factory):
    """Фабрика для создания задач"""

    class Meta:
        model = Task

    title = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("text", max_nb_chars=500)
    status = fuzzy.FuzzyChoice(
        [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.DONE]
    )
    priority = fuzzy.FuzzyChoice(
        [TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH]
    )
    story_point = fuzzy.FuzzyChoice([1, 2, 3, 5, 8])
    estimated_hours = fuzzy.FuzzyChoice([1, 2, 4, 8, 16])

    # Связи
    project = factory.SubFactory(ProjectFactory)
    creator = factory.SubFactory(UserFactory)
    assignee = factory.SubFactory(UserFactory)

    @factory.post_generation
    def with_assignee(obj, create, extracted, **kwargs):
        """Установить конкретного исполнителя"""
        if extracted:
            obj.assignee = extracted
        return obj


class SprintFactory(factory.Factory):
    """Фабрика для создания спринтов"""

    class Meta:
        model = Sprint

    name = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("text", max_nb_chars=300)
    status = SprintStatus.ACTIVE
    capacity_hours = fuzzy.FuzzyChoice([40, 60, 80, 100])
    velocity_points = fuzzy.FuzzyChoice([20, 30, 40, 50])

    # Даты
    start_date = factory.LazyFunction(lambda: datetime.now(UTC).date())
    end_date = factory.LazyFunction(
        lambda: (datetime.now(UTC) + timedelta(days=14)).date()
    )

    # Связи
    project = factory.SubFactory(ProjectFactory)


class TimeEntryFactory(factory.Factory):
    """Фабрика для создания записей времени"""

    class Meta:
        model = None  # Будет определена после импорта модели

    description = factory.Faker("sentence", nb_words=6)
    duration_minutes = fuzzy.FuzzyChoice([15, 30, 60, 90, 120, 180, 240])

    # Время
    start_time = factory.LazyFunction(
        lambda: datetime.now(UTC).replace(hour=9, minute=0, second=0, microsecond=0)
    )
    end_time = factory.LazyAttribute(
        lambda o: o.start_time + timedelta(minutes=o.duration_minutes)
    )

    # Связи
    user = factory.SubFactory(UserFactory)
    task = factory.SubFactory(TaskFactory)


# Комплексные фабрики для создания сценариев
class TestScenariosFactory:
    """Фабрика для создания комплексных тестовых сценариев"""

    @staticmethod
    async def create_full_project_scenario(db_session, num_members=3, num_tasks=10):
        """
        Создать полный сценарий проекта с участниками и задачами

        Args:
            db_session: Сессия базы данных
            num_members: Количество участников
            num_tasks: Количество задач

        Returns:
            dict: Словарь со всеми созданными объектами
        """
        # Создаем владельца проекта
        owner = await UserFactory()
        db_session.add(owner)
        await db_session.flush()

        # Создаем проект
        project = await ProjectFactory(owner=owner)
        db_session.add(project)
        await db_session.flush()

        # Создаем участников
        members = []
        for _member_count in range(num_members):
            member = await UserFactory()
            db_session.add(member)
            await db_session.flush()
            project.members.append(member)
            members.append(member)

        # Создаем задачи
        tasks = []
        for task_index in range(num_tasks):
            assignee = (
                owner if task_index % 3 == 0 else members[task_index % len(members)]
            )
            task = await TaskFactory(project=project, creator=owner, assignee=assignee)
            db_session.add(task)
            tasks.append(task)

        await db_session.commit()

        return {"project": project, "owner": owner, "members": members, "tasks": tasks}

    @staticmethod
    async def create_sprint_scenario(db_session, num_tasks=8):
        """
        Создать сценарий спринта с задачами

        Args:
            db_session: Сессия базы данных
            num_tasks: Количество задач в спринте

        Returns:
            dict: Словарь со всеми созданными объектами
        """
        # Создаем проект и владельца
        owner = await UserFactory()
        project = await ProjectFactory(owner=owner)

        # Создаем спринт
        sprint = await SprintFactory(project=project)

        # Создаем задачи для спринта
        tasks = []
        for _task_count in range(num_tasks):
            task = await TaskFactory(project=project, creator=owner, assignee=owner)
            sprint.tasks.append(task)
            tasks.append(task)

        await db_session.commit()

        return {"project": project, "owner": owner, "sprint": sprint, "tasks": tasks}

    @staticmethod
    async def create_time_tracking_scenario(db_session, num_entries=20):
        """
        Создать сценарий отслеживания времени

        Args:
            db_session: Сессия базы данных
            num_entries: Количество записей времени

        Returns:
            dict: Словарь со всеми созданными объектами
        """
        # Создаем пользователя и проект
        user = await UserFactory()
        project = await ProjectFactory(owner=user)
        task = await TaskFactory(project=project, creator=user, assignee=user)

        # Создаем записи времени за последние дни
        time_entries = []
        for _i in range(num_entries):
            days_ago = _i % 7  # Записи за последние 7 дней
            start_time = (
                datetime.now(UTC) - timedelta(days=days_ago, hours=9)
            ).replace(minute=0, second=0, microsecond=0)

            duration = [60, 90, 120, 180, 240][_i % 5]  # Разная продолжительность

            # Импортируем модель здесь для избежания circular import
            from app.models.time_entry import TimeEntry

            time_entry = TimeEntry(
                description=f"Работа над задачей {_i+1}",
                start_time=start_time,
                end_time=start_time + timedelta(minutes=duration),
                duration_minutes=duration,
                user=user,
                task=task,
            )
            time_entries.append(time_entry)

        await db_session.commit()

        return {
            "user": user,
            "project": project,
            "task": task,
            "time_entries": time_entries,
        }
