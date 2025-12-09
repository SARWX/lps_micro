from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4


class SingleMeasurement(BaseModel):
    anchor_id: str
    tag_id: str
    distance_m: float = Field(gt=0, description="Расстояние в метрах > 0")


class MeasurementBatch(BaseModel):
    gateway_id: str
    timestamp: datetime
    measurements: List[SingleMeasurement] = Field(min_length=3)


class Position(BaseModel):
    tag_id: str
    x: float  # координата X в метрах
    y: float  # координата Y в метрах
    z: float = 0.0  # высота (можно 0 для 2D)
    timestamp: datetime
    accuracy: float = Field(ge=0, le=10)  # погрешность 0-10 метров


class Anchor(BaseModel):
    anchor_id: str
    x: float
    y: float
    z: float = 0.0
    description: Optional[str] = None
    is_active: bool = True
    last_calibration: Optional[datetime] = None