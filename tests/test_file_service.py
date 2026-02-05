"""
Тесты для FileService
"""

import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File, FileType
from app.services.file_service import FileService


@pytest.fixture
async def file_service(db_session: AsyncSession) -> FileService:
    """Фикстура для FileService"""
    return FileService(db_session)


@pytest.fixture
def sample_file() -> UploadFile:
    """Фикстура для тестового файла"""
    file = UploadFile(
        filename="test.txt", file=MagicMock(), headers={"content-type": "text/plain"}
    )
    file.read = AsyncMock(return_value=b"test content")
    return file


@pytest.fixture
def sample_image() -> UploadFile:
    """Фикстура для тестового изображения"""
    file = UploadFile(
        filename="test.jpg", file=MagicMock(), headers={"content-type": "image/jpeg"}
    )
    file.read = AsyncMock(return_value=b"\xff\xd8\xff\xe0\x00\x10JFIF")
    return file


class TestFileService:
    """Тесты для FileService"""

    async def test_upload_file_success(
        self, file_service: FileService, sample_file: UploadFile, test_user
    ) -> None:
        """Тест успешной загрузки файла"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Мокаем настройки
            with patch.object(file_service, "upload_dir", Path(temp_dir)):
                with patch.object(file_service, "max_file_size", 1024 * 1024):
                    with patch.object(
                        file_service, "allowed_extensions", [".txt", ".jpg"]
                    ):
                        # Мокаем сервис подписок
                        with patch.object(
                            file_service.subscription_service,
                            "can_upload_file",
                            return_value=(True, None),
                        ):
                            with patch.object(
                                file_service.subscription_service,
                                "get_user_limits",
                                return_value={"max_file_size": 1024 * 1024},
                            ):
                                with patch.object(
                                    file_service.subscription_service,
                                    "track_usage",
                                    new_callable=AsyncMock,
                                ):
                                    # Мокаем запись файла
                                    with patch(
                                        "builtins.open", new_callable=MagicMock
                                    ) as mock_open:
                                        mock_file = MagicMock()
                                        mock_open.return_value.__enter__.return_value = (
                                            mock_file
                                        )

                                        # Загружаем файл
                                        result = await file_service.upload_file(
                                            file=sample_file,
                                            uploader_id=test_user.id,
                                            description="Test file",
                                        )

                                        # Проверки
                                        assert result is not None
                                        assert result.original_filename == "test.txt"
                                        assert result.file_type == FileType.DOCUMENT
                                        assert result.uploader_id == test_user.id
                                        assert result.description == "Test file"
                                        assert result.file_size == len(b"test content")

                                        # Проверяем что open был вызван для записи файла
                                        mock_open.assert_called_once()
                                        mock_file.write.assert_called_once_with(
                                            b"test content"
                                        )

    async def test_upload_file_too_large(
        self, file_service: FileService, sample_file: UploadFile, test_user
    ) -> None:
        """Тест загрузки файла слишком большого размера"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(file_service, "upload_dir", Path(temp_dir)):
                with patch.object(file_service, "max_file_size", 10):  # 10 bytes limit
                    with patch.object(file_service, "allowed_extensions", [".txt"]):

                        # Мокаем большой контент
                        sample_file.read = AsyncMock(return_value=b"x" * 100)

                        from fastapi import HTTPException

                        with pytest.raises(HTTPException):
                            await file_service.upload_file(
                                file=sample_file,
                                uploader_id=test_user.id,
                            )

    async def test_upload_file_invalid_extension(
        self, file_service: FileService, sample_file: UploadFile, test_user
    ) -> None:
        """Тест загрузки файла с недопустимым расширением"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(file_service, "upload_dir", Path(temp_dir)):
                with patch.object(file_service, "max_file_size", 1024 * 1024):
                    with patch.object(file_service, "allowed_extensions", [".jpg"]):

                        from fastapi import HTTPException

                        with pytest.raises(HTTPException):
                            await file_service.upload_file(
                                file=sample_file,
                                uploader_id=test_user.id,
                            )

    async def test_upload_image_file(
        self, file_service: FileService, sample_image: UploadFile, test_user
    ) -> None:
        """Тест загрузки изображения"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(file_service, "upload_dir", Path(temp_dir)):
                with patch.object(file_service, "max_file_size", 1024 * 1024):
                    with patch.object(file_service, "allowed_extensions", [".jpg"]):

                        result = await file_service.upload_file(
                            file=sample_image,
                            uploader_id=test_user.id,
                        )

                        assert result is not None
                        assert result.file_type == FileType.IMAGE
                        assert result.mime_type == "image/jpeg"

    async def test_get_file_by_id(
        self, file_service: FileService, test_file: File
    ) -> None:
        """Тест получения файла по ID"""
        result = await file_service.get_file_by_id(test_file.id)

        assert result is not None
        assert result.id == test_file.id
        assert result.original_filename == test_file.original_filename

    async def test_get_file_by_id_not_found(self, file_service: FileService) -> None:
        """Тест получения несуществующего файла"""
        fake_id = uuid.uuid4()
        result = await file_service.get_file_by_id(fake_id)

        assert result is None

    async def test_get_user_files(
        self, file_service: FileService, test_user: File, test_file: File
    ) -> None:
        """Тест получения файлов пользователя"""
        # test_file уже должен принадлежать test_user
        result = await file_service.get_user_files(user_id=test_user.id)

        assert len(result) >= 1
        assert any(f.id == test_file.id for f in result)

    async def test_get_user_files_with_filters(
        self, file_service: FileService, test_user: File, test_file: File
    ) -> None:
        """Тест получения файлов пользователя с фильтрами"""
        # Фильтр по типу файла
        result = await file_service.get_user_files(
            user_id=test_user.id, file_type=test_file.file_type
        )

        assert len(result) >= 1
        assert all(f.file_type == test_file.file_type for f in result)

    async def test_update_file(
        self, file_service: FileService, test_file: File
    ) -> None:
        """Тест обновления файла"""
        new_description = "Updated description"
        new_is_public = True

        result = await file_service.update_file(
            file_id=test_file.id,
            description=new_description,
            is_public=new_is_public,
        )

        assert result is not None
        assert result.description == new_description
        assert result.is_public == new_is_public

    async def test_update_file_not_found(self, file_service: FileService) -> None:
        """Тест обновления несуществующего файла"""
        fake_id = uuid.uuid4()
        result = await file_service.update_file(fake_id, description="test")

        assert result is None

    async def test_delete_file(
        self, file_service: FileService, test_file: File
    ) -> None:
        """Тест удаления файла"""
        result = await file_service.delete_file(test_file.id)

        assert result is True

        # Проверяем что файл помечен как удаленный
        deleted_file = await file_service.get_file_by_id(test_file.id)
        assert deleted_file is None  # is_deleted=True фильтрует

    async def test_delete_file_not_found(self, file_service: FileService) -> None:
        """Тест удаления несуществующего файла"""
        fake_id = uuid.uuid4()
        result = await file_service.delete_file(fake_id)

        assert result is False

    async def test_download_file(
        self, file_service: FileService, test_file: File
    ) -> None:
        """Тест скачивания файла"""
        # Создаем реальный файл для теста
        test_content = b"test file content"
        file_path = Path(test_file.file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(test_content)

        try:
            result = await file_service.download_file(test_file.id)

            assert result is not None
            file, content = result
            assert file.id == test_file.id
            assert content == test_content
            assert file.download_count == 1  # Счетчик увеличился
        finally:
            # Очистка
            if file_path.exists():
                file_path.unlink()

    async def test_download_file_not_found(self, file_service: FileService) -> None:
        """Тест скачивания несуществующего файла"""
        fake_id = uuid.uuid4()
        result = await file_service.download_file(fake_id)

        assert result is None

    async def test_get_file_stats(
        self, file_service: FileService, test_user: File, test_file: File
    ) -> None:
        """Тест получения статистики файлов"""
        result = await file_service.get_file_stats(user_id=test_user.id)

        assert result is not None
        assert "total_files" in result
        assert "total_size" in result
        assert "type_stats" in result
        assert "avg_file_size" in result
        assert result["total_files"] >= 1

    def test_determine_file_type(self, file_service: FileService) -> None:
        """Тест определения типа файла"""
        # Изображения
        assert file_service._determine_file_type("image/jpeg") == FileType.IMAGE
        assert file_service._determine_file_type("image/png") == FileType.IMAGE

        # Документы
        assert file_service._determine_file_type("application/pdf") == FileType.DOCUMENT
        assert file_service._determine_file_type("text/plain") == FileType.DOCUMENT

        # Видео
        assert file_service._determine_file_type("video/mp4") == FileType.VIDEO

        # Аудио
        assert file_service._determine_file_type("audio/mp3") == FileType.AUDIO

        # Архивы
        assert file_service._determine_file_type("application/zip") == FileType.ARCHIVE

        # Другое
        assert (
            file_service._determine_file_type("application/octet-stream")
            == FileType.OTHER
        )

    async def test_file_properties(self, test_file: File) -> None:
        """Тест свойств файла"""
        # Расширение
        assert test_file.file_extension == "txt"

        # Тип файла
        assert test_file.is_document
        assert not test_file.is_image

        # Форматированный размер
        assert "B" in test_file.formatted_size

        # Методы
        original_count = test_file.download_count
        test_file.increment_download_count()
        assert test_file.download_count == original_count + 1
        assert test_file.last_accessed_at is not None

        # Мягкое удаление
        test_file.soft_delete()
        assert test_file.is_deleted

        # Восстановление
        test_file.restore()
        assert not test_file.is_deleted
