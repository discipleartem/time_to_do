# API документация Time to DO

## � Обзор

Time to DO предоставляет RESTful API для управления задачами, проектами и пользователями. API построен на FastAPI с автоматической документацией Swagger/OpenAPI.

**Базовый URL:** `http://localhost:8000/api/v1`

**Документация:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 🔐 Аутентификация

### JWT Bearer Token
Все защищенные эндпоинты требуют JWT токен в заголовке:
```
Authorization: Bearer <your-jwt-token>
```

### Получение токена
```bash
# Регистрация (возвращает access_token и refresh_token)
POST /api/v1/auth/register

# Вход по email/пароль
POST /api/v1/auth/login

# Обновление токена
POST /api/v1/auth/refresh
```

### Токены
- **Access Token**: Кратковременный токен (15 минут) для API запросов
- **Refresh Token**: Долговременный токен (7 дней) для обновления access token

### Пример ответа при регистрации/логине
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe"
  }
}
```

---

## 🚀 Эндпоинты API

### 📝 Аутентификация (`/auth`)

| Метод | Эндпоинт | Описание | Требует авторизации |
|-------|----------|----------|---------------------|
| POST | `/register` | Регистрация нового пользователя | ❌ |
| POST | `/login` | Вход по email/пароль | ❌ |
| POST | `/refresh` | Обновление JWT токена | ❌ |
| POST | `/change-password` | Смена пароля | ✅ |
| GET | `/me` | Информация о текущем пользователе | ✅ |
| POST | `/logout` | Выход из системы | ✅ |

### 👥 Пользователи (`/users`)

| Метод | Эндпоинт | Описание | Требует авторизации |
|-------|----------|----------|---------------------|
| GET | `/` | Список пользователей | ✅ |
| GET | `/me` | Профиль текущего пользователя | ✅ |
| PUT | `/me` | Обновление текущего пользователя | ✅ |
| GET | `/{user_id}` | Информация о пользователе | ✅ |
| PUT | `/{user_id}` | Обновление пользователя (админ) | ✅ |
| DELETE | `/{user_id}` | Удаление пользователя (админ) | ✅ |

### 🏗️ Проекты (`/projects`)

| Метод | Эндпоинт | Описание | Требует авторизации |
|-------|----------|----------|---------------------|
| GET | `/` | Список проектов пользователя | ✅ |
| POST | `/` | Создание проекта | ✅ |
| GET | `/{project_id}` | Информация о проекте | ✅ |
| PUT | `/{project_id}` | Обновление проекта | ✅ |
| DELETE | `/{project_id}` | Удаление проекта | ✅ |
| GET | `/{project_id}/members` | Участники проекта | ✅ |
| POST | `/{project_id}/members` | Добавление участника | ✅ |
| DELETE | `/{project_id}/members/{user_id}` | Удаление участника | ✅ |

### ✅ Реализованные эндпоинты
- **Аутентификация**: Полностью реализована (регистрация, логин, обновление токена)
- **Проекты**: Полностью реализованы CRUD операции и управление участниками
- **Пользователи**: Базовые операции с профилем

### 🚧 В разработке
- **Задачи**: CRUD операции, комментарии, статусы
- **Kanban**: Доска с drag & drop
- **Time Tracker**: Таймеры, записи времени
- **Спринты**: SCRUM методология
- **Метрики**: Velocity, burndown, cycle time

### 📋 Задачи (`/tasks`)

| Метод | Эндпоинт | Описание | Требует авторизации |
|-------|----------|----------|---------------------|
| GET | `/` | Список задач (с фильтрацией) | ✅ |
| POST | `/` | Создание задачи | ✅ |
| GET | `/{task_id}` | Информация о задаче | ✅ |
| PUT | `/{task_id}` | Обновление задачи | ✅ |
| DELETE | `/{task_id}` | Удаление задачи | ✅ |
| GET | `/{task_id}/comments` | Комментарии к задаче | ✅ |
| POST | `/{task_id}/comments` | Добавление комментария | ✅ |
| PUT | `/{task_id}/comments/{comment_id}` | Обновление комментария | ✅ |
| DELETE | `/{task_id}/comments/{comment_id}` | Удаление комментария | ✅ |

### 🐙 GitHub OAuth (`/github`)

| Метод | Эндпоинт | Описание | Требует авторизации |
|-------|----------|----------|---------------------|
| GET | `/login` | Перенаправление на GitHub | ❌ |
| GET | `/callback` | Обработка callback от GitHub | ❌ |
| GET | `/user-info` | Информация о GitHub пользователе | ✅ |
| POST | `/disconnect` | Отключение GitHub | ✅ |
```

