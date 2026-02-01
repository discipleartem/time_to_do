---
trigger: glob
---
# Работа с виртуальным окружением (.venv)

## 🐍 Основное правило

**Все команды Python и pip должны выполняться в виртуальном окружении `.venv`**

## 📁 Структура проекта

```
project/
├── .venv/              # Виртуальное окружение (игнорируется в Git)
├── requirements.txt    # Зависимости production env проекта
├── pyproject.toml      # Основной формат учета зависимостей
└── ...                 # Остальные файлы проекта
```

## 🚀 Правила работы

### 1. Активация окружения

Перед выполнением любых команд Python:

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


## 🛠️ Интеграция с инструментами

### VS Code / Windsurf

Настройки в `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.terminal.activateEnvInCurrentTerminal": true
}
```



## ⚠️ Важные моменты

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


## 🔄 Автоматизация

### Скрипт активации (`activate.sh`):
```bash
#!/bin/bash
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi
source .venv/bin/activate
echo "✅ Окружение активировано: $(which python)"
``` 

---
