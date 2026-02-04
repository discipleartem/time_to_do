"""
API v1 модули
"""

from .auth import router as auth_router
from .github import router as github_router
from .notifications import router as notifications_router
from .projects import router as projects_router
from .search import router as search_router
from .share_links import router as share_links_router
from .sprints import router as sprints_router
from .tasks import router as tasks_router
from .time_entries import router as time_entries_router
from .users import router as users_router
from .websocket import router as websocket_router

__all__ = [
    "auth_router",
    "users_router",
    "projects_router",
    "sprints_router",
    "tasks_router",
    "github_router",
    "time_entries_router",
    "notifications_router",
    "share_links_router",
    "search_router",
    "websocket_router",
]
