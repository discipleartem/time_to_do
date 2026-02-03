"""
API эндпоинты для управления SCRUM спринтами
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.sprint import (
    Sprint,
    SprintBulkTaskAdd,
    SprintBurndown,
    SprintCreate,
    SprintStart,
    SprintStats,
    SprintTask,
    SprintTaskCreate,
    SprintTaskWithDetails,
    SprintUpdate,
    SprintWithDetails,
    TeamVelocity,
)
from app.services.sprint_service import SprintService

router = APIRouter(prefix="/sprints", tags=["sprints"])


def get_sprint_service(db: AsyncSession = Depends(get_db)) -> SprintService:
    """Получение экземпляра сервиса спринтов"""
    return SprintService(db)


@router.post("/", response_model=Sprint, status_code=201)
async def create_sprint(
    sprint_data: SprintCreate,
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> Sprint:
    """Создание нового спринта"""
    try:
        sprint = await sprint_service.create_sprint(sprint_data)
        return Sprint.model_validate(sprint)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{sprint_id}", response_model=SprintWithDetails)
async def get_sprint(
    sprint_id: str,
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> SprintWithDetails:
    """Получение спринта по ID"""
    sprint = await sprint_service.get_sprint_by_id(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Спринт не найден")

    return SprintWithDetails(
        id=str(sprint.id),
        name=sprint.name,
        description=sprint.description,
        goal=sprint.goal,
        status=sprint.status if isinstance(sprint.status, str) else sprint.status.value,
        start_date=sprint.start_date,
        end_date=sprint.end_date,
        capacity_hours=sprint.capacity_hours,
        velocity_points=sprint.velocity_points,
        completed_points=sprint.completed_points,
        project_id=str(sprint.project_id),
        created_at=sprint.created_at,
        updated_at=sprint.updated_at,
        duration_days=sprint.duration_days,
        is_active=sprint.is_active,
        completion_percentage=sprint.completion_percentage,
        task_count=sprint.task_count,
        completed_task_count=sprint.completed_task_count,
    )


@router.put("/{sprint_id}", response_model=Sprint)
async def update_sprint(
    sprint_id: str,
    sprint_data: SprintUpdate,
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> Sprint:
    """Обновление спринта"""
    sprint = await sprint_service.update_sprint(sprint_id, sprint_data)
    if not sprint:
        raise HTTPException(status_code=404, detail="Спринт не найден")

    return Sprint.model_validate(sprint)


@router.post("/{sprint_id}/start", response_model=Sprint)
async def start_sprint(
    sprint_id: str,
    start_data: SprintStart,
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> Sprint:
    """Запуск спринта"""
    try:
        sprint = await sprint_service.start_sprint(
            sprint_id=sprint_id,
            start_date=start_data.start_date,
            end_date=start_data.end_date,
            capacity_hours=start_data.capacity_hours,
            velocity_points=start_data.velocity_points,
        )
        if not sprint:
            raise HTTPException(status_code=404, detail="Спринт не найден")

        return Sprint.model_validate(sprint)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{sprint_id}/complete", response_model=Sprint)
async def complete_sprint(
    sprint_id: str,
    completed_data: dict[str, Any],
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> Sprint:
    """Завершение спринта"""
    try:
        completed_points = completed_data.get("completed_points")
        retrospective_notes = completed_data.get("retrospective_notes")

        sprint = await sprint_service.complete_sprint(
            sprint_id=sprint_id,
            completed_points=completed_points,
            retrospective_notes=retrospective_notes,
        )
        if not sprint:
            raise HTTPException(status_code=404, detail="Спринт не найден")

        return Sprint.model_validate(sprint)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{sprint_id}/cancel", response_model=Sprint)
async def cancel_sprint(
    sprint_id: str,
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> Sprint:
    """Отмена спринта"""
    try:
        sprint = await sprint_service.cancel_sprint(sprint_id)
        if not sprint:
            raise HTTPException(status_code=404, detail="Спринт не найден")

        return Sprint.model_validate(sprint)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/project/{project_id}", response_model=list[Sprint])
async def get_project_sprints(
    project_id: str,
    include_completed: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> list[Sprint]:
    """Получение спринтов проекта"""
    sprints = await sprint_service.get_project_sprints(
        project_id=project_id, include_completed=include_completed
    )
    return [Sprint.model_validate(sprint) for sprint in sprints]


@router.get("/project/{project_id}/active", response_model=SprintWithDetails | dict)
async def get_active_sprint(
    project_id: str,
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> SprintWithDetails | dict:
    """Получение активного спринта проекта"""
    sprint = await sprint_service.get_active_sprint(project_id)
    if not sprint:
        return {"message": "Активный спринт не найден"}

    return SprintWithDetails(
        id=str(sprint.id),
        name=sprint.name,
        description=sprint.description,
        goal=sprint.goal,
        status=sprint.status if isinstance(sprint.status, str) else sprint.status.value,
        start_date=sprint.start_date,
        end_date=sprint.end_date,
        capacity_hours=sprint.capacity_hours,
        velocity_points=sprint.velocity_points,
        completed_points=sprint.completed_points,
        project_id=str(sprint.project_id),
        created_at=sprint.created_at,
        updated_at=sprint.updated_at,
        duration_days=sprint.duration_days,
        is_active=sprint.is_active,
        completion_percentage=sprint.completion_percentage,
        task_count=sprint.task_count,
        completed_task_count=sprint.completed_task_count,
    )


@router.get("/{sprint_id}/stats", response_model=SprintStats)
async def get_sprint_stats(
    sprint_id: str,
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> SprintStats:
    """Получение статистики спринта"""
    stats = await sprint_service.get_sprint_stats(sprint_id)
    return stats


@router.get("/{sprint_id}/burndown", response_model=SprintBurndown)
async def get_burndown_data(
    sprint_id: str,
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> SprintBurndown:
    """Получение данных для burndown chart"""
    try:
        burndown = await sprint_service.get_burndown_data(sprint_id)
        return burndown
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{sprint_id}/tasks", response_model=list[SprintTaskWithDetails])
async def get_sprint_tasks(
    sprint_id: str,
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> list[SprintTaskWithDetails]:
    """Получение задач спринта"""
    sprint_tasks = await sprint_service.get_sprint_tasks(sprint_id)

    result = []
    for sprint_task in sprint_tasks:
        task_data = None
        if sprint_task.task:
            task_data = {
                "id": str(sprint_task.task.id),
                "title": sprint_task.task.title,
                "description": sprint_task.task.description,
                "status": sprint_task.task.status.value,
                "priority": sprint_task.task.priority.value,
                "story_points": getattr(sprint_task.task, "story_points", None),
                "assignee_id": (
                    str(sprint_task.task.assignee_id)
                    if sprint_task.task.assignee_id
                    else None
                ),
                "created_at": sprint_task.task.created_at,
                "updated_at": sprint_task.task.updated_at,
            }

        result.append(
            SprintTaskWithDetails(
                id=str(sprint_task.id),
                sprint_id=str(sprint_task.sprint_id),
                task_id=str(sprint_task.task_id),
                order=sprint_task.order,
                is_added_mid_sprint=sprint_task.is_added_mid_sprint,
                created_at=sprint_task.created_at,
                updated_at=sprint_task.updated_at,
                task=task_data,
            )
        )

    return result


@router.post("/{sprint_id}/tasks", response_model=SprintTask, status_code=201)
async def add_task_to_sprint(
    sprint_id: str,
    task_data: SprintTaskCreate,
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> SprintTask:
    """Добавление задачи в спринт"""
    try:
        sprint_task = await sprint_service.add_task_to_sprint(
            sprint_id=sprint_id,
            task_id=task_data.task_id,
            order=task_data.order,
            is_added_mid_sprint=task_data.is_added_mid_sprint,
        )
        return SprintTask.model_validate(sprint_task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{sprint_id}/tasks/{task_id}")
async def remove_task_from_sprint(
    sprint_id: str,
    task_id: str,
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> dict[str, str]:
    """Удаление задачи из спринта"""
    success = await sprint_service.remove_task_from_sprint(sprint_id, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Задача в спринте не найдена")

    return {"message": "Задача удалена из спринта"}


@router.post("/{sprint_id}/tasks/bulk", response_model=list[SprintTask])
async def bulk_add_tasks_to_sprint(
    sprint_id: str,
    bulk_data: SprintBulkTaskAdd,
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> list[SprintTask]:
    """Массовое добавление задач в спринт"""
    try:
        sprint_tasks = await sprint_service.bulk_add_tasks_to_sprint(
            sprint_id=sprint_id,
            task_ids=bulk_data.task_ids,
            is_added_mid_sprint=True,  # При массовом добавлении считаем, что в середине спринта
        )
        return [SprintTask.model_validate(st) for st in sprint_tasks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/project/{project_id}/velocity", response_model=TeamVelocity)
async def get_team_velocity(
    project_id: str,
    limit: int = Query(default=10, le=20),
    current_user: User = Depends(get_current_user),
    sprint_service: SprintService = Depends(get_sprint_service),
) -> TeamVelocity:
    """Получение velocity команды"""
    velocity = await sprint_service.get_team_velocity(project_id, limit)
    return velocity
