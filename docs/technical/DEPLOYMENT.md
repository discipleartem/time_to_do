# Развертывание Time to DO

## 🚀 Обзор

Time to DO развертывается на Render.com с использованием Docker контейнеров. Проект поддерживает автоматический CI/CD через GitHub Actions.

---

## 🏗️ Архитектура развертывания

### Production окружение
```
┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │      CDN        │
│   (Render)      │    │   (Render)      │
└─────────┬───────┘    └─────────────────┘
          │
┌─────────▼───────┐    ┌─────────────────┐
│  FastAPI App    │    │   WebSocket     │
│  (Render)       │    │   (Render)      │
└─────────┬───────┘    └─────────────────┘
          │
┌─────────▼───────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis        │
│   (Render)      │    │   (Render)      │
└─────────────────┘    └─────────────────┘
```

---

## 🐳 Docker конфигурация

### Dockerfile
```dockerfile
# Multi-stage build для оптимизации
FROM python:3.13-slim as builder

# Установка зависимостей
RUN apt-get update && apt-get install -y gcc postgresql-client
RUN pip install poetry==1.7.1
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false
RUN poetry install --only=main --no-dev

# Production stage
FROM python:3.13-slim as production
RUN apt-get update && apt-get install -y postgresql-client curl
RUN groupadd -r appuser && useradd -r -g appuser appuser
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
WORKDIR /app
COPY . .
RUN mkdir -p uploads logs
RUN chown -R appuser:appuser /app
USER appuser
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=False
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

---

## 🌐 Render.com развертывание

### Автоматический деплой (рекомендуется)

Render.com автоматически деплоит приложение при push в GitHub:

1. **Подключение GitHub репозитория**
   - В Render dashboard: New → Web Service
   - Connect GitHub репозиторий
   - Выберите ветку `main`

2. **Настройка Web Service**
   ```yaml
   # render.yaml (в корне проекта)
   services:
     - type: web
       name: timetodo-api
       env: python
       buildCommand: pip install -e .
       startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
       healthCheckPath: /health
       autoDeploy: true
       envVars:
         - key: DATABASE_URL
           sync: false
         - key: REDIS_URL
           sync: false
         - key: SECRET_KEY
           sync: false
   ```

3. **Автоматический деплой**
   - Push в `main` → автоматический деплой
   - Render автоматически собирает и запускает
   - Статус виден в dashboard

### Ручной деплой (через dashboard)

1. **Manual Deploy**
   - Render dashboard → Web Service
   - Click "Manual Deploy"
   - Выберите коммит
   - Deploy

2. **Rollback**
   - Dashboard → Deploys
   - Выберите предыдущий успешный деплой
   - Click "Redeploy"

### PostgreSQL конфигурация

#### Базовые настройки
- **Name**: `timetodo-db`
- **Database Name**: `timetodo`
- **User**: `postgres`
- **Version**: `15`
- **Instance Type**: `Free` (7.5GB)

#### Подключение
```bash
# После создания получите connection string
DATABASE_URL=postgresql://postgres:password@host:5432/timetodo
```

### Redis конфигурация

#### Базовые настройки
- **Name**: `timetodo-redis`
- **Version**: `7`
- **Instance Type**: `Free`

---

## 🔄 CI/CD Pipeline

### GitHub Actions workflow

```yaml
name: Deploy to Render

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: timeto_do_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .

    - name: Run tests
      env:
        DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/timeto_do_test
        REDIS_URL: redis://localhost:6379/0
        SECRET_KEY: test-secret-key
      run: |
        pytest --cov=app --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  lint:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .

    - name: Run linting
      run: |
        ruff check app/
        mypy app/
        black --check app/

  deploy:
    needs: [test, lint]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - name: Deploy to Render
      run: |
        curl -X POST \
          -H "Authorization: Bearer ${{ secrets.RENDER_API_KEY }}" \
          -H "Content-Type: application/json" \
          -d '{"serviceId": "${{ secrets.RENDER_SERVICE_ID }}"}' \
          https://api.render.com/v1/services/${{ secrets.RENDER_SERVICE_ID }}/deploys
```

### Secrets в GitHub

```bash
# Добавить в Repository Settings > Secrets
RENDER_API_KEY=your_render_api_key
RENDER_SERVICE_ID=your_service_id
```

---

## 🗄️ Миграции базы данных

### Автоматические миграции

```dockerfile
# Добавить в Dockerfile
RUN alembic upgrade head
```

### Ручные миграции

```bash
# Локально
alembic upgrade head

# В production через Render Console
# 1. Connect to service
# 2. Run: alembic upgrade head
```

### Создание миграций

```bash
# Создание новой миграции
alembic revision --autogenerate -m "Add new feature"

