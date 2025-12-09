from fastapi import APIRouter, HTTPException
from typing import List

from app.models import Anchor

router = APIRouter()

@router.get("/anchors", response_model=List[Anchor])
async def get_all_anchors():
    """Получение списка всех анкеров"""
    from app.main import app
    anchors = app.state.anchors
    
    result = []
    for anchor_id, data in anchors.items():
        result.append(Anchor(
            anchor_id=anchor_id,
            x=data["x"],
            y=data["y"],
            z=data["z"],
            description=data.get("description"),
            is_active=True
        ))
    
    return result

@router.get("/anchors/{anchor_id}", response_model=Anchor)
async def get_anchor(anchor_id: str):
    """Получение информации о конкретном анкере"""
    from app.main import app
    anchors = app.state.anchors
    
    if anchor_id not in anchors:
        raise HTTPException(status_code=404, detail="Anchor not found")
    
    data = anchors[anchor_id]
    return Anchor(
        anchor_id=anchor_id,
        x=data["x"],
        y=data["y"],
        z=data["z"],
        description=data.get("description"),
        is_active=True
    )