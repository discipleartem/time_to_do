"""
Модель пользователя
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class UserRole(str):
    """Роли пользователя в системе"""

    ADMIN = "ADMIN"
    USER = "USER"


# Создаем ENUM для SQLAlchemy
UserRoleEnum = ENUM(
    UserRole.ADMIN,
    UserRole.USER,
    name="userrole",
    create_type=True,  # Создаем тип автоматически
)


class User(BaseModel):
    """Модель пользователя"""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Email пользователя",
    )

    username: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
        comment="Имя пользователя",
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Полное имя пользователя",
    )

    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Хешированный пароль",
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL аватара",
    )

    github_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
        comment="GitHub ID пользователя",
    )

    github_username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="GitHub имя пользователя",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Активен ли пользователь",
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Подтвержден ли email",
    )

    role: Mapped[UserRole] = mapped_column(
        UserRoleEnum,
        default=UserRole.USER,
        nullable=False,
        comment="Роль пользователя",
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Последний вход в систему",
    )

    # Отношения
    owned_projects = relationship(
        "Project",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    project_memberships = relationship(
        "ProjectMember",
        foreign_keys="ProjectMember.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    assigned_tasks = relationship(
        "Task",
        foreign_keys="Task.assignee_id",
        back_populates="assignee",
    )

    created_tasks = relationship(
        "Task",
        foreign_keys="Task.creator_id",
        back_populates="creator",
    )

    comments = relationship(
        "Comment",
        back_populates="author",
        cascade="all, delete-orphan",
    )

    # Properties с правильной типизацией для mypy
    @property
    def id_str(self) -> str:
        """ID как строка для схем"""
        return str(self.id)

    @property
    def email_str(self) -> str:
        """Email как строка для схем"""
        return self.email

    @property
    def username_str(self) -> str | None:
        """Username как строка для схем"""
        return self.username

    @property
    def full_name_str(self) -> str | None:
        """Full name как строка для схем"""
        return self.full_name

    @property
    def avatar_url_str(self) -> str | None:
        """Avatar URL как строка для схем"""
        return self.avatar_url

    @property
    def is_active_bool(self) -> bool:
        """Is active как bool для схем"""
        return self.is_active

    @property
    def is_verified_bool(self) -> bool:
        """Is verified как bool для схем"""
        return self.is_verified

    @property
    def github_id_str(self) -> str | None:
        """GitHub ID как строка для схем"""
        return self.github_id

    @property
    def github_username_str(self) -> str | None:
        """GitHub username как строка для схем"""
        return self.github_username

    time_entries = relationship(
        "TimeEntry",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Notification.created_at)",
    )

    def __repr__(self) -> str:
        return f"<User(email={self.email}, username={self.username})>"

    @property
    def is_admin(self) -> bool:
        """Является ли пользователь администратором"""
        return self.role == UserRole.ADMIN

    @property
    def display_name(self) -> str:
        """Отображаемое имя пользователя"""
        if self.full_name:
            return self.full_name
        elif self.username:
            return self.username
        else:
            return self.email
