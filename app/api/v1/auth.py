"""
API роутеры для аутентификации
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.auth.service import AuthService
from app.core.config import settings
from app.core.constants import BEARER_TOKEN_TYPE
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    PasswordChange,
    RefreshTokenRequest,
    RegisterRequest,
    Token,
    update_auth_forward_refs,
)
from app.schemas.user import User as UserSchema

router = APIRouter()


@router.post(
    "/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Регистрация нового пользователя
    """
    # Обновляем forward references если нужно
    update_auth_forward_refs()

    auth_service = AuthService(db)

    try:
        user, access_token, refresh_token = await auth_service.register(user_data)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=BEARER_TOKEN_TYPE,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserSchema.model_validate(user),
        )
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при регистрации пользователя",
        ) from err


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Вход пользователя
    """
    # Обновляем forward references если нужно
    update_auth_forward_refs()

    auth_service = AuthService(db)

    try:
        user, access_token, refresh_token = await auth_service.login(login_data)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=BEARER_TOKEN_TYPE,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserSchema.model_validate(user),
        )
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при входе",
        ) from err


@router.post("/login/oauth2", response_model=LoginResponse)
async def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Вход через OAuth2 (для совместимости)
    """
    # Обновляем forward references если нужно
    update_auth_forward_refs()

    login_request = LoginRequest(
        email=form_data.username,
        password=form_data.password,
    )

    auth_service = AuthService(db)

    try:
        user, access_token, refresh_token = await auth_service.login(login_request)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=BEARER_TOKEN_TYPE,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserSchema.model_validate(user),
        )
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при входе",
        ) from err


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Обновление access токена
    """
    auth_service = AuthService(db)

    try:
        access_token, refresh_token = await auth_service.refresh_token(refresh_data)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=BEARER_TOKEN_TYPE,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении токена",
        ) from err


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Изменение пароля текущего пользователя
    """
    auth_service = AuthService(db)

    success = await auth_service.change_password(
        current_user,
        password_data.current_password,
        password_data.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль",
        )

    return {"message": "Пароль успешно изменен"}


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> UserSchema:
    """
    Получение информации о текущем пользователе
    """
    return UserSchema.model_validate(current_user)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    """
    Выход пользователя (клиент должен удалить токены)
    """
    # В будущем здесь можно добавить инвалидацию токенов через Redis
    return {"message": "Выполнен выход"}
