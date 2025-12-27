import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from uuid import uuid4, UUID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "notification_service.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

def init_db():
    """Инициализация базы данных для notification-service"""
    print("=" * 50)
    print("🟢 NOTIFICATION SERVICE INIT_DB STARTED")
    print("=" * 50)
    
    try:
        with get_db() as conn:
            print("✅ Database connection established")
            
            # 1. templates - таблица для хранения шаблонов уведомлений
            print("\n1. Creating templates table...")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                template_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL CHECK(category IN ('security', 'maintenance', 'analytics', 'system')),
                channel TEXT NOT NULL CHECK(channel IN ('email', 'sms', 'telegram', 'push', 'webhook')),
                content TEXT NOT NULL,
                variables TEXT,
                default_priority TEXT NOT NULL CHECK(default_priority IN ('low', 'medium', 'high', 'critical')),
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            print("   ✅ templates table created")
            
            # Индексы для шаблонов
            conn.execute("CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_templates_channel ON templates(channel)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_templates_active ON templates(is_active)")
            
            # 2. user_preferences - таблица для хранения настроек пользователей
            print("\n2. Creating user_preferences table...")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                channels TEXT NOT NULL,
                categories TEXT NOT NULL,
                schedule TEXT NOT NULL,
                contact_details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            print("   ✅ user_preferences table created")
            
            # 3. notifications - таблица для хранения отправленных уведомлений
            print("\n3. Creating notifications table...")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                channel TEXT NOT NULL CHECK(channel IN ('email', 'sms', 'telegram', 'push', 'webhook')),
                recipient TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending', 'sent', 'failed', 'delivered', 'read')),
                sent_at TIMESTAMP NOT NULL,
                delivered_at TIMESTAMP,
                failed_reason TEXT,
                priority TEXT NOT NULL CHECK(priority IN ('low', 'medium', 'high', 'critical')),
                template_id TEXT,
                metadata TEXT,
                FOREIGN KEY (template_id) REFERENCES templates(template_id)
            )
            """)
            print("   ✅ notifications table created")
            
            # Индексы для уведомлений
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_channel ON notifications(channel)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_sent ON notifications(sent_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_priority ON notifications(priority)")
            
            # 4. notification_queue - таблица для очереди отправки уведомлений
            print("\n4. Creating notification_queue table...")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS notification_queue (
                queue_id TEXT PRIMARY KEY,
                notification_id TEXT NOT NULL,
                channel TEXT NOT NULL CHECK(channel IN ('email', 'sms', 'telegram', 'push', 'webhook')),
                recipient TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT NOT NULL CHECK(priority IN ('low', 'medium', 'high', 'critical')),
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                next_retry_at TIMESTAMP,
                status TEXT NOT NULL CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (notification_id) REFERENCES notifications(notification_id)
            )
            """)
            print("   ✅ notification_queue table created")
            
            # Проверка созданных таблиц
            print("\n5. Checking created tables...")
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"   📋 Tables in DB: {[row[0] for row in tables]}")
            
            # Добавление демо-данных если таблицы пустые
            print("\n6. Adding demo data if needed...")
            
            # Шаблоны
            cursor = conn.execute("SELECT COUNT(*) FROM templates")
            if cursor.fetchone()[0] == 0:
                print("   Adding demo templates...")
                demo_templates = [
                    (
                        str(uuid4()),
                        'Нарушение безопасности',
                        'Шаблон для оповещения о нарушениях безопасности',
                        'security',
                        'email',
                        json.dumps({
                            "subject": "🚨 НАРУШЕНИЕ БЕЗОПАСНОСТИ: {{entity_name}} в запрещенной зоне",
                            "body": "Сотрудник {{entity_name}} ({{entity_id}}) обнаружен в запрещенной зоне {{zone_name}}.\nКоординаты: X={{x}}, Y={{y}}, Z={{z}}\nВремя: {{timestamp}}\nУровень критичности: {{severity}}",
                            "html_body": "<h2>🚨 НАРУШЕНИЕ БЕЗОПАСНОСТИ</h2><p><strong>Сотрудник:</strong> {{entity_name}} ({{entity_id}})</p><p><strong>Зона:</strong> {{zone_name}}</p><p><strong>Координаты:</strong> X={{x}}, Y={{y}}, Z={{z}}</p><p><strong>Время:</strong> {{timestamp}}</p><p><strong>Уровень критичности:</strong> {{severity}}</p>"
                        }),
                        json.dumps(['entity_name', 'entity_id', 'zone_name', 'x', 'y', 'z', 'timestamp', 'severity']),
                        'high',
                        1
                    ),
                    (
                        str(uuid4()),
                        'Нарушение безопасности (Telegram)',
                        'Шаблон для Telegram оповещений о нарушениях безопасности',
                        'security',
                        'telegram',
                        json.dumps({
                            "body": "🚨 <b>НАРУШЕНИЕ БЕЗОПАСНОСТИ</b>\n\n<strong>Сотрудник:</strong> {{entity_name}}\n<strong>ID:</strong> {{entity_id}}\n<strong>Зона:</strong> {{zone_name}}\n<strong>Координаты:</strong> X={{x}}, Y={{y}}\n<strong>Время:</strong> {{timestamp}}\n<strong>Критичность:</strong> {{severity}}"
                        }),
                        json.dumps(['entity_name', 'entity_id', 'zone_name', 'x', 'y', 'z', 'timestamp', 'severity']),
                        'high',
                        1
                    ),
                    (
                        str(uuid4()),
                        'Аналитика (ежедневный отчет)',
                        'Шаблон для ежедневных аналитических отчетов',
                        'analytics',
                        'email',
                        json.dumps({
                            "subject": "📊 Ежедневный отчет по перемещениям за {{date}}",
                            "body": "Ежедневный отчет по перемещениям персонала за {{date}}:\n\nОбщее количество сотрудников: {{total_employees}}\nПосещенные зоны: {{zones_visited}}\nНарушений безопасности: {{violations_count}}\n\nПодробный отчет во вложении.",
                            "html_body": "<h2>📊 Ежедневный отчет по перемещениям</h2><p><strong>Дата:</strong> {{date}}</p><p><strong>Общее количество сотрудников:</strong> {{total_employees}}</p><p><strong>Посещенные зоны:</strong> {{zones_visited}}</p><p><strong>Нарушений безопасности:</strong> {{violations_count}}</p><p>Подробный отчет во вложении.</p>"
                        }),
                        json.dumps(['date', 'total_employees', 'zones_visited', 'violations_count']),
                        'low',
                        1
                    ),
                ]
                conn.executemany(
                    """INSERT INTO templates 
                    (template_id, name, description, category, channel, content, variables, default_priority, is_active) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    demo_templates
                )
                print("   ✅ Demo templates added")
            
            # Демо-настройки для пользователя
            cursor = conn.execute("SELECT COUNT(*) FROM user_preferences")
            if cursor.fetchone()[0] == 0:
                print("   Adding demo user preferences...")
                demo_preferences = (
                    'demo-admin',
                    json.dumps({
                        "email": True,
                        "sms": False,
                        "telegram": True,
                        "push": True,
                        "webhook": False
                    }),
                    json.dumps({
                        "security": "high",
                        "maintenance": "medium",
                        "analytics": "low",
                        "system": "medium"
                    }),
                    json.dumps({
                        "do_not_disturb": False,
                        "quiet_hours_start": "22:00",
                        "quiet_hours_end": "08:00"
                    }),
                    json.dumps({
                        "email": "admin@company.com",
                        "phone": "+1234567890",
                        "telegram_id": "admin_telegram",
                        "push_token": "push_token_demo"
                    })
                )
                conn.execute(
                    """INSERT INTO user_preferences 
                    (user_id, channels, categories, schedule, contact_details) 
                    VALUES (?, ?, ?, ?, ?)""",
                    demo_preferences
                )
                print("   ✅ Demo user preferences added")
            
            conn.commit()
            print("\n✅ COMMIT successful")
            
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR in init_db: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 50)
    print("🟢 NOTIFICATION SERVICE INIT_DB COMPLETED")
    print("=" * 50)

# ==================== CRUD для templates ====================
def create_template(template_: dict) -> Dict[str, Any]:
    """Создание нового шаблона"""
    with get_db() as conn:
        template_id = str(uuid4())
        conn.execute("""
        INSERT INTO templates
        (template_id, name, description, category, channel, content, variables, default_priority, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template_id,
            template_data['name'],
            template_data.get('description'),
            template_data['category'],
            template_data['channel'],
            json.dumps(template_data['content']),
            json.dumps(template_data.get('variables', [])),
            template_data.get('default_priority', 'medium'),
            template_data.get('is_active', True)
        ))
        conn.commit()
        return get_template_by_id(template_id)

