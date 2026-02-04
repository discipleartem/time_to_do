"""
Тесты для публичных ссылок (External Sharing)
"""

from uuid import uuid4

import pytest

from app.models.project import Project, ProjectMember, ProjectRole, ProjectStatus
from app.models.share_link import ShareLink, SharePermission
from app.models.user import User
from app.schemas.share_link import ShareableType, ShareLinkCreate
from app.services.share_link_service import ShareLinkService


@pytest.mark.asyncio
class TestShareLinkModel:
    """Тесты модели ShareLink"""

    async def test_share_link_creation(self, db_session):
        """Тест создания публичной ссылки."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        share_link = ShareLink(
            token="test_token_123",
            shareable_type=ShareableType.PROJECT,
            shareable_id=uuid4(),
            permission=SharePermission.VIEW,
            created_by=user.id,
        )
        db_session.add(share_link)
        await db_session.commit()
        await db_session.refresh(share_link)

        assert share_link.id is not None
        assert share_link.token == "test_token_123"
        assert share_link.shareable_type == ShareableType.PROJECT
        assert share_link.permission == SharePermission.VIEW
        assert share_link.current_views == 0
        assert share_link.is_active is True

    async def test_share_link_is_accessible(self, db_session):
        """Тест проверки доступности ссылки."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Активная ссылка
        active_link = ShareLink(
            token="active_token",
            shareable_type=ShareableType.PROJECT,
            shareable_id=uuid4(),
            permission=SharePermission.VIEW,
            created_by=user.id,
            is_active=True,
        )
        db_session.add(active_link)

        # Неактивная ссылка
        inactive_link = ShareLink(
            token="inactive_token",
            shareable_type=ShareableType.PROJECT,
            shareable_id=uuid4(),
            permission=SharePermission.VIEW,
            created_by=user.id,
            is_active=False,
        )
        db_session.add(inactive_link)
        await db_session.commit()

        assert active_link.is_accessible is True
        assert inactive_link.is_accessible is False

    async def test_share_link_increment_views(self, db_session):
        """Тест увеличения счетчика просмотров."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        share_link = ShareLink(
            token="views_token",
            shareable_type=ShareableType.PROJECT,
            shareable_id=uuid4(),
            permission=SharePermission.VIEW,
            created_by=user.id,
            current_views=5,
        )
        db_session.add(share_link)
        await db_session.commit()
        await db_session.refresh(share_link)

        assert share_link.current_views == 5

        share_link.increment_views()
        await db_session.commit()
        await db_session.refresh(share_link)

        assert share_link.current_views == 6

    async def test_share_link_to_dict(self, db_session):
        """Тест преобразования в словарь."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        share_link = ShareLink(
            token="dict_token",
            shareable_type=ShareableType.TASK,
            shareable_id=uuid4(),
            permission=SharePermission.COMMENT,
            title="Test Link",
            description="Test Description",
            created_by=user.id,
        )
        db_session.add(share_link)
        await db_session.commit()
        await db_session.refresh(share_link)

        link_dict = share_link.to_dict()

        assert link_dict["token"] == "dict_token"
        assert link_dict["shareable_type"] == ShareableType.TASK
        assert link_dict["permission"] == SharePermission.COMMENT
        assert link_dict["title"] == "Test Link"
        assert link_dict["description"] == "Test Description"
        assert link_dict["has_password"] is False
        assert link_dict["is_accessible"] is True
        assert "public_url" in link_dict


