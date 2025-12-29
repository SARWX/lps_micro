import asyncio
import aiohttp
import random
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional
import numpy as np
import sys
import json

class RTLSComplianceSimulator:
    def __init__(self, 
                 positioning_url: str = "http://0.0.0.0:8001",
                 access_control_url: str = "http://0.0.0.0:8002"):
        self.positioning_url = positioning_url
        self.access_control_url = access_control_url
        self.tags = []
        self.entities = []  # entity_id
        self.positions = {}  # tag_id -> (x, y, z)
        self.entity_to_tag = {}  # entity_id -> tag_id
        self.tag_to_entity = {}  # tag_id -> entity_id
        self.geofences = []
        self.rules = []
        
    async def initialize(self):
        """Инициализация всех компонентов"""
        print("=" * 60)
        print("Инициализация RTLS Compliance симулятора")
        print("=" * 60)
        
        # 1. Инициализация Positioning Service
        await self.initialize_positioning()
        
        # 2. Инициализация Access Control Service
        await self.initialize_access_control()
        
        # 3. Создание тестовых данных
        await self.create_test_data()
        
        print("\n✅ Инициализация завершена!")
        print(f"   Меток: {len(self.tags)}")
        print(f"   Сущностей: {len(self.entities)}")
        print(f"   Геозон: {len(self.geofences)}")
        print(f"   Правил: {len(self.rules)}")
    
    async def initialize_positioning(self):
        """Инициализация Positioning Service"""
        print("\n1. Инициализация Positioning Service...")
        
        # Получаем анкеры с сервера
        self.anchors = await self.get_anchors_from_server()
        
        if len(self.anchors) < 3:
            print(f"Предупреждение: найдено только {len(self.anchors)} анкеров")
            if len(self.anchors) == 0:
                print("Создание тестовых анкеров...")
                await self.create_test_anchors()
                self.anchors = await self.get_anchors_from_server()
        
        if len(self.anchors) < 3:
            raise ValueError(f"Нужно минимум 3 анкера для трилатерации, а найдено {len(self.anchors)}")
    
    async def initialize_access_control(self):
        """Инициализация Access Control Service"""
        print("\n2. Инициализация Access Control Service...")
        
        # Проверяем доступность сервиса
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.access_control_url}/docs") as response:
                    if response.status == 200:
                        print("  ✅ Access Control Service доступен")
                    else:
                        print(f"  ⚠️ Access Control Service ответил с кодом: {response.status}")
        except Exception as e:
            print(f"  ❌ Не удалось подключиться к Access Control Service: {e}")
            print("  Продолжаем без проверки compliance...")
    
    async def create_test_data(self):
        """Создание тестовых данных"""
        print("\n3. Создание тестовых данных...")
        
        # Создаем 10 сущностей (сотрудников)
        for i in range(10):
            entity_id = f"emp-{100 + i}"
            tag_id = f"tag-employee-{100 + i}"
            
            self.entities.append(entity_id)
            self.tags.append(tag_id)
            self.entity_to_tag[entity_id] = tag_id
            self.tag_to_entity[tag_id] = entity_id
            
            # Начальная позиция в пределах комнаты 20x20 метров
            self.positions[tag_id] = (
                random.uniform(1, 19),
                random.uniform(1, 19),
                random.uniform(0.5, 2)
            )
        
        # Создаем сущности и геозоны в Access Control Service
        await self.create_access_control_test_data()
    
    async def create_access_control_test_data(self):
        """Создание тестовых данных в Access Control Service"""
        try:
            async with aiohttp.ClientSession() as session:
                
                # 1. Создаем сущности (сотрудников)
                print("  Создание сущностей в Access Control...")
                for i, entity_id in enumerate(self.entities):
                    tag_id = self.entity_to_tag[entity_id]
                    
                    # Определяем отдел и роль
                    departments = ["IT отдел", "Бухгалтерия", "Производство", "Логистика", "HR"]
                    roles = ["инженер", "бухгалтер", "оператор", "менеджер", "аналитик"]
                    
                    entity_data = {
                        "entity_id": entity_id,
                        "name": f"Сотрудник {entity_id}",
                        "entity_type": "employee",
                        "tag_id": tag_id,
                        "department": random.choice(departments),
                        "role": random.choice(roles),
                        "is_active": True
                    }
                    
                    async with session.post(
                        f"{self.access_control_url}/api/v1/entities",
                        json=entity_data
                    ) as response:
                        if response.status in [200, 201]:
                            print(f"    ✅ Создана сущность: {entity_id}")
                        elif response.status == 409:
                            print(f"    ⚠️ Сущность {entity_id} уже существует")
                        else:
                            print(f"    ❌ Ошибка создания сущности {entity_id}: {response.status}")
                
                # 2. Создаем геозоны
                print("\n  Создание геозон...")
                
                # Опасная зона вокруг станка
                danger_zone = {
                    "name": "Опасная зона станка",
                    "zone_type": "danger",
                    "description": "Опасная зона вокруг производственного станка",
                    "shape": "circle",
                    "coordinates": {
                        "center_x": 15.0,
                        "center_y": 15.0,
                        "radius": 3.0
                    },
                    "buffer_meters": 0.5,
                    "is_active": True
                }
                
                # Запретная зона (серверная)
                restricted_zone = {
                    "name": "Серверная комната",
                    "zone_type": "restricted",
                    "description": "Запретная зона, доступ только для IT сотрудников",
                    "shape": "rectangle",
                    "coordinates": {
                        "min_x": 2.0,
                        "max_x": 6.0,
                        "min_y": 2.0,
                        "max_y": 6.0,
                        "min_z": 0.0,
                        "max_z": 3.0
                    },
                    "buffer_meters": 0.3,
                    "is_active": True
                }
                
                # Зона отдыха
                safe_zone = {
                    "name": "Зона отдыха",
                    "zone_type": "safe",
                    "description": "Зона отдыха сотрудников",
                    "shape": "rectangle",
                    "coordinates": {
                        "min_x": 14.0,
                        "max_x": 18.0,
                        "min_y": 2.0,
                        "max_y": 6.0,
                        "min_z": 0.0,
                        "max_z": 3.0
                    },
                    "buffer_meters": 0.0,
                    "is_active": True
                }
                
                geofences_to_create = [danger_zone, restricted_zone, safe_zone]
                created_geofences = []
                
                for geofence in geofences_to_create:
                    async with session.post(
                        f"{self.access_control_url}/api/v1/geofences",
                        json=geofence
                    ) as response:
                        if response.status in [200, 201]:
                            created = await response.json()
                            created_geofences.append(created)
                            print(f"    ✅ Создана геозона: {geofence['name']}")
                        else:
                            print(f"    ❌ Ошибка создания геозоны {geofence['name']}: {response.status}")
                
                self.geofences = created_geofences
                
                # 3. Создаем правила доступа
                print("\n  Создание правил доступа...")
                
                if len(self.geofences) >= 3:
                    danger_zone_id = self.geofences[0]['geofence_id']
                    restricted_zone_id = self.geofences[1]['geofence_id']
                    safe_zone_id = self.geofences[2]['geofence_id']
                    
                    # Правило 1: В опасную зону никому нельзя (всегда запрет)
                    rule1 = {
                        "name": "Запрет входа в опасную зону",
                        "description": "Вход в опасную зону станка запрещен для всех",
                        "entity_type": "all",
                        "geofence_id": danger_zone_id,
                        "action": "deny",
                        "severity": "critical",
                        "is_active": True,
                        "metadata": {
                            "auto_generated": True
                        }
                    }
                    
                    # Правило 2: В серверную только IT сотрудники
                    rule2 = {
                        "name": "Доступ в серверную только для IT",
                        "description": "Только сотрудники IT отдела могут входить в серверную",
                        "entity_type": "employee",
                        "role_required": "инженер",  # IT сотрудники
                        "geofence_id": restricted_zone_id,
                        "action": "allow",
                        "severity": "high",
                        "is_active": True,
                        "metadata": {
                            "auto_generated": True
                        }
                    }
                    
                    # Правило 3: Зона отдыха для всех
                    rule3 = {
                        "name": "Свободный доступ в зону отдыха",
                        "description": "Все сотрудники могут находиться в зоне отдыха",
                        "entity_type": "all",
                        "geofence_id": safe_zone_id,
                        "action": "allow",
                        "severity": "low",
                        "is_active": True,
                        "metadata": {
                            "auto_generated": True
                        }
                    }
                    
                    rules_to_create = [rule1, rule2, rule3]
                    
                    for rule in rules_to_create:
                        async with session.post(
                            f"{self.access_control_url}/api/v1/rules",
                            json=rule
                        ) as response:
                            if response.status in [200, 201]:
                                created = await response.json()
                                self.rules.append(created)
                                print(f"    ✅ Создано правило: {rule['name']}")
                            else:
                                print(f"    ❌ Ошибка создания правила {rule['name']}: {response.status}")
        
        except Exception as e:
            print(f"  ⚠️ Ошибка при создании тестовых данных: {e}")
    
    async def get_anchors_from_server(self) -> List[Dict]:
        """Получение списка анкеров с сервера"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.positioning_url}/api/v1/anchors") as response:
                    if response.status == 200:
                        anchors = await response.json()
                        print(f"  ✅ Получено {len(anchors)} анкеров с сервера")
                        return anchors
                    else:
                        print(f"  ⚠️ Ошибка при получении анкеров: {response.status}")
                        return []
        except Exception as e:
            print(f"  ❌ Исключение при получении анкеров: {e}")
            return []
    
    async def create_test_anchors(self):
        """Создание тестовых анкеров если их нет на сервере"""
        test_anchors = [
            {
                "anchor_id": "anchor-1",
                "x": 0.0,
                "y": 0.0,
                "z": 2.5,
                "description": "Северо-западный угол",
                "is_active": True,
                "last_calibration": datetime.now(timezone.utc).isoformat()
            },
            {
                "anchor_id": "anchor-2",
                "x": 20.0,
                "y": 0.0,
                "z": 2.5,
                "description": "Северо-восточный угол",
                "is_active": True,
                "last_calibration": datetime.now(timezone.utc).isoformat()
            },
            {
                "anchor_id": "anchor-3",
                "x": 0.0,
                "y": 20.0,
                "z": 2.5,
                "description": "Юго-западный угол",
                "is_active": True,
                "last_calibration": datetime.now(timezone.utc).isoformat()
            },
            {
                "anchor_id": "anchor-4",
                "x": 20.0,
                "y": 20.0,
                "z": 3.0,
                "description": "Юго-восточный угол, потолок",
                "is_active": True,
                "last_calibration": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        async with aiohttp.ClientSession() as session:
            for anchor in test_anchors:
                try:
                    async with session.post(
                        f"{self.positioning_url}/api/v1/anchors",
                        json=anchor
                    ) as response:
                        if response.status in [200, 201]:
                            print(f"  ✅ Создан анкер: {anchor['anchor_id']}")
                        else:
                            print(f"  ❌ Ошибка создания анкера {anchor['anchor_id']}: {response.status}")
                except Exception as e:
                    print(f"  ❌ Исключение при создании анкера {anchor['anchor_id']}: {e}")
        
        await asyncio.sleep(1)
    
    def calculate_distance(self, tag_pos: Tuple[float, float, float], 
                          anchor: Dict) -> float:
        """Вычисление расстояния от метки до анкера"""
        dx = tag_pos[0] - anchor['x']
        dy = tag_pos[1] - anchor['y']
        dz = tag_pos[2] - anchor['z']
        return np.sqrt(dx*dx + dy*dy + dz*dz)
    
    def update_position(self, tag_id: str):
        """Обновление позиции метки (небольшое случайное изменение)"""
        x, y, z = self.positions[tag_id]
        
        # Случайное смещение (имитация ходьбы человека)
        step_size = 0.5  # Максимальный шаг в метрах
        x += random.uniform(-step_size, step_size)
        y += random.uniform(-step_size, step_size)
        
        # Небольшое изменение высоты
        z += random.uniform(-0.05, 0.05)
        
        # Ограничиваем в пределах комнаты
        x = max(0.5, min(x, 19.5))
        y = max(0.5, min(y, 19.5))
        z = max(0.5, min(z, 3.0))
        
        self.positions[tag_id] = (x, y, z)
        return (x, y, z)
    
    def create_measurement_batch(self) -> Dict:
        """Создание пакета измерений для ВСЕХ меток"""
        measurements = []
        current_time = datetime.now(timezone.utc)
        
        for tag_id in self.tags:
            # Обновляем позицию для каждой метки
            pos = self.update_position(tag_id)
            
            # Для каждой метки создаем измерения для случайных 3 анкеров
            available_anchors = random.sample(self.anchors, min(3, len(self.anchors)))
            
            for anchor in available_anchors:
                distance = self.calculate_distance(pos, anchor)
                # Добавляем реалистичную погрешность измерения
                distance_with_noise = distance + random.uniform(-0.2, 0.2)
                distance_with_noise = max(0.3, distance_with_noise)
                
                measurements.append({
                    "anchor_id": anchor['anchor_id'],
                    "tag_id": tag_id,
                    "distance_m": round(distance_with_noise, 3)
                })
        
        return {
            "timestamp": current_time.isoformat(),
            "measurements": measurements
        }
    
    async def send_to_positioning(self, session: aiohttp.ClientSession) -> bool:
        """Отправка пакета измерений в Positioning Service"""
        try:
            batch = self.create_measurement_batch()
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Отправка в Positioning:")
            print(f"  Меток: {len(self.tags)}")
            print(f"  Измерений: {len(batch['measurements'])}")
            
            async with session.post(
                f"{self.positioning_url}/api/v1/measurements",
                json=batch
            ) as response:
                if response.status == 202:
                    result = await response.json()
                    print(f"  ✅ Принято в обработку, batch_id: {result.get('batch_id', 'N/A')}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"  ❌ Ошибка {response.status}: {error_text[:100]}")
                    return False
                    
        except Exception as e:
            print(f"  ❌ Исключение при отправке в Positioning: {str(e)}")
            return False
    
    async def check_compliance(self, session: aiohttp.ClientSession):
        """Проверка соблюдения правил для всех меток"""
        print("\n  Проверка compliance для текущих позиций:")
        
        compliance_results = []
        
        for tag_id in self.tags[:5]:  # Проверяем только первые 5 для примера
            entity_id = self.tag_to_entity.get(tag_id)
            if not entity_id:
                continue
            
            x, y, z = self.positions[tag_id]
            current_time = datetime.now(timezone.utc)
            
            # Подготавливаем запрос на проверку compliance
            compliance_request = {
                "entity_id": entity_id,
                "position": {
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "z": round(z, 2),
                    "timestamp": current_time.isoformat()
                }
            }
            
            try:
                async with session.post(
                    f"{self.access_control_url}/api/v1/compliance/check",
                    json=compliance_request
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Проверяем, есть ли нарушения
                        if result.get('is_compliant', True) == False:
                            violations = result.get('violations', [])
                            if violations:
                                violation_count = len(violations)
                                print(f"    ⚠️ {entity_id} ({tag_id}): {violation_count} нарушений")
                                
                                # Выводим информацию о нарушениях
                                for violation in violations[:2]:  # Показываем только первые 2
                                    rule_name = violation.get('rule_name', 'Неизвестно')
                                    severity = violation.get('severity', 'medium')
                                    print(f"      • {rule_name} ({severity})")
                                
                                compliance_results.append({
                                    'entity_id': entity_id,
                                    'tag_id': tag_id,
                                    'violations': violations,
                                    'position': (x, y, z)
                                })
                            else:
                                print(f"    ✅ {entity_id} ({tag_id}): без нарушений")
                        else:
                            print(f"    ✅ {entity_id} ({tag_id}): без нарушений")
                    
                    elif response.status == 404:
                        print(f"    ⚠️ {entity_id}: сущность не найдена в Access Control")
                    else:
                        print(f"    ❌ {entity_id}: ошибка проверки compliance: {response.status}")
                        
            except Exception as e:
                print(f"    ❌ {entity_id}: исключение при проверке compliance: {e}")
        
        return compliance_results
    
    async def check_geofence_intersection(self, session: aiohttp.ClientSession):
        """Проверка пересечения с геозонами"""
        print("\n  Проверка пересечения с геозонами:")
        
        for tag_id in self.tags[:3]:  # Проверяем только первые 3 метки
            x, y, z = self.positions[tag_id]
            
            check_request = {
                "x": round(x, 2),
                "y": round(y, 2),
                "z": round(z, 2)
            }
            
            try:
                async with session.post(
                    f"{self.access_control_url}/api/v1/geofences/check",
                    json=check_request
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        intersections = result.get('intersections', [])
                        
                        inside_zones = []
                        for intersection in intersections:
                            if intersection.get('is_inside', False):
                                zone_name = intersection.get('geofence_name', 'Неизвестно')
                                zone_type = intersection.get('zone_type', 'other')
                                inside_zones.append(f"{zone_name} ({zone_type})")
                        
                        if inside_zones:
                            print(f"    📍 {tag_id} находится в: {', '.join(inside_zones)}")
                        else:
                            print(f"    📍 {tag_id} вне геозон")
                    else:
                        print(f"    ❌ {tag_id}: ошибка проверки геозон: {response.status}")
                        
            except Exception as e:
                print(f"    ❌ {tag_id}: исключение при проверке геозон: {e}")
    
    async def verify_current_positions(self, session: aiohttp.ClientSession):
        """Проверка текущих позиций на сервере Positioning"""
        print("\n  Проверка позиций в Positioning Service:")
        for tag_id in self.tags[:2]:  # Проверяем только первые 2
            try:
                async with session.get(
                    f"{self.positioning_url}/api/v1/positions/current/{tag_id}"
                ) as response:
                    if response.status == 200:
                        pos = await response.json()
                        x, y, z = self.positions[tag_id]
                        print(f"    {tag_id}: сервер ({pos['x']:.2f}, {pos['y']:.2f}, {pos['z']:.2f}), "
                              f"симулятор ({x:.2f}, {y:.2f}, {z:.2f})")
                    elif response.status == 404:
                        print(f"    {tag_id}: позиция еще не вычислена")
                    else:
                        print(f"    {tag_id}: ошибка {response.status}")
            except Exception as e:
                print(f"    {tag_id}: исключение при проверке - {e}")
    
    
    async def get_violations_history(self, session: aiohttp.ClientSession):
        """Получение истории нарушений"""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=30)
            
            params = {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "limit": 10
            }
            
            async with session.get(
                f"{self.access_control_url}/api/v1/compliance/violations",
                params=params
            ) as response:
                if response.status == 200:
                    violations = await response.json()
                    if violations:
                        print(f"\n  📋 История нарушений (последние 30 мин): {len(violations)} записей")
                        for violation in violations[:3]:  # Показываем только 3
                            entity = violation.get('entity_name', violation.get('entity_id', 'Unknown'))
                            rule = violation.get('rule_name', 'Unknown')
                            severity = violation.get('severity', 'medium')
                            print(f"    • {entity}: {rule} ({severity})")
                    else:
                        print(f"\n  📋 Нарушений за последние 30 минут нет")
                else:
                    print(f"\n  ⚠️ Не удалось получить историю нарушений: {response.status}")
                        
        except Exception as e:
            print(f"\n  ❌ Ошибка получения истории нарушений: {e}")
    
    async def run_compliance_simulation(self, delay: float = 3.0):
        """Запуск симуляции с проверкой compliance"""
        print("\n" + "=" * 60)
        print("Запуск симуляции RTLS Compliance системы")
        print("=" * 60)
        print(f"Positioning URL: {self.positioning_url}")
        print(f"Access Control URL: {self.access_control_url}")
        print(f"Интервал отправки: {delay} секунд")
        print("=" * 60)
        
        iteration = 0
        async with aiohttp.ClientSession() as session:
            while True:
                iteration += 1
                print(f"\n{'='*40}")
                print(f"Итерация #{iteration}")
                print(f"{'='*40}")
                
                # Проверяем доступность Access Control Service
                ac_available = True
                
                # Отправляем пакет измерений в Positioning
                positioning_success = await self.send_to_positioning(session)
                
                if ac_available:
                    # 1. Проверяем пересечение с геозонами
                    await self.check_geofence_intersection(session)
                    
                    # 2. Проверяем compliance
                    compliance_results = await self.check_compliance(session)
                    
                    # 3. Периодически получаем историю нарушений
                    if iteration % 5 == 0:
                        await self.get_violations_history(session)
                
                # 4. Периодически проверяем позиции на сервере
                if iteration % 3 == 0:
                    await self.verify_current_positions(session)
                
                # Выводим статистику текущих позиций
                print("\n  📊 Текущие позиции (первые 3 метки):")
                for i, tag_id in enumerate(self.tags[:3]):
                    entity_id = self.tag_to_entity.get(tag_id, "Неизвестно")
                    x, y, z = self.positions[tag_id]
                    print(f"    {entity_id} ({tag_id}): ({x:.2f}, {y:.2f}, {z:.2f})")
                
                # Ждем перед следующей итерацией
                if iteration < 3:  # Первые 3 итерации быстрее
                    wait_time = 1.0
                else:
                    wait_time = delay
                
                print(f"\n  ⏳ Ожидание {wait_time} секунд до следующей итерации...")
                await asyncio.sleep(wait_time)
    
    def print_summary(self):
        """Вывод сводной информации"""
        print("\n" + "=" * 60)
        print("Сводная информация о симуляции")
        print("=" * 60)
        
        print(f"\nМетки ({len(self.tags)}):")
        for tag_id in self.tags:
            entity_id = self.tag_to_entity.get(tag_id, "Неизвестно")
            x, y, z = self.positions[tag_id]
            print(f"  {tag_id} -> {entity_id}: ({x:.2f}, {y:.2f}, {z:.2f})")
        
        if self.geofences:
            print(f"\nГеозоны ({len(self.geofences)}):")
            for geofence in self.geofences:
                print(f"  {geofence['name']} ({geofence['zone_type']})")
        
        if self.rules:
            print(f"\nПравила ({len(self.rules)}):")
            for rule in self.rules:
                print(f"  {rule['name']} -> {rule['action']} ({rule['severity']})")


async def main():
    # Настройки
    POSITIONING_URL = "http://0.0.0.0:8001"  # Positioning Service
    ACCESS_CONTROL_URL = "http://0.0.0.0:8002"  # Access Control Service
    DELAY_BETWEEN_ITERATIONS = 3.0  # Пауза между итерациями в секундах
    
    # Создаем и инициализируем симулятор
    simulator = RTLSComplianceSimulator(
        positioning_url=POSITIONING_URL,
        access_control_url=ACCESS_CONTROL_URL
    )
    
    try:
        await simulator.initialize()
        simulator.print_summary()
        
        print("\n" + "=" * 60)
        print("Запуск основной симуляции...")
        print("=" * 60)
        print("Нажмите Ctrl+C для остановки")
        
        # Запускаем симуляцию
        await simulator.run_compliance_simulation(delay=DELAY_BETWEEN_ITERATIONS)
        
    except KeyboardInterrupt:
        print("\n\n" + "="*50)
        print("Симуляция остановлена пользователем")
        print("="*50)
        simulator.print_summary()
        print("\nСистема готова к запуску.")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Для Windows нужна специальная политика event loop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
