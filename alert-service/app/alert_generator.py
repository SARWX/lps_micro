"""
Модуль для генерации оповещений.
Содержит логику создания и отправки оповещений при возникновении инцидентов.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import aiohttp
from app.database import create_alert, update_alert_status, get_incident_by_id
from app.models import AlertRequest, AlertChannel, AlertStatus

logger = logging.getLogger(__name__)

class AlertGenerator:
    """
    Генератор оповещений для инцидентов.
    """
    
    def __init__(self):
        self.notification_services = {
            'email': self._send_email_notification,
            'sms': self._send_sms_notification,
            'telegram': self._send_telegram_notification,
            'push': self._send_push_notification,
            'webhook': self._send_webhook_notification
        }
    
    async def generate_alert(self, alert_request: AlertRequest) -> Dict[str, Any]:
        """
        Генерация оповещения на основе запроса.
        
        Args:
            alert_request: Данные для генерации оповещения
        
        Returns:
            Dict[str, Any]: Результат генерации оповещения
        """
        try:
            # Получаем инцидент
            incident = get_incident_by_id(str(alert_request.incident_id))
            if not incident:
                raise ValueError(f"Incident with ID '{alert_request.incident_id}' not found")
            
            # Определяем приоритет оповещения
            priority = alert_request.priority_override or incident['severity']
            
            # Создаем запись об оповещении
            alert_data = {
                'incident_id': str(alert_request.incident_id),
                'channels': alert_request.channels,
                'status': 'pending',
                'metadata': {
                    'priority': priority,
                    'custom_message': alert_request.custom_message,
                    'recipients': alert_request.recipients,
                    'webhook_url': alert_request.webhook_url,
                    'generated_at': datetime.now().isoformat()
                }
            }
            
            alert = create_alert(alert_data)
            logger.info(f"Created alert {alert['alert_id']} for incident {incident['incident_id']}")
            
            # Отправляем оповещения в фоновом режиме
            asyncio.create_task(self._send_alerts(alert, incident, alert_request))
            
            return {
                'alert_id': alert['alert_id'],
                'status': 'queued',
                'channels': alert_request.channels,
                'message': 'Alert queued for sending'
            }
        
        except Exception as e:
            logger.error(f"Error generating alert: {e}")
            raise
    
    async def _send_alerts(self, alert: Dict[str, Any], incident: Dict[str, Any], 
                          alert_request: AlertRequest):
        """
        Асинхронная отправка оповещений по всем каналам.
        
        Args:
            alert: Данные оповещения
            incident: Данные инцидента
            alert_request: Исходный запрос
        """
        try:
            results = []
            
            for channel in alert_request.channels:
                if channel in self.notification_services:
                    try:
                        service_func = self.notification_services[channel]
                        result = await service_func(alert, incident, alert_request)
                        results.append({
                            'channel': channel,
                            'success': result,
                            'timestamp': datetime.now().isoformat()
                        })
                    except Exception as e:
                        logger.error(f"Error sending {channel} notification: {e}")
                        results.append({
                            'channel': channel,
                            'success': False,
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        })
            
            # Обновляем статус оповещения
            all_success = all(r['success'] for r in results if 'success' in r)
            status = 'sent' if all_success else 'failed'
            
            metadata = alert.get('metadata', {})
            metadata['results'] = results
            metadata['completed_at'] = datetime.now().isoformat()
            
            update_alert_status(
                alert['alert_id'],
                status,
                failed_reason=None if all_success else 'One or more channels failed'
            )
            
            if status == 'sent':
                logger.info(f"Alert {alert['alert_id']} sent successfully to all channels")
            else:
                logger.warning(f"Alert {alert['alert_id']} partially failed: {results}")
        
        except Exception as e:
            logger.error(f"Error in _send_alerts: {e}")
    
    async def _send_email_notification(self, alert: Dict[str, Any], incident: Dict[str, Any], 
                                      alert_request: AlertRequest) -> bool:
        """
        Отправка email оповещения.
        """
        # Здесь должна быть интеграция с почтовым сервисом
        logger.info(f"Sending email notification for incident {incident['incident_id']}")
        # Пример реализации:
        # await send_email(
        #     recipients=alert_request.recipients or ['admin@example.com'],
        #     subject=f"ALERT: {incident['severity'].upper()} incident in {incident['geozone_name']}",
        #     body=self._format_email_body(incident, alert_request)
        # )
        return True  # Для демо всегда успешно
    
    async def _send_sms_notification(self, alert: Dict[str, Any], incident: Dict[str, Any], 
                                   alert_request: AlertRequest) -> bool:
        """
        Отправка SMS оповещения.
        """
        logger.info(f"Sending SMS notification for incident {incident['incident_id']}")
        return True  # Для демо всегда успешно
    
    async def _send_telegram_notification(self, alert: Dict[str, Any], incident: Dict[str, Any], 
                                        alert_request: AlertRequest) -> bool:
        """
        Отправка Telegram оповещения.
        """
        logger.info(f"Sending Telegram notification for incident {incident['incident_id']}")
        # Пример реализации с использованием aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                message = self._format_telegram_message(incident, alert_request)
                # Здесь должен быть вызов Telegram Bot API
                # await session.post(
                #     f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                #     json={
                #         "chat_id": TELEGRAM_CHAT_ID,
                #         "text": message,
                #         "parse_Mode": "HTML"
                #     }
                # )
            return True
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False
    
    async def _send_push_notification(self, alert: Dict[str, Any], incident: Dict[str, Any], 
                                    alert_request: AlertRequest) -> bool:
        """
        Отправка push оповещения.
        """
        logger.info(f"Sending push notification for incident {incident['incident_id']}")
        return True  # Для демо всегда успешно
    
    async def _send_webhook_notification(self, alert: Dict[str, Any], incident: Dict[str, Any], 
                                       alert_request: AlertRequest) -> bool:
        """
        Отправка webhook оповещения.
        """
        webhook_url = alert_request.webhook_url
        if not webhook_url:
            logger.warning("Webhook URL not provided for webhook notification")
            return False
        
        logger.info(f"Sending webhook notification to {webhook_url} for incident {incident['incident_id']}")
        
        try:
            payload = {
                'alert_id': alert['alert_id'],
                'incident_id': incident['incident_id'],
                'severity': incident['severity'],
                'geozone_name': incident['geozone_name'],
                'entity_id': incident['entity_id'],
                'entity_name': incident['entity_name'],
                'timestamp': datetime.now().isoformat(),
                'description': incident['description'],
                'position': incident['position'],
                'metadata': alert.get('metadata', {})
            }
            
            headers = {'Content-Type': 'application/json'}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload, headers=headers, timeout=10) as response:
                    if response.status in [200, 201, 202]:
                        return True
                    else:
                        logger.error(f"Webhook failed with status {response.status}: {await response.text()}")
                        return False
        
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            return False
    
    def _format_telegram_message(self, incident: Dict[str, Any], alert_request: AlertRequest) -> str:
        """Форматирование сообщения для Telegram"""
        severity_emoji = {
            'low': '🟡',
            'medium': '🟠', 
            'high': '🔴',
            'critical': '🔴🔴'
        }
        
        severity_text = severity_emoji.get(incident['severity'], '⚪') + f" {incident['severity'].upper()}"
        
        message = f"""
