import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
from uuid import uuid4
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "data_aggregator.db"

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
    """Инициализация базы данных для сервиса агрегации данных"""
    print("=" * 50)
    print("🟢 DATA AGGREGATOR SERVICE INIT_DB STARTED")
    print("=" * 50)
    
    try:
        with get_db() as conn:
            print("✅ Database connection established")
            
            # 1. aggregated_data - таблица для хранения агрегированных данных
            print("\n1. Creating aggregated_data table...")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS aggregated_data (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                entity_name TEXT,
                entity_type TEXT CHECK(entity_type IN ('employee', 'equipment')),
                zone_id TEXT NOT NULL,
                zone_name TEXT,
                zone_type TEXT,
                timestamp TIMESTAMP NOT NULL,
                duration_minutes REAL,
                hour INTEGER,
                day_of_week INTEGER,
                week_number INTEGER,
                month INTEGER,
                year INTEGER,
                data_type TEXT CHECK(data_type IN ('position', 'zone_entry', 'zone_exit', 'workflow')),
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            print("   ✅ aggregated_data table created")
            
            # Индексы для быстрого поиска
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agg_entity_time ON aggregated_data(entity_id, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agg_zone_time ON aggregated_data(zone_id, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agg_data_type ON aggregated_data(data_type, timestamp)")
            
            # 2. reports - таблица для хранения сгенерированных отчетов
            print("\n2. Creating reports table...")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                report_type TEXT NOT NULL CHECK(report_type IN ('zone_occupancy', 'time_in_zone', 'workflow_efficiency', 'anomalies')),
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                period_start TIMESTAMP NOT NULL,
                period_end TIMESTAMP NOT NULL,
                parameters TEXT,
                report_data TEXT NOT NULL,
                format TEXT CHECK(format IN ('json', 'csv', 'excel', 'pdf')),
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            print("   ✅ reports table created")
            
            # 3. aggregation_tasks - таблица для отслеживания задач агрегации
            print("\n3. Creating aggregation_tasks table...")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS aggregation_tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                records_processed INTEGER DEFAULT 0,
                aggregation_type TEXT CHECK(aggregation_type IN ('hourly', 'daily', 'custom'))
            )
            """)
            print("   ✅ aggregation_tasks table created")
            
            # 4. anomalies - таблица для хранения обнаруженных аномалий
            print("\n4. Creating anomalies table...")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS anomalies (
                anomaly_id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                entity_name TEXT,
                entity_type TEXT,
                anomaly_type TEXT NOT NULL CHECK(anomaly_type IN ('unexpected_zone', 'unusual_time', 'abnormal_speed', 'prolonged_stay')),
                zone_id TEXT,
                zone_name TEXT,
                position TEXT,
                timestamp TIMESTAMP NOT NULL,
                description TEXT,
                severity TEXT CHECK(severity IN ('low', 'medium', 'high', 'critical')),
                confidence REAL CHECK(confidence BETWEEN 0 AND 1),
                related_violations TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            print("   ✅ anomalies table created")
            
            # Индексы для аномалий
            conn.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_entity_time ON anomalies(entity_id, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON anomalies(severity, confidence)")
            
            # 5. exports - таблица для отслеживания экспорта данных
            print("\n5. Creating exports table...")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS exports (
                export_id TEXT PRIMARY KEY,
                report_id TEXT NOT NULL,
                export_format TEXT NOT NULL CHECK(export_format IN ('csv', 'excel', 'pdf')),
                file_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER,
                status TEXT CHECK(status IN ('pending', 'completed', 'failed'))
            )
            """)
            print("   ✅ exports table created")
            
            # Проверка созданных таблиц
            print("\n6. Checking created tables...")
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"   📋 Tables in DB: {[row[0] for row in tables]}")
            
            conn.commit()
            print("\n✅ COMMIT successful")
            
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR in init_db: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 50)
    print("🟢 DATA AGGREGATOR SERVICE INIT_DB COMPLETED")
    print("=" * 50)

