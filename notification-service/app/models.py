from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import List, Optional, Any, Dict
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

# === Модели для уведомлений ===
class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"
    PUSH = "push"
    WEBHOOK = "webhook"

class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"
    READ = "read"

class NotificationRequest(BaseModel):
    recipients: List[str] = Field(..., description="Список получателей")
    message: str = Field(..., description="Текст сообщения")
    subject: Optional[str] = Field(None, description="Тема сообщения (для email)")
    channels: List[NotificationChannel] = Field(..., description="Каналы доставки")
    priority: Optional[NotificationPriority] = Field(
        NotificationPriority.MEDIUM,
        description="Приоритет уведомления"
    )
    template_id: Optional[UUID] = Field(None, description="ID шаблона для форматирования сообщения")
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Контекстные данные для шаблона"
    )
    attachments: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Вложения для email"
    )
    webhook_url: Optional[str] = Field(
        None,
        description="URL для webhook (если канал webhook)",
        pattern=r'^https?://'
    )

class NotificationResponse(BaseModel):
    notification_id: UUID
    timestamp: datetime
    status: NotificationStatus
    channels: List[NotificationChannel]
    recipients_count: int

# === Модели для шаблонов ===
class TemplateCategory(str, Enum):
    SECURITY = "security"
    MAINTENANCE = "maintenance"
    ANALYTICS = "analytics"
    SYSTEM = "system"

class TemplateContent(BaseModel):
    subject: Optional[str] = None
    body: str
    html_body: Optional[str] = None

class TemplateCreate(BaseModel):
    name: str = Field(..., description="Название шаблона")
    description: Optional[str] = Field(None, description="Описание шаблона")
    category: TemplateCategory
    channel: NotificationChannel
    content: Dict[str, Any]
    variables: List[str] = Field(default_factory=list)
    default_priority: NotificationPriority
    is_active: bool = Field(True, description="Активен ли шаблон")

class Template(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    template_id: UUID
    name: str
    description: Optional[str] = None
    category: TemplateCategory
    channel: NotificationChannel
    content: Dict[str, Any]
    variables: List[str] = Field(default_factory=list)
    default_priority: NotificationPriority
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    variables: Optional[List[str]] = None
    default_priority: Optional[NotificationPriority] = None
    is_active: Optional[bool] = None

# === Модели для пользователей ===
class UserChannelPreferences(BaseModel):
    email: bool = Field(True, description="Получать уведомления по email")
    sms: bool = Field(False, description="Получать SMS уведомления")
    telegram: bool = Field(True, description="Получать уведомления в Telegram")
    push: bool = Field(True, description="Получать push-уведомления")
    webhook: bool = Field(False, description="Получать webhook уведомления")

class UserCategoryPreferences(BaseModel):
    security: NotificationPriority = Field(NotificationPriority.HIGH)
    maintenance: NotificationPriority = Field(NotificationPriority.MEDIUM)
    analytics: NotificationPriority = Field(NotificationPriority.LOW)
    system: NotificationPriority = Field(NotificationPriority.MEDIUM)

class UserSchedulePreferences(BaseModel):
    do_not_disturb: bool = Field(False, description="Режим 'Не беспокоить'")
    quiet_hours_start: Optional[str] = Field(
        None,
        description="Начало тихого времени (HH:MM)",
        pattern=r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$'
    )
    quiet_hours_end: Optional[str] = Field(
        None,
        description="Конец тихого времени (HH:MM)",
        pattern=r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$'
    )

class UserContactDetails(BaseModel):
    email: Optional[str] = Field(None, description="Email адрес")
    phone: Optional[str] = Field(None, description="Номер телефона для SMS")
    telegram_id: Optional[str] = Field(None, description="Telegram ID")
    push_token: Optional[str] = Field(None, description="Токен для push-уведомлений")
    webhook_url: Optional[str] = Field(None, description="URL для webhook уведомлений")

class UserPreferences(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str
    channels: UserChannelPreferences
    categories: UserCategoryPreferences
    schedule: UserSchedulePreferences
    contact_details: UserContactDetails
    created_at: datetime
    updated_at: datetime

class UserPreferencesUpdate(BaseModel):
    channels: Optional[UserChannelPreferences] = None
    categories: Optional[UserCategoryPreferences] = None
    schedule: Optional[UserSchedulePreferences] = None
    contact_details: Optional[UserContactDetails] = None

# === Модели для истории ===
class NotificationHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    notification_id: UUID
    user_id: str
    channel: NotificationChannel
    recipient: str
    subject: Optional[str]
    message_preview: str
    status: NotificationStatus
    sent_at: datetime
    delivered_at: Optional[datetime] = None
    failed_reason: Optional[str] = None
    priority: NotificationPriority
    template_id: Optional[UUID] = None
    meta: Optional[Dict[str, Any]] = None

# === Модели для сервиса ===
class ChannelStats(BaseModel):
    channel: NotificationChannel
    total_sent: int
    total_delivered: int
    total_failed: int
    average_delivery_time: float  # в секундах

class ServiceStats(BaseModel):
    total_notifications: int
    notifications_by_channel: List[ChannelStats]
    notifications_by_status: Dict[str, int]
    notifications_by_priority: Dict[str, int]
    last_notification_at: Optional[datetime] = None
    average_delivery_time: float  # в секундах

class DatabaseStats(BaseModel):
    templates_count: int
    user_preferences_count: int
    notifications_count: int
    database_size_mb: float
    last_notification: Optional[datetime] = None

class HealthStatus(BaseModel):
    status: str
    timestamp: datetime
    version: str
    dependencies: Dict[str, Any]