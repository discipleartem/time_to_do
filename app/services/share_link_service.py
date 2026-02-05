"""
Сервис для работы с публичными ссылками
"""

import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.project import Project, ProjectMember
from app.models.share_link import ShareableType as ModelShareableType
from app.models.share_link import ShareLink
from app.models.share_link import SharePermission as ModelSharePermission
from app.models.task import Task
from app.schemas.share_link import ShareableType as SchemaShareableType
from app.schemas.share_link import (
    ShareLinkCreate,
    ShareLinkResponse,
    ShareLinkStats,
    ShareLinkUpdate,
)


class ShareLinkService:
    """Сервис для работы с публичными ссылками."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def generate_token(self) -> str:
        """Генерировать уникальный токен для ссылки."""
        return secrets.token_urlsafe(36)

    async def create_share_link(
        self, share_data: ShareLinkCreate, created_by: UUID
    ) -> ShareLink:
        """Создать новую публичную ссылку."""
        # Конвертируем schema enum в model enum
        model_shareable_type = ModelShareableType(share_data.shareable_type.value)
        model_permission = ModelSharePermission(share_data.permission.value)

        # Проверяем права доступа к объекту
        await self._check_access_permission(
            model_shareable_type, share_data.shareable_id, created_by
        )

        # Генерируем уникальный токен
        token = self.generate_token()
        while await self._token_exists(token):
            token = self.generate_token()

        # Создаем ссылку
        share_link = ShareLink(
            token=token,
            shareable_type=model_shareable_type,
            shareable_id=share_data.shareable_id,
            permission=model_permission,
            password=share_data.password,
            expires_at=share_data.expires_at,
            max_views=share_data.max_views,
            title=share_data.title,
            description=share_data.description,
            created_by=created_by,
        )

        self.db.add(share_link)
        await self.db.commit()
        await self.db.refresh(share_link)

        return share_link

    async def get_share_link_by_token(self, token: str) -> ShareLink | None:
        """Получить ссылку по токену."""
        query = select(ShareLink).where(ShareLink.token == token)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_share_links(
        self,
        user_id: UUID,
        shareable_type: SchemaShareableType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ShareLink]:
        """Получить ссылки созданные пользователем."""
        query = select(ShareLink).where(ShareLink.created_by == user_id)

        if shareable_type:
            model_shareable_type = ModelShareableType(shareable_type)
            query = query.where(ShareLink.shareable_type == model_shareable_type)

        query = query.order_by(desc(ShareLink.created_at)).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_share_link(
        self, link_id: UUID, user_id: UUID, update_data: ShareLinkUpdate
    ) -> ShareLink | None:
        """Обновить публичную ссылку."""
        query = select(ShareLink).where(
            ShareLink.id == link_id, ShareLink.created_by == user_id
        )
        result = await self.db.execute(query)
        share_link = result.scalar_one_or_none()

        if not share_link:
            return None

        # Обновляем поля
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(share_link, field, value)

        await self.db.commit()
        await self.db.refresh(share_link)

        return share_link

    async def delete_share_link(self, link_id: UUID, user_id: UUID) -> bool:
        """Удалить публичную ссылку."""
        query = select(ShareLink).where(
            ShareLink.id == link_id, ShareLink.created_by == user_id
        )
        result = await self.db.execute(query)
        share_link = result.scalar_one_or_none()

        if not share_link:
            return False

        await self.db.delete(share_link)
        await self.db.commit()

        return True

    async def access_shared_content(
        self, token: str, password: str | None = None
    ) -> tuple[ShareLink, dict] | None:
        """Получить доступ к контенту по публичной ссылке."""
        share_link = await self.get_share_link_by_token(token)

        if not share_link or not share_link.can_access(password):
            return None

        # Увеличиваем счетчик просмотров
        share_link.increment_views()
        await self.db.commit()

        # Получаем контент
        content = await self._get_shared_content(
            ModelShareableType(share_link.shareable_type),
            UUID(str(share_link.shareable_id)),
        )

        return share_link, content

    async def get_share_stats(self, user_id: UUID) -> ShareLinkStats:
        """Получить статистику ссылок пользователя."""
        # Общая статистика
        total_query = select(func.count(ShareLink.id)).where(
            ShareLink.created_by == user_id
        )
        total_result = await self.db.execute(total_query)
        total_links = total_result.scalar() or 0

        # Активные ссылки
        active_query = select(func.count(ShareLink.id)).where(
            ShareLink.created_by == user_id,
            ShareLink.is_active == True,
        )
        active_result = await self.db.execute(active_query)
        active_links = active_result.scalar() or 0

        # Истекшие ссылки
        expired_query = select(func.count(ShareLink.id)).where(
            ShareLink.created_by == user_id,
            ShareLink.expires_at < datetime.now(UTC),
        )
        expired_result = await self.db.execute(expired_query)
        expired_links = expired_result.scalar() or 0

        # Общее количество просмотров
        views_query = select(func.sum(ShareLink.current_views)).where(
            ShareLink.created_by == user_id
        )
        views_result = await self.db.execute(views_query)
        total_views = views_result.scalar() or 0

        # Самые просматриваемые ссылки
        popular_query = (
            select(ShareLink)
            .where(ShareLink.created_by == user_id)
            .order_by(desc(ShareLink.current_views))
            .limit(5)
        )
        popular_result = await self.db.execute(popular_query)
        most_viewed = popular_result.scalars().all()

        return ShareLinkStats(
            total_links=total_links,
            active_links=active_links,
            expired_links=expired_links,
            total_views=total_views,
            most_viewed=[
                ShareLinkResponse.model_validate(link.to_dict()) for link in most_viewed
            ],
        )

    async def _token_exists(self, token: str) -> bool:
        """Проверить, существует ли токен."""
        query = select(func.count(ShareLink.id)).where(ShareLink.token == token)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def _check_access_permission(
        self, shareable_type: ModelShareableType, shareable_id: UUID, user_id: UUID
    ) -> None:
        """Проверить права доступа к объекту."""
        if shareable_type == ModelShareableType.PROJECT:
            # Проверяем, что пользователь является участником проекта
            query = select(ProjectMember).where(
                ProjectMember.project_id == shareable_id,
                ProjectMember.user_id == user_id,
            )
            result = await self.db.execute(query)
            if not result.scalar_one_or_none():
                raise PermissionError("Нет доступа к проекту")

        elif shareable_type == ModelShareableType.TASK:
            # Проверяем, что пользователь имеет доступ к задаче
            query = (
                select(ProjectMember)
                .join(Project)
                .join(Task)
                .where(
                    Task.id == shareable_id,
                    ProjectMember.user_id == user_id,
                )
            )
            result = await self.db.execute(query)
            if not result.scalar_one_or_none():
                raise PermissionError("Нет доступа к задаче")

        # Для спринтов проверяем через проект
        elif shareable_type == ModelShareableType.SPRINT:
            # TODO: Добавить проверку для спринтов
            pass

    async def _get_shared_content(
        self, shareable_type: ModelShareableType, shareable_id: UUID
    ) -> dict:
        """Получить контент для шаринга."""
        if shareable_type == ModelShareableType.PROJECT:
            query = select(Project).where(Project.id == shareable_id)
            result = await self.db.execute(query)
            project = result.scalar_one_or_none()

            if project:
                return {
                    "type": "project",
                    "id": str(project.id),
                    "name": project.name,
                    "description": project.description,
                    "status": project.status,
                    "created_at": project.created_at.isoformat(),
                    "updated_at": project.updated_at.isoformat(),
                }

        elif shareable_type == ModelShareableType.TASK:
            task_query = select(Task).where(Task.id == shareable_id)
            task_result = await self.db.execute(task_query)
            task: Task | None = task_result.scalar_one_or_none()

            if task:
                return {
                    "type": "task",
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "priority": task.priority,
                    "story_points": task.story_points,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                }

        # TODO: Добавить получение контента для спринтов
        return {}
