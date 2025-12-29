import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def connect_to_positioning_db() -> sqlite3.Connection:
    """Подключение к базе данных positioning service"""
    # Путь к базе данных positioning (вне контейнера)
    positioning_db_path = Path("../positioning_service/positioning.db")
    
    # В контейнере путь может быть другим
    if not positioning_db_path.exists():
        # Пробуем путь внутри контейнера
        positioning_db_path = Path("/app/positioning.db")
    
    if not positioning_db_path.exists():
        # Пробуем через Docker volume
        positioning_db_path = Path("/app/data/positioning.db")
    
    conn = sqlite3.connect(str(positioning_db_path))
    conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
    return conn

def connect_to_access_control_db() -> sqlite3.Connection:
    """Подключение к базе данных access control service"""
    # Путь к базе данных access control (вне контейнера)
    access_control_db_path = Path("../access_control_service/access_control.db")
    
    # В контейнере путь может быть другим
    if not access_control_db_path.exists():
        # Пробуем путь внутри контейнера
        access_control_db_path = Path("/app/access_control.db")
    
    if not access_control_db_path.exists():
        # Пробуем через Docker volume
        access_control_db_path = Path("/app/data/access_control.db")
    
    conn = sqlite3.connect(str(access_control_db_path))
    conn.row_factory = sqlite3.Row
    return conn

