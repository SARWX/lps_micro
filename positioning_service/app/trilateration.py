import math
from typing import List, Dict, Tuple, Any
import numpy as np
from datetime import datetime


def simple_trilateration(measurements: List[Dict], 
                        anchors: Dict[str, Tuple[float, float, float]]) -> Dict:
    """
    Упрощенная трилатерация для курсовой.
    В реальности используется алгоритм минимизации невязки.
    """
    if len(measurements) < 3:
        raise ValueError("Недостаточно измерений для трилатерации")
    
    # Проверяем, что все анкеры известны
    unknown_anchors = []
    for m in measurements:
        if m['anchor_id'] not in anchors:
            unknown_anchors.append(m['anchor_id'])
    
    if unknown_anchors:
        raise ValueError(f"Неизвестные анкеры: {unknown_anchors}")
    
    # Матрицы для метода наименьших квадратов
    A = []
    B = []
    
    for i in range(len(measurements) - 1):
        m1 = measurements[i]
        m2 = measurements[i + 1]
        
        x1, y1, z1 = anchors[m1['anchor_id']]
        x2, y2, z2 = anchors[m2['anchor_id']]
        r1 = m1['distance_m']
        r2 = m2['distance_m']
        
        # Уравнения для трилатерации
        A.append([2*(x2 - x1), 2*(y2 - y1), 2*(z2 - z1)])
        B.append([r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2 - z1**2 + z2**2])
    
    try:
        # Решаем систему уравнений AX = B
        A_np = np.array(A)
        B_np = np.array(B)
        
        # Используем метод наименьших квадратов
        X = np.linalg.lstsq(A_np, B_np, rcond=None)[0]
        
        # Вычисляем погрешность
        residuals = []
        for m in measurements:
            xa, ya, za = anchors[m['anchor_id']]
            distance_calc = math.sqrt(
                (X[0][0] - xa)**2 + 
                (X[1][0] - ya)**2 + 
                (X[2][0] - za)**2
            )
            residuals.append(abs(distance_calc - m['distance_m']))
        
        accuracy = np.mean(residuals)
        
        return {
            'x': float(X[0][0]),
            'y': float(X[1][0]),
            'z': float(X[2][0]),
            'accuracy': float(accuracy)
        }
        
    except np.linalg.LinAlgError:
        # Если матрица вырожденная, используем упрощенный метод
        return fallback_trilateration(measurements, anchors)


def fallback_trilateration(measurements: List[Dict], 
                          anchors: Dict[str, Tuple[float, float, float]]) -> Dict:
    """Резервный метод трилатерации"""
    x_sum, y_sum, z_sum = 0, 0, 0
    weight_sum = 0
    
    for m in measurements:
        x, y, z = anchors[m['anchor_id']]
        weight = 1.0 / (m['distance_m'] + 0.001)  # Чем ближе, тем больше вес
        
        x_sum += x * weight
        y_sum += y * weight
        z_sum += z * weight
        weight_sum += weight
    
    return {
        'x': x_sum / weight_sum,
        'y': y_sum / weight_sum,
        'z': z_sum / weight_sum,
        'accuracy': 2.0  # Консервативная оценка
    }


def save_calculated_position(
    batch_id: str, 
    tag_id: str, 
    position: Dict[str, Any]
) -> None:
    """Сохранение вычисленной позиции в БД"""
    from app.database import get_db
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO calculated_positions 
            (batch_id, tag_id, x, y, z, accuracy, calculation_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id, tag_id, 
            position['x'], position['y'], position['z'],
            position['accuracy'], datetime.now()
        ))
        conn.commit()

def get_anchors_from_db() -> Dict[str, Tuple[float, float, float]]:
    """Получение анкеров из БД"""
    from app.database import get_all_anchors
    
    anchors = {}
    for anchor in get_all_anchors():
        if anchor['is_active']:
            anchors[anchor['anchor_id']] = (anchor['x'], anchor['y'], anchor['z'])
    return anchors
