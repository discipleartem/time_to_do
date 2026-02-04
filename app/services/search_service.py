"""
Сервис для полнотекстового поиска
"""

import json
import uuid
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectMember
from app.models.search import SavedSearch, SearchableType, SearchIndex
from app.models.sprint import Sprint
from app.models.task import Comment, Task


class SearchService:
    """Сервис для поиска по сущностям проекта"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def index_entity(
        self,
        entity_type: SearchableType,
        entity_id: uuid.UUID,
        title: str,
        content: str | None = None,
        project_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        is_public: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> SearchIndex:
        """Индексировать сущность для поиска"""

        # Удаляем существующий индекс
        await self.remove_from_index(entity_type, entity_id)

        # Создаем поисковый вектор
        search_text = f"{title} {content or ''}"

        # Создаем новый индекс
        search_index = SearchIndex(
            title=title,
            content=content,
            search_vector=func.to_tsvector("russian", search_text),
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            user_id=user_id,
            is_public=is_public,
            search_metadata=json.dumps(metadata) if metadata else None,
        )

        self.db.add(search_index)
        await self.db.commit()
        await self.db.refresh(search_index)

        return search_index

    async def remove_from_index(
        self,
        entity_type: SearchableType,
        entity_id: uuid.UUID,
    ) -> None:
        """Удалить сущность из индекса поиска"""

        stmt = select(SearchIndex).where(
            and_(
                SearchIndex.entity_type == entity_type,
                SearchIndex.entity_id == entity_id,
            )
        )
        result = await self.db.execute(stmt)
        search_index = result.scalar_one_or_none()

        if search_index:
            await self.db.delete(search_index)
            await self.db.commit()

    async def search(
        self,
        query: str,
        user_id: uuid.UUID,
        entity_types: list[SearchableType] | None = None,
        project_ids: list[uuid.UUID] | None = None,
        limit: int = 50,
        offset: int = 0,
        include_public: bool = True,
    ) -> tuple[list[dict[str, Any]], int]:
        """Выполнить полнотекстовый поиск"""

        # Базовый запрос с ранжированием
        search_query = func.to_tsquery("russian", query)

        stmt = select(
            SearchIndex,
            func.ts_rank(SearchIndex.search_vector, search_query).label("rank"),
        ).where(SearchIndex.search_vector.op("@@")(search_query))

        # Фильтры доступа
        access_filters = [
            # Пользователь имеет доступ к своим объектам
            or_(
                SearchIndex.user_id == user_id,
                SearchIndex.is_public == True,
            )
        ]

        # Фильтр по проектам (если пользователь участник)
        if project_ids:
            access_filters.append(SearchIndex.project_id.in_(project_ids))
        else:
            # Получаем проекты пользователя
            user_projects = await self._get_user_projects(user_id)
            if user_projects:
                access_filters.append(SearchIndex.project_id.in_(user_projects))

        stmt = stmt.where(and_(*access_filters))

        # Фильтр по типам сущностей
        if entity_types:
            stmt = stmt.where(SearchIndex.entity_type.in_(entity_types))

        # Сортировка по релевантности
        stmt = stmt.order_by(
            func.ts_rank(SearchIndex.search_vector, search_query).desc()
        )

        # Пагинация
        stmt = stmt.limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        search_results = result.all()

        # Получаем общее количество
        count_stmt = (
            select(func.count(SearchIndex.id))
            .where(SearchIndex.search_vector.op("@@")(search_query))
            .where(and_(*access_filters))
        )

        if entity_types:
            count_stmt = count_stmt.where(SearchIndex.entity_type.in_(entity_types))

        count_result = await self.db.execute(count_stmt)
        total_count = count_result.scalar()

        # Формируем результаты с детальной информацией
        results = []
        for search_index, rank in search_results:
            entity_data = await self._get_entity_data(
                search_index.entity_type,
                search_index.entity_id,
            )

            if entity_data:
                results.append(
                    {
                        "id": str(search_index.id),
                        "entity_type": search_index.entity_type,
                        "entity_id": str(search_index.entity_id),
                        "title": search_index.title,
                        "content": search_index.content,
                        "rank": float(rank),
                        "project_id": (
                            str(search_index.project_id)
                            if search_index.project_id
                            else None
                        ),
                        "is_public": search_index.is_public,
                        "metadata": (
                            json.loads(search_index.search_metadata)
                            if search_index.search_metadata
                            else None
                        ),
                        "entity_data": entity_data,
                    }
                )

        return results, total_count

    async def _get_user_projects(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """Получить ID проектов пользователя"""

        stmt = select(Project.id).where(
            or_(
                Project.owner_id == user_id,
                Project.is_public == True,
            )
        )

        # Также проверяем участие в проектах
        project_member_stmt = select(ProjectMember.project_id).where(
            and_(
                ProjectMember.user_id == user_id,
                ProjectMember.is_active == True,
            )
        )

        result = await self.db.execute(stmt)
        projects = result.scalars().all()

        member_result = await self.db.execute(project_member_stmt)
        member_projects = member_result.scalars().all()

        return list(set(projects + member_projects))

    async def _get_entity_data(
        self,
        entity_type: SearchableType,
        entity_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Получить детальные данные сущности"""

        if entity_type == SearchableType.TASK:
            stmt = (
                select(Task)
                .options(
                    selectinload(Task.project),
                    selectinload(Task.assignee),
                    selectinload(Task.creator),
                )
                .where(Task.id == entity_id)
            )
            result = await self.db.execute(stmt)
            task = result.scalar_one_or_none()

            if task:
                return {
                    "status": task.status,
                    "priority": task.priority,
                    "story_point": task.story_point,
                    "project_name": task.project.name if task.project else None,
                    "assignee_name": task.assignee.full_name if task.assignee else None,
                    "creator_name": task.creator.full_name if task.creator else None,
                    "due_date": task.due_date,
                    "created_at": (
                        task.created_at.isoformat() if task.created_at else None
                    ),
                }

        elif entity_type == SearchableType.PROJECT:
            stmt = (
                select(Project)
                .options(
                    selectinload(Project.owner),
                    selectinload(Project.members),
                )
                .where(Project.id == entity_id)
            )
            result = await self.db.execute(stmt)
            project = result.scalar_one_or_none()

            if project:
                return {
                    "status": project.status,
                    "is_public": project.is_public,
                    "owner_name": project.owner.full_name if project.owner else None,
                    "member_count": project.member_count,
                    "created_at": (
                        project.created_at.isoformat() if project.created_at else None
                    ),
                }

        elif entity_type == SearchableType.SPRINT:
            stmt = (
                select(Sprint)
                .options(selectinload(Sprint.project))
                .where(Sprint.id == entity_id)
            )
            result = await self.db.execute(stmt)
            sprint = result.scalar_one_or_none()

            if sprint:
                return {
                    "status": sprint.status,
                    "project_name": sprint.project.name if sprint.project else None,
                    "start_date": (
                        sprint.start_date.isoformat() if sprint.start_date else None
                    ),
                    "end_date": (
                        sprint.end_date.isoformat() if sprint.end_date else None
                    ),
                    "task_count": sprint.task_count,
                    "completed_task_count": sprint.completed_task_count,
                    "created_at": (
                        sprint.created_at.isoformat() if sprint.created_at else None
                    ),
                }

        elif entity_type == SearchableType.COMMENT:
            stmt = (
                select(Comment)
                .options(
                    selectinload(Comment.task),
                    selectinload(Comment.author),
                )
                .where(Comment.id == entity_id)
            )
            result = await self.db.execute(stmt)
            comment = result.scalar_one_or_none()

            if comment:
                return {
                    "task_title": comment.task.title if comment.task else None,
                    "author_name": comment.author.full_name if comment.author else None,
                    "is_edited": comment.is_edited,
                    "created_at": (
                        comment.created_at.isoformat() if comment.created_at else None
                    ),
                }

        return None

    async def save_search(
        self,
        user_id: uuid.UUID,
        name: str,
        query: str,
        filters: dict[str, Any] | None = None,
        is_public: bool = False,
    ) -> SavedSearch:
        """Сохранить поиск"""

        saved_search = SavedSearch(
            name=name,
            query=query,
            filters=json.dumps(filters) if filters else None,
            user_id=user_id,
            is_public=is_public,
        )

        self.db.add(saved_search)
        await self.db.commit()
        await self.db.refresh(saved_search)

        return saved_search

    async def get_saved_searches(
        self,
        user_id: uuid.UUID,
        include_public: bool = True,
    ) -> list[SavedSearch]:
        """Получить сохраненные поиски пользователя"""

        if include_public:
            # Если включены public, то получаем все поиски пользователя + public поиски других пользователей
            stmt = select(SavedSearch).where(
                (SavedSearch.user_id == user_id) | (SavedSearch.is_public == True)
            )
        else:
            # Только поиски пользователя
            stmt = select(SavedSearch).where(SavedSearch.user_id == user_id)

        stmt = stmt.order_by(SavedSearch.created_at.desc())

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def reindex_all(self) -> None:
        """Переиндексировать все сущности"""

        # Очищаем текущий индекс
        await self.db.execute(SearchIndex.__table__.delete())

        # Индексируем задачи
        await self._reindex_tasks()

        # Индексируем проекты
        await self._reindex_projects()

        # Индексируем спринты
        await self._reindex_sprints()

        # Индексируем комментарии
        await self._reindex_comments()

        await self.db.commit()

    async def _reindex_tasks(self) -> None:
        """Переиндексировать задачи"""

        stmt = select(Task).options(
            selectinload(Task.project),
            selectinload(Task.assignee),
        )
        result = await self.db.execute(stmt)
        tasks = result.scalars().all()

        for task in tasks:
            await self.index_entity(
                entity_type=SearchableType.TASK,
                entity_id=task.id,
                title=task.title,
                content=task.description,
                project_id=task.project_id,
                user_id=task.assignee_id or task.creator_id,
                is_public=task.project.is_public if task.project else False,
                metadata={
                    "status": task.status,
                    "priority": task.priority,
                    "story_point": task.story_point,
                    "due_date": task.due_date,
                },
            )

    async def _reindex_projects(self) -> None:
        """Переиндексировать проекты"""

        stmt = select(Project)
        result = await self.db.execute(stmt)
        projects = result.scalars().all()

        for project in projects:
            await self.index_entity(
                entity_type=SearchableType.PROJECT,
                entity_id=project.id,
                title=project.name,
                content=project.description,
                project_id=project.id,
                user_id=project.owner_id,
                is_public=project.is_public,
                metadata={
                    "status": project.status,
                },
            )

    async def _reindex_sprints(self) -> None:
        """Переиндексировать спринты"""

        stmt = select(Sprint).options(selectinload(Sprint.project))
        result = await self.db.execute(stmt)
        sprints = result.scalars().all()

        for sprint in sprints:
            await self.index_entity(
                entity_type=SearchableType.SPRINT,
                entity_id=sprint.id,
                title=sprint.name,
                content=f"{sprint.description or ''} {sprint.goal or ''}",
                project_id=sprint.project_id,
                user_id=sprint.project.owner_id if sprint.project else None,
                is_public=sprint.project.is_public if sprint.project else False,
                metadata={
                    "status": sprint.status,
                    "start_date": (
                        sprint.start_date.isoformat() if sprint.start_date else None
                    ),
                    "end_date": (
                        sprint.end_date.isoformat() if sprint.end_date else None
                    ),
                },
            )

    async def _reindex_comments(self) -> None:
        """Переиндексировать комментарии"""

        stmt = select(Comment).options(
            selectinload(Comment.task).selectinload(Task.project),
            selectinload(Comment.author),
        )
        result = await self.db.execute(stmt)
        comments = result.scalars().all()

        for comment in comments:
            await self.index_entity(
                entity_type=SearchableType.COMMENT,
                entity_id=comment.id,
                title=(
                    f"Комментарий к задаче: {comment.task.title}"
                    if comment.task
                    else "Комментарий"
                ),
                content=comment.content,
                project_id=comment.task.project_id if comment.task else None,
                user_id=comment.author_id,
                is_public=(
                    comment.task.project.is_public
                    if comment.task and comment.task.project
                    else False
                ),
                metadata={
                    "task_id": str(comment.task_id) if comment.task_id else None,
                    "is_edited": comment.is_edited,
                },
            )
