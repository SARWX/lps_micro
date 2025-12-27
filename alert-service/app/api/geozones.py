from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
import logging
from uuid import UUID
from app.models import (
    Geozone, GeozoneCreate, PointCheckRequest, PointCheckResult,
    ErrorResponse, ValidationErrorResponse
)
from app.database import (
    create_geozone, get_all_geozones, get_geozone_by_id,
    update_geozone, delete_geozone, check_point_in_geozones
)
from app.incident_processor import process_position

router = APIRouter(tags=["Geozones"])
logger = logging.getLogger(__name__)

@router.get(
    "/geozones",
    response_model=list[Geozone],
    responses={
        200: {"description": "Успешный запрос", "model": list[Geozone]},
        500: {"description": "Ошибка сервера", "model": ErrorResponse}
    }
)
async def get_all_geozones_endpoint():
    """
    Получение списка всех геозон.
    Возвращает список всех зарегистрированных геозон.
    """
    try:
        geozones_data = get_all_geozones()
        return [Geozone(**geozone_data) for geozone_data in geozones_data]
    except Exception as e:
        logger.error(f"Error getting geozones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="DATABASE_ERROR",
                message=f"Failed to get geozones: {str(e)}"
            ).model_dump()
        )

@router.post(
    "/geozones",
    response_model=Geozone,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Геозона успешно создана", "model": Geozone},
        400: {"description": "Некорректные данные геозоны", "model": ErrorResponse}
    }
)
async def create_geozone_endpoint(geozone: GeozoneCreate):
    """
    Создание новой геозоны.
    Создает новую геозону (зону безопасности, доступа и т.д.).
    """
    try:
        geozone_data = geozone.model_dump()
        created_geozone = create_geozone(geozone_data)
        return Geozone(**created_geozone)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ValidationErrorResponse(
                error_code="VALIDATION_ERROR",
                message=str(e),
                details=[{"field": "coordinates", "error": str(e)}]
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Error creating geozone: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="CREATE_GEOZONE_ERROR",
                message=f"Failed to create geozone: {str(e)}"
            ).model_dump()
        )

@router.get(
    "/geozones/{geozone_id}",
    response_model=Geozone,
    responses={
        200: {"description": "Успешный запрос", "model": Geozone},
        404: {"description": "Геозона с указанным ID не найдена", "model": ErrorResponse}
    }
)
async def get_geozone_by_id_endpoint(geozone_id: str):
    """
    Получение информации о конкретной геозоне.
    Возвращает детальную информацию о геозоне.
    """
    try:
        UUID(geozone_id)  # Проверка валидности UUID
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message=f"Invalid geozone_id format: '{geozone_id}'"
            ).model_dump()
        )
    
    try:
        geozone_data = get_geozone_by_id(geozone_id)
        if not geozone_:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="GEOZONE_NOT_FOUND",
                    message=f"Geozone with ID '{geozone_id}' not found"
                ).model_dump()
            )
        return Geozone(**geozone_data)
    except Exception as e:
        logger.error(f"Error getting geozone {geozone_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="DATABASE_ERROR",
                message=f"Failed to get geozone: {str(e)}"
            ).model_dump()
        )

@router.put(
    "/geozones/{geozone_id}",
    response_model=Geozone,
    responses={
        200: {"description": "Геозона успешно обновлена", "model": Geozone},
        404: {"description": "Геозона с указанным ID не найдена", "model": ErrorResponse},
        400: {"description": "Некорректные данные геозоны", "model": ErrorResponse}
    }
)
async def update_geozone_endpoint(geozone_id: str, geozone: GeozoneCreate):
    """
    Обновление геозоны.
    Полностью обновляет информацию о геозоне.
    """
    try:
        UUID(geozone_id)  # Проверка валидности UUID
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message=f"Invalid geozone_id format: '{geozone_id}'"
            ).model_dump()
        )
    
    try:
        if not get_geozone_by_id(geozone_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="GEOZONE_NOT_FOUND",
                    message=f"Geozone with ID '{geozone_id}' not found"
                ).model_dump()
            )
        
        geozone_data = geozone.model_dump()
        updated_geozone = update_geozone(geozone_id, geozone_data)
        if not updated_geozone:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code="UPDATE_FAILED",
                    message="Failed to update geozone"
                ).model_dump()
            )
        return Geozone(**updated_geozone)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ValidationErrorResponse(
                error_code="VALIDATION_ERROR",
                message=str(e),
                details=[{"field": "coordinates", "error": str(e)}]
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Error updating geozone {geozone_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="UPDATE_GEOZONE_ERROR",
                message=f"Failed to update geozone: {str(e)}"
            ).model_dump()
        )

@router.delete(
    "/geozones/{geozone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Геозона успешно удалена"},
        404: {"description": "Геозона с указанным ID не найдена", "model": ErrorResponse}
    }
)
async def delete_geozone_endpoint(geozone_id: str):
    """
    Удаление геозоны.
    Удаляет геозону из системы.
    """
    try:
        UUID(geozone_id)  # Проверка валидности UUID
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message=f"Invalid geozone_id format: '{geozone_id}'"
            ).model_dump()
        )
    
    try:
        if not get_geozone_by_id(geozone_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="GEOZONE_NOT_FOUND",
                    message=f"Geozone with ID '{geozone_id}' not found"
                ).model_dump()
            )
        
        deleted = delete_geozone(geozone_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code="DELETE_FAILED",
                    message="Failed to delete geozone"
                ).model_dump()
            )
        return None
    except Exception as e:
        logger.error(f"Error deleting geozone {geozone_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="DELETE_GEOZONE_ERROR",
                message=f"Failed to delete geozone: {str(e)}"
            ).model_dump()
        )

@router.post(
    "/geozones/check",
    response_model=PointCheckResult,
    responses={
        200: {"description": "Успешная проверка", "model": PointCheckResult},
        400: {"description": "Некорректные данные запроса", "model": ErrorResponse}
    }
)
async def check_point_in_geozones_endpoint(check_request: PointCheckRequest):
    """
    Проверка нахождения точки в геозонах.
    Проверяет, находится ли указанная точка внутри какой-либо геозоны.
    """
    try:
        geozone_ids = None
        if check_request.geozone_ids:
            geozone_ids = [str(geozone_id) for geozone_id in check_request.geozone_ids]
        
        intersections = check_point_in_geozones(
            x=check_request.x,
            y=check_request.y,
            z=check_request.z,
            geozone_ids=geozone_ids
        )
        
        return PointCheckResult(
            point={
                "x": check_request.x,
                "y": check_request.y,
                "z": check_request.z
            },
            intersections=[
                GeozoneIntersection(
                    geozone_id=intersection['geozone_id'],
                    geozone_name=intersection['geozone_name'],
                    zone_type=intersection['zone_type'],
                    is_inside=intersection['is_inside']
                )
                for intersection in intersections
            ]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ValidationErrorResponse(
                error_code="VALIDATION_ERROR",
                message=str(e),
                details=[{"field": "coordinates", "error": str(e)}]
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Error checking point in geozones: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="CHECK_POINT_ERROR",
                message=f"Failed to check point in geozones: {str(e)}"
            ).model_dump()
        )