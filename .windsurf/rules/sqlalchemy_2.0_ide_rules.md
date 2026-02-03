# Правила SQLAlchemy 2.0 для Агентных IDE

## Источник
Эти правила основаны на официальной документации SQLAlchemy 2.0:
https://docs.sqlalchemy.org/en/20/

---

## 1. ОСНОВЫ И АРХИТЕКТУРА

### 1.1 Компоненты SQLAlchemy
- **Core**: Фундаментальная архитектура для работы с базами данных
  - Engine - управление подключениями к БД
  - Connection - высокоуровневые операции с БД
  - SQL Expression Language - программное построение SQL
- **ORM**: Объектно-реляционный маппинг поверх Core
  - Session - управление транзакциями и состоянием объектов
  - Mapper - связывает классы Python с таблицами БД
  - Declarative - декларативный стиль маппинга

### 1.2 Версионность
- Текущая стабильная версия: 2.0.x
- Используйте современный стиль работы (2.0 style), а не устаревший 1.x
- Проверяйте версию: `import sqlalchemy; sqlalchemy.__version__`

---

## 2. DECLARATIVE MAPPING (Предпочтительный стиль)

### 2.1 Базовая настройка
```python
from __future__ import annotations
from typing import List, Optional
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass
```

### 2.2 Определение моделей с типизацией (PEP 484)

**ВАЖНО**: Всегда используйте аннотации `Mapped[]` для ORM-атрибутов

```python
class User(Base):
    __tablename__ = "user"

    # Обязательные поля
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str] = mapped_column(String(100), unique=True)

    # Опциональные поля
    age: Mapped[Optional[int]]

    # Отношения
    addresses: Mapped[List["Address"]] = relationship(back_populates="user")


class Address(Base):
    __tablename__ = "address"

    id: Mapped[int] = mapped_column(primary_key=True)
    email_address: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))

    user: Mapped["User"] = relationship(back_populates="addresses")
```

### 2.3 Правила типизации
- **Обязательные поля**: `Mapped[тип]`
- **Опциональные поля**: `Mapped[Optional[тип]]` или `Mapped[тип | None]`
- **Коллекции**: `Mapped[List["ClassName"]]` или `Mapped[Set["ClassName"]]`
- **Один к одному**: `Mapped["ClassName"]` или `Mapped[Optional["ClassName"]]`

---

## 3. RELATIONSHIPS (Связи между моделями)

### 3.1 One-to-Many (Один ко многим)
```python
class Parent(Base):
    __tablename__ = "parent_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    children: Mapped[List["Child"]] = relationship(back_populates="parent")


class Child(Base):
    __tablename__ = "child_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parent_table.id"))
    parent: Mapped["Parent"] = relationship(back_populates="children")
```

### 3.2 Many-to-One (Многие к одному)
```python
class Parent(Base):
    __tablename__ = "parent_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child_table.id"))
    child: Mapped["Child"] = relationship(back_populates="parents")


class Child(Base):
    __tablename__ = "child_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    parents: Mapped[List["Parent"]] = relationship(back_populates="child")
```

### 3.3 Many-to-Many (Многие ко многим)
```python
from sqlalchemy import Table, Column, Integer, ForeignKey

# Ассоциативная таблица
association_table = Table(
    "association",
    Base.metadata,
    Column("left_id", ForeignKey("left.id"), primary_key=True),
    Column("right_id", ForeignKey("right.id"), primary_key=True),
)


class Left(Base):
    __tablename__ = "left"

    id: Mapped[int] = mapped_column(primary_key=True)
    rights: Mapped[List["Right"]] = relationship(
        secondary=association_table,
        back_populates="lefts"
    )


class Right(Base):
    __tablename__ = "right"

    id: Mapped[int] = mapped_column(primary_key=True)
    lefts: Mapped[List["Left"]] = relationship(
        secondary=association_table,
        back_populates="rights"
    )
```

### 3.4 Правила для relationship()
- **ВСЕГДА используйте `back_populates`** вместо устаревшего `backref`
- Указывайте имя класса в кавычках для отложенной оценки: `"ClassName"`
- ForeignKey всегда ссылается на имя таблицы, а не класса: `ForeignKey("table_name.id")`

