"""
Зависимости для аутентификации
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User

# Схема для Bearer токенов (auto_error=False для возврата 401 вместо 403)
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Получение текущего пользователя по JWT токену

    Args:
        credentials: JWT токен
        db: Сессия базы данных

    Returns:
        User: Текущий пользователь

    Raises:
        HTTPException: Если токен невалидный или пользователь не найден
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    try:
        email = verify_token(credentials.credentials)
        if email is None:
            raise credentials_exception
    except Exception as e:
        raise credentials_exception from e

    user = await get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Получение текущего активного пользователя

    Args:
        current_user: Текущий пользователь

    Returns:
        User: Активный пользователь

    Raises:
        HTTPException: Если пользователь неактивен
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь неактивен"
        )

    return current_user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Получение опционального текущего пользователя

    Args:
        credentials: JWT токен (опционально)
        db: Сессия базы данных

    Returns:
        Optional[User]: Пользователь или None
    """
    if not credentials:
        return None

    try:
        email = verify_token(credentials.credentials)
        if email is None:
            return None

        user = await get_user_by_email(db, email=email)
        return user
    except Exception:
        return None


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Получение текущего администратора

    Args:
        current_user: Текущий пользователь

    Returns:
        User: Администратор

    Raises:
        HTTPException: Если пользователь не администратор
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав доступа"
        )

    return current_user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """
    Получение пользователя по email

    Args:
        db: Сессия базы данных
        email: Email пользователя

    Returns:
        Optional[User]: Пользователь или None
    """
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_current_user_ws(token: str) -> User:
    """
    Получение текущего пользователя по JWT токену для WebSocket

    Args:
        token: JWT токен из query параметра

    Returns:
        User: Текущий пользователь

    Raises:
        HTTPException: Если токен невалидный или пользователь не найден
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        email = verify_token(token)
        if email is None:
            raise credentials_exception
    except Exception as e:
        raise credentials_exception from e

    # Создаем временную сессию для WebSocket
    from app.core.database import get_db_session_context

    async with get_db_session_context() as db:
        user = await get_user_by_email(db, email=email)
        if user is None:
            raise credentials_exception

        return user
