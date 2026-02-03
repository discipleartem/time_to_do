"""
API роутеры для управления проектами
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.project import Project, ProjectMember, ProjectRole
from app.models.user import User
from app.schemas.project import (
    Project as ProjectSchema,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectUpdate,
)
from app.schemas.project import (
    ProjectMember as ProjectMemberSchema,
)

router = APIRouter()


@router.get("/", response_model=list[ProjectSchema])
async def get_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectSchema]:
    """
    Получение списка проектов текущего пользователя
    """
    # Получаем проекты, где пользователь является владельцем или участником
    result = await db.execute(
        select(Project)
        .join(ProjectMember, Project.id == ProjectMember.project_id, isouter=True)
        .where(
            (Project.owner_id == current_user.id)
            | (ProjectMember.user_id == current_user.id)
        )
        .distinct()
        .offset(skip)
        .limit(limit)
        .order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    return [ProjectSchema.model_validate(project) for project in projects]


@router.post("/", response_model=ProjectSchema, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectSchema:
    """
    Создание нового проекта
    """
    # TODO: Проверка лимитов проектов для free tier

    project = Project(
        name=project_data.name,
        description=project_data.description,
        owner_id=current_user.id,
        status=project_data.status,
        is_public=project_data.is_public,
        allow_external_sharing=project_data.allow_external_sharing,
        max_members=project_data.max_members,
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Добавляем владельца как участника с ролью owner
    owner_member = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role=ProjectRole.OWNER,
        is_active=True,
        invited_by_id=current_user.id,
    )

    db.add(owner_member)
    await db.commit()
    await db.refresh(project)

    return ProjectSchema.model_validate(project)


@router.get("/{project_id}", response_model=ProjectSchema)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectSchema:
    """
    Получение информации о проекте
    """
    # Преобразуем строку в UUID
    try:
        project_uuid = UUID(project_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат ID проекта",
        ) from err

    project = await get_project_with_access_check(project_uuid, current_user, db)

    return ProjectSchema.model_validate(project)


@router.put("/{project_id}", response_model=ProjectSchema)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectSchema:
    """
    Обновление проекта
    """
    # Преобразуем строку в UUID
    try:
        project_uuid = UUID(project_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат ID проекта",
        ) from err

    project = await get_project_with_access_check(project_uuid, current_user, db)

    # TODO: Добавить проверку прав на редактирование
    # Для базовой функциональности разрешаем редактирование владельцу и участникам

    # Обновляем данные
    update_data = project_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)

    return ProjectSchema.model_validate(project)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Удаление проекта
    """
    # Преобразуем строку в UUID
    try:
        project_uuid = UUID(project_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат ID проекта",
        ) from err

    project = await get_project_with_access_check(project_uuid, current_user, db)

    # Проверяем, что пользователь является владельцем
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только владелец может удалить проект",
        )

    await db.delete(project)
    await db.commit()

    return {"message": "Проект успешно удален"}


@router.get("/{project_id}/members", response_model=list[ProjectMemberSchema])
async def get_project_members(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectMemberSchema]:
    """
    Получение участников проекта
    """
    # Преобразуем строку в UUID
    try:
        project_uuid = UUID(project_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат ID проекта",
        ) from err

    await get_project_with_access_check(project_uuid, current_user, db)

    result = await db.execute(
        select(ProjectMember)
        .where(ProjectMember.project_id == str(project_uuid))
        .order_by(ProjectMember.created_at)
    )
    members = result.scalars().all()

    return [ProjectMemberSchema.model_validate(member) for member in members]


@router.post("/{project_id}/members", response_model=ProjectMemberSchema)
async def add_project_member(
    project_id: str,
    member_data: ProjectMemberCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectMemberSchema:
    """
    Добавление участника в проект
    """
    # Преобразуем строку в UUID
    try:
        project_uuid = UUID(project_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат ID проекта",
        ) from err

    await get_project_with_access_check(project_uuid, current_user, db)

    # Проверяем права на добавление участников
    member = await get_project_member(project_uuid, current_user.id, db)
    if not member or not member.can_manage_project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для добавления участников",
        )

    # Проверяем, не является ли пользователь уже участником
    member_uuid = (
        UUID(member_data.user_id)
        if isinstance(member_data.user_id, str)
        else member_data.user_id
    )
    existing_member = await get_project_member(project_uuid, member_uuid, db)
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь уже является участником проекта",
        )

    # TODO: Реализовать проверку лимита для free tier

    # Добавляем нового участника
    new_member = ProjectMember(
        project_id=project_uuid,
        user_id=member_uuid,
        role=member_data.role,
        is_active=True,
        invited_by_id=current_user.id,
    )

    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)

    return ProjectMemberSchema.model_validate(new_member)


@router.delete("/{project_id}/members/{user_id}")
async def remove_project_member(
    project_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Удаление участника из проекта
    """
    # Преобразуем строку в UUID
    try:
        project_uuid = UUID(project_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат ID проекта",
        ) from err

    project = await get_project_with_access_check(project_uuid, current_user, db)

    # Проверяем права на удаление участников
    member = await get_project_member(project_uuid, current_user.id, db)
    if not member or not member.can_manage_project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления участников",
        )

    # Нельзя удалить владельца
    user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
    if project.owner_id == user_uuid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить владельца проекта",
        )

    # Находим и удаляем участника
    target_member = await get_project_member(project_uuid, user_id, db)
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден",
        )

    await db.delete(target_member)
    await db.commit()

    return {"message": "Участник успешно удален из проекта"}


# Вспомогательные функции
async def get_project_with_access_check(
    project_id: UUID,
    user: User,
    db: AsyncSession,
) -> Project:
    """Получение проекта с проверкой доступа"""
    result = await db.execute(
        select(Project)
        .join(ProjectMember, Project.id == ProjectMember.project_id, isouter=True)
        .where(
            (Project.id == project_id)
            & (
                (Project.owner_id == user.id)
                | (ProjectMember.user_id == user.id)
                | (Project.is_public)
            )
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден или доступ запрещен",
        )

    return project


async def get_project_member(
    project_id: UUID,
    user_id: str | UUID,
    db: AsyncSession,
) -> ProjectMember | None:
    """Получение участника проекта"""
    # Конвертируем user_id в UUID если необходимо
    user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_uuid,
        )
    )
    return result.scalar_one_or_none()
