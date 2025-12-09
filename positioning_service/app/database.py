import sqlite3
from contextlib import contextmanager
from datetime import datetime
import json

DB_PATH = "positioning.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
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
        
        # Таблица позиций
        conn.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_id TEXT NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                z REAL NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                accuracy REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица сырых измерений
        conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gateway_id TEXT NOT NULL,
                batch_timestamp TIMESTAMP NOT NULL,
                anchor_id TEXT NOT NULL,
                tag_id TEXT NOT NULL,
                distance_m REAL NOT NULL,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()

# Простые CRUD операции
def save_position(position: dict):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO positions (tag_id, x, y, z, timestamp, accuracy) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (position["tag_id"], position["x"], position["y"], 
             position["z"], position["timestamp"], position["accuracy"])
        )
        conn.commit()

def get_latest_position(tag_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM positions WHERE tag_id = ? ORDER BY timestamp DESC LIMIT 1",
            (tag_id,)
        ).fetchone()
        return dict(row) if row else None