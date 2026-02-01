---
trigger: model_decision
description: FastAPI
---

# FastAPI - Ключевые принципы для проекта

> **FastAPI framework, high performance, easy to learn, fast to code, ready for production**

---

## 🚀 Основные принципы для проекта Time to Do

### 1. Структура приложения
- **Модульная архитектура** - разделение на логические модули
- **Repository Pattern** - инкапсуляция доступа к данным
- **Service Layer** - бизнес-логика в отдельных сервисах
- **Dependency Injection** - внедрение зависимостей через FastAPI

### 2. Безопасность
- **JWT аутентификация** с refresh токенами
- **Rate limiting** - 100 запросов в минуту на IP
- **CORS** настройка через environment variables
- **Security headers** - X-Content-Type-Options, X-Frame-Options, HSTS

### 3. Валидация данных
- **Pydantic V2** для всех моделей данных
- **Автоматическая валидация** входных данных
- **Четкие ошибки валидации** для клиента

---

## 📝 Структура роутов

### API роуты (`/api/*`)
```python
# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    auth_service: AuthService = Depends()
) -> TokenResponse:
    """Authenticate user and return JWT token."""
    try:
        return await auth_service.authenticate(login_data)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
```

### Web роуты (HTML/HTMX)
```python
# app/web/dashboard.py
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from app.services.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard")
async def dashboard(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Render dashboard page."""
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "user": current_user}
    )
```

---

## 🏗️ Repository Pattern

### Базовый репозиторий
```python
# app/repositories/base.py
from typing import Generic, TypeVar, Type, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    """Base repository with CRUD operations."""
    
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db
    
    def get(self, id: int) -> Optional[ModelType]:
        """Get entity by ID."""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[ModelType]:
        """Get multiple entities with pagination."""
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, obj_in: dict) -> ModelType:
        """Create new entity."""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def update(self, db_obj: ModelType, obj_in: dict) -> ModelType:
        """Update entity."""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def delete(self, id: int) -> ModelType:
        """Delete entity by ID."""
        obj = self.get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj
```

### Специализированный репозиторий
```python
# app/repositories/user.py
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    """Repository for User operations."""
    
    def __init__(self, db: Session):
        super().__init__(User, db)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_active_users(self, skip: int = 0, limit: int = 100):
        """Get active users only."""
        return (
            self.db.query(User)
            .filter(User.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )
```

---

## 🔧 Service Layer

### Пример сервиса
```python
# app/services/user.py
from typing import Optional, List
from sqlalchemy.orm import Session
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash

class UserService:
    """Service for user business logic."""
    
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create new user with validation."""
        # Check if user exists
        if self.user_repo.get_by_email(user_data.email):
            raise ValueError("User with this email already exists")
        
        if self.user_repo.get_by_username(user_data.username):
            raise ValueError("Username already taken")
        
        # Create user
        hashed_password = get_password_hash(user_data.password)
        user_dict = user_data.dict()
        user_dict["hashed_password"] = hashed_password
        del user_dict["password"]
        
        return self.user_repo.create(user_dict)
    
    async def update_user(
        self, 
        user_id: int, 
        user_data: UserUpdate
    ) -> Optional[User]:
        """Update user with validation."""
        user = self.user_repo.get(user_id)
        if not user:
            return None
        
        # Check email uniqueness
        if user_data.email and user_data.email != user.email:
            if self.user_repo.get_by_email(user_data.email):
                raise ValueError("Email already exists")
        
        return self.user_repo.update(user, user_data.dict(exclude_unset=True))
```

---

## 🔄 Dependency Injection

### Фабрика зависимостей
```python
# app/core/dependencies.py
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.user import UserService
from app.services.auth import AuthService
from app.repositories.user import UserRepository

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Get user service instance."""
    return UserService(db)

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get auth service instance."""
    return AuthService(db)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """Get current authenticated user."""
    return auth_service.get_current_user(token)
```

---

## 📊 Pydantic схемы

### Пример схем
```python
# app/schemas/user.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, validator

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    """User creation schema."""
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    """User response schema."""
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
```

---

## 🛡️ Middleware

### Пример middleware
```python
# app/core/middleware.py
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.requests = {}
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if current_time - req_time < self.period
            ]
        else:
            self.requests[client_ip] = []
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.calls:
            return Response(
                content="Rate limit exceeded",
                status_code=429
            )
        
        self.requests[client_ip].append(current_time)
        
        return await call_next(request)
```

---

## 🧪 Тестирование

### Пример теста
```python
# tests/test_user_service.py
import pytest
from sqlalchemy.orm import Session
from app.services.user import UserService
from app.schemas.user import UserCreate

@pytest.fixture
def user_service(db_session: Session):
    """Create user service fixture."""
    return UserService(db_session)

@pytest.fixture
def user_data():
    """Create test user data."""
    return UserCreate(
        email="test@example.com",
        username="testuser",
        password="testpass123",
        full_name="Test User"
    )

async def test_create_user(user_service: UserService, user_data: UserCreate):
    """Test user creation."""
    user = await user_service.create_user(user_data)
    
    assert user.email == user_data.email
    assert user.username == user_data.username
    assert user.is_active is True
    assert user.hashed_password is not None
    assert user.hashed_password != user_data.password

async def test_create_duplicate_email(user_service: UserService, user_data: UserCreate):
    """Test duplicate email validation."""
    await user_service.create_user(user_data)
    
    with pytest.raises(ValueError, match="email already exists"):
        await user_service.create_user(user_data)
```

---

## 🚀 Производительность

### Оптимизация запросов
```python
# Используйте select_related и preload_related
def get_user_with_projects(user_id: int):
    """Get user with their projects (optimized)."""
    return (
        db.query(User)
        .options(selectinload(User.projects))
        .filter(User.id == user_id)
        .first()
    )

# Индексы для производительности
# В модели:
class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    status = Column(String, index=True)  # Индекс для фильтрации
    priority = Column(String, index=True)  # Индекс для сортировки
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    due_date = Column(DateTime, index=True)  # Индекс для дат
```

---

## 📈 Мониторинг

### Health checks
```python
# app/api/health.py
from fastapi import APIRouter
from sqlalchemy import text
from app.core.database import engine

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.4.0",
        "service": "Time to Do API",
        "database": db_status
    }
```

---

*Эти принципы обеспечат создание масштабируемого, безопасного и поддерживаемого FastAPI приложения.*
