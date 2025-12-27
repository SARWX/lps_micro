# app/api/__init__.py
"""
API модули Alert Service.
"""
# Экспортируем все роутеры для удобного импорта
from .geozones import router as geozones_router
from .rules import router as rules_router
from .incidents import router as incidents_router
from .alerts import router as alerts_router

__all__ = [
    "geozones_router",
    "rules_router",
    "incidents_router",
    "alerts_router"
]