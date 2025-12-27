from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
import logging
from uuid import UUID
from app.models import (
    Incident, IncidentCreate, IncidentStatusUpdate,
    IncidentAcknowledgeRequest, ErrorResponse, ValidationErrorResponse
)
from app.database import (
    get_incidents, get_incident_by_id, update_incident_status,
    acknowledge_incidents, create_incident
)
from app.incident_processor import create_incident_from_violation

router = APIRouter(tags=["Incidents"])
logger = logging.getLogger(__name__)

@router.get(
    "/incidents",
    response_model=list[Incident],
    responses={
        200: {"description": "Успешный запрос", "model": list[Incident]},
        400: {"description": "Некорректные параметры запроса", "model": ErrorResponse}
    }
)
async def get_incidents_endpoint(
    status: str = Query(None, description="Статус инцидентов для фильтрации", enum=["active", "acknowledged", "resolved", "false_positive"]),
    severity: str = Query(None, description="Серьезность инцидентов", enum=["low", "medium", "high", "critical"]),
    start_time: str = Query(None, description="Начало периода"),
    end_time: str = Query(None, description="Конец периода"),
    limit: int = Query(100, description="Максимальное количество записей", ge=1, le=1000)
):
    """
    Получение списка инцидентов.
    Возвращает список инцидентов с возможностью фильтрации.
    """
    try:
        incidents_data = get_incidents(
            status=status,
            severity=severity,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        return [Incident(**incident_data) for incident_data in incidents_data]
    except Exception as e:
        logger.error(f"Error getting incidents: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="DATABASE_ERROR",
                message=f"Failed to get incidents: {str(e)}"
            ).model_dump()
        )

@router.post(
    "/incidents",
    response_model=Incident,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Инцидент успешно создан", "model": Incident},
        400: {"description": "Некорректные данные инцидента", "model": ErrorResponse}
    }
)
async def create_incident_endpoint(incident: IncidentCreate):
    """
    Создание нового инцидента.
    Создает новый инцидент вручную (для тестирования или специальных случаев).
    """
    try:
        # Проверяем, что rule_id существует
        from app.database import get_rule_by_id
        rule = get_rule_by_id(str(incident.rule_id))
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code="RULE_NOT_FOUND",
                    message=f"Rule with ID '{incident.rule_id}' not found"
                ).model_dump()
            )
        
        # Проверяем, что geozone_id существует
        from app.database import get_geozone_by_id
        geozone = get_geozone_by_id(str(incident.geozone_id))
        if not geozone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code="GEOZONE_NOT_FOUND",
                    message=f"Geozone with ID '{incident.geozone_id}' not found"
                ).model_dump()
            )
        
        incident_data = incident.model_dump()
        created_incident = create_incident(incident_data)
        return Incident(**created_incident)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ValidationErrorResponse(
                error_code="VALIDATION_ERROR",
                message=str(e),
                details=[{"field": "position", "error": str(e)}]
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Error creating incident: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="CREATE_INCIDENT_ERROR",
                message=f"Failed to create incident: {str(e)}"
            ).model_dump()
        )

@router.get(
    "/incidents/{incident_id}",
    response_model=Incident,
    responses={
        200: {"description": "Успешный запрос", "model": Incident},
        404: {"description": "Инцидент с указанным ID не найден", "model": ErrorResponse}
    }
)
async def get_incident_by_id_endpoint(incident_id: str):
    """
    Получение информации об инциденте.
    Возвращает детальную информацию об инциденте.
    """
    try:
        UUID(incident_id)  # Проверка валидности UUID
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message=f"Invalid incident_id format: '{incident_id}'"
            ).model_dump()
        )
    
    try:
        incident_data = get_incident_by_id(incident_id)
        if not incident_:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="INCIDENT_NOT_FOUND",
                    message=f"Incident with ID '{incident_id}' not found"
                ).model_dump()
            )
        return Incident(**incident_data)
    except Exception as e:
        logger.error(f"Error getting incident {incident_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="DATABASE_ERROR",
                message=f"Failed to get incident: {str(e)}"
            ).model_dump()
        )

@router.patch(
    "/incidents/{incident_id}",
    response_model=Incident,
    responses={
        200: {"description": "Статус инцидента успешно обновлен", "model": Incident},
        404: {"description": "Инцидент с указанным ID не найден", "model": ErrorResponse},
        400: {"description": "Некорректные данные запроса", "model": ErrorResponse}
    }
)
async def update_incident_status_endpoint(incident_id: str, status_update: IncidentStatusUpdate):
    """
    Обновление статуса инцидента.
    Обновляет статус инцидента (например, подтверждение, разрешение).
    """
    try:
        UUID(incident_id)  # Проверка валидности UUID
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message=f"Invalid incident_id format: '{incident_id}'"
            ).model_dump()
        )
    
    try:
        if not get_incident_by_id(incident_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="INCIDENT_NOT_FOUND",
                    message=f"Incident with ID '{incident_id}' not found"
                ).model_dump()
            )
        
        updated_incident = update_incident_status(
            incident_id=incident_id,
            status=status_update.status,
            changed_by=status_update.resolved_by,
            comment=status_update.resolution_comment
        )
        
        if not updated_incident:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code="UPDATE_FAILED",
                    message="Failed to update incident status"
                ).model_dump()
            )
        
        return Incident(**updated_incident)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ValidationErrorResponse(
                error_code="VALIDATION_ERROR",
                message=str(e),
                details=[{"field": "status", "error": str(e)}]
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Error updating incident {incident_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="UPDATE_INCIDENT_STATUS_ERROR",
                message=f"Failed to update incident status: {str(e)}"
            ).model_dump()
        )

@router.post(
    "/incidents/acknowledge",
    response_model=dict,
    responses={
        200: {"description": "Инциденты успешно подтверждены", "model": dict},
        400: {"description": "Некорректные данные запроса", "model": ErrorResponse}
    }
)
async def acknowledge_incidents_endpoint(ack_request: IncidentAcknowledgeRequest):
    """
    Подтверждение инцидентов.
    Подтверждает один или несколько инцидентов.
    """
    try:
        # Проверяем валидность UUID
        for incident_id in ack_request.incident_ids:
            try:
                UUID(incident_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error_code="INVALID_UUID",
                        message=f"Invalid incident_id format: '{incident_id}'"
                    ).model_dump()
                )
        
        # Подтверждаем инциденты
        acknowledged_count = acknowledge_incidents(
            incident_ids=ack_request.incident_ids,
            acknowledged_by=ack_request.acknowledged_by,
            comment=ack_request.comment
        )
        
        return {
            "acknowledged": acknowledged_count,
            "total_requested": len(ack_request.incident_ids),
            "success": acknowledged_count > 0 if ack_request.incident_ids else False
        }
    except Exception as e:
        logger.error(f"Error acknowledging incidents: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="ACKNOWLEDGE_INCIDENTS_ERROR",
                message=f"Failed to acknowledge incidents: {str(e)}"
            ).model_dump()
        )