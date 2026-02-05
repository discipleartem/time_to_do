"""
Тесты управления задачами
"""

import uuid

from httpx import AsyncClient


class TestTasks:
    """Тесты управления задачами"""

    async def get_auth_headers(self, client: AsyncClient, test_user_data: dict) -> dict:
        """Получение заголовков авторизации"""
        # Используем уникальный email для каждого вызова
        unique_id = str(uuid.uuid4())[:8]
        user_data = test_user_data.copy()
        user_data["email"] = f"tasks_{unique_id}@example.com"
        user_data["username"] = f"tasks_user_{unique_id}"

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

    async def test_create_task(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест создания задачи"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)

        # Добавляем project_id к данным задачи
        task_data = test_task_data.copy()
        task_data["project_id"] = project["id"]

        response = await client.post("/api/v1/tasks/", json=task_data, headers=headers)

        assert response.status_code == 201
        data = response.json()

        assert data["title"] == test_task_data["title"]
        assert data["description"] == test_task_data["description"]
        assert data["status"] == test_task_data["status"]
        assert data["priority"] == test_task_data["priority"]
        assert data["story_point"] == test_task_data["story_point"]
        assert data["estimated_hours"] == test_task_data["estimated_hours"]
        assert data["project_id"] == project["id"]
        assert "id" in data
        assert "created_at" in data

    async def test_get_tasks(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест получения списка задач"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)

        # Создаем несколько задач
        for i in range(3):
            task_data = test_task_data.copy()
            task_data["title"] = f"Task {i}"
            task_data["project_id"] = project["id"]
            await client.post("/api/v1/tasks/", json=task_data, headers=headers)

        # Получаем список задач
        response = await client.get(
            f"/api/v1/tasks/?project_id={project['id']}", headers=headers
        )

        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) == 3

    async def test_get_task_with_filter(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест фильтрации задач по статусу"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)

        # Создаем задачи с разными статусами
        todo_task = test_task_data.copy()
        todo_task["title"] = "TODO Task"
        todo_task["status"] = "todo"
        todo_task["project_id"] = project["id"]
        await client.post("/api/v1/tasks/", json=todo_task, headers=headers)

        done_task = test_task_data.copy()
        done_task["title"] = "Done Task"
        done_task["status"] = "done"
        done_task["project_id"] = project["id"]
        await client.post("/api/v1/tasks/", json=done_task, headers=headers)

        # Фильтруем по статусу
        response = await client.get(
            f"/api/v1/tasks/?project_id={project['id']}&status=todo", headers=headers
        )

        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) == 1
        assert tasks[0]["status"] == "todo"

    async def test_get_task_by_id(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест получения задачи по ID"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)

        # Создаем задачу
        task_data = test_task_data.copy()
        task_data["project_id"] = project["id"]
        create_response = await client.post(
            "/api/v1/tasks/", json=task_data, headers=headers
        )
        created_task = create_response.json()

        # Получаем задачу по ID
        response = await client.get(
            f"/api/v1/tasks/{created_task['id']}", headers=headers
        )

        assert response.status_code == 200
        task = response.json()
        assert task["id"] == created_task["id"]
        assert task["title"] == test_task_data["title"]

    async def test_update_task(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест обновления задачи"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)

        # Создаем задачу
        task_data = test_task_data.copy()
        task_data["project_id"] = project["id"]
        create_response = await client.post(
            "/api/v1/tasks/", json=task_data, headers=headers
        )
        created_task = create_response.json()

        # Обновляем задачу
        update_data = {
            "title": "Updated Task",
            "status": "in_progress",
            "priority": "high",
        }
        response = await client.put(
            f"/api/v1/tasks/{created_task['id']}", json=update_data, headers=headers
        )

        assert response.status_code == 200
        updated_task = response.json()
        assert updated_task["title"] == update_data["title"]
        assert updated_task["status"] == update_data["status"]
        assert updated_task["priority"] == update_data["priority"]

    async def test_delete_task(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест удаления задачи"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)

        # Создаем задачу
        task_data = test_task_data.copy()
        task_data["project_id"] = project["id"]
        create_response = await client.post(
            "/api/v1/tasks/", json=task_data, headers=headers
        )
        created_task = create_response.json()

        # Удаляем задачу
        response = await client.delete(
            f"/api/v1/tasks/{created_task['id']}", headers=headers
        )

        assert response.status_code == 200

        # Проверяем, что задача удалена
        get_response = await client.get(
            f"/api/v1/tasks/{created_task['id']}", headers=headers
        )
        assert get_response.status_code == 404

    async def test_create_task_with_due_date(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест создания задачи с датой выполнения"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)

        # Добавляем due_date
        task_data = test_task_data.copy()
        task_data["project_id"] = project["id"]
        task_data["due_date"] = "2024-12-31"

        response = await client.post("/api/v1/tasks/", json=task_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["due_date"] == "2024-12-31"

    async def test_create_task_with_assignee(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест создания задачи с исполнителем"""
        # Создаем двух пользователей
        headers1 = await self.get_auth_headers(client, test_user_data)

        unique_id = str(uuid.uuid4())[:8]
        user_data2 = test_user_data.copy()
        user_data2["email"] = f"assignee_{unique_id}@example.com"
        user_data2["username"] = f"assignee_user_{unique_id}"

        response2 = await client.post("/api/v1/auth/register", json=user_data2)
        assignee_id = response2.json()["user"]["id"]

        # Создаем проект
        project = await self.create_test_project(client, headers1, test_project_data)

        # Создаем задачу с исполнителем
        task_data = test_task_data.copy()
        task_data["project_id"] = project["id"]
        task_data["assignee_id"] = assignee_id

        response = await client.post("/api/v1/tasks/", json=task_data, headers=headers1)

        assert response.status_code == 201
        data = response.json()
        assert data["assignee_id"] == assignee_id

    async def test_task_unauthorized_access(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест доступа к задаче без авторизации"""
        # Создаем задачу с первым пользователем
        headers1 = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers1, test_project_data)

        task_data = test_task_data.copy()
        task_data["project_id"] = project["id"]
        create_response = await client.post(
            "/api/v1/tasks/", json=task_data, headers=headers1
        )
        created_task = create_response.json()

        # Пытаемся получить задачу без авторизации
        response = await client.get(f"/api/v1/tasks/{created_task['id']}")
        assert response.status_code == 401

    async def test_add_comment_to_task(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест добавления комментария к задаче"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)

        # Создаем задачу
        task_data = test_task_data.copy()
        task_data["project_id"] = project["id"]
        create_response = await client.post(
            "/api/v1/tasks/", json=task_data, headers=headers
        )
        created_task = create_response.json()

        # Добавляем комментарий
        comment_data = {"content": "This is a test comment"}
        response = await client.post(
            f"/api/v1/tasks/{created_task['id']}/comments",
            json=comment_data,
            headers=headers,
        )

        assert response.status_code == 201
        comment = response.json()
        assert comment["content"] == comment_data["content"]
        assert comment["task_id"] == created_task["id"]

    async def test_get_task_comments(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест получения комментариев задачи"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)

        # Создаем задачу
        task_data = test_task_data.copy()
        task_data["project_id"] = project["id"]
        create_response = await client.post(
            "/api/v1/tasks/", json=task_data, headers=headers
        )
        created_task = create_response.json()

        # Добавляем несколько комментариев
        for i in range(3):
            comment_data = {"content": f"Comment {i}"}
            await client.post(
                f"/api/v1/tasks/{created_task['id']}/comments",
                json=comment_data,
                headers=headers,
            )

        # Получаем комментарии
        response = await client.get(
            f"/api/v1/tasks/{created_task['id']}/comments", headers=headers
        )

        assert response.status_code == 200
        comments = response.json()
        assert len(comments) == 3

    async def test_update_comment(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест обновления комментария"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)

        # Создаем задачу
        task_data = test_task_data.copy()
        task_data["project_id"] = project["id"]
        create_response = await client.post(
            "/api/v1/tasks/", json=task_data, headers=headers
        )
        created_task = create_response.json()

        # Добавляем комментарий
        comment_data = {"content": "Original comment"}
        create_comment_response = await client.post(
            f"/api/v1/tasks/{created_task['id']}/comments",
            json=comment_data,
            headers=headers,
        )
        created_comment = create_comment_response.json()

        # Обновляем комментарий
        update_data = {"content": "Updated comment"}
        response = await client.put(
            f"/api/v1/tasks/{created_task['id']}/comments/{created_comment['id']}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == 200
        updated_comment = response.json()
        assert updated_comment["content"] == update_data["content"]

    async def test_delete_comment(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест удаления комментария"""
        headers = await self.get_auth_headers(client, test_user_data)
        project = await self.create_test_project(client, headers, test_project_data)

        # Создаем задачу
        task_data = test_task_data.copy()
        task_data["project_id"] = project["id"]
        create_response = await client.post(
            "/api/v1/tasks/", json=task_data, headers=headers
        )
        created_task = create_response.json()

        # Добавляем комментарий
        comment_data = {"content": "Comment to delete"}
        create_comment_response = await client.post(
            f"/api/v1/tasks/{created_task['id']}/comments",
            json=comment_data,
            headers=headers,
        )
        created_comment = create_comment_response.json()

        # Удаляем комментарий
        response = await client.delete(
            f"/api/v1/tasks/{created_task['id']}/comments/{created_comment['id']}",
            headers=headers,
        )

        assert response.status_code == 200

        # Проверяем, что комментарий удален
        get_response = await client.get(
            f"/api/v1/tasks/{created_task['id']}/comments", headers=headers
        )
        comments = get_response.json()
        assert len(comments) == 0
