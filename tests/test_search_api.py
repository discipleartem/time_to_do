"""
Тесты для API поиска
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_search_post(client: AsyncClient, test_user_token: str):
    """Тест поиска через POST"""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.post(
        "/api/v1/search/search",
        headers=headers,
        json={
            "query": "test",
            "limit": 10,
            "offset": 0,
            "include_public": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total_count" in data
    assert "query" in data
    assert data["query"] == "test"
    assert isinstance(data["results"], list)
    assert isinstance(data["total_count"], int)


@pytest.mark.asyncio
async def test_search_get(client: AsyncClient, test_user_token: str):
    """Тест поиска через GET"""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.get(
        "/api/v1/search/search",
        headers=headers,
        params={
            "q": "test",
            "limit": 10,
            "offset": 0,
            "public": "true",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total_count" in data
    assert data["query"] == "test"


@pytest.mark.asyncio
async def test_search_with_entity_types(client: AsyncClient, test_user_token: str):
    """Тест поиска с фильтром по типам сущностей"""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.post(
        "/api/v1/search/search",
        headers=headers,
        json={
            "query": "test",
            "entity_types": ["task"],
            "limit": 10,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["results"], list)

    # Проверяем, что все результаты имеют тип task
    for result in data["results"]:
        assert result["entity_type"] == "task"


@pytest.mark.asyncio
async def test_search_invalid_entity_type(client: AsyncClient, test_user_token: str):
    """Тест поиска с невалидным типом сущности"""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.post(
        "/api/v1/search/search",
        headers=headers,
        json={
            "query": "test",
            "entity_types": [
                "nonexistent_type"
            ],  # Используем действительно несуществующий тип
            "limit": 10,
            "offset": 0,
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_search_unauthorized(client: AsyncClient):
    """Тест поиска без авторизации"""
    response = await client.post(
        "/api/v1/search/search",
        json={
            "query": "test",
            "limit": 10,
            "offset": 0,
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_empty_query(client: AsyncClient, test_user_token: str):
    """Тест поиска с пустым запросом"""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.post(
        "/api/v1/search/search",
        headers=headers,
        json={
            "query": "",
            "limit": 10,
            "offset": 0,
        },
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_save_search(client: AsyncClient, test_user_token: str):
    """Тест сохранения поиска"""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.post(
        "/api/v1/search/saved-searches",
        headers=headers,
        json={
            "name": "Test Search",
            "query": "test query",
            "filters": {"entity_types": ["task"], "limit": 20},
            "is_public": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Search"
    assert data["query"] == "test query"
    assert data["is_public"] is False
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_save_search_invalid_data(client: AsyncClient, test_user_token: str):
    """Тест сохранения поиска с невалидными данными"""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.post(
        "/api/v1/search/saved-searches",
        headers=headers,
        json={
            "name": "",  # Пустое имя
            "query": "test query",
        },
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_saved_searches(client: AsyncClient, test_user_token: str):
    """Тест получения сохраненных поисков"""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    # Сначала создаем сохраненный поиск
    create_response = await client.post(
        "/api/v1/search/saved-searches",
        headers=headers,
        json={
            "name": "Test Search",
            "query": "test query",
            "is_public": False,
        },
    )

    # Проверяем, что поиск создан успешно
    assert create_response.status_code == 200

    # Получаем список сохраненных поисков (только свои, без публичных)
    response = await client.get(
        "/api/v1/search/saved-searches?public=false",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Проверяем структуру ответа
    for search in data:
        assert "id" in search
        assert "name" in search
        assert "query" in search
        assert "is_public" in search
        assert "created_at" in search


@pytest.mark.asyncio
async def test_get_saved_searches_unauthorized(client: AsyncClient):
    """Тест получения сохраненных поисков без авторизации"""
    response = await client.get("/api/v1/search/saved-searches")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_suggestions(client: AsyncClient, test_user_token: str):
    """Тест получения подсказок поиска"""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.get(
        "/api/v1/search/suggestions",
        headers=headers,
        params={"q": "test"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert "query" in data
    assert data["query"] == "test"
    assert isinstance(data["suggestions"], list)


@pytest.mark.asyncio
async def test_search_suggestions_unauthorized(client: AsyncClient):
    """Тест получения подсказок без авторизации"""
    response = await client.get("/api/v1/search/suggestions")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_reindex_search(client: AsyncClient, test_user_token: str):
    """Тест переиндексации"""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.post(
        "/api/v1/search/reindex",
        headers=headers,
    )

    # Должен вернуть 501 (функция в разработке) или 200
    assert response.status_code in [200, 501]


@pytest.mark.asyncio
async def test_delete_saved_search(client: AsyncClient, test_user_token: str):
    """Тест удаления сохраненного поиска"""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    # Сначала создаем сохраненный поиск
    create_response = await client.post(
        "/api/v1/search/saved-searches",
        headers=headers,
        json={
            "name": "Test Search to Delete",
            "query": "test query",
            "is_public": False,
        },
    )

    assert create_response.status_code == 200
    search_id = create_response.json()["id"]

    # Удаляем сохраненный поиск
    response = await client.delete(
        f"/api/v1/search/saved-searches/{search_id}",
        headers=headers,
    )

    # Должен вернуть 501 (функция в разработке)
    assert response.status_code == 501


@pytest.mark.asyncio
async def test_search_with_project_filter(client: AsyncClient, test_user_token: str):
    """Тест поиска с фильтром по проектам"""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.post(
        "/api/v1/search/search",
        headers=headers,
        json={
            "query": "test",
            "project_ids": ["550e8400-e29b-41d4-a716-446655440000"],  # UUID проекта
            "limit": 10,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["results"], list)


@pytest.mark.asyncio
async def test_search_limit_validation(client: AsyncClient, test_user_token: str):
    """Тест валидации лимита поиска"""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    # Тест с лимитом больше 100
    response = await client.post(
        "/api/v1/search/search",
        headers=headers,
        json={
            "query": "test",
            "limit": 150,  # Больше максимума
            "offset": 0,
        },
    )

    assert response.status_code == 422  # Validation error

    # Тест с лимитом меньше 1
    response = await client.post(
        "/api/v1/search/search",
        headers=headers,
        json={
            "query": "test",
            "limit": 0,  # Меньше минимума
            "offset": 0,
        },
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_search_offset_validation(client: AsyncClient, test_user_token: str):
    """Тест валидации смещения поиска"""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.post(
        "/api/v1/search/search",
        headers=headers,
        json={
            "query": "test",
            "limit": 10,
            "offset": -1,  # Отрицательное смещение
        },
    )

    assert response.status_code == 422  # Validation error
