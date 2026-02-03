"""
Основной файл приложения FastAPI
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.v1.api import api_router
from app.core import close_db, close_redis, init_db, init_redis
from app.core.config import settings
from app.schemas.auth import update_auth_forward_refs


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Управление жизненным циклом приложения"""
    # Startup
    print(f"🚀 Запуск {settings.PROJECT_NAME} v{settings.VERSION}")

    # Обновление forward references для Pydantic
    update_auth_forward_refs()

    # Инициализация базы данных
    await init_db()

    # Инициализация Redis
    await init_redis()

    print("✅ Приложение успешно запущено")

    yield

    # Shutdown
    print("🔄 Остановка приложения...")
    await close_db()
    await close_redis()
    print("✅ Приложение остановлено")


# Создание FastAPI приложения
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Task Tracker с SCRUM/Kanban методологиями для эффективной командной работы",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Проверка здоровья приложения

    Returns:
        dict: Статус приложения
    """
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "debug": str(settings.DEBUG),
        "timestamp": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
    }


# Root endpoint
@app.get("/")
async def root() -> dict[str, str]:
    """
    Корневой endpoint

    Returns:
        dict: Информация о приложении
    """
    return {
        "message": f"Добро пожаловать в {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
        "api": settings.API_V1_STR,
    }


# Exception handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Обработчик ошибок валидации Pydantic"""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "error_type": "validation_error"},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Обработчик ошибок значения"""
    return JSONResponse(
        status_code=400, content={"detail": str(exc), "error_type": "value_error"}
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Обработчик 404 ошибки"""
    return JSONResponse(
        status_code=404,
        content={"detail": "Ресурс не найден"},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Обработчик 500 ошибки"""
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"},
    )


app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
    )