# ==================== CRUD для aggregated_data ====================
def store_aggregated_data(data_records: List[Dict[str, Any]]) -> int:
    """Сохранение агрегированных данных"""
    with get_db() as conn:
        cursor = conn.cursor()
        inserted_count = 0
        
        for record in data_records:
            record_id = str(uuid4())
            cursor.execute("""
            INSERT INTO aggregated_data (
                id, entity_id, entity_name, entity_type, zone_id, zone_name, zone_type,
                timestamp, duration_minutes, hour, day_of_week, week_number, month, year,
                data_type, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record_id,
                record['entity_id'],
                record.get('entity_name'),
                record.get('entity_type', 'employee'),
                record['zone_id'],
                record.get('zone_name'),
                record.get('zone_type'),
                record['timestamp'],
                record.get('duration_minutes'),
                record.get('hour'),
                record.get('day_of_week'),
                record.get('week_number'),
                record.get('month'),
                record.get('year'),
                record.get('data_type', 'position'),
                json.dumps(record.get('raw_data', {}))
            ))
            inserted_count += 1
        
        conn.commit()
        return inserted_count

def get_data_for_period(start_time: datetime, end_time: datetime,
                       zone_ids: Optional[List[str]] = None,
                       entity_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Получение агрегированных данных за период"""
    with get_db() as conn:
        query = """
        SELECT * FROM aggregated_data
        WHERE timestamp BETWEEN ? AND ?
        """
        params = [start_time.isoformat(), end_time.isoformat()]
        
        if zone_ids:
            placeholders = ','.join(['?'] * len(zone_ids))
            query += f" AND zone_id IN ({placeholders})"
            params.extend(zone_ids)
        
        if entity_types:
            placeholders = ','.join(['?'] * len(entity_types))
            query += f" AND entity_type IN ({placeholders})"
            params.extend(entity_types)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            record = dict(row)
            if record.get('raw_data'):
                record['raw_data'] = json.loads(record['raw_data'])
            result.append(record)
        
        return result

def get_aggregated_data(data_type: str, start_time: datetime, end_time: datetime,
                       entity_id: Optional[str] = None, zone_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Получение агрегированных данных по типу"""
    with get_db() as conn:
        query = """
        SELECT * FROM aggregated_data
        WHERE data_type = ? AND timestamp BETWEEN ? AND ?
        """
        params = [data_type, start_time.isoformat(), end_time.isoformat()]
        
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)
        
        if zone_id:
            query += " AND zone_id = ?"
            params.append(zone_id)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            record = dict(row)
            if record.get('raw_data'):
                record['raw_data'] = json.loads(record['raw_data'])
            result.append(record)
        
        return result

# ==================== CRUD для reports ====================
def store_report(report_id: str, report_type: str, report_data: Dict[str, Any],
                period_start: datetime, period_end: datetime,
                parameters: Optional[Dict[str, Any]] = None,
                format: str = 'json') -> Dict[str, Any]:
    """Сохранение сгенерированного отчета"""
    with get_db() as conn:
        conn.execute("""
        INSERT INTO reports (
            report_id, report_type, report_data, period_start, period_end, parameters, format
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id,
            report_type,
            json.dumps(report_data),
            period_start.isoformat(),
            period_end.isoformat(),
            json.dumps(parameters) if parameters else None,
            format
        ))
        conn.commit()
        
        # Возвращаем сохраненный отчет
        cursor = conn.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,))
        row = cursor.fetchone()
        if row:
            report = dict(row)
            if report.get('report_data'):
                report['report_data'] = json.loads(report['report_data'])
            if report.get('parameters'):
                report['parameters'] = json.loads(report['parameters'])
            return report
        return None

def get_report_by_id(report_id: str) -> Optional[Dict[str, Any]]:
    """Получение отчета по ID"""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,))
        row = cursor.fetchone()
        if row:
            report = dict(row)
            if report.get('report_data'):
                report['report_data'] = json.loads(report['report_data'])
            if report.get('parameters'):
                report['parameters'] = json.loads(report['parameters'])
            return report
        return None

