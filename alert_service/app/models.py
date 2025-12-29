from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, time
from typing import List, Optional, Any, Dict, Union
from uuid import UUID
import uuid
from enum import Enum

# === Базовые модели ошибок ===
class ValidationErrorDetail(BaseModel):
    field: str
    error: str

class ValidationErrorResponse(BaseModel):
    error_code: str = "VALIDATION_ERROR"
    message: str
    details: List[ValidationErrorDetail]

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

# === Модели для геозон ===
class GeozoneCoordinates(BaseModel):
    # Для прямоугольных зон
    min_x: Optional[float] = None
    max_x: Optional[float] = None
    min_y: Optional[float] = None
    max_y: Optional[float] = None
    min_z: Optional[float] = Field(0.0, description="Минимальная высота")
    max_z: Optional[float] = Field(3.0, description="Максимальная высота")
    
    # Для круглых зон
    center_x: Optional[float] = None
    center_y: Optional[float] = None
    radius: Optional[float] = None
    
    # Для полигонов
    vertices: Optional[List[Dict[str, float]]] = None

    @field_validator('vertices')
    @classmethod
    def validate_vertices(cls, v: Optional[List[Dict[str, float]]]) -> Optional[List[Dict[str, float]]]:
        if v is not None:
            if len(v) < 3:
                raise ValueError('Polygon must have at least 3 vertices')
            for vertex in v:
                if 'x' not in vertex or 'y' not in vertex:
                    raise ValueError('Each vertex must have x and y coordinates')
        return v

class GeozoneCreate(BaseModel):
    name: str = Field(..., description="Название геозоны")
    zone_type: str = Field(
        ...,
        description="Тип зоны",
        enum=["restricted", "danger", "safe", "work_area", "parking", "other"]
    )
    description: Optional[str] = Field(None, description="Описание зоны")
    shape: str = Field(..., description="Форма зоны", enum=["rectangle", "circle", "polygon"])
    coordinates: GeozoneCoordinates
    buffer_meters: float = Field(0.0, description="Буферная зона вокруг геозоны (в метрах)")
    is_active: bool = Field(True, description="Активна ли геозона")

    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v: GeozoneCoordinates, info):
        shape = info.data.get('shape')
        if shape == "rectangle":
            required_fields = ['min_x', 'max_x', 'min_y', 'max_y']
            for field in required_fields:
                if getattr(v, field) is None:
                    raise ValueError(f'Rectangle geofence requires {field}')
            if v.min_x >= v.max_x:
                raise ValueError('min_x must be less than max_x')
            if v.min_y >= v.max_y:
                raise ValueError('min_y must be less than max_y')
        elif shape == "circle":
            required_fields = ['center_x', 'center_y', 'radius']
            for field in required_fields:
                if getattr(v, field) is None:
                    raise ValueError(f'Circle geofence requires {field}')
            if v.radius <= 0:
                raise ValueError('Radius must be greater than 0')
        elif shape == "polygon":
            if not v.vertices or len(v.vertices) < 3:
                raise ValueError('Polygon must have at least 3 vertices')
        return v

