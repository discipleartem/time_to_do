"""
Базовые тесты для SCRUM спринтов
"""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_sprint_basic(
    client: AsyncClient, auth_headers: dict[str, str], test_project_with_user
) -> None:
    """Базовый тест создания спринта"""
    sprint_data = {
        "name": "Test Sprint",
        "description": "Test sprint description",
        "goal": "Complete user authentication",
        "project_id": str(test_project_with_user.id),
        "capacity_hours": 80,
        "velocity_points": 20,
    }

    response = await client.post(
        "/api/v1/sprints/", json=sprint_data, headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Sprint"
    assert data["description"] == "Test sprint description"
    assert data["goal"] == "Complete user authentication"
    assert data["project_id"] == str(test_project_with_user.id)
    assert data["capacity_hours"] == 80
    assert data["velocity_points"] == 20
    assert data["status"] == "planning"


@pytest.mark.asyncio
async def test_get_sprint_basic(
    client: AsyncClient, auth_headers: dict[str, str], test_project_with_user
) -> None:
    """Базовый тест получения спринта"""
    # Создаем спринт
    sprint_data = {
        "name": "Test Sprint",
        "project_id": str(test_project_with_user.id),
    }
    create_response = await client.post(
        "/api/v1/sprints/", json=sprint_data, headers=auth_headers
    )
    sprint_id = create_response.json()["id"]

    # Получаем спринт
    response = await client.get(f"/api/v1/sprints/{sprint_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sprint_id
    assert data["name"] == "Test Sprint"


@pytest.mark.asyncio
async def test_start_sprint_basic(
    client: AsyncClient, auth_headers: dict[str, str], test_project_with_user
) -> None:
    """Базовый тест запуска спринта"""
    # Создаем спринт
    sprint_data = {
        "name": "Test Sprint",
        "project_id": str(test_project_with_user.id),
    }
    create_response = await client.post(
        "/api/v1/sprints/", json=sprint_data, headers=auth_headers
    )
    sprint_id = create_response.json()["id"]

    # Запускаем спринт
    start_data = {
        "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=14)).isoformat(),
        "capacity_hours": 100,
        "velocity_points": 25,
    }
    response = await client.post(
        f"/api/v1/sprints/{sprint_id}/start", json=start_data, headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["capacity_hours"] == 100
    assert data["velocity_points"] == 25


@pytest.mark.asyncio
async def test_complete_sprint_basic(
    client: AsyncClient, auth_headers: dict[str, str], test_project_with_user
) -> None:
    """Базовый тест завершения спринта"""
    # Создаем спринт
    sprint_data = {
        "name": "Test Sprint",
        "project_id": str(test_project_with_user.id),
    }
    create_response = await client.post(
        "/api/v1/sprints/", json=sprint_data, headers=auth_headers
    )
    sprint_id = create_response.json()["id"]

    # Запускаем спринт
    start_data = {
        "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=14)).isoformat(),
    }
    await client.post(
        f"/api/v1/sprints/{sprint_id}/start", json=start_data, headers=auth_headers
    )

    # Завершаем спринт
    response = await client.post(
        f"/api/v1/sprints/{sprint_id}/complete",
        json={"completed_points": 18},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["completed_points"] == 18


@pytest.mark.asyncio
async def test_get_project_sprints_basic(
    client: AsyncClient, auth_headers: dict[str, str], test_project_with_user
) -> None:
    """Базовый тест получения спринтов проекта"""
    # Создаем несколько спринтов
    for i in range(3):
        sprint_data = {
            "name": f"Sprint {i+1}",
            "project_id": str(test_project_with_user.id),
        }
        await client.post("/api/v1/sprints/", json=sprint_data, headers=auth_headers)

    # Получаем спринты проекта
    response = await client.get(
        f"/api/v1/sprints/project/{test_project_with_user.id}", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_get_active_sprint_basic(
    client: AsyncClient, auth_headers: dict[str, str], test_project_with_user
) -> None:
    """Базовый тест получения активного спринта проекта"""
    # Создаем спринт
    sprint_data = {
        "name": "Test Sprint",
        "project_id": str(test_project_with_user.id),
    }
    create_response = await client.post(
        "/api/v1/sprints/", json=sprint_data, headers=auth_headers
    )
    sprint_id = create_response.json()["id"]

    # Запускаем спринт
    start_data = {
        "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=14)).isoformat(),
    }
    await client.post(
        f"/api/v1/sprints/{sprint_id}/start", json=start_data, headers=auth_headers
    )

    # Получаем активный спринт
    response = await client.get(
        f"/api/v1/sprints/project/{test_project_with_user.id}/active",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["id"] == sprint_id


@pytest.mark.asyncio
async def test_get_sprint_stats_basic(
    client: AsyncClient, auth_headers: dict[str, str], test_project_with_user
) -> None:
    """Базовый тест получения статистики спринта"""
    # Создаем спринт
    sprint_data = {
        "name": "Test Sprint",
        "project_id": str(test_project_with_user.id),
    }
    create_response = await client.post(
        "/api/v1/sprints/", json=sprint_data, headers=auth_headers
    )
    sprint_id = create_response.json()["id"]

    # Получаем статистику
    response = await client.get(
        f"/api/v1/sprints/{sprint_id}/stats", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "total_tasks" in data
    assert "completed_tasks" in data
    assert "completion_percentage" in data
    assert data["total_tasks"] == 0  # Нет задач в спринte


@pytest.mark.asyncio
async def test_unauthorized_sprint_access(client: AsyncClient) -> None:
    """Тест неавторизованного доступа к спринтам"""
    sprint_data = {
        "name": "Test Sprint",
        "project_id": str(uuid.uuid4()),
    }

    response = await client.post("/api/v1/sprints/", json=sprint_data)

    assert response.status_code == 401
