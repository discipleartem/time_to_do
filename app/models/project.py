"""
Модели проектов и участников
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ProjectStatus(str):
    """Статусы проекта"""

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"
    ON_HOLD = "ON_HOLD"


class ProjectRole(str):
    """Роли в проекте"""

    OWNER = "OWNER"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


# Создаем ENUM для SQLAlchemy
ProjectStatusEnum = ENUM(
    ProjectStatus.ACTIVE,
    ProjectStatus.COMPLETED,
    ProjectStatus.ARCHIVED,
    ProjectStatus.ON_HOLD,
    name="projectstatus",
    create_type=True,  # Создаем тип автоматически
)

ProjectRoleEnum = ENUM(
    ProjectRole.OWNER,
    ProjectRole.MEMBER,
    ProjectRole.VIEWER,
    name="projectrole",
    create_type=True,  # Создаем тип автоматически
)


class Project(BaseModel):
    """Модель проекта"""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Название проекта",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Описание проекта",
    )

    status: Mapped[ProjectStatus] = mapped_column(
        ProjectStatusEnum,
        default=ProjectStatus.ACTIVE,
        nullable=False,
        comment="Статус проекта",
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Публичный ли проект",
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="ID владельца проекта",
    )

    allow_external_sharing: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Разрешить внешний доступ",
    )

    max_members: Mapped[str] = mapped_column(
        String(10),
        default="5",
        nullable=False,
        comment="Максимальное количество участников",
    )

    # Отношения
    owner = relationship(
        "User",
        back_populates="owned_projects",
    )

    members = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    tasks = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    sprints = relationship(
        "Sprint",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    notifications = relationship(
        "Notification",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project(name={self.name}, status={self.status})>"

    @property
    def member_count(self) -> int:
        """Количество участников в проекте"""
        return len([m for m in self.members if m.role != ProjectRole.VIEWER])

    @property
    def is_at_member_limit(self) -> bool:
        """Достигнут ли лимит участников"""
        try:
            max_limit = int(self.max_members)
            return self.member_count >= max_limit
        except (ValueError, TypeError):
            return False


class ProjectMember(BaseModel):
    """Модель участника проекта"""

    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False,
        comment="ID проекта",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="ID пользователя",
    )

    role: Mapped[ProjectRole] = mapped_column(
        ProjectRoleEnum,
        default=ProjectRole.MEMBER,
        nullable=False,
        comment="Роль в проекте",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Активен ли участник",
    )

    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="Кто пригласил участника",
    )

    # Отношения
    project = relationship(
        "Project",
        back_populates="members",
    )

    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="project_memberships",
    )

    invited_by = relationship(
        "User",
        foreign_keys="ProjectMember.invited_by_id",
    )

    # Properties с правильной типизацией для mypy
    @property
    def status_str(self) -> str:
        """Status как строка для схем"""
        return "active" if self.is_active else "inactive"

    @property
    def role_str(self) -> str:
        """Role как строка для схем"""
        return str(self.role) if self.role else "member"

    @property
    def can_manage_project(self) -> bool:
        """Может ли управлять проектом"""
        return self.role == ProjectRole.OWNER

    @property
    def can_edit_project(self) -> bool:
        """Может ли редактировать проект"""
        return self.role in [ProjectRole.OWNER, ProjectRole.MEMBER]

    @property
    def can_view_project(self) -> bool:
        """Может ли просматривать проект"""
        return self.role in [ProjectRole.OWNER, ProjectRole.MEMBER, ProjectRole.VIEWER]

    @property
    def can_edit_tasks(self) -> bool:
        """Может ли редактировать задачи"""
        return self.role in [ProjectRole.OWNER, ProjectRole.MEMBER]

    def __repr__(self) -> str:
        return f"<ProjectMember(user={self.user_id}, project={self.project_id}, role={self.role})>"
