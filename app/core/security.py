"""
Безопасность: JWT токены, хеширование паролей
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from jwt.exceptions import PyJWTError as JWTError

from app.core.config import settings


def create_access_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:
    """
    Создание JWT access token

    Args:
        subject: Идентификатор пользователя (обычно email или user_id)
        expires_delta: Время жизни токена

    Returns:
        str: JWT токен
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"sub": str(subject), "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> str | None:
    """
    Верификация JWT токена

    Args:
        token: JWT токен

    Returns:
        Optional[str]: Идентификатор пользователя или None если токен невалиден
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload.get("sub")
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Верификация пароля

    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Хешированный пароль

    Returns:
        bool: True если пароль верный
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """
    Хеширование пароля

    Args:
        password: Пароль в открытом виде

    Returns:
        str: Хешированный пароль
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_refresh_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:
    """
    Создание JWT refresh token (более долгоживущий)

    Args:
        subject: Идентификатор пользователя
        expires_delta: Время жизни токена

    Returns:
        str: JWT refresh token
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=7)  # 7 дней для refresh token

    to_encode = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_refresh_token(token: str) -> str | None:
    """
    Верификация refresh token

    Args:
        token: JWT refresh token

    Returns:
        Optional[str]: Идентификатор пользователя или None если токен невалиден
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        # Проверяем что это refresh токен
        if payload.get("type") != "refresh":
            return None
        return payload.get("sub")
    except JWTError:
        return None