---

## 👥 Пользователи

### Регистрация
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "password": "password123"
}
```

### Получение текущего пользователя
```http
GET /api/v1/auth/me
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "avatar_url": "https://github.com/johndoe.png",
  "is_active": true,
  "role": "user",
  "created_at": "2024-01-01T00:00:00Z",
  "is_verified": true
}
```

### Обновление профиля
```http
PUT /api/v1/users/me
Authorization: Bearer <token>
Content-Type: application/json

{
  "full_name": "John Smith",
  "avatar_url": "https://example.com/avatar.png"
}
```

---

## 🏢 Проекты

### Получение проектов
```http
GET /api/v1/projects/?skip=0&limit=20
Authorization: Bearer <token>
```

**Ответ:**
```json
[
  {
    "id": "uuid",
    "name": "My Project",
    "description": "Project description",
    "status": "active",
    "is_public": false,
    "owner_id": "uuid",
    "created_at": "2024-01-01T00:00:00Z",
    "member_count": 3
  }
]
```

### Создание проекта
```http
POST /api/v1/projects/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "New Project",
  "description": "Project description",
  "is_public": false,
  "allow_external_sharing": true,
  "max_members": "5"
}
```

### Получение проекта
```http
GET /api/v1/projects/{project_id}
Authorization: Bearer <token>
```

### Обновление проекта
```http
PUT /api/v1/projects/{project_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Updated Project",
  "description": "New description"
}
```

### Участники проекта
```http
GET /api/v1/projects/{project_id}/members
Authorization: Bearer <token>
```

**Ответ:**
```json
[
  {
    "id": "uuid",
    "project_id": "uuid",
    "user_id": "uuid",
    "role": "owner",
    "is_active": true,
    "user": {
      "id": "uuid",
      "username": "johndoe",
      "full_name": "John Doe",
      "avatar_url": "https://github.com/johndoe.png"
    }
  }
]
```

### Добавление участника
```http
POST /api/v1/projects/{project_id}/members
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": "uuid",
  "role": "member"
}
```

---

## 📋 Задачи

### Получение задач проекта
```http
GET /api/v1/tasks/?project_id=uuid&status=todo&skip=0&limit=20
Authorization: Bearer <token>
```

**Ответ:**
```json
[
  {
    "id": "uuid",
    "title": "Task title",
    "description": "Task description",
    "status": "todo",
    "priority": "medium",
    "story_point": "3",
    "order": 1,
    "project_id": "uuid",
    "creator_id": "uuid",
    "assignee_id": "uuid",
    "due_date": "2024-01-15",
    "estimated_hours": 8,
    "actual_hours": 5,
    "created_at": "2024-01-01T00:00:00Z",
    "creator": {
      "id": "uuid",
      "username": "creator",
      "full_name": "Creator Name"
    },
    "assignee": {
      "id": "uuid",
      "username": "assignee",
      "full_name": "Assignee Name"
    }
  }
]
```

### Создание задачи
```http
POST /api/v1/tasks/
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "New Task",
  "description": "Task description",
  "status": "todo",
  "priority": "medium",
  "story_point": "3",
  "project_id": "uuid",
  "assignee_id": "uuid",
  "due_date": "2024-01-15",
  "estimated_hours": 8
}
```

### Получение задачи
```http
GET /api/v1/tasks/{task_id}
Authorization: Bearer <token>
```

### Обновление задачи
```http
PUT /api/v1/tasks/{task_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Updated Task",
  "status": "in_progress",
  "assignee_id": "uuid"
}
```

### Комментарии к задаче
```http
GET /api/v1/tasks/{task_id}/comments
Authorization: Bearer <token>
```

**Ответ:**
```json
[
  {
    "id": "uuid",
    "content": "Comment text",
    "task_id": "uuid",
    "author_id": "uuid",
    "is_edited": false,
    "created_at": "2024-01-01T00:00:00Z",
    "author": {
      "id": "uuid",
      "username": "commenter",
      "full_name": "Commenter Name",
      "avatar_url": "https://github.com/commenter.png"
    }
  }
]
```

### Добавление комментария
```http
POST /api/v1/tasks/{task_id}/comments
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "This is a comment"
}
```

---

## 🏃‍♂️ Kanban доска

### Получение доски проекта
```http
GET /api/v1/kanban/projects/{project_id}/board
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "project_id": "uuid",
  "columns": [
    {
      "id": "todo",
      "name": "To Do",
      "tasks": [
        {
          "id": "uuid",
          "title": "Task 1",
          "status": "todo",
          "priority": "high",
          "order": 1,
          "assignee": {
            "id": "uuid",
            "username": "assignee",
            "avatar_url": "https://github.com/assignee.png"
          }
        }
      ]
    },
    {
      "id": "in_progress",
      "name": "In Progress",
      "tasks": []
    },
    {
      "id": "done",
      "name": "Done",
      "tasks": []
    }
  ]
}
```

### Перемещение задачи
```http
PUT /api/v1/kanban/tasks/{task_id}/move
Authorization: Bearer <token>
Content-Type: application/json

