"""
Pydantic схемы для API
"""

from .auth import LoginRequest, Token, TokenData
from .notification import (
    NotificationCreate,
    NotificationFactory,
    NotificationList,
    NotificationMarkRead,
    NotificationPreferences,
    NotificationRead,
    NotificationStats,
    NotificationUpdate,
    TaskAssignedNotification,
    TaskCompletedNotification,
)
from .project import (
    Project,
    ProjectCreate,
    ProjectMember,
    ProjectMemberCreate,
    ProjectUpdate,
)
from .sprint import Sprint, SprintCreate, SprintTask, SprintUpdate
from .task import Comment, CommentCreate, Task, TaskCreate, TaskUpdate
from .time_entry import TimeEntry, TimeEntryCreate, TimeEntryUpdate
from .user import User, UserCreate, UserInDB, UserUpdate

__all__ = [
    "User",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "Project",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectMember",
    "ProjectMemberCreate",
    "Task",
    "TaskCreate",
    "TaskUpdate",
    "Comment",
    "CommentCreate",
    "Sprint",
    "SprintCreate",
    "SprintUpdate",
    "SprintTask",
    "TimeEntry",
    "TimeEntryCreate",
    "TimeEntryUpdate",
    "Token",
    "TokenData",
    "LoginRequest",
    "NotificationCreate",
    "NotificationRead",
    "NotificationUpdate",
    "NotificationList",
    "NotificationStats",
    "NotificationPreferences",
    "NotificationMarkRead",
    "NotificationFactory",
    "TaskAssignedNotification",
    "TaskCompletedNotification",
]
