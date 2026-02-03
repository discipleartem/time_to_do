# Руководство по тестированию Time to DO

## 🧪 Обзор

В проекте Time to DO используется комплексная система тестирования, включающая unit-тесты, интеграционные тесты и тесты сервисного слоя. Все тесты написаны с использованием **pytest** и **pytest-asyncio** для поддержки асинхронного кода FastAPI.

---

## 🏗️ Архитектура тестирования

### Структура директории тестов

```
tests/
├── conftest.py              # Фикстуры и общая конфигурация
├── test_auth.py             # Тесты аутентификации
├── test_projects.py         # Тесты управления проектами
├── test_tasks.py            # Тесты управления задачами
├── test_users.py            # Тесты управления пользователями
├── test_time_entries.py     # Тесты отслеживания времени
├── test_services.py         # Тесты сервисного слоя
├── test_integration.py      # Интеграционные тесты
└── e2e/                     # E2E тесты (в будущем)
```

### Типы тестов

1. **Unit-тесты** - Тестирование отдельных функций и классов
2. **Интеграционные тесты** - Тестирование взаимодействия компонентов
3. **API-тесты** - Тестирование HTTP эндпоинтов
4. **Сервисные тесты** - Тестирование бизнес-логики

---

## 🚀 Быстрый старт

### Запуск всех тестов

```bash
# Запуск всех тестов
make test

# Запуск с покрытием кода
make test-cov

# Запуск только unit-тестов
pytest -m unit

# Запуск только интеграционных тестов
pytest -m integration

# Запуск конкретного файла тестов
pytest tests/test_auth.py

# Запуск с детальным выводом
pytest -v -s
```

### Фильтрация тестов

```bash
# Запуск тестов по ключевому слову
pytest -k "test_create_user"

# Запуск тестов по маркеру
pytest -m "not slow"  # Исключить медленные тесты

# Запуск тестов для конкретного модуля
pytest tests/test_tasks.py::TestTasks::test_create_task
```

---

## 🔧 Конфигурация тестов

### pytest.ini

Конфигурация pytest находится в `pyproject.toml`:

```toml
[tool.pytest.ini_options]
minversion = "6.0"
addopts = "-ra -q --strict-markers --strict-config"
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

### Тестовая база данных

Для изоляции тестов используется **SQLite in-memory** база данных:

```python
# Тестовая база данных (SQLite для изоляции)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
```

Это обеспечивает:
- ✅ Быстрое выполнение тестов
- ✅ Полную изоляцию между тестами
- ✅ Автоматическую очистку после тестов

---

## 📝 Написание тестов

### Структура теста

```python
import pytest
from httpx import AsyncClient

class TestExample:
    """Класс тестов с общими фикстурами"""

    async def test_example(self, client: AsyncClient, test_user_data: dict):
        """Пример теста"""
        # Подготовка
        headers = await self.get_auth_headers(client, test_user_data)

        # Действие
        response = await client.post("/api/v1/endpoint", json=data, headers=headers)

        # Проверка
        assert response.status_code == 200
        result = response.json()
        assert result["field"] == "expected_value"
```

### Фикстуры

Основные фикстуры доступны в `conftest.py`:

```python
@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    """Тестовый HTTP клиент"""

@pytest.fixture
def test_user_data() -> dict:
    """Данные тестового пользователя"""

@pytest.fixture
def test_project_data() -> dict:
    """Данные тестового проекта"""

@pytest.fixture
def test_task_data() -> dict:
    """Данные тестовой задачи"""
```

### Асинхронные тесты

Все тесты должны быть асинхронными:

```python
async def test_async_example(self, client: AsyncClient):
    """Асинхронный тест"""
    response = await client.get("/api/v1/endpoint")
    assert response.status_code == 200
```

---

## 📊 Покрытие кода

### Генерация отчета

```bash
# Генерация HTML отчета
pytest --cov=app --cov-report=html

# Отчет в терминале
pytest --cov=app --cov-report=term-missing

