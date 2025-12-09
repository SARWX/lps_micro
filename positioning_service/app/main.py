from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager

from app.database import init_db
from app.api import measurements, positions, anchors

# Создаем анкеры в памяти для демо
DEMO_ANCHORS = {
    "anchor-1": {"x": 0.0, "y": 0.0, "z": 3.0, "description": "Северная стена"},
    "anchor-2": {"x": 50.0, "y": 0.0, "z": 3.0, "description": "Южная стена"},
    "anchor-3": {"x": 25.0, "y": 30.0, "z": 3.0, "description": "Центральная колонна"},
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Старт: инициализация БД
    print("Инициализация базы данных...")
    init_db()
    print("Сервис positioning-service запущен на порту 8082")
    yield
    # Завершение: очистка ресурсов
    print("Сервис останавливается...")

app = FastAPI(
    title="Positioning Service API",
    description="Микросервис для позиционирования персонала в реальном времени",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Подключаем роутеры
app.include_router(measurements.router, prefix="/api/v1", tags=["Measurements"])
app.include_router(positions.router, prefix="/api/v1", tags=["Positions"])
app.include_router(anchors.router, prefix="/api/v1", tags=["Anchors"])

# Кэш для хранения последних позиций (в памяти)
position_cache = {}

# Глобальные переменные для доступа из модулей
app.state.anchors = DEMO_ANCHORS
app.state.position_cache = position_cache

@app.get("/", include_in_schema=False)
async def root():
    """Перенаправление на документацию"""
    return RedirectResponse(url="/docs")

@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    return {
        "status": "healthy",
        "service": "positioning-service",
        "version": "1.0.0",
        "cache_size": len(position_cache)
    }