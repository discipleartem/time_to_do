# Makefile for Time to DO

.PHONY: setup dev dev-frontend test test-setup lint clean migrate migrate-down migration reset-db docker-dev docker-prod docker-up docker-stop docker-restart docker-logs docker-build docker-build-clean docker-images docker-clean render-deploy render-status shell db-shell redis-shell help

# =============================================================================
# 🚀 УСТАНОВКА И НАСТРОЙКА
# =============================================================================

setup:
	@echo "🚀 Полная настройка проекта с Python 3.13..."
	./scripts/reinstall-deps.sh

# =============================================================================
# 🛠️ РАЗРАБОТКА
# =============================================================================

dev:
	@echo "🚀 Запуск сервера разработки..."
	.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "🎨 Запуск сервера с фронтендом..."
	.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
	@echo "🌐 Приложение доступно на http://localhost:8000"
	@echo "📱 Дашборд: http://localhost:8000/"
	@echo "📋 Kanban: http://localhost:8000/projects/{id}/kanban"

shell:
	@echo "🐍 Запуск Python shell с моделями..."
	.venv/bin/python -i -c "from app.core.database import get_db_session; from app.models import *; print(' Ready to work with database!')"

db-shell:
	@echo "🗄️ PostgreSQL shell..."
	docker-compose exec postgres psql -U postgres -d timeto_do

redis-shell:
	@echo "🔴 Redis shell..."
	docker-compose exec redis redis-cli

# =============================================================================
# 🧪 ТЕСТИРОВАНИЕ
# =============================================================================

test:
	@echo "🧪 Запуск всех тестов с покрытием кода..."
	.venv/bin/pytest --cov=app --cov-report=html --cov-report=term -v

test-setup:
	@echo "🗄️ Создание тестовой базы данных..."
	createdb timeto_do_test || echo "База данных уже существует"
	@echo "🔄 Применение миграций для тестовой БД..."
	DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/timeto_do_test" .venv/bin/alembic upgrade head
	@echo "✅ Тестовая база данных готова"

# =============================================================================
# 🔍 КОД И КАЧЕСТВО
# =============================================================================

lint:
	@echo "🔍 Полная проверка кода..."
	.venv/bin/black --target-version=py313 app/
	.venv/bin/ruff check --fix app/
	.venv/bin/mypy app/
	.venv/bin/bandit -r app/

clean:
	@echo "🧹 Очистка временных файлов..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/

# =============================================================================
# 🗄️ БАЗА ДАННЫХ
# =============================================================================

# --- Локальные команды (для IDE разработки) ---
migrate-local:
	@echo "🔄 Применение миграций (локально)..."
	.venv/bin/alembic upgrade head

migrate-down-local:
	@echo "⬇️ Откат миграций (локально)..."
	.venv/bin/alembic downgrade -1

migration-local:
	@echo "📝 Создание новой миграции (локально)..."
	@if [ -z "$(MSG)" ]; then \
		echo "❌ Использование: make migration-local MSG='описание миграции'"; \
		exit 1; \
	fi
	.venv/bin/alembic revision --autogenerate -m "$(MSG)"

reset-db-local:
	@echo "🔄 Сброс базы данных (локально)..."
	.venv/bin/alembic downgrade base
	.venv/bin/alembic upgrade head

# --- Docker команды (для Docker разработки) ---
migrate:
	@echo "🔄 Применение миграций (Docker)..."
	docker exec timetodo_app_dev alembic upgrade head

migrate-down:
	@echo "⬇️ Откат миграций (Docker)..."
	docker exec timetodo_app_dev alembic downgrade -1

migration:
	@echo "📝 Создание новой миграции (Docker)..."
	@if [ -z "$(MSG)" ]; then \
		echo "❌ Использование: make migration MSG='описание миграции'"; \
		exit 1; \
	fi
	docker exec timetodo_app_dev alembic revision --autogenerate -m "$(MSG)"

reset-db:
	@echo "🔄 Сброс базы данных (Docker)..."
	docker exec timetodo_app_dev alembic downgrade base
	docker exec timetodo_app_dev alembic upgrade head

# =============================================================================
# 🐳 DOCKER КОНТЕЙНЕРЫ
# =============================================================================

# --- Запуск и управление ---
docker-dev:
	@echo "🚀 Запуск для разработки (dev профиль)..."
	docker-compose --profile dev up -d
	@echo "🌐 Приложение доступно на http://localhost:8000"

docker-prod:
	@echo "🚀 Запуск для production (prod профиль)..."
	docker-compose --profile prod up -d
	@echo "🌐 Приложение доступно на http://localhost:8000"

docker-up:
	@echo "🚀 Запуск контейнеров по умолчанию..."
	docker-compose up -d
	sleep 15
	@echo "✅ Docker контейнеры запущены"

docker-stop:
	@echo "🛑 Остановка всех контейнеров..."
	docker-compose down

docker-restart:
	@echo "🔄 Перезапуск всех контейнеров..."
	docker-compose restart

docker-logs:
	@echo "📋 Логи всех контейнеров..."
	docker-compose logs -f

# --- Сборка и оптимизация ---
docker-build:
	@echo "🔨 Сборка Docker образов..."
	docker-compose build
	@echo "🧹 Очистка dangling образов..."
	docker image prune -f

docker-build-clean:
	@echo "🔨 Сборка с полной очисткой..."
	docker-compose build --no-cache
	@echo "🗑️ Удаление всех неиспользуемых образов..."
	docker system prune -f --volumes

docker-images:
	@echo "📋 Просмотр Docker образов..."
	@if [ -z "$(COUNT)" ]; then \
		docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"; \
	else \
		echo "Показ последних $$COUNT образов:"; \
		docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | head -n $$((COUNT + 1)); \
	fi

