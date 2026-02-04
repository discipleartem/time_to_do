"""
Тесты для сервиса поиска
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.search import SearchableType
from app.models.task import Task, TaskPriority, TaskStatus
from app.services.search_service import SearchService


@pytest.mark.asyncio
async def test_index_task(db_session: AsyncSession, async_user_factory):
    """Тест индексации задачи"""
    # Создаем пользователя
    test_user = await async_user_factory()
    await db_session.commit()

    # Создаем проект
    project = Project(
        name="Test Project",
        description="Test project description",
        owner_id=test_user.id,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Создаем задачу
    task = Task(
        title="Test Task",
        description="Test task description for search",
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
        project_id=project.id,
        creator_id=test_user.id,
        assignee_id=test_user.id,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    # Индексируем задачу
    search_service = SearchService(db_session)
    search_index = await search_service.index_entity(
        entity_type=SearchableType.TASK,
        entity_id=task.id,
        title=task.title,
        content=task.description,
        project_id=project.id,
        user_id=test_user.id,
        is_public=project.is_public,
        metadata={
            "status": task.status,
            "priority": task.priority,
        },
    )

    assert search_index.title == task.title
    assert search_index.content == task.description
    assert search_index.entity_type == SearchableType.TASK
    assert search_index.entity_id == task.id
    assert search_index.project_id == project.id
    assert search_index.user_id == test_user.id


@pytest.mark.asyncio
async def test_search_tasks(db_session: AsyncSession, async_user_factory):
    """Тест поиска задач"""
    # Создаем пользователя
    test_user = await async_user_factory()
    await db_session.commit()

    # Создаем проект
    project = Project(
        name="Search Project",
        description="Project for testing search",
        owner_id=test_user.id,
        is_public=True,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Создаем несколько задач
    tasks = [
        Task(
            title="Important task",
            description="This is an important task for testing",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            project_id=project.id,
            creator_id=test_user.id,
            assignee_id=test_user.id,
        ),
        Task(
            title="Another task",
            description="Another task for search testing",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            project_id=project.id,
            creator_id=test_user.id,
            assignee_id=test_user.id,
        ),
        Task(
            title="Different task",
            description="Completely different task",
            status=TaskStatus.DONE,
            priority=TaskPriority.LOW,
            project_id=project.id,
            creator_id=test_user.id,
            assignee_id=test_user.id,
        ),
    ]

    for task in tasks:
        db_session.add(task)
    await db_session.commit()

    # Индексируем задачи
    search_service = SearchService(db_session)
    for task in tasks:
        await search_service.index_entity(
            entity_type=SearchableType.TASK,
            entity_id=task.id,
            title=task.title,
            content=task.description,
            project_id=project.id,
            user_id=test_user.id,
            is_public=project.is_public,
        )

    # Ищем задачи
    results, total_count = await search_service.search(
        query="important",
        user_id=test_user.id,
    )

    assert total_count == 1
    assert len(results) == 1
    assert results[0]["title"] == "Important task"
    assert results[0]["entity_type"] == SearchableType.TASK


@pytest.mark.asyncio
async def test_search_multiple_types(db_session: AsyncSession, async_user_factory):
    """Тест поиска по нескольким типам сущностей"""
    # Создаем пользователя
    test_user = await async_user_factory()
    await db_session.commit()

    # Создаем проект
    project = Project(
        name="Search Test Project",
        description="Project for multi-type search testing",
        owner_id=test_user.id,
        is_public=True,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Создаем задачу
    task = Task(
        title="Search Task",
        description="Task for multi-type search",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        project_id=project.id,
        creator_id=test_user.id,
        assignee_id=test_user.id,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    # Индексируем сущности
    search_service = SearchService(db_session)

    await search_service.index_entity(
        entity_type=SearchableType.PROJECT,
        entity_id=project.id,
        title=project.name,
        content=project.description,
        project_id=project.id,
        user_id=test_user.id,
        is_public=project.is_public,
    )

    await search_service.index_entity(
        entity_type=SearchableType.TASK,
        entity_id=task.id,
        title=task.title,
        content=task.description,
        project_id=project.id,
        user_id=test_user.id,
        is_public=project.is_public,
    )

    # Ищем по общему слову
    results, total_count = await search_service.search(
        query="search",
        user_id=test_user.id,
    )

    assert total_count == 2
    assert len(results) == 2

    # Проверяем, что оба типа присутствуют
    entity_types = {result["entity_type"] for result in results}
    assert SearchableType.PROJECT in entity_types
    assert SearchableType.TASK in entity_types


@pytest.mark.asyncio
async def test_search_with_filters(db_session: AsyncSession, async_user_factory):
    """Тест поиска с фильтрами"""
    # Создаем пользователя
    test_user = await async_user_factory()
    await db_session.commit()

    # Создаем проект
    project = Project(
        name="Filter Project",
        description="Project for filter testing",
        owner_id=test_user.id,
        is_public=True,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Создаем задачу
    task = Task(
        title="Filter Task",
        description="Task for filter testing",
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
        project_id=project.id,
        creator_id=test_user.id,
        assignee_id=test_user.id,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    # Индексируем задачу
    search_service = SearchService(db_session)
    await search_service.index_entity(
        entity_type=SearchableType.TASK,
        entity_id=task.id,
        title=task.title,
        content=task.description,
        project_id=project.id,
        user_id=test_user.id,
        is_public=project.is_public,
    )

    # Ищем с фильтром по типу
    results, total_count = await search_service.search(
        query="filter",
        user_id=test_user.id,
        entity_types=[SearchableType.TASK],
    )

    assert total_count == 1
    assert len(results) == 1
    assert results[0]["entity_type"] == SearchableType.TASK

    # Ищем с фильтром по другому типу (должно быть 0 результатов)
    results, total_count = await search_service.search(
        query="filter",
        user_id=test_user.id,
        entity_types=[SearchableType.PROJECT],
    )

    assert total_count == 0
    assert len(results) == 0


@pytest.mark.asyncio
async def test_save_search(db_session: AsyncSession, async_user_factory):
    """Тест сохранения поиска"""
    # Создаем пользователя
    test_user = await async_user_factory()
    await db_session.commit()

    search_service = SearchService(db_session)

    saved_search = await search_service.save_search(
        user_id=test_user.id,
        name="My Search",
        query="test query",
        filters={"entity_types": ["task"], "limit": 20},
        is_public=False,
    )

    assert saved_search.name == "My Search"
    assert saved_search.query == "test query"
    assert saved_search.user_id == test_user.id
    assert saved_search.is_public is False


@pytest.mark.asyncio
async def test_get_saved_searches(db_session: AsyncSession, async_user_factory):
    """Тест получения сохраненных поисков"""
    # Создаем пользователя
    test_user = await async_user_factory()
    await db_session.commit()

    search_service = SearchService(db_session)

    # Создаем несколько сохраненных поисков
    await search_service.save_search(
        user_id=test_user.id,
        name="Search 1",
        query="query 1",
        is_public=False,
    )

    await search_service.save_search(
        user_id=test_user.id,
        name="Search 2",
        query="query 2",
        is_public=True,
    )

    # Получаем сохраненные поиски
    saved_searches = await search_service.get_saved_searches(
        user_id=test_user.id,
        include_public=True,
    )

    assert len(saved_searches) == 2
    assert saved_searches[0].name == "Search 2"  # Отсортировано по created_at DESC
    assert saved_searches[1].name == "Search 1"


@pytest.mark.asyncio
async def test_remove_from_index(db_session: AsyncSession, async_user_factory):
    """Тест удаления из индекса"""
    # Создаем пользователя
    test_user = await async_user_factory()
    await db_session.commit()

    # Создаем проект и задачу
    project = Project(
        name="Remove Test Project",
        description="Project for removal testing",
        owner_id=test_user.id,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    task = Task(
        title="Remove Task",
        description="Task for removal testing",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        project_id=project.id,
        creator_id=test_user.id,
        assignee_id=test_user.id,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    # Индексируем задачу
    search_service = SearchService(db_session)
    await search_service.index_entity(
        entity_type=SearchableType.TASK,
        entity_id=task.id,
        title=task.title,
        content=task.description,
        project_id=project.id,
        user_id=test_user.id,
    )

    # Проверяем, что задача найдена
    results, total_count = await search_service.search(
        query="remove",
        user_id=test_user.id,
    )
    assert total_count == 1

    # Удаляем из индекса
    await search_service.remove_from_index(
        entity_type=SearchableType.TASK,
        entity_id=task.id,
    )

    # Проверяем, что задача больше не найдена
    results, total_count = await search_service.search(
        query="remove",
        user_id=test_user.id,
    )
    assert total_count == 0


@pytest.mark.asyncio
async def test_search_pagination(db_session: AsyncSession, async_user_factory):
    """Тест пагинации поиска"""
    # Создаем пользователя
    test_user = await async_user_factory()
    await db_session.commit()

    # Создаем проект
    project = Project(
        name="Pagination Project",
        description="Project for pagination testing",
        owner_id=test_user.id,
        is_public=True,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Создаем несколько задач
    search_service = SearchService(db_session)

    for i in range(5):
        task = Task(
            title=f"Task {i}",
            description=f"Task description {i} with pagination test",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            project_id=project.id,
            creator_id=test_user.id,
            assignee_id=test_user.id,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Индексируем задачу
        await search_service.index_entity(
            entity_type=SearchableType.TASK,
            entity_id=task.id,
            title=task.title,
            content=task.description,
            project_id=project.id,
            user_id=test_user.id,
            is_public=project.is_public,
        )

    # Тестируем пагинацию
    results, total_count = await search_service.search(
        query="pagination",
        user_id=test_user.id,
        limit=2,
        offset=0,
    )
    assert total_count == 5
    assert len(results) == 2

    results, total_count = await search_service.search(
        query="pagination",
        user_id=test_user.id,
        limit=2,
        offset=2,
    )
    assert total_count == 5
    assert len(results) == 2

    results, total_count = await search_service.search(
        query="pagination",
        user_id=test_user.id,
        limit=2,
        offset=4,
    )
    assert total_count == 5
    assert len(results) == 1
