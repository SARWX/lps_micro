from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
import logging
from app.models import (
    NotificationHistoryItem, ErrorResponse, ValidationErrorResponse
)
from app.database import (
    get_notifications_history
)
from datetime import datetime, timezone

router = APIRouter(tags=["History"])
logger = logging.getLogger(__name__)

@router.get(
    "/notifications/history",
    response_model=list[NotificationHistoryItem],
    responses={
        200: {"description": "Успешный запрос", "model": list[NotificationHistoryItem]},
        400: {"description": "Некорректные параметры запроса", "model": ErrorResponse}
    }
)
async def get_notification_history_endpoint(
    user_id: str = Query(None, description="ID пользователя для фильтрации"),
    start_time: str = Query(None, description="Начало периода"),
    end_time: str = Query(None, description="Конец периода"),
    channel: str = Query(None, description="Канал доставки", enum=["email", "sms", "telegram", "push", "webhook"]),
    status: str = Query(None, description="Статус уведомления", enum=["pending", "sent", "failed", "delivered"]),
    limit: int = Query(100, description="Максимальное количество записей", ge=1, le=1000)
):
    """
    Получение истории уведомлений.
    Возвращает историю отправленных уведомлений.
    """
    try:
        # Преобразуем временные параметры
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00')) if start_time else None
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00')) if end_time else None
        
        # Получаем историю уведомлений
        history_data = get_notifications_history(
            user_id=user_id,
            start_time=start_dt,
            end_time=end_dt,
            channel=channel,
            status=status,
            limit=limit
        )
        
        # Преобразуем в модели Pydantic
        result = []
        for item_data in history_data:
            # Парсим JSON поля если нужно
            if item_data.get('metadata'):
                item_data['metadata'] = json.loads(item_data['metadata'])
            
            result.append(NotificationHistoryItem(**item_data))
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ValidationErrorResponse(
                error_code="INVALID_DATE_FORMAT",
                message=f"Invalid date format: {str(e)}",
                details=[{"field": "start_time" if "start_time" in str(e) else "end_time", "error": str(e)}]
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Error getting notification history: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="GET_HISTORY_ERROR",
                message=f"Failed to get notification history: {str(e)}"
            ).model_dump()
        )