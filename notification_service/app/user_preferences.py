"""
Модуль для управления настройками пользователей уведомлений.
Содержит бизнес-логику для работы с предпочтениями пользователей,
валидации настроек и применения правил фильтрации уведомлений.
"""
import logging
from datetime import datetime, time
from typing import Dict, Any, Optional, List
from app.models import (
    UserPreferences, NotificationChannel, NotificationPriority,
    UserChannelPreferences, UserCategoryPreferences, UserSchedulePreferences
)
from app.database import get_user_preferences, create_or_update_user_preferences

logger = logging.getLogger(__name__)

class UserPreferencesManager:
    """
    Менеджер настроек пользователей для уведомлений.
    """
    
    def __init__(self):
        self.default_preferences = UserPreferences(
            user_id="default",
            channels=UserChannelPreferences(
                email=True,
                sms=False,
                telegram=True,
                push=True,
                webhook=False
            ),
            categories=UserCategoryPreferences(
                security=NotificationPriority.HIGH,
                maintenance=NotificationPriority.MEDIUM,
                analytics=NotificationPriority.LOW,
                system=NotificationPriority.MEDIUM
            ),
            schedule=UserSchedulePreferences(
                do_not_disturb=False,
                quiet_hours_start="22:00",
                quiet_hours_end="08:00"
            ),
            contact_details={
                "email": "",
                "phone": "",
                "telegram_id": "",
                "push_token": "",
                "webhook_url": ""
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def get_user_preferences(self, user_id: str) -> UserPreferences:
        """
        Получение настроек пользователя с применением настроек по умолчанию.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            UserPreferences: Настройки пользователя
        """
        try:
            db_prefs = get_user_preferences(user_id)
            if db_prefs:
                return UserPreferences(**db_prefs)
            return self._create_default_preferences(user_id)
        except Exception as e:
            logger.error(f"Error getting user preferences for {user_id}: {e}")
            return self._create_default_preferences(user_id)
    
    def _create_default_preferences(self, user_id: str) -> UserPreferences:
        """
        Создание настроек по умолчанию для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            UserPreferences: Настройки по умолчанию
        """
        default_data = self.default_preferences.model_dump()
        default_data['user_id'] = user_id
        default_data['created_at'] = datetime.now()
        default_data['updated_at'] = datetime.now()
        
        # Создаем настройки в базе данных
        create_or_update_user_preferences(user_id, default_data)
        
        return UserPreferences(**default_data)
    
    def should_receive_notification(self, user_id: str, 
                                   channel: NotificationChannel,
                                   category: str,
                                   priority: NotificationPriority) -> bool:
        """
        Проверка, должен ли пользователь получить уведомление.
        
        Args:
            user_id: ID пользователя
            channel: Канал уведомления
            category: Категория уведомления
            priority: Приоритет уведомления
            
        Returns:
            bool: True если пользователь должен получить уведомление
        """
        try:
            prefs = self.get_user_preferences(user_id)
            
            # Проверяем, включен ли канал
            channel_prefs = prefs.channels
            if not getattr(channel_prefs, channel.value, False):
                logger.debug(f"Channel {channel.value} disabled for user {user_id}")
                return False
            
            # Проверяем приоритет для категории
            category_prefs = prefs.categories
            category_priority = getattr(category_prefs, category, None)
            if category_priority:
                # Проверяем минимальный приоритет
                priority_order = {
                    'low': 0,
                    'medium': 1,
                    'high': 2,
                    'critical': 3
                }
                
                min_priority_value = priority_order.get(category_priority.value, 0)
                current_priority_value = priority_order.get(priority.value, 0)
                
                if current_priority_value < min_priority_value:
                    logger.debug(f"Priority {priority.value} below minimum {category_priority.value} for category {category} and user {user_id}")
                    return False
            
            # Проверяем режим "Не беспокоить" и тихое время
            schedule = prefs.schedule
            if schedule.do_not_disturb:
                logger.debug(f"Do not disturb mode enabled for user {user_id}")
                return False
            
            if self._is_quiet_time(schedule):
                # В тихое время разрешаем только критические уведомления
                if priority != NotificationPriority.CRITICAL:
                    logger.debug(f"Quiet time - only critical notifications allowed for user {user_id}")
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error checking notification permissions for user {user_id}: {e}")
            return True  # По умолчанию разрешаем уведомление
    
    def _is_quiet_time(self, schedule: UserSchedulePreferences) -> bool:
        """
        Проверка, является ли текущее время тихим временем.
        
        Args:
            schedule: Настройки расписания пользователя
            
        Returns:
            bool: True если сейчас тихое время
        """
        if not schedule.quiet_hours_start or not schedule.quiet_hours_end:
            return False
        
        try:
            now = datetime.now().time()
            start_time = datetime.strptime(schedule.quiet_hours_start, '%H:%M').time()
            end_time = datetime.strptime(schedule.quiet_hours_end, '%H:%M').time()
            
            # Проверяем, находится ли текущее время в интервале тихого времени
            if start_time <= end_time:
                return start_time <= now <= end_time
            else:
                # Интервал пересекает полночь (например, 22:00 - 08:00)
                return now >= start_time or now <= end_time
        
        except Exception as e:
            logger.error(f"Error checking quiet time: {e}")
            return False
    
    def get_user_contact_details(self, user_id: str, channel: NotificationChannel) -> Optional[str]:
        """
        Получение контактных данных пользователя для конкретного канала.
        
        Args:
            user_id: ID пользователя
            channel: Канал уведомления
            
        Returns:
            Optional[str]: Контактные данные или None если не найдены
        """
        try:
            prefs = self.get_user_preferences(user_id)
            contact_details = prefs.contact_details
            
            if channel == NotificationChannel.EMAIL:
                return contact_details.get('email')
            elif channel == NotificationChannel.SMS:
                return contact_details.get('phone')
            elif channel == NotificationChannel.TELEGRAM:
                return contact_details.get('telegram_id')
            elif channel == NotificationChannel.PUSH:
                return contact_details.get('push_token')
            elif channel == NotificationChannel.WEBHOOK:
                return contact_details.get('webhook_url')
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting contact details for user {user_id} and channel {channel}: {e}")
            return None
    
    def validate_preferences(self, prefs_data: Dict[str, Any]) -> List[str]:
        """
        Валидация настроек пользователя.
        
        Args:
            prefs_data: Данные настроек
            
        Returns:
            List[str]: Список ошибок валидации
        """
        errors = []
        
        # Валидация user_id
        user_id = prefs_data.get('user_id', '').strip()
        if not user_id:
            errors.append("user_id cannot be empty")
        
        # Валидация contact details
        contact_details = prefs_data.get('contact_details', {})
        
        if prefs_data.get('channels', {}).get('email', False):
            email = contact_details.get('email', '')
            if not email or '@' not in email:
                errors.append("Valid email address is required when email notifications are enabled")
        
        if prefs_data.get('channels', {}).get('sms', False):
            phone = contact_details.get('phone', '')
            if not phone or not phone.startswith('+'):
                errors.append("Valid phone number (with country code) is required when SMS notifications are enabled")
        
        if prefs_data.get('channels', {}).get('telegram', False):
            telegram_id = contact_details.get('telegram_id', '')
            if not telegram_id:
                errors.append("Telegram ID is required when Telegram notifications are enabled")
        
        # Валидация расписания
        schedule = prefs_data.get('schedule', {})
        if schedule.get('quiet_hours_start') and schedule.get('quiet_hours_end'):
            try:
                start_time = datetime.strptime(schedule['quiet_hours_start'], '%H:%M').time()
                end_time = datetime.strptime(schedule['quiet_hours_end'], '%H:%M').time()
                
                if start_time == end_time:
                    errors.append("Quiet hours start and end time cannot be the same")
            except ValueError:
                errors.append("Invalid time format for quiet hours (use HH:MM format)")
        
        return errors
    
    def update_user_contact_details(self, user_id: str, contact_details: Dict[str, str]) -> bool:
        """
        Обновление контактных данных пользователя.
        
        Args:
            user_id: ID пользователя
            contact_details: Словарь с контактными данными
            
        Returns:
            bool: True если обновление успешно
        """
        try:
            current_prefs = self.get_user_preferences(user_id)
            if not current_prefs:
                return False
            
            updated_prefs = current_prefs.model_dump()
            updated_prefs['contact_details'].update(contact_details)
            updated_prefs['updated_at'] = datetime.now()
            
            create_or_update_user_preferences(user_id, updated_prefs)
            return True
        
        except Exception as e:
            logger.error(f"Error updating contact details for user {user_id}: {e}")
            return False
    
    def get_active_channels(self, user_id: str) -> List[NotificationChannel]:
        """
        Получение списка активных каналов для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[NotificationChannel]: Список активных каналов
        """
        try:
            prefs = self.get_user_preferences(user_id)
            channels = prefs.channels
            active_channels = []
            
            for channel in NotificationChannel:
                if getattr(channels, channel.value, False):
                    active_channels.append(channel)
            
            return active_channels
        
        except Exception as e:
            logger.error(f"Error getting active channels for user {user_id}: {e}")
            return []
    
    def get_notification_settings_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Получение сводной информации о настройках уведомлений пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Dict[str, Any]: Сводная информация
        """
        try:
            prefs = self.get_user_preferences(user_id)
            
            return {
                "user_id": user_id,
                "active_channels": [channel.value for channel in self.get_active_channels(user_id)],
                "category_priorities": {
                    "security": prefs.categories.security.value,
                    "maintenance": prefs.categories.maintenance.value,
                    "analytics": prefs.categories.analytics.value,
                    "system": prefs.categories.system.value
                },
                "quiet_hours": {
                    "enabled": prefs.schedule.quiet_hours_start is not None and prefs.schedule.quiet_hours_end is not None,
                    "start": prefs.schedule.quiet_hours_start,
                    "end": prefs.schedule.quiet_hours_end,
                    "do_not_disturb": prefs.schedule.do_not_disturb
                },
                "contact_methods": {
                    "email": bool(prefs.contact_details.get('email')),
                    "phone": bool(prefs.contact_details.get('phone')),
                    "telegram": bool(prefs.contact_details.get('telegram_id')),
                    "push": bool(prefs.contact_details.get('push_token')),
                    "webhook": bool(prefs.contact_details.get('webhook_url'))
                }
            }
        
        except Exception as e:
            logger.error(f"Error getting notification settings summary for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "error": str(e)
            }