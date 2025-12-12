from fastapi import APIRouter, HTTPException, status
from typing import List

from app.models import Anchor
from app.database import get_all_anchors, get_anchor_by_id, delete_anchor

router = APIRouter()


@router.get(
    "/anchors/{anchor_id}",
    response_model=Anchor,
    responses={
        200: {"description": "Успешный запрос", "model": Anchor},
        404: {"description": "Анкер с указанным ID не найден"}
    }
)
async def get_anchor_endpoint(anchor_id: str):  # ← ИЗМЕНИ ИМЯ
    """
    Получение информации о конкретном анкере.
    
    Возвращает детальную конфигурацию анкера по его ID.
    """
    from app.database import get_anchor_by_id
    
    anchor_data = get_anchor_by_id(anchor_id)  # ← Теперь это функция из БД
    
    if not anchor_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anchor '{anchor_id}' not found"
        )
    
    return Anchor(**anchor_data)


@router.delete(
    "/anchors/{anchor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Анкер успешно удален"},
        404: {"description": "Анкер с указанным ID не найден"}
    }
)
async def delete_anchor_endpoint(anchor_id: str):
    """
    Удаление анкера из системы.
    
    Удаляет конфигурацию анкера. Используйте с осторожностью.
    """
    if not delete_anchor(anchor_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anchor '{anchor_id}' not found"
        )
    
    return None  # 204 No Content
