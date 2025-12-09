from fastapi import APIRouter, HTTPException, Depends
from fastapi import FastAPI
from datetime import datetime

from app.models import MeasurementBatch, SingleMeasurement
from app.database import save_position
from app.trilateration import calculate_position

router = APIRouter()

def get_anchors():
    """Зависимость для получения анкеров"""
    # В реальности из БД, пока из состояния приложения
    from app.main import app
    return app.state.anchors

def get_cache():
    """Зависимость для кэша позиций"""
    from app.main import app
    return app.state.position_cache

@router.post("/measurements", status_code=202)
async def submit_measurements(
    batch: MeasurementBatch,
    anchors: dict = Depends(get_anchors),
    cache: dict = Depends(get_cache)
):
    """
    Прием пакета измерений от анкеров.
    
    - **gateway_id**: ID шлюза
    - **timestamp**: время измерений
    - **measurements**: массив измерений (минимум 3)
    """
    try:
        # Группируем измерения по tag_id
        measurements_by_tag = {}
        for meas in batch.measurements:
            tag_id = meas.tag_id
            if tag_id not in measurements_by_tag:
                measurements_by_tag[tag_id] = []
            measurements_by_tag[tag_id].append({
                "anchor_id": meas.anchor_id,
                "distance_m": meas.distance_m
            })
        
        results = []
        
        # Для каждой метки вычисляем позицию
        for tag_id, tag_measurements in measurements_by_tag.items():
            if len(tag_measurements) >= 3:
                # Вычисляем координаты
                position_data = calculate_position(tag_measurements, anchors)
                
                position = {
                    "tag_id": tag_id,
                    "x": position_data["x"],
                    "y": position_data["y"],
                    "z": position_data["z"],
                    "timestamp": batch.timestamp,
                    "accuracy": position_data["accuracy"]
                }
                
                # Сохраняем в БД
                save_position(position)
                
                # Обновляем кэш
                cache[tag_id] = position
                
                results.append({
                    "tag_id": tag_id,
                    "position": position,
                    "status": "calculated"
                })
            else:
                results.append({
                    "tag_id": tag_id,
                    "status": "insufficient_data",
                    "message": f"Только {len(tag_measurements)} измерений, нужно минимум 3"
                })
        
        return {
            "message": "Measurements accepted for processing",
            "batch_id": f"batch_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))