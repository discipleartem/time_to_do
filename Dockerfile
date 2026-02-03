# Multi-stage build для оптимизации размера
FROM python:3.13-slim as builder

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установка poetry
RUN pip install poetry==1.7.1

# Копирование файлов зависимостей
COPY pyproject.toml poetry.lock* ./

# Конфигурация poetry
RUN poetry config virtualenvs.create false

# Установка зависимостей
RUN poetry install --only=main --no-dev

# Production stage
FROM python:3.13-slim as production

# Создание пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Установка runtime зависимостей
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копирование зависимостей из builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Установка рабочей директории
WORKDIR /app

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

# Запуск приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
