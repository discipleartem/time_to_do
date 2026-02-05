# 🌐 Web/API Development — Специализированные правила

**Цель:** Правила для FastAPI, Flask, Django разработки
**Фокус:** REST API, async endpoints, валидация, обработка ошибок

---

## 📋 Содержание

1. [FastAPI правила](#1-fastapi-правила)
2. [Pydantic модели](#2-pydantic-модели)
3. [Обработка ошибок](#3-обработка-ошибок)
4. [Dependency Injection](#4-dependency-injection)
5. [Async & Concurrency](#5-async--concurrency)
6. [Security](#6-security)
7. [Rate Limiting](#7-rate-limiting)

---

## 1. FastAPI правила

### Структура endpoint

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter()

class UserCreate(BaseModel):
    email: str
    password: str
    name: str

class UserOut(BaseModel):
    id: int
    email: str
    name: str

# ✅ Правильно: явный response_model, dependency injection
@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать пользователя",
    description="Создаёт нового пользователя в системе"
)
async def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service)
) -> UserOut:
    """
    Создаёт нового пользователя.

    Args:
        payload: Данные для создания пользователя
        service: Сервис для работы с пользователями

    Returns:
        Созданный пользователь

    Raises:
        HTTPException: 400 если пользователь уже существует
    """
    try:
        user = await service.create_user(payload)
        return UserOut.from_orm(user)
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

### Router организация

```python
# ✅ Правильно: группировка по доменам
from fastapi import APIRouter

# Отдельные роутеры для каждого домена
users_router = APIRouter(prefix="/users", tags=["users"])
auth_router = APIRouter(prefix="/auth", tags=["authentication"])
posts_router = APIRouter(prefix="/posts", tags=["posts"])

# В main.py
app.include_router(users_router)
app.include_router(auth_router)
app.include_router(posts_router)
```

---

## 2. Pydantic модели

### Pydantic v2 (современный подход)

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

# ✅ Правильно: Pydantic v2
class UserCreate(BaseModel):
    email: str = Field(
        ...,
        pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$",
        description="Email адрес пользователя"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Пароль (минимум 8 символов)"
    )
    age: int = Field(..., ge=18, le=150, description="Возраст")
    name: str = Field(..., min_length=1, max_length=100)

    @field_validator('email')
    @classmethod
    def email_must_be_lowercase(cls, v: str) -> str:
        """Email всегда в нижнем регистре."""
        return v.lower()

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Проверка сложности пароля."""
        if not any(c.isupper() for c in v):
            raise ValueError("Пароль должен содержать заглавную букву")
        if not any(c.isdigit() for c in v):
            raise ValueError("Пароль должен содержать цифру")
        return v

    model_config = {
        "str_strip_whitespace": True,
        "validate_assignment": True,
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "SecurePass123",
                    "age": 25,
                    "name": "Ivan Petrov"
                }
            ]
        }
    }

class UserOut(BaseModel):
    """Модель для вывода данных пользователя."""
    id: int
    email: str
    name: str
    created_at: datetime
    is_active: bool = True

    model_config = {
        "from_attributes": True  # Для работы с ORM
    }

class UserUpdate(BaseModel):
    """Модель для обновления пользователя."""
    email: Optional[str] = None
    name: Optional[str] = None
    age: Optional[int] = Field(None, ge=18, le=150)

    @field_validator('email')
    @classmethod
    def email_must_be_lowercase(cls, v: str | None) -> str | None:
        """Email всегда в нижнем регистре."""
        return v.lower() if v else None
```

---

## 3. Обработка ошибок

### Принципы

```text
✓ HTTPException только на границе API (в endpoints)
✓ Внутри сервисов — domain exceptions
✓ Логирование с контекстом
✓ Понятные сообщения для клиента
```

### Кастомные исключения для домена

```python
# domain/exceptions.py
class DomainError(Exception):
    """Базовое исключение домена."""
    pass

class UserAlreadyExistsError(DomainError):
    """Пользователь уже существует."""
    pass

class UserNotFoundError(DomainError):
    """Пользователь не найден."""
    pass

class ValidationError(DomainError):
    """Ошибка валидации."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}
```

### Обработка в endpoints

```python
import logging
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# ✅ Правильно: маппинг domain exceptions → HTTP
@router.post("/users", response_model=UserOut)
async def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service)
):
    """Создаёт пользователя."""
    try:
        user = await service.create_user(payload)
        logger.info(f"Создан пользователь: {user.id}")
        return UserOut.from_orm(user)

    except UserAlreadyExistsError as e:
        logger.warning(f"Попытка создать существующего пользователя: {payload.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Пользователь с email {payload.email} уже существует"
        )

    except ValidationError as e:
        logger.error(f"Ошибка валидации: {e.details}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

    except Exception as e:
        logger.exception("Неожиданная ошибка при создании пользователя")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )

@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service)
):
    """Получает пользователя по ID."""
    try:
        user = await service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пользователь с ID {user_id} не найден"
            )
        return UserOut.from_orm(user)

    except HTTPException:
        raise  # Пробрасываем HTTP ошибки дальше

    except Exception as e:
        logger.exception(f"Ошибка при получении пользователя {user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )
```

---

## 4. Dependency Injection

### Принципы

```text
✓ Используем FastAPI Depends для injection
✓ Создаём фабрики для зависимостей
✓ Явные зависимости в конструкторах
✓ Лёгкое тестирование через моки
```

### Примеры

```python
from fastapi import Depends
from typing import Annotated

# ✅ Фабрики зависимостей
def get_db_session() -> Generator[Session, None, None]:
    """Создаёт сессию БД."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_cache_client() -> Redis:
    """Получает клиент Redis."""
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )

def get_user_repository(
    db: Session = Depends(get_db_session)
) -> UserRepository:
    """Создаёт репозиторий пользователей."""
    return UserRepository(db)

def get_user_service(
    repository: UserRepository = Depends(get_user_repository),
    cache: Redis = Depends(get_cache_client)
) -> UserService:
    """Создаёт сервис пользователей."""
    return UserService(repository, cache)

# ✅ Использование в endpoint
@router.post("/users", response_model=UserOut)
async def create_user(
    payload: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)]
):
    """Создаёт пользователя."""
    user = await service.create_user(payload)
    return UserOut.from_orm(user)
```

---

## 5. Async & Concurrency

### Основные правила

```text
✓ Async endpoints для I/O операций
✓ asyncio.gather() для параллельных запросов
✓ Async database drivers (asyncpg, motor)
✓ Async HTTP clients (httpx, aiohttp)
```

### Запрещено

```text
✗ time.sleep() в async функциях
✗ requests (синхронный) в async endpoints
✗ Blocking I/O в event loop
```

### Примеры

```python
import asyncio
import httpx
from typing import List

# ✅ Правильно: async endpoint с параллельными запросами
@router.get("/users/{user_id}/full", response_model=UserFullOut)
async def get_user_with_details(
    user_id: int,
    service: UserService = Depends(get_user_service),
    posts_service: PostsService = Depends(get_posts_service)
):
    """Получает пользователя со всеми деталями."""
    # Параллельное выполнение нескольких async операций
    user, posts, stats = await asyncio.gather(
        service.get_user(user_id),
        posts_service.get_user_posts(user_id),
        service.get_user_stats(user_id)
    )

    if not user:
        raise HTTPException(404, "Пользователь не найден")

    return UserFullOut(
        user=UserOut.from_orm(user),
        posts=[PostOut.from_orm(p) for p in posts],
        stats=stats
    )

# ✅ Async HTTP запросы
async def fetch_external_data(user_id: int) -> dict:
    """Получает данные из внешнего API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.example.com/users/{user_id}",
            timeout=5.0
        )
        response.raise_for_status()
        return response.json()

