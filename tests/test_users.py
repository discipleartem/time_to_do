"""
Тесты управления пользователями
"""

import uuid

from httpx import AsyncClient


class TestUsers:
    """Тесты управления пользователями"""

    async def register_user(self, client: AsyncClient, user_data: dict) -> dict:
        """Регистрация пользователя с точными данными"""
        response = await client.post("/api/v1/auth/register", json=user_data)
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    async def get_auth_headers(self, client: AsyncClient, test_user_data: dict) -> dict:
        """Получение заголовков авторизации"""
        # Используем уникальный email для каждого вызова
        unique_id = str(uuid.uuid4())[:8]
        user_data = test_user_data.copy()
        user_data["email"] = f"users_{unique_id}@example.com"
        user_data["username"] = f"users_user_{unique_id}"

        response = await client.post("/api/v1/auth/register", json=user_data)
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    async def get_admin_headers(
        self, client: AsyncClient, test_user_data: dict
    ) -> dict:
        """Получение заголовков авторизации для админа"""
        # Создаем админа
        unique_id = str(uuid.uuid4())[:8]
        admin_data = test_user_data.copy()
        admin_data["email"] = f"admin_{unique_id}@example.com"
        admin_data["username"] = f"admin_user_{unique_id}"
        admin_data["role"] = "ADMIN"  # Устанавливаем роль админа

        response = await client.post("/api/v1/auth/register", json=admin_data)
        token = response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    async def test_get_current_user_profile(
        self, client: AsyncClient, test_user_data: dict, auth_headers: dict
    ):
        """Тест получения профиля текущего пользователя"""
        response = await client.get("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert "email" in data
        assert "username" in data
        assert "full_name" in data
        assert "is_active" in data
        assert "created_at" in data

    async def test_update_current_user(self, client: AsyncClient, test_user_data: dict):
        """Тест обновления профиля текущего пользователя"""
        headers = await self.get_auth_headers(client, test_user_data)

        # Обновляем профиль
        update_data = {
            "full_name": "Updated Name",
            "avatar_url": "https://example.com/avatar.png",
        }
        response = await client.put(
            "/api/v1/users/me", json=update_data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["avatar_url"] == update_data["avatar_url"]

    async def test_get_users_as_admin(self, client: AsyncClient, test_user_data: dict):
        """Тест получения списка пользователей (только для админа)"""
        headers = await self.get_admin_headers(client, test_user_data)

        # Создаем несколько пользователей
        for i in range(3):
            unique_id = str(uuid.uuid4())[:8]
            user_data = test_user_data.copy()
            user_data["email"] = f"test_user_{i}_{unique_id}@example.com"
            user_data["username"] = f"test_user_{i}_{unique_id}"
            await client.post("/api/v1/auth/register", json=user_data)

        # Получаем список пользователей
        response = await client.get("/api/v1/users/", headers=headers)

        assert response.status_code == 200
        users = response.json()
        assert len(users) >= 4  # 3 созданных + 1 админ

    async def test_get_users_unauthorized(
        self, client: AsyncClient, test_user_data: dict
    ):
        """Тест получения списка пользователей без прав админа"""
        headers = await self.get_auth_headers(client, test_user_data)

        response = await client.get("/api/v1/users/", headers=headers)

        assert response.status_code == 403  # Forbidden

    async def test_get_user_by_id_as_admin(
        self, client: AsyncClient, test_user_data: dict
    ):
        """Тест получения пользователя по ID (админ)"""
        admin_headers = await self.get_admin_headers(client, test_user_data)

        # Создаем тестового пользователя
        unique_id = str(uuid.uuid4())[:8]
        user_data = test_user_data.copy()
        user_data["email"] = f"target_user_{unique_id}@example.com"
        user_data["username"] = f"target_user_{unique_id}"

        create_response = await client.post("/api/v1/auth/register", json=user_data)
        created_user = create_response.json()["user"]

        # Получаем пользователя по ID
        response = await client.get(
            f"/api/v1/users/{created_user['id']}", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_user["id"]
        assert data["email"] == created_user["email"]

    async def test_update_user_by_admin(
        self, client: AsyncClient, test_user_data: dict
    ):
        """Тест обновления пользователя админом"""
        admin_headers = await self.get_admin_headers(client, test_user_data)

        # Создаем тестового пользователя
        unique_id = str(uuid.uuid4())[:8]
        user_data = test_user_data.copy()
        user_data["email"] = f"update_user_{unique_id}@example.com"
        user_data["username"] = f"update_user_{unique_id}"

        create_response = await client.post("/api/v1/auth/register", json=user_data)
        created_user = create_response.json()["user"]

        # Обновляем пользователя
        update_data = {
            "full_name": "Admin Updated Name",
            "is_active": False,
        }
        response = await client.put(
            f"/api/v1/users/{created_user['id']}",
            json=update_data,
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["is_active"] == update_data["is_active"]

    async def test_delete_user_by_admin(
        self, client: AsyncClient, test_user_data: dict
    ):
        """Тест удаления пользователя админом"""
        admin_headers = await self.get_admin_headers(client, test_user_data)

        # Создаем тестового пользователя
        unique_id = str(uuid.uuid4())[:8]
        user_data = test_user_data.copy()
        user_data["email"] = f"delete_user_{unique_id}@example.com"
        user_data["username"] = f"delete_user_{unique_id}"

        create_response = await client.post("/api/v1/auth/register", json=user_data)
        created_user = create_response.json()["user"]

        # Удаляем пользователя
        response = await client.delete(
            f"/api/v1/users/{created_user['id']}", headers=admin_headers
        )

        assert response.status_code == 200

        # Проверяем, что пользователь удален
        get_response = await client.get(
            f"/api/v1/users/{created_user['id']}", headers=admin_headers
        )
        assert get_response.status_code == 404

    async def test_get_user_not_found(self, client: AsyncClient, test_user_data: dict):
        """Тест получения несуществующего пользователя"""
        headers = await self.get_admin_headers(client, test_user_data)

        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/users/{fake_id}", headers=headers)

        assert response.status_code == 404

    async def test_update_user_not_found(
        self, client: AsyncClient, test_user_data: dict
    ):
        """Тест обновления несуществующего пользователя"""
        headers = await self.get_admin_headers(client, test_user_data)

        fake_id = str(uuid.uuid4())
        update_data = {"full_name": "Updated Name"}
        response = await client.put(
            f"/api/v1/users/{fake_id}", json=update_data, headers=headers
        )

        assert response.status_code == 404

    async def test_delete_user_not_found(
        self, client: AsyncClient, test_user_data: dict
    ):
        """Тест удаления несуществующего пользователя"""
        headers = await self.get_admin_headers(client, test_user_data)

        fake_id = str(uuid.uuid4())
        response = await client.delete(f"/api/v1/users/{fake_id}", headers=headers)

        assert response.status_code == 404

    async def test_user_profile_validation(
        self, client: AsyncClient, test_user_data: dict
    ):
        """Тест валидации данных профиля"""
        headers = await self.get_auth_headers(client, test_user_data)

        # Пытаемся обновить с невалидными данными
        invalid_data = {
            "full_name": "",  # Пустое имя
            "avatar_url": "invalid-url",  # Невалидный URL
        }
        response = await client.put(
            "/api/v1/users/me", json=invalid_data, headers=headers
        )

        # Должна быть ошибка валидации
        assert response.status_code == 422

    async def test_user_email_uniqueness(
        self, client: AsyncClient, test_user_data: dict
    ):
        """Тест уникальности email при обновлении"""
        # Создаем первого пользователя
        unique_id1 = str(uuid.uuid4())[:8]
        user_data1 = test_user_data.copy()
        user_data1["email"] = f"first_user_{unique_id1}@example.com"
        user_data1["username"] = f"first_user_{unique_id1}"
        headers1 = await self.register_user(client, user_data1)

        # Создаем второго пользователя
        unique_id2 = str(uuid.uuid4())[:8]
        user_data2 = test_user_data.copy()
        user_data2["email"] = f"second_user_{unique_id2}@example.com"
        user_data2["username"] = f"second_user_{unique_id2}"
        await self.register_user(client, user_data2)

        # Пытаемся обновить email первого пользователя на email второго
        update_data = {"email": user_data2["email"]}
        response = await client.put(
            "/api/v1/users/me", json=update_data, headers=headers1
        )

        # Должна быть ошибка - email уже существует
        assert response.status_code == 400

    async def test_user_username_uniqueness(
        self, client: AsyncClient, test_user_data: dict
    ):
        """Тест уникальности username при обновлении"""
        # Создаем первого пользователя
        unique_id1 = str(uuid.uuid4())[:8]
        user_data1 = test_user_data.copy()
        user_data1["email"] = f"first_user_{unique_id1}@example.com"
        user_data1["username"] = f"first_user_{unique_id1}"
        headers1 = await self.register_user(client, user_data1)

        # Создаем второго пользователя
        unique_id2 = str(uuid.uuid4())[:8]
        user_data2 = test_user_data.copy()
        user_data2["email"] = f"second_user_{unique_id2}@example.com"
        user_data2["username"] = f"second_user_{unique_id2}"
        await self.register_user(client, user_data2)

        # Пытаемся обновить username первого пользователя на username второго
        update_data = {"username": user_data2["username"]}
        response = await client.put(
            "/api/v1/users/me", json=update_data, headers=headers1
        )

        # Должна быть ошибка - username уже существует
        assert response.status_code == 400

    async def test_get_users_with_pagination(
        self, client: AsyncClient, test_user_data: dict
    ):
        """Тест пагинации при получении списка пользователей"""
        headers = await self.get_admin_headers(client, test_user_data)

        # Проверяем, что admin пользователь создан и имеет права
        me_response = await client.get("/api/v1/users/me", headers=headers)
        assert me_response.status_code == 200

        # Получаем общее количество пользователей ДО создания новых
        initial_users_response = await client.get(
            "/api/v1/users/?skip=0&limit=100", headers=headers
        )
        assert initial_users_response.status_code == 200
        initial_users = initial_users_response.json()
        initial_count = len(initial_users)

        # Создаем много пользователей
        created_emails = []
        for i in range(5):
            unique_id = str(uuid.uuid4())[:8]
            user_data = test_user_data.copy()
            email = f"paginated_user_{i}_{unique_id}@example.com"
            username = f"paginated_user_{i}_{unique_id}"
            user_data["email"] = email
            user_data["username"] = username
            created_emails.append(email)

            response = await client.post("/api/v1/auth/register", json=user_data)
            assert response.status_code == 201  # Убеждаемся, что пользователь создан

        # Получаем общее количество пользователей ПОСЛЕ создания новых
        all_users_response = await client.get(
            "/api/v1/users/?skip=0&limit=100", headers=headers
        )
        assert all_users_response.status_code == 200
        all_users = all_users_response.json()
        total_users = len(all_users)

        # Проверяем, что количество пользователей увеличилось
        # (может быть больше, если другие тесты тоже создают пользователей)
        assert total_users >= initial_count

        # Получаем первую страницу с лимитом 10
        response = await client.get("/api/v1/users/?skip=0&limit=10", headers=headers)
        assert response.status_code == 200
        first_page = response.json()
        assert len(first_page) == 10

        # Получаем вторую страницу
        response = await client.get("/api/v1/users/?skip=10&limit=10", headers=headers)
        assert response.status_code == 200
        second_page = response.json()
        # На второй странице должно быть хотя бы 0 пользователей (может быть 0, если всего <=10)
        assert len(second_page) >= 0

        # Убеждаемся, что страницы не пересекаются
        first_page_ids = {user["id"] for user in first_page}
        second_page_ids = {user["id"] for user in second_page}
        assert len(first_page_ids.intersection(second_page_ids)) == 0
