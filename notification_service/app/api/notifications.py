from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
import logging
from app.models import (
    NotificationRequest, NotificationResponse,
    ErrorResponse, ValidationErrorResponse
)
from app.notification_sender import NotificationSender

router = APIRouter(tags=["Notifications"])
logger = logging.getLogger(__name__)

# Инициализируем отправителя уведомлений
notification_sender = NotificationSender()

@router.post(
    "/notifications/send",
    response_model=NotificationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Уведомление поставлено в очередь для отправки", "model": NotificationResponse},
        400: {"description": "Некорректные данные запроса", "model": ErrorResponse},
        404: {"description": "Пользователь или шаблон не найдены", "model": ErrorResponse}
    }
)
async def send_notification_endpoint(request: NotificationRequest):
    """
    Отправка уведомления.
    Отправляет уведомление по указанным каналам.
    """
    try:
        result = await notification_sender.send_notification(request.model_dump())
        return NotificationResponse(
            notification_id="batch-" + str(len(result['results'])),
            timestamp=datetime.now(),
            status="queued",
            channels=request.channels,
            recipients_count=len(request.recipients)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ValidationErrorResponse(
                error_code="VALIDATION_ERROR",
                message=str(e),
                details=[{"field": "template_id", "error": str(e)}]
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="NOTIFICATION_SEND_ERROR",
                message=f"Failed to send notification: {str(e)}"
            ).model_dump()
        )

@router.post(
    "/notifications/test",
    response_model=NotificationResponse,
    responses={
        200: {"description": "Тестовое уведомление успешно отправлено", "model": NotificationResponse},
        400: {"description": "Некорректные данные запроса", "model": ErrorResponse}
    }
)
async def send_test_notification(request: NotificationRequest):
    """
    Отправка тестового уведомления.
    Отправляет тестовое уведомление для проверки работоспособности каналов.
    """
    try:
        # Добавляем префикс к сообщению для тестовых уведомлений
        test_context = request.context.copy() if request.context else {}
        test_context['is_test'] = True
        
        test_request = request.model_dump()
        test_request['message'] = f"[ТЕСТ] {request.message}"
        test_request['context'] = test_context
        
        result = await notification_sender.send_notification(test_request)
        return NotificationResponse(
            notification_id="test-" + str(result['queued_count']),
            timestamp=datetime.now(),
            status="queued",
            channels=request.channels,
            recipients_count=len(request.recipients)
        )
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="TEST_NOTIFICATION_ERROR",
                message=f"Failed to send test notification: {str(e)}"
            ).model_dump()
        )