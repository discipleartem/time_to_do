"""
Схемы для проектов и участников
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectBase(BaseModel):
    """Базовая схема проекта"""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    status: str = "ACTIVE"
    is_public: bool = False
    allow_external_sharing: bool = True
    max_members: str = "5"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Валидация имени проекта"""
        if not v or not v.strip():
            raise ValueError("Имя проекта не может быть пустым")
        if len(v.strip()) != len(v):
            raise ValueError(
                "Имя проекта не должно содержать только пробельные символы"
            )
        return v.strip()


class ProjectCreate(ProjectBase):
    """Создание проекта"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Новый проект",
                "description": "Описание проекта",
                "status": "active",
                "is_public": False,
                "allow_external_sharing": True,
                "max_members": "10",
            }
        }
    )


class ProjectUpdate(BaseModel):
    """Обновление проекта"""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    is_public: bool | None = None
    allow_external_sharing: bool | None = None
    max_members: str | None = None


class Project(ProjectBase):
    """Схема проекта для API"""

    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Конвертирует UUID в строку"""
        return str(v) if v is not None else None

    @field_validator("owner_id", mode="before")
    @classmethod
    def convert_owner_id_to_str(cls, v):
        """Конвертирует UUID в строку"""
        return str(v) if v is not None else None


class ProjectWithDetails(Project):
    """Проект с дополнительной информацией"""

    member_count: int = 0
    task_count: int = 0
    completed_task_count: int = 0
    is_at_member_limit: bool = False
    owner: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectMemberBase(BaseModel):
    """Базовая схема участника проекта"""

    role: str = "member"
    is_active: bool = True


class ProjectMemberCreate(ProjectMemberBase):
    """Добавление участника в проект"""

    user_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"user_id": "uuid-user-id", "role": "member", "is_active": True}
        }
    )


class ProjectMemberUpdate(BaseModel):
    """Обновление участника проекта"""

    role: str | None = None
    is_active: bool | None = None


class ProjectMember(ProjectMemberBase):
    """Схема участника проекта для API"""

    id: str
    project_id: str
    user_id: str
    invited_by_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Конвертирует UUID в строку"""
        return str(v) if v is not None else None

    @field_validator("project_id", mode="before")
    @classmethod
    def convert_project_id_to_str(cls, v):
        """Конвертирует UUID в строку"""
        return str(v) if v is not None else None

    @field_validator("user_id", mode="before")
    @classmethod
    def convert_user_id_to_str(cls, v):
        """Конвертирует UUID в строку"""
        return str(v) if v is not None else None

    @field_validator("invited_by_id", mode="before")
    @classmethod
    def convert_invited_by_id_to_str(cls, v):
        """Конвертирует UUID в строку"""
        return str(v) if v is not None else None


class ProjectMemberWithDetails(ProjectMember):
    """Участник проекта с деталями пользователя"""

    user: dict[str, Any] | None = None
    invited_by: dict[str, Any] | None = None
    can_manage_project: bool = False
    can_edit_tasks: bool = False
    can_view_project: bool = True

    model_config = ConfigDict(from_attributes=True)


class ProjectInvite(BaseModel):
    """Приглашение в проект"""

    email: str = Field(..., min_length=1)
    role: str = "member"
    message: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "role": "member",
                "message": "Присоединяйтесь к нашему проекту!",
            }
        }
    )


class PublicProject(BaseModel):
    """Публичная информация о проекте"""

    id: str
    name: str
    description: str | None = None
    created_at: datetime
    owner: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Конвертирует UUID в строку"""
        return str(v) if v is not None else None


class ProjectStats(BaseModel):
    """Статистика проекта"""

    total_tasks: int = 0
    completed_tasks: int = 0
    todo_tasks: int = 0
    in_progress_tasks: int = 0
    done_tasks: int = 0
    blocked_tasks: int = 0
    total_members: int = 0
    active_members: int = 0

    model_config = ConfigDict(from_attributes=True)
