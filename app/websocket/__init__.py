"""
WebSocket модуль - real-time функциональность
"""

from app.websocket.connection import Connection
from app.websocket.handlers import WebSocketHandler, handler
from app.websocket.manager import ConnectionManager, manager

__all__ = ["Connection", "ConnectionManager", "WebSocketHandler", "manager", "handler"]
