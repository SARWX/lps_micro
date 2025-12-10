from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.models import ValidationErrorResponse, ErrorResponse
from app.api.measurements import router as measurements_router

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.models import ValidationErrorResponse, ErrorResponse
from app.api.measurements import router as measurements_router
from app.api.positions import router as positions_router 
from app.api.anchors import router as anchors_router

app = FastAPI(
    title="Positioning Service API",
    description="Микросервис для позиционирования персонала в реальном времени",
    version="1.0.0"
)

# Обработчик ошибок валидации Pydantic
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

# Обработчик общих ошибок
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error_code="INTERNAL_ERROR",
            message=str(exc)
        ).model_dump()
    )

# Подключаем роутер
app.include_router(measurements_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    # Инициализация БД при старте
    from app.database import init_db
    init_db()

app.include_router(measurements_router, prefix="/api/v1")
app.include_router(positions_router, prefix="/api/v1")
app.include_router(anchors_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    from app.database import init_db
    init_db()