---

## 4. ENGINE И CONNECTION

### 4.1 Создание Engine
```python
from sqlalchemy import create_engine

# Синхронный engine
engine = create_engine(
    "postgresql+psycopg2://user:password@localhost/dbname",
    echo=True,  # Логирование SQL (для отладки)
    pool_size=5,
    max_overflow=10
)

# Асинхронный engine
from sqlalchemy.ext.asyncio import create_async_engine

async_engine = create_async_engine(
    "postgresql+asyncpg://user:password@localhost/dbname",
    echo=True
)
```

### 4.2 URL форматы для популярных БД
```python
# PostgreSQL
"postgresql+psycopg2://user:password@localhost/dbname"
"postgresql+asyncpg://user:password@localhost/dbname"  # async

# MySQL/MariaDB
"mysql+pymysql://user:password@localhost/dbname"

# SQLite
"sqlite:///path/to/database.db"
"sqlite:///:memory:"  # в памяти

# SQL Server
"mssql+pyodbc://user:password@localhost/dbname?driver=ODBC+Driver+17+for+SQL+Server"

# Oracle
"oracle+cx_oracle://user:password@localhost:1521/dbname"
```

### 4.3 Создание таблиц
```python
# Создать все таблицы
Base.metadata.create_all(engine)

# Удалить все таблицы
Base.metadata.drop_all(engine)
```

---

## 5. SESSION (Управление сессиями)

### 5.1 Создание Session

**РЕКОМЕНДУЕТСЯ**: Используйте context manager для автоматического управления

```python
from sqlalchemy.orm import Session, sessionmaker

# Вариант 1: Прямое создание (рекомендуется для простых случаев)
with Session(engine) as session:
    # Работа с сессией
    session.add(user)
    session.commit()
# Сессия автоматически закрывается

# Вариант 2: SessionMaker (для переиспользования конфигурации)
SessionLocal = sessionmaker(bind=engine)

with SessionLocal() as session:
    session.add(user)
    session.commit()

# Вариант 3: С автоматическим commit
with Session.begin(engine) as session:
    session.add(user)
# Автоматический commit при выходе
```

### 5.2 Правила работы с Session

**КРИТИЧЕСКИ ВАЖНО**:
- **Одна сессия на запрос/транзакцию** (особенно в веб-приложениях)
- **Короткие транзакции** - лучшая практика
- **Session per thread** для многопоточности
- **AsyncSession per task** для asyncio
- Используйте context manager для автоматического закрытия

### 5.3 Паттерн для веб-приложений (FastAPI пример)
```python
from typing import Generator
from sqlalchemy.orm import Session

def get_db() -> Generator[Session, None, None]:
    """Dependency для получения DB сессии"""
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
```

### 5.4 Состояния объектов в Session
- **Transient**: Новый объект, не в сессии, нет ID
- **Pending**: Добавлен в сессию (add()), но не сохранен в БД
- **Persistent**: В сессии и в БД
- **Deleted**: Помечен на удаление, но транзакция не завершена
- **Detached**: Был в сессии, но больше нет

---

## 6. CRUD ОПЕРАЦИИ (2.0 Style)

### 6.1 CREATE (Создание)
```python
from sqlalchemy.orm import Session

with Session(engine) as session:
    # Один объект
    new_user = User(name="John", email="john@example.com")
    session.add(new_user)

    # Несколько объектов
    users = [
        User(name="Alice", email="alice@example.com"),
        User(name="Bob", email="bob@example.com"),
    ]
    session.add_all(users)

    session.commit()

    # После commit объект имеет ID
    print(new_user.id)
```

### 6.2 READ (Чтение) - используйте select()

**ВАЖНО**: В SQLAlchemy 2.0 используйте `select()`, а НЕ `Query`

