# FastAPI Documentation - Optimized for AI Agents

> **AI Agent Context**: This documentation is structured for LLM-based coding assistants and agentive IDEs. Each section includes metadata, explicit requirements, and self-contained examples.

## 📋 Document Metadata
- **Framework**: FastAPI 0.100+
- **Language**: Python 3.7+
- **Type**: Web Framework Documentation
- **Use Case**: Building REST APIs with automatic validation and documentation
- **Key Dependencies**: Pydantic, Starlette, Uvicorn

---

## 🎯 Quick Reference for Agents

### Common Tasks Mapping
```yaml
CREATE_API_ENDPOINT: "See Section 2.1 - Basic Route Definition"
ADD_VALIDATION: "See Section 3 - Request Validation with Pydantic"
SETUP_DATABASE: "See Section 7 - Database Integration"
ADD_AUTH: "See Section 8 - Authentication & Security"
HANDLE_FILES: "See Section 6 - File Operations"
CREATE_DOCS: "Auto-generated at /docs and /redoc"
```

### Critical Information for Code Generation
1. **Import Pattern**: Always `from fastapi import FastAPI`
2. **App Instance**: Create once with `app = FastAPI()`
3. **Async Support**: Prefer `async def` for I/O operations
4. **Type Hints**: Required for automatic validation
5. **Pydantic Models**: Use for request/response schemas

---

## 1. Installation & Setup

### 1.1 Installation Command
```bash
# Agent Instruction: Execute this for new projects
pip install "fastapi[all]"

# Minimal installation (production)
pip install fastapi uvicorn[standard]
```

### 1.2 Minimal Working Example
```python
# File: main.py
# Agent Note: This is the simplest possible FastAPI application

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

# Run with: uvicorn main:app --reload
```

**Agent Checklist**:
- ✅ Import FastAPI
- ✅ Create app instance
- ✅ Define at least one route
- ✅ Return JSON-serializable data

---

## 2. Route Definition

### 2.1 HTTP Methods Mapping
```python
# Agent Pattern: Map HTTP verbs to decorators

@app.get("/items")           # READ (list/search)
@app.post("/items")          # CREATE
@app.put("/items/{id}")      # UPDATE (full)
@app.patch("/items/{id}")    # UPDATE (partial)
@app.delete("/items/{id}")   # DELETE
@app.options("/items")       # OPTIONS
@app.head("/items")          # HEAD
```

### 2.2 Path Parameters
```python
# Agent Rule: Use {param_name} in path, add type hint in function

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    # FastAPI automatically converts and validates item_id as int
    return {"item_id": item_id}

# Multiple parameters
@app.get("/users/{user_id}/items/{item_id}")
async def read_user_item(user_id: int, item_id: str):
    return {"user_id": user_id, "item_id": item_id}
```

**Validation Behavior**:
- `/items/42` → ✅ `item_id = 42`
- `/items/foo` → ❌ 422 Validation Error

### 2.3 Query Parameters
```python
# Agent Rule: Function params NOT in path = query params

@app.get("/items")
async def read_items(
    skip: int = 0,           # Optional with default
    limit: int = 10,         # Optional with default
    q: str | None = None     # Optional, can be None
):
    return {"skip": skip, "limit": limit, "q": q}

# URL: /items?skip=20&limit=5&q=search
# Result: {"skip": 20, "limit": 5, "q": "search"}
```

### 2.4 Request Body (POST/PUT)
```python
from pydantic import BaseModel

# Agent Pattern: Define Pydantic model for request schema
class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

@app.post("/items")
async def create_item(item: Item):
    # item is automatically validated and parsed
    item_dict = item.dict()
    if item.tax:
        item_dict["price_with_tax"] = item.price + item.tax
    return item_dict
```

**Request Example**:
```json
POST /items
{
    "name": "Widget",
    "price": 29.99,
    "tax": 2.50
}
```

---

## 3. Data Validation with Pydantic

