"""
Модель File для управления файлами
"""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import UUID, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:

    from app.models.project import Project
    from app.models.task import Task
    from app.models.user import User


class FileType(str, Enum):
    """Типы файлов"""

    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    OTHER = "other"


class File(BaseModel):
    """Модель файла"""

    __tablename__ = "files"

    # Основные поля
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_type: Mapped[FileType] = mapped_column(
        String(20), nullable=False, default=FileType.OTHER
    )

    # Метаданные
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256

    # Связи с сущностями
    uploader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )

    # Статус и доступ
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Временные метки
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Отношения
    if TYPE_CHECKING:
        uploader: Mapped["User"] = relationship("User", lazy="selectin")
        task: Mapped["Task" | None] = relationship("Task", lazy="selectin")
        project: Mapped["Project" | None] = relationship("Project", lazy="selectin")
    else:
        uploader: Mapped[any] = relationship("User", lazy="selectin")
        task: Mapped[any] = relationship("Task", lazy="selectin")
        project: Mapped[any] = relationship("Project", lazy="selectin")

    def __repr__(self) -> str:
        return f"<File(id={self.id}, filename={self.filename}, size={self.file_size})>"

    @property
    def file_extension(self) -> str:
        """Расширение файла"""
        return self.filename.split(".")[-1].lower() if "." in self.filename else ""

    @property
    def is_image(self) -> bool:
        """Является ли файл изображением"""
        return self.file_type == FileType.IMAGE

    @property
    def is_document(self) -> bool:
        """Является ли файл документом"""
        return self.file_type == FileType.DOCUMENT

    @property
    def formatted_size(self) -> str:
        """Форматированный размер файла"""
        size: float = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def increment_download_count(self) -> None:
        """Увеличить счетчик скачиваний"""
        self.download_count += 1
        self.last_accessed_at = datetime.now(UTC)

    def soft_delete(self) -> None:
        """Мягкое удаление файла"""
        self.is_deleted = True

    def restore(self) -> None:
        """Восстановление файла"""
        self.is_deleted = False
