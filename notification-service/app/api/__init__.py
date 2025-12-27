# app/api/__init__.py
"""
API модули Notification Service.
"""
# Экспортируем все роутеры для удобного импорта
from .notifications import router as notifications_router
from .templates import router as templates_router
from .users import router as users_router
from .history import router as history_router

__all__ = [
    "notifications_router",
    "templates_router",
    "users_router",
    "history_router"
]