"""
API роутеры для управления пользователями
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user, get_current_admin_user
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import User as UserSchema
from app.schemas.user import UserProfile, UserUpdate

router = APIRouter()


@router.get("/", response_model=list[UserSchema])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserSchema]:
    """
    Получение списка пользователей (только для админа)
    """
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    return [UserSchema.model_validate(user) for user in users]


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    """
    Получение профиля текущего пользователя с дополнительной информацией
    """
    # TODO: Добавить подсчет проектов и задач
    # Это будет реализовано после создания соответствующих сервисов

    return UserProfile(
        id=str(current_user.id),
        email=str(current_user.email),
        username=str(current_user.username) if current_user.username else None,
        full_name=str(current_user.full_name) if current_user.full_name else None,
        avatar_url=str(current_user.avatar_url) if current_user.avatar_url else None,
        is_active=bool(current_user.is_active),
        role=UserRole(current_user.role),
        created_at=current_user.created_at,  # type: ignore[assignment] # SQLAlchemy DateTime field limitation
        updated_at=current_user.updated_at,  # type: ignore[assignment] # SQLAlchemy DateTime field limitation
        is_verified=bool(current_user.is_verified),
        github_id=str(current_user.github_id) if current_user.github_id else None,
        github_username=(
            str(current_user.github_username) if current_user.github_username else None
        ),
        project_count=0,  # TODO: Реализовать подсчет
        task_count=0,  # TODO: Реализовать подсчет
        completed_task_count=0,  # TODO: Реализовать подсчет
    )


@router.put("/me", response_model=UserSchema)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserSchema:
    """
    Обновление данных текущего пользователя
    """
    # Проверяем, что email не занят другим пользователем
    if user_update.email and user_update.email != current_user.email:
        existing_user = await db.execute(
            select(User).where(
                User.email == user_update.email, User.id != current_user.id
            )
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email уже используется другим пользователем",
            )

    # Проверяем, что username не занят другим пользователем
    if user_update.username and user_update.username != current_user.username:
        existing_user = await db.execute(
            select(User).where(
                User.username == user_update.username, User.id != current_user.id
            )
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Имя пользователя уже используется",
            )

    # Обновляем данные пользователя
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)

    return UserSchema.model_validate(current_user)


@router.get("/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserSchema:
    """
    Получение информации о пользователе по ID
    """
    # TODO: Добавить проверку прав доступа
    # Конвертируем user_id в UUID
    from uuid import UUID

    user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    return UserSchema.model_validate(user)


@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserSchema:
    """
    Обновление пользователя (только для админа)
    """
    # Конвертируем user_id в UUID
    from uuid import UUID

    user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    # Проверяем уникальность email и username
    if user_update.email and user_update.email != user.email:
        existing_user = await db.execute(
            select(User).where(User.email == user_update.email)
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email уже используется",
            )

    if user_update.username and user_update.username != user.username:
        existing_user = await db.execute(
            select(User).where(User.username == user_update.username)
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Имя пользователя уже используется",
            )

    # Обновляем данные
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return UserSchema.model_validate(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Удаление пользователя (только для админа)
    """
    # Конвертируем user_id в UUID
    from uuid import UUID

    user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    # Нельзя удалить самого себя
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить самого себя",
        )

    await db.delete(user)
    await db.commit()

    return {"message": "Пользователь успешно удален"}
