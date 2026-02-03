# Руководство по созданию модулей Time to DO

## 🧩 Обзор модульной архитектуры

Time to DO использует модульную архитектуру для обеспечения гибкости и масштабируемости. Каждый модуль является независимым компонентом с минимальными зависимостями.

### Структура модуля

```
modules/analytics/
├── __init__.py          # Экспорт компонентов модуля
├── models.py            # SQLAlchemy модели
├── api.py               # FastAPI роутеры
├── service.py           # Бизнес-логика
├── dependencies.py      # FastAPI зависимости
├── schemas.py           # Pydantic схемы
└── tests/               # Тесты модуля
    ├── __init__.py
    ├── test_api.py
    ├── test_service.py
    └── test_models.py
```

---

## 🚀 Создание нового модуля

### 1. Использование Make команды

```bash
make create-module MODULE_NAME=analytics
```

Эта команда автоматически создаст структуру модуля с базовыми файлами.

### 2. Ручное создание (если Make недоступен)

```bash
mkdir -p modules/analytics/tests
touch modules/analytics/__init__.py
touch modules/analytics/models.py
touch modules/analytics/api.py
touch modules/analytics/service.py
touch modules/analytics/dependencies.py
touch modules/analytics/schemas.py
touch modules/analytics/tests/__init__.py
touch modules/analytics/tests/test_api.py
touch modules/analytics/tests/test_service.py
touch modules/analytics/tests/test_models.py
```

---

## 📁 Файлы модуля

### __init__.py

Экспортирует основные компоненты модуля для использования в других частях приложения.

```python
# modules/analytics/__init__.py
from .api import router as analytics_router
from .models import AnalyticsEvent, Report
from .service import AnalyticsService

__all__ = ["analytics_router", "AnalyticsEvent", "Report", "AnalyticsService"]
```

### models.py

Определяет SQLAlchemy модели для хранения данных модуля.

```python
# modules/analytics/models.py
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from core.models.base import BaseModel

class AnalyticsEvent(BaseModel):
    """Модель события аналитики"""

    __tablename__ = "analytics_events"

    user_id = Column(String, nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    event_data = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Связи
    user = relationship("User", back_populates="analytics_events")

class Report(BaseModel):
    """Модель отчета"""

    __tablename__ = "reports"

    name = Column(String(200), nullable=False)
    description = Column(Text)
    report_type = Column(String(50), nullable=False)
    filters = Column(Text)  # JSON
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    creator = relationship("User", back_populates="reports")
```

### schemas.py

Pydantic схемы для валидации и сериализации данных.

```python
# modules/analytics/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class AnalyticsEventCreate(BaseModel):
    """Схема создания события аналитики"""
    event_type: str = Field(..., max_length=50)
    event_data: Optional[Dict[str, Any]] = None

class AnalyticsEventResponse(BaseModel):
    """Схема ответа события аналитики"""
    id: str
    user_id: str
    event_type: str
    event_data: Optional[Dict[str, Any]]
    timestamp: datetime

    class Config:
        from_attributes = True

class ReportCreate(BaseModel):
    """Схема создания отчета"""
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    report_type: str = Field(..., max_length=50)
    filters: Optional[Dict[str, Any]] = None

class ReportResponse(BaseModel):
    """Схема ответа отчета"""
    id: str
    name: str
    description: Optional[str]
    report_type: str
    filters: Optional[Dict[str, Any]]
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True
```

### service.py

Бизнес-логика модуля.