# Комбинированный отчет
pytest --cov=app --cov-report=html --cov-report=term
```

### Целевые показатели

- **Общее покрытие**: ≥ 80%
- **Core functionality**: ≥ 95%
- **API endpoints**: ≥ 90%

### Исключения из покрытия

```toml
[tool.coverage.run]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
]
```

---

## 🏷️ Маркеры тестов

### Доступные маркеры

```python
@pytest.mark.unit          # Unit-тесты
@pytest.mark.integration   # Интеграционные тесты
@pytest.mark.slow         # Медленные тесты
```

### Использование маркеров

```python
@pytest.mark.integration
async def test_full_workflow(self, client: AsyncClient):
    """Интеграционный тест полного рабочего процесса"""
    pass

@pytest.mark.slow
async def test_performance_test(self, client: AsyncClient):
    """Медленный тест производительности"""
    pass
```

---

## 🔍 Отладка тестов

### Детальный вывод

```bash
# Показать вывод print() в тестах
pytest -s

# Детальный вывод с traceback
pytest -v --tb=long

# Остановка при первом неудачном тесте
pytest -x

# Запуск с pdb для отладки
pytest --pdb
```

### Логирование в тестах

```python
import logging

logger = logging.getLogger(__name__)

async def test_with_logging(self, client: AsyncClient):
    """Тест с логированием"""
    logger.info("Начало выполнения теста")

    # Код теста

    logger.info("Тест выполнен успешно")
```

### Тестирование ошибок

```python
import pytest

async def test_error_handling(self, client: AsyncClient):
    """Тест обработки ошибок"""

    # Проверка статуса ошибки
    response = await client.post("/api/v1/invalid", json={})
    assert response.status_code == 404

    # Проверка исключения
    with pytest.raises(ValueError):
        some_function_that_raises()
```

---

## 📋 Примеры тестов

### Тест API эндпоинта

```python
async def test_create_project(self, client: AsyncClient, test_user_data: dict, test_project_data: dict):
    """Тест создания проекта"""
    # Аутентификация
    headers = await self.get_auth_headers(client, test_user_data)

    # Создание проекта
    response = await client.post("/api/v1/projects/", json=test_project_data, headers=headers)

    # Проверки
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == test_project_data["name"]
    assert "id" in data
    assert "created_at" in data
```

### Тест сервисного слоя

```python
async def test_create_user_service(self, user_service: UserService, test_user_data: dict):
    """Тест создания пользователя через сервис"""
    # Создание пользователя
    user = await user_service.create_user(test_user_data)

    # Проверки
    assert user.email == test_user_data["email"]
    assert user.hashed_password is not None
    assert user.hashed_password != test_user_data["password"]
