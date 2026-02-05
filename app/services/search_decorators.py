"""
Декораторы для автоматической индексации сущностей
"""

import functools
import uuid
from collections.abc import Callable
from typing import Any

from app.models.search import SearchableType
from app.services.search_service import SearchService


def auto_index(entity_type: SearchableType) -> Callable[..., Callable]:
    """
    Декоратор для автоматической индексации сущностей

    Args:
        entity_type: Тип сущности для индексации
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Выполняем основную функцию
            result = await func(self, *args, **kwargs)

            # Получаем сессию БД из сервиса
            db_session = getattr(self, "db", None)
            if not db_session:
                return result

            try:
                # Создаем SearchService для индексации
                search_service = SearchService(db_session)

                # Определяем ID сущности и данные для индексации
                entity_id = None
                title = ""
                content = None
                project_id = None
                user_id = None
                is_public = False
                metadata = None

                if entity_type == SearchableType.TASK and isinstance(result, type):
                    # Для задач получаем данные из результата
                    entity_id = result.id
                    title = result.title
                    content = result.description
                    project_id = result.project_id
                    user_id = result.assignee_id or result.creator_id
                    is_public = (
                        getattr(result.project, "is_public", False)
                        if result.project
                        else False
                    )
                    metadata = {
                        "status": result.status,
                        "priority": result.priority,
                        "story_point": result.story_point,
                        "due_date": result.due_date,
                    }

                elif entity_type == SearchableType.PROJECT and isinstance(result, type):
                    # Для проектов
                    entity_id = result.id
                    title = result.name
                    content = result.description
                    project_id = result.id
                    user_id = result.owner_id
                    is_public = result.is_public
                    metadata = {"status": result.status}

                elif entity_type == SearchableType.COMMENT and isinstance(result, type):
                    # Для комментариев
                    entity_id = result.id
                    title = (
                        f"Комментарий к задаче: {result.task.title}"
                        if result.task
                        else "Комментарий"
                    )
                    content = result.content
                    project_id = result.task.project_id if result.task else None
                    user_id = result.author_id
                    is_public = (
                        getattr(result.task.project, "is_public", False)
                        if result.task and result.task.project
                        else False
                    )
                    metadata = {
                        "task_id": str(result.task_id) if result.task_id else None,
                        "is_edited": result.is_edited,
                    }

                # Индексируем сущность
                if entity_id and title:
                    await search_service.index_entity(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        title=title,
                        content=content,
                        project_id=project_id,
                        user_id=user_id,
                        is_public=is_public,
                        metadata=metadata,
                    )

            except Exception:  # nosec B110
                # Ошибки индексации не должны прерывать основную операцию
                # В реальном приложении здесь можно добавить логирование
                pass

            return result

        return wrapper

    return decorator


def auto_index_delete(entity_type: SearchableType) -> Callable[..., Callable]:
    """
    Декоратор для автоматического удаления из индекса

    Args:
        entity_type: Тип сущности для удаления из индекса
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Получаем ID сущности из аргументов
            entity_id = None

            # Ищем ID в аргументах
            for arg in args:
                if isinstance(arg, (str, uuid.UUID)):
                    entity_id = arg
                    break

            for key, value in kwargs.items():
                if (
                    key in ["entity_id", "task_id", "project_id", "comment_id"]
                    and value
                ):
                    entity_id = value
                    break

            # Выполняем основную функцию
            result = await func(self, *args, **kwargs)

            # Удаляем из индекса
            if entity_id:
                db_session = getattr(self, "db", None)
                if db_session:
                    try:
                        search_service = SearchService(db_session)
                        await search_service.remove_from_index(entity_type, entity_id)
                    except Exception:  # nosec B110
                        # Ошибки удаления из индекса не должны прерывать операцию
                        pass

            return result

        return wrapper

    return decorator
