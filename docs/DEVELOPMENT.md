# Руководство для разработчиков Time to DO

## 🚀 Начало работы

### Требования
- Python 3.13
- Docker & Docker Compose
- Git
- PostgreSQL клиент (опционально)

### Быстрая настройка

```bash
# 1. Клонирование репозитория
git clone <repository-url>
cd time_to_do

# 2. Полная настройка окружения
make setup

# 3. Запуск в режиме разработки
make dev
```

Приложение будет доступно по адресу: http://localhost:8000

---

## 🚀 Основные команды разработки

### Установка и настройка
```bash
make setup          # Полная настройка проекта с Python 3.13
make clean          # Очистка кэша и временных файлов
```

### Разработка
```bash
make dev            # Запуск сервера разработки (uvicorn)
make shell          # Python shell с загруженными моделями
make lint           # Полная проверка кода (black + ruff + mypy + bandit)
```

### Тестирование
```bash
make test           # Запуск всех тестов (17 тестов)
make test-cov       # Тесты с покрытием кода
```

**Тестовое окружение:**
- **Изоляция**: SQLite in-memory базы данных
- **Фреймворк**: pytest + pytest-asyncio
- **Покрытие**: 100% для core functionality
- **Категории**: Аутентификация (9 тестов), Проекты (8 тестов)

### База данных
```bash
make migrate        # Применить все миграции
make migration MSG='описание'  # Создать новую миграцию
make migrate-down   # Откатить последнюю миграцию
make reset-db       # Полный сброс и пересоздание БД
make db-shell       # Подключиться к PostgreSQL
```

### Docker
```bash
make docker-build   # Собрать Docker образ
make docker-up      # Запустить контейнеры
make docker-down    # Остановить контейнеры
make docker-logs    # Посмотреть логи контейнеров
```

---

## 🏗️ Структура проекта

### Директории

```
app/
├── api/                    # API роутеры
│   └── v1/               # Версия 1 API
│       ├── auth.py       # Аутентификация
│       ├── users.py      # Пользователи
│       ├── projects.py   # Проекты
│       ├── tasks.py      # Задачи
│       ├── github.py     # GitHub OAuth
│       └── api.py        # Базовые API эндпоинты
├── core/                  # Основные компоненты
│   ├── config.py         # Конфигурация
│   ├── database.py       # База данных
│   ├── security.py       # Безопасность
│   └── redis.py          # Redis
├── models/                # SQLAlchemy модели
│   ├── base.py           # Базовая модель
│   ├── user.py           # Пользователь
│   ├── project.py        # Проект
│   ├── task.py           # Задача
│   ├── sprint.py         # Спринт
│   └── time_entry.py     # Временные записи
├── schemas/               # Pydantic схемы
│   ├── auth.py          # Аутентификация
│   ├── user.py          # Пользователь
│   ├── project.py       # Проект
│   └── task.py          # Задача
├── services/              # Бизнес-логика
├── auth/                  # Аутентификация
│   ├── service.py       # Сервис аутентификации
│   └── dependencies.py  # Зависимости
└── websocket/             # WebSocket
```

---

## 🛠️ Разработка

### Основные команды

```bash
# Установка зависимостей
make install

# Запуск в режиме разработки
make dev

# Запуск тестов
make test

# Проверка кода
make lint

# Форматирование кода
make format

# Создание миграции
make migrate MSG="описание изменений"

# Применение миграций
make migrate-apply
```

### Работа с Docker

```bash
# Запуск всех сервисов
make docker-up

# Остановка сервисов
make docker-down

# Просмотр логов
make docker-logs

# Запуск с инструментами разработки
make docker-tools
```

### Работа с базой данных

```bash
# Подключение к PostgreSQL
make db-shell

# Подключение к Redis
make redis-shell

# Переинициализация БД
make reset-db
```

---

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты
make test

# С покрытием
make test-cov

