"""
Pydantic схемы для файлов
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.file import FileType


class FileBase(BaseModel):
    """Базовая схема файла"""

    filename: str = Field(..., description="Имя файла")
    original_filename: str = Field(..., description="Оригинальное имя файла")
    description: str | None = Field(None, description="Описание файла")
    is_public: bool = Field(False, description="Флаг публичного доступа")


class FileCreate(FileBase):
    """Схема для создания файла"""

    task_id: uuid.UUID | None = Field(None, description="ID задачи")
    project_id: uuid.UUID | None = Field(None, description="ID проекта")


class FileUpdate(BaseModel):
    """Схема для обновления файла"""

    description: str | None = Field(None, description="Описание файла")
    is_public: bool | None = Field(None, description="Флаг публичного доступа")


class FileResponse(FileBase):
    """Схема ответа файла"""

    id: uuid.UUID = Field(..., description="ID файла")
    file_size: int = Field(..., description="Размер файла в байтах")
    mime_type: str = Field(..., description="MIME тип файла")
    file_type: FileType = Field(..., description="Тип файла")
    checksum: str | None = Field(None, description="SHA-256 checksum")
    uploader_id: uuid.UUID = Field(..., description="ID загрузившего пользователя")
    task_id: uuid.UUID | None = Field(None, description="ID задачи")
    project_id: uuid.UUID | None = Field(None, description="ID проекта")
    download_count: int = Field(..., description="Количество скачиваний")
    uploaded_at: datetime = Field(..., description="Дата загрузки")
    last_accessed_at: datetime | None = Field(
        None, description="Дата последнего доступа"
    )

    # Вычисляемые поля
    file_extension: str = Field(..., description="Расширение файла")
    formatted_size: str = Field(..., description="Форматированный размер файла")
    is_image: bool = Field(..., description="Является ли файл изображением")
    is_document: bool = Field(..., description="Является ли файл документом")

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    """Схема ответа при загрузке файла"""

    message: str = Field(..., description="Сообщение о результате")
    file: FileResponse = Field(..., description="Загруженный файл")


class FileListResponse(BaseModel):
    """Схема ответа со списком файлов"""

    files: list[FileResponse] = Field(..., description="Список файлов")
    total: int = Field(..., description="Общее количество файлов")
    offset: int = Field(..., description="Смещение")
    limit: int = Field(..., description="Лимит")


class FileStatsResponse(BaseModel):
    """Схема ответа со статистикой файлов"""

    total_files: int = Field(..., description="Общее количество файлов")
    total_size: int = Field(..., description="Общий размер в байтах")
    avg_file_size: float = Field(..., description="Средний размер файла")
    type_stats: dict[str, dict[str, int]] = Field(
        ..., description="Статистика по типам файлов"
    )


class FileSearchRequest(BaseModel):
    """Схема запроса поиска файлов"""

    query: str | None = Field(None, description="Поисковый запрос")
    file_type: FileType | None = Field(None, description="Фильтр по типу файла")
    task_id: uuid.UUID | None = Field(None, description="Фильтр по задаче")
    project_id: uuid.UUID | None = Field(None, description="Фильтр по проекту")
    is_public: bool | None = Field(None, description="Фильтр по публичности")
    offset: int = Field(0, ge=0, description="Смещение")
    limit: int = Field(20, ge=1, le=100, description="Лимит")
