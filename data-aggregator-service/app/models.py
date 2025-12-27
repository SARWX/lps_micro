from pydantic import BaseModel, Field, field_validator
from datetime import datetime, time
from typing import List, Optional, Any, Dict, Union
from enum import Enum
import uuid

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

# === Модели для отчетов ===
class ZoneOccupancyReport(BaseModel):
    report_id: str
    generated_at: datetime
    period: Dict[str, datetime]
    zones: List[Dict[str, Any]]

class TimeInZoneReport(BaseModel):
    report_id: str
    generated_at: datetime
    period: Dict[str, datetime]
    group_by: str
    data: List[Dict[str, Any]]

class WorkflowEfficiencyReport(BaseModel):
    report_id: str
    generated_at: datetime
    period: Dict[str, datetime]
    zones: List[Dict[str, Any]]

class AnomalyBase(BaseModel):
    anomaly_id: str
    timestamp: datetime
    anomaly_type: str
    entity_id: str
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    zone_id: Optional[str] = None
    zone_name: Optional[str] = None
    position: Optional[Dict[str, float]] = None
    description: Optional[str] = None
    severity: str
    confidence: float
    related_violations: List[str] = []

class AnomalyDetectionReport(BaseModel):
    report_id: str
    generated_at: datetime
    period: Dict[str, datetime]
    anomalies: List[AnomalyBase]

# === Модели для задач агрегации ===
class AggregationTaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class AggregationTaskType(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    CUSTOM = "custom"

class AggregationTask(BaseModel):
    task_id: str
    status: AggregationTaskStatus
    start_time: datetime
    end_time: datetime
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    records_processed: int = 0
    aggregation_type: AggregationTaskType

# === Модель для проверки здоровья сервиса ===
class HealthStatus(BaseModel):
    status: str
    timestamp: datetime
    version: str
    dependencies: Dict[str, Any]

# === Модели для экспорта ===
class ExportFormat(str, Enum):
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"

class ExportStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class ExportInfo(BaseModel):
    export_id: str
    report_id: str
    export_format: ExportFormat
    file_path: str
    created_at: datetime
    file_size: Optional[int] = None
    status: ExportStatus

# === Вспомогательные модели ===
class BehaviorPatternReport(BaseModel):
    entity_id: str
    analysis_period: Dict[str, datetime]
    patterns: Dict[str, Any]
    recommendations: List[str]

class DatabaseStats(BaseModel):
    aggregated_data_count: int
    reports_count: int
    aggregation_tasks_count: int
    anomalies_count: int
    exports_count: int
    database_size_mb: float
    last_data_record: Optional[datetime] = None
    last_report: Optional[datetime] = None