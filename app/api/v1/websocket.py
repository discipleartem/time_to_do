"""
WebSocket роутер для real-time функциональности
"""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.websocket.handlers import handler

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None, description="JWT токен для аутентификации"),
) -> None:
    """
    WebSocket эндпоинт для real-time обновлений

    Args:
        websocket: WebSocket соединение
        token: JWT токен для аутентификации (опционально)
    """
    connection_id = None

    try:
        # Установка соединения и аутентификация
        connection_id = await handler.handle_connection(websocket, token)

        # Обработка сообщений
        while True:
            try:
                # Получение сообщения от клиента
                message = await websocket.receive_text()

                # Обработка сообщения
                await handler.handle_message(connection_id, message)

            except WebSocketDisconnect:
                # Нормальное отключение клиента
                break
            except Exception as e:
                # Ошибка обработки сообщения
                print(f"Ошибка обработки сообщения {connection_id}: {e}")
                # Продолжаем работу, не разрывая соединение

    except WebSocketDisconnect:
        # Клиент отключился до установки соединения
        pass
    except Exception as e:
        # Критическая ошибка соединения
        print(f"Критическая ошибка WebSocket: {e}")
    finally:
        # Гарантированная очистка соединения
        if connection_id:
            await handler.handle_disconnection(connection_id)


@router.get("/ws/stats")
async def websocket_stats() -> dict:
    """
    Получение статистики WebSocket соединений

    Returns:
        dict: Статистика соединений
    """
    return handler.manager.get_stats()
