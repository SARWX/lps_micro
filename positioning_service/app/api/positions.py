from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime
from typing import Optional

from app.models import Position
from app.database import get_latest_position

router = APIRouter()

def get_cache():
    from app.main import app
    return app.state.position_cache

@router.get("/positions/current/{tag_id}", response_model=Position)
async def get_current_position(
    tag_id: str,
    cache: dict = Depends(get_cache)
):
    """Получение последней известной позиции метки"""
    # Сначала проверяем кэш
    if tag_id in cache:
        return cache[tag_id]
    
    # Если нет в кэше, ищем в БД
    position = get_latest_position(tag_id)
    if position:
        # Обновляем кэш
        cache[tag_id] = position
        return position
    
    raise HTTPException(
        status_code=404,
        detail=f"Position for tag '{tag_id}' not found"
    )

@router.get("/positions/history/{tag_id}", response_model=list[Position])
async def get_position_history(
    tag_id: str,
    start_time: datetime = Query(..., description="Начало периода"),
    end_time: datetime = Query(..., description="Конец периода"),
    limit: int = Query(1000, ge=1, le=10000)
):
    """Получение истории перемещений за период"""
    # Заглушка - в реальности запрос к БД
    # SELECT * FROM positions WHERE tag_id = ? 
    # AND timestamp BETWEEN ? AND ? LIMIT ?
    
    from app.database import get_db
    import sqlite3
    
    try:
        with get_db() as conn:
            rows = conn.execute(
                """SELECT * FROM positions 
                   WHERE tag_id = ? AND timestamp BETWEEN ? AND ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (tag_id, start_time, end_time, limit)
            ).fetchall()
            
            if not rows:
                return []
            
            return [dict(row) for row in rows]
            
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")