```

### Интеграционный тест

```python
@pytest.mark.integration
async def test_complete_workflow(self, client: AsyncClient, test_user_data: dict):
    """Тест полного рабочего процесса"""
    # 1. Регистрация
    register_response = await client.post("/api/v1/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Создание проекта
    project_response = await client.post("/api/v1/projects/", json=project_data, headers=headers)
    project = project_response.json()

    # 3. Создание задачи
    task_data = {"title": "Test Task", "project_id": project["id"]}
    task_response = await client.post("/api/v1/tasks/", json=task_data, headers=headers)

    # 4. Проверки
    assert task_response.status_code == 200
    assert task_response.json()["title"] == "Test Task"
```

---

## 🛠️ Советы и лучшие практики

### 1. Изоляция тестов

```python
# ✅ Хорошо: уникальные данные для каждого теста
async def test_user_creation(self, client: AsyncClient):
    unique_id = str(uuid.uuid4())[:8]
    user_data = {
        "email": f"test_{unique_id}@example.com",
        "username": f"test_user_{unique_id}",
    }

# ❌ Плохо: жестко закодированные данные
async def test_user_creation(self, client: AsyncClient):
    user_data = {"email": "test@example.com"}  # Может конфликтовать
```

### 2. Атомарность тестов

```python
# ✅ Хорошо: каждый тест независим
async def test_create_user(self, client: AsyncClient):
    # Создаем пользователя в этом тесте
    pass

async def test_update_user(self, client: AsyncClient):
    # Создаем нового пользователя для этого теста
    pass

# ❌ Плохо: зависимость от других тестов
async def test_create_user(self, client: AsyncClient):
    # Создаем пользователя для других тестов
    pass
```

### 3. Понятные имена тестов

```python
# ✅ Хорошо: описательное имя
async def test_create_project_with_valid_data_should_return_201(self, client: AsyncClient):
    pass

async def test_create_project_with_duplicate_name_should_return_400(self, client: AsyncClient):
    pass

# ❌ Плохо: непонятное имя
async def test_project_1(self, client: AsyncClient):
    pass
```

### 4. Использование фикстур

```python
# ✅ Хорошо: переиспользование фикстур
async def test_create_project(self, client: AsyncClient, test_project_data: dict):
    response = await client.post("/api/v1/projects/", json=test_project_data, headers=headers)

# ❌ Плохо: дублирование данных
async def test_create_project(self, client: AsyncClient):
    project_data = {
        "name": "Test Project",
        "description": "Test Description",
        # ...
    }
```

### 5. Правильные утверждения (assertions)

```python
# ✅ Хорошо: конкретные проверки
assert response.status_code == 200
assert data["id"] is not None
assert data["name"] == expected_name

# ❌ Плохо: общие проверки
assert response.ok  # Не достаточно конкретно
assert data  # Проверяет только наличие данных
```

---

## 🚨 Распространенные проблемы

### 1. Проблемы с асинхронностью

```python
# ❌ Неправильно: синхронный вызов в асинхронном тесте
def test_sync_method(self):
    result = some_sync_function()

# ✅ Правильно: асинхронный вызов
async def test_async_method(self):
    result = await some_async_function()
```

### 2. Проблемы с базой данных

```python
# ❌ Неправильно: использование реальной базы данных
async def test_with_real_db(self):
    # Использует реальную PostgreSQL

# ✅ Правильно: использование тестовой базы данных
async def test_with_test_db(self, db_session: AsyncSession):
    # Использует SQLite in-memory
```

### 3. Проблемы с авторизацией

```python
# ❌ Неправильно: жестко закодированный токен
headers = {"Authorization": "Bearer hardcoded_token"}

# ✅ Правильно: получение токена через фикстуру
headers = await self.get_auth_headers(client, test_user_data)
```

---

## 📈 Производительность тестов

### Оптимизация скорости

1. **Используйте in-memory базу данных** для быстрых тестов
2. **Мокируйте внешние сервисы** (Redis, email, etc.)
3. **Параллельный запуск тестов** с `pytest-xdist`
4. **Кэширование фикстур** с `scope="session"`

```bash
# Параллельный запуск
pytest -n auto

# Только быстрые тесты
pytest -m "not slow"
```

### Мониторинг производительности

```bash
# Показать медленные тесты
pytest --durations=10

# Профилирование тестов
pytest --profile
```

---

## 🔮 Будущее тестирования

### Планируемые улучшения

1. **E2E тесты** с Playwright/Selenium
2. **Нагрузочные тесты** с Locust
3. **Контрактные тесты** с Pact
4. **Визуальное тестирование** с Percy
5. **Тесты безопасности** с Bandit

### CI/CD интеграция

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 📚 Полезные ресурсы

### Документация

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#testing-asyncio)

### Инструменты

- **pytest** - основной фреймворк тестирования
- **pytest-asyncio** - асинхронные тесты
- **pytest-cov** - покрытие кода
- **pytest-xdist** - параллельный запуск
- **pytest-mock** - мокирование объектов
- **httpx** - асинхронный HTTP клиент для тестов

### Лучшие практики

- [Pytest Best Practices](https://docs.pytest.org/en/stable/best-practices.html)
- [FastAPI Testing Best Practices](https://fastapi.tiangolo.com/advanced/testing-events/)
- [Python Testing Anti-Patterns](https://docs.pytest.org/en/stable/explanation/goodpractices.html)

---

**Happy testing! 🧪**

Если у вас есть вопросы по тестированию, обращайтесь к документации или создайте Issue в проекте.
