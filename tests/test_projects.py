"""
Тесты управления проектами
"""

import uuid

from httpx import AsyncClient

from app.schemas.project import ProjectUpdate


class TestProjects:
    """Тесты управления проектами"""

    async def get_auth_headers(self, client: AsyncClient, test_user_data: dict) -> dict:
        """Получение заголовков авторизации"""
        # Используем уникальный email для каждого вызова
        unique_id = str(uuid.uuid4())[:8]
        user_data = test_user_data.copy()
        user_data["email"] = f"projects_{unique_id}@example.com"
        user_data["username"] = f"projects_user_{unique_id}"

        response = await client.post("/api/v1/auth/register", json=user_data)
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    async def test_create_project(
        self, client: AsyncClient, test_user_data: dict, test_project_data: dict
    ):
        """Тест создания проекта"""
        headers = await self.get_auth_headers(client, test_user_data)

        response = await client.post(
            "/api/v1/projects/", json=test_project_data, headers=headers
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == test_project_data["name"]
        assert data["description"] == test_project_data["description"]
        assert data["is_public"] == test_project_data["is_public"]
        assert "id" in data
        assert "created_at" in data

    async def test_get_projects(
        self, client: AsyncClient, test_user_data: dict, test_project_data: dict
    ):
        """Тест получения списка проектов"""
        headers = await self.get_auth_headers(client, test_user_data)

        # Создаем проект
        await client.post("/api/v1/projects/", json=test_project_data, headers=headers)

        # Получаем список проектов
        response = await client.get("/api/v1/projects/", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["name"] == test_project_data["name"]

    async def test_get_project(
        self, client: AsyncClient, test_user_data: dict, test_project_data: dict
    ):
        """Тест получения информации о проекте"""
        headers = await self.get_auth_headers(client, test_user_data)

        # Создаем проект
        create_response = await client.post(
            "/api/v1/projects/", json=test_project_data, headers=headers
        )
        project_id = create_response.json()["id"]

        # Получаем информацию о проекте
        response = await client.get(f"/api/v1/projects/{project_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == project_id
        assert data["name"] == test_project_data["name"]

    async def test_update_project(
        self, client: AsyncClient, test_user_data: dict, test_project_data: dict
    ):
        """Тест обновления проекта"""
        headers = await self.get_auth_headers(client, test_user_data)

        # Создаем проект
        create_response = await client.post(
            "/api/v1/projects/", json=test_project_data, headers=headers
        )
        project_id = create_response.json()["id"]

        # Обновляем проект
        project_update = ProjectUpdate(name="Updated Project Name")
        update_data = project_update.model_dump(exclude_unset=True)
        response = await client.put(
            f"/api/v1/projects/{project_id}", json=update_data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == update_data["name"]

    async def test_delete_project(
        self, client: AsyncClient, test_user_data: dict, test_project_data: dict
    ):
        """Тест удаления проекта"""
        headers = await self.get_auth_headers(client, test_user_data)

        # Создаем проект
        create_response = await client.post(
            "/api/v1/projects/", json=test_project_data, headers=headers
        )
        project_id = create_response.json()["id"]

        # Удаляем проект (владелец может удалять)
        response = await client.delete(
            f"/api/v1/projects/{project_id}", headers=headers
        )

        assert response.status_code == 200  # Владелец может удалить проект
        assert "Проект успешно удален" in response.json()["message"]

        # Проверяем, что проект удален
        get_response = await client.get(
            f"/api/v1/projects/{project_id}", headers=headers
        )
        assert get_response.status_code == 404  # Проект не найден

    async def test_create_project_unauthorized(
        self, client: AsyncClient, test_project_data: dict
    ):
        """Тест создания проекта без авторизации"""
        response = await client.post("/api/v1/projects/", json=test_project_data)

        assert response.status_code == 401  # Без токена возвращается 401

    async def test_get_project_unauthorized(
        self, client: AsyncClient, test_project_data: dict
    ):
        """Тест получения проекта без авторизации"""
        response = await client.get("/api/v1/projects/some-project-id")

        assert response.status_code == 401  # Без токена возвращается 401

    async def test_get_nonexistent_project(
        self, client: AsyncClient, test_user_data: dict
    ):
        """Тест получения несуществующего проекта"""
        headers = await self.get_auth_headers(client, test_user_data)

        # Используем валидный, но несуществующий UUID
        nonexistent_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(
            f"/api/v1/projects/{nonexistent_id}", headers=headers
        )

        assert response.status_code == 404
        assert "Ресурс не найден" in response.json()["detail"]