def get_all_templates(category: Optional[str] = None, 
                     channel: Optional[str] = None) -> List[Dict[str, Any]]:
    """Получение всех шаблонов"""
    with get_db() as conn:
        query = "SELECT * FROM templates WHERE is_active = 1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        if channel:
            query += " AND channel = ?"
            params.append(channel)
        
        query += " ORDER BY created_at DESC"
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            template = dict(row)
            if template.get('content'):
                template['content'] = json.loads(template['content'])
            if template.get('variables'):
                template['variables'] = json.loads(template['variables'])
            result.append(template)
        
        return result

def get_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
    """Получение шаблона по ID"""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM templates WHERE template_id = ?", (template_id,))
        row = cursor.fetchone()
        if row:
            template = dict(row)
            if template.get('content'):
                template['content'] = json.loads(template['content'])
            if template.get('variables'):
                template['variables'] = json.loads(template['variables'])
            return template
        return None

def update_template(template_id: str, update_: dict) -> Optional[Dict[str, Any]]:
    """Обновление шаблона"""
    with get_db() as conn:
        if not get_template_by_id(template_id):
            return None
        
        fields = []
        params = []
        for field in ['name', 'description', 'category', 'channel', 'default_priority', 'is_active']:
            if field in update_:
                fields.append(f"{field} = ?")
                params.append(update_data[field])
        
        if 'content' in update_:
            fields.append("content = ?")
            params.append(json.dumps(update_data['content']))
        
        if 'variables' in update_:
            fields.append("variables = ?")
            params.append(json.dumps(update_data['variables']))
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(template_id)
        
        query = f"UPDATE templates SET {', '.join(fields)} WHERE template_id = ?"
        conn.execute(query, params)
        conn.commit()
        return get_template_by_id(template_id)

