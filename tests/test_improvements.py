"""
Простой тест для проверки улучшений
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.task import TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService


@pytest.mark.asyncio
async def test_task_service_improvements(db_session: AsyncSession):
    """
    ✅ Тест улучшений TaskService согласно лучшим практикам
    """
    # Создаем пользователя и проект
    user = User(email="test@example.com", username="testuser", full_name="Test User")
    db_session.add(user)
    await db_session.flush()

    project = Project(
        name="Test Project", description="Test Description", owner_id=user.id
    )
    db_session.add(project)
    await db_session.flush()

    # Создаем сервис
    task_service = TaskService(db_session)

    # Тестируем улучшенный create_task метод
    task_data = TaskCreate(
        title="Test Task",
        description="Testing improvements",
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
        story_point="8",  # ✅ Исправляем: должно быть строкой
        project_id=str(project.id),  # ✅ Добавляем обязательное поле
    )

    # ✅ Выполняем операцию
    task = await task_service.create_task(
        task_data=task_data, project_id=str(project.id), creator_id=str(user.id)
    )

    # Проверяем результаты
    assert task is not None
    assert task.title == "Test Task"
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.HIGH
    assert task.story_point == "8"  # Исправляем: это строка
    assert str(task.project_id) == str(project.id)  # ✅ Сравниваем строки
    assert str(task.creator_id) == str(user.id)  # ✅ Сравниваем строки
    assert task.order == 1  # Первая задача в колонке

    print("Улучшения работают корректно!")
