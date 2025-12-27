import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from uuid import uuid4, UUID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "alert_service.db"

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
    """Инициализация базы данных для alert-service"""
    print("=" * 50)
    print("🟢 ALERT SERVICE INIT_DB STARTED")
    print("=" * 50)
    
    try:
        with get_db() as conn:
            print("✅ Database connection established")
            
            # 1. geozones - таблица для хранения геозон
            print("\n1. Creating geozones table...")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS geozones (
                geozone_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                zone_type TEXT NOT NULL CHECK(zone_type IN ('restricted', 'danger', 'safe', 'work_area', 'parking', 'other')),
                description TEXT,
                shape TEXT NOT NULL CHECK(shape IN ('rectangle', 'circle', 'polygon')),
                coordinates TEXT NOT NULL,
                buffer_meters REAL DEFAULT 0.0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            print("   ✅ geozones table created")
            
            # Индексы для геозон
            conn.execute("CREATE INDEX IF NOT EXISTS idx_geozones_zone_type ON geozones(zone_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_geozones_active ON geozones(is_active)")
            
            # 2. rules - таблица для хранения правил доступа
            print("\n2. Creating rules table...")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                rule_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                entity_type TEXT NOT NULL CHECK(entity_type IN ('employee', 'equipment', 'all')),
                entity_id TEXT,
                role_required TEXT,
                geozone_id TEXT NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('allow', 'deny', 'alert')),
                schedule TEXT,
                threshold_seconds INTEGER,
                severity TEXT NOT NULL CHECK(severity IN ('low', 'medium', 'high', 'critical')),
                is_active INTEGER DEFAULT 1,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (geozone_id) REFERENCES geozones(geozone_id)
            )
            """)
            print("   ✅ rules table created")
            
            # Индексы для правил
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_entity ON rules(entity_type, entity_id, is_active)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_geozone ON rules(geozone_id, is_active)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_severity ON rules(severity)")
            
            # 3. incidents - таблица для хранения инцидентов
            print("\n3. Creating incidents table...")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                rule_id TEXT NOT NULL,
                rule_name TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                entity_name TEXT,
                position TEXT NOT NULL,
                geozone_id TEXT NOT NULL,
                geozone_name TEXT NOT NULL,
                severity TEXT NOT NULL CHECK(severity IN ('low', 'medium', 'high', 'critical')),
                status TEXT NOT NULL CHECK(status IN ('active', 'acknowledged', 'resolved', 'false_positive')),
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged_at TIMESTAMP,
                acknowledged_by TEXT,
                resolved_at TIMESTAMP,
                resolved_by TEXT,
                metadata TEXT,
                FOREIGN KEY (rule_id) REFERENCES rules(rule_id),
                FOREIGN KEY (geozone_id) REFERENCES geozones(geozone_id)
            )
            """)
            print("   ✅ incidents table created")
            
            # Индексы для инцидентов
            conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status, severity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_entity ON incidents(entity_id, created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents(created_at)")
            
            # 4. alerts - таблица для хранения истории оповещений
            print("\n4. Creating alerts table...")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                channels TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending', 'sent', 'failed')),
                sent_at TIMESTAMP,
                failed_reason TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)
            )
            """)
            print("   ✅ alerts table created")
            
            # Индексы для оповещений
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_incident ON alerts(incident_id)")
            
            # 5. incident_histories - таблица для хранения истории изменений инцидентов
            print("\n5. Creating incident_histories table...")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS incident_histories (
                history_id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                changed_by TEXT,
                change_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                comment TEXT,
                FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)
            )
            """)
            print("   ✅ incident_histories table created")
            
            # Проверка созданных таблиц
            print("\n6. Checking created tables...")
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"   📋 Tables in DB: {[row[0] for row in tables]}")
            
            # Добавление демо-данных если таблицы пустые
            print("\n7. Adding demo data if needed...")
            
            # Геозоны
            cursor = conn.execute("SELECT COUNT(*) FROM geozones")
            if cursor.fetchone()[0] == 0:
                print("   Adding demo geozones...")
                demo_geozones = [
                    (
                        str(uuid4()),
                        'Серверная комната',
                        'restricted',
                        'Запрещенная зона для посторонних',
                        'rectangle',
                        json.dumps({
                            "min_x": 10.0, "max_x": 15.0,
                            "min_y": 5.0, "max_y": 10.0,
                            "min_z": 0.0, "max_z": 3.0
                        }),
                        0.5,
                        1
                    ),
                    (
                        str(uuid4()),
                        'Опасная зона станка',
                        'danger',
                        'Опасная зона вокруг станка',
                        'circle',
                        json.dumps({
                            "center_x": 25.0, "center_y": 30.0,
                            "radius": 3.0
                        }),
                        0.0,
                        1
                    ),
                    (
                        str(uuid4()),
                        'Зона отдыха',
                        'safe',
                        'Зона отдыха сотрудников',
                        'rectangle',
                        json.dumps({
                            "min_x": 30.0, "max_x": 40.0,
                            "min_y": 20.0, "max_y": 25.0,
                            "min_z": 0.0, "max_z": 3.0
                        }),
                        0.0,
                        1
                    ),
                ]
                conn.executemany(
                    """INSERT INTO geozones 
                    (geozone_id, name, zone_type, description, shape, coordinates, buffer_meters, is_active) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    demo_geozones
                )
                print("   ✅ Demo geozones added")
            
            # Правила
            cursor = conn.execute("SELECT COUNT(*) FROM rules")
            if cursor.fetchone()[0] == 0:
                # Получаем ID геозон для создания правил
                cursor = conn.execute("SELECT geozone_id, zone_type FROM geozones")
                geozones = cursor.fetchall()
                if geozones:
                    print("   Adding demo rules...")
                    geozone_map = {zone['zone_type']: zone['geozone_id'] for zone in geozones}
                    
                    demo_rules = []
                    if 'restricted' in geozone_map:
                        demo_rules.append((
                            str(uuid4()),
                            'Только IT в серверную',
                            'Доступ в серверную комнату только для сотрудников IT отдела',
                            'employee',
                            None,
                            'engineer',
                            geozone_map['restricted'],
                            'allow',
                            json.dumps({"days_of_week": [0, 1, 2, 3, 4, 5, 6], "start_time": "00:00", "end_time": "23:59"}),
                            5,  # 5 секунд
                            'high',
                            1,
                            json.dumps({"auto_generated": True})
                        ))
                    
                    if 'danger' in geozone_map:
                        demo_rules.append((
                            str(uuid4()),
                            'Опасная зона - всем запрещено',
                            'Никто не может входить в опасную зону станка',
                            'all',
                            None,
                            None,
                            geozone_map['danger'],
                            'deny',
                            json.dumps({"days_of_week": [0, 1, 2, 3, 4, 5, 6], "start_time": "00:00", "end_time": "23:59"}),
                            2,  # 2 секунды
                            'critical',
                            1,
                            json.dumps({"auto_generated": True})
                        ))
                    
                    if demo_rules:
                        conn.executemany(
                            """INSERT INTO rules 
                            (rule_id, name, description, entity_type, entity_id, role_required,
                             geozone_id, action, schedule, threshold_seconds, severity, is_active, metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            demo_rules
                        )
                        print("   ✅ Demo rules added")
            
            conn.commit()
            print("\n✅ COMMIT successful")
            
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR in init_db: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 50)
    print("🟢 ALERT SERVICE INIT_DB COMPLETED")
    print("=" * 50)

