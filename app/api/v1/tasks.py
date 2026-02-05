"""
API роутеры для управления задачами
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.project import ProjectMember
from app.models.task import Comment, Task
from app.models.user import User
from app.schemas.task import (
    Comment as CommentSchema,
)
from app.schemas.task import (
    CommentCreate,
    TaskCreate,
    TaskUpdate,
)
from app.schemas.task import (
    Task as TaskSchema,
)
from app.websocket.events import EventType
from app.websocket.handlers import handler

router = APIRouter()


@router.get("/", response_model=list[TaskSchema])
async def get_tasks(
    project_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: str = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskSchema]:
    """
    Получение списка задач проекта
    """
    # Проверяем доступ к проекту
    await check_project_access(project_id, current_user, db)

    query = select(Task).where(Task.project_id == uuid.UUID(project_id))

    if status:
        query = query.where(Task.status == status)

    query = query.offset(skip).limit(limit).order_by(Task.order, Task.created_at.desc())

    result = await db.execute(query)
    tasks = result.scalars().all()

    return [TaskSchema.model_validate(task) for task in tasks]


@router.post("/", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TaskSchema:
    """
    Создание новой задачи
    """
    # Проверяем доступ к проекту
    await check_project_access(task_data.project_id, current_user, db)

    # Проверяем права на создание задач
    member = await get_project_member(task_data.project_id, str(current_user.id), db)
    if not member or not member.can_edit_tasks:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для создания задач",
        )

    # Получаем максимальный порядок для статуса
    max_order_result = await db.execute(
        select(Task.order)
        .where(
            Task.project_id == uuid.UUID(str(task_data.project_id)),
            Task.status == task_data.status,
        )
        .order_by(Task.order.desc())
        .limit(1)
    )
    max_order = max_order_result.scalar() or 0

    task = Task(
        title=task_data.title,
        description=task_data.description,
        status=task_data.status,
        priority=task_data.priority,
        story_point=task_data.story_point,
        order=max_order + 1,
        project_id=uuid.UUID(str(task_data.project_id)),
        creator_id=current_user.id,
        assignee_id=(
            uuid.UUID(str(task_data.assignee_id)) if task_data.assignee_id else None
        ),
        parent_task_id=(
            uuid.UUID(str(task_data.parent_task_id))
            if task_data.parent_task_id
            else None
        ),
        due_date=task_data.due_date,
        estimated_hours=task_data.estimated_hours,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Отправляем WebSocket уведомление о создании задачи
    await handler.broadcast_task_event(
        EventType.TASK_CREATED,
        {
            "task_id": task.id,
            "project_id": str(task.project_id),
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "story_point": task.story_point,
            "assignee_id": task.assignee_id,
            "creator_id": task.creator_id,
        },
        current_user.id,
    )

    return TaskSchema.model_validate(task)


@router.get("/{task_id}", response_model=TaskSchema)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TaskSchema:
    """
    Получение информации о задаче
    """
    task = await get_task_with_access_check(task_id, current_user, db)

    return TaskSchema.model_validate(task)


@router.put("/{task_id}", response_model=TaskSchema)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TaskSchema:
    """
    Обновление задачи
    """
    task = await get_task_with_access_check(task_id, current_user, db)

    # Проверяем права на редактирование
    member = await get_project_member(str(task.project_id), str(current_user.id), db)
    if not member or not member.can_edit_tasks:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для редактирования задачи",
        )

    # Обновляем данные
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)

    # Отправляем WebSocket уведомление об обновлении задачи
    await handler.broadcast_task_event(
        EventType.TASK_UPDATED,
        {
            "task_id": task.id,
            "project_id": str(task.project_id),
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "story_point": task.story_point,
            "assignee_id": task.assignee_id,
        },
        current_user.id,
    )

    return TaskSchema.model_validate(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Удаление задачи
    """
    task = await get_task_with_access_check(task_id, current_user, db)

    # Проверяем права на удаление
    member = await get_project_member(str(task.project_id), str(current_user.id), db)
    if not member or not member.can_edit_tasks:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления задачи",
        )

    await db.delete(task)
    await db.commit()

    # Отправляем WebSocket уведомление об удалении задачи
    await handler.broadcast_task_event(
        EventType.TASK_DELETED,
        {
            "task_id": task.id,
            "project_id": str(task.project_id),
            "title": task.title,
            "status": task.status,
        },
        current_user.id,
    )

    return {"message": "Задача успешно удалена"}


