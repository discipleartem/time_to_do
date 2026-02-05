# PEP 8 – Style Guide for Python Code

**Краткое руководство по основным правилам PEP 8 для проекта Time to Do**

---

## 📝 Основные правила

### Отступы
- Используйте **4 пробела** на каждый уровень отступа
- Не используйте табы

### Длина строки
- **Максимум 79 символов** для кода
- **Максимум 72 символа** для комментариев и docstrings

### Пустые строки
- **2 пустые строки** между определениями классов и функций верхнего уровня
- **1 пустая строка** между методами в классе

### Импорты
- Каждый импорт на отдельной строке
- Группируйте импорты в порядке:
  1. Стандартная библиотека
  2. Сторонние библиотеки
  3. Локальные импорты
- Разделяйте группы пустой строкой

```python
# Правильно
import os
import sys

from fastapi import FastAPI
from sqlalchemy import create_engine

from app.models import User
from app.core import config
```

---

## 🏷️ Именование

### Функции и переменные
- `lowercase_with_underscores`
- Описательные имена

```python
# Правильно
def get_user_by_id(user_id: int) -> User:
    user_name = "John"
    is_active = True

# Неправильно
def getUserByID(uid):
    n = "John"
    flag = True
```

### Классы
- `CapWords` (CamelCase)

```python
# Правильно
class UserService:
    pass

class DatabaseConnection:
    pass
```

### Константы
- `UPPER_CASE_WITH_UNDERSCORES`

```python
# Правильно
MAX_CONNECTIONS = 100
DEFAULT_TIMEOUT = 30
API_BASE_URL = "https://api.example.com"
```

---

## 📏 Пробелы в выражениях

### Операторы
- Окружайте бинарные операторы пробелами

```python
# Правильно
x = x + 1
result = (a + b) * (c - d)
is_valid = name is not None

# Неправильно
x=x+1
result=(a+b)*(c-d)
is_valid=name is not None
```

### Запятые
- Пробел после запятой, но не перед ней

```python
# Правильно
def func(a, b, c):
    my_list = [1, 2, 3]
    result = func(1, 2, 3)

# Неправильно
def func(a ,b ,c):
    my_list = [1 ,2 ,3]
```

### Скобки
- Не используйте пробелы сразу после открывающей скобки
- Не используйте пробелы перед закрывающей скобкой

```python
# Правильно
result = func(arg1, arg2)
my_list = [1, 2, 3]
my_dict = {'key': 'value'}

# Неправильно
result = func ( arg1, arg2 )
my_list = [ 1, 2, 3 ]
my_dict = { 'key': 'value' }
```

---

## 📖 Документация

### Docstrings
- Используйте тройные двойные кавычки `"""`
- Первая строка - краткое описание
- Пустая строка после первого предложения

```python
def calculate_user_age(birth_date: datetime) -> int:
    """Calculate user age from birth date.

    Args:
        birth_date: User's birth date

    Returns:
        Age in years

    Raises:
        ValueError: If birth_date is in the future
    """
    # реализация
```

### Комментарии
- Пишите комментарии на английском (если проект международный)
- Комментарии должны объяснять **ПОЧЕМУ**, а не **ЧТО**

```python
# Правильно
# Используем быстрый алгоритм для больших данных
if len(data) > 1000:
    result = quick_sort(data)
else:
    result = bubble_sort(data)

# Неправильно
# Сортируем данные
result = sort(data)
```

---

## 🚫 Чего следует избегать

### Сравнения
- Используйте `is`/`is not` для сравнения с `None`
- Используйте `is not` вместо `not ... is`

```python
# Правильно
if user is not None:
    pass

if obj is None:
    pass

# Неправильно
if not user is None:
    pass

if obj == None:
    pass
```

### Логические выражения
- Не используйте `True`/`False` в условиях

```python
# Правильно
if is_valid:
    pass

if not is_active:
    pass

# Неправильно
if is_valid == True:
    pass

if not is_active == False:
    pass
```

---

## ✅ Пример хорошего кода

```python
"""
User service module for managing user operations.

This module provides functionality for user registration,
authentication, and profile management.
"""

from typing import Optional
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


class UserService:
    """Service for managing user operations."""

    def __init__(self, db: Session):
        """Initialize user service with database session."""
        self.db = db

    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user.

        Args:
            user_data: User creation data

        Returns:
            Created user object

        Raises:
            HTTPException: If user already exists
        """
        # Check if user already exists
        existing_user = self.db.query(User).filter(
            User.email == user_data.email
        ).first()

        if existing_user is not None:
            raise HTTPException(
                status_code=400,
                detail="User with this email already exists"
            )

        # Create new user
        hashed_password = get_password_hash(user_data.password)

        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            is_active=True,
            created_at=datetime.utcnow()
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(User.id == user_id).first()
```

---

## 🔧 Автоматическое форматирование

В проекте используются:
- **Black** - для форматирования кода
- **Ruff** - для линтинга и форматирования

```bash
# Форматировать код
make format

# Проверить стиль
make lint
```

---

*Следование этим правилам обеспечит консистентность и читаемость кода в проекте.*
