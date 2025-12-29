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
    print("=" * 50)
    print("🟢 INIT_DB STARTED")
    print("=" * 50)
    
    try:
        with get_db() as conn:
            print("✅ Database connection established")
            
            # Включение поддержки FOREIGN KEY
            conn.execute("PRAGMA foreign_keys = ON")
            print("🔧 FOREIGN KEYS support enabled")
            
            # 1. calculated_positions
            print("\n1. Creating calculated_positions...")
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS calculated_positions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        batch_id TEXT NOT NULL,
                        tag_id TEXT NOT NULL,
                        x REAL NOT NULL,
                        y REAL NOT NULL,
                        z REAL NOT NULL DEFAULT 0.0,
                        accuracy REAL NOT NULL DEFAULT 1.0,
                        calculation_timestamp TEXT NOT NULL,
                        
                        -- Внешние ключи
                        FOREIGN KEY (batch_id) 
                            REFERENCES processed_batches(batch_id)
                            ON DELETE CASCADE
                    )
                """)
                print("   ✅ CREATE TABLE executed")
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
            
            # 2. anchors
            print("\n2. Creating anchors...")
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS anchors (
                        anchor_id TEXT PRIMARY KEY,
                        x REAL NOT NULL,
                        y REAL NOT NULL,
                        z REAL NOT NULL,
                        description TEXT,
                        is_active INTEGER DEFAULT 1,
                        last_calibration TEXT
                    )
                """)
                print("   ✅ CREATE TABLE executed")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # 3. raw_measurements
            print("\n3. Creating raw_measurements...")
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS raw_measurements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        batch_id TEXT NOT NULL,
                        measurement_timestamp TEXT NOT NULL,
                        anchor_id TEXT NOT NULL,
                        tag_id TEXT NOT NULL,
                        distance_m REAL NOT NULL,
                        
                        -- Внешние ключи
                        FOREIGN KEY (batch_id) 
                            REFERENCES processed_batches(batch_id)
                            ON DELETE CASCADE,
                        FOREIGN KEY (anchor_id) 
                            REFERENCES anchors(anchor_id)
                            ON DELETE CASCADE
                    )
                """)
                print("   ✅ CREATE TABLE executed")
            except Exception as e:
                print(f"   ❌ Error: {e}")

            # 4. processed_batches (создается перед таблицами с FK на него)
            print("\n4. Creating processed_batches...")
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS processed_batches (
                        batch_id TEXT PRIMARY KEY,
                        measurement_count INTEGER NOT NULL,
                        processed_at TEXT,
                        status TEXT DEFAULT 'pending'
                    )
                """)
                print("   ✅ CREATE TABLE executed")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Какие таблицы создались ????
            print("\n5. Checking created tables...")
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"   📋 Tables in DB: {[row[0] for row in tables]}")
            
            # Демо-данные анкеров
            print("\n6. Adding demo anchors...")
            cursor = conn.execute("SELECT COUNT(*) FROM anchors")
            count = cursor.fetchone()[0]
            print(f"   Current anchors count: {count}")
            
            if count == 0:
                print("   Adding demo data...")
                conn.execute("""
                    INSERT OR IGNORE INTO anchors (anchor_id, x, y, z, description)
                    VALUES 
                        ('anchor-1', 0.0, 0.0, 0.0, 'Северная стена'),
                        ('anchor-2', 0.0, 1.0, 0.0, 'Южная стена'),
                        ('anchor-3', 0.0, 0.0, 1.0, 'Центральная колонна');
                """)
                print("   ✅ Demo data added")
            
            conn.commit()
            print("\n✅ COMMIT successful")
            
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR in init_db: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 50)
    print("🟢 INIT_DB COMPLETED")
    print("=" * 50)
    
    # Финальная проверка
    print("\n🔍 Final verification:")
    try:
        import sqlite3
        check_conn = sqlite3.connect(DB_PATH)
        cursor = check_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        print(f"   Tables on disk: {cursor.fetchall()}")
        check_conn.close()
    except Exception as e:
        print(f"   Verification failed: {e}")

def save_measurements_batch(batch_id: str, measurements: List[Dict]):
    """Сохранение пакета измерений"""
    try:
        logger.info(f"Saving {len(measurements)} measurements for batch {batch_id}")
        
        with get_db() as conn:
            for i, measurement in enumerate(measurements):
                # Преобразуем timestamp в строку
                timestamp = measurement.get('timestamp')
                if hasattr(timestamp, 'isoformat'):
                    timestamp_str = timestamp.isoformat()
                else:
                    timestamp_str = str(timestamp)
                
                # Параметры для SQL
                params = (
                    batch_id,
                    timestamp_str,
                    measurement['anchor_id'],
                    measurement['tag_id'],
                    measurement['distance_m']
                )
                
                logger.debug(f"Inserting measurement {i}: {params}")
                
                conn.execute("""
                    INSERT INTO raw_measurements 
                    (batch_id, measurement_timestamp, anchor_id, tag_id, distance_m)
                    VALUES (?, ?, ?, ?, ?)
                """, params)
            
            conn.commit()
            logger.info(f"Successfully saved {len(measurements)} measurements")
            
    except Exception as e:
        logger.error(f"Database error in save_measurements_batch: {e}", exc_info=True)
        raise

def get_latest_position_db(tag_id: str) -> Optional[dict]:
    """Получение последней позиции из БД"""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT tag_id, x, y, z, calculation_timestamp, accuracy
            FROM calculated_positions 
            WHERE tag_id = ?
            ORDER BY calculation_timestamp DESC 
            LIMIT 1
        """, (tag_id,))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_position_history_db(
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
            SELECT tag_id, x, y, z, calculation_timestamp, accuracy
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

def get_all_anchors() -> List[dict]:
    """Получение всех анкеров"""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT anchor_id, x, y, z, description, is_active, last_calibration
            FROM anchors
            ORDER BY anchor_id
        """)
        return [dict(row) for row in cursor.fetchall()]

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
