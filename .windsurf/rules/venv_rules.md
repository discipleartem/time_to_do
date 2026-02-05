# 🐍 Virtual Environment (.venv) — Специализированные правила

**Цель:** Правила работы с виртуальным окружением Python
**Применимость:** Все Python проекты с .venv

---

## Основное правило

**Все команды Python и pip должны выполняться в виртуальном окружении `.venv`**

---

## Структура проекта

```
project/
├── .venv/              # Виртуальное окружение (игнорируется в Git)
├── requirements.txt    # Зависимости production env проекта
├── pyproject.toml      # Основной формат учета зависимостей
└── ...                 # Остальные файлы проекта
```

---

## Правила работы с окружением

### 1. Активация окружения

```bash
# Активация окружения
source .venv/bin/activate

# Проверка активации
which python  # Должен указывать на .venv/bin/python
which pip     # Должен указывать на .venv/bin/pip
```

### 2. Установка зависимостей

```bash
# Из pyproject.toml
pip install -e .

# Из requirements.txt
pip install -r requirements.txt

# Отдельные пакеты
pip install package-name
```

### 3. Запуск приложений

```bash
# FastAPI
python main.py
# или
uvicorn main:app --reload

# Django
python manage.py runserver

# Скрипты
python script.py
```

### 4. Тестирование

```bash
# pytest
pytest

# coverage
pytest --cov=.

# unittest
python -m unittest discover
```

---

## Интеграция с инструментами

### VS Code / Windsurf

Настройки в `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.terminal.activateEnvInCurrentTerminal": true
}
```

### Makefile

```makefile
.PHONY: install run test clean

install:
    python -m venv .venv
    source .venv/bin/activate && pip install -r requirements.txt

run:
    source .venv/bin/activate && python main.py

test:
    source .venv/bin/activate && pytest

clean:
    rm -rf .venv
    find . -type d -name __pycache__ -delete
    find . -type f -name "*.pyc" -delete
```

---

## Важные моменты

### Никогда не использовать системный Python:

```bash
# ❌ Неправильно
python script.py
pip install package

# ✅ Правильно
source .venv/bin/activate
python script.py
pip install package
```

### Проверка окружения:

```python
import sys
print(sys.executable)  # Должен указывать на .venv/bin/python
```

### Деплой:

```bash
# Создание requirements.txt
pip freeze > requirements.txt

# Или использование pip-tools
pip-compile requirements.in
```

---

## Автоматизация

### Скрипт активации (`activate.sh`):

```bash
#!/bin/bash
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi
source .venv/bin/activate
echo "✅ Окружение активировано: $(which python)"
```

### Проверка в Python коде:

```python
import sys
import os

def check_venv():
    """Проверяет, что код работает в виртуальном окружении"""
    venv_path = os.path.join(os.getcwd(), '.venv')
    python_path = sys.executable

    if venv_path not in python_path:
        raise RuntimeError(
            "❌ Активируйте виртуальное окружение: source .venv/bin/activate"
        )

    print("✅ Работаем в виртуальном окружении")

if __name__ == "__main__":
    check_venv()
```

---

## Правила для AI

### AI должен:

```text
✓ Всегда проверять активацию .venv перед выполнением команд
✓ Использовать source .venv/bin/activate в скриптах
✓ Добавлять проверку окружения в автоматизированные задачи
✓ Напоминать пользователю об активации окружения
```

### AI запрещено:

```text
✗ Запускать команды вне виртуального окружения .venv
✗ Использовать системный Python для проекта
✗ Игнорировать отсутствие активированного окружения
```

---

## Чеклист

```text
☐ .venv создан
☐ .venv активирован
☐ which python указывает на .venv/bin/python
☐ requirements.txt обновлён
☐ .venv добавлен в .gitignore
☐ IDE настроен на использование .venv
```

---

**Версия:** 1.0
**Дата обновления:** Февраль 2026
**Рекомендуемое местоположение:** `.windsurf/rules/venv.md`