```python
from sqlalchemy import select

with Session(engine) as session:
    # Один объект по ID
    stmt = select(User).where(User.id == 1)
    user = session.scalar(stmt)

    # Первый объект (или None)
    stmt = select(User).where(User.name == "John")
    user = session.scalars(stmt).first()

    # Все объекты
    stmt = select(User)
    users = session.scalars(stmt).all()

    # С условиями
    stmt = select(User).where(User.age > 18).order_by(User.name)
    adult_users = session.scalars(stmt).all()

    # С join
    stmt = (
        select(User)
        .join(User.addresses)
        .where(Address.email_address.like("%@example.com"))
    )
    users_with_example_email = session.scalars(stmt).all()
```

### 6.3 UPDATE (Обновление)
```python
with Session(engine) as session:
    # Способ 1: Загрузить и изменить
    user = session.scalar(select(User).where(User.id == 1))
    if user:
        user.email = "newemail@example.com"
        session.commit()

    # Способ 2: Bulk update (без загрузки объектов)
    from sqlalchemy import update

    stmt = update(User).where(User.age < 18).values(status="minor")
    session.execute(stmt)
    session.commit()
```

### 6.4 DELETE (Удаление)
```python
with Session(engine) as session:
    # Способ 1: Загрузить и удалить
    user = session.scalar(select(User).where(User.id == 1))
    if user:
        session.delete(user)
        session.commit()

    # Способ 2: Bulk delete
    from sqlalchemy import delete

    stmt = delete(User).where(User.age < 0)
    session.execute(stmt)
    session.commit()
```

---

## 7. QUERYING (Запросы)

### 7.1 Основные операции select()
```python
from sqlalchemy import select, and_, or_, not_

# WHERE условия
stmt = select(User).where(User.age > 18)
stmt = select(User).where(User.name == "John", User.age > 18)  # AND
stmt = select(User).where(and_(User.age > 18, User.age < 65))
stmt = select(User).where(or_(User.name == "John", User.name == "Jane"))

# IN, NOT IN
stmt = select(User).where(User.id.in_([1, 2, 3]))
stmt = select(User).where(User.name.not_in(["Admin", "System"]))

# LIKE, ILIKE (case-insensitive)
stmt = select(User).where(User.email.like("%@gmail.com"))
stmt = select(User).where(User.name.ilike("%john%"))

# IS NULL, IS NOT NULL
stmt = select(User).where(User.age.is_(None))
stmt = select(User).where(User.age.is_not(None))

# ORDER BY
stmt = select(User).order_by(User.name)
stmt = select(User).order_by(User.age.desc(), User.name.asc())

# LIMIT, OFFSET
stmt = select(User).limit(10).offset(20)

# DISTINCT
stmt = select(User.name).distinct()
```

### 7.2 Joins
```python
# Inner join (по relationship)
stmt = select(User).join(User.addresses)

# Left outer join
stmt = select(User).outerjoin(User.addresses)

# Явный join с ON
from sqlalchemy import join
stmt = select(User).select_from(
    join(User, Address, User.id == Address.user_id)
)

# Множественные joins
stmt = (
    select(User)
    .join(User.addresses)
    .join(Address.city)
    .where(City.name == "New York")
)
```

### 7.3 Агрегация
```python
from sqlalchemy import func

# COUNT
stmt = select(func.count(User.id))
count = session.scalar(stmt)

# GROUP BY
stmt = select(User.age, func.count(User.id)).group_by(User.age)
results = session.execute(stmt).all()

# HAVING
stmt = (
    select(User.age, func.count(User.id))
    .group_by(User.age)
    .having(func.count(User.id) > 5)
)

# AVG, SUM, MIN, MAX
stmt = select(func.avg(User.age))
stmt = select(func.sum(Order.amount))
stmt = select(func.min(Product.price), func.max(Product.price))
```

### 7.4 Eager Loading (Загрузка связанных объектов)
```python
from sqlalchemy.orm import joinedload, selectinload, subqueryload

# joinedload - один запрос с JOIN
stmt = select(User).options(joinedload(User.addresses))

# selectinload - два запроса с IN
stmt = select(User).options(selectinload(User.addresses))

# Вложенные загрузки
stmt = select(User).options(
    selectinload(User.orders).selectinload(Order.items)
)
```