🚨 <b>SECURITY ALERT</b> 🚨

<b>Severity:</b> {severity_text}
<b>Location:</b> {incident['geozone_name']}
<b>Entity:</b> {incident['entity_name']} ({incident['entity_id']})
<b>Time:</b> {incident['created_at']}

<b>Description:</b>
{incident['description']}

<b>Position:</b>
X: {incident['position']['x']}, Y: {incident['position']['y']}, Z: {incident['position']['z']}

#alert #{incident['severity']} #{incident['geozone_name'].replace(' ', '_')}
"""
        
        if alert_request.custom_message:
            message += f"\n\n<b>Custom Message:</b>\n{alert_request.custom_message}"
        
        return message
    
    def _format_email_body(self, incident: Dict[str, Any], alert_request: AlertRequest) -> str:
        """Форматирование тела email сообщения"""
        # Реализация форматирования email
        return f"""
Security Alert - {incident['severity'].upper()}

Incident ID: {incident['incident_id']}
Timestamp: {incident['created_at']}
Location: {incident['geozone_name']}
Entity: {incident['entity_name']} ({incident['entity_id']})
Description: {incident['description']}

Position:
X: {incident['position']['x']}
Y: {incident['position']['y']}
Z: {incident['position']['z']}

Please take appropriate action immediately.
"""
    
    async def get_active_alerts_count(self) -> Dict[str, int]:
        """
        Получение количества активных оповещений по каналам.
        
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