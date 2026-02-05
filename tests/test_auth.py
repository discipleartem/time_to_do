"""
Тесты аутентификации
"""

from httpx import AsyncClient


class TestAuth:
    """Тесты аутентификации"""

    async def test_register_user(self, client: AsyncClient, test_user_data: dict):
        """Тест регистрации пользователя"""
        response = await client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == 201
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == test_user_data["email"]
        assert data["user"]["username"] == test_user_data["username"]

    async def test_register_duplicate_email(
        self, client: AsyncClient, test_user_data: dict
    ):
        """Тест регистрации с дублирующим email"""
        # Первая регистрация
        await client.post("/api/v1/auth/register", json=test_user_data)

        # Вторая регистрация с тем же email
        response = await client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == 400
        assert "Пользователь с таким email уже существует" in response.json()["detail"]

    async def test_login_user(self, client: AsyncClient, test_user_data: dict):
        """Тест входа пользователя"""
        # Регистрация
        await client.post("/api/v1/auth/register", json=test_user_data)

        # Вход
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        }
        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data

    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Тест входа с неверными учетными данными"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword",
        }
        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        assert "Неверный email или пароль" in response.json()["detail"]

    async def test_get_current_user(self, client: AsyncClient, test_user_data: dict):
        """Тест получения текущего пользователя"""
        # Используем уникальный email для этого теста
        user_data = test_user_data.copy()
        user_data["email"] = "get_current_user@example.com"
        user_data["username"] = "get_current_user"

        # Регистрация
        register_response = await client.post("/api/v1/auth/register", json=user_data)
        token = register_response.json()["access_token"]

        # Получение текущего пользователя
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]

    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Тест получения текущего пользователя без токена"""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401  # Без токена возвращается 401

    async def test_refresh_token(self, client: AsyncClient, test_user_data: dict):
        """Тест обновления токена"""
        # Используем уникальный email для этого теста
        user_data = test_user_data.copy()
        user_data["email"] = "refresh_token@example.com"
        user_data["username"] = "refresh_token"

        # Регистрация
        register_response = await client.post("/api/v1/auth/register", json=user_data)
        refresh_token = register_response.json()["refresh_token"]

        # Обновление токена
        refresh_data = {"refresh_token": refresh_token}
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_change_password(self, client: AsyncClient, test_user_data: dict):
        """Тест изменения пароля"""
        import uuid

        unique_suffix = uuid.uuid4().hex[:8]

        # Используем уникальный email для этого теста
        user_data = test_user_data.copy()
        user_data["email"] = f"change_password_{unique_suffix}@example.com"
        user_data["username"] = f"change_password_{unique_suffix}"

        # Регистрация
        register_response = await client.post("/api/v1/auth/register", json=user_data)
        token = register_response.json()["access_token"]

        # Изменение пароля
        password_data = {
            "current_password": test_user_data["password"],
            "new_password": "newpassword123",
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            "/api/v1/auth/change-password", json=password_data, headers=headers
        )

        assert response.status_code == 200
        assert "Пароль успешно изменен" in response.json()["message"]

    async def test_logout(self, client: AsyncClient, test_user_data: dict):
        """Тест выхода"""
        # Используем уникальный email для этого теста
        user_data = test_user_data.copy()
        user_data["email"] = "logout@example.com"
        user_data["username"] = "logout"

        # Регистрация
        register_response = await client.post("/api/v1/auth/register", json=user_data)
        token = register_response.json()["access_token"]

        # Выход
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post("/api/v1/auth/logout", headers=headers)

        assert response.status_code == 200
        assert "Выполнен выход" in response.json()["message"]