# ==================== CRUD для geozones ====================
def create_geozone(geozone_: dict) -> Dict[str, Any]:
    """Создание новой геозоны"""
    with get_db() as conn:
        geozone_id = str(uuid4())
        conn.execute("""
        INSERT INTO geozones
        (geozone_id, name, zone_type, description, shape, coordinates, buffer_meters, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            geozone_id,
            geozone_data['name'],
            geozone_data['zone_type'],
            geozone_data.get('description'),
            geozone_data['shape'],
            json.dumps(geozone_data['coordinates']),
            geozone_data.get('buffer_meters', 0.0),
            geozone_data.get('is_active', True)
        ))
        conn.commit()
        return get_geozone_by_id(geozone_id)

def get_all_geozones() -> List[Dict[str, Any]]:
    """Получение всех геозон"""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM geozones ORDER BY name")
        rows = cursor.fetchall()
        result = []
        for row in rows:
            geozone = dict(row)
            if geozone.get('coordinates'):
                geozone['coordinates'] = json.loads(geozone['coordinates'])
            result.append(geozone)
        return result

def get_geozone_by_id(geozone_id: str) -> Optional[Dict[str, Any]]:
    """Получение геозоны по ID"""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM geozones WHERE geozone_id = ?", (geozone_id,))
        row = cursor.fetchone()
        if row:
            geozone = dict(row)
            if geozone.get('coordinates'):
                geozone['coordinates'] = json.loads(geozone['coordinates'])
            return geozone
        return None

def update_geozone(geozone_id: str, geozone_: dict) -> Optional[Dict[str, Any]]:
    """Обновление геозоны"""
    with get_db() as conn:
        if not get_geozone_by_id(geozone_id):
            return None
        
        fields = []
        params = []
        for field in ['name', 'zone_type', 'description', 'shape', 'buffer_meters', 'is_active']:
            if field in geozone_:
                fields.append(f"{field} = ?")
                params.append(geozone_data[field])
        
        if 'coordinates' in geozone_:
            fields.append("coordinates = ?")
            params.append(json.dumps(geozone_data['coordinates']))
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(geozone_id)
        
        query = f"UPDATE geozones SET {', '.join(fields)} WHERE geozone_id = ?"
        conn.execute(query, params)
        conn.commit()
        return get_geozone_by_id(geozone_id)

def delete_geozone(geozone_id: str) -> bool:
    """Удаление геозоны"""
    with get_db() as conn:
        # Сначала удаляем связанные правила
        conn.execute("DELETE FROM rules WHERE geozone_id = ?", (geozone_id,))
        # Удаляем геозону
        cursor = conn.execute("DELETE FROM geozones WHERE geozone_id = ?", (geozone_id,))
        conn.commit()
        return cursor.rowcount > 0

def check_point_in_geozones(x: float, y: float, z: float = 0.0,
                          geozone_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Проверка нахождения точки в геозонах"""
    with get_db() as conn:
        query = "SELECT * FROM geozones WHERE is_active = 1"
        params = []
        
        if geozone_ids:
            placeholders = ','.join(['?'] * len(geozone_ids))
            query += f" AND geozone_id IN ({placeholders})"
            params.extend(geozone_ids)
        
        cursor = conn.execute(query, params)
        geozones = cursor.fetchall()
        
        result = []
        for row in geozones:
            geozone = dict(row)
            if geozone.get('coordinates'):
                geozone['coordinates'] = json.loads(geozone['coordinates'])
            
            # Проверка нахождения точки в геозоне
            is_inside = False
            coordinates = geozone['coordinates']
            
            if geozone['shape'] == 'rectangle':
                min_x = coordinates.get('min_x', 0) - geozone['buffer_meters']
                max_x = coordinates.get('max_x', 0) + geozone['buffer_meters']
                min_y = coordinates.get('min_y', 0) - geozone['buffer_meters']
                max_y = coordinates.get('max_y', 0) + geozone['buffer_meters']
                min_z = coordinates.get('min_z', 0) - geozone['buffer_meters']
                max_z = coordinates.get('max_z', 3) + geozone['buffer_meters']
                
                is_inside = (min_x <= x <= max_x and
                            min_y <= y <= max_y and
                            min_z <= z <= max_z)
            
            elif geozone['shape'] == 'circle':
                center_x = coordinates.get('center_x', 0)
                center_y = coordinates.get('center_y', 0)
                radius = coordinates.get('radius', 0) + geozone['buffer_meters']
                distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                is_inside = distance <= radius
            
            if is_inside:
                result.append({
                    'geozone_id': geozone['geozone_id'],
                    'geozone_name': geozone['name'],
                    'zone_type': geozone['zone_type'],
                    'is_inside': True
                })
        
        return result

# ==================== CRUD для rules ====================
def create_rule(rule_: dict) -> Dict[str, Any]:
    """Создание нового правила"""
    with get_db() as conn:
        rule_id = str(uuid4())
        conn.execute("""
        INSERT INTO rules
        (rule_id, name, description, entity_type, entity_id, role_required,
         geozone_id, action, schedule, threshold_seconds, severity, is_active, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule_id,
            rule_data['name'],
            rule_data.get('description'),
            rule_data['entity_type'],
            rule_data.get('entity_id'),
            rule_data.get('role_required'),
            str(rule_data['geozone_id']),
            rule_data['action'],
            json.dumps(rule_data.get('schedule')) if rule_data.get('schedule') else None,
            rule_data.get('threshold_seconds'),
            rule_data.get('severity', 'medium'),
            rule_data.get('is_active', True),
            json.dumps(rule_data.get('metadata')) if rule_data.get('metadata') else None
        ))
        conn.commit()
        return get_rule_by_id(rule_id)

def get_all_rules(is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
    """Получение всех правил с фильтрацией по активности"""
    with get_db() as conn:
        query = "SELECT * FROM rules"
        params = []
        
        if is_active is not None:
            query += " WHERE is_active = ?"
            params.append(1 if is_active else 0)
        
        query += " ORDER BY created_at DESC"
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            rule = dict(row)
            if rule.get('schedule'):
                rule['schedule'] = json.loads(rule['schedule'])
            if rule.get('metadata'):
                rule['metadata'] = json.loads(rule['metadata'])
            result.append(rule)
        
        return result

def get_rule_by_id(rule_id: str) -> Optional[Dict[str, Any]]:
    """Получение правила по ID"""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM rules WHERE rule_id = ?", (rule_id,))
        row = cursor.fetchone()
        if row:
            rule = dict(row)
            if rule.get('schedule'):
                rule['schedule'] = json.loads(rule['schedule'])
            if rule.get('metadata'):
                rule['metadata'] = json.loads(rule['metadata'])
            return rule
        return None

def update_rule(rule_id: str, update_: dict) -> Optional[Dict[str, Any]]:
    """Обновление правила"""
    with get_db() as conn:
        if not get_rule_by_id(rule_id):
            return None
        
        fields = []
        params = []
        for field in ['name', 'description', 'is_active', 'severity', 'threshold_seconds']:
            if field in update_:
                fields.append(f"{field} = ?")
                params.append(update_data[field])
        
        if 'schedule' in update_:
            fields.append("schedule = ?")
            params.append(json.dumps(update_data['schedule']))
        
        if 'metadata' in update_:
            fields.append("metadata = ?")
            params.append(json.dumps(update_data['metadata']))
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(rule_id)
        
        query = f"UPDATE rules SET {', '.join(fields)} WHERE rule_id = ?"
        conn.execute(query, params)
        conn.commit()
        return get_rule_by_id(rule_id)

def delete_rule(rule_id: str) -> bool:
    """Удаление правила"""
    with get_db() as conn:
        # Сначала удаляем связанные инциденты
        conn.execute("DELETE FROM incidents WHERE rule_id = ?", (rule_id,))
        # Удаляем правило
        cursor = conn.execute("DELETE FROM rules WHERE rule_id = ?", (rule_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_applicable_rules(entity_type: str, entity_id: Optional[str] = None,
                        role: Optional[str] = None) -> List[Dict[str, Any]]:
    """Получение правил, применимых к конкретной сущности"""
    with get_db() as conn:
        # Правила, которые применяются ко всем (entity_type = 'all')
        query_all = """
        SELECT r.*, g.name as geozone_name, g.zone_type
        FROM rules r
        JOIN geozones g ON r.geozone_id = g.geozone_id
        WHERE r.is_active = 1 AND g.is_active = 1
        AND r.entity_type = 'all'
        """
        
        # Правила для конкретного типа сущности
        query_type = """
        SELECT r.*, g.name as geozone_name, g.zone_type
        FROM rules r
        JOIN geozones g ON r.geozone_id = g.geozone_id
        WHERE r.is_active = 1 AND g.is_active = 1
        AND r.entity_type = ?
        """
        
        # Правила для конкретной сущности
        query_entity = """
        SELECT r.*, g.name as geozone_name, g.zone_type
        FROM rules r
        JOIN geozones g ON r.geozone_id = g.geozone_id
        WHERE r.is_active = 1 AND g.is_active = 1
        AND r.entity_type = ? AND r.entity_id = ?
        """
        
        result = []
        
        # 1. Правила для всех
        cursor = conn.execute(query_all)
        result.extend([dict(row) for row in cursor.fetchall()])
        
        # 2. Правила для типа сущности
        cursor = conn.execute(query_type, (entity_type,))
        result.extend([dict(row) for row in cursor.fetchall()])
        
        # 3. Правила для конкретной сущности
        if entity_id:
            cursor = conn.execute(query_entity, (entity_type, entity_id))
            result.extend([dict(row) for row in cursor.fetchall()])
        
        # Парсим JSON поля и фильтруем по роли если нужно
        filtered_result = []
        for rule in result:
            if rule.get('schedule'):
                rule['schedule'] = json.loads(rule['schedule'])
            if rule.get('metadata'):
                rule['metadata'] = json.loads(rule['metadata'])
            
            # Проверка требования к роли
            if rule.get('role_required') and role != rule['role_required']:
                continue
            
            filtered_result.append(rule)
        
        return filtered_result

# ==================== CRUD для incidents ====================
def create_incident(incident_: dict) -> Dict[str, Any]:
    """Создание нового инцидента"""
    with get_db() as conn:
        incident_id = str(uuid4())
        conn.execute("""
        INSERT INTO incidents
        (incident_id, rule_id, rule_name, entity_id, entity_name, position,
         geozone_id, geozone_name, severity, status, description, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            incident_id,
            str(incident_data['rule_id']),
            incident_data['rule_name'],
            incident_data['entity_id'],
            incident_data.get('entity_name'),
            json.dumps(incident_data['position']),
            str(incident_data['geozone_id']),
            incident_data['geozone_name'],
            incident_data['severity'],
            'active',
            incident_data.get('description'),
            json.dumps(incident_data.get('metadata')) if incident_data.get('metadata') else None
        ))
        
        # Создаем запись в истории
        conn.execute("""
        INSERT INTO incident_histories
        (history_id, incident_id, old_status, new_status, changed_by, comment)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid4()),
            incident_id,
            None,
            'active',
            'system',
            'Incident created automatically'
        ))
        
        conn.commit()
        return get_incident_by_id(incident_id)

def get_incidents(status: Optional[str] = None, severity: Optional[str] = None,
                 start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
                 limit: int = 100) -> List[Dict[str, Any]]:
    """Получение инцидентов с фильтрацией"""
    with get_db() as conn:
        query = "SELECT * FROM incidents WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        if start_time:
            query += " AND created_at >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND created_at <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            incident = dict(row)
            if incident.get('position'):
                incident['position'] = json.loads(incident['position'])
            if incident.get('metadata'):
                incident['metadata'] = json.loads(incident['metadata'])
            result.append(incident)
        
        return result

def get_incident_by_id(incident_id: str) -> Optional[Dict[str, Any]]:
    """Получение инцидента по ID"""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,))
        row = cursor.fetchone()
        if row:
            incident = dict(row)
            if incident.get('position'):
                incident['position'] = json.loads(incident['position'])
            if incident.get('metadata'):
                incident['metadata'] = json.loads(incident['metadata'])
            return incident
        return None

def update_incident_status(incident_id: str, status: str, 
                         changed_by: Optional[str] = None, 
                         comment: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Обновление статуса инцидента"""
    with get_db() as conn:
        # Получаем текущий инцидент
        current = get_incident_by_id(incident_id)
        if not current:
            return None
        
        # Определяем поля для обновления
        fields = ["status = ?"]
        params = [status]
        
        if status == 'acknowledged':
            fields.append("acknowledged_at = CURRENT_TIMESTAMP")
            if changed_by:
                fields.append("acknowledged_by = ?")
                params.append(changed_by)
        
        elif status in ['resolved', 'false_positive']:
            fields.append("resolved_at = CURRENT_TIMESTAMP")
            if changed_by:
                fields.append("resolved_by = ?")
                params.append(changed_by)
        
        params.append(incident_id)
        
        # Обновляем инцидент
        query = f"UPDATE incidents SET {', '.join(fields)} WHERE incident_id = ?"
        conn.execute(query, params)
        
        # Создаем запись в истории
        conn.execute("""
        INSERT INTO incident_histories
        (history_id, incident_id, old_status, new_status, changed_by, comment)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid4()),
            incident_id,
            current['status'],
            status,
            changed_by or 'system',
            comment
        ))
        
        conn.commit()
        return get_incident_by_id(incident_id)

def acknowledge_incidents(incident_ids: List[str], acknowledged_by: str, 
                         comment: Optional[str] = None) -> int:
    """Подтверждение нескольких инцидентов"""
    acknowledged_count = 0
    for incident_id in incident_ids:
        if update_incident_status(incident_id, 'acknowledged', acknowledged_by, comment):
            acknowledged_count += 1
    return acknowledged_count

# ==================== CRUD для alerts ====================
def create_alert(alert_: dict) -> Dict[str, Any]:
    """Создание записи об оповещении"""
    with get_db() as conn:
        alert_id = str(uuid4())
        conn.execute("""
        INSERT INTO alerts
        (alert_id, incident_id, channels, status, metadata)
        VALUES (?, ?, ?, ?, ?)
        """, (
            alert_id,
            str(alert_data['incident_id']),
            json.dumps(alert_data['channels']),
            alert_data.get('status', 'pending'),
            json.dumps(alert_data.get('metadata')) if alert_data.get('metadata') else None
        ))
        conn.commit()
        
        # Обновляем метаданные инцидента
        if alert_data.get('status') == 'sent':
            incident = get_incident_by_id(str(alert_data['incident_id']))
            if incident and incident.get('metadata'):
                metadata = json.loads(incident['metadata'])
            else:
                metadata = {}
            
            metadata.setdefault('alerts_sent', 0)
            metadata['alerts_sent'] += 1
            metadata['last_alert_at'] = datetime.now().isoformat()
            
            update_incident_metadata(str(alert_data['incident_id']), metadata)
        
        return get_alert_by_id(alert_id)

def get_alert_by_id(alert_id: str) -> Optional[Dict[str, Any]]:
    """Получение оповещения по ID"""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
        row = cursor.fetchone()
        if row:
            alert = dict(row)
            if alert.get('channels'):
                alert['channels'] = json.loads(alert['channels'])
            if alert.get('metadata'):
                alert['metadata'] = json.loads(alert['metadata'])
            return alert
        return None

def get_alert_history(start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
                     status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Получение истории оповещений"""
    with get_db() as conn:
        query = "SELECT * FROM alerts WHERE 1=1"
        params = []
        
        if start_time:
            query += " AND created_at >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND created_at <= ?"
            params.append(end_time.isoformat())
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            alert = dict(row)
            if alert.get('channels'):
                alert['channels'] = json.loads(alert['channels'])
            if alert.get('metadata'):
                alert['metadata'] = json.loads(alert['metadata'])
            result.append(alert)
        
        return result

def update_alert_status(alert_id: str, status: str, 
                       failed_reason: Optional[str] = None) -> bool:
    """Обновление статуса оповещения"""
    with get_db() as conn:
        fields = ["status = ?"]
        params = [status]
        
        if status == 'sent':
            fields.append("sent_at = CURRENT_TIMESTAMP")
        elif status == 'failed' and failed_reason:
            fields.append("failed_reason = ?")
            params.append(failed_reason)
        
        params.append(alert_id)
        
        query = f"UPDATE alerts SET {', '.join(fields)} WHERE alert_id = ?"
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0

def update_incident_metadata(incident_id: str, metadata: dict) -> bool:
    """Обновление метаданных инцидента"""
    with get_db() as conn:
        cursor = conn.execute("""
        UPDATE incidents SET metadata = ?, updated_at = CURRENT_TIMESTAMP
        WHERE incident_id = ?
        """, (json.dumps(metadata), incident_id))
        conn.commit()
        return cursor.rowcount > 0

def get_database_stats() -> Dict[str, Any]:
    """Получение статистики по базе данных"""
    with get_db() as conn:
        stats = {}
        
        # Количество записей в каждой таблице
        tables = ['geozones', 'rules', 'incidents', 'alerts']
        for table in tables:
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
            stats[f'{table}_count'] = cursor.fetchone()['count']
        
        # Размер базы данных
        cursor = conn.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        cursor = conn.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        stats['database_size_mb'] = round((page_count * page_size) / (1024 * 1024), 2)
        
        # Последние записи
        cursor = conn.execute("SELECT MAX(created_at) as last_incident FROM incidents")
        stats['last_incident'] = cursor.fetchone()['last_incident']
        
        cursor = conn.execute("SELECT MAX(created_at) as last_alert FROM alerts")
        stats['last_alert'] = cursor.fetchone()['last_alert']
        
        return stats

def cleanup_old_incidents(days_to_keep: int = 90) -> int:
    """Очистка старых инцидентов"""
    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
    
    with get_db() as conn:
        # Удаляем старые инциденты
        cursor = conn.execute("DELETE FROM incidents WHERE created_at < ?", (cutoff_date,))
        deleted_incidents = cursor.rowcount
        
        # Удаляем старые оповещения
        cursor = conn.execute("DELETE FROM alerts WHERE created_at < ?", (cutoff_date,))
        deleted_alerts = cursor.rowcount
        
        # Удаляем старые записи истории
        cursor = conn.execute("DELETE FROM incident_histories WHERE change_time < ?", (cutoff_date,))
        deleted_histories = cursor.rowcount
        
        conn.commit()
        
        logger.info(f"Cleaned up  {deleted_incidents} incidents, {deleted_alerts} alerts, {deleted_histories} histories")
        return deleted_incidents + deleted_alerts + deleted_histories