---

## 8. ASYNC SUPPORT (Асинхронность)

### 8.1 Настройка AsyncEngine и AsyncSession
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Создание async engine
async_engine = create_async_engine(
    "postgresql+asyncpg://user:password@localhost/dbname",
    echo=True
)

# Создание async session factory
async_session = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

### 8.2 Работа с AsyncSession
```python
from sqlalchemy import select

async def get_users():
    async with async_session() as session:
        stmt = select(User).where(User.age > 18)
        result = await session.execute(stmt)
        users = result.scalars().all()
        return users


async def create_user(name: str, email: str):
    async with async_session() as session:
        async with session.begin():
            user = User(name=name, email=email)
            session.add(user)
        # Автоматический commit при выходе из session.begin()
        return user
```

### 8.3 Async операции
```python
async def async_operations():
    async with async_session() as session:
        # SELECT
        result = await session.execute(select(User))
        users = result.scalars().all()

        # INSERT
        new_user = User(name="Alice")
        session.add(new_user)
        await session.commit()

        # UPDATE
        user = await session.get(User, 1)
        user.email = "new@example.com"
        await session.commit()

        # DELETE
        await session.delete(user)
        await session.commit()

        # Refresh
        await session.refresh(user)
```

---

## 9. MIXINS И ПОВТОРНОЕ ИСПОЛЬЗОВАНИЕ

### 9.1 Общие колонки через Mixin
```python
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import declared_attr, Mapped, mapped_column

class TimestampMixin:
    """Добавляет created_at и updated_at"""
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )


class SoftDeleteMixin:
    """Добавляет soft delete функциональность"""
    deleted_at: Mapped[Optional[datetime]]

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class User(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
```

### 9.2 Динамические tablename через Mixin
```python
class TableNameMixin:
    @declared_attr.directive
    def __tablename__(cls) -> str:
        # Автоматически генерирует имя таблицы из имени класса
        return cls.__name__.lower()


class User(TableNameMixin, Base):
    # __tablename__ будет "user"
    id: Mapped[int] = mapped_column(primary_key=True)
```

---

## 10. ТРАНЗАКЦИИ И SAVEPOINTS

### 10.1 Управление транзакциями
```python
# Автоматический commit через context manager
with Session.begin(engine) as session:
    session.add(user)
    # Автоматический commit при выходе

# Ручное управление
with Session(engine) as session:
    try:
        session.add(user)
        session.commit()
    except Exception:
        session.rollback()
        raise
```

### 10.2 Savepoints (вложенные транзакции)
```python
with Session(engine) as session:
    session.add(user1)

    try:
        with session.begin_nested():  # SAVEPOINT
            session.add(user2)
            # Если здесь ошибка, откатится только user2
    except Exception:
        pass  # user1 все еще в транзакции

    session.commit()  # Сохраняется user1
```

---

## 11. BEST PRACTICES (Лучшие практики)

### 11.1 Структура проекта
```
project/
├── models/
│   ├── __init__.py
│   ├── base.py          # Base class
│   ├── user.py          # User model
│   └── order.py         # Order model
├── database.py          # Engine и session setup
├── crud/
│   ├── user.py          # CRUD для User
│   └── order.py         # CRUD для Order
└── schemas/
    ├── user.py          # Pydantic schemas
    └── order.py
```

### 11.2 database.py пример
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

DATABASE_URL = "postgresql://user:password@localhost/dbname"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency для получения DB сессии"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 11.3 CRUD паттерн
```python
# crud/user.py
from sqlalchemy import select
from sqlalchemy.orm import Session
from models.user import User

def get_user(db: Session, user_id: int) -> User | None:
    return db.scalar(select(User).where(User.id == user_id))


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    stmt = select(User).offset(skip).limit(limit)
    return db.scalars(stmt).all()


def create_user(db: Session, name: str, email: str) -> User:
    user = User(name=name, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, **kwargs) -> User | None:
    user = get_user(db, user_id)
    if user:
        for key, value in kwargs.items():
            setattr(user, key, value)
        db.commit()
        db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = get_user(db, user_id)
    if user:
        db.delete(user)
        db.commit()
        return True
    return False
```

