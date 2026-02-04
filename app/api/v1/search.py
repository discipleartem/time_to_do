"""
API роутеры для поиска
"""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.search import SearchableType
from app.models.user import User
from app.schemas.search import (
    ReindexResponse,
    SavedSearch,
    SaveSearchRequest,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SearchSuggestionsResponse,
)
from app.services.search_service import SearchService

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(
    search_query: SearchQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Выполнить полнотекстовый поиск"""

    search_service = SearchService(db)

    # Конвертируем типы сущностей
    entity_types = None
    if search_query.entity_types:
        entity_types = []
        for entity_type in search_query.entity_types:
            try:
                entity_types.append(SearchableType(entity_type))
            except ValueError as err:
                raise HTTPException(
                    status_code=400,
                    detail=f"Неверный тип сущности: {entity_type}",
                ) from err

    # Конвертируем ID проектов
    project_ids = None
    if search_query.project_ids:
        project_ids = [uuid.UUID(pid) for pid in search_query.project_ids]

    # Выполняем поиск
    results, total_count = await search_service.search(
        query=search_query.query,
        user_id=current_user.id,
        entity_types=entity_types,
        project_ids=project_ids,
        limit=search_query.limit,
        offset=search_query.offset,
        include_public=search_query.include_public,
    )

    # Конвертируем результаты
    search_results = []
    for result in results:
        search_results.append(
            SearchResult(
                id=result["id"],
                entity_type=result["entity_type"],
                entity_id=result["entity_id"],
                title=result["title"],
                content=result["content"],
                rank=result["rank"],
                project_id=result["project_id"],
                is_public=result["is_public"],
                metadata=result["metadata"],
                entity_data=result["entity_data"],
            )
        )

    return SearchResponse(
        results=search_results,
        total_count=total_count,
        query=search_query.query,
        limit=search_query.limit,
        offset=search_query.offset,
    )


@router.get("/search")
async def search_get(
    q: str = Query(..., min_length=1, max_length=500, description="Поисковый запрос"),
    type: list[str] = Query(default=None, description="Типы сущностей"),
    project: list[str] = Query(default=None, description="ID проектов"),
    limit: int = Query(default=20, ge=1, le=100, description="Лимит результатов"),
    offset: int = Query(default=0, ge=0, description="Смещение"),
    public: bool = Query(default=True, description="Включать публичные объекты"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Поиск через GET параметры"""

    search_query = SearchQuery(
        query=q,
        entity_types=type,
        project_ids=project,
        limit=limit,
        offset=offset,
        include_public=public,
    )

    return await search(search_query, current_user, db)


@router.post("/saved-searches", response_model=SavedSearch)
async def save_search(
    save_request: SaveSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavedSearch:
    """Сохранить поиск"""

    search_service = SearchService(db)

    saved_search = await search_service.save_search(
        user_id=current_user.id,
        name=save_request.name,
        query=save_request.query,
        filters=save_request.filters,
        is_public=save_request.is_public,
    )

    # Конвертируем JSON строку в dict если необходимо
    filters_dict = None
    if saved_search.filters:
        try:
            filters_dict = json.loads(saved_search.filters)
        except (json.JSONDecodeError, TypeError):
            filters_dict = {}
            # Логируем ошибку, но продолжаем с пустыми фильтрами
            # В реальном приложении здесь можно добавить логирование

    return SavedSearch(
        id=saved_search.id,
        name=saved_search.name,
        query=saved_search.query,
        filters=filters_dict,
        user_id=saved_search.user_id,
        is_public=saved_search.is_public,
        created_at=saved_search.created_at.isoformat(),
        updated_at=saved_search.updated_at.isoformat(),
    )


@router.get("/saved-searches", response_model=list[SavedSearch])
async def get_saved_searches(
    public: bool = Query(default=True, description="Включать публичные поиски"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SavedSearch]:
    """Получить сохраненные поиски"""

    search_service = SearchService(db)

    saved_searches = await search_service.get_saved_searches(
        user_id=current_user.id,
        include_public=public,
    )

    result = []
    for search in saved_searches:
        # Конвертируем JSON строку в dict если необходимо
        filters_dict = None
        if search.filters:
            try:
                filters_dict = json.loads(search.filters)
            except (json.JSONDecodeError, TypeError):
                filters_dict = {}
                # Логируем ошибку, но продолжаем с пустыми фильтрами
                # В реальном приложении здесь можно добавить логирование

        result.append(
            SavedSearch(
                id=search.id,
                name=search.name,
                query=search.query,
                filters=filters_dict,
                user_id=search.user_id,
                is_public=search.is_public,
                created_at=search.created_at.isoformat(),
                updated_at=search.updated_at.isoformat(),
            )
        )

    return result


@router.delete("/saved-searches/{search_id}")
async def delete_saved_search(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Удалить сохраненный поиск"""

    # TODO: Реализовать удаление в SearchService
    raise HTTPException(status_code=501, detail="Функция в разработке")


@router.post("/reindex", response_model=ReindexResponse)
async def reindex_search(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReindexResponse:
    """Переиндексировать все сущности (только для администраторов)"""

    # TODO: Проверка прав администратора
    search_service = SearchService(db)

    await search_service.reindex_all()

    return ReindexResponse(
        message="Переиндексация завершена",
        reindexed_entities=0,  # TODO: Подсчитать количество
    )


@router.get("/suggestions", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(
    q: str = Query(..., min_length=1, max_length=100, description="Начало запроса"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchSuggestionsResponse:
    """Получить подсказки для поиска"""

    # TODO: Реализовать подсказки на основе частых запросов
    from app.schemas.search import SearchSuggestion

    suggestions = [
        SearchSuggestion(text=f"{q} задача", type="task", count=10),
        SearchSuggestion(text=f"{q} проект", type="project", count=5),
    ]

    return SearchSuggestionsResponse(
        suggestions=suggestions,
        query=q,
    )