{
  "new_status": "in_progress",
  "new_order": 1
}
```

---

## ⏱️ Time Tracker

### Создание записи времени
```http
POST /api/v1/time/entries
Authorization: Bearer <token>
Content-Type: application/json

{
  "task_id": "uuid",
  "description": "Work on feature",
  "start_time": "2024-01-01T09:00:00Z",
  "end_time": "2024-01-01T11:00:00Z"
}
```

### Запуск таймера
```http
PUT /api/v1/time/entries/{entry_id}/start
Authorization: Bearer <token>
```

### Остановка таймера
```http
PUT /api/v1/time/entries/{entry_id}/stop
Authorization: Bearer <token>
```

### История записей
```http
GET /api/v1/time/entries?task_id=uuid&user_id=uuid&date_from=2024-01-01&date_to=2024-01-31
Authorization: Bearer <token>
```

**Ответ:**
```json
[
  {
    "id": "uuid",
    "description": "Work on feature",
    "start_time": "2024-01-01T09:00:00Z",
    "end_time": "2024-01-01T11:00:00Z",
    "duration_minutes": 120,
    "is_active": false,
    "task_id": "uuid",
    "user_id": "uuid",
    "task": {
      "id": "uuid",
      "title": "Task title"
    }
  }
]
```

---

## 🏃‍♂️ Спринты

### Получение спринтов проекта
```http
GET /api/v1/sprints?project_id=uuid
Authorization: Bearer <token>
```

### Создание спринта
```http
POST /api/v1/sprints
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Sprint 1",
  "description": "First sprint",
  "project_id": "uuid",
  "start_date": "2024-01-01",
  "end_date": "2024-01-14",
  "capacity_hours": 80,
  "velocity_points": 20
}
```

### Запуск спринта
```http
PUT /api/v1/sprints/{sprint_id}/start
Authorization: Bearer <token>
```

### Завершение спринта
```http
PUT /api/v1/sprints/{sprint_id}/complete
Authorization: Bearer <token>
```

### Burndown данные
```http
GET /api/v1/sprints/{sprint_id}/burndown
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "sprint_id": "uuid",
  "total_points": 20,
  "completed_points": 8,
  "remaining_points": 12,
  "days": [
    {
      "date": "2024-01-01",
      "remaining_points": 20,
      "ideal_remaining": 18
    },
    {
      "date": "2024-01-02",
      "remaining_points": 15,
      "ideal_remaining": 16
    }
  ]
}
```

---

## 🔗 GitHub OAuth

### Начало аутентификации
```http
GET /api/v1/github/login
```

Перенаправляет на GitHub для авторизации.

### Callback обработка
```http
GET /api/v1/github/callback?code=xxx&state=xxx
```

Возвращает JWT токены после успешной аутентификации.

### Отключение GitHub
```http
POST /api/v1/github/disconnect
Authorization: Bearer <token>
```

---

## 📊 Метрики

### Velocity команды
```http
GET /api/v1/metrics/velocity?project_id=uuid&sprints_count=5
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "project_id": "uuid",
  "sprints": [
    {
      "sprint_id": "uuid",
      "name": "Sprint 1",
      "planned_points": 20,
      "completed_points": 18
    }
  ],
  "average_velocity": 17.5,
  "velocity_trend": "increasing"
}
```

### Cycle time
```http
GET /api/v1/metrics/cycle-time?project_id=uuid&date_from=2024-01-01&date_to=2024-01-31
Authorization: Bearer <token>
```

---

## 🔄 WebSocket Events

### Подключение
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onopen = function() {
  // Аутентификация
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'Bearer <jwt_token>'
  }));
};
```

