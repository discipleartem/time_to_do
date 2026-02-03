"""
Модуль аутентификации
"""

from .dependencies import (
    get_current_active_user,
    get_current_user,
    get_optional_current_user,
)
from .service import AuthService

__all__ = [
    "AuthService",
    "get_current_user",
    "get_current_active_user",
    "get_optional_current_user",
]