# Применение миграции
alembic upgrade head

# Откат миграции
alembic downgrade -1
```

---

## 🔧 Мониторинг и логирование

### Health checks

```python
# app/main.py
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": settings.VERSION
    }

@app.get("/health/detailed")
async def detailed_health_check():
    # Проверка БД
    try:
        await db.execute("SELECT 1")
        db_status = "healthy"
    except:
        db_status = "unhealthy"

    # Проверка Redis
    try:
        await redis.ping()
        redis_status = "healthy"
    except:
        redis_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy",
        "database": db_status,
        "redis": redis_status,
        "timestamp": datetime.utcnow()
    }
```

### Логирование

```python
# app/core/logging.py
import logging
import sys
from pathlib import Path

def setup_logging():
    # Создаем директорию для логов
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Настройка форматирования
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # File handler
    file_handler = logging.FileHandler(log_dir / "app.log")
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
```

### Метрики

```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Response

# Метрики
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    REQUEST_DURATION.observe(duration)

    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

## 🔒 Безопасность в production

### SSL/TLS
- Автоматически настраивается на Render.com
- Redirect с HTTP на HTTPS
- HSTS заголовки

### Переменные окружения
```bash
# Production переменные
DEBUG=False
SECRET_KEY=your-super-secure-secret-key
ALLOWED_HOSTS=["your-app.onrender.com"]
CORS_ORIGINS=["https://your-app.onrender.com"]
```

### Rate limiting
```python
# app/middleware/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/v1/auth/login")
@limiter.limit("5/minute")
async def login(request: Request):
    pass
```

---

## 🚀 Zero-downtime deployment

### Стратегия развертывания

1. **Blue-Green Deployment**
   - Два идентичных окружения
   - Переключение трафика
   - Откат при проблемах

2. **Rolling Updates**
   - Постепенное обновление инстансов
   - Health checks во время развертывания
   - Автоматический откат

### Render автоматизация

Render автоматически:
- Создает новый контейнер с новым кодом
- Проверяет health check
- Переключает трафик
- Удаляет старый контейнер

---

## 📊 Масштабирование

### Вертикальное масштабирование
```yaml
# render.yaml (для Render)
services:
  - type: web
    name: timetodo-api
    env: python
    plan: standard  # Изменить на standard для production
    healthCheckPath: /health
    autoDeploy: true
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: REDIS_URL
        sync: false
```

### Горизонтальное масштабирование
```python
# app/core/config.py
class Settings:
    # Настройки для масштабирования
    DATABASE_POOL_SIZE = 20
    DATABASE_MAX_OVERFLOW = 30
    REDIS_CONNECTION_POOL_SIZE = 50
```

---

## 🔄 Backup и восстановление

### PostgreSQL backup

```bash
# Автоматический backup (через cron)
0 2 * * * pg_dump -h $DB_HOST -U $DB_USER $DB_NAME > backup_$(date +%Y%m%d).sql

# Восстановление
psql -h $DB_HOST -U $DB_USER $DB_NAME < backup_20240101.sql
```

### Redis backup

```bash
# Backup Redis
redis-cli --rdb backup.rdb

# Восстановление
redis-cli --rdb backup.rdb
```

---

## 🐛 Troubleshooting

### Общие проблемы

#### 1. Application не запускается
```bash
# Проверка логов
render logs

# Локальная отладка
docker-compose up --build
```

#### 2. Database connection errors
```bash
# Проверка connection string
echo $DATABASE_URL

# Тест подключения
python -c "
import asyncpg
await asyncpg.connect('$DATABASE_URL')
print('Connection successful')
"
```

#### 3. Redis connection errors
```bash
# Тест Redis
redis-cli -u $REDIS_URL ping
```

### Мониторинг

```bash
# System metrics
render dashboard

# Application logs
render logs <service-name>

# Database metrics
# PostgreSQL dashboard в Render
```

---

## 📋 Deployment checklist

### Pre-deployment
- [ ] Все тесты проходят
- [ ] Code review завершен
- [ ] Миграции протестированы
- [ ] Переменные окружения настроены
- [ ] Backup создан

### Post-deployment
- [ ] Health checks проходят
- [ ] API работает корректно
- [ ] WebSocket подключается
- [ ] Мониторинг настроен
- [ ] Логи проверены

### Rollback plan
- [ ] Предыдущая версия доступна
- [ ] Database rollback готов
- [ ] Команда для отката известна
- [ ] Уведомления настроены

---

Эта инструкция обеспечивает надежное развертывание Time to DO в production окружении.
