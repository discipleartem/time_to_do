"""
Тесты управления временными записями
"""

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient


class TestTimeEntries:
    """Тесты управления временными записями"""

    async def get_auth_headers(self, client: AsyncClient, test_user_data: dict) -> dict:
        """Получение заголовков авторизации"""
        # Используем уникальный email для каждого вызова
        unique_id = str(uuid.uuid4())[:8]
        user_data = test_user_data.copy()
        user_data["email"] = f"time_{unique_id}@example.com"
        user_data["username"] = f"time_user_{unique_id}"

        response = await client.post("/api/v1/auth/register", json=user_data)
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    async def create_test_project(
        self, client: AsyncClient, headers: dict, test_project_data: dict
    ) -> dict:
        """Создание тестового проекта"""
        response = await client.post(
            "/api/v1/projects/", json=test_project_data, headers=headers
        )
        return response.json()

    async def create_test_task(
        self, client: AsyncClient, headers: dict, project_id: str, test_task_data: dict
    ) -> dict:
        """Создание тестовой задачи"""
        task_data = test_task_data.copy()
        task_data["project_id"] = project_id
        response = await client.post("/api/v1/tasks/", json=task_data, headers=headers)
        return response.json()

    async def test_create_time_entry(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест создания временной записи"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)
        task = await self.create_test_task(
            client, headers, project["id"], test_task_data
        )

        # Создаем временную запись
        time_entry_data = {
            "task_id": task["id"],
            "description": "Work on feature implementation",
            "start_time": "2024-01-01T09:00:00",
            "end_time": "2024-01-01T11:00:00",
        }

        response = await client.post(
            "/api/v1/time-entries/", json=time_entry_data, headers=headers
        )

        assert response.status_code == 201
        data = response.json()

        assert data["task_id"] == task["id"]
        assert data["description"] == time_entry_data["description"]
        assert data["duration_minutes"] == 120  # 2 часа = 120 минут
        assert data["is_active"] is False
        assert "id" in data
        assert "created_at" in data

    async def test_create_time_entry_with_duration_only(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест создания временной записи только с длительностью"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)
        task = await self.create_test_task(
            client, headers, project["id"], test_task_data
        )

        # Создаем запись только с длительностью
        time_entry_data = {
            "task_id": task["id"],
            "description": "Quick task",
            "duration_minutes": 60,
        }

        response = await client.post(
            "/api/v1/time-entries/", json=time_entry_data, headers=headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["duration_minutes"] == 60

    async def test_start_timer(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест запуска таймера"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)
        task = await self.create_test_task(
            client, headers, project["id"], test_task_data
        )

        # Создаем запись с таймером
        time_entry_data = {
            "task_id": task["id"],
            "description": "Starting timer",
            "start_time": datetime.now(UTC).isoformat(),
        }

        response = await client.post(
            "/api/v1/time-entries/", json=time_entry_data, headers=headers
        )

        # Запускаем таймер
        response = await client.post(
            "/api/v1/time-entries/start", json={"task_id": task["id"]}, headers=headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["is_active"] is True

    async def test_stop_timer(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест остановки таймера"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)
        task = await self.create_test_task(
            client, headers, project["id"], test_task_data
        )

        # Создаем и запускаем таймер
        time_entry_data = {
            "task_id": task["id"],
            "description": "Timer task",
            "start_time": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
        }

        response = await client.post(
            "/api/v1/time-entries/", json=time_entry_data, headers=headers
        )

        # Запускаем таймер
        await client.post(
            "/api/v1/time-entries/start", json={"task_id": task["id"]}, headers=headers
        )

        # Останавливаем таймер
        response = await client.post("/api/v1/time-entries/stop", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        assert data["end_time"] is not None
        assert data["duration_minutes"] is not None

    async def test_get_time_entries(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест получения списка временных записей"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)
        task = await self.create_test_task(
            client, headers, project["id"], test_task_data
        )

        # Создаем несколько записей
        for i in range(3):
            time_entry_data = {
                "task_id": task["id"],
                "description": f"Work session {i}",
                "start_time": f"2024-01-0{i+1}T09:00:00",
                "end_time": f"2024-01-0{i+1}T11:00:00",
            }
            await client.post(
                "/api/v1/time-entries/", json=time_entry_data, headers=headers
            )

        # Получаем записи
        response = await client.get("/api/v1/time-entries/", headers=headers)

        assert response.status_code == 200
        entries = response.json()
        assert len(entries) == 3

    async def test_get_time_entries_by_task(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест фильтрации записей по задаче"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)
        task1 = await self.create_test_task(
            client, headers, project["id"], test_task_data
        )

        # Создаем вторую задачу
        task2_data = test_task_data.copy()
        task2_data["title"] = "Second Task"
        task2 = await self.create_test_task(client, headers, project["id"], task2_data)

        # Создаем записи для разных задач
        time_entry_data1 = {
            "task_id": task1["id"],
            "description": "Work on task 1",
            "start_time": "2024-01-01T09:00:00",
            "end_time": "2024-01-01T11:00:00",
        }
        await client.post(
            "/api/v1/time-entries/", json=time_entry_data1, headers=headers
        )

        time_entry_data2 = {
            "task_id": task2["id"],
            "description": "Work on task 2",
            "start_time": "2024-01-01T13:00:00",
            "end_time": "2024-01-01T15:00:00",
        }
        await client.post(
            "/api/v1/time-entries/", json=time_entry_data2, headers=headers
        )

        # Фильтруем по первой задаче
        response = await client.get(
            f"/api/v1/time-entries/?task_id={task1['id']}", headers=headers
        )

        assert response.status_code == 200
        entries = response.json()
        assert len(entries) == 1
        assert entries[0]["task_id"] == task1["id"]

    async def test_get_time_entries_by_date_range(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест фильтрации записей по диапазону дат"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)
        task = await self.create_test_task(
            client, headers, project["id"], test_task_data
        )

        # Создаем записи в разные дни
        time_entry_data1 = {
            "task_id": task["id"],
            "description": "Work on Jan 1",
            "start_time": "2024-01-01T09:00:00",
            "end_time": "2024-01-01T11:00:00",
        }
        await client.post(
            "/api/v1/time-entries/", json=time_entry_data1, headers=headers
        )

        time_entry_data2 = {
            "task_id": task["id"],
            "description": "Work on Jan 15",
            "start_time": "2024-01-15T09:00:00",
            "end_time": "2024-01-15T11:00:00",
        }
        await client.post(
            "/api/v1/time-entries/", json=time_entry_data2, headers=headers
        )

        # Фильтруем по диапазону дат
        response = await client.get(
            "/api/v1/time-entries/?date_from=2024-01-01&date_to=2024-01-10",
            headers=headers,
        )

        assert response.status_code == 200
        entries = response.json()
        assert len(entries) == 1
        assert "Jan 1" in entries[0]["description"]

    async def test_get_time_entry_by_id(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест получения временной записи по ID"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)
        task = await self.create_test_task(
            client, headers, project["id"], test_task_data
        )

        # Создаем запись
        time_entry_data = {
            "task_id": task["id"],
            "description": "Test entry",
            "start_time": "2024-01-01T09:00:00",
            "end_time": "2024-01-01T11:00:00",
        }
        create_response = await client.post(
            "/api/v1/time-entries/", json=time_entry_data, headers=headers
        )
        created_entry = create_response.json()

        # Получаем запись по ID
        response = await client.get(
            f"/api/v1/time-entries/{created_entry['id']}", headers=headers
        )

        assert response.status_code == 200
        entry = response.json()
        assert entry["id"] == created_entry["id"]
        assert entry["description"] == time_entry_data["description"]

    async def test_update_time_entry(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест обновления временной записи"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)
        task = await self.create_test_task(
            client, headers, project["id"], test_task_data
        )

        # Создаем запись
        time_entry_data = {
            "task_id": task["id"],
            "description": "Original description",
            "start_time": "2024-01-01T09:00:00",
            "end_time": "2024-01-01T11:00:00",
        }
        create_response = await client.post(
            "/api/v1/time-entries/", json=time_entry_data, headers=headers
        )
        created_entry = create_response.json()

        # Обновляем запись
        update_data = {
            "description": "Updated description",
            "start_time": "2024-01-01T08:00:00",
            "end_time": "2024-01-01T12:00:00",
        }
        response = await client.put(
            f"/api/v1/time-entries/{created_entry['id']}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == 200
        updated_entry = response.json()
        assert updated_entry["description"] == update_data["description"]
        assert updated_entry["duration_minutes"] == 240  # 4 часа

    async def test_delete_time_entry(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест удаления временной записи"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)
        task = await self.create_test_task(
            client, headers, project["id"], test_task_data
        )

        # Создаем запись
        time_entry_data = {
            "task_id": task["id"],
            "description": "Entry to delete",
            "start_time": "2024-01-01T09:00:00",
            "end_time": "2024-01-01T11:00:00",
        }
        create_response = await client.post(
            "/api/v1/time-entries/", json=time_entry_data, headers=headers
        )
        created_entry = create_response.json()

        # Удаляем запись
        response = await client.delete(
            f"/api/v1/time-entries/{created_entry['id']}", headers=headers
        )

        assert response.status_code == 200

        # Проверяем, что запись удалена
        get_response = await client.get(
            f"/api/v1/time-entries/{created_entry['id']}", headers=headers
        )
        assert get_response.status_code == 404

    async def test_time_entry_unauthorized_access(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест доступа к временной записи без авторизации"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)
        task = await self.create_test_task(
            client, headers, project["id"], test_task_data
        )

        # Создаем запись
        time_entry_data = {
            "task_id": task["id"],
            "description": "Test entry",
            "start_time": "2024-01-01T09:00:00",
            "end_time": "2024-01-01T11:00:00",
        }
        create_response = await client.post(
            "/api/v1/time-entries/", json=time_entry_data, headers=headers
        )
        created_entry = create_response.json()

        # Пытаемся получить запись без авторизации
        response = await client.get(f"/api/v1/time-entries/{created_entry['id']}")
        assert response.status_code == 401

    async def test_time_entry_validation(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест валидации данных временной записи"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)
        task = await self.create_test_task(
            client, headers, project["id"], test_task_data
        )

        # Пытаемся создать запись с невалидными данными
        invalid_data = {
            "task_id": task["id"],
            "description": "",  # Пустое описание
            "start_time": "invalid-date",  # Невалидная дата
            "end_time": "2024-01-01T11:00:00",
        }
        response = await client.post(
            "/api/v1/time-entries/", json=invalid_data, headers=headers
        )

        # Должна быть ошибка валидации
        assert response.status_code == 422

    async def test_time_entry_negative_duration(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест создания записи с отрицательной длительностью"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)
        task = await self.create_test_task(
            client, headers, project["id"], test_task_data
        )

        # Пытаемся создать запись с end_time раньше start_time
        invalid_data = {
            "task_id": task["id"],
            "description": "Invalid duration",
            "start_time": "2024-01-01T11:00:00",
            "end_time": "2024-01-01T09:00:00",  # Раньше начала
        }
        response = await client.post(
            "/api/v1/time-entries/", json=invalid_data, headers=headers
        )

        # Должна быть ошибка валидации
        assert response.status_code == 400
