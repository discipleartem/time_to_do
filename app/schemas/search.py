"""
Pydantic схемы для поиска
"""

import uuid
from typing import Any

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Поисковый запрос"""

    query: str = Field(
        ..., min_length=1, max_length=500, description="Поисковый запрос"
    )
    entity_types: list[str] | None = Field(
        default=None,
        description="Типы сущностей для поиска (task, project, sprint, comment)",
    )
    project_ids: list[str] | None = Field(
        default=None,
        description="ID проектов для фильтрации",
    )
    limit: int = Field(default=20, ge=1, le=100, description="Лимит результатов")
    offset: int = Field(default=0, ge=0, description="Смещение для пагинации")
    include_public: bool = Field(default=True, description="Включать публичные объекты")


class SearchResult(BaseModel):
    """Результат поиска"""

    id: str = Field(..., description="ID результата поиска")
    entity_type: str = Field(..., description="Тип сущности")
    entity_id: str = Field(..., description="ID сущности")
    title: str = Field(..., description="Заголовок")
    content: str | None = Field(None, description="Содержимое")
    rank: float = Field(..., description="Релевантность")
    project_id: str | None = Field(None, description="ID проекта")
    is_public: bool = Field(..., description="Публичный ли объект")
    metadata: dict[str, Any] | None = Field(None, description="Метаданные")
    entity_data: dict[str, Any] | None = Field(None, description="Данные сущности")


class SearchResponse(BaseModel):
    """Ответ поиска"""

    results: list[SearchResult] = Field(..., description="Результаты поиска")
    total_count: int = Field(..., description="Общее количество результатов")
    query: str = Field(..., description="Исходный запрос")
    limit: int = Field(..., description="Лимит")
    offset: int = Field(..., description="Смещение")


class SaveSearchRequest(BaseModel):
    """Запрос на сохранение поиска"""

    name: str = Field(..., min_length=1, max_length=255, description="Название поиска")
    query: str = Field(
        ..., min_length=1, max_length=500, description="Поисковый запрос"
    )
    filters: dict[str, Any] | None = Field(None, description="Фильтры")
    is_public: bool = Field(default=False, description="Публичный ли поиск")


class SavedSearch(BaseModel):
    """Сохраненный поиск"""

    id: uuid.UUID = Field(..., description="ID")
    name: str = Field(..., description="Название")
    query: str = Field(..., description="Запрос")
    filters: dict[str, Any] | None = Field(None, description="Фильтры")
    user_id: uuid.UUID = Field(..., description="ID пользователя")
    is_public: bool = Field(..., description="Публичный ли поиск")
    created_at: str = Field(..., description="Дата создания")
    updated_at: str = Field(..., description="Дата обновления")


class ReindexResponse(BaseModel):
    """Ответ переиндексации"""

    message: str = Field(..., description="Сообщение")
    reindexed_entities: int = Field(
        ..., description="Количество переиндексированных сущностей"
    )


class SearchSuggestion(BaseModel):
    """Подсказка для поиска"""

    text: str = Field(..., description="Текст подсказки")
    type: str = Field(..., description="Тип подсказки")
    count: int = Field(..., description="Количество результатов")


class SearchSuggestionsResponse(BaseModel):
    """Ответ с подсказками"""

    suggestions: list[SearchSuggestion] = Field(..., description="Подсказки")
    query: str = Field(..., description="Исходный запрос")
