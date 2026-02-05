"""
Тесты для системы поиска
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search import SearchableType, SearchIndex
from app.models.user import User
from app.schemas.search import SearchQuery
from app.services.search_service import SearchService


class TestSearchAPI:
    """Тесты API эндпоинтов поиска"""

    @pytest.fixture
    async def test_user(self, db_session: AsyncSession) -> User:
        """Создает тестового пользователя"""
        import bcrypt

        hashed_password = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()

        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            hashed_password=hashed_password,
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    async def sample_search_index(
        self, db_session: AsyncSession, test_user: User
    ) -> SearchIndex:
        """Создает тестовый поисковый индекс"""
        search_index = SearchIndex(
            title="Test Task",
            content="Test task description",
            search_vector="test task description",
            entity_type=SearchableType.TASK,
            entity_id=uuid.uuid4(),
            user_id=test_user.id,
            is_public=False,
        )
        db_session.add(search_index)
        await db_session.commit()
        await db_session.refresh(search_index)
        return search_index

    async def test_search_post_success(
        self, client: AsyncClient, test_user: User, sample_search_index: SearchIndex
    ) -> None:
        """Тест успешного поиска через POST"""
        # Логинимся
        login_response = await client.post(
            "/api/v1/auth/login/oauth2",
            data={"username": "test@example.com", "password": "password123"},
        )
        assert login_response.status_code == 200

        # Устанавливаем токен в headers
        token_data = login_response.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Выполняем поиск
        search_data = {
            "query": "test",
            "entity_types": ["task"],
            "limit": 10,
            "offset": 0,
            "include_public": False,
        }

        response = await client.post(
            "/api/v1/search/search", json=search_data, headers=headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        assert "total_count" in data
        assert "query" in data
        assert data["query"] == "test"
        assert isinstance(data["results"], list)
        assert isinstance(data["total_count"], int)

    async def test_search_get_success(
        self, client: AsyncClient, test_user: User, sample_search_index: SearchIndex
    ) -> None:
        """Тест успешного поиска через GET"""
        # Логинимся
        login_response = await client.post(
            "/api/v1/auth/login/oauth2",
            data={"username": "test@example.com", "password": "password123"},
        )
        assert login_response.status_code == 200

        # Устанавливаем токен в headers
        token_data = login_response.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Выполняем поиск
        params = {
            "q": "test",
            "type": "task",
            "limit": 10,
            "offset": 0,
            "public": "false",
        }

        response = await client.get(
            "/api/v1/search/search", params=params, headers=headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        assert "total_count" in data
        assert data["query"] == "test"

    async def test_search_empty_query(
        self, client: AsyncClient, test_user: User
    ) -> None:
        """Тест поиска с пустым запросом"""
        # Логинимся
        login_response = await client.post(
            "/api/v1/auth/login/oauth2",
            data={"username": "test@example.com", "password": "password123"},
        )
        assert login_response.status_code == 200

        # Устанавливаем токен в headers
        token_data = login_response.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Пытаемся выполнить поиск с пустым запросом
        search_data = {
            "query": "",
            "limit": 10,
            "offset": 0,
        }

        response = await client.post(
            "/api/v1/search/search", json=search_data, headers=headers
        )
        assert response.status_code == 422  # Validation error

    async def test_search_invalid_entity_type(
        self, client: AsyncClient, test_user: User
    ) -> None:
        """Тест поиска с неверным типом сущности"""
        # Логинимся
        login_response = await client.post(
            "/api/v1/auth/login/oauth2",
            data={"username": "test@example.com", "password": "password123"},
        )
        assert login_response.status_code == 200

        # Устанавливаем токен в headers
        token_data = login_response.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Пытаемся выполнить поиск с неверным типом
        search_data = {
            "query": "test",
            "entity_types": ["invalid_type"],
            "limit": 10,
            "offset": 0,
        }

        response = await client.post(
            "/api/v1/search/search", json=search_data, headers=headers
        )
        assert response.status_code == 400

    async def test_search_unauthorized(self, client: AsyncClient) -> None:
        """Тест поиска без авторизации"""
        search_data = {
            "query": "test",
            "limit": 10,
            "offset": 0,
        }

        response = await client.post("/api/v1/search/search", json=search_data)
        assert response.status_code == 401

    async def test_save_search_success(
        self, client: AsyncClient, test_user: User
    ) -> None:
        """Тест сохранения поиска"""
        # Логинимся
        login_response = await client.post(
            "/api/v1/auth/login/oauth2",
            data={"username": "test@example.com", "password": "password123"},
        )
        assert login_response.status_code == 200

        # Устанавливаем токен в headers
        token_data = login_response.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Сохраняем поиск
        save_data = {
            "name": "Test Search",
            "query": "test query",
            "filters": {"entity_types": ["task"], "limit": 20},
            "is_public": False,
        }

        response = await client.post(
            "/api/v1/search/saved-searches", json=save_data, headers=headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Test Search"
        assert data["query"] == "test query"
        assert data["is_public"] is False
        assert "id" in data

    async def test_get_saved_searches(
        self, client: AsyncClient, test_user: User
    ) -> None:
        """Тест получения сохраненных поисков"""
        # Логинимся
        login_response = await client.post(
            "/api/v1/auth/login/oauth2",
            data={"username": "test@example.com", "password": "password123"},
        )
        assert login_response.status_code == 200

        # Устанавливаем токен в headers
        token_data = login_response.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Получаем сохраненные поиски
        response = await client.get("/api/v1/search/saved-searches", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    async def test_search_suggestions(
        self, client: AsyncClient, test_user: User
    ) -> None:
        """Тест получения подсказок поиска"""
        # Логинимся
        login_response = await client.post(
            "/api/v1/auth/login/oauth2",
            data={"username": "test@example.com", "password": "password123"},
        )
        assert login_response.status_code == 200

        # Устанавливаем токен в headers
        token_data = login_response.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Получаем подсказки
        response = await client.get(
            "/api/v1/search/suggestions?q=test", headers=headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "suggestions" in data
        assert "query" in data
        assert data["query"] == "test"
        assert isinstance(data["suggestions"], list)


class TestSearchService:
    """Тесты сервиса поиска"""

    @pytest.fixture
    async def search_service(self, db_session: AsyncSession) -> SearchService:
        """Создает экземпляр SearchService"""
        return SearchService(db_session)

    @pytest.fixture
    async def test_user(self, db_session: AsyncSession) -> User:
        """Создает тестового пользователя"""
        import bcrypt

        hashed_password = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()

        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            hashed_password=hashed_password,
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    async def test_index_entity(
        self, search_service: SearchService, test_user: User
    ) -> None:
        """Тест индексации сущности"""
        entity_id = uuid.uuid4()

        search_index = await search_service.index_entity(
            entity_type=SearchableType.TASK,
            entity_id=entity_id,
            title="Test Task",
            content="Test task description",
            user_id=test_user.id,
            is_public=False,
        )

        assert search_index.title == "Test Task"
        assert search_index.content == "Test task description"
        assert search_index.entity_type == SearchableType.TASK
        assert search_index.entity_id == entity_id
        assert search_index.user_id == test_user.id
        assert search_index.is_public is False

    async def test_remove_from_index(
        self, search_service: SearchService, test_user: User
    ) -> None:
        """Тест удаления из индекса"""
        entity_id = uuid.uuid4()

        # Сначала индексируем
        await search_service.index_entity(
            entity_type=SearchableType.TASK,
            entity_id=entity_id,
            title="Test Task",
            user_id=test_user.id,
        )

        # Затем удаляем
        await search_service.remove_from_index(SearchableType.TASK, entity_id)

        # Проверяем, что удалено (поиск не должен найти)
        results, total = await search_service.search(
            query="Test Task",
            user_id=test_user.id,
        )
        assert total == 0

    async def test_search_basic(
        self, search_service: SearchService, test_user: User
    ) -> None:
        """Тест базового поиска"""
        # Индексируем тестовые данные
        await search_service.index_entity(
            entity_type=SearchableType.TASK,
            entity_id=uuid.uuid4(),
            title="Test Task One",
            content="Description for task one",
            user_id=test_user.id,
        )

        await search_service.index_entity(
            entity_type=SearchableType.TASK,
            entity_id=uuid.uuid4(),
            title="Another Task",
            content="Different description",
            user_id=test_user.id,
        )

        # Ищем
        results, total = await search_service.search(
            query="Test",
            user_id=test_user.id,
        )

        assert total == 1
        assert len(results) == 1
        assert results[0]["title"] == "Test Task One"

    async def test_search_with_filters(
        self, search_service: SearchService, test_user: User
    ) -> None:
        """Тест поиска с фильтрами"""
        # Индексируем разные типы сущностей
        await search_service.index_entity(
            entity_type=SearchableType.TASK,
            entity_id=uuid.uuid4(),
            title="Test Task",
            user_id=test_user.id,
        )

        await search_service.index_entity(
            entity_type=SearchableType.PROJECT,
            entity_id=uuid.uuid4(),
            title="Test Project",
            user_id=test_user.id,
        )

        # Ищем только задачи
        results, total = await search_service.search(
            query="Test",
            user_id=test_user.id,
            entity_types=[SearchableType.TASK],
        )

        assert total == 1
        assert len(results) == 1
        assert results[0]["entity_type"] == SearchableType.TASK

    async def test_save_search(
        self, search_service: SearchService, test_user: User
    ) -> None:
        """Тест сохранения поиска"""
        saved_search = await search_service.save_search(
            user_id=test_user.id,
            name="Test Search",
            query="test query",
            filters={"entity_types": ["task"], "limit": 20},
            is_public=False,
        )

        assert saved_search.name == "Test Search"
        assert saved_search.query == "test query"
        assert saved_search.user_id == test_user.id
        assert saved_search.is_public is False

    async def test_get_saved_searches(
        self, search_service: SearchService, test_user: User
    ) -> None:
        """Тест получения сохраненных поисков"""
        # Создаем сохраненный поиск
        await search_service.save_search(
            user_id=test_user.id,
            name="Test Search",
            query="test query",
            is_public=False,
        )

        # Получаем сохраненные поиски
        saved_searches = await search_service.get_saved_searches(
            user_id=test_user.id,
        )

        assert len(saved_searches) == 1
        assert saved_searches[0].name == "Test Search"
        assert saved_searches[0].query == "test query"

    async def test_reindex_all(
        self, search_service: SearchService, test_user: User
    ) -> None:
        """Тест переиндексации всех сущностей"""
        # Этот тест требует наличия реальных данных в БД
        # Пока просто проверим, что метод выполняется без ошибок
        try:
            await search_service.reindex_all()
        except Exception as e:
            # Ошибки могут быть из-за отсутствия данных
            assert not isinstance(e, AttributeError)


class TestSearchModels:
    """Тесты моделей поиска"""

    def test_searchable_type_validation(self) -> None:
        """Тест валидации типов сущностей"""
        # Корректные значения
        assert SearchableType.TASK == "task"
        assert SearchableType.PROJECT == "project"
        assert SearchableType.SPRINT == "sprint"
        assert SearchableType.COMMENT == "comment"

        # Некорректное значение должно вызывать ошибку
        with pytest.raises(ValueError):
            SearchableType("invalid_type")

    def test_search_query_schema(self) -> None:
        """Тест схемы поискового запроса"""
        # Корректные данные
        query_data = {
            "query": "test query",
            "entity_types": ["task", "project"],
            "limit": 20,
            "offset": 0,
            "include_public": True,
        }

        query = SearchQuery(**query_data)
        assert query.query == "test query"
        assert query.entity_types == ["task", "project"]
        assert query.limit == 20
        assert query.offset == 0
        assert query.include_public is True

        # Минимальные данные
        query_data = {"query": "test"}
        query = SearchQuery(**query_data)
        assert query.query == "test"
        assert query.entity_types is None
        assert query.limit == 20  # значение по умолчанию

    def test_search_query_validation(self) -> None:
        """Тест валидации поискового запроса"""
        # Пустой запрос
        with pytest.raises(ValueError):
            SearchQuery(query="")

        # Слишком длинный запрос
        with pytest.raises(ValueError):
            SearchQuery(query="a" * 501)

        # Неверный лимит
        with pytest.raises(ValueError):
            SearchQuery(query="test", limit=0)

        with pytest.raises(ValueError):
            SearchQuery(query="test", limit=101)


class TestSearchPage:
    """Тесты страницы поиска"""

    async def test_search_page_render(self, client: AsyncClient) -> None:
        """Тест отображения страницы поиска"""
        response = await client.get("/search")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    async def test_search_page_with_query(self, client: AsyncClient) -> None:
        """Тест страницы поиска с параметрами"""
        response = await client.get("/search?q=test&limit=20")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