### 11.4 Общие рекомендации

**DO (Делайте)**:
- ✅ Используйте `Mapped[]` аннотации для всех ORM атрибутов
- ✅ Используйте `select()` вместо устаревшего `Query`
- ✅ Используйте `back_populates` вместо `backref`
- ✅ Используйте context managers для Session
- ✅ Короткие транзакции
- ✅ Используйте connection pooling
- ✅ Добавляйте индексы на часто используемые колонки
- ✅ Используйте eager loading для избежания N+1 проблем
- ✅ Валидируйте данные перед сохранением (Pydantic)

**DON'T (Не делайте)**:
- ❌ НЕ используйте устаревший `Query` API
- ❌ НЕ используйте `backref` (используйте `back_populates`)
- ❌ НЕ держите Session открытой долго
- ❌ НЕ используйте один Session в нескольких потоках
- ❌ НЕ забывайте про индексы
- ❌ НЕ используйте строковые SQL запросы без параметризации
- ❌ НЕ игнорируйте ошибки транзакций

---

## 12. МИГРАЦИИ С ALEMBIC

### 12.1 Установка и инициализация
```bash
pip install alembic
alembic init alembic
```

### 12.2 Настройка alembic.ini и env.py
```python
# alembic/env.py
from models.base import Base
target_metadata = Base.metadata
```

### 12.3 Создание и применение миграций
```bash
# Создать автоматическую миграцию
alembic revision --autogenerate -m "Add user table"

# Применить миграции
alembic upgrade head

# Откатить миграцию
alembic downgrade -1

# История миграций
alembic history
```

---

## 13. ТИПИЧНЫЕ ОШИБКИ И РЕШЕНИЯ

### 13.1 "DetachedInstanceError"
```python
# ПРОБЛЕМА: Доступ к lazy-loaded атрибуту после закрытия сессии
with Session(engine) as session:
    user = session.scalar(select(User).where(User.id == 1))
# session закрыта
print(user.addresses)  # ❌ DetachedInstanceError

# РЕШЕНИЕ 1: Eager loading
with Session(engine) as session:
    stmt = select(User).options(selectinload(User.addresses))
    user = session.scalar(stmt.where(User.id == 1))
print(user.addresses)  # ✅ OK

# РЕШЕНИЕ 2: expire_on_commit=False
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
```

### 13.2 "N+1 Query Problem"
```python
# ПРОБЛЕМА
users = session.scalars(select(User)).all()
for user in users:
    print(user.addresses)  # ❌ Отдельный запрос для каждого user

# РЕШЕНИЕ: Eager loading
stmt = select(User).options(selectinload(User.addresses))
users = session.scalars(stmt).all()
for user in users:
    print(user.addresses)  # ✅ Один дополнительный запрос
```

### 13.3 "Duplicate primary key"
```python
# ПРОБЛЕМА
user1 = User(id=1, name="John")
session.add(user1)
session.commit()

user2 = User(id=1, name="Jane")
session.add(user2)
session.commit()  # ❌ IntegrityError

# РЕШЕНИЕ: Используйте merge
user2 = User(id=1, name="Jane")
merged_user = session.merge(user2)
session.commit()  # ✅ UPDATE вместо INSERT
```

---

## 14. ПРОИЗВОДИТЕЛЬНОСТЬ

### 14.1 Connection Pooling
```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://...",
    poolclass=QueuePool,
    pool_size=10,          # Постоянные соединения
    max_overflow=20,       # Дополнительные при необходимости
    pool_pre_ping=True,    # Проверка живых соединений
    pool_recycle=3600,     # Пересоздание соединений каждый час
)
```

### 14.2 Bulk операции
```python
# Bulk insert (быстрее чем add_all)
from sqlalchemy import insert

stmt = insert(User).values([
    {"name": "User1", "email": "user1@example.com"},
    {"name": "User2", "email": "user2@example.com"},
    # ... тысячи записей
])
session.execute(stmt)
session.commit()

# Bulk update
from sqlalchemy import update

stmt = update(User).where(User.age < 18).values(status="minor")
session.execute(stmt)
session.commit()
```

