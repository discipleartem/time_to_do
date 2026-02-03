#!/bin/bash

# Скрипт полной переустановки зависимостей с Python 3.13
# Usage: ./scripts/reinstall-deps.sh

set -e  # Выход при ошибке

echo "🔄 Начинаю полную переустановку зависимостей с Python 3.13..."

# 1. Проверка и установка Python 3.13
echo "🐍 Проверка Python 3.13..."

# Проверяем текущую версию Python
CURRENT_PYTHON=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' || echo "0.0")
PYTHON313_VERSION=$(python3.13 --version 2>&1 | grep -oP '\d+\.\d+' || echo "0.0")
REQUIRED_VERSION="3.13"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON313_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
    echo "✅ Python $PYTHON313_VERSION найден (требуется $REQUIRED_VERSION+)"
    PYTHON_CMD="python3.13"
else
    echo "❌ Требуется Python 3.13+, найден Python $CURRENT_PYTHON"
    echo "🔧 Попытка установки Python 3.13..."

    # Установка Python 3.13 в зависимости от системы
    if command -v apt-get &> /dev/null; then
        # Ubuntu/Debian
        echo "📦 Установка Python 3.13 через apt..."
        sudo apt-get update
        sudo apt-get install -y python3.13 python3.13-venv python3.13-dev
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL/Fedora
        echo "📦 Установка Python 3.13 через yum..."
        sudo yum install -y python3.13
    elif command -v brew &> /dev/null; then
        # macOS
        echo "📦 Установка Python 3.13 через Homebrew..."
        brew install python@3.13
    else
        echo "❌ Не удалось определить пакетный менеджер"
        echo "🔧 Пожалуйста, установите Python 3.13 вручную:"
        echo "   Ubuntu/Debian: sudo apt-get install python3.13 python3.13-venv"
        echo "   macOS: brew install python@3.13"
        echo "   CentOS/RHEL: sudo yum install python3.13"
        exit 1
    fi

    # Проверяем установку
    if command -v python3.13 &> /dev/null; then
        echo "✅ Python 3.13 успешно установлен"
        PYTHON_CMD="python3.13"
    else
        echo "❌ Не удалось установить Python 3.13"
        exit 1
    fi
fi

# 2. Деактивация и удаление виртуального окружения
echo "🗑️ Удаление виртуального окружения..."
if [ -d ".venv" ]; then
    echo "Найдено существующее .venv, удаляю..."
    rm -rf .venv
fi

# 3. Создание нового виртуального окружения с Python 3.13
echo "🐍 Создание виртуального окружения с Python $REQUIRED_VERSION..."
$PYTHON_CMD -m venv .venv
source .venv/bin/activate

# 4. Проверка версии Python в виртуальном окружении
echo "🔍 Проверка версии Python в .venv:"
python --version

# 5. Обновление pip
echo "📦 Обновление pip..."
pip install --upgrade pip setuptools wheel

# 6. Установка зависимостей из pyproject.toml
echo "📋 Установка зависимостей из pyproject.toml..."
if [ -f "pyproject.toml" ]; then
    echo "Найден pyproject.toml, устанавливаю через pip..."
    pip install -e .
else
    echo "❌ pyproject.toml не найден!"
    exit 1
fi

# 7. Установка Poetry (если нет)
echo "📜 Проверка Poetry..."
if ! command -v poetry &> /dev/null; then
    echo "Установка Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "Poetry уже установлен"
fi

# 8. Синхронизация с Poetry
echo "🔄 Синхронизация с Poetry..."
if [ -f "pyproject.toml" ]; then
    poetry env use .venv/bin/python
    poetry sync
    echo "✅ Poetry синхронизирован"
else
    echo "❌ pyproject.toml не найден для Poetry!"
    exit 1
fi

# 9. Создание requirements.txt для production
echo "📝 Создание requirements.txt для production..."

# Активируем poetry окружение
source $(poetry env info --path)/bin/activate

# Получаем только основные зависимости в формате requirements.txt
echo "# Production dependencies generated from Poetry" > requirements.txt
poetry show --only main --format json | python3 -c "
import json
import sys

data = json.loads(sys.stdin.read())
for pkg in data:
    name = pkg['name']
    version = pkg['version']
    print(f'{name}=={version}')
" >> requirements.txt

echo "✅ requirements.txt создан из Poetry main dependencies"

# 10. Создание requirements-dev.txt для разработки
echo "📝 Создание requirements-dev.txt для разработки..."

echo "# All dependencies (main + dev) generated from Poetry" > requirements-dev.txt
poetry show --format json | python3 -c "
import json
import sys

data = json.loads(sys.stdin.read())
for pkg in data:
    name = pkg['name']
    version = pkg['version']
    print(f'{name}=={version}')
" >> requirements-dev.txt

echo "✅ requirements-dev.txt создан из Poetry all dependencies"

# 11. Проверка установки
echo "🔍 Проверка установки..."
echo "Python: $(python --version)"
echo "Pip: $(pip --version)"
echo "Poetry: $(poetry --version)"

# 12. Показ установленных пакетов
echo ""
echo "📦 Установленные пакеты:"
pip list

# 13. Проверка критичных зависимостей
echo ""
echo "🔍 Проверка критичных зависимостей:"
python -c "
import sys
critical_packages = ['fastapi', 'sqlalchemy', 'alembic', 'pydantic', 'uvicorn']
missing = []
for pkg in critical_packages:
    try:
        __import__(pkg)
        print(f'✅ {pkg}')
    except ImportError:
        print(f'❌ {pkg}')
        missing.append(pkg)

if missing:
    print(f'\\n⚠️ Отсутствуют критичные пакеты: {missing}')
    sys.exit(1)
else:
    print('\\n🎉 Все критичные пакеты установлены!')
"

echo ""
echo "✅ Переустановка зависимостей завершена успешно!"
echo "🐍 Используется Python: $(python --version)"
echo ""
echo "📋 Созданные файлы:"
echo "   - requirements.txt (production)"
echo "   - requirements-dev.txt (development)"
echo ""
echo "🚀 Теперь можно использовать:"
echo "   make dev     - запуск разработки"
echo "   make test    - запуск тестов"
echo "   make lint    - проверка кода"
