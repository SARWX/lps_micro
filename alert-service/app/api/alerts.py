from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
import logging
import json
from app.models import (
    AlertRequest, AlertHistoryItem, ErrorResponse, ValidationErrorResponse
)
from app.database import (
    get_alert_history
)
from app.alert_generator import AlertGenerator

router = APIRouter(tags=["Alerts"])
logger = logging.getLogger(__name__)

# Инициализируем генератор оповещений
alert_generator = AlertGenerator()

@router.post(
    "/alerts",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Оповещение поставлено в очередь для отправки", "model": dict},
        400: {"description": "Некорректные данные запроса", "model": ErrorResponse}
    }
)
async def generate_alert_endpoint(alert_request: AlertRequest):
    """
    Генерация оповещения.
    Генерирует оповещение на основе инцидента или правила.
    """
    try:
        # Генерируем оповещение
        result = await alert_generator.generate_alert(alert_request)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ValidationErrorResponse(
                error_code="VALIDATION_ERROR",
                message=str(e),
                details=[{"field": "incident_id", "error": str(e)}]
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Error generating alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="ALERT_GENERATION_ERROR",
                message=f"Failed to generate alert: {str(e)}"
            ).model_dump()
        )

@router.get(
    "/alerts/history",
    response_model=list[AlertHistoryItem],
    responses={
        200: {"description": "Успешный запрос", "model": list[AlertHistoryItem]},
        400: {"description": "Некорректные параметры запроса", "model": ErrorResponse}
    }
)
async def get_alert_history_endpoint(
    start_time: str = Query(None, description="Начало периода"),
    end_time: str = Query(None, description="Конец периода"),
    status: str = Query(None, description="Статус оповещений", enum=["sent", "failed", "pending"]),
    limit: int = Query(100, description="Максимальное количество записей", ge=1, le=1000)
):
    """
    Получение истории оповещений.
    Возвращает историю отправленных оповещений.
    """
    try:
        alerts_data = get_alert_history(
            start_time=start_time,
            end_time=end_time,
            status=status,
            limit=limit
        )
        
        result = []
        for alert_data in alerts_:
            # Парсим JSON поля
            if alert_data.get('channels'):
                alert_data['channels'] = json.loads(alert_data['channels'])
            if alert_data.get('metadata'):
                alert_data['metadata'] = json.loads(alert_data['metadata'])
            
            result.append(AlertHistoryItem(**alert_data))
        
        return result
    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="GET_ALERT_HISTORY_ERROR",
                message=f"Failed to get alert history: {str(e)}"
            ).model_dump()
        )