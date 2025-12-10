import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "positioning.db"

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
    """Инициализация базы данных"""
    with get_db() as conn:
        # Сырые измерения
        conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                gateway_id TEXT NOT NULL,
                measurement_timestamp TIMESTAMP NOT NULL,
                anchor_id TEXT NOT NULL,
                tag_id TEXT NOT NULL,
                distance_m REAL NOT NULL CHECK(distance_m > 0),
                processed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_batch (batch_id),
                INDEX idx_tag_time (tag_id, measurement_timestamp)
            )
        """)
        
        # Вычисленные позиции
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calculated_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                tag_id TEXT NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                z REAL NOT NULL,
                accuracy REAL NOT NULL,
                calculation_timestamp TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES raw_measurements(batch_id),
                INDEX idx_tag (tag_id),
                INDEX idx_batch_tag (batch_id, tag_id)
            )
        """)
        
        # Обработанные батчи
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_batches (
                batch_id TEXT PRIMARY KEY,
                gateway_id TEXT NOT NULL,
                measurement_count INTEGER NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        conn.commit()
    logger.info("Database initialized")


def save_measurements_batch(batch_id: str, gateway_id: str, 
                           measurements: List[Dict[str, Any]]) -> int:
    """Сохранение пакета измерений в БД"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Сохраняем метаинформацию о батче
        cursor.execute(
            """INSERT INTO processed_batches 
               (batch_id, gateway_id, measurement_count) 
               VALUES (?, ?, ?)""",
            (batch_id, gateway_id, len(measurements))
        )
        
        # Сохраняем каждое измерение
        for meas in measurements:
            cursor.execute(
                """INSERT INTO raw_measurements 
                   (batch_id, gateway_id, measurement_timestamp, 
                    anchor_id, tag_id, distance_m) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (batch_id, gateway_id, meas.get('timestamp'),
                 meas['anchor_id'], meas['tag_id'], meas['distance_m'])
            )
        
        conn.commit()
        return cursor.lastrowid


def get_measurements_for_trilateration(tag_id: str, 
                                      timestamp: datetime) -> List[Dict]:
    """Получение измерений для трилатерации"""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT anchor_id, distance_m 
            FROM raw_measurements 
            WHERE tag_id = ? AND measurement_timestamp = ?
            ORDER BY anchor_id
        """, (tag_id, timestamp))
        
        return [dict(row) for row in cursor.fetchall()]

def get_latest_position(tag_id: str) -> Optional[dict]:
    """Получение последней позиции из БД"""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT tag_id, x, y, z, calculation_timestamp as timestamp, accuracy
            FROM calculated_positions 
            WHERE tag_id = ?
            ORDER BY calculation_timestamp DESC 
            LIMIT 1
        """, (tag_id,))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_position_history(
    tag_id: str, 
    start_time: datetime, 
    end_time: datetime, 
    limit: int = 1000
) -> List[dict]:
    """Получение истории позиций"""
    if start_time >= end_time:
        raise ValueError("start_time must be earlier than end_time")
    
    if limit > 10000:
        raise ValueError("Limit cannot exceed 10000")
    
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT tag_id, x, y, z, calculation_timestamp as timestamp, accuracy
            FROM calculated_positions 
            WHERE tag_id = ? 
                AND calculation_timestamp BETWEEN ? AND ?
            ORDER BY calculation_timestamp ASC
            LIMIT ?
        """, (tag_id, start_time, end_time, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
def get_all_anchors() -> List[dict]:
    """Получение всех анкеров"""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT anchor_id, x, y, z, description, is_active, last_calibration
            FROM anchors
            ORDER BY anchor_id
        """)
        return [dict(row) for row in cursor.fetchall()]


def get_anchor_by_id(anchor_id: str) -> Optional[dict]:
    """Получение анкера по ID"""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT anchor_id, x, y, z, description, is_active, last_calibration
            FROM anchors
            WHERE anchor_id = ?
        """, (anchor_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_anchor(anchor_id: str) -> bool:
    """Удаление анкера"""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM anchors WHERE anchor_id = ?", (anchor_id,))
        conn.commit()
        return cursor.rowcount > 0


def create_or_update_anchor(anchor_data: dict) -> None:
    """Создание или обновление анкера"""
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO anchors 
            (anchor_id, x, y, z, description, is_active, last_calibration)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            anchor_data['anchor_id'],
            anchor_data['x'],
            anchor_data['y'],
            anchor_data['z'],
            anchor_data.get('description'),
            anchor_data.get('is_active', True),
            anchor_data.get('last_calibration')
        ))
        conn.commit()


def init_db():
    """Инициализация базы данных - дополняем"""
    with get_db() as conn:
        # ... существующие CREATE TABLE ...
        
        # Таблица анкеров
        conn.execute("""
            CREATE TABLE IF NOT EXISTS anchors (
                anchor_id TEXT PRIMARY KEY,
                x REAL NOT NULL,
                y REAL NOT NULL,
                z REAL NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                last_calibration TIMESTAMP
            )
        """)
        
        # Демо-данные анкеров
        conn.execute("""
            INSERT OR IGNORE INTO anchors (anchor_id, x, y, z, description, is_active)
            VALUES 
                ('anchor-1', 0.0, 0.0, 3.0, 'Северная стена цеха №1', 1),
                ('anchor-2', 50.0, 0.0, 3.0, 'Южная стена цеха №1', 1),
                ('anchor-3', 25.0, 30.0, 3.0, 'Центральная колонна цеха №1', 1),
                ('anchor-4', 0.0, 30.0, 3.0, 'Северо-восточный угол цеха №2', 1)
        """)
        
        conn.commit()
    logger.info("Database initialized")