@router.get("/{task_id}/comments", response_model=list[CommentSchema])
async def get_task_comments(
    task_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[CommentSchema]:
    """
    Получение комментариев к задаче
    """
    await get_task_with_access_check(task_id, current_user, db)

    result = await db.execute(
        select(Comment)
        .where(Comment.task_id == uuid.UUID(task_id))
        .offset(skip)
        .limit(limit)
        .order_by(Comment.created_at)
    )
    comments = result.scalars().all()

    return [CommentSchema.model_validate(comment) for comment in comments]


@router.post(
    "/{task_id}/comments",
    response_model=CommentSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_task_comment(
    task_id: str,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> CommentSchema:
    """
    Добавление комментария к задаче
    """
    task = await get_task_with_access_check(task_id, current_user, db)

    # Проверяем права на комментирование
    member = await get_project_member(str(task.project_id), str(current_user.id), db)
    if not member or not member.can_view_project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для комментирования",
        )

    comment = Comment(
        content=comment_data.content,
        task_id=uuid.UUID(task_id),
        author_id=current_user.id,
    )

    db.add(comment)
    await db.commit()
    await db.refresh(comment, ["author"])

    # Отправляем WebSocket уведомление о добавлении комментария
    await handler.broadcast_comment_event(
        EventType.COMMENT_ADDED,
        {
            "comment_id": comment.id,
            "task_id": comment.task_id,
            "project_id": str(task.project_id),
            "content": comment.content,
            "author_id": comment.author_id,
        },
        current_user.id,
    )

    # Убедимся, что comment имеет все необходимые поля
    return CommentSchema.model_validate(comment)


@router.put("/{task_id}/comments/{comment_id}", response_model=CommentSchema)
async def update_task_comment(
    task_id: str,
    comment_id: str,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> CommentSchema:
    """
    Обновление комментария
    """
    await get_task_with_access_check(task_id, current_user, db)

    # Конвертируем UUID строки в UUID объекты
    from uuid import UUID

    comment_uuid = UUID(comment_id) if isinstance(comment_id, str) else comment_id
    task_uuid = UUID(task_id) if isinstance(task_id, str) else task_id

    result = await db.execute(
        select(Comment).where(
            Comment.id == comment_uuid,
            Comment.task_id == task_uuid,
        )
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Комментарий не найден",
        )

    # Только автор может редактировать комментарий
    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только автор может редактировать комментарий",
        )

    comment.content = comment_data.content  # type: ignore[assignment] # SQLAlchemy Text field limitation
    comment.is_edited = True  # type: ignore[assignment] # SQLAlchemy Boolean field limitation

    await db.commit()
    await db.refresh(comment)

    return CommentSchema.model_validate(comment)


@router.delete("/{task_id}/comments/{comment_id}")
async def delete_task_comment(
    task_id: str,
    comment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Удаление комментария
    """
    task = await get_task_with_access_check(task_id, current_user, db)

    result = await db.execute(
        select(Comment).where(
            Comment.id == uuid.UUID(comment_id),
            Comment.task_id == uuid.UUID(task_id),
        )
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Комментарий не найден",
        )

    # Автор или участник проекта с правами управления может удалить
    can_delete = comment.author_id == current_user.id or await is_project_manager(
        str(task.project_id), str(current_user.id), db
    )

    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления комментария",
        )

    await db.delete(comment)
    await db.commit()

    return {"message": "Комментарий успешно удален"}


# Вспомогательные функции
async def check_project_access(
    project_id: str,
    user: User,
    db: AsyncSession,
) -> bool:
    """Проверка доступа к проекту"""
    # Конвертируем project_id в UUID
    from uuid import UUID

    project_uuid = UUID(project_id) if isinstance(project_id, str) else project_id

    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_uuid,
            ProjectMember.user_id == user.id,
            ProjectMember.is_active,
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ к проекту запрещен",
        )

    return True


async def get_project_member(
    project_id: str,
    user_id: str,
    db: AsyncSession,
) -> ProjectMember | None:
    """Получение участника проекта"""
    # Конвертируем в UUID если необходимо
    from uuid import UUID

    project_uuid = UUID(project_id) if isinstance(project_id, str) else project_id
    user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_uuid,
            ProjectMember.user_id == user_uuid,
            ProjectMember.is_active,
        )
    )
    return result.scalar_one_or_none()


async def get_task_with_access_check(
    task_id: str,
    user: User,
    db: AsyncSession,
) -> Task:
    """Получение задачи с проверкой доступа"""
    # Конвертируем task_id в UUID
    from uuid import UUID

    task_uuid = UUID(task_id) if isinstance(task_id, str) else task_id

    result = await db.execute(select(Task).where(Task.id == task_uuid))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена",
        )

    await check_project_access(str(task.project_id), user, db)

    return task


async def is_project_manager(
    project_id: str,
    user_id: str,
    db: AsyncSession,
) -> bool:
    """Проверка, является ли пользователь менеджером проекта"""
    member = await get_project_member(project_id, user_id, db)
    return bool(member and member.can_manage_project)
