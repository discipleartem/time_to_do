"""
API роутеры для управления временными записями (time tracking)
"""

import uuid
from datetime import UTC, date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.time_entry import TimeEntry
from app.models.user import User
from app.schemas.time_entry import (
    TimeEntry as TimeEntrySchema,
)
from app.schemas.time_entry import (
    TimeEntryCreate,
    TimeEntryUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[TimeEntrySchema])
async def get_time_entries(
    task_id: str | None = Query(None, description="Фильтр по ID задачи"),
    project_id: str | None = Query(None, description="Фильтр по ID проекта"),
    date_from: date | None = Query(None, description="Начальная дата"),
    date_to: date | None = Query(None, description="Конечная дата"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[TimeEntrySchema]:
    """
    Получение списка временных записей текущего пользователя
    """
    query = select(TimeEntry).where(TimeEntry.user_id == current_user.id)

    if task_id:
        query = query.where(TimeEntry.task_id == uuid.UUID(task_id))

    if project_id:
        # TODO: Добавить join с tasks для фильтрации по project_id
        pass

    if date_from:
        query = query.where(TimeEntry.start_time >= date_from)

    if date_to:
        # Добавляем время 23:59:59 к date_to для включения всей даты
        date_to_with_time = datetime.combine(date_to, time(23, 59, 59))
        query = query.where(TimeEntry.start_time <= date_to_with_time)

    query = query.order_by(TimeEntry.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    time_entries = result.scalars().all()

    return [TimeEntrySchema.model_validate(entry) for entry in time_entries]


@router.get("/by-task/{task_id}", response_model=list[TimeEntrySchema])
async def get_time_entries_by_task(
    task_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[TimeEntrySchema]:
    """
    Получение временных записей по конкретной задаче
    """
    result = await db.execute(
        select(TimeEntry)
        .where(
            TimeEntry.task_id == uuid.UUID(task_id),
            TimeEntry.user_id == current_user.id,
        )
        .order_by(TimeEntry.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    time_entries = result.scalars().all()

    return [TimeEntrySchema.model_validate(entry) for entry in time_entries]


@router.get("/by-date", response_model=list[TimeEntrySchema])
async def get_time_entries_by_date_range(
    date_from: date = Query(..., description="Начальная дата"),
    date_to: date = Query(..., description="Конечная дата"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[TimeEntrySchema]:
    """
    Получение временных записей за период дат
    """
    result = await db.execute(
        select(TimeEntry)
        .where(
            TimeEntry.user_id == current_user.id,
            TimeEntry.start_time >= date_from,
            TimeEntry.start_time <= date_to,
        )
        .order_by(TimeEntry.start_time.desc(), TimeEntry.created_at.desc())
    )
    time_entries = result.scalars().all()

    return [TimeEntrySchema.model_validate(entry) for entry in time_entries]


@router.post("/", response_model=TimeEntrySchema, status_code=status.HTTP_201_CREATED)
async def create_time_entry(
    time_entry_data: TimeEntryCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TimeEntrySchema:
    """
    Создание новой временной записи
    """
    # Проверяем, что задача существует и пользователь имеет к ней доступ
    from app.models.task import Task

    task_result = await db.execute(
        select(Task).where(Task.id == uuid.UUID(str(time_entry_data.task_id)))
    )
    task = task_result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена",
        )

    # TODO: Проверить, что пользователь является участником проекта задачи

    # Рассчитываем duration_minutes если не указано
    entry_data = time_entry_data.model_dump()

    # Если указаны start_time и end_time, рассчитываем duration
    if (
        not entry_data.get("duration_minutes")
        and entry_data.get("start_time")
        and entry_data.get("end_time")
    ):
        from datetime import datetime

        start = entry_data["start_time"]
        end = entry_data["end_time"]
        if isinstance(start, str) and isinstance(end, str):
            start = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end.replace("Z", "+00:00"))

        # Приводим к timezone-aware если нужно
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)

        duration = int((end - start).total_seconds() / 60)
        # Проверяем, что длительность не отрицательная
        if duration < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Время окончания не может быть раньше времени начала",
            )
        entry_data["duration_minutes"] = duration

    # Если указана только длительность, устанавливаем текущее время как start_time
    elif entry_data.get("duration_minutes") and not entry_data.get("start_time"):
        from datetime import datetime

        entry_data["start_time"] = datetime.now(UTC)

    # Преобразуем task_id в UUID
    if "task_id" in entry_data:
        entry_data["task_id"] = uuid.UUID(str(entry_data["task_id"]))

    time_entry = TimeEntry(
        **entry_data,
        user_id=current_user.id,
    )

    db.add(time_entry)
    await db.commit()
    await db.refresh(time_entry)

    return TimeEntrySchema.model_validate(time_entry)


@router.post(
    "/start", response_model=TimeEntrySchema, status_code=status.HTTP_201_CREATED
)
async def start_timer(
    timer_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TimeEntrySchema:
    """
    Запуск таймера для задачи
    """
    task_id = timer_data.get("task_id")
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="task_id является обязательным полем",
        )
    # Проверяем, что задача существует
    from app.models.task import Task

    task_result = await db.execute(select(Task).where(Task.id == uuid.UUID(task_id)))
    task = task_result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена",
        )

    # Проверяем, что нет активного таймера
    active_timer = await db.execute(
        select(TimeEntry).where(
            TimeEntry.user_id == current_user.id,
            TimeEntry.is_active,
        )
    )
    if active_timer.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Уже есть активный таймер",
        )

    from datetime import datetime

    time_entry = TimeEntry(
        task_id=uuid.UUID(task_id),
        user_id=current_user.id,
        start_time=datetime.now(UTC),
        is_active=True,
    )

    db.add(time_entry)
    await db.commit()
    await db.refresh(time_entry)

    return TimeEntrySchema.model_validate(time_entry)


@router.post("/stop", response_model=TimeEntrySchema)
async def stop_timer(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TimeEntrySchema:
    """
    Остановка активного таймера
    """
    # Находим активный таймер
    active_timer = await db.execute(
        select(TimeEntry).where(
            TimeEntry.user_id == current_user.id,
            TimeEntry.is_active,
        )
    )
    time_entry = active_timer.scalar_one_or_none()

    if not time_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Нет активного таймера",
        )

    # Рассчитываем продолжительность
    from datetime import datetime

    time_entry.end_time = datetime.now(UTC)
    if time_entry.start_time:
        # Приводим start_time к timezone-aware если он naive
        start_time = time_entry.start_time
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)

        duration_seconds = int((time_entry.end_time - start_time).total_seconds())
        time_entry.duration_minutes = duration_seconds // 60
    time_entry.is_active = False

    await db.commit()
    await db.refresh(time_entry)

    return TimeEntrySchema.model_validate(time_entry)


@router.get("/{time_entry_id}", response_model=TimeEntrySchema)
async def get_time_entry_by_id(
    time_entry_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TimeEntrySchema:
    """
    Получение временной записи по ID
    """
    # Конвертируем time_entry_id в UUID
    time_entry_uuid = (
        uuid.UUID(time_entry_id) if isinstance(time_entry_id, str) else time_entry_id
    )
    result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.id == time_entry_uuid,
            TimeEntry.user_id == current_user.id,
        )
    )
    time_entry = result.scalar_one_or_none()

    if not time_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена",
        )

    return TimeEntrySchema.model_validate(time_entry)


