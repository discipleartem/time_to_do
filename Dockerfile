# Universal Dockerfile for Time to DO
# Supports development, production, and render environments via build-arg

ARG ENV=development

# Builder stage
FROM python:3.13-slim as builder

# Установка зависимостей для сборки
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установка Poetry
RUN pip install poetry==1.7.1

# Копирование файлов зависимостей
COPY pyproject.toml poetry.lock* ./

# Конфигурация Poetry
RUN poetry config virtualenvs.create false

# Установка зависимостей в зависимости от окружения
RUN if [ "$ENV" = "development" ]; then \
        poetry install; \
    else \
        poetry install --only=main --no-dev; \
    fi

# Production stage
FROM python:3.13-slim as production

ARG ENV=development

# Установка runtime зависимостей
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Создание пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Установка рабочей директории
WORKDIR /app

# Копирование зависимостей из builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копирование приложения
COPY . .

# Создание необходимых директорий
RUN mkdir -p uploads logs \
    && chown -R appuser:appuser /app

# Переключение на пользователя
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Запуск приложения в зависимости от окружения
CMD if [ "$ENV" = "development" ]; then \
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload; \
    else \
        uvicorn app.main:app --host 0.0.0.0 --port 8000; \
    fi