def get_reports_by_type(report_type: str, start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Получение отчетов по типу с фильтрацией по периоду"""
    with get_db() as conn:
        query = "SELECT * FROM reports WHERE report_type = ?"
        params = [report_type]
        
        if start_time:
            query += " AND period_start >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND period_end <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY generated_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            report = dict(row)
            if report.get('report_data'):
                report['report_data'] = json.loads(report['report_data'])
            if report.get('parameters'):
                report['parameters'] = json.loads(report['parameters'])
            result.append(report)
        
        return result

# ==================== CRUD для aggregation_tasks ====================
def create_aggregation_task(start_time: datetime, end_time: datetime,
                          aggregation_type: str = 'custom') -> Dict[str, Any]:
    """Создание задачи агрегации данных"""
    task_id = str(uuid4())
    with get_db() as conn:
        conn.execute("""
        INSERT INTO aggregation_tasks (
            task_id, status, start_time, end_time, aggregation_type
        ) VALUES (?, ?, ?, ?, ?)
        """, (
            task_id,
            'pending',
            start_time.isoformat(),
            end_time.isoformat(),
            aggregation_type
        ))
        conn.commit()
        
        return get_aggregation_task(task_id)

def update_aggregation_task(task_id: str, status: str, 
                          records_processed: Optional[int] = None,
                          error_message: Optional[str] = None) -> bool:
    """Обновление статуса задачи агрегации"""
    with get_db() as conn:
        fields = ["status = ?"]
        params = [status]
        
        if records_processed is not None:
            fields.append("records_processed = ?")
            params.append(records_processed)
        
        if error_message is not None:
            fields.append("error_message = ?")
            params.append(error_message)
        
        if status in ['completed', 'failed']:
            fields.append("completed_at = CURRENT_TIMESTAMP")
        
        params.append(task_id)
        
        query = f"UPDATE aggregation_tasks SET {', '.join(fields)} WHERE task_id = ?"
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0

def get_aggregation_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Получение задачи агрегации по ID"""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM aggregation_tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def get_pending_aggregation_tasks(limit: int = 10) -> List[Dict[str, Any]]:
    """Получение ожидающих задач агрегации"""
    with get_db() as conn:
        cursor = conn.execute("""
        SELECT * FROM aggregation_tasks 
        WHERE status = 'pending' 
        ORDER BY created_at ASC 
        LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

# ==================== CRUD для anomalies ====================
def store_anomaly(anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
    """Сохранение обнаруженной аномалии"""
    anomaly_id = str(uuid4())
    with get_db() as conn:
        conn.execute("""
        INSERT INTO anomalies (
            anomaly_id, entity_id, entity_name, entity_type, anomaly_type,
            zone_id, zone_name, position, timestamp, description,
            severity, confidence, related_violations
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            anomaly_id,
            anomaly_data['entity_id'],
            anomaly_data.get('entity_name'),
            anomaly_data.get('entity_type'),
            anomaly_data['anomaly_type'],
            anomaly_data.get('zone_id'),
            anomaly_data.get('zone_name'),
            json.dumps(anomaly_data.get('position', {})),
            anomaly_data['timestamp'].isoformat(),
            anomaly_data.get('description'),
            anomaly_data.get('severity', 'medium'),
            anomaly_data.get('confidence', 0.7),
            json.dumps(anomaly_data.get('related_violations', []))
        ))
        conn.commit()
        
        return get_anomaly_by_id(anomaly_id)

def get_anomaly_by_id(anomaly_id: str) -> Optional[Dict[str, Any]]:
    """Получение аномалии по ID"""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM anomalies WHERE anomaly_id = ?", (anomaly_id,))
        row = cursor.fetchone()
        if row:
            anomaly = dict(row)
            if anomaly.get('position'):
                anomaly['position'] = json.loads(anomaly['position'])
            if anomaly.get('related_violations'):
                anomaly['related_violations'] = json.loads(anomaly['related_violations'])
            return anomaly
        return None

def get_anomalies_for_period(start_time: datetime, end_time: datetime,
                           anomaly_types: Optional[List[str]] = None,
                           entity_ids: Optional[List[str]] = None,
                           severity_threshold: Optional[str] = None) -> List[Dict[str, Any]]:
    """Получение аномалий за период"""
    with get_db() as conn:
        query = """
        SELECT * FROM anomalies
        WHERE timestamp BETWEEN ? AND ?
        """
        params = [start_time.isoformat(), end_time.isoformat()]
        
        if anomaly_types:
            placeholders = ','.join(['?'] * len(anomaly_types))
            query += f" AND anomaly_type IN ({placeholders})"
            params.extend(anomaly_types)
        
        if entity_ids:
            placeholders = ','.join(['?'] * len(entity_ids))
            query += f" AND entity_id IN ({placeholders})"
            params.extend(entity_ids)
        
        if severity_threshold:
            # Предполагаем порядок серьезности: low < medium < high < critical
            severity_levels = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            threshold_level = severity_levels.get(severity_threshold, 1)
            query += " AND (CASE severity WHEN 'low' THEN 1 WHEN 'medium' THEN 2 WHEN 'high' THEN 3 WHEN 'critical' THEN 4 ELSE 0 END) >= ?"
            params.append(threshold_level)
        
        query += " ORDER BY timestamp DESC, confidence DESC"
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            anomaly = dict(row)
            if anomaly.get('position'):
                anomaly['position'] = json.loads(anomaly['position'])
            if anomaly.get('related_violations'):
                anomaly['related_violations'] = json.loads(anomaly['related_violations'])
            result.append(anomaly)
        
        return result

# ==================== CRUD для exports ====================
def store_export(report_id: str, export_format: str, file_path: str,
                file_size: Optional[int] = None, status: str = 'completed') -> Dict[str, Any]:
    """Сохранение информации об экспорте"""
    export_id = str(uuid4())
    with get_db() as conn:
        conn.execute("""
        INSERT INTO exports (
            export_id, report_id, export_format, file_path, file_size, status
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            export_id,
            report_id,
            export_format,
            file_path,
            file_size,
            status
        ))
        conn.commit()
        
        return get_export_by_id(export_id)

def get_export_by_id(export_id: str) -> Optional[Dict[str, Any]]:
    """Получение экспорта по ID"""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM exports WHERE export_id = ?", (export_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def get_exports_for_report(report_id: str) -> List[Dict[str, Any]]:
    """Получение всех экспорта для отчета"""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM exports WHERE report_id = ?", (report_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

# ==================== Вспомогательные функции ====================
def get_entity_statistics(entity_id: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
    """Получение статистики по сущности за период"""
    with get_db() as conn:
        # Общее время в зонах
        cursor = conn.execute("""
        SELECT 
            SUM(duration_minutes) as total_time,
            COUNT(DISTINCT zone_id) as unique_zones,
            COUNT(*) as total_visits
        FROM aggregated_data
        WHERE entity_id = ? AND timestamp BETWEEN ? AND ?
        """, (entity_id, start_time.isoformat(), end_time.isoformat()))
        
        stats = dict(cursor.fetchone())
        
        # Самые посещаемые зоны
        cursor = conn.execute("""
        SELECT zone_id, zone_name, COUNT(*) as visits_count, SUM(duration_minutes) as total_duration
        FROM aggregated_data
        WHERE entity_id = ? AND timestamp BETWEEN ? AND ?
        GROUP BY zone_id
        ORDER BY visits_count DESC
        LIMIT 5
        """, (entity_id, start_time.isoformat(), end_time.isoformat()))
        
        top_zones = [dict(row) for row in cursor.fetchall()]
        stats['top_zones'] = top_zones
        
        return stats

def get_zone_statistics(zone_id: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
    """Получение статистики по зоне за период"""
    with get_db() as conn:
        # Общая статистика по зоне
        cursor = conn.execute("""
        SELECT 
            COUNT(*) as total_visits,
            COUNT(DISTINCT entity_id) as unique_entities,
            AVG(duration_minutes) as avg_duration,
            SUM(duration_minutes) as total_time
        FROM aggregated_data
        WHERE zone_id = ? AND timestamp BETWEEN ? AND ?
        """, (zone_id, start_time.isoformat(), end_time.isoformat()))
        
        stats = dict(cursor.fetchone())
        
        # Статистика по часам
        cursor = conn.execute("""
        SELECT hour, COUNT(*) as visits_count
        FROM aggregated_data
        WHERE zone_id = ? AND timestamp BETWEEN ? AND ?
        GROUP BY hour
        ORDER BY visits_count DESC
        """, (zone_id, start_time.isoformat(), end_time.isoformat()))
        
        hourly_stats = {row['hour']: row['visits_count'] for row in cursor.fetchall()}
        stats['hourly_distribution'] = hourly_stats
        
        # Типы сущностей
        cursor = conn.execute("""
        SELECT entity_type, COUNT(*) as count
        FROM aggregated_data
        WHERE zone_id = ? AND timestamp BETWEEN ? AND ?
        GROUP BY entity_type
        """, (zone_id, start_time.isoformat(), end_time.isoformat()))
        
        entity_breakdown = {row['entity_type']: row['count'] for row in cursor.fetchall()}
        stats['entity_breakdown'] = entity_breakdown
        
        return stats

def cleanup_old_data(days_to_keep: int = 90) -> int:
    """Очистка старых данных (кроме отчетов)"""
    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
    
    with get_db() as conn:
        # Удаляем старые агрегированные данные
        cursor = conn.execute("DELETE FROM aggregated_data WHERE timestamp < ?", (cutoff_date,))
        deleted_records = cursor.rowcount
        
        # Удаляем старые аномалии
        cursor = conn.execute("DELETE FROM anomalies WHERE timestamp < ?", (cutoff_date,))
        deleted_anomalies = cursor.rowcount
        
        # Удаляем старые задачи агрегации (кроме completed)
        cursor = conn.execute("DELETE FROM aggregation_tasks WHERE created_at < ? AND status NOT IN ('completed', 'failed')", (cutoff_date,))
        deleted_tasks = cursor.rowcount
        
        conn.commit()
        
        logger.info(f"Cleaned up data: {deleted_records} records, {deleted_anomalies} anomalies, {deleted_tasks} tasks")
        return deleted_records + deleted_anomalies + deleted_tasks

def get_database_stats() -> Dict[str, Any]:
    """Получение статистики по базе данных"""
    with get_db() as conn:
        stats = {}
        
        # Количество записей в каждой таблице
        tables = ['aggregated_data', 'reports', 'aggregation_tasks', 'anomalies', 'exports']
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
        cursor = conn.execute("SELECT MAX(timestamp) as last_data FROM aggregated_data")
        stats['last_data_record'] = cursor.fetchone()['last_data']
        
        cursor = conn.execute("SELECT MAX(generated_at) as last_report FROM reports")
        stats['last_report'] = cursor.fetchone()['last_report']
        
        return stats