### 3.1 Field Validation
```python
from pydantic import BaseModel, Field, EmailStr, validator

class User(BaseModel):
    # Agent Pattern: Use Field() for constraints
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr  # Validates email format
    age: int = Field(..., ge=18, le=120)  # ge = >=, le = <=
    is_active: bool = True

    # Custom validation
    @validator('username')
    def username_alphanumeric(cls, v):
        assert v.isalnum(), 'must be alphanumeric'
        return v

# Usage in endpoint
@app.post("/users")
async def create_user(user: User):
    return user
```

### 3.2 Nested Models
```python
class Address(BaseModel):
    street: str
    city: str
    country: str

class UserWithAddress(BaseModel):
    name: str
    email: EmailStr
    address: Address  # Nested model

# Request body:
{
    "name": "John",
    "email": "john@example.com",
    "address": {
        "street": "123 Main St",
        "city": "Kyiv",
        "country": "Ukraine"
    }
}
```

### 3.3 Response Models
```python
# Agent Pattern: Separate input/output models for security

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str  # Received from client

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    # password NOT included in response

    class Config:
        orm_mode = True  # For database models

@app.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate):
    # Save user (password hashed)
    db_user = {"id": 1, **user.dict()}
    return db_user  # Only UserResponse fields returned
```

---

## 4. Dependency Injection

### 4.1 Basic Dependencies
```python
from fastapi import Depends

# Agent Pattern: Reusable dependencies
def get_query_params(skip: int = 0, limit: int = 100):
    return {"skip": skip, "limit": limit}

@app.get("/items")
async def read_items(commons: dict = Depends(get_query_params)):
    return commons

# Equivalent to:
# async def read_items(skip: int = 0, limit: int = 100):
```

### 4.2 Database Session Dependency
```python
# Agent Pattern: Database session management

from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/{user_id}")
async def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    return user
```

### 4.3 Authentication Dependency
```python
from fastapi import HTTPException, Header

# Agent Pattern: Reusable auth check
async def verify_token(x_token: str = Header(...)):
    if x_token != "secret-token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return x_token

@app.get("/protected")
async def protected_route(token: str = Depends(verify_token)):
    return {"message": "Access granted"}
```

---

## 5. Error Handling

### 5.1 HTTP Exceptions
```python
from fastapi import HTTPException

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    if item_id not in database:
        raise HTTPException(
            status_code=404,
            detail="Item not found",
            headers={"X-Error": "Custom header"}
        )
    return {"item_id": item_id}
```

### 5.2 Custom Exception Handlers
```python
from fastapi import Request
from fastapi.responses import JSONResponse

class CustomException(Exception):
    def __init__(self, name: str):
        self.name = name

@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(
        status_code=418,
        content={"message": f"Oops! {exc.name} did something wrong."}
    )

@app.get("/trigger")
async def trigger_error():
    raise CustomException(name="Agent")
```

### 5.3 Validation Error Response
```python
# Agent Note: Automatic validation errors return:
{
    "detail": [
        {
            "loc": ["body", "price"],
            "msg": "field required",
            "type": "value_error.missing"
        }
    ]
}
```

---

## 6. File Operations

### 6.1 File Upload
```python
from fastapi import File, UploadFile

# Agent Pattern: Small files
@app.post("/upload")
async def upload_file(file: bytes = File(...)):
    return {"file_size": len(file)}

# Agent Pattern: Large files (recommended)
@app.post("/uploadfile")
async def upload_large_file(file: UploadFile = File(...)):
    contents = await file.read()
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(contents)
    }

# Multiple files
@app.post("/uploadfiles")
async def upload_multiple(files: list[UploadFile] = File(...)):
    return [{"filename": f.filename} for f in files]
```

### 6.2 File Download
```python
from fastapi.responses import FileResponse

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = f"/path/to/files/{filename}"
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )
```

---

## 7. Database Integration

