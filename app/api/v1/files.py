"""
API роутеры для управления файлами
"""

import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_active_user
from app.core.database import get_db
from app.models.file import FileType
from app.models.user import User
from app.schemas.file import (
    FileListResponse,
    FileResponse,
    FileStatsResponse,
    FileUpdate,
    FileUploadResponse,
)
from app.services.file_service import FileService
from app.services.subscription_service import SubscriptionService

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    task_id: uuid.UUID | None = Form(None),
    project_id: uuid.UUID | None = Form(None),
    description: str | None = Form(None),
    is_public: bool = Form(False),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileUploadResponse:
    """
    Загрузка файла

    Args:
        file: Загружаемый файл
        task_id: ID задачи (опционально)
        project_id: ID проекта (опционально)
        description: Описание файла (опционально)
        is_public: Флаг публичного доступа
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        FileUploadResponse: Результат загрузки

    Raises:
        HTTPException: При ошибке загрузки
    """
    try:
        # Создаем FileService с настройками по умолчанию
        file_service = FileService(db)

        uploaded_file = await file_service.upload_file(
            file=file,
            uploader_id=current_user.id,
            task_id=task_id,
            project_id=project_id,
            description=description,
            is_public=is_public,
        )

        return FileUploadResponse(
            message="File uploaded successfully",
            file=FileResponse.model_validate(uploaded_file),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to upload file: {str(e)}"
        ) from e


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """
    Получение информации о файле

    Args:
        file_id: ID файла
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        FileResponse: Информация о файле

    Raises:
        HTTPException: Если файл не найден или нет доступа
    """
    file_service = FileService(db)

    db_file = await file_service.get_file_by_id(file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    # Проверка доступа
    if (
        not db_file.is_public
        and db_file.uploader_id != current_user.id
        and not await _has_project_access(current_user, db_file.project_id, db)
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse.model_validate(db_file)


@router.get("/{file_id}/download")
async def download_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Скачивание файла

    Args:
        file_id: ID файла
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        StreamingResponse: Файл для скачивания

    Raises:
        HTTPException: Если файл не найден или нет доступа
    """
    file_service = FileService(db)

    result = await file_service.download_file(file_id)
    if not result:
        raise HTTPException(status_code=404, detail="File not found")

    db_file, content = result

    # Проверка доступа
    if (
        not db_file.is_public
        and db_file.uploader_id != current_user.id
        and not await _has_project_access(current_user, db_file.project_id, db)
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    return StreamingResponse(
        iter([content]),
        media_type=db_file.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename={db_file.original_filename}"
        },
    )


@router.get("/", response_model=FileListResponse)
async def get_user_files(
    task_id: uuid.UUID | None = Query(None, description="Фильтр по задаче"),
    project_id: uuid.UUID | None = Query(None, description="Фильтр по проекту"),
    file_type: FileType | None = Query(None, description="Фильтр по типу файла"),
    offset: int = Query(0, ge=0, description="Смещение"),
    limit: int = Query(20, ge=1, le=100, description="Лимит"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileListResponse:
    """
    Получение файлов пользователя

    Args:
        task_id: Фильтр по задаче
        project_id: Фильтр по проекту
        file_type: Фильтр по типу файла
        offset: Смещение
        limit: Лимит
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        FileListResponse: Список файлов
    """
    file_service = FileService(db)

    files = await file_service.get_user_files(
        user_id=current_user.id,
        task_id=task_id,
        project_id=project_id,
        file_type=file_type,
        offset=offset,
        limit=limit,
    )

    return FileListResponse(
        files=[FileResponse.model_validate(f) for f in files],
        total=len(files),
        offset=offset,
        limit=limit,
    )


@router.get("/task/{task_id}", response_model=FileListResponse)
async def get_task_files(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileListResponse:
    """
    Получение файлов задачи

    Args:
        task_id: ID задачи
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        FileListResponse: Список файлов задачи

    Raises:
        HTTPException: Если нет доступа к задаче
    """
    # Проверка доступа к задаче
    if not await _has_task_access(current_user, task_id, db):
        raise HTTPException(status_code=403, detail="Access denied to task")

    file_service = FileService(db)
    files = await file_service.get_task_files(task_id)

    return FileListResponse(
        files=[FileResponse.model_validate(f) for f in files],
        total=len(files),
        offset=0,
        limit=len(files),
    )


@router.get("/project/{project_id}", response_model=FileListResponse)
async def get_project_files(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileListResponse:
    """
    Получение файлов проекта

    Args:
        project_id: ID проекта
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        FileListResponse: Список файлов проекта

    Raises:
        HTTPException: Если нет доступа к проекту
    """
    # Проверка доступа к проекту
    if not await _has_project_access(current_user, project_id, db):
        raise HTTPException(status_code=403, detail="Access denied to project")

    file_service = FileService(db)
    files = await file_service.get_project_files(project_id)

    return FileListResponse(
        files=[FileResponse.model_validate(f) for f in files],
        total=len(files),
        offset=0,
        limit=len(files),
    )


@router.put("/{file_id}", response_model=FileResponse)
async def update_file(
    file_id: uuid.UUID,
    file_update: FileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """
    Обновление метаданных файла

    Args:
        file_id: ID файла
        file_update: Данные для обновления
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        FileResponse: Обновленный файл

    Raises:
        HTTPException: Если файл не найден или нет доступа
    """
    file_service = FileService(db)

    # Проверка доступа
    db_file = await file_service.get_file_by_id(file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    if db_file.uploader_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only file owner can update file")

    updated_file = await file_service.update_file(
        file_id=file_id,
        description=file_update.description,
        is_public=file_update.is_public,
    )

    if not updated_file:
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse.model_validate(updated_file)


@router.delete("/{file_id}")
async def delete_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Удаление файла

    Args:
        file_id: ID файла
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        dict: Результат удаления

    Raises:
        HTTPException: Если файл не найден или нет доступа
    """
    file_service = FileService(db)

    # Проверка доступа
    db_file = await file_service.get_file_by_id(file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    if db_file.uploader_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only file owner can delete file")

    success = await file_service.delete_file(file_id)

    if not success:
        raise HTTPException(status_code=404, detail="File not found")

    return {"message": "File deleted successfully"}


@router.get("/stats/summary", response_model=FileStatsResponse)
async def get_file_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileStatsResponse:
    """
    Получение статистики по файлам пользователя
    """
    file_service = FileService(db)
    subscription_service = SubscriptionService(db)

    stats = await file_service.get_file_stats(user_id=current_user.id)
    limits = await subscription_service.get_user_limits(user_id=current_user.id)

    # Добавляем информацию о подписке
    subscription = await subscription_service.get_user_subscription(current_user.id)
    stats["subscription_info"] = {
        "plan": subscription.plan if subscription else "free",
        "limits": limits,
        "usage": {
            "storage_used": await subscription_service.get_storage_usage(
                current_user.id
            ),
            "files_count": await subscription_service.get_files_count(current_user.id),
        },
    }

    return FileStatsResponse(**stats)


async def _has_project_access(
    user: User, project_id: uuid.UUID | None, db: AsyncSession
) -> bool:
    """Проверка доступа к проекту"""
    if not project_id:
        return False

    from sqlalchemy import select

    from app.models.project import ProjectMember

    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user.id,
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    return member is not None


async def _has_task_access(user: User, task_id: uuid.UUID, db: AsyncSession) -> bool:
    """Проверка доступа к задаче"""
    from sqlalchemy import select

    from app.models.task import Task

    stmt = select(Task).where(Task.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        return False

    # Проверка доступа через проект
    return await _has_project_access(user, task.project_id, db)