### 14.3 Индексы
```python
from sqlalchemy import Index

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(index=True)

    # Композитный индекс
    __table_args__ = (
        Index("idx_name_email", "name", "email"),
    )
```

---

## 15. СПЕЦИАЛЬНЫЕ СЛУЧАИ

### 15.1 UUID как Primary Key
```python
from sqlalchemy.dialects.postgresql import UUID
import uuid

class User(Base):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str]
```

### 15.2 JSON колонки
```python
from sqlalchemy.dialects.postgresql import JSON

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    metadata: Mapped[dict] = mapped_column(JSON)

# Использование
user = User(metadata={"age": 25, "city": "NYC"})
```

### 15.3 Enum типы
```python
import enum
from sqlalchemy import Enum as SQLEnum

class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole))
```

---

## 16. ТЕСТИРОВАНИЕ

### 16.1 In-memory SQLite для тестов
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

@pytest.fixture
def db_session():
    # Создаем in-memory БД для каждого теста
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    Base.metadata.drop_all(engine)


def test_create_user(db_session):
    user = User(name="Test", email="test@example.com")
    db_session.add(user)
    db_session.commit()

    assert user.id is not None
    assert user.name == "Test"
```

---

## 17. БЕЗОПАСНОСТЬ

### 17.1 SQL Injection защита
```python
# ❌ НИКОГДА не делайте так
user_input = "1 OR 1=1"
stmt = f"SELECT * FROM users WHERE id = {user_input}"

# ✅ ВСЕГДА используйте параметризованные запросы
from sqlalchemy import text

user_id = request.args.get("id")
stmt = text("SELECT * FROM users WHERE id = :id")
result = session.execute(stmt, {"id": user_id})

# ✅ Еще лучше - используйте ORM
stmt = select(User).where(User.id == user_id)
user = session.scalar(stmt)
```

### 17.2 Валидация с Pydantic
```python
from pydantic import BaseModel, EmailStr, validator

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    age: int

    @validator("age")
    def validate_age(cls, v):
        if v < 0 or v > 150:
            raise ValueError("Invalid age")
        return v


def create_user(db: Session, user_data: UserCreate) -> User:
    # Данные уже валидированы Pydantic
    user = User(**user_data.dict())
    db.add(user)
    db.commit()
    return user
```

---

## 18. БЫСТРАЯ СПРАВКА

### Импорты
```python
# Основные
from sqlalchemy import create_engine, select, update, delete, insert
from sqlalchemy import Column, String, Integer, ForeignKey, func
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Типы
from typing import List, Optional

# Async
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Eager loading
from sqlalchemy.orm import selectinload, joinedload, subqueryload
```

### Шаблон быстрого старта
```python
# 1. Создать базу
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# 2. Создать модель
class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

# 3. Создать engine
from sqlalchemy import create_engine
engine = create_engine("sqlite:///db.sqlite")

# 4. Создать таблицы
Base.metadata.create_all(engine)

# 5. Работать с данными
from sqlalchemy.orm import Session
from sqlalchemy import select

with Session(engine) as session:
    # CREATE
    user = User(name="John")
    session.add(user)
    session.commit()

    # READ
    users = session.scalars(select(User)).all()

    # UPDATE
    user.name = "Jane"
    session.commit()

    # DELETE
    session.delete(user)
    session.commit()
```

---

## ИСТОЧНИКИ И ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ

- **Официальная документация**: https://docs.sqlalchemy.org/en/20/
- **Unified Tutorial**: https://docs.sqlalchemy.org/en/20/tutorial/index.html
- **ORM Quick Start**: https://docs.sqlalchemy.org/en/20/orm/quickstart.html
- **Миграция с 1.x на 2.0**: https://docs.sqlalchemy.org/en/20/changelog/migration_20.html

---

**Версия правил**: 1.0 (на основе SQLAlchemy 2.0.46, февраль 2026)