@pytest.mark.asyncio
class TestShareLinkService:
    """Тесты сервиса ShareLinkService"""

    async def test_create_share_link(self, db_session):
        """Тест создания публичной ссылки через сервис."""
        # Создаем пользователя
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Создаем проект
        project = Project(
            name="Test Project", description="Test Description", owner_id=user.id
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Добавляем пользователя в проект
        member = ProjectMember(
            project_id=project.id, user_id=user.id, role=ProjectRole.OWNER
        )
        db_session.add(member)
        await db_session.commit()

        # Создаем публичную ссылку
        service = ShareLinkService(db_session)
        share_data = ShareLinkCreate(
            shareable_type=ShareableType.PROJECT,
            shareable_id=project.id,
            permission=SharePermission.VIEW,
            title="Project Share",
            description="Shared project for testing",
        )

        share_link = await service.create_share_link(share_data, user.id)

        assert share_link.id is not None
        assert share_link.shareable_type == ShareableType.PROJECT
        assert share_link.shareable_id == project.id
        assert share_link.permission == SharePermission.VIEW
        assert share_link.title == "Project Share"
        assert share_link.created_by == user.id
        assert len(share_link.token) == 48  # token_urlsafe(36)

    async def test_get_user_share_links(self, db_session):
        """Тест получения публичных ссылок пользователя."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Создаем проект и добавляем пользователя в участники
        project = Project(
            name="Test Project",
            description="Test Description",
            owner_id=user.id,
            status=ProjectStatus.ACTIVE,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Добавляем пользователя в участники проекта
        project_member = ProjectMember(
            project_id=project.id, user_id=user.id, role=ProjectRole.OWNER
        )
        db_session.add(project_member)
        await db_session.commit()

        service = ShareLinkService(db_session)

        # Создаем несколько ссылок
        for i in range(3):
            share_data = ShareLinkCreate(
                shareable_type=ShareableType.PROJECT,
                shareable_id=project.id,
                permission=SharePermission.VIEW,
                title=f"Link {i}",
            )
            await service.create_share_link(share_data, user.id)

        # Получаем ссылки
        links = await service.get_user_share_links(user.id)
        assert len(links) == 3

        # Фильтруем по типу
        project_links = await service.get_user_share_links(
            user.id, ShareableType.PROJECT
        )
        assert len(project_links) == 3

    async def test_delete_share_link(self, db_session):
        """Тест удаления публичной ссылки."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Создаем проект и добавляем пользователя в участники
        project = Project(
            name="Test Project",
            description="Test Description",
            owner_id=user.id,
            status=ProjectStatus.ACTIVE,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Добавляем пользователя в участники проекта
        project_member = ProjectMember(
            project_id=project.id, user_id=user.id, role=ProjectRole.OWNER
        )
        db_session.add(project_member)
        await db_session.commit()

        service = ShareLinkService(db_session)

        # Создаем ссылку
        share_data = ShareLinkCreate(
            shareable_type=ShareableType.PROJECT,
            shareable_id=project.id,
            permission=SharePermission.VIEW,
        )
        share_link = await service.create_share_link(share_data, user.id)

        # Удаляем ссылку
        success = await service.delete_share_link(share_link.id, user.id)
        assert success is True

        # Проверяем, что ссылка удалена
        links = await service.get_user_share_links(user.id)
        assert len(links) == 0

    async def test_delete_share_link_wrong_user(self, db_session):
        """Тест удаления ссылки другим пользователем."""
        user1 = User(
            email="user1@example.com",
            username="user1",
            hashed_password="hashed_password",
        )
        user2 = User(
            email="user2@example.com",
            username="user2",
            hashed_password="hashed_password",
        )
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        # Создаем проект и добавляем user1 в участники
        project = Project(
            name="Test Project",
            description="Test Description",
            owner_id=user1.id,
            status=ProjectStatus.ACTIVE,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Добавляем user1 в участники проекта
        project_member = ProjectMember(
            project_id=project.id, user_id=user1.id, role=ProjectRole.OWNER
        )
        db_session.add(project_member)
        await db_session.commit()

        service = ShareLinkService(db_session)

        # Создаем ссылку от имени user1
        share_data = ShareLinkCreate(
            shareable_type=ShareableType.PROJECT,
            shareable_id=project.id,
            permission=SharePermission.VIEW,
        )
        share_link = await service.create_share_link(share_data, user1.id)

        # Пытаемся удалить от имени user2
        success = await service.delete_share_link(share_link.id, user2.id)
        assert success is False

    async def test_generate_unique_token(self, db_session):
        """Тест генерации уникальных токенов."""
        service = ShareLinkService(db_session)

        tokens = set()
        for _ in range(100):
            token = service.generate_token()
            assert token not in tokens  # Проверяем уникальность
            assert len(token) == 48  # token_urlsafe(36) дает 48 символов
            tokens.add(token)