```python
# modules/analytics/service.py
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import json

from core.models.user import User
from shared.database import get_db
from .models import AnalyticsEvent, Report
from .schemas import AnalyticsEventCreate, ReportCreate

class AnalyticsService:
    """Сервис для работы с аналитикой"""

    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def track_event(
        self,
        user_id: str,
        event_data: AnalyticsEventCreate
    ) -> AnalyticsEvent:
        """Отслеживание события"""
        event = AnalyticsEvent(
            user_id=user_id,
            event_type=event_data.event_type,
            event_data=json.dumps(event_data.event_data) if event_data.event_data else None
        )

        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        return event

    async def get_user_events(
        self,
        user_id: str,
        event_type: Optional[str] = None,
        days: int = 30
    ) -> List[AnalyticsEvent]:
        """Получение событий пользователя"""
        since_date = datetime.utcnow() - timedelta(days=days)

        stmt = select(AnalyticsEvent).where(
            AnalyticsEvent.user_id == user_id,
            AnalyticsEvent.timestamp >= since_date
        )

        if event_type:
            stmt = stmt.where(AnalyticsEvent.event_type == event_type)

        stmt = stmt.order_by(AnalyticsEvent.timestamp.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_report(
        self,
        user_id: str,
        report_data: ReportCreate
    ) -> Report:
        """Создание отчета"""
        report = Report(
            name=report_data.name,
            description=report_data.description,
            report_type=report_data.report_type,
            filters=json.dumps(report_data.filters) if report_data.filters else None,
            created_by=user_id
        )

        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        return report
```

### api.py

FastAPI роутеры для обработки HTTP запросов.

```python
# modules/analytics/api.py
from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from core.auth.dependencies import get_current_user
from core.models.user import User
from .service import AnalyticsService
from .schemas import (
    AnalyticsEventCreate,
    AnalyticsEventResponse,
    ReportCreate,
    ReportResponse
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.post("/events", response_model=AnalyticsEventResponse)
async def track_event(
    event_data: AnalyticsEventCreate,
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends()
):
    """Отслеживание события"""
    event = await service.track_event(current_user.id, event_data)
    return event

@router.get("/events", response_model=List[AnalyticsEventResponse])
async def get_user_events(
    event_type: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends()
):
    """Получение событий пользователя"""
    events = await service.get_user_events(current_user.id, event_type, days)
    return events

@router.post("/reports", response_model=ReportResponse)
async def create_report(
    report_data: ReportCreate,
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends()
):
    """Создание отчета"""
    report = await service.create_report(current_user.id, report_data)
    return report
```

### dependencies.py

FastAPI зависимости для инъекции сервисов.

```python
# modules/analytics/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from .service import AnalyticsService

def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    """Получение сервиса аналитики"""
    return AnalyticsService(db)
```

---

## 🧪 Тестирование модуля

### test_service.py

Тесты для бизнес-логики модуля.

```python
# modules/analytics/tests/test_service.py
import pytest
from datetime import datetime, timedelta

from modules.analytics.service import AnalyticsService
from modules.analytics.schemas import AnalyticsEventCreate

class TestAnalyticsService:
    """Тесты сервиса аналитики"""

    async def test_track_event(self, db_session, test_user):
        """Тест отслеживания события"""
        service = AnalyticsService(db_session)

        event_data = AnalyticsEventCreate(
            event_type="task_completed",
            event_data={"task_id": "test_task"}
        )

        event = await service.track_event(test_user.id, event_data)

        assert event.user_id == test_user.id
        assert event.event_type == "task_completed"
        assert event.timestamp is not None

    async def test_get_user_events(self, db_session, test_user):
        """Тест получения событий пользователя"""
        service = AnalyticsService(db_session)

        # Создаем несколько событий
        for i in range(5):
            event_data = AnalyticsEventCreate(
                event_type=f"event_{i}",
                event_data={"index": i}
            )
            await service.track_event(test_user.id, event_data)

        # Получаем события
        events = await service.get_user_events(test_user.id)

        assert len(events) == 5
        assert all(event.user_id == test_user.id for event in events)
```

### test_api.py

Тесты для API эндпоинтов модуля.

```python
# modules/analytics/tests/test_api.py
import pytest
from fastapi.testclient import AsyncClient

class TestAnalyticsAPI:
    """Тесты API аналитики"""

    async def test_track_event(self, client: AsyncClient, authenticated_user):
        """Тест отслеживания события через API"""
        headers = {"Authorization": f"Bearer {authenticated_user['token']}"}

        response = await client.post(
            "/api/v1/analytics/events",
            json={
                "event_type": "task_completed",
                "event_data": {"task_id": "test_task"}
            },
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["event_type"] == "task_completed"
        assert "id" in data

    async def test_get_user_events(self, client: AsyncClient, authenticated_user):
        """Тест получения событий через API"""
        headers = {"Authorization": f"Bearer {authenticated_user['token']}"}

        # Сначала создаем событие
        await client.post(
            "/api/v1/analytics/events",
            json={"event_type": "test_event"},
            headers=headers
        )

        # Получаем события
        response = await client.get(
            "/api/v1/analytics/events",
            headers=headers
        )

        assert response.status_code == 200
        events = response.json()
        assert len(events) == 1
        assert events[0]["event_type"] == "test_event"
```

