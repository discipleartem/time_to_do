# Makefile for Time to DO

.PHONY: setup dev test lint clean migrate shell db-shell docker-dev docker-prod docker-build docker-clean help

# 🚀 Установка и настройка
setup:
	@echo "🚀 Полная настройка проекта с Python 3.13..."
	./scripts/reinstall-deps.sh

# 🛠️ Разработка
dev:
	@echo "🚀 Запуск сервера разработки..."
	.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 🧪 Тестирование
test:
	@echo "🧪 Запуск всех тестов с покрытием кода..."
	.venv/bin/pytest --cov=app --cov-report=html --cov-report=term -v

# 🔍 Проверка кода
lint:
	@echo "🔍 Полная проверка кода..."
	.venv/bin/black --target-version=py313 app/
	.venv/bin/ruff check --fix app/
	.venv/bin/mypy app/
	.venv/bin/bandit -r app/

# 🗄️ Работа с базой данных
migrate:
	@echo "🔄 Применение миграций..."
	.venv/bin/alembic upgrade head

migrate-down:
	@echo "⬇️ Откат миграций..."
	.venv/bin/alembic downgrade -1

migration:
	@echo "📝 Создание новой миграции..."
	@if [ -z "$(MSG)" ]; then \
		echo "❌ Использование: make migration MSG='описание миграции'"; \
		exit 1; \
	fi
	.venv/bin/alembic revision --autogenerate -m "$(MSG)"

reset-db:
	@echo " Сброс базы данных..."
	.venv/bin/alembic downgrade base
	.venv/bin/alembic upgrade head

# Docker - Простые команды
docker-dev:
	@echo " Запуск для разработки..."
	docker-compose --profile dev up -d

docker-prod:
	@echo " Запуск для production..."
	docker-compose --profile prod up -d

docker-stop:
	@echo " Остановка контейнеров..."
	docker-compose down

docker-logs:
	@echo "📋 Логи контейнеров..."
	docker-compose logs -f

docker-build:
	@echo "🔨 Сборка Docker образов..."
	docker-compose build

docker-clean:
	@echo "🗑️ Удаление Docker образов и контейнеров..."
	docker-compose down --rmi all --volumes --remove-orphans
	docker system prune -f
	docker volume prune -f

# Полезные утилиты
shell:
	@echo " Запуск Python shell..."
	.venv/bin/python -i -c "from app.core.database import get_db_session; from app.models import *; print(' Ready to work with database!')"

db-shell:
	@echo " PostgreSQL shell..."
	docker-compose exec postgres psql -U postgres -d timeto_do

redis-shell:
	@echo " Redis shell..."
	docker-compose exec redis redis-cli

# Очистка
clean:
	@echo " Очистка..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/

# Помощь
help:
	@echo " Доступные команды:"
	@echo ""
	@echo " Установка:"
	@echo "   make setup     - Полная настройка проекта с Python 3.13"
	@echo ""
	@echo " Разработка:"
	@echo "   make dev       - Запуск сервера разработки"
	@echo "   make shell     - Python shell с моделями"
	@echo "   make db-shell  - PostgreSQL shell"
	@echo "   make redis-shell - Redis shell"
	@echo ""
	@echo " Тестирование:"
	@echo "   make test      - Запуск всех тестов с покрытием кода"
	@echo ""
	@echo " Код:"
	@echo "   make lint      - Полная проверка (black + ruff + mypy + bandit)"
	@echo ""
	@echo " База данных:"
	@echo "   make migrate   - Применить миграции"
	@echo "   make migration MSG='описание' - Создать новую миграцию"
	@echo "   make reset-db  - Сброс базы данных"
	@echo ""
	@echo " Docker:"
	@echo "   make docker-dev   - Запуск для разработки (с БД и Redis)"
	@echo "   make docker-prod  - Запуск для production (только приложение)"
	@echo "   make docker-stop  - Остановка всех контейнеров"
	@echo "   make docker-logs  - Просмотр логов"
	@echo "   make docker-build - Сборка Docker образов"
	@echo "   make docker-clean - Удаление образов и контейнеров"
	@echo ""
	@echo " Утилиты:"
	@echo "   make clean     - Очистка"
	@echo "   make help      - Эта справка"