def delete_template(template_id: str) -> bool:
    """Удаление шаблона"""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM templates WHERE template_id = ?", (template_id,))
        conn.commit()
        return cursor.rowcount > 0

# ==================== CRUD для user_preferences ====================
def get_user_preferences(user_id: str) -> Optional[Dict[str, Any]]:
    """Получение настроек пользователя"""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            prefs = dict(row)
            if prefs.get('channels'):
                prefs['channels'] = json.loads(prefs['channels'])
            if prefs.get('categories'):
                prefs['categories'] = json.loads(prefs['categories'])
            if prefs.get('schedule'):
                prefs['schedule'] = json.loads(prefs['schedule'])
            if prefs.get('contact_details'):
                prefs['contact_details'] = json.loads(prefs['contact_details'])
            return prefs
        return None

def create_or_update_user_preferences(user_id: str, 
                                     prefs_: dict) -> Dict[str, Any]:
    """Создание или обновление настроек пользователя"""
    with get_db() as conn:
        existing = get_user_preferences(user_id)
        
        channels = json.dumps(prefs_data.get('channels', {}))
        categories = json.dumps(prefs_data.get('categories', {}))
        schedule = json.dumps(prefs_data.get('schedule', {}))
        contact_details = json.dumps(prefs_data.get('contact_details', {}))
        
        if existing:
            # Обновление существующих настроек
            conn.execute("""
            UPDATE user_preferences
            SET channels = ?, categories = ?, schedule = ?, contact_details = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """, (channels, categories, schedule, contact_details, user_id))
        else:
            # Создание новых настроек
            conn.execute("""
            INSERT INTO user_preferences
            (user_id, channels, categories, schedule, contact_details)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, channels, categories, schedule, contact_details))
        
        conn.commit()
        return get_user_preferences(user_id)

def delete_user_preferences(user_id: str) -> bool:
    """Удаление настроек пользователя"""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0

# ==================== CRUD для notifications ====================
def create_notification(notification_: dict) -> Dict[str, Any]:
    """Создание записи об уведомлении"""
    with get_db() as conn:
        notification_id = str(uuid4())
        conn.execute("""
        INSERT INTO notifications
        (notification_id, user_id, channel, recipient, subject, message, status,
         sent_at, priority, template_id, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            notification_id,
            notification_data['user_id'],
            notification_data['channel'],
            notification_data['recipient'],
            notification_data.get('subject'),
            notification_data['message'],
            notification_data.get('status', 'pending'),
            notification_data.get('sent_at', datetime.now().isoformat()),
            notification_data.get('priority', 'medium'),
            notification_data.get('template_id'),
            json.dumps(notification_data.get('metadata', {}))
        ))
        conn.commit()
        return get_notification_by_id(notification_id)

def get_notification_by_id(notification_id: str) -> Optional[Dict[str, Any]]:
    """Получение уведомления по ID"""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM notifications WHERE notification_id = ?", (notification_id,))
        row = cursor.fetchone()
        if row:
            notification = dict(row)
            if notification.get('metadata'):
                notification['metadata'] = json.loads(notification['metadata'])
            return notification
        return None