---

## 🔗 Регистрация модуля в приложении

### 1. Добавление в core/main.py

```python
# core/main.py
from modules import load_modules

app = FastAPI()

# Загрузка модулей
load_modules(app, [
    "projects",
    "tasks",
    "time_tracking",
    "notifications",
    "github",
    "analytics"  # Новый модуль
])
```

### 2. Конфигурация модуля

Добавьте переменные окружения в `.env`:

```bash
# Модуль Analytics
ENABLE_ANALYTICS=true
ANALYTICS_RETENTION_DAYS=90
ANALYTICS_BATCH_SIZE=100
```

### 3. Миграции базы данных

Создайте миграции для новых моделей:

```bash
# Создание миграции
make migration MSG='add analytics module'

# Применение миграции
make migrate
```

---

## 🛠️ Работа с модулем

### Команды разработки

```bash
# Тестирование только модуля
make test-module MODULE_NAME=analytics

# Линтинг модуля
make lint-module MODULE_NAME=analytics

# Запуск с конкретными модулями
MODULES=projects,analytics make dev
```

### Отладка

```bash
# Python shell с моделями модуля
make shell
>>> from modules.analytics.models import AnalyticsEvent
>>> from modules.analytics.service import AnalyticsService
```

---

## 📋 Best Practices

### 1. Минимальные зависимости

Используйте только необходимые зависимости:

```python
# ✅ Хорошо - только Core зависимости
from core.auth.dependencies import get_current_user
from core.models.user import User
from shared.database import get_db

# ❌ Плохо - импорт других модулей
from modules.tasks.models import Task  # Избегайте циклических зависимостей
```

### 2. Изоляция тестов

Тесты модуля должны быть изолированными:

```python
# ✅ Изолированный тест
async def test_service_logic(self, db_session):
    service = AnalyticsService(db_session)
    # Тестируем только логику сервиса

# ❌ Зависимый тест
async def test_with_other_modules(self, client):
    # Тест зависит от других модулей
```

### 3. Конфигурация

Используйте конфигурацию для включения/выключения модуля:

```python
# core/config.py
class ModuleSettings(BaseSettings):
    enable_analytics: bool = True
    analytics_retention_days: int = 90

# В коде модуля
from core.config import module_settings

if not module_settings.enable_analytics:
    raise HTTPException(404, "Analytics module disabled")
```

### 4. Обработка ошибок

Используйте явную обработку ошибок:

```python
async def track_event(self, user_id: str, event_data: AnalyticsEventCreate) -> AnalyticsEvent:
    try:
        event = AnalyticsEvent(...)
        self.db.add(event)
        await self.db.commit()
        return event
    except IntegrityError as err:
        await self.db.rollback()
        raise ValueError(f"Invalid event data: {err}") from err
```

---

## 🔄 Обновление модуля

### 1. Добавление новых полей в модель

```python
# models.py
class AnalyticsEvent(BaseModel):
    # ... существующие поля
    priority = Column(String(20), default="medium")  # Новое поле
```

### 2. Создание миграции

```bash
make migration MSG='add priority to analytics events'
make migrate
```

### 3. Обновление схем

```python
# schemas.py
class AnalyticsEventCreate(BaseModel):
    event_type: str = Field(..., max_length=50)
    event_data: Optional[Dict[str, Any]] = None
    priority: str = Field("medium", regex="^(low|medium|high)$")  # Новое поле
```

---

## 📚 Дополнительные ресурсы

- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic Models](https://docs.pydantic.dev/latest/concepts/models/)
- [Pytest Async Testing](https://pytest-asyncio.readthedocs.io/)

---

Следуя этому руководству, вы сможете создавать мощные и независимые модули для Time to DO, которые легко тестировать, поддерживать и масштабировать.