docker-clean:
	@echo "🗑️ Удаление Docker образов и контейнеров..."
	docker-compose down --rmi all --volumes --remove-orphans
	docker system prune -f
	docker volume prune -f

docker-reset:
	@echo "🔄 Полный сброс Docker окружения..."
	docker-compose down --volumes --remove-orphans
	docker system prune -af --volumes
	docker volume prune -f
	@echo "✅ Docker окружение сброшено"

# =============================================================================
# 🚀 DEPLOYMENT
# =============================================================================

render-deploy:
	@echo "🚀 Подготовка к деплою на Render.com..."
	@echo "📋 Проверка зависимостей..."
	poetry install --only=main
	@echo "🧹 Очистка кэша Python..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	@echo "🔍 Проверка критичных файлов..."
	@if [ ! -f "render.yaml" ]; then \
		echo "❌ render.yaml не найден!"; \
		exit 1; \
	fi
	@if [ ! -f "pyproject.toml" ]; then \
		echo "❌ pyproject.toml не найден!"; \
		exit 1; \
	fi
	@echo "✅ Готово к деплою на Render.com!"
	@echo "📝 Следующие шаги:"
	@echo "   1. git add ."
	@echo "   2. git commit -m 'feat: обновление для production'"
	@echo "   3. git push origin main"
	@echo "   4. Проверить статус в Render.com Dashboard"

render-status:
	@echo "🔍 Проверка статуса деплоя..."
	@echo "📊 Откройте Render.com Dashboard для просмотра:"
	@echo "   - Logs: https://dashboard.render.com/web/timetodo-api/logs"
	@echo "   - Metrics: https://dashboard.render.com/web/timetodo-api/metrics"
	@echo "   - Events: https://dashboard.render.com/web/timetodo-api/events"

# =============================================================================
# 🔨 ПОМОЩЬ
# =============================================================================

help:
	@echo "🚀 Time to DO - Управление проектом"
	@echo ""
	@echo "=============================================================================="
	@echo " 🚀 УСТАНОВКА И НАСТРОЙКА"
	@echo "=============================================================================="
	@echo "   make setup          - Полная настройка проекта с Python 3.13"
	@echo ""
	@echo "=============================================================================="
	@echo " 🛠️ РАЗРАБОТКА"
	@echo "=============================================================================="
	@echo "   make dev            - Запуск сервера разработки"
	@echo "   make dev-frontend   - Запуск с фронтендом (Bootstrap 5)"
	@echo "   make shell          - Python shell с моделями"
	@echo "   make db-shell       - PostgreSQL shell"
	@echo "   make redis-shell    - Redis shell"
	@echo ""
	@echo "=============================================================================="
	@echo " 🧪 ТЕСТИРОВАНИЕ"
	@echo "=============================================================================="
	@echo "   make test           - Запуск всех тестов с покрытием кода"
	@echo "   make test-setup     - Создание тестовой базы данных"
	@echo ""
	@echo "=============================================================================="
	@echo " 🔍 КОД И КАЧЕСТВО"
	@echo "=============================================================================="
	@echo "   make lint           - Полная проверка кода (black + ruff + mypy + bandit)"
	@echo "   make clean          - Очистка временных файлов"
	@echo ""
	@echo "=============================================================================="
	@echo " 🗄️ БАЗА ДАННЫХ"
	@echo "=============================================================================="
	@echo "   make migrate-local      - Применение миграций (локально)"
	@echo "   make migrate-down-local - Откат миграций (локально)"
	@echo "   make migration-local MSG='описание' - Создание миграции (локально)"
	@echo "   make reset-db-local     - Сброс базы данных (локально)"
	@echo "   make migrate           - Применение миграций (Docker)"
	@echo "   make migrate-down      - Откат миграций (Docker)"
	@echo "   make migration MSG='описание' - Создание миграции (Docker)"
	@echo "   make reset-db           - Сброс базы данных (Docker)"
	@echo ""
	@echo "=============================================================================="
	@echo " 🐳 DOCKER КОНТЕЙНЕРЫ"
	@echo "=============================================================================="
	@echo "   make docker-dev     - Запуск для разработки (dev профиль)"
	@echo "   make docker-prod    - Запуск для production (prod профиль)"
	@echo "   make docker-up      - Запуск контейнеров по умолчанию"
	@echo "   make docker-stop    - Остановка всех контейнеров"
	@echo "   make docker-restart - Перезапуск всех контейнеров"
	@echo "   make docker-logs    - Логи всех контейнеров"
	@echo ""
	@echo "   --- Сборка и оптимизация ---"
	@echo "   make docker-build       - Сборка образов с очисткой"
	@echo "   make docker-build-clean - Сборка с полной очисткой"
	@echo "   make docker-images COUNT=N - Просмотр Docker образов"
	@echo "   make docker-clean       - Удаление образов и контейнеров"
	@echo "   make docker-reset       - Полный сброс Docker окружения"
	@echo ""
	@echo "=============================================================================="
	@echo " 🚀 DEPLOYMENT"
	@echo "=============================================================================="
	@echo "   make render-deploy   - Подготовка к деплою на Render.com"
	@echo "   make render-status   - Проверка статуса деплоя"
	@echo ""
	@echo "=============================================================================="
	@echo " 🔨 ПОМОЩЬ"
	@echo "=============================================================================="
	@echo "   make help           - Эта справка"
	@echo ""
	@echo " 🔄 Cascade Algorithm:"
	@echo "   Алгоритм работы AI агента сохранен в .windsurf/rules/cascade_algorithm.md"
	@echo "   Следует Global Rules → Project Rules → Context Rules иерархии"
