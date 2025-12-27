from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from app.models import ValidationErrorResponse, ErrorResponse
from app.api.geozones import router as geozones_router
from app.api.rules import router as rules_router
from app.api.incidents import router as incidents_router
from app.api.alerts import router as alerts_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.database import init_db
    init_db()
    logger.info("Alert Service started")
    
    # Запускаем планировщик задач
    scheduler = AsyncIOScheduler()
    
    # Добавляем задачу для очистки старых инцидентов
    from app.incident_processor import cleanup_old_incidents
    
    async def daily_cleanup():
        try:
            logger.info("Starting daily incident cleanup")
            deleted_count = cleanup_old_incidents(days_to_keep=90)
            logger.info(f"Daily cleanup completed. Deleted {deleted_count} records")
        except Exception as e:
            logger.error(f"Error in daily cleanup: {e}")
    
    # Запускаем задачи
    scheduler.add_job(
        daily_cleanup,
        trigger=IntervalTrigger(days=1),
        id='daily_cleanup',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started with periodic tasks")
    
    yield
    
    # Shutdown
    scheduler.shutdown()
    logger.info("Alert Service shutting down")

app = FastAPI(
    title="Alert Service API",
    description="Микросервис для управления геозонами, правилами доступа и генерации оповещений о нарушениях",
    version="1.0.0",
    lifespan=lifespan
)

# Обработчики ошибок
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error.get("loc", []))
        errors.append({
            "field": field,
            "error": error.get("msg")
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ValidationErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Invalid request data",
            details=errors
        ).model_dump()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()  # Для отладки
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error_code="INTERNAL_ERROR",
            message=str(exc)
        ).model_dump()
    )

# Корневой endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Перенаправление на документацию Swagger"""
    return RedirectResponse(url="/docs")

# Health endpoint
@app.get("/health", include_in_schema=False)
async def health_check():
    from app.database import get_database_stats
    try:
        db_stats = get_database_stats()
        return {
            "status": "healthy",
            "service": "alert_service",
            "timestamp": datetime.now().isoformat(),
            "database_stats": db_stats
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "alert_service",
                "error": str(e)
            }
        )

# Подключаем роутеры
app.include_router(geozones_router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
app.include_router(incidents_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")