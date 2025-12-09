import math
from typing import List, Dict

def calculate_position(measurements: List[Dict], anchors_db: Dict) -> Dict:
    """
    Упрощенная трилатерация.
    В реальности здесь будет сложная математика.
    """
    if len(measurements) < 3:
        raise ValueError("Нужно минимум 3 измерения для трилатерации")
    
    # Простейший алгоритм - среднее координат анкеров с весом по расстоянию
    total_weight = 0
    x_sum = 0
    y_sum = 0
    
    for meas in measurements:
        anchor = anchors_db.get(meas["anchor_id"])
        if not anchor:
            continue
            
        # Чем ближе метка к анкеру, тем больше вес его координат
        weight = 1 / (meas["distance_m"] + 0.1)  # +0.1 чтобы избежать деления на 0
        x_sum += anchor["x"] * weight
        y_sum += anchor["y"] * weight
        total_weight += weight
    
    if total_weight == 0:
        raise ValueError("Не найдены координаты анкеров")
    
    return {
        "x": x_sum / total_weight,
        "y": y_sum / total_weight,
        "z": 0.0,
        "accuracy": 1.5  # примерная погрешность
    }