@router.put("/{time_entry_id}", response_model=TimeEntrySchema)
async def update_time_entry(
    time_entry_id: str,
    time_entry_update: TimeEntryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TimeEntrySchema:
    """
    Обновление временной записи
    """
    # Конвертируем time_entry_id в UUID
    time_entry_uuid = (
        uuid.UUID(time_entry_id) if isinstance(time_entry_id, str) else time_entry_id
    )
    result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.id == time_entry_uuid,
            TimeEntry.user_id == current_user.id,
        )
    )
    time_entry = result.scalar_one_or_none()

    if not time_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена",
        )

    update_data = time_entry_update.model_dump(exclude_unset=True)

    # Проверяем, нужно ли пересчитать duration_minutes
    if "start_time" in update_data or "end_time" in update_data:
        start_time = update_data.get("start_time", time_entry.start_time)
        end_time = update_data.get("end_time", time_entry.end_time)

        # Если оба времени указаны, рассчитываем duration
        if start_time and end_time:

            # Приводим к timezone-aware если нужно
            if hasattr(start_time, "tzinfo") and start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=UTC)
            if hasattr(end_time, "tzinfo") and end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=UTC)

            duration_seconds = int((end_time - start_time).total_seconds())
            update_data["duration_minutes"] = duration_seconds // 60

    for field, value in update_data.items():
        setattr(time_entry, field, value)

    await db.commit()
    await db.refresh(time_entry)

    return TimeEntrySchema.model_validate(time_entry)


