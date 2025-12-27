"""
Модуль для обработки инцидентов и проверки правил.
Содержит логику проверки позиций сущностей против установленных правил
и генерации инцидентов при нарушении.
"""
from datetime import datetime, time
from typing import Dict, Any, List, Optional, Tuple
import logging
from app.database import (
    get_applicable_rules, check_point_in_geozones,
    create_incident, get_incident_by_id, update_incident_status
)
from app.models import PositionCheck, IncidentCreate, Incident
from uuid import uuid4

logger = logging.getLogger(__name__)

def process_position(entity: Dict[str, Any], position: PositionCheck) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Обработка позиции сущности и проверка на соответствие правилам.
    
    Args:
        entity: Словарь с данными сущности
        position: Позиция для проверки
    
    Returns:
        Tuple[bool, List[Dict[str, Any]]]: (является ли позиция соответствующей правилам, список нарушений)
    """
    try:
        # Получаем применимые правила для сущности
        rules = get_applicable_rules(
            entity_type=entity['entity_type'],
            entity_id=entity.get('entity_id'),
            role=entity.get('role')
        )
        
        violations = []
        is_compliant = True
        
        # Проверяем каждое правило
        for rule in rules:
            # Проверяем расписание правила
            if not check_schedule_compliance(rule, position.timestamp):
                continue
            
            # Проверяем находится ли позиция в геозоне правила
            geozone_intersections = check_point_in_geozones(
                x=position.x,
                y=position.y,
                z=position.z,
                geozone_ids=[rule['geozone_id']]
            )
            
            if not geozone_intersections:
                continue
            
            is_inside = geozone_intersections[0]['is_inside']
            violation = check_rule_violation(rule, is_inside, position)
            
            if violation:
                violations.append({
                    'rule_id': rule['rule_id'],
                    'rule_name': rule['name'],
                    'geozone_id': rule['geozone_id'],
                    'geozone_name': rule['geozone_name'],
                    'severity': rule['severity'],
                    'description': violation,
                    'timestamp': position.timestamp.isoformat()
                })
                is_compliant = False
        
        return is_compliant, violations
    
    except Exception as e:
        logger.error(f"Error processing position: {e}")
        return False, []

def check_schedule_compliance(rule: Dict[str, Any], timestamp: datetime) -> bool:
    """Проверка соответствия расписанию правила"""
    schedule = rule.get('schedule')
    if not schedule:
        return True  # Нет расписания - правило всегда активно
    
    # Проверяем день недели
    weekday = timestamp.weekday()  # 0 = Monday, 6 = Sunday
    if 'days_of_week' in schedule and schedule['days_of_week']:
        if weekday not in schedule['days_of_week']:
            return False
    
    # Проверяем время
    current_time = timestamp.time()
    
    if 'start_time' in schedule and schedule['start_time']:
        start_time = time.fromisoformat(schedule['start_time'])
        if current_time < start_time:
            return False
    
    if 'end_time' in schedule and schedule['end_time']:
        end_time = time.fromisoformat(schedule['end_time'])
        if current_time > end_time:
            return False
    
    return True

def check_rule_violation(rule: Dict[str, Any], is_inside: bool, position: PositionCheck) -> Optional[str]:
    """
    Проверка нарушения конкретного правила.
    
    Args:
        rule: Правило для проверки
        is_inside: Находится ли позиция внутри геозоны
        position: Позиция для проверки
    
    Returns:
        Optional[str]: Описание нарушения или None если нарушения нет
    """
    try:
        if rule['action'] == 'deny':
            if is_inside:
                # Проверяем пороговое время
                if rule.get('threshold_seconds'):
                    # Здесь должна быть логика проверки времени пребывания
                    # Для упрощения считаем, что нарушение есть
                    return f"Access denied to restricted area '{rule['geozone_name']}'"
                else:
                    return f"Access denied to restricted area '{rule['geozone_name']}'"
        
        elif rule['action'] == 'alert':
            if is_inside:
                if rule.get('threshold_seconds'):
                    # Здесь должна быть логика проверки времени пребывания
                    return f"Alert triggered in monitored area '{rule['geozone_name']}'"
                else:
                    return f"Alert triggered in monitored area '{rule['geozone_name']}'"
        
        elif rule['action'] == 'allow':
            if not is_inside and rule.get('threshold_seconds'):
                # Правило allow с порогом времени может означать, что сущность должна
                # находиться в зоне определенное время
                return f"Entity not in allowed area '{rule['geozone_name']}' for required duration"
    
        return None
    
    except Exception as e:
        logger.error(f"Error checking rule violation: {e}")
        return None

def create_incident_from_violation(violation: Dict[str, Any], entity: Dict[str, Any], 
                                 position: PositionCheck) -> Dict[str, Any]:
    """
    Создание инцидента на основе нарушения.
    
    Args:
        violation: Данные о нарушении
        entity: Данные сущности
        position: Позиция сущности
    
    Returns:
        Dict[str, Any]: Созданный инцидент
    """
    try:
        incident_data = {
            'rule_id': violation['rule_id'],
            'rule_name': violation['rule_name'],
            'entity_id': entity['entity_id'],
            'entity_name': entity.get('name', ''),
            'position': {
                'x': position.x,
                'y': position.y,
                'z': position.z,
                'timestamp': position.timestamp.isoformat()
            },
            'geozone_id': violation['geozone_id'],
            'geozone_name': violation['geozone_name'],
            'severity': violation['severity'],
            'description': violation['description']
        }
        
        # Добавляем дополнительные метаданные
        metadata = {
            'violation_timestamp': violation['timestamp'],
            'entity_type': entity.get('entity_type', 'unknown'),
            'rule_action': violation.get('rule_action', 'unknown'),
            'triggered_by': 'automatic'
        }
        
        if entity.get('department'):
            metadata['department'] = entity['department']
        if entity.get('role'):
            metadata['role'] = entity['role']
        
        incident_data['metadata'] = metadata
        
        # Создаем инцидент
        incident = create_incident(incident_data)
        logger.info(f"Created incident {incident['incident_id']} for rule {violation['rule_id']}")
        return incident
    
    except Exception as e:
        logger.error(f"Error creating incident from violation: {e}")
        raise

def cleanup_old_incidents(days_to_keep: int = 90) -> int:
    """
    Очистка старых инцидентов.
    
    Args:
        days_to_keep: Количество дней для хранения инцидентов
    
    Returns:
        int: Количество удаленных инцидентов
    """
    from app.database import cleanup_old_incidents as db_cleanup
    return db_cleanup(days_to_keep)