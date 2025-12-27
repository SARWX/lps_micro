from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
import logging
from uuid import UUID
from app.models import (
    Rule, RuleCreate, RuleUpdate, PositionValidationRequest, PositionValidationResult,
    ErrorResponse, ValidationErrorResponse
)
from app.database import (
    create_rule, get_all_rules, get_rule_by_id,
    update_rule, delete_rule, get_applicable_rules
)
from app.incident_processor import process_position, check_point_in_geozones

router = APIRouter(tags=["Rules"])
logger = logging.getLogger(__name__)

@router.get(
    "/rules",
    response_model=list[Rule],
    responses={
        200: {"description": "Успешный запрос", "model": list[Rule]},
        500: {"description": "Ошибка сервера", "model": ErrorResponse}
    }
)
async def get_all_rules_endpoint(
    is_active: bool = Query(None, description="Фильтр по активности правил")
):
    """
    Получение списка всех правил.
    Возвращает список всех правил доступа и безопасности.
    """
    try:
        rules_data = get_all_rules(is_active=is_active)
        return [Rule(**rule_data) for rule_data in rules_data]
    except Exception as e:
        logger.error(f"Error getting rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="DATABASE_ERROR",
                message=f"Failed to get rules: {str(e)}"
            ).model_dump()
        )

@router.post(
    "/rules",
    response_model=Rule,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Правило успешно создано", "model": Rule},
        400: {"description": "Некорректные данные правила", "model": ErrorResponse}
    }
)
async def create_rule_endpoint(rule: RuleCreate):
    """
    Создание нового правила.
    Создает новое правило доступа или безопасности.
    """
    try:
        # Проверяем, что geozone_id существует
        from app.database import get_geozone_by_id
        geozone = get_geozone_by_id(str(rule.geozone_id))
        if not geozone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code="GEOZONE_NOT_FOUND",
                    message=f"Geozone with ID '{rule.geozone_id}' not found"
                ).model_dump()
            )
        
        rule_data = rule.model_dump()
        created_rule = create_rule(rule_data)
        return Rule(**created_rule)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ValidationErrorResponse(
                error_code="VALIDATION_ERROR",
                message=str(e),
                details=[{"field": "entity_type", "error": str(e)}]
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="CREATE_RULE_ERROR",
                message=f"Failed to create rule: {str(e)}"
            ).model_dump()
        )

@router.get(
    "/rules/{rule_id}",
    response_model=Rule,
    responses={
        200: {"description": "Успешный запрос", "model": Rule},
        404: {"description": "Правило с указанным ID не найдено", "model": ErrorResponse}
    }
)
async def get_rule_by_id_endpoint(rule_id: str):
    """
    Получение информации о правиле.
    Возвращает детальную информацию о правиле.
    """
    try:
        UUID(rule_id)  # Проверка валидности UUID
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message=f"Invalid rule_id format: '{rule_id}'"
            ).model_dump()
        )
    
    try:
        rule_data = get_rule_by_id(rule_id)
        if not rule_:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="RULE_NOT_FOUND",
                    message=f"Rule with ID '{rule_id}' not found"
                ).model_dump()
            )
        return Rule(**rule_data)
    except Exception as e:
        logger.error(f"Error getting rule {rule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="DATABASE_ERROR",
                message=f"Failed to get rule: {str(e)}"
            ).model_dump()
        )

@router.patch(
    "/rules/{rule_id}",
    response_model=Rule,
    responses={
        200: {"description": "Правило успешно обновлено", "model": Rule},
        404: {"description": "Правило с указанным ID не найдено", "model": ErrorResponse},
        400: {"description": "Некорректные данные", "model": ErrorResponse}
    }
)
async def update_rule_endpoint(rule_id: str, rule_update: RuleUpdate):
    """
    Обновление правила.
    Обновляет данные правила (например, активность).
    """
    try:
        UUID(rule_id)  # Проверка валидности UUID
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message=f"Invalid rule_id format: '{rule_id}'"
            ).model_dump()
        )
    
    try:
        if not get_rule_by_id(rule_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="RULE_NOT_FOUND",
                    message=f"Rule with ID '{rule_id}' not found"
                ).model_dump()
            )
        
        update_data = rule_update.model_dump(exclude_unset=True)
        updated_rule = update_rule(rule_id, update_data)
        if not updated_rule:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code="UPDATE_FAILED",
                    message="Failed to update rule"
                ).model_dump()
            )
        return Rule(**updated_rule)
    except Exception as e:
        logger.error(f"Error updating rule {rule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="UPDATE_RULE_ERROR",
                message=f"Failed to update rule: {str(e)}"
            ).model_dump()
        )

@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Правило успешно удалено"},
        404: {"description": "Правило с указанным ID не найдено", "model": ErrorResponse}
    }
)
async def delete_rule_endpoint(rule_id: str):
    """
    Удаление правила.
    Удаляет правило из системы.
    """
    try:
        UUID(rule_id)  # Проверка валидности UUID
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message=f"Invalid rule_id format: '{rule_id}'"
            ).model_dump()
        )
    
    try:
        if not get_rule_by_id(rule_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="RULE_NOT_FOUND",
                    message=f"Rule with ID '{rule_id}' not found"
                ).model_dump()
            )
        
        deleted = delete_rule(rule_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code="DELETE_FAILED",
                    message="Failed to delete rule"
                ).model_dump()
            )
        return None
    except Exception as e:
        logger.error(f"Error deleting rule {rule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="DELETE_RULE_ERROR",
                message=f"Failed to delete rule: {str(e)}"
            ).model_dump()
        )

@router.post(
    "/rules/validate",
    response_model=PositionValidationResult,
    responses={
        200: {"description": "Результат проверки", "model": PositionValidationResult},
        400: {"description": "Некорректные данные запроса", "model": ErrorResponse}
    }
)
async def validate_position_endpoint(validate_request: PositionValidationRequest):
    """
    Проверка позиции на соответствие правилам.
    Проверяет, соответствует ли текущая позиция установленным правилам.
    """
    try:
        # Здесь должна быть логика получения информации о сущности
        # Для примера создаем временную сущность
        entity = {
            'entity_id': validate_request.entity_id,
            'entity_type': 'employee',
            'name': 'Test Entity',
            'role': 'engineer'
        }
        
        # Обрабатываем позицию
        is_compliant, violations = process_position(entity, validate_request.position)
        
        # Формируем результат
        result = PositionValidationResult(
            entity_id=validate_request.entity_id,
            position=validate_request.position,
            is_compliant=is_compliant,
            violations=[
                RuleViolation(
                    rule_id=violation['rule_id'],
                    rule_name=violation['rule_name'],
                    geozone_id=violation['geozone_id'],
                    geozone_name=violation['geozone_name'],
                    severity=violation['severity'],
                    description=violation['description'],
                    timestamp=datetime.fromisoformat(violation['timestamp'])
                )
                for violation in violations
            ],
            warnings=[]
        )
        
        return result
    
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
        logger.error(f"Error validating position: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="VALIDATION_ERROR",
                message=f"Failed to validate position: {str(e)}"
            ).model_dump()
        )