"""
Интеграционные тесты для Time to DO
"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestProjectWorkflow:
    """Интеграционные тесты полного рабочего процесса с проектами"""

    async def test_complete_project_workflow(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест полного рабочего процесса: проект → задачи → комментарии"""
        # 1. Регистрация пользователя
        unique_id = str(uuid.uuid4())[:8]
        user_data = test_user_data.copy()
        user_data["email"] = f"workflow_{unique_id}@example.com"
        user_data["username"] = f"workflow_user_{unique_id}"

        register_response = await client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Создание проекта
        project_response = await client.post(
            "/api/v1/projects/", json=test_project_data, headers=headers
        )
        assert project_response.status_code == 201
        project = project_response.json()

        # 3. Создание нескольких задач
        tasks = []
        for i in range(3):
            task_data = test_task_data.copy()
            task_data["title"] = f"Task {i+1}"
            task_data["project_id"] = project["id"]
            task_data["status"] = (
                "todo" if i == 0 else "in_progress" if i == 1 else "done"
            )

            task_response = await client.post(
                "/api/v1/tasks/", json=task_data, headers=headers
            )
            assert task_response.status_code == 201
            tasks.append(task_response.json())

        # 4. Добавление комментариев к задачам
        for i, task in enumerate(tasks):
            comment_data = {"content": f"Comment for task {i+1}"}
            comment_response = await client.post(
                f"/api/v1/tasks/{task['id']}/comments",
                json=comment_data,
                headers=headers,
            )
            assert comment_response.status_code == 201

        # 5. Проверка получения всех задач проекта
        tasks_response = await client.get(
            f"/api/v1/tasks/?project_id={project['id']}", headers=headers
        )
        assert tasks_response.status_code == 200
        project_tasks = tasks_response.json()
        assert len(project_tasks) == 3

        # 6. Проверка фильтрации задач по статусу
        todo_response = await client.get(
            f"/api/v1/tasks/?project_id={project['id']}&status=todo", headers=headers
        )
        assert todo_response.status_code == 200
        todo_tasks = todo_response.json()
        assert len(todo_tasks) == 1
        assert todo_tasks[0]["status"] == "todo"

        # 7. Проверка получения комментариев задачи
        comments_response = await client.get(
            f"/api/v1/tasks/{tasks[0]['id']}/comments", headers=headers
        )
        assert comments_response.status_code == 200
        comments = comments_response.json()
        assert len(comments) == 1

    async def test_multi_user_project_collaboration(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест совместной работы нескольких пользователей над проектом"""
        # 1. Создание владельца проекта
        unique_id = str(uuid.uuid4())[:8]
        owner_data = test_user_data.copy()
        owner_data["email"] = f"owner_{unique_id}@example.com"
        owner_data["username"] = f"owner_{unique_id}"

        owner_response = await client.post("/api/v1/auth/register", json=owner_data)
        owner_token = owner_response.json()["access_token"]
        owner_headers = {"Authorization": f"Bearer {owner_token}"}

        # 2. Создание проекта
        project_response = await client.post(
            "/api/v1/projects/", json=test_project_data, headers=owner_headers
        )
        project = project_response.json()

        # 3. Создание участника проекта
        member_unique_id = str(uuid.uuid4())[:8]
        member_data = test_user_data.copy()
        member_data["email"] = f"member_{member_unique_id}@example.com"
        member_data["username"] = f"member_{member_unique_id}"

        member_response = await client.post("/api/v1/auth/register", json=member_data)
        member_token = member_response.json()["access_token"]
        member_headers = {"Authorization": f"Bearer {member_token}"}
        member_user = member_response.json()["user"]

        # 4. Добавление участника в проект
        add_member_response = await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": member_user["id"], "role": "MEMBER"},
            headers=owner_headers,
        )
        assert add_member_response.status_code == 200

        # 5. Владелец создает задачу
        task_data = test_task_data.copy()
        task_data["project_id"] = project["id"]
        task_data["assignee_id"] = member_user["id"]

        task_response = await client.post(
            "/api/v1/tasks/", json=task_data, headers=owner_headers
        )
        task = task_response.json()

        # 6. Участник обновляет статус задачи
        update_response = await client.put(
            f"/api/v1/tasks/{task['id']}",
            json={"status": "in_progress"},
            headers=member_headers,
        )
        assert update_response.status_code == 200

        # 7. Участник добавляет комментарий
        comment_response = await client.post(
            f"/api/v1/tasks/{task['id']}/comments",
            json={"content": "Started working on this task"},
            headers=member_headers,
        )
        assert comment_response.status_code == 201

        # 8. Владелец видит обновления
        updated_task_response = await client.get(
            f"/api/v1/tasks/{task['id']}", headers=owner_headers
        )
        updated_task = updated_task_response.json()
        assert updated_task["status"] == "in_progress"

        comments_response = await client.get(
            f"/api/v1/tasks/{task['id']}/comments", headers=owner_headers
        )
        comments = comments_response.json()
        assert len(comments) == 1
        assert "Started working" in comments[0]["content"]


@pytest.mark.integration
class TestTimeTrackingWorkflow:
    """Интеграционные тесты отслеживания времени"""

    async def test_complete_time_tracking_workflow(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест полного рабочего процесса отслеживания времени"""
        # 1. Настройка пользователя, проекта и задачи
        unique_id = str(uuid.uuid4())[:8]
        user_data = test_user_data.copy()
        user_data["email"] = f"time_{unique_id}@example.com"
        user_data["username"] = f"time_user_{unique_id}"

        register_response = await client.post("/api/v1/auth/register", json=user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        project_response = await client.post(
            "/api/v1/projects/", json=test_project_data, headers=headers
        )
        project = project_response.json()

        task_data = test_task_data.copy()
        task_data["project_id"] = project["id"]
        task_response = await client.post(
            "/api/v1/tasks/", json=task_data, headers=headers
        )
        task = task_response.json()

        # 2. Создание нескольких временных записей
        time_entries = []
        for i in range(3):
            entry_data = {
                "task_id": task["id"],
                "description": f"Work session {i+1}",
                "start_time": f"2024-01-0{i+1}T09:00:00",
                "end_time": f"2024-01-0{i+1}T11:30:00",
            }

            entry_response = await client.post(
                "/api/v1/time-entries/", json=entry_data, headers=headers
            )
            assert entry_response.status_code == 201
            time_entries.append(entry_response.json())

        # 3. Проверка получения всех записей
        entries_response = await client.get("/api/v1/time-entries/", headers=headers)
        assert entries_response.status_code == 200
        all_entries = entries_response.json()
        assert len(all_entries) == 3

        # 4. Проверка фильтрации по задаче
        task_entries_response = await client.get(
            f"/api/v1/time-entries/?task_id={task['id']}", headers=headers
        )
        assert task_entries_response.status_code == 200
        task_entries = task_entries_response.json()
        assert len(task_entries) == 3

        # 5. Проверка фильтрации по диапазону дат
        date_range_response = await client.get(
            "/api/v1/time-entries/?date_from=2024-01-01&date_to=2024-01-02",
            headers=headers,
        )
        assert date_range_response.status_code == 200
        range_entries = date_range_response.json()
        assert len(range_entries) == 2

        # 6. Обновление записи
        update_data = {"description": "Updated work session"}
        update_response = await client.put(
            f"/api/v1/time-entries/{time_entries[0]['id']}",
            json=update_data,
            headers=headers,
        )
        assert update_response.status_code == 200
        updated_entry = update_response.json()
        assert updated_entry["description"] == update_data["description"]

    async def test_timer_workflow(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест работы с таймером"""
        # 1. Настройка
        unique_id = str(uuid.uuid4())[:8]
        user_data = test_user_data.copy()
        user_data["email"] = f"timer_{unique_id}@example.com"
        user_data["username"] = f"timer_user_{unique_id}"

        register_response = await client.post("/api/v1/auth/register", json=user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        project_response = await client.post(
            "/api/v1/projects/", json=test_project_data, headers=headers
        )
        project = project_response.json()

        task_data = test_task_data.copy()
        task_data["project_id"] = project["id"]
        task_response = await client.post(
            "/api/v1/tasks/", json=task_data, headers=headers
        )
        task = task_response.json()

        # 2. Создание записи с таймером
        timer_data = {
            "task_id": task["id"],
            "description": "Timer session",
            "start_time": datetime.now(UTC).isoformat(),
        }

        timer_response = await client.post(
            "/api/v1/time-entries/", json=timer_data, headers=headers
        )
        timer_entry = timer_response.json()

        # 3. Запуск таймера
        start_response = await client.put(
            f"/api/v1/time-entries/{timer_entry['id']}/start", headers=headers
        )
        assert start_response.status_code == 200
        started_entry = start_response.json()
        assert started_entry["is_active"] is True

        # 4. Остановка таймера
        stop_response = await client.put(
            f"/api/v1/time-entries/{timer_entry['id']}/stop", headers=headers
        )
        assert stop_response.status_code == 200
        stopped_entry = stop_response.json()
        assert stopped_entry["is_active"] is False
        assert stopped_entry["end_time"] is not None
        assert stopped_entry["duration_minutes"] is not None


@pytest.mark.integration
class TestUserManagementWorkflow:
    """Интеграционные тесты управления пользователями"""

    async def test_user_profile_and_projects_workflow(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест рабочего процесса пользователя: профиль → проекты → статистика"""
        # 1. Регистрация пользователя
        unique_id = str(uuid.uuid4())[:8]
        user_data = test_user_data.copy()
        user_data["email"] = f"profile_{unique_id}@example.com"
        user_data["username"] = f"profile_user_{unique_id}"

        register_response = await client.post("/api/v1/auth/register", json=user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Получение профиля
        profile_response = await client.get("/api/v1/users/me", headers=headers)
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["email"] == user_data["email"]

        # 3. Обновление профиля
        update_data = {
            "full_name": "Updated Full Name",
            "avatar_url": "https://example.com/avatar.png",
        }
        update_response = await client.put(
            "/api/v1/users/me", json=update_data, headers=headers
        )
        assert update_response.status_code == 200

        # 4. Создание нескольких проектов
        projects = []
        for i in range(3):
            project_data = test_project_data.copy()
            project_data["name"] = f"Project {i+1}"

            project_response = await client.post(
                "/api/v1/projects/", json=project_data, headers=headers
            )
            assert project_response.status_code == 201
            projects.append(project_response.json())

        # 5. Создание задач в проектах
        total_tasks = 0
        for project in projects:
            for i in range(2):
                task_data = test_task_data.copy()
                task_data["title"] = f"Task {project['name']}-{i+1}"
                task_data["project_id"] = project["id"]

                task_response = await client.post(
                    "/api/v1/tasks/", json=task_data, headers=headers
                )
                assert task_response.status_code == 201
                total_tasks += 1

        # 6. Проверка получения всех проектов
        projects_response = await client.get("/api/v1/projects/", headers=headers)
        assert projects_response.status_code == 200
        user_projects = projects_response.json()
        assert len(user_projects) == 3

        # 7. Проверка обновленного профиля
        updated_profile_response = await client.get("/api/v1/users/me", headers=headers)
        updated_profile = updated_profile_response.json()
        assert updated_profile["full_name"] == update_data["full_name"]
        assert updated_profile["avatar_url"] == update_data["avatar_url"]


@pytest.mark.integration
class TestErrorHandlingWorkflow:
    """Интеграционные тесты обработки ошибок"""

    async def test_unauthorized_access_workflow(
        self,
        client: AsyncClient,
        test_user_data: dict,
        test_project_data: dict,
        test_task_data: dict,
    ):
        """Тест доступа без авторизации"""
        # 1. Попытка доступа к защищенным эндпоинтам без токена
        protected_endpoints = [
            "/api/v1/users/me",
            "/api/v1/projects/",
            "/api/v1/tasks/",
            "/api/v1/time-entries/",
        ]

        for endpoint in protected_endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 401

        # 2. Попытка создания ресурсов без авторизации
        create_endpoints = [
            ("/api/v1/projects/", test_project_data),
            ("/api/v1/tasks/", test_task_data),
        ]

        for endpoint, data in create_endpoints:
            response = await client.post(endpoint, json=data)
            assert response.status_code == 401

    async def test_invalid_data_workflow(
        self,
        client: AsyncClient,
        test_user_data: dict,
    ):
        """Тест обработки невалидных данных"""
        # 1. Регистрация с невалидными данными
        invalid_user_data = [
            {},  # Пустые данные
            {"email": "invalid-email"},  # Невалидный email
            {"email": "test@example.com", "password": "123"},  # Слишком короткий пароль
        ]

        for data in invalid_user_data:
            response = await client.post("/api/v1/auth/register", json=data)
            assert response.status_code in [400, 422]

        # 2. Регистрация пользователя
        unique_id = str(uuid.uuid4())[:8]
        user_data = test_user_data.copy()
        user_data["email"] = f"invalid_{unique_id}@example.com"
        user_data["username"] = f"invalid_user_{unique_id}"

        register_response = await client.post("/api/v1/auth/register", json=user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Создание проекта с невалидными данными
        invalid_project_data = [
            {},  # Пустые данные
            {"name": ""},  # Пустое название
            {"name": "a" * 300},  # Слишком длинное название
        ]

        for data in invalid_project_data:
            response = await client.post(
                "/api/v1/projects/", json=data, headers=headers
            )
            assert response.status_code in [400, 422]

    async def test_resource_not_found_workflow(
        self,
        client: AsyncClient,
        test_user_data: dict,
    ):
        """Тест доступа к несуществующим ресурсам"""
        # 1. Регистрация пользователя
        unique_id = str(uuid.uuid4())[:8]
        user_data = test_user_data.copy()
        user_data["email"] = f"notfound_{unique_id}@example.com"
        user_data["username"] = f"notfound_user_{unique_id}"

        register_response = await client.post("/api/v1/auth/register", json=user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Попытка доступа к несуществующим ресурсам
        fake_id = str(uuid.uuid4())
        not_found_endpoints = [
            f"/api/v1/projects/{fake_id}",
            f"/api/v1/tasks/{fake_id}",
            f"/api/v1/time-entries/{fake_id}",
            f"/api/v1/users/{fake_id}",
        ]

        for endpoint in not_found_endpoints:
            response = await client.get(endpoint, headers=headers)
            assert response.status_code == 404
