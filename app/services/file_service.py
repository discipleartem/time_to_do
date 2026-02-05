"""
Сервис для управления файлами
"""

import hashlib
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.file import File, FileType
from app.services.subscription_service import SubscriptionService


class FileService:
    """Сервис для управления файлами"""

    def __init__(self, db: AsyncSession, settings: object | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.upload_dir = Path(self.settings.UPLOAD_DIR)
        self.max_file_size = self.settings.MAX_FILE_SIZE
        self.allowed_extensions = self.settings.ALLOWED_EXTENSIONS
        self.subscription_service = SubscriptionService(db)

    async def upload_file(
        self,
        file: UploadFile,
        uploader_id: uuid.UUID,
        task_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        description: str | None = None,
        is_public: bool = False,
    ) -> File:
        """
        Загрузка файла с проверкой подписки

        Args:
            file: Загружаемый файл
            uploader_id: ID пользователя, загрузившего файл
            task_id: ID задачи (опционально)
            project_id: ID проекта (опционально)
            description: Описание файла (опционально)
            is_public: Флаг публичного доступа

        Returns:
            File: Созданная запись о файле

        Raises:
            HTTPException: При ошибке загрузки или превышении лимитов
        """
        # Используем текущие настройки, а не получаем новые
        upload_dir = Path(self.settings.UPLOAD_DIR)

        from app.models.user import User

        # Получаем пользователя для проверки подписки
        user_stmt = select(User).where(User.id == uploader_id)
        user_result = await self.db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Определяем тип файла
        file_type = self._determine_file_type(file.content_type or "")

        # Проверяем размер файла (предварительная проверка)
        content = await file.read()
        file_size = len(content)

        # Проверяем лимиты подписки
        can_upload, error_message = await self.subscription_service.can_upload_file(
            user, file_size, file_type
        )

        if not can_upload:
            raise HTTPException(
                status_code=403, detail=error_message or "Upload limit exceeded"
            )

        # Получаем актуальные лимиты
        limits = await self.subscription_service.get_user_limits(uploader_id)

        # Валидация файла
        await self._validate_file(file)

        # Генерация уникального имени файла
        file_extension = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        # Создание директории если не существует
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Путь к файлу
        file_path = upload_dir / unique_filename

        try:
            # Проверка размера файла с учетом лимитов подписки
            max_size = min(limits["max_file_size"], self.max_file_size)
            if file_size > max_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File size exceeds maximum allowed size of {max_size} bytes",
                )

            # Запись файла
            with open(file_path, "wb") as f:
                f.write(content)

            # Вычисление checksum
            checksum = hashlib.sha256(content).hexdigest()

            # Создание записи в БД
            db_file = File(
                filename=unique_filename,
                original_filename=file.filename or "unnamed",
                file_path=str(file_path),
                file_size=file_size,
                mime_type=file.content_type or "application/octet-stream",
                file_type=file_type,
                description=description,
                checksum=checksum,
                uploader_id=uploader_id,
                task_id=task_id,
                project_id=project_id,
                is_public=is_public,
            )

            self.db.add(db_file)
            await self.db.commit()
            await self.db.refresh(db_file)

            # Отслеживаем использование
            await self.subscription_service.track_usage(
                uploader_id, file_size, file_type
            )

            return db_file

        except Exception as e:
            # Удаление файла при ошибке
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=500, detail=f"Failed to upload file: {str(e)}"
            ) from e

    async def get_file_by_id(self, file_id: uuid.UUID) -> File | None:
        """Получение файла по ID"""
        stmt = select(File).where(File.id == file_id, File.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_files(
        self,
        user_id: uuid.UUID,
        task_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        file_type: FileType | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[File]:
        """
        Получение файлов пользователя

        Args:
            user_id: ID пользователя
            task_id: Фильтр по задаче
            project_id: Фильтр по проекту
            file_type: Фильтр по типу файла
            offset: Смещение
            limit: Лимит

        Returns:
            list[File]: Список файлов
        """
        stmt = select(File).where(File.uploader_id == user_id, File.is_deleted == False)

        if task_id:
            stmt = stmt.where(File.task_id == task_id)
        if project_id:
            stmt = stmt.where(File.project_id == project_id)
        if file_type:
            stmt = stmt.where(File.file_type == file_type)

        stmt = stmt.order_by(File.uploaded_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_task_files(self, task_id: uuid.UUID) -> list[File]:
        """Получение файлов задачи"""
        stmt = (
            select(File)
            .where(File.task_id == task_id, File.is_deleted == False)
            .order_by(File.uploaded_at.desc())
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_project_files(self, project_id: uuid.UUID) -> list[File]:
        """Получение файлов проекта"""
        stmt = (
            select(File)
            .where(File.project_id == project_id, File.is_deleted == False)
            .order_by(File.uploaded_at.desc())
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_file(
        self,
        file_id: uuid.UUID,
        description: str | None = None,
        is_public: bool | None = None,
    ) -> File | None:
        """
        Обновление метаданных файла

        Args:
            file_id: ID файла
            description: Новое описание
            is_public: Новый флаг публичности

        Returns:
            File: Обновленный файл или None
        """
        db_file = await self.get_file_by_id(file_id)
        if not db_file:
            return None

        if description is not None:
            db_file.description = description
        if is_public is not None:
            db_file.is_public = is_public

        await self.db.commit()
        await self.db.refresh(db_file)

        return db_file

    async def delete_file(self, file_id: uuid.UUID) -> bool:
        """
        Удаление файла (мягкое удаление)

        Args:
            file_id: ID файла

        Returns:
            bool: True если файл удален
        """
        db_file = await self.get_file_by_id(file_id)
        if not db_file:
            return False

        db_file.soft_delete()
        await self.db.commit()

        return True

    async def download_file(self, file_id: uuid.UUID) -> tuple[File, bytes] | None:
        """
        Скачать файл

        Args:
            file_id: ID файла

        Returns:
            tuple[File, bytes]: Файл и его содержимое или None
        """
        db_file = await self.get_file_by_id(file_id)
        if not db_file:
            return None

        try:
            file_path = Path(db_file.file_path)
            if not file_path.exists():
                return None

            with open(file_path, "rb") as f:
                content = f.read()

            # Обновление статистики
            db_file.increment_download_count()
            await self.db.commit()

            return db_file, content

        except Exception:
            return None

    async def _validate_file(self, file: UploadFile) -> None:
        """Валидация файла"""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Проверка расширения
        file_extension = Path(file.filename).suffix.lower()
        if self.allowed_extensions and file_extension not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File extension {file_extension} is not allowed",
            )

    def _determine_file_type(self, mime_type: str) -> FileType:
        """Определение типа файла по MIME типу"""
        if mime_type.startswith("image/"):
            return FileType.IMAGE
        elif mime_type.startswith("video/"):
            return FileType.VIDEO
        elif mime_type.startswith("audio/"):
            return FileType.AUDIO
        elif mime_type in [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "text/plain",
            "text/csv",
        ]:
            return FileType.DOCUMENT
        elif mime_type in [
            "application/zip",
            "application/x-rar-compressed",
            "application/x-7z-compressed",
            "application/gzip",
        ]:
            return FileType.ARCHIVE
        else:
            return FileType.OTHER

    async def get_file_stats(self, user_id: uuid.UUID | None = None) -> dict:
        """
        Получение статистики по файлам

        Args:
            user_id: ID пользователя для фильтрации (опционально)

        Returns:
            dict: Статистика
        """
        stmt = select(File).where(File.is_deleted == False)

        if user_id:
            stmt = stmt.where(File.uploader_id == user_id)

        result = await self.db.execute(stmt)
        files = result.scalars().all()

        total_files = len(files)
        total_size = sum(f.file_size for f in files)

        # Статистика по типам
        type_stats = {}
        for file_type in FileType:
            count = sum(1 for f in files if f.file_type == file_type)
            size = sum(f.file_size for f in files if f.file_type == file_type)
            type_stats[file_type.value] = {"count": count, "size": size}

        return {
            "total_files": total_files,
            "total_size": total_size,
            "type_stats": type_stats,
            "avg_file_size": total_size / total_files if total_files > 0 else 0,
        }
