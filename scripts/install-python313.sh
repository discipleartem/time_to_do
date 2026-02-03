#!/bin/bash

# Скрипт установки Python 3.13
# Usage: ./scripts/install-python313.sh

set -e

echo "🐍 Установка Python 3.13..."

REQUIRED_VERSION="3.13"

# Проверяем текущую версию
if command -v python3.13 &> /dev/null; then
    echo "✅ Python 3.13 уже установлен"
    python3.13 --version
    exit 0
fi

# Проверяем версию системного python3
CURRENT_PYTHON=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' || echo "0.0")

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$CURRENT_PYTHON" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
    echo "✅ Python $CURRENT_PYTHON уже удовлетворяет требованиям (нужен $REQUIRED_VERSION+)"
    python3 --version
    exit 0
fi

echo "❌ Требуется Python 3.13+, найден Python $CURRENT_PYTHON"
echo "🔧 Начинаю установку Python 3.13..."

# Определение ОС и пакетного менеджера
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v apt-get &> /dev/null; then
        # Ubuntu/Debian
        echo "📦 Обнаружен Ubuntu/Debian, установка через apt..."

        # Добавляем PPA для Python 3.13 если нужно
        if ! apt-cache policy python3.13 | grep -q "3.13"; then
            echo "➕ Добавление PPA для Python 3.13..."
            sudo apt-get update
            sudo apt-get install -y software-properties-common
            sudo add-apt-repository ppa:deadsnakes/ppa -y
            sudo apt-get update
        fi

        echo "📦 Установка Python 3.13 и зависимостей..."
        sudo apt-get install -y python3.13 python3.13-venv python3.13-dev python3.13-pip python3.13-distutils

    elif command -v yum &> /dev/null; then
        # CentOS/RHEL/Fedora
        echo "📦 Обнаружен CentOS/RHEL/Fedora, установка через yum..."
        sudo yum install -y python3.13 python3.13-pip

    elif command -v dnf &> /dev/null; then
        # Fedora (новые версии)
        echo "📦 Обнаружен Fedora, установка через dnf..."
        sudo dnf install -y python3.13 python3.13-pip

    elif command -v pacman &> /dev/null; then
        # Arch Linux
        echo "📦 Обнаружен Arch Linux, установка через pacman..."
        sudo pacman -S python3.13

    else
        echo "❌ Не удалось определить пакетный менеджер Linux"
        echo "🔧 Пожалуйста, установите Python 3.13 вручную"
        exit 1
    fi

elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if command -v brew &> /dev/null; then
        echo "📦 Обнаружен macOS с Homebrew, установка через brew..."
        brew install python@3.13
    else
        echo "❌ Homebrew не найден. Пожалуйста, установите Homebrew:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi

else
    echo "❌ Не удалось определить операционную систему: $OSTYPE"
    echo "🔧 Пожалуйста, установите Python 3.13 вручную:"
    echo "   https://www.python.org/downloads/"
    exit 1
fi

# Проверка установки
echo "🔍 Проверка установки Python 3.13..."

if command -v python3.13 &> /dev/null; then
    echo "✅ Python 3.13 успешно установлен!"
    python3.13 --version

    # Проверка venv
    echo "🔍 Проверка модуля venv..."
    python3.13 -m venv --help > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ Модуль venv доступен"
    else
        echo "⚠️ Модуль venv не найден, устанавливаю..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y python3.13-venv
        fi
    fi

    echo ""
    echo "🎉 Python 3.13 готов к использованию!"
    echo "🚀 Теперь можно запустить: ./scripts/reinstall-deps.sh"

else
    echo "❌ Не удалось установить Python 3.13"
    echo "🔧 Попробуйте установить вручную:"
    echo "   Ubuntu/Debian: sudo apt-get install python3.13 python3.13-venv"
    echo "   macOS: brew install python@3.13"
    echo "   CentOS/RHEL: sudo yum install python3.13"
    exit 1
fi
