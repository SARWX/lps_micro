from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
import logging
from uuid import UUID
from app.models import (
    Template, TemplateCreate, TemplateUpdate,
    ErrorResponse, ValidationErrorResponse
)
from app.database import (
    create_template, get_all_templates, get_template_by_id,
    update_template, delete_template
)

router = APIRouter(tags=["Templates"])
logger = logging.getLogger(__name__)

@router.get(
    "/notifications/templates",
    response_model=list[Template],
    responses={
        200: {"description": "Успешный запрос", "model": list[Template]},
        400: {"description": "Некорректные параметры запроса", "model": ErrorResponse}
    }
)
async def get_templates_endpoint(
    category: str = Query(None, description="Категория шаблонов", enum=["security", "maintenance", "analytics", "system"]),
    channel: str = Query(None, description="Канал доставки", enum=["email", "sms", "telegram", "push", "webhook"]),
    limit: int = Query(100, description="Максимальное количество записей", ge=1, le=1000)
):
    """
    Получение списка шаблонов.
    Возвращает список всех доступных шаблонов уведомлений.
    """
    try:
        templates_data = get_all_templates(category=category, channel=channel)
        return [Template(**template_data) for template_data in templates_data[:limit]]
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="GET_TEMPLATES_ERROR",
                message=f"Failed to get templates: {str(e)}"
            ).model_dump()
        )

@router.post(
    "/notifications/templates",
    response_model=Template,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Шаблон успешно создан", "model": Template},
        400: {"description": "Некорректные данные шаблона", "model": ErrorResponse}
    }
)
async def create_template_endpoint(template: TemplateCreate):
    """
    Создание нового шаблона.
    Создает новый шаблон уведомления.
    """
    try:
        template_data = template.model_dump()
        created_template = create_template(template_data)
        return Template(**created_template)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ValidationErrorResponse(
                error_code="VALIDATION_ERROR",
                message=str(e),
                details=[{"field": "content", "error": str(e)}]
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="CREATE_TEMPLATE_ERROR",
                message=f"Failed to create template: {str(e)}"
            ).model_dump()
        )

@router.get(
    "/notifications/templates/{template_id}",
    response_model=Template,
    responses={
        200: {"description": "Успешный запрос", "model": Template},
        404: {"description": "Шаблон не найден", "model": ErrorResponse},
        400: {"description": "Некорректный шаблон ID", "model": ErrorResponse}
    }
)
async def get_template_by_id_endpoint(template_id: str):
    """
    Получение информации о шаблоне.
    Возвращает детальную информацию о шаблоне.
    """
    try:
        UUID(template_id)  # Проверка валидности UUID
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message=f"Invalid template_id format: '{template_id}'"
            ).model_dump()
        )
    
    try:
        template_data = get_template_by_id(template_id)
        if not template_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="TEMPLATE_NOT_FOUND",
                    message=f"Template with ID '{template_id}' not found"
                ).model_dump()
            )
        return Template(**template_data)
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="GET_TEMPLATE_ERROR",
                message=f"Failed to get template: {str(e)}"
            ).model_dump()
        )

@router.put(
    "/notifications/templates/{template_id}",
    response_model=Template,
    responses={
        200: {"description": "Шаблон успешно обновлен", "model": Template},
        404: {"description": "Шаблон не найден", "model": ErrorResponse},
        400: {"description": "Некорректные данные", "model": ErrorResponse}
    }
)
async def update_template_endpoint(template_id: str, template_update: TemplateUpdate):
    """
    Обновление шаблона.
    Обновляет существующий шаблон уведомления.
    """
    try:
        UUID(template_id)  # Проверка валидности UUID
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message=f"Invalid template_id format: '{template_id}'"
            ).model_dump()
        )
    
    try:
        if not get_template_by_id(template_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="TEMPLATE_NOT_FOUND",
                    message=f"Template with ID '{template_id}' not found"
                ).model_dump()
            )
        
        update_data = template_update.model_dump(exclude_unset=True)
        updated_template = update_template(template_id, update_data)
        return Template(**updated_template)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ValidationErrorResponse(
                error_code="VALIDATION_ERROR",
                message=str(e),
                details=[{"field": "content", "error": str(e)}]
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="UPDATE_TEMPLATE_ERROR",
                message=f"Failed to update template: {str(e)}"
            ).model_dump()
        )

@router.delete(
    "/notifications/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Шаблон успешно удален"},
        404: {"description": "Шаблон не найден", "model": ErrorResponse},
        400: {"description": "Некорректный шаблон ID", "model": ErrorResponse}
    }
)
async def delete_template_endpoint(template_id: str):
    """
    Удаление шаблона.
    Удаляет шаблон из системы.
    """
    try:
        UUID(template_id)  # Проверка валидности UUID
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message=f"Invalid template_id format: '{template_id}'"
            ).model_dump()
        )
    
    try:
        if not get_template_by_id(template_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="TEMPLATE_NOT_FOUND",
                    message=f"Template with ID '{template_id}' not found"
                ).model_dump()
            )
        
        deleted = delete_template(template_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code="DELETE_FAILED",
                    message="Failed to delete template"
                ).model_dump()
            )
        return None
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="DELETE_TEMPLATE_ERROR",
                message=f"Failed to delete template: {str(e)}"
            ).model_dump()
        )