### События

#### Задача обновлена
```json
{
  "type": "task_updated",
  "data": {
    "task_id": "uuid",
    "project_id": "uuid",
    "changes": {
      "status": "in_progress"
    }
  }
}
```

#### Новый комментарий
```json
{
  "type": "comment_added",
  "data": {
    "task_id": "uuid",
    "comment": {
      "id": "uuid",
      "content": "New comment",
      "author": {
        "id": "uuid",
        "username": "commenter"
      }
    }
  }
}
```

#### Пользователь онлайн
```json
{
  "type": "user_online",
  "data": {
    "user_id": "uuid",
    "project_id": "uuid"
  }
}
```

---

## ❌ Ошибки

### Формат ошибок
```json
{
  "detail": "Error description",
  "error_code": "VALIDATION_ERROR",
  "field": "email"
}
```

### HTTP статусы
- `200` - OK
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `409` - Conflict
- `422` - Validation Error
- `429` - Rate Limited
- `500` - Internal Server Error

### Примеры ошибок

#### Валидация
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### Авторизация
```json
{
  "detail": "Could not validate credentials"
}
```

#### Доступ запрещен
```json
{
  "detail": "Not enough permissions"
}
```

---

## 📝 Rate Limiting

### Лимиты
- **Аутентификация**: 5 запросов в минуту
- **API**: 100 запросов в минуту
- **WebSocket**: 10 сообщений в секунду

### Заголовки
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1640995200
```

---

## 🧪 Тестирование API

### Пример с curl
```bash
# Логин
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}' \
  | jq -r '.access_token')

# Получение проектов
curl -s -X GET http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer $TOKEN"
```

### Пример с Python
```python
import httpx

class TimeToDoAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.Client()
        self.token = None

    def login(self, email: str, password: str):
        response = self.client.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        return data

    def get_projects(self):
        response = self.client.get(
            f"{self.base_url}/api/v1/projects/",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        response.raise_for_status()
        return response.json()

# Использование
api = TimeToDoAPI("http://localhost:8000")
api.login("user@example.com", "password123")
projects = api.get_projects()
```

---

## 📚 SDK и клиенты

### Python SDK
```bash
pip install timetodo-python
```

```python
from timetodo import TimeToDoClient

client = TimeToDoClient(api_key="your_token")
projects = client.projects.list()
```

### JavaScript SDK
```bash
npm install timetodo-js
```

```javascript
import { TimeToDoClient } from 'timetodo-js';

const client = new TimeToDoClient({ apiKey: 'your_token' });
const projects = await client.projects.list();
```

---

Эта API документация предоставляет полную информацию для интеграции с Time to DO.