### 7.1 SQLAlchemy Setup
```python
# Agent Pattern: Complete database setup

# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://user:password@localhost/dbname"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# models.py
from sqlalchemy import Column, Integer, String
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

# schemas.py (Pydantic)
from pydantic import BaseModel

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True  # Enables ORM model conversion

# main.py
from sqlalchemy.orm import Session
from . import models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/users/", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(
        email=user.email,
        hashed_password=hash_password(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}", response_model=schemas.UserOut)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

---

## 8. Authentication & Security

### 8.1 OAuth2 with Password Flow
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

# Agent Configuration
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Password hashing
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# JWT token creation
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Get current user from token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_from_db(username)  # Your DB query
    if user is None:
        raise credentials_exception
    return user

# Login endpoint
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Protected endpoint
@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
```

### 8.2 API Key Security
```python
from fastapi import Security
from fastapi.security.api_key import APIKeyHeader

API_KEY = "your-api-key"
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

@app.get("/secure")
async def secure_endpoint(api_key: str = Depends(verify_api_key)):
    return {"message": "Access granted"}
```

---

## 9. Background Tasks

```python
from fastapi import BackgroundTasks

# Agent Pattern: Non-blocking operations
def write_notification(email: str, message: str):
    # Simulate slow operation
    with open("log.txt", "a") as log:
        log.write(f"Email to {email}: {message}\n")

@app.post("/send-notification/{email}")
async def send_notification(
    email: str,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(write_notification, email, "Welcome!")
    return {"message": "Notification sent in background"}
```

---

## 10. CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

# Agent Pattern: Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React/Vue dev server
    allow_credentials=True,
    allow_methods=["*"],  # Or ["GET", "POST"]
    allow_headers=["*"],
)
```

---

## 11. Testing

```python
from fastapi.testclient import TestClient

# Agent Pattern: Unit testing endpoints
client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

def test_create_item():
    response = client.post(
        "/items",
        json={"name": "Widget", "price": 29.99}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Widget"
```

---

## 12. Project Structure (Agent Template)

```
my_fastapi_project/
│
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app instance
│   ├── dependencies.py      # Shared dependencies
│   ├── config.py            # Configuration
│   │
│   ├── routers/             # Route handlers
│   │   ├── __init__.py
│   │   ├── users.py
│   │   └── items.py
│   │
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   └── user.py
│   │
│   ├── schemas/             # Pydantic models
│   │   ├── __init__.py
│   │   └── user.py
│   │
│   └── database.py          # Database connection
│
├── tests/
│   ├── __init__.py
│   └── test_main.py
│
├── requirements.txt
└── .env                     # Environment variables
```

**main.py Template**:
```python
from fastapi import FastAPI
from .routers import users, items
from .database import engine
from . import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="My API", version="1.0.0")

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(items.router, prefix="/items", tags=["items"])

@app.get("/")
async def root():
    return {"message": "API is running"}
```

---

## 13. Common Patterns for AI Agents

### 13.1 CRUD Operations Template
```python
# Agent: Use this template for standard CRUD

