from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
import logging
from app.models import (
    UserPreferences, UserPreferencesUpdate,
    ErrorResponse, ValidationErrorResponse
)
from app.database import (
    get_user_preferences, create_or_update_user_preferences,
    delete_user_preferences
)

router = APIRouter(tags=["Users"])
logger = logging.getLogger(__name__)

@router.get(
    "/users/preferences",
    response_model=UserPreferences,
    responses={
        200: {"description": "Успешный запрос", "model": UserPreferences},
        404: {"description": "Настройки для пользователя не найдены", "model": ErrorResponse},
        400: {"description": "Некорректный user_id", "model": ErrorResponse}
    }
)
async def get_user_preferences_endpoint(user_id: str = Query(..., description="ID пользователя")):
    """
    Получение предпочтений уведомлений.
    Возвращает настройки пользователя для получения уведомлений.
    """
    try:
        if not user_id or not user_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code="INVALID_USER_ID",
                    message="User ID cannot be empty"
                ).model_dump()
            )
        
        user_prefs = get_user_preferences(user_id)
        if not user_prefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="PREFERENCES_NOT_FOUND",
                    message=f"No preferences found for user '{user_id}'"
                ).model_dump()
            )
        return UserPreferences(**user_prefs)
    except Exception as e:
        logger.error(f"Error getting user preferences for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="GET_PREFERENCES_ERROR",
                message=f"Failed to get user preferences: {str(e)}"
            ).model_dump()
        )

@router.put(
    "/users/preferences",
    response_model=UserPreferences,
    responses={
        200: {"description": "Настройки успешно обновлены", "model": UserPreferences},
        400: {"description": "Некорректные данные запроса", "model": ErrorResponse}
    }
)
async def update_user_preferences_endpoint(prefs_update: UserPreferencesUpdate):
    """
    Обновление предпочтений уведомлений.
    Обновляет настройки пользователя для получения уведомлений.
    """
    try:
        if not prefs_update.user_id or not prefs_update.user_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code="INVALID_USER_ID",
                    message="User ID cannot be empty"
                ).model_dump()
            )
        
        # Преобразуем Pydantic модель в словарь
        prefs_data = prefs_update.model_dump()
        
        # Обновляем или создаем настройки
        updated_prefs = create_or_update_user_preferences(prefs_update.user_id, prefs_data)
        return UserPreferences(**updated_prefs)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ValidationErrorResponse(
                error_code="VALIDATION_ERROR",
                message=str(e),
                details=[{"field": "preferences", "error": str(e)}]
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="UPDATE_PREFERENCES_ERROR",
                message=f"Failed to update user preferences: {str(e)}"
            ).model_dump()
        )

@router.delete(
    "/users/preferences/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Настройки успешно удалены"},
        404: {"description": "Настройки для пользователя не найдены", "model": ErrorResponse},
        400: {"description": "Некорректный user_id", "model": ErrorResponse}
    }
)
async def delete_user_preferences_endpoint(user_id: str):
    """
    Удаление предпочтений уведомлений.
    Удаляет настройки пользователя для получения уведомлений.
    """
    try:
        if not user_id or not user_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code="INVALID_USER_ID",
                    message="User ID cannot be empty"
                ).model_dump()
            )
        
        if not get_user_preferences(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="PREFERENCES_NOT_FOUND",
                    message=f"No preferences found for user '{user_id}'"
                ).model_dump()
            )
        
        deleted = delete_user_preferences(user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code="DELETE_FAILED",
                    message="Failed to delete user preferences"
                ).model_dump()
            )
        return None
    except Exception as e:
        logger.error(f"Error deleting user preferences for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="DELETE_PREFERENCES_ERROR",
                message=f"Failed to delete user preferences: {str(e)}"
            ).model_dump()
        )