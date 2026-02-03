"""
Основной API роутер v1
"""

from fastapi import APIRouter

from app.api.v1 import (
    auth_router,
    github_router,
    projects_router,
    sprints_router,
    tasks_router,
    time_entries_router,
    users_router,
)

api_router = APIRouter()

# Аутентификация
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Аутентификация"],
)

# Пользователи
api_router.include_router(
    users_router,
    prefix="/users",
    tags=["Пользователи"],
)

# Проекты
api_router.include_router(
    projects_router,
    prefix="/projects",
    tags=["Проекты"],
)

# Задачи
api_router.include_router(
    tasks_router,
    prefix="/tasks",
    tags=["Задачи"],
)

# GitHub OAuth
api_router.include_router(
    github_router,
    prefix="/github",
    tags=["GitHub OAuth"],
)

# Time entries
api_router.include_router(
    time_entries_router,
    prefix="/time-entries",
    tags=["Time Tracking"],
)

# Спринты
api_router.include_router(
    sprints_router,
    tags=["SCRUM"],
)