@router.put("/{time_entry_id}/start", response_model=TimeEntrySchema)
async def start_timer_for_entry(
    time_entry_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TimeEntrySchema:
    """
    Запуск таймера для конкретной записи
    """
    # Конвертируем time_entry_id в UUID
    time_entry_uuid = (
        uuid.UUID(time_entry_id) if isinstance(time_entry_id, str) else time_entry_id
    )
    result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.id == time_entry_uuid,
            TimeEntry.user_id == current_user.id,
        )
    )
    time_entry = result.scalar_one_or_none()

    if not time_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена",
        )

    # Проверяем, что нет других активных таймеров
    active_timer = await db.execute(
        select(TimeEntry).where(
            TimeEntry.user_id == current_user.id,
            TimeEntry.is_active,
            TimeEntry.id != time_entry_uuid,
        )
    )
    if active_timer.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Уже есть активный таймер",
        )

    from datetime import datetime

    time_entry.is_active = True
    if not time_entry.start_time:
        time_entry.start_time = datetime.now(UTC)

    await db.commit()
    await db.refresh(time_entry)

    return TimeEntrySchema.model_validate(time_entry)


@router.put("/{time_entry_id}/stop", response_model=TimeEntrySchema)
async def stop_timer_for_entry(
    time_entry_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TimeEntrySchema:
    """
    Остановка таймера для конкретной записи
    """
    # Конвертируем time_entry_id в UUID
    time_entry_uuid = (
        uuid.UUID(time_entry_id) if isinstance(time_entry_id, str) else time_entry_id
    )
    result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.id == time_entry_uuid,
            TimeEntry.user_id == current_user.id,
        )
    )
    time_entry = result.scalar_one_or_none()

    if not time_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена",
        )

    if not time_entry.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Таймер уже остановлен",
        )

    from datetime import datetime

    time_entry.end_time = datetime.now(UTC)
    time_entry.is_active = False

    # Рассчитываем продолжительность
    if time_entry.start_time:
        start_time = time_entry.start_time
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)

        duration_seconds = int((time_entry.end_time - start_time).total_seconds())
        time_entry.duration_minutes = duration_seconds // 60

    await db.commit()
    await db.refresh(time_entry)

    return TimeEntrySchema.model_validate(time_entry)


@router.delete("/{time_entry_id}")
async def delete_time_entry(
    time_entry_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Удаление временной записи
    """
    # Конвертируем time_entry_id в UUID
    time_entry_uuid = (
        uuid.UUID(time_entry_id) if isinstance(time_entry_id, str) else time_entry_id
    )
    result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.id == time_entry_uuid,
            TimeEntry.user_id == current_user.id,
        )
    )
    time_entry = result.scalar_one_or_none()

    if not time_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена",
        )

    await db.delete(time_entry)
    await db.commit()

    return {"message": "Запись успешно удалена"}