# Быстрый запуск
make test-fast
```

### Структура тестов

```
tests/
├── conftest.py           # Фикстуры pytest
├── test_auth.py         # Тесты аутентификации
├── test_projects.py     # Тесты проектов
├── test_tasks.py        # Тесты задач
└── e2e/                 # E2E тесты
```

### Написание тестов

```python
# Пример теста
async def test_create_project(client: AsyncClient, test_user_data: dict):
    # Создание пользователя
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    token = response.json()["access_token"]

    # Создание проекта
    headers = {"Authorization": f"Bearer {token}"}
    project_data = {"name": "Test Project"}

    response = await client.post("/api/v1/projects/", json=project_data, headers=headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Test Project"
```

---

## 📝 Код стиль и качество

### Инструменты

- **Black** - форматирование кода (line-length 88)
- **Ruff** - линтинг и сортировка импортов
- **MyPy** - проверка типов
- **Bandit** - проверка безопасности
- **Pytest** - тестирование с SQLite изоляцией

### Правила

1. **Форматирование**: Используйте Black с line-length 88
2. **Импорты**: Сортируйте с ruff
3. **Типы**: Добавляйте type hints для всех функций
4. **Тесты**: Пишите тесты на новый функционал
5. **Документация**: Добавляйте docstrings на русском языке
6. **Обработка ошибок**: Используйте `raise ... from err` для цепочки исключений
7. **UUID**: Конвертируйте строковые UUID в объекты UUID в API endpoints

### Pre-commit hooks
Автоматическая проверка при коммите:
- Форматирование Black
- Линтинг Ruff
- Проверка типов MyPy
- Безопасность Bandit
- Удаление trailing whitespace

### Пример кода

```python
from typing import List, Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse


class UserService:
    """Сервис для работы с пользователями"""

    async def create_user(
        self,
        user_data: UserCreate,
        db: AsyncSession
    ) -> UserResponse:
        """
        Создание нового пользователя

        Args:
            user_data: Данные для создания пользователя
            db: Сессия базы данных

        Returns:
            UserResponse: Созданный пользователь
        """
        # Реализация...
        pass
```

---

## 🔧 Конфигурация

### Переменные окружения

Скопируйте `.env.example` в `.env`:

```bash
cp .env.example .env
```

### Основные настройки

```bash
# База данных
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/timeto_do_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Безопасность
SECRET_KEY=your-super-secret-key
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Приложение
DEBUG=True
CORS_ORIGINS=["http://localhost:3000"]
```

---

## 🚀 Развертывание

### Локальное развертывание

```bash
# Полная настройка
make setup-dev

# Запуск
make dev
```

### Production развертывание

```bash
# Сборка Docker образов
make docker-build

# Запуск в production режиме
docker-compose up -d
```

Подробности в [DEPLOYMENT.md](./DEPLOYMENT.md).

---

## 🔄 Git workflow

### Ветки

- `main` - основная ветка (production)
- `develop` - ветка разработки
- `feature/*` - функциональные ветки
- `hotfix/*` - исправления

### Коммиты

Используйте conventional commits:

```
feat: добавление Kanban доски
fix: исправление аутентификации
docs: обновление документации
test: добавление тестов
refactor: рефакторинг сервиса
```

### Pull Request

1. Создайте ветку от `develop`
2. Внесите изменения
3. Добавьте тесты
4. Создайте Pull Request
5. Дождитесь ревью и мерджа

---

## 🐛 Отладка

### Логирование

```python
import logging

logger = logging.getLogger(__name__)

async def some_function():
    logger.info("Начало выполнения функции")
    try:
        # Код
        logger.info("Функция выполнена успешно")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        raise
```

### Отладка в VS Code

Создайте `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/app/main.py",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```

---

## 📚 Полезные ресурсы

### Документация

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [Pydantic](https://pydantic-docs.helpmanual.io/)
- [Alembic](https://alembic.sqlalchemy.org/)

### Инструменты

- [Docker](https://docs.docker.com/)
- [PostgreSQL](https://www.postgresql.org/docs/)
- [Redis](https://redis.io/documentation)
- [GitHub Actions](https://docs.github.com/en/actions)

---

## 🤝 Участие в разработке

1. Изучите архитектуру проекта
2. Выберите задачу из [development plan](./development-plan-decomposed.md)
3. Создайте ветку
4. Реализуйте функционал с тестами
5. Отправьте Pull Request

### Code Review

При ревью обращайте внимание на:
- Соответствие код стилю
- Наличие тестов
- Производительность
- Безопасность
- Документацию

---

## 🚀 Performance Testing (P1 - High Priority)

### Locust - Нагрузочное тестирование

**Установка:**
```bash
pip install locust
```

**Создание теста нагрузки:**
```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class TimeToDoUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Аутентификация пользователя"""
        response = self.client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def view_projects(self):
        """Просмотр проектов (самая частая операция)"""
        self.client.get("/api/v1/projects/", headers=self.headers)

    @task(2)
    def view_tasks(self):
        """Просмотр задач"""
        self.client.get("/api/v1/tasks/", headers=self.headers)

    @task(1)
    def create_project(self):
        """Создание проекта"""
        self.client.post("/api/v1/projects/",
                        json={"name": f"Load Test Project {self.environment.parsed_options.num_users}"},
                        headers=self.headers)
```

**Запуск нагрузочного тестирования:**
```bash
# Веб-интерфейс
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Командная строка
locust -f tests/performance/locustfile.py --headless \
       --users=100 --spawn-rate=10 --run-time=60s \
       --host=http://localhost:8000
```

### pytest-benchmark - Микро-бенчмарки

**Установка:**
```bash
pip install pytest-benchmark
```

**Пример бенчмарка:**
```python
# tests/performance/test_benchmarks.py
import pytest
from app.services.project_service import ProjectService
from app.schemas.project import ProjectCreate

@pytest.mark.benchmark
class TestProjectPerformance:

    def test_create_project_performance(self, benchmark, db_session):
        """Тест производительности создания проекта"""
        service = ProjectService(db_session)
        project_data = ProjectCreate(name="Benchmark Project")

        result = benchmark(service.create_project, project_data)
        assert result.name == "Benchmark Project"

    def test_get_projects_performance(self, benchmark, db_session, async_user_factory):
        """Тест производительности получения проектов"""
        service = ProjectService(db_session)

        # Создаем тестовые данные
        user = await async_user_factory()

        result = benchmark(service.get_user_projects, user.id)
        assert isinstance(result, list)
```

**Запуск бенчмарков:**
```bash
# Запуск всех бенчмарков
pytest tests/performance/test_benchmarks.py --benchmark-only

# Сравнение с предыдущими результатами
pytest tests/performance/test_benchmarks.py --benchmark-only --benchmark-compare

# Генерация отчета
pytest tests/performance/test_benchmarks.py --benchmark-only --benchmark-json=benchmark.json
```

**Интеграция в CI/CD:**
```yaml
# .github/workflows/performance.yml
- name: Run performance tests
  run: |
    pytest tests/performance/test_benchmarks.py --benchmark-only --benchmark-json=benchmark.json

- name: Upload benchmark results
  uses: benchmark-action/github-action-benchmark@v1
  with:
    tool: 'pytest'
    output-file-path: benchmark.json
```

---

## 🆘 Поддержка

Если у вас есть вопросы:

1. Проверьте [FAQ](./FAQ.md)
2. Поищите в [Issues](https://github.com/yourusername/time_to_do/issues)
3. Создайте новый Issue
4. Обратитесь в Discord

---

**Happy coding! 🚀**