@app.post("/items", response_model=schemas.Item)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    db_item = models.Item(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/items", response_model=list[schemas.Item])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = db.query(models.Item).offset(skip).limit(limit).all()
    return items

@app.get("/items/{item_id}", response_model=schemas.Item)
def read_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.put("/items/{item_id}", response_model=schemas.Item)
def update_item(item_id: int, item: schemas.ItemUpdate, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    for key, value in item.dict(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return {"message": "Item deleted"}
```

### 13.2 Pagination Pattern
```python
from pydantic import BaseModel

class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list

@app.get("/items", response_model=PaginatedResponse)
def get_items(page: int = 1, per_page: int = 10, db: Session = Depends(get_db)):
    skip = (page - 1) * per_page
    items = db.query(models.Item).offset(skip).limit(per_page).all()
    total = db.query(models.Item).count()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": items
    }
```

### 13.3 Search/Filter Pattern
```python
@app.get("/items/search")
def search_items(
    q: str | None = None,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Item)

    if q:
        query = query.filter(models.Item.name.contains(q))
    if category:
        query = query.filter(models.Item.category == category)
    if min_price:
        query = query.filter(models.Item.price >= min_price)
    if max_price:
        query = query.filter(models.Item.price <= max_price)

    return query.all()
```

---

## 14. Performance Optimization

### 14.1 Async Database Operations
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session

@app.get("/users/{user_id}")
async def read_user(user_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    return user
```

### 14.2 Caching with Redis
```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    # Check cache
    cached = redis_client.get(f"item:{item_id}")
    if cached:
        return json.loads(cached)

    # Fetch from database
    item = get_item_from_db(item_id)

    # Cache for 1 hour
    redis_client.setex(
        f"item:{item_id}",
        3600,
        json.dumps(item)
    )
    return item
```

---

## 15. Deployment Checklist for Agents

### 15.1 Environment Variables
```python
# Agent Pattern: Use pydantic settings
from pydantic import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
```

### 15.2 Production Run Command
```bash
# Agent: Production deployment
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# With Gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 15.3 Docker Configuration
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 16. Debugging & Logging

```python
import logging

# Agent Pattern: Structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    logger.info(f"Fetching item with id: {item_id}")
    try:
        item = get_item(item_id)
        logger.info(f"Successfully fetched item: {item}")
        return item
    except Exception as e:
        logger.error(f"Error fetching item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## 17. API Documentation Customization

```python
# Agent: Custom OpenAPI schema
app = FastAPI(
    title="My Amazing API",
    description="This API does amazing things",
    version="2.0.0",
    docs_url="/documentation",  # Default: /docs
    redoc_url="/redocumentation",  # Default: /redoc
    openapi_url="/api/v1/openapi.json"
)

# Add custom metadata
@app.get("/items", tags=["items"], summary="Get all items")
async def read_items():
    """
    Retrieve all items from the database.

    - **skip**: Number of items to skip
    - **limit**: Maximum number of items to return
    """
    return []
```

---

## 🤖 Agent Decision Tree

```
User Request → Analyze Intent
    │
    ├─ Create API Endpoint?
    │   └─ Use Section 2 (Route Definition)
    │
    ├─ Add Data Validation?
    │   └─ Use Section 3 (Pydantic Models)
    │
    ├─ Need Database?
    │   └─ Use Section 7 (SQLAlchemy Setup)
    │
    ├─ Add Authentication?
    │   └─ Use Section 8 (OAuth2/JWT)
    │
    ├─ Handle File Upload?
    │   └─ Use Section 6 (File Operations)
    │
    └─ Full CRUD App?
        └─ Combine: Section 2 + 3 + 7 + 13.1
```

---

## 📚 Quick Reference: Status Codes

```python
# Agent: Common HTTP status codes in FastAPI
from fastapi import status

200: status.HTTP_200_OK                    # Success
201: status.HTTP_201_CREATED              # Resource created
204: status.HTTP_204_NO_CONTENT           # Success, no content
400: status.HTTP_400_BAD_REQUEST          # Invalid request
401: status.HTTP_401_UNAUTHORIZED         # Not authenticated
403: status.HTTP_403_FORBIDDEN            # Not authorized
404: status.HTTP_404_NOT_FOUND           # Resource not found
422: status.HTTP_422_UNPROCESSABLE_ENTITY # Validation error
500: status.HTTP_500_INTERNAL_SERVER_ERROR # Server error
```

---

## 🔍 Troubleshooting Guide for Agents

| Error | Cause | Solution |
|-------|-------|----------|
| `422 Unprocessable Entity` | Validation failed | Check Pydantic model matches request body |
| `ImportError: No module named 'uvicorn'` | Missing dependency | Run `pip install uvicorn` |
| `RuntimeError: no running event loop` | Sync function called in async context | Use `async def` or `def` consistently |
| `sqlalchemy.exc.OperationalError` | Database connection failed | Check DATABASE_URL and database is running |
| `401 Unauthorized` | Missing/invalid token | Verify token in `Authorization: Bearer <token>` header |

---

## 📖 Additional Resources

- **Official Docs**: https://fastapi.tiangolo.com
- **GitHub**: https://github.com/tiangolo/fastapi
- **Pydantic Docs**: https://docs.pydantic.dev
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org

---

**Document Version**: 1.0 (Optimized for AI Agents)
**Last Updated**: 2025-02-03
**Compatibility**: FastAPI 0.100+, Python 3.7+
