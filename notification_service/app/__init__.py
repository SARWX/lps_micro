# app/__init__.py
"""
Notification Service - Микросервис для доставки уведомлений через различные каналы.
"""
__version__ = "1.0.0"
__author__ = "Your Name"
__description__ = "Микросервис для доставки уведомлений (email, SMS, Telegram, push)"

# Экспортируем основные модули для удобного импорта
from .main import app
from . import models
from . import database
from . import notification_sender
from . import notification_templates
from . import user_preferences
from .api import notifications_router, templates_router, users_router, history_router

__all__ = [
    "app",
    "models",
    "database",
    "notification_sender",
    "notification_templates",
    "user_preferences",
    "notifications_router",
    "templates_router",
    "users_router",
    "history_router"
]