class Geozone(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    geozone_id: UUID
    name: str
    zone_type: str
    description: Optional[str]
    shape: str
    coordinates: Dict[str, Any]
    buffer_meters: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

# === Модели для правил ===
class RuleSchedule(BaseModel):
    days_of_week: List[int] = Field(
        default=[0, 1, 2, 3, 4, 5, 6],
        description="Дни недели (0-воскресенье, 6-суббота)"
    )
    start_time: Optional[str] = Field(
        None,
        description="Время начала (HH:MM)",
        pattern=r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$'
    )
    end_time: Optional[str] = Field(
        None,
        description="Время окончания (HH:MM)",
        pattern=r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$'
    )

    @field_validator('days_of_week')
    @classmethod
    def validate_days_of_week(cls, v: List[int]) -> List[int]:
        if not all(0 <= day <= 6 for day in v):
            raise ValueError('Days of week must be between 0 and 6')
        return list(set(v))  # Удаляем дубликаты

    @field_validator('end_time')
    @classmethod
    def validate_times(cls, v: Optional[str], info) -> Optional[str]:
        start_time = info.data.get('start_time')
        if start_time and v:
            if start_time >= v:
                raise ValueError('end_time must be after start_time')
        return v

class RuleCreate(BaseModel):
    name: str = Field(..., description="Название правила")
    description: Optional[str] = Field(None, description="Описание правила")
    entity_type: str = Field(
        ...,
        description="Тип сущности, к которой применяется правило",
        enum=["employee", "equipment", "all"]
    )
    entity_id: Optional[str] = Field(None, description="Конкретная сущность (если null - применяется ко всем)")
    role_required: Optional[str] = Field(None, description="Требуемая роль (только для сотрудников)")
    geozone_id: UUID = Field(..., description="ID геозоны, к которой применяется правило")
    action: str = Field(..., description="Действие правила", enum=["allow", "deny", "alert"])
    schedule: Optional[RuleSchedule] = Field(None, description="Расписание действия правила")
    threshold_seconds: Optional[int] = Field(
        None, 
        description="Минимальное время в зоне для срабатывания правила",
        ge=0
    )
    severity: str = Field(
        "medium",
        description="Серьезность нарушения",
        enum=["low", "medium", "high", "critical"]
    )
    is_active: bool = Field(True, description="Активно ли правило")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные метаданные")

    @field_validator('entity_id')
    @classmethod
    def validate_entity_specificity(cls, v: Optional[str], info) -> Optional[str]:
        entity_type = info.data.get('entity_type')
        if entity_type == "all" and v is not None:
            raise ValueError('entity_id must be null when entity_type is "all"')
        return v

class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    severity: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class Rule(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    rule_id: UUID
    name: str
    description: Optional[str]
    entity_type: str
    entity_id: Optional[str]
    role_required: Optional[str]
    geozone_id: UUID
    action: str
    schedule: Optional[Dict[str, Any]]
    threshold_seconds: Optional[int]
    severity: str
    is_active: bool
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

# === Модели для проверки позиций ===
class PositionCheck(BaseModel):
    x: float = Field(..., description="Координата X")
    y: float = Field(..., description="Координата Y")
    z: float = Field(0.0, description="Координата Z (высота)")
    timestamp: datetime = Field(..., description="Время позиции")

class PositionValidationRequest(BaseModel):
    entity_id: str = Field(..., description="ID сущности")
    position: PositionCheck

class RuleViolation(BaseModel):
    rule_id: UUID
    rule_name: str
    geozone_id: UUID
    geozone_name: str
    severity: str
    description: str
    timestamp: datetime

class PositionValidationResult(BaseModel):
    entity_id: str
    position: PositionCheck
    is_compliant: bool = Field(..., description="Соответствует ли позиция всем правилам")
    violations: List[RuleViolation] = Field(default_factory=list)
    warnings: List[RuleViolation] = Field(default_factory=list, description="Предупреждения (низкая серьезность)")

# === Модели для инцидентов ===
class IncidentStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"

class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IncidentCreate(BaseModel):
    rule_id: UUID
    entity_id: str
    position: Dict[str, Any]
    severity: str = Field(..., enum=["low", "medium", "high", "critical"])
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class IncidentStatusUpdate(BaseModel):
    status: str = Field(..., enum=["acknowledged", "resolved", "false_positive"])
    resolved_by: Optional[str] = None
    resolution_comment: Optional[str] = None

class Incident(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    incident_id: UUID
    rule_id: UUID
    rule_name: str
    entity_id: str
    entity_name: Optional[str]
    position: Dict[str, Any]
    geozone_id: UUID
    geozone_name: str
    severity: str
    status: str
    description: Optional[str]
    created_at: datetime
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[str]
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    metadata: Optional[Dict[str, Any]]

class IncidentAcknowledgeRequest(BaseModel):
    incident_ids: List[UUID] = Field(..., description="Список ID инцидентов для подтверждения")
    acknowledged_by: str = Field(..., description="Кто подтверждает инциденты")
    comment: Optional[str] = Field(None, description="Комментарий к подтверждению")

# === Модели для оповещений ===
class AlertChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"
    PUSH = "push"
    WEBHOOK = "webhook"

class AlertStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"

class AlertRequest(BaseModel):
    incident_id: UUID
    channels: List[str] = Field(..., enum=["email", "sms", "telegram", "push", "webhook"])
    priority_override: Optional[str] = Field(None, enum=["low", "medium", "high", "critical"])
    custom_message: Optional[str] = None
    recipients: Optional[List[str]] = None
    webhook_url: Optional[str] = None

class AlertHistoryItem(BaseModel):
    alert_id: UUID
    incident_id: UUID
    channels: List[str]
    status: str
    sent_at: Optional[datetime]
    failed_reason: Optional[str]
    metadata: Optional[Dict[str, Any]]

# === Вспомогательные модели ===
class PointCheckRequest(BaseModel):
    x: float = Field(..., description="Координата X")
    y: float = Field(..., description="Координата Y")
    z: float = Field(0.0, description="Координата Z")
    geozone_ids: Optional[List[UUID]] = Field(
        None,
        description="Список ID геозон для проверки (если не указано - проверяются все)"
    )

class GeozoneIntersection(BaseModel):
    geozone_id: UUID
    geozone_name: str
    zone_type: str
    is_inside: bool

class PointCheckResult(BaseModel):
    point: Dict[str, float]
    intersections: List[GeozoneIntersection]

class HealthStatus(BaseModel):
    status: str
    timestamp: datetime
    version: str
    dependencies: Dict[str, Any]

class DatabaseStats(BaseModel):
    geozones_count: int
    rules_count: int
    incidents_count: int
    alerts_count: int
    database_size_mb: float
    last_incident: Optional[datetime] = None
    last_alert: Optional[datetime] = None