def fetch_positioning_data(start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
    """
    Получение данных о позициях из positioning service
    
    Args:
        start_time: Начало периода
        end_time: Конец периода
    
    Returns:
        List[Dict[str, Any]]: Данные о позициях
    """
    data = []
    
    try:
        conn = connect_to_positioning_db()
        cursor = conn.cursor()
        
        # Получаем позиции за указанный период
        query = """
        SELECT 
            cp.tag_id,
            cp.x,
            cp.y,
            cp.z,
            cp.accuracy,
            cp.calculation_timestamp as timestamp,
            rm.anchor_id,
            rm.distance_m
        FROM calculated_positions cp
        LEFT JOIN raw_measurements rm ON cp.batch_id = rm.batch_id AND cp.tag_id = rm.tag_id
        WHERE cp.calculation_timestamp BETWEEN ? AND ?
        ORDER BY cp.calculation_timestamp
        """
        
        cursor.execute(query, (start_time.isoformat(), end_time.isoformat()))
        rows = cursor.fetchall()
        
        for row in rows:
            record = {
                'tag_id': row['tag_id'],
                'position': {
                    'x': row['x'],
                    'y': row['y'],
                    'z': row['z'],
                    'accuracy': row['accuracy']
                },
                'timestamp': row['timestamp'],
                'anchor_id': row['anchor_id'],
                'distance_m': row['distance_m'],
                'source': 'positioning'
            }
            data.append(record)
        
        conn.close()
        logger.info(f"Fetched {len(data)} positioning records from {start_time} to {end_time}")
        
    except Exception as e:
        logger.error(f"Error fetching positioning data: {e}")
        raise
    
    return data

def fetch_access_control_data(start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
    """
    Получение данных о нарушениях и сущностях из access control service
    
    Args:
        start_time: Начало периода
        end_time: Конец периода
    
    Returns:
        List[Dict[str, Any]]: Данные о нарушениях и сущностях
    """
    data = []
    
    try:
        conn = connect_to_access_control_db()
        cursor = conn.cursor()
        
        # 1. Получаем нарушения за период
        violations_query = """
        SELECT 
            v.violation_id,
            v.entity_id,
            v.entity_name,
            v.entity_type,
            v.geofence_id,
            v.geofence_name,
            v.position,
            v.severity,
            v.description,
            v.timestamp,
            v.acknowledged,
            r.rule_name,
            r.action
        FROM violations v
        LEFT JOIN rules r ON v.rule_id = r.rule_id
        WHERE v.timestamp BETWEEN ? AND ?
        ORDER BY v.timestamp
        """
        
        cursor.execute(violations_query, (start_time.isoformat(), end_time.isoformat()))
        violations = cursor.fetchall()
        
        for row in violations:
            try:
                position_data = json.loads(row['position'])
            except:
                position_data = {}
            
            record = {
                'entity_id': row['entity_id'],
                'entity_name': row['entity_name'],
                'entity_type': row['entity_type'],
                'geofence_id': row['geofence_id'],
                'geofence_name': row['geofence_name'],
                'position': position_data,
                'severity': row['severity'],
                'description': row['description'],
                'timestamp': row['timestamp'],
                'acknowledged': bool(row['acknowledged']),
                'rule_name': row['rule_name'],
                'action': row['action'],
                'source': 'access_control',
                'data_type': 'violation'
            }
            data.append(record)
        
        # 2. Получаем информацию о сущностях для связи с tag_id
        entities_query = """
        SELECT 
            entity_id,
            name as entity_name,
            entity_type,
            tag_id,
            department,
            role,
            is_active
        FROM entities
        WHERE is_active = 1
        """
        
        cursor.execute(entities_query)
        entities = cursor.fetchall()
        
        entity_map = {}
        for row in entities:
            entity_map[row['entity_id']] = {
                'tag_id': row['tag_id'],
                'entity_name': row['entity_name'],
                'entity_type': row['entity_type'],
                'department': row['department'],
                'role': row['role']
            }
        
        # 3. Получаем информацию о геозонах
        geofences_query = """
        SELECT 
            geofence_id,
            name as zone_name,
            zone_type,
            shape,
            coordinates,
            buffer_meters
        FROM geofences
        WHERE is_active = 1
        """
        
        cursor.execute(geofences_query)
        geofences = cursor.fetchall()
        
        geofence_map = {}
        for row in geofences:
            try:
                coordinates = json.loads(row['coordinates'])
            except:
                coordinates = {}
            
            geofence_map[row['geofence_id']] = {
                'zone_name': row['zone_name'],
                'zone_type': row['zone_type'],
                'shape': row['shape'],
                'coordinates': coordinates,
                'buffer_meters': row['buffer_meters']
            }
        
        conn.close()
        
        logger.info(f"Fetched {len(violations)} violations and {len(entities)} entities from access control")
        
        # Сохраняем вспомогательные данные
        data.append({
            'entity_map': entity_map,
            'geofence_map': geofence_map,
            'source': 'access_control',
            'data_type': 'metadata'
        })
        
    except Exception as e:
        logger.error(f"Error fetching access control data: {e}")
        raise
    
    return data

def combine_and_transform_data(
    positioning_data: List[Dict[str, Any]],
    access_control_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Объединение и трансформация данных из разных источников
    
    Args:
        positioning_data: Данные о позициях
        access_control_data: Данные о нарушениях и сущностях
    
    Returns:
        List[Dict[str, Any]]: Объединенные и подготовленные данные
    """
    combined_data = []
    
    try:
        # Извлекаем метаданные из access_control_data
        entity_map = {}
        geofence_map = {}
        
        for item in access_control_data:
            if item.get('data_type') == 'metadata':
                entity_map = item.get('entity_map', {})
                geofence_map = item.get('geofence_map', {})
                break
        
        # Создаем обратное отображение tag_id -> entity_id
        tag_to_entity = {}
        for entity_id, entity_info in entity_map.items():
            if entity_info.get('tag_id'):
                tag_to_entity[entity_info['tag_id']] = entity_id
        
        # Обрабатываем данные о позициях
        for pos_record in positioning_data:
            if pos_record.get('source') != 'positioning':
                continue
            
            tag_id = pos_record.get('tag_id')
            entity_id = tag_to_entity.get(tag_id)
            
            if not entity_id:
                # Если нет связи с сущностью, пропускаем
                continue
            
            entity_info = entity_map.get(entity_id, {})
            
            # Преобразуем данные в формат для агрегации
            record = {
                'entity_id': entity_id,
                'entity_name': entity_info.get('entity_name', 'Unknown'),
                'entity_type': entity_info.get('entity_type', 'employee'),
                'tag_id': tag_id,
                'position': pos_record.get('position', {}),
                'timestamp': pos_record.get('timestamp'),
                'source': 'positioning',
                'duration_minutes': 1.0,  # Примерное время, можно вычислить точнее
                'department': entity_info.get('department'),
                'role': entity_info.get('role')
            }
            combined_data.append(record)
        
        # Обрабатываем данные о нарушениях
        for violation_record in access_control_data:
            if violation_record.get('data_type') != 'violation':
                continue
            
            # Для нарушений вычисляем длительность (если есть информация о начале/конце)
            # В данном случае используем фиксированное значение или вычисляем из контекста
            entity_id = violation_record.get('entity_id')
            entity_info = entity_map.get(entity_id, {})
            
            record = {
                'entity_id': entity_id,
                'entity_name': violation_record.get('entity_name', 'Unknown'),
                'entity_type': violation_record.get('entity_type', 'employee'),
                'tag_id': entity_info.get('tag_id'),
                'geofence_id': violation_record.get('geofence_id'),
                'geofence_name': violation_record.get('geofence_name'),
                'zone_id': violation_record.get('geofence_id'),  # Для совместимости
                'zone_name': violation_record.get('geofence_name'),
                'zone_type': geofence_map.get(violation_record.get('geofence_id', {}), {}).get('zone_type', 'other'),
                'position': violation_record.get('position', {}),
                'timestamp': violation_record.get('timestamp'),
                'source': 'access_control',
                'data_type': 'violation',
                'duration_minutes': 5.0,  # Примерная длительность нарушения
                'severity': violation_record.get('severity'),
                'acknowledged': violation_record.get('acknowledged', False),
                'rule_name': violation_record.get('rule_name'),
                'action': violation_record.get('action'),
                'description': violation_record.get('description')
            }
            combined_data.append(record)
        
        logger.info(f"Combined and transformed {len(combined_data)} records")
        
    except Exception as e:
        logger.error(f"Error combining data: {e}")
        raise
    
    return combined_data

def collect_data_for_aggregation(
    start_time: datetime, 
    end_time: datetime,
    use_cached: bool = False
) -> List[Dict[str, Any]]:
    """
    Основная функция сбора данных для агрегации
    
    Args:
        start_time: Начало периода
        end_time: Конец периода
        use_cached: Использовать кэшированные данные если есть
    
    Returns:
        List[Dict[str, Any]]: Подготовленные данные для агрегации
    """
    logger.info(f"Collecting data for period {start_time} to {end_time}")
    
    # 1. Получаем данные из positioning service
    positioning_data = fetch_positioning_data(start_time, end_time)
    
    # 2. Получаем данные из access control service
    access_control_data = fetch_access_control_data(start_time, end_time)
    
    # 3. Объединяем и трансформируем данные
    combined_data = combine_and_transform_data(positioning_data, access_control_data)
    
    # 4. Дополнительная обработка: вычисление длительности пребывания в зонах
    processed_data = _calculate_zone_durations(combined_data)
    
    return processed_data

def _calculate_zone_durations(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Вычисление длительности пребывания в зонах на основе последовательности позиций
    
    Args:
        data: Входные данные
    
    Returns:
        List[Dict[str, Any]]: Данные с вычисленными длительностями
    """
    try:
        # Группируем данные по entity_id
        df = pd.DataFrame(data)
        
        if df.empty:
            return data
        
        # Сортируем по времени
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(['entity_id', 'timestamp'])
        
        processed_records = []
        
        # Для каждой сущности вычисляем время в зонах
        for entity_id, group in df.groupby('entity_id'):
            group = group.reset_index(drop=True)
            
            current_zone = None
            zone_start_time = None
            
            for i, row in group.iterrows():
                # Если есть информация о геозоне
                if pd.notna(row.get('geofence_id')):
                    zone_id = row['geofence_id']
                    
                    if current_zone != zone_id:
                        # Если была предыдущая зона, сохраняем её длительность
                        if current_zone is not None and zone_start_time is not None:
                            duration = (row['timestamp'] - zone_start_time).total_seconds() / 60.0
                            
                            if duration > 0:
                                record = {
                                    'entity_id': entity_id,
                                    'entity_name': row['entity_name'],
                                    'entity_type': row['entity_type'],
                                    'zone_id': current_zone,
                                    'zone_name': group.loc[i-1, 'geofence_name'] if i > 0 else '',
                                    'zone_type': group.loc[i-1, 'zone_type'] if i > 0 else '',
                                    'timestamp': zone_start_time.isoformat(),
                                    'duration_minutes': round(duration, 2),
                                    'data_type': 'zone_entry'
                                }
                                processed_records.append(record)
                        
                        # Начинаем новую зону
                        current_zone = zone_id
                        zone_start_time = row['timestamp']
                
                else:
                    # Если нет информации о зоне, сбрасываем
                    if current_zone is not None and zone_start_time is not None:
                        duration = (row['timestamp'] - zone_start_time).total_seconds() / 60.0
                        
                        if duration > 0:
                            record = {
                                'entity_id': entity_id,
                                'entity_name': row['entity_name'],
                                'entity_type': row['entity_type'],
                                'zone_id': current_zone,
                                'zone_name': group.loc[i-1, 'geofence_name'] if i > 0 else '',
                                'zone_type': group.loc[i-1, 'zone_type'] if i > 0 else '',
                                'timestamp': zone_start_time.isoformat(),
                                'duration_minutes': round(duration, 2),
                                'data_type': 'zone_entry'
                            }
                            processed_records.append(record)
                    
                    current_zone = None
                    zone_start_time = None
        
        logger.info(f"Calculated durations for {len(processed_records)} zone entries")
        return processed_records
        
    except Exception as e:
        logger.error(f"Error calculating zone durations: {e}")
        return data

def main_aggregation_pipeline(start_time: datetime, end_time: datetime, force: bool = False):
    """
    Основной пайплайн агрегации данных
    
    Args:
        start_time: Начало периода
        end_time: Конец периода
        force: Принудительная агрегация
    """
    try:
        # 1. Собираем данные из всех источников
        raw_data = collect_data_for_aggregation(start_time, end_time)
        
        # 2. Вызываем функцию агрегации
        from app.aggregation_engine import aggregate_data_for_period  # Импортируем твою функцию
        
        aggregated_results = aggregate_data_for_period(
            start_time=start_time,
            end_time=end_time,
            raw_data=raw_data,
            force=force
        )
        
        logger.info(f"Aggregation completed. Generated {len(aggregated_results)} aggregated records")
        
        return aggregated_results
        
    except Exception as e:
        logger.error(f"Error in aggregation pipeline: {e}")
        raise

# Пример использования
if __name__ == "__main__":
    # Тестирование функции
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    try:
        results = main_aggregation_pipeline(start_time, end_time)
        print(f"✅ Aggregation completed successfully. {len(results)} records generated.")
    except Exception as e:
        print(f"❌ Error: {e}")
