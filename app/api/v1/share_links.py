"""
API эндпоинты для публичных ссылок (External Sharing)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.share_link import (
    ShareableType,
    SharedContentResponse,
    ShareLinkAccess,
    ShareLinkCreate,
    ShareLinkResponse,
    ShareLinkStats,
    ShareLinkUpdate,
)
from app.services.share_link_service import ShareLinkService

router = APIRouter()


@router.post("/", response_model=ShareLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_share_link(
    share_data: ShareLinkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareLinkResponse:
    """Создать новую публичную ссылку."""
    try:
        service = ShareLinkService(db)
        share_link = await service.create_share_link(share_data, current_user.id)
        return ShareLinkResponse.model_validate(share_link.to_dict())
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.get("/", response_model=list[ShareLinkResponse])
async def get_user_share_links(
    shareable_type: ShareableType | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ShareLinkResponse]:
    """Получить публичные ссылки пользователя."""
    service = ShareLinkService(db)
    share_links = await service.get_user_share_links(
        current_user.id, shareable_type, limit, offset
    )
    return [ShareLinkResponse.model_validate(link.to_dict()) for link in share_links]


@router.get("/stats", response_model=ShareLinkStats)
async def get_share_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareLinkStats:
    """Получить статистику публичных ссылок."""
    service = ShareLinkService(db)
    stats = await service.get_share_stats(current_user.id)
    return stats


@router.get("/{link_id}", response_model=ShareLinkResponse)
async def get_share_link(
    link_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareLinkResponse:
    """Получить информацию о публичной ссылке."""
    service = ShareLinkService(db)
    share_links = await service.get_user_share_links(current_user.id)

    # Ищем ссылку по ID
    share_link = None
    for link in share_links:
        if link.id == link_id:
            share_link = link
            break

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ссылка не найдена"
        )

    return ShareLinkResponse.model_validate(share_link.to_dict())


@router.put("/{link_id}", response_model=ShareLinkResponse)
async def update_share_link(
    link_id: UUID,
    update_data: ShareLinkUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareLinkResponse:
    """Обновить публичную ссылку."""
    service = ShareLinkService(db)
    share_link = await service.update_share_link(link_id, current_user.id, update_data)

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ссылка не найдена"
        )

    return ShareLinkResponse.model_validate(share_link.to_dict())


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_share_link(
    link_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Удалить публичную ссылку."""
    service = ShareLinkService(db)
    success = await service.delete_share_link(link_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ссылка не найдена"
        )


@router.post("/access", response_model=SharedContentResponse)
async def access_shared_content(
    access_data: ShareLinkAccess,
    db: AsyncSession = Depends(get_db),
) -> SharedContentResponse:
    """Получить доступ к контенту по публичной ссылке."""
    service = ShareLinkService(db)
    result = await service.access_shared_content(
        access_data.token, access_data.password
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ссылка не найдена или доступ запрещен",
        )

    share_link, content = result

    return SharedContentResponse(
        share_link=ShareLinkResponse.model_validate(share_link.to_dict()),
        content=content,
        can_comment=share_link.permission == "comment",
        access_granted=True,
    )


@router.get("/public/{token}", response_model=SharedContentResponse)
async def get_public_content(
    token: str,
    password: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> SharedContentResponse:
    """Получить публичный контент по токену (без аутентификации)."""
    service = ShareLinkService(db)
    result = await service.access_shared_content(token, password)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ссылка не найдена или доступ запрещен",
        )

    share_link, content = result

    return SharedContentResponse(
        share_link=ShareLinkResponse.model_validate(share_link.to_dict()),
        content=content,
        can_comment=share_link.permission == "comment",
        access_granted=True,
    )
