# app/__init__.py
"""
Alert Service - Микросервис для управления геозонами, правилами доступа
и генерации оповещений о нарушениях.
"""
__version__ = "1.0.0"
__author__ = "Your Name"
__description__ = "Микросервис для управления геозонами, правилами и генерации оповещений"

# Экспортируем основные модули для удобного импорта
from .main import app
from . import models
from . import database
from . import incident_processor
from . import alert_generator
from .api import geozones_router, rules_router, incidents_router, alerts_router

__all__ = [
    "app",
    "models",
    "database",
    "incident_processor",
    "alert_generator",
    "geozones_router",
    "rules_router",
    "incidents_router",
    "alerts_router"
]