"""
Модели для системы поиска
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ENUM, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class SearchableType(str):
    """Типы сущностей для поиска"""

    TASK = "task"
    PROJECT = "project"
    SPRINT = "sprint"
    COMMENT = "comment"

    # Допустимые значения
    _VALID_VALUES = {TASK, PROJECT, SPRINT, COMMENT}

    def __new__(cls, value):
        if value not in cls._VALID_VALUES:
            raise ValueError(f"Invalid searchable type: {value}")
        return super().__new__(cls, value)


# Создаем ENUM для SQLAlchemy
SearchableTypeEnum = ENUM(
    SearchableType.TASK,
    SearchableType.PROJECT,
    SearchableType.SPRINT,
    SearchableType.COMMENT,
    name="searchabletype",
    create_type=True,
)


class SearchIndex(BaseModel):
    """Индекс для полнотекстового поиска"""

    __tablename__ = "search_index"

    # Основные поля
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Заголовок для поиска",
    )

    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Содержимое для поиска",
    )

    # Полнотекстовый вектор для PostgreSQL
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        nullable=False,
        comment="Полнотекстовый вектор",
    )

    # Тип и ID сущности
    entity_type: Mapped[SearchableType] = mapped_column(
        SearchableTypeEnum,
        nullable=False,
        comment="Тип сущности",
    )

    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="ID сущности",
    )

    # Метаданные для фильтрации
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID проекта (если применимо)",
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID пользователя (владелец/исполнитель)",
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Публичный ли объект",
    )

    # Дополнительные метаданные в JSON
    search_metadata: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Дополнительные метаданные в JSON",
    )

    def __repr__(self) -> str:
        return f"<SearchIndex(title={self.title}, type={self.entity_type})>"


class SavedSearch(BaseModel):
    """Сохраненные поиски пользователей"""

    __tablename__ = "saved_searches"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Название сохраненного поиска",
    )

    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Поисковый запрос",
    )

    filters: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Фильтры в JSON",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="ID пользователя",
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Публичный ли поиск",
    )

    # Отношения
    user = relationship(
        "User",
        back_populates="saved_searches",
    )

    def __repr__(self) -> str:
        return f"<SavedSearch(name={self.name}, user_id={self.user_id})>"


# Триггеры для автоматического обновления search_vector
# Это будет добавлено через миграции Alembic
