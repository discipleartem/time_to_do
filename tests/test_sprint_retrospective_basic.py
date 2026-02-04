"""
Базовые тесты для функционала ретроспективы спринтов
"""

import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_retrospective_page_loads(client: AsyncClient) -> None:
    """Тест что страница ретроспективы загружается"""
    # Тестируем загрузку страницы с тестовым ID
    response = await client.get("/sprints/test-id/retrospective?sprint_id=test-id")

    # Страница должна загрузиться (даже с несуществующим спринтом)
    assert response.status_code == 200
    assert "Ретроспектива спринта" in response.text


@pytest.mark.asyncio
async def test_sprint_lifecycle_with_retrospective(
    client: AsyncClient, auth_headers: dict[str, str], test_project_with_user
) -> None:
    """Тест полного жизненного цикла спринта с ретроспективой"""
    # 1. Создаем спринт
    sprint_data = {
        "name": "Full Lifecycle Sprint",
        "description": "Testing complete sprint lifecycle",
        "goal": "Test retrospective functionality",
        "project_id": str(test_project_with_user.id),
    }

    response = await client.post(
        "/api/v1/sprints/", json=sprint_data, headers=auth_headers
    )
    assert response.status_code == 201
    sprint = response.json()
    assert sprint["status"] == "planning"

    # 2. Запускаем спринт
    start_response = await client.post(
        f"/api/v1/sprints/{sprint['id']}/start",
        json={
            "start_date": "2026-01-01",
            "end_date": "2026-01-14",
            "capacity_hours": 80,
            "velocity_points": 20,
        },
        headers=auth_headers,
    )
    assert start_response.status_code == 200
    started_sprint = start_response.json()
    assert started_sprint["status"] == "active"

    # 3. Завершаем спринт с ретроспективой
    retrospective_data = {
        "went_well": ["Good teamwork", "On time delivery"],
        "improve": ["Better planning", "More testing"],
        "ideas": ["Daily standups", "Code reviews"],
        "actions": ["Setup planning meetings", "Add more tests"],
        "general_notes": "Successful sprint with room for improvement",
    }

    complete_response = await client.post(
        f"/api/v1/sprints/{sprint['id']}/complete",
        json={
            "completed_points": 18,
            "retrospective_notes": json.dumps(retrospective_data),
        },
        headers=auth_headers,
    )
    assert complete_response.status_code == 200
    completed_sprint = complete_response.json()
    assert completed_sprint["status"] == "completed"

    # 4. Проверяем страницу ретроспективы
    page_response = await client.get(
        f"/sprints/{sprint['id']}/retrospective?sprint_id={sprint['id']}"
    )
    assert page_response.status_code == 200
    assert "Ретроспектива спринта" in page_response.text


@pytest.mark.asyncio
async def test_empty_retrospective_data(
    client: AsyncClient, auth_headers: dict[str, str], test_project_with_user
) -> None:
    """Тест пустой ретроспективы"""
    # Создаем и запускаем спринт
    sprint_data = {
        "name": "Empty Retro Sprint",
        "description": "Testing empty retrospective",
        "goal": "Minimal retrospective test",
        "project_id": str(test_project_with_user.id),
    }

    response = await client.post(
        "/api/v1/sprints/", json=sprint_data, headers=auth_headers
    )
    assert response.status_code == 201
    sprint = response.json()

    # Запускаем спринт
    start_response = await client.post(
        f"/api/v1/sprints/{sprint['id']}/start",
        json={
            "start_date": "2026-01-01",
            "end_date": "2026-01-07",
            "capacity_hours": 40,
            "velocity_points": 10,
        },
        headers=auth_headers,
    )
    assert start_response.status_code == 200

    # Завершаем с пустой ретроспективой
    empty_retrospective = {
        "went_well": [],
        "improve": [],
        "ideas": [],
        "actions": [],
        "general_notes": "",
    }

    complete_response = await client.post(
        f"/api/v1/sprints/{sprint['id']}/complete",
        json={
            "completed_points": 5,
            "retrospective_notes": json.dumps(empty_retrospective),
        },
        headers=auth_headers,
    )
    assert complete_response.status_code == 200

    # Проверяем страницу
    page_response = await client.get(
        f"/sprints/{sprint['id']}/retrospective?sprint_id={sprint['id']}"
    )
    assert page_response.status_code == 200


@pytest.mark.asyncio
async def test_retrospective_with_unicode_content(
    client: AsyncClient, auth_headers: dict[str, str], test_project_with_user
) -> None:
    """Тест ретроспективы с Unicode контентом"""
    # Создаем и запускаем спринт
    sprint_data = {
        "name": "Unicode Sprint",
        "description": "Тестирование Unicode",
        "goal": "Проверка кодировки",
        "project_id": str(test_project_with_user.id),
    }

    response = await client.post(
        "/api/v1/sprints/", json=sprint_data, headers=auth_headers
    )
    assert response.status_code == 201
    sprint = response.json()

    # Запускаем спринт
    start_response = await client.post(
        f"/api/v1/sprints/{sprint['id']}/start",
        json={
            "start_date": "2026-01-01",
            "end_date": "2026-01-07",
            "capacity_hours": 40,
            "velocity_points": 15,
        },
        headers=auth_headers,
    )
    assert start_response.status_code == 200

    # Завершаем с Unicode контентом
    unicode_retrospective = {
        "went_well": ["Отличная работа команды", "Соблюдение сроков"],
        "improve": ["Улучшить планирование", "Больше автоматизации"],
        "ideas": ["Ежедневные встречи", "Парное программирование"],
        "actions": ["Внедрить agile практики", "Настроить CI/CD"],
        "general_notes": "Спринт прошел успешно! Отличная работа всей команды. 🎉",
    }

    complete_response = await client.post(
        f"/api/v1/sprints/{sprint['id']}/complete",
        json={
            "completed_points": 12,
            "retrospective_notes": json.dumps(
                unicode_retrospective, ensure_ascii=False
            ),
        },
        headers=auth_headers,
    )
    assert complete_response.status_code == 200

    # Проверяем страницу
    page_response = await client.get(
        f"/sprints/{sprint['id']}/retrospective?sprint_id={sprint['id']}"
    )
    assert page_response.status_code == 200