# ❌ Неправильно: blocking операции
@router.get("/users/{user_id}")
async def get_user_bad(user_id: int):
    time.sleep(1)  # ❌ Блокирует event loop
    response = requests.get(f"https://api.example.com/users/{user_id}")  # ❌
    return response.json()

# ✅ Правильно: async операции
@router.get("/users/{user_id}")
async def get_user_good(user_id: int):
    await asyncio.sleep(1)  # ✅ Не блокирует
    async with httpx.AsyncClient() as client:  # ✅
        response = await client.get(f"https://api.example.com/users/{user_id}")
        return response.json()
```

---

## 6. Security

### Основные принципы

```text
✓ HTTPS only в production
✓ CORS правильно настроен
✓ Rate limiting
✓ Input validation (Pydantic)
✓ Хеширование паролей
✓ JWT токены
```

### CORS

```python
from fastapi.middleware.cors import CORSMiddleware

# ✅ Правильная настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Из .env, не "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Хеширование паролей

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Хеширует пароль."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed: str) -> bool:
    """Проверяет пароль."""
    return pwd_context.verify(plain_password, hashed)
```

### JWT аутентификация

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Создаёт JWT токен."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(get_user_service)
) -> User:
    """Получает текущего пользователя из JWT токена."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невозможно проверить учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await service.get_user(user_id)
    if user is None:
        raise credentials_exception

    return user
```

---

## 7. Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ✅ Использование rate limiting
@app.post("/api/login")
@limiter.limit("5/minute")  # Максимум 5 попыток в минуту
async def login(
    request: Request,
    credentials: LoginCredentials,
    service: AuthService = Depends(get_auth_service)
):
    """Эндпоинт авторизации с rate limiting."""
    user = await service.authenticate(credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учётные данные"
        )

    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}
```

---

## Чеклист для Web/API

```text
☐ Response models явно указаны
☐ Dependency Injection используется
☐ Async для I/O операций
☐ HTTPException только в endpoints
☐ Domain exceptions в сервисах
☐ Логирование с контекстом
☐ Pydantic валидация
☐ Хеширование паролей
☐ CORS настроен
☐ Rate limiting добавлен
☐ Документация API (OpenAPI)
```

---

**Версия:** 1.0
**Дата обновления:** Февраль 2026
**Рекомендуемое местоположение:** `.windsurf/rules/web-api.md`
