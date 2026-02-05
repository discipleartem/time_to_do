"""
Тесты для API эндпоинтов файлов
"""

import tempfile
import uuid
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def upload_file():
    """Фикстура для создания тестового файла"""
    file_content = b"test file content"
    return ("test.txt", BytesIO(file_content), "text/plain")


@pytest.fixture
def upload_image():
    """Фикстура для создания тестового изображения"""
    image_content = b"\xff\xd8\xff\xe0\x00\x10JFIF"
    return ("test.jpg", BytesIO(image_content), "image/jpeg")


class TestFilesAPI:
    """Тесты для API эндпоинтов файлов"""

    async def test_upload_file_success(
        self, client: AsyncClient, authenticated_user, upload_file
    ) -> None:
        """Тест успешной загрузки файла"""
        filename, file_content, content_type = upload_file

        # Используем реальную uploads директорию

        # Создаем временный файл для загрузки
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w+b", delete=False) as temp_file:
            temp_file.write(file_content.getbuffer())
            temp_file.seek(0)

            # Используем правильный формат multipart form
            files = {
                "file": (filename, temp_file, content_type),
                "description": ("", "Test file description", "text/plain"),
            }

            response = await client.post(
                "/api/v1/files/upload",
                files=files,
                headers=authenticated_user["headers"],
            )

            # Закрываем временный файл
            temp_file.close()

        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")

        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "File uploaded successfully"
        assert "file" in result
        assert result["file"]["original_filename"] == filename
        assert result["file"]["description"] == "Test file description"

    async def test_upload_file_unauthorized(
        self, client: AsyncClient, upload_file
    ) -> None:
        """Тест загрузки файла без авторизации"""
        filename, file_content, content_type = upload_file

        data = {"file": (filename, file_content, content_type)}

        response = await client.post("/api/v1/files/upload", files=data)

        assert response.status_code == 401

    async def test_get_file_success(
        self, client: AsyncClient, authenticated_user, test_file
    ) -> None:
        """Тест получения информации о файле"""
        response = await client.get(
            f"/api/v1/files/{test_file.id}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == 200
        result = response.json()
        assert result["id"] == str(test_file.id)
        assert result["original_filename"] == test_file.original_filename

    async def test_get_file_not_found(
        self, client: AsyncClient, authenticated_user
    ) -> None:
        """Тест получения несуществующего файла"""
        fake_id = uuid.uuid4()

        response = await client.get(
            f"/api/v1/files/{fake_id}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == 404

    async def test_get_file_access_denied(
        self, client: AsyncClient, other_user_auth, test_file
    ) -> None:
        """Тест получения файла без прав доступа"""
        # test_file принадлежит authenticated_user, не other_user
        response = await client.get(
            f"/api/v1/files/{test_file.id}",
            headers=other_user_auth["headers"],
        )

        assert response.status_code == 403

    async def test_download_file_success(
        self, client: AsyncClient, authenticated_user, test_file
    ) -> None:
        """Тест скачивания файла"""
        # Создаем реальный файл
        test_content = b"test file content"
        file_path = Path(test_file.file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(test_content)

        try:
            response = await client.get(
                f"/api/v1/files/{test_file.id}/download",
                headers=authenticated_user["headers"],
            )

            assert response.status_code == 200
            assert response.content == test_content
            assert "attachment" in response.headers["content-disposition"]
        finally:
            # Очистка
            if file_path.exists():
                file_path.unlink()

    async def test_download_file_not_found(
        self, client: AsyncClient, authenticated_user
    ) -> None:
        """Тест скачивания несуществующего файла"""
        fake_id = uuid.uuid4()

        response = await client.get(
            f"/api/v1/files/{fake_id}/download",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == 404

    async def test_get_user_files(
        self, client: AsyncClient, authenticated_user, test_file
    ) -> None:
        """Тест получения файлов пользователя"""
        response = await client.get(
            "/api/v1/files/",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == 200
        result = response.json()
        assert "files" in result
        assert "total" in result
        assert result["total"] >= 1
        assert any(f["id"] == str(test_file.id) for f in result["files"])

    async def test_get_user_files_with_filters(
        self, client: AsyncClient, authenticated_user, test_file
    ) -> None:
        """Тест получения файлов пользователя с фильтрами"""
        response = await client.get(
            f"/api/v1/files/?file_type={test_file.file_type.value}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == 200
        result = response.json()
        assert all(f["file_type"] == test_file.file_type.value for f in result["files"])

    async def test_get_task_files(
        self,
        client: AsyncClient,
        authenticated_user,
        test_file,
        test_task,
        db_session: AsyncSession,
    ) -> None:
        """Тест получения файлов задачи"""
        # Привязываем файл к задаче
        test_file.task_id = test_task.id
        await authenticated_user["db"].commit()

        # Создаем ProjectMember напрямую для теста
        from app.models.project import ProjectMember

        member = ProjectMember(
            project_id=test_task.project_id,
            user_id=authenticated_user["user"].id,
            role="OWNER",
        )
        db_session.add(member)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/files/task/{test_task.id}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == 200
        result = response.json()
        assert "files" in result
        assert any(f["id"] == str(test_file.id) for f in result["files"])

    async def test_get_task_files_access_denied(
        self, client: AsyncClient, other_user_auth, test_task
    ) -> None:
        """Тест получения файлов задачи без доступа"""
        response = await client.get(
            f"/api/v1/files/task/{test_task.id}",
            headers=other_user_auth["headers"],
        )

        assert response.status_code == 403

    async def test_get_project_files(
        self,
        client: AsyncClient,
        authenticated_user,
        test_file,
        test_project,
        db_session: AsyncSession,
    ) -> None:
        """Тест получения файлов проекта"""
        # Привязываем файл к проекту
        test_file.project_id = test_project.id
        await authenticated_user["db"].commit()

        # Создаем ProjectMember напрямую для теста
        from app.models.project import ProjectMember

        member = ProjectMember(
            project_id=test_project.id,
            user_id=authenticated_user["user"].id,
            role="OWNER",
        )
        db_session.add(member)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/files/project/{test_project.id}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == 200
        result = response.json()
        assert "files" in result

    async def test_update_file_success(
        self, client: AsyncClient, authenticated_user, test_file
    ) -> None:
        """Тест обновления файла"""
        update_data = {
            "description": "Updated description",
            "is_public": True,
        }

        response = await client.put(
            f"/api/v1/files/{test_file.id}",
            json=update_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code == 200
        result = response.json()
        assert result["description"] == "Updated description"
        assert result["is_public"] is True

    async def test_update_file_not_owner(
        self, client: AsyncClient, other_user_auth, test_file
    ) -> None:
        """Тест обновления файла не владельцем"""
        update_data = {"description": "Updated description"}

        response = await client.put(
            f"/api/v1/files/{test_file.id}",
            json=update_data,
            headers=other_user_auth["headers"],
        )

        assert response.status_code == 403

    async def test_update_file_not_found(
        self, client: AsyncClient, authenticated_user
    ) -> None:
        """Тест обновления несуществующего файла"""
        fake_id = uuid.uuid4()
        update_data = {"description": "Updated description"}

        response = await client.put(
            f"/api/v1/files/{fake_id}",
            json=update_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code == 404

    async def test_delete_file_success(
        self, client: AsyncClient, authenticated_user, test_file
    ) -> None:
        """Тест удаления файла"""
        response = await client.delete(
            f"/api/v1/files/{test_file.id}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "File deleted successfully"

    async def test_delete_file_not_owner(
        self, client: AsyncClient, other_user_auth, test_file
    ) -> None:
        """Тест удаления файла не владельцем"""
        response = await client.delete(
            f"/api/v1/files/{test_file.id}",
            headers=other_user_auth["headers"],
        )

        assert response.status_code == 403

    async def test_delete_file_not_found(
        self, client: AsyncClient, authenticated_user
    ) -> None:
        """Тест удаления несуществующего файла"""
        fake_id = uuid.uuid4()

        response = await client.delete(
            f"/api/v1/files/{fake_id}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == 404

    async def test_get_file_stats(
        self, client: AsyncClient, authenticated_user, test_file
    ) -> None:
        """Тест получения статистики файлов"""
        response = await client.get(
            "/api/v1/files/stats/summary",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == 200
        result = response.json()
        assert "total_files" in result
        assert "total_size" in result
        assert "type_stats" in result
        assert "avg_file_size" in result
        assert result["total_files"] >= 1

    async def test_upload_file_with_task_and_project(
        self,
        client: AsyncClient,
        authenticated_user,
        upload_file,
        test_task,
        test_project,
    ) -> None:
        """Тест загрузки файла с привязкой к задаче и проекту"""
        filename, file_content, content_type = upload_file

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("app.core.config.get_settings") as mock_settings:
                mock_settings.return_value.UPLOAD_DIR = temp_dir

                # Создаем временный файл для загрузки
                with tempfile.NamedTemporaryFile(mode="w+b", delete=False) as temp_file:
                    temp_file.write(file_content.getbuffer())
                    temp_file.seek(0)

                    # Используем правильный формат multipart form
                    files = {
                        "file": (filename, temp_file, content_type),
                        "task_id": ("", str(test_task.id), "text/plain"),
                        "project_id": ("", str(test_project.id), "text/plain"),
                        "description": ("", "File with task and project", "text/plain"),
                    }

                    response = await client.post(
                        "/api/v1/files/upload",
                        files=files,
                        headers=authenticated_user["headers"],
                    )

                    # Закрываем временный файл
                    temp_file.close()

                assert response.status_code == 200
                result = response.json()
                assert result["file"]["task_id"] == str(test_task.id)
                assert result["file"]["project_id"] == str(test_project.id)

    async def test_upload_public_file(
        self, client: AsyncClient, authenticated_user, upload_file
    ) -> None:
        """Тест загрузки публичного файла"""
        filename, file_content, content_type = upload_file

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("app.core.config.get_settings") as mock_settings:
                mock_settings.return_value.UPLOAD_DIR = temp_dir

                # Создаем временный файл для загрузки
                with tempfile.NamedTemporaryFile(mode="w+b", delete=False) as temp_file:
                    temp_file.write(file_content.getbuffer())
                    temp_file.seek(0)

                    # Используем правильный формат multipart form
                    files = {
                        "file": (filename, temp_file, content_type),
                        "is_public": ("", "true", "text/plain"),
                    }

                    response = await client.post(
                        "/api/v1/files/upload",
                        files=files,
                        headers=authenticated_user["headers"],
                    )

                    # Закрываем временный файл
                    temp_file.close()

                assert response.status_code == 200
                result = response.json()
                assert result["file"]["is_public"] is True

    async def test_get_public_file_by_other_user(
        self, client: AsyncClient, other_user_auth, test_file
    ) -> None:
        """Тест получения публичного файла другим пользователем"""
        # Делаем файл публичным
        test_file.is_public = True
        await other_user_auth["db"].commit()

        response = await client.get(
            f"/api/v1/files/{test_file.id}",
            headers=other_user_auth["headers"],
        )

        assert response.status_code == 200
        result = response.json()
        assert result["id"] == str(test_file.id)
