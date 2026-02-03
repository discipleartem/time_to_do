"""
Сервис аутентификации
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_refresh_token,
)
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
)
from app.schemas.user import GitHubUserInfo, UserCreate


class AuthService:
    """Сервис аутентификации"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, user_data: RegisterRequest) -> tuple[User, str, str]:
        """
        Регистрация нового пользователя

        Args:
            user_data: Данные для регистрации

        Returns:
            Tuple[User, str, str]: Пользователь, access_token, refresh_token

        Raises:
            HTTPException: Если пользователь уже существует
        """
        # Проверяем, существует ли пользователь
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует",
            )

        if user_data.username:
            existing_username = await self.get_user_by_username(user_data.username)
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с таким именем уже существует",
                )

        # Создаем нового пользователя
        user_create = UserCreate(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            password=user_data.password,
        )

        hashed_password = get_password_hash(user_create.password)

        # Определяем роль пользователя
        user_role = UserRole.USER
        if user_data.role and user_data.role == "ADMIN":
            user_role = UserRole.ADMIN

        db_user = User(
            email=user_create.email,
            username=user_create.username,
            full_name=user_create.full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,
            role=user_role,
        )

        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)

        # Создаем токены
        access_token = create_access_token(subject=db_user.email)
        refresh_token = create_refresh_token(subject=db_user.email)

        return db_user, access_token, refresh_token

    async def login(self, login_data: LoginRequest) -> tuple[User, str, str]:
        """
        Вход пользователя

        Args:
            login_data: Данные для входа

        Returns:
            Tuple[User, str, str]: Пользователь, access_token, refresh_token

        Raises:
            HTTPException: Если неверные учетные данные
        """
        user = await self.authenticate_user(login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь неактивен",
            )

        # Создаем токены
        access_token = create_access_token(subject=user.email)
        refresh_token = create_refresh_token(subject=user.email)

        return user, access_token, refresh_token

    async def refresh_token(self, refresh_data: RefreshTokenRequest) -> tuple[str, str]:
        """
        Обновление access токена

        Args:
            refresh_data: Refresh токен

        Returns:
            Tuple[str, str]: Новый access_token, refresh_token

        Raises:
            HTTPException: Если refresh токен невалиден
        """
        email = verify_refresh_token(refresh_data.refresh_token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный refresh токен",
            )

        user = await self.get_user_by_email(email)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден или неактивен",
            )

        # Создаем новые токены
        access_token = create_access_token(subject=user.email)
        new_refresh_token = create_refresh_token(subject=user.email)

        return access_token, new_refresh_token

    async def authenticate_github(
        self, github_user: GitHubUserInfo
    ) -> tuple[User, str, str]:
        """
        Аутентификация через GitHub

        Args:
            github_user: Данные от GitHub

        Returns:
            Tuple[User, str, str]: Пользователь, access_token, refresh_token
        """
        # Ищем пользователя по GitHub ID
        user = await self.get_user_by_github_id(str(github_user.id))

        if not user:
            # Ищем по email
            if github_user.email:
                user = await self.get_user_by_email(github_user.email)
                if user:
                    # Обновляем существующего пользователя
                    user.github_id = str(github_user.id)  # type: ignore
                    user.github_username = github_user.login  # type: ignore
                    user.avatar_url = github_user.avatar_url  # type: ignore
                    if not user.full_name and github_user.name:
                        user.full_name = github_user.name  # type: ignore
                    await self.db.commit()
                    await self.db.refresh(user)
                else:
                    # Создаем нового пользователя
                    user = User(
                        email=github_user.email or f"{github_user.login}@github.local",
                        username=github_user.login,
                        full_name=github_user.name,
                        avatar_url=github_user.avatar_url,
                        github_id=str(github_user.id),
                        github_username=github_user.login,
                        is_active=True,
                        is_verified=True,  # GitHub пользователи считаются верифицированными
                        role=UserRole.USER,
                    )
                    self.db.add(user)
                    await self.db.commit()
                    await self.db.refresh(user)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь неактивен",
            )

        # Создаем токены
        access_token = create_access_token(subject=user.email)
        refresh_token = create_refresh_token(subject=user.email)

        return user, access_token, refresh_token

    async def authenticate_user(self, email: str, password: str) -> User | None:
        """
        Аутентификация пользователя по email и паролю

        Args:
            email: Email пользователя
            password: Пароль

        Returns:
            Optional[User]: Пользователь или None
        """
        user = await self.get_user_by_email(email)
        if not user:
            return None

        if not user.hashed_password:
            return None

        if not verify_password(password, str(user.hashed_password)):
            return None

        return user

    async def get_user_by_email(self, email: str) -> User | None:
        """Получение пользователя по email"""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        """Получение пользователя по имени"""
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_user_by_github_id(self, github_id: str) -> User | None:
        """Получение пользователя по GitHub ID"""
        result = await self.db.execute(select(User).where(User.github_id == github_id))
        return result.scalar_one_or_none()

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> bool:
        """
        Изменение пароля пользователя

        Args:
            user: Пользователь
            current_password: Текущий пароль
            new_password: Новый пароль

        Returns:
            bool: Успешно ли изменен пароль
        """
        if not user.hashed_password:
            return False

        if not verify_password(current_password, str(user.hashed_password)):
            return False

        user.hashed_password = get_password_hash(new_password)  # type: ignore
        await self.db.commit()

        return True
