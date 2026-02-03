"""
API роутеры для GitHub OAuth
"""

from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.auth.service import AuthService
from app.core.config import settings
from app.core.constants import BEARER_TOKEN_TYPE, GITHUB_TOKEN_URL
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import LoginResponse
from app.schemas.user import GitHubUserInfo
from app.schemas.user import User as UserSchema

router = APIRouter()


@router.get("/login")
async def github_login() -> RedirectResponse:
    """
    Перенаправление на GitHub для аутентификации
    """
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth не настроен",
        )

    # Параметры для GitHub OAuth
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": "user:email read:user public_repo read:org",
        "state": "random_state_string",  # TODO: генерировать безопасный state
    }

    github_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    return RedirectResponse(url=github_url)


@router.get("/callback")
async def github_callback(
    code: str,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Обработка callback от GitHub OAuth
    """
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth не настроен",
        )

    try:
        # Обмен кода на access token
        access_token = await exchange_code_for_token(code)

        # Получение информации о пользователе
        github_user = await get_github_user_info(access_token)

        # Аутентификация или регистрация пользователя
        auth_service = AuthService(db)
        user, access_token, refresh_token = await auth_service.authenticate_github(
            github_user
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=BEARER_TOKEN_TYPE,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserSchema.model_validate(user),
        )

    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при аутентификации через GitHub: {str(err)}",
        ) from err


async def exchange_code_for_token(code: str) -> str:
    """
    Обмен кода авторизации на access token

    Args:
        code: Код авторизации от GitHub

    Returns:
        str: Access token

    Raises:
        HTTPException: Если не удалось получить token
    """
    token_url = GITHUB_TOKEN_URL

    data = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "code": code,
    }

    headers = {
        "Accept": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось получить access token от GitHub",
            )

        token_data = response.json()

        if "access_token" not in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Отсутствует access token в ответе GitHub",
            )

        return token_data["access_token"]


async def get_github_user_info(access_token: str) -> GitHubUserInfo:
    """
    Получение информации о пользователе из GitHub

    Args:
        access_token: GitHub access token

    Returns:
        GitHubUserInfo: Информация о пользователе

    Raises:
        HTTPException: Если не удалось получить информацию о пользователе
    """
    user_url = "https://api.github.com/user"
    email_url = "https://api.github.com/user/emails"

    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    async with httpx.AsyncClient() as client:
        # Получаем основную информацию о пользователе
        user_response = await client.get(user_url, headers=headers)

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось получить информацию о пользователе GitHub",
            )

        user_data = user_response.json()

        # Получаем email (он может быть приватным)
        email_response = await client.get(email_url, headers=headers)

        if email_response.status_code == 200:
            emails = email_response.json()
            # Ищем primary email
            primary_email = None
            for email_info in emails:
                if email_info.get("primary", False) and email_info.get(
                    "verified", False
                ):
                    primary_email = email_info["email"]
                    break

            if primary_email:
                user_data["email"] = primary_email

    return GitHubUserInfo(**user_data)


@router.get("/user-info")
async def get_github_user_info_endpoint(
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Получение информации о GitHub пользователе (если он авторизован через GitHub)
    """
    if not current_user.github_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь не авторизован через GitHub",
        )

    return {
        "github_id": current_user.github_id,
        "github_username": current_user.github_username,
        "avatar_url": current_user.avatar_url,
    }


@router.post("/disconnect")
async def disconnect_github(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Отключение GitHub аккаунта
    """
    if not current_user.github_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub аккаунт не подключен",
        )

    # Проверяем, есть ли у пользователя пароль
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя отключить GitHub аккаунт без установленного пароля",
        )

    # Отключаем GitHub
    current_user.github_id = None  # type: ignore[assignment] # SQLAlchemy String field limitation
    current_user.github_username = None  # type: ignore[assignment] # SQLAlchemy String field limitation

    await db.commit()

    return {"message": "GitHub аккаунт успешно отключен"}
