"""
Модуль для отправки уведомлений через различные каналы.
Содержит логику доставки уведомлений по email, SMS, Telegram, push и webhook.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
from app.database import (
    add_to_queue, get_pending_notifications, update_queue_item_status,
    update_notification_status, create_notification, get_user_preferences,
    cleanup_old_notifications
)
from app.notification_templates import render_template
from app.models import NotificationChannel, NotificationStatus, NotificationPriority

logger = logging.getLogger(__name__)

class NotificationSender:
    """
    Класс для отправки уведомлений через различные каналы.
    """
    
    def __init__(self):
        self.channel_senders = {
            NotificationChannel.EMAIL: self._send_email,
            NotificationChannel.SMS: self._send_sms,
            NotificationChannel.TELEGRAM: self._send_telegram,
            NotificationChannel.PUSH: self._send_push,
            NotificationChannel.WEBHOOK: self._send_webhook
        }
    
    async def send_notification(self, request_: Dict[str, Any]) -> Dict[str, Any]:
        """
        Отправка уведомления по указанным каналам.
        
        Args:
            request_ Данные для отправки уведомления
            
        Returns:
            Dict[str, Any]: Результат отправки
        """
        try:
            # Создаем запись об уведомлении для каждого получателя
            results = []
            for recipient in request_data['recipients']:
                user_prefs = get_user_preferences(recipient)
                
                for channel in request_data['channels']:
                    # Проверяем, включены ли уведомления для этого канала у пользователя
                    if user_prefs and not self._is_channel_enabled(user_prefs, channel, request_data.get('priority')):
                        logger.info(f"Channel {channel} disabled for user {recipient}, skipping")
                        continue
                    
                    # Обрабатываем шаблон если указан
                    message = request_data['message']
                    subject = request_data.get('subject')
                    metadata = {}
                    
                    if request_data.get('template_id'):
                        template_id = request_data['template_id']
                        context = request_data.get('context', {})
                        context.update({
                            'recipient': recipient,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        rendered = await render_template(template_id, context)
                        if rendered:
                            message = rendered.get('body', message)
                            subject = rendered.get('subject', subject)
                            metadata['template_used'] = template_id
                            metadata['context'] = context
                    
                    # Создаем запись об уведомлении
                    notification_data = {
                        'user_id': recipient,
                        'channel': channel.value,
                        'recipient': recipient,
                        'subject': subject,
                        'message': message,
                        'status': 'pending',
                        'priority': request_data.get('priority', 'medium'),
                        'template_id': request_data.get('template_id'),
                        'metadata': metadata
                    }
                    
                    notification = create_notification(notification_data)
                    
                    # Добавляем в очередь отправки
                    queue_item = add_to_queue(
                        notification_id=notification['notification_id'],
                        channel=channel.value,
                        recipient=recipient,
                        message=message,
                        priority=request_data.get('priority', 'medium'),
                        metadata={
                            'subject': subject,
                            'attachments': request_data.get('attachments'),
                            'webhook_url': request_data.get('webhook_url')
                        }
                    )
                    
                    # Отправляем уведомление в фоновом режиме
                    asyncio.create_task(self._process_queue_item(queue_item))
                    
                    results.append({
                        'notification_id': notification['notification_id'],
                        'recipient': recipient,
                        'channel': channel.value,
                        'status': 'queued'
                    })
            
            return {
                'queued_count': len(results),
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            raise
    
    async def _process_queue_item(self, queue_item: Dict[str, Any]):
        """
        Обработка элемента очереди отправки.
        
        Args:
            queue_item: Элемент очереди
        """
        try:
            notification_id = queue_item['notification_id']
            channel = queue_item['channel']
            recipient = queue_item['recipient']
            message = queue_item['message']
            priority = queue_item['priority']
            metadata = json.loads(queue_item['metadata']) if isinstance(queue_item['metadata'], str) else queue_item['metadata']
            
            # Обновляем статус на 'processing'
            update_queue_item_status(
                queue_id=queue_item['queue_id'],
                status='processing'
            )
            
            # Отправляем уведомление
            channel_enum = NotificationChannel(channel)
            sender_func = self.channel_senders.get(channel_enum)
            
            if not sender_func:
                raise ValueError(f"Unsupported channel: {channel}")
            
            success = await sender_func(
                recipient=recipient,
                message=message,
                priority=priority,
                metadata=metadata
            )
            
            # Обновляем статус уведомления
            status = 'sent' if success else 'failed'
            update_notification_status(
                notification_id=notification_id,
                status=status
            )
            
            # Обновляем статус в очереди
            update_queue_item_status(
                queue_id=queue_item['queue_id'],
                status='completed' if success else 'failed'
            )
            
            if success:
                logger.info(f"Successfully sent notification {notification_id} to {recipient} via {channel}")
            else:
                logger.warning(f"Failed to send notification {notification_id} to {recipient} via {channel}")
                
                # Планируем повторную попытку
                if queue_item['retry_count'] < queue_item['max_retries']:
                    next_retry = datetime.now() + timedelta(minutes=2 ** queue_item['retry_count'])
                    update_queue_item_status(
                        queue_id=queue_item['queue_id'],
                        status='pending',
                        retry_count=queue_item['retry_count'] + 1,
                        next_retry_at=next_retry
                    )
                    logger.info(f"Scheduled retry {queue_item['retry_count'] + 1} for notification {notification_id}")
        
        except Exception as e:
            logger.error(f"Error processing queue item {queue_item.get('queue_id')}: {e}")
            # Обновляем статус на 'failed'
            update_queue_item_status(
                queue_id=queue_item['queue_id'],
                status='failed'
            )
            update_notification_status(
                notification_id=queue_item['notification_id'],
                status='failed',
                failed_reason=str(e)
            )
    
    def _is_channel_enabled(self, user_prefs: Dict[str, Any], 
                          channel: NotificationChannel, 
                          priority: Optional[str] = None) -> bool:
        """
        Проверка, включен ли канал для пользователя с учетом приоритета.
        
        Args:
            user_prefs: Настройки пользователя
            channel: Канал уведомления
            priority: Приоритет уведомления
            
        Returns:
            bool: True если канал включен
        """
        try:
            # Проверяем глобальные настройки канала
            channel_prefs = user_prefs.get('channels', {})
            if not channel_prefs.get(channel.value, True):
                return False
            
            # Проверяем режим "Не беспокоить"
            schedule = user_prefs.get('schedule', {})
            if schedule.get('do_not_disturb', False):
                return False
            
            # Проверяем тихое время
            now = datetime.now().time()
            quiet_start = schedule.get('quiet_hours_start')
            quiet_end = schedule.get('quiet_hours_end')
            
            if quiet_start and quiet_end:
                start_time = datetime.strptime(quiet_start, '%H:%M').time()
                end_time = datetime.strptime(quiet_end, '%H:%M').time()
                
                if start_time <= now <= end_time:
                    # В тихое время разрешаем только критические уведомления
                    if priority != 'critical':
                        return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error checking channel enabled: {e}")
            return True  # По умолчанию разрешаем
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _send_email(self, recipient: str, message: str, 
                        priority: str, meta: Dict[str, Any]) -> bool:
        """
        Отправка email уведомления.
        """
        try:
            logger.info(f"Sending email to {recipient}")
            
            # Здесь должна быть интеграция с почтовым сервисом
            # Для демо всегда успешно
            return True
        
        except Exception as e:
            logger.error(f"Error sending email to {recipient}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _send_sms(self, recipient: str, message: str, 
                      priority: str, meta: Dict[str, Any]) -> bool:
        """
        Отправка SMS уведомления.
        """
        try:
            logger.info(f"Sending SMS to {recipient}")
            
            # Здесь должна быть интеграция с SMS сервисом
            # Для демо всегда успешно
            return True
        
        except Exception as e:
            logger.error(f"Error sending SMS to {recipient}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _send_telegram(self, recipient: str, message: str, 
                           priority: str, meta: Dict[str, Any]) -> bool:
        """
        Отправка Telegram уведомления.
        """
        try:
            logger.info(f"Sending Telegram message to {recipient}")
            
            # Здесь должна быть интеграция с Telegram Bot API
            # Для демо всегда успешно
            return True
        
        except Exception as e:
            logger.error(f"Error sending Telegram message to {recipient}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _send_push(self, recipient: str, message: str, 
                       priority: str, meta: Dict[str, Any]) -> bool:
        """
        Отправка push уведомления.
        """
        try:
            logger.info(f"Sending push notification to {recipient}")
            
            # Здесь должна быть интеграция с push сервисом
            # Для демо всегда успешно
            return True
        
        except Exception as e:
            logger.error(f"Error sending push notification to {recipient}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _send_webhook(self, recipient: str, message: str, 
                          priority: str, meta: Dict[str, Any]) -> bool:
        """
        Отправка webhook уведомления.
        """
        try:
            webhook_url = metadata.get('webhook_url')
            if not webhook_url:
                logger.warning(f"No webhook_url provided for recipient {recipient}")
                return False
            
            logger.info(f"Sending webhook to {webhook_url}")
            
            payload = {
                'recipient': recipient,
                'message': message,
                'priority': priority,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    timeout=10
                ) as response:
                    if response.status in [200, 201, 202]:
                        return True
                    else:
                        logger.error(f"Webhook failed with status {response.status}: {await response.text()}")
                        return False
        
        except Exception as e:
            logger.error(f"Error sending webhook to {recipient}: {e}")
            raise
    
    async def process_pending_notifications(self, batch_size: int = 10):
        """
        Обработка pending уведомлений в очереди.
        
        Args:
            batch_size: Максимальное количество уведомлений за один раз
        """
        try:
            pending_items = get_pending_notifications(limit=batch_size)
            
            if not pending_items:
                return
            
            logger.info(f"Processing {len(pending_items)} pending notifications")
            
            tasks = []
            for item in pending_items:
                tasks.append(self._process_queue_item(item))
            
            await asyncio.gather(*tasks, return_exceptions=True)
        
        except Exception as e:
            logger.error(f"Error processing pending notifications: {e}")
    
    async def get_active_notifications_count(self) -> Dict[str, int]:
        """
        Получение количества активных уведомлений.
        
        Returns:
            Dict[str, int]: Статистика по каналам
        """
        # Здесь должна быть реализация получения статистики
        return {
            'email': 5,
            'sms': 2,
            'telegram': 8,
            'push': 3,
            'webhook': 1
        }