def get_notifications_history(user_id: Optional[str] = None,
                             start_time: Optional[datetime] = None,
                             end_time: Optional[datetime] = None,
                             channel: Optional[str] = None,
                             status: Optional[str] = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
    """Получение истории уведомлений"""
    with get_db() as conn:
        query = "SELECT * FROM notifications WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if start_time:
            query += " AND sent_at >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND sent_at <= ?"
            params.append(end_time.isoformat())
        
        if channel:
            query += " AND channel = ?"
            params.append(channel)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY sent_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            notification = dict(row)
            if notification.get('metadata'):
                notification['metadata'] = json.loads(notification['metadata'])
            result.append(notification)
        
        return result

def update_notification_status(notification_id: str, status: str,
                              delivered_at: Optional[datetime] = None,
                              failed_reason: Optional[str] = None) -> bool:
    """Обновление статуса уведомления"""
    with get_db() as conn:
        fields = ["status = ?"]
        params = [status]
        
        if status == 'delivered':
            fields.append("delivered_at = ?")
            params.append(delivered_at or datetime.now().isoformat())
        elif status == 'failed' and failed_reason:
            fields.append("failed_reason = ?")
            params.append(failed_reason)
        
        params.append(notification_id)
        
        query = f"UPDATE notifications SET {', '.join(fields)} WHERE notification_id = ?"
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0

# ==================== CRUD для notification_queue ====================
def add_to_queue(notification_id: str, channel: str, recipient: str,
                 message: str, priority: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Добавление уведомления в очередь"""
    with get_db() as conn:
        queue_id = str(uuid4())
        conn.execute("""
        INSERT INTO notification_queue
        (queue_id, notification_id, channel, recipient, message, priority, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            queue_id,
            notification_id,
            channel,
            recipient,
            message,
            priority,
            json.dumps(metadata or {})
        ))
        conn.commit()
        
        cursor = conn.execute("SELECT * FROM notification_queue WHERE queue_id = ?", (queue_id,))
        row = cursor.fetchone()
        if row:
            queue_item = dict(row)
            if queue_item.get('metadata'):
                queue_item['metadata'] = json.loads(queue_item['metadata'])
            return queue_item
        return None

def get_pending_notifications(channel: Optional[str] = None,
                             max_retries: int = 3,
                             limit: int = 100) -> List[Dict[str, Any]]:
    """Получение pending уведомлений из очереди"""
    with get_db() as conn:
        query = """
        SELECT * FROM notification_queue
        WHERE status = 'pending' 
        AND (next_retry_at IS NULL OR next_retry_at <= ?)
        AND retry_count < ?
        """
        params = [datetime.now().isoformat(), max_retries]
        
        if channel:
            query += " AND channel = ?"
            params.append(channel)
        
        query += " ORDER BY priority DESC, created_at ASC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            item = dict(row)
            if item.get('metadata'):
                item['metadata'] = json.loads(item['metadata'])
            result.append(item)
        
        return result

def update_queue_item_status(queue_id: str, status: str,
                           retry_count: Optional[int] = None,
                           next_retry_at: Optional[datetime] = None) -> bool:
    """Обновление статуса элемента очереди"""
    with get_db() as conn:
        fields = ["status = ?"]
        params = [status]
        
        if retry_count is not None:
            fields.append("retry_count = ?")
            params.append(retry_count)
        
        if next_retry_at:
            fields.append("next_retry_at = ?")
            params.append(next_retry_at.isoformat())
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(queue_id)
        
        query = f"UPDATE notification_queue SET {', '.join(fields)} WHERE queue_id = ?"
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0

# ==================== Статистика и очистка ====================
def get_database_stats() -> Dict[str, Any]:
    """Получение статистики по базе данных"""
    with get_db() as conn:
        stats = {}
        
        # Количество записей в каждой таблице
        tables = ['templates', 'user_preferences', 'notifications']
        for table in tables:
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
            stats[f'{table}_count'] = cursor.fetchone()['count']
        
        # Размер базы данных
        cursor = conn.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        cursor = conn.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        stats['database_size_mb'] = round((page_count * page_size) / (1024 * 1024), 2)
        
        # Последнее уведомление
        cursor = conn.execute("SELECT MAX(sent_at) as last_notification FROM notifications")
        stats['last_notification'] = cursor.fetchone()['last_notification']
        
        return stats

def cleanup_old_notifications(days_to_keep: int = 90) -> int:
    """Очистка старых уведомлений"""
    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
    
    with get_db() as conn:
        # Удаляем старые уведомления
        cursor = conn.execute("DELETE FROM notifications WHERE sent_at < ?", (cutoff_date,))
        deleted_notifications = cursor.rowcount
        
        # Удаляем старые записи из очереди
        cursor = conn.execute("DELETE FROM notification_queue WHERE created_at < ?", (cutoff_date,))
        deleted_queue_items = cursor.rowcount
        
        conn.commit()
        
        logger.info(f"Cleaned up {deleted_notifications} notifications and {deleted_queue_items} queue items")
        return deleted_notifications + deleted_queue_items