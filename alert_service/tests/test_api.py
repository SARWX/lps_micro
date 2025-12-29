import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import uuid

# Добавляем родительскую директорию в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, get_database_stats

# ИНИЦИАЛИЗИРУЙ БД ПЕРЕД ТЕСТАМИ
print("🔄 Initializing database for tests...")
init_db()
client = TestClient(app)

# Глобальные переменные для хранения тестовых ID
TEST_GEOZONE_ID = None
TEST_RULE_ID = None
TEST_INCIDENT_ID = None

def test_health_check():
    """Тест проверки работоспособности"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "alert_service"
    assert "database_stats" in data

def test_root_redirect():
    """Тест корневого endpoint'а (редирект на docs)"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307  # Temporary Redirect

# ==================== Geozones Tests ====================

def test_get_all_geozones():
    """Тест получения списка всех геозон"""
    response = client.get("/api/v1/geozones")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0  # Должны быть демо-геозоны

def test_create_geozone_rectangle():
    """Тест создания прямоугольной геозоны"""
    global TEST_GEOZONE_ID
    payload = {
        "name": "Тестовая прямоугольная зона",
        "zone_type": "restricted",
        "description": "Тестовая зона для тестирования",
        "shape": "rectangle",
        "coordinates": {
            "min_x": 0.0,
            "max_x": 10.0,
            "min_y": 0.0,
            "max_y": 10.0,
            "min_z": 0.0,
            "max_z": 3.0
        },
        "buffer_meters": 0.5
    }
    response = client.post("/api/v1/geozones", json=payload)
    assert response.status_code == 201
    data = response.json()
    TEST_GEOZONE_ID = data["geozone_id"]
    assert data["name"] == "Тестовая прямоугольная зона"
    assert data["zone_type"] == "restricted"
    assert data["shape"] == "rectangle"
    assert data["buffer_meters"] == 0.5
    assert data["is_active"] == True

def test_check_point_in_geozones():
    """Тест проверки точки в геозонах"""
    payload = {
        "x": 5.0,
        "y": 5.0,
        "z": 1.0,
        "geozone_ids": [TEST_GEOZONE_ID]
    }
    response = client.post("/api/v1/geozones/check", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["point"]["x"] == 5.0
    assert data["point"]["y"] == 5.0
    assert isinstance(data["intersections"], list)
    if data["intersections"]:
        assert data["intersections"][0]["is_inside"] == True

# ==================== Rules Tests ====================

def test_create_rule():
    """Тест создания нового правила"""
    global TEST_RULE_ID
    
    # Создаем правило
    rule_payload = {
        "name": "Тестовое правило",
        "description": "Правило для тестирования",
        "entity_type": "employee",
        "entity_id": "test-entity-001",
        "role_required": "engineer",
        "geozone_id": TEST_GEOZONE_ID,
        "action": "deny",
        "schedule": {
            "days_of_week": [1, 2, 3, 4, 5],  # Пн-Пт
            "start_time": "09:00",
            "end_time": "18:00"
        },
        "severity": "high"
    }
    response = client.post("/api/v1/rules", json=rule_payload)
    assert response.status_code == 201
    data = response.json()
    TEST_RULE_ID = data["rule_id"]
    assert data["name"] == "Тестовое правило"
    assert data["action"] == "deny"
    assert data["severity"] == "high"

# ==================== Incidents Tests ====================

def test_create_incident():
    """Тест создания нового инцидента"""
    global TEST_INCIDENT_ID
    payload = {
        "rule_id": TEST_RULE_ID,
        "entity_id": "test-entity-001",
        "position": {
            "x": 5.0,
            "y": 5.0,
            "z": 1.0
        },
        "severity": "high",
        "description": "Тестовый инцидент"
    }
    response = client.post("/api/v1/incidents", json=payload)
    assert response.status_code == 201
    data = response.json()
    TEST_INCIDENT_ID = data["incident_id"]
    assert data["severity"] == "high"
    assert data["status"] == "active"

def test_get_incidents():
    """Тест получения списка инцидентов"""
    response = client.get("/api/v1/incidents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

def test_acknowledge_incidents():
    """Тест подтверждения инцидентов"""
    payload = {
        "incident_ids": [TEST_INCIDENT_ID],
        "acknowledged_by": "test-operator",
        "comment": "Тестовое подтверждение"
    }
    response = client.post("/api/v1/incidents/acknowledge", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["acknowledged"] == 1
    assert data["success"] == True

# ==================== Alerts Tests ====================

def test_generate_alert():
    """Тест генерации оповещения"""
    payload = {
        "incident_id": TEST_INCIDENT_ID,
        "channels": ["email", "telegram"],
        "recipients": ["test@example.com"],
        "webhook_url": "https://example.com/webhook"
    }
    response = client.post("/api/v1/alerts", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert "alert_id" in data

def test_get_alert_history():
    """Тест получения истории оповещений"""
    response = client.get("/api/v1/alerts/history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

# ==================== Cleanup Tests ====================

def test_delete_rule():
    """Тест удаления правила"""
    if TEST_RULE_ID:
        response = client.delete(f"/api/v1/rules/{TEST_RULE_ID}")
        assert response.status_code == 204

def test_delete_geozone():
    """Тест удаления геозоны"""
    if TEST_GEOZONE_ID:
        response = client.delete(f"/api/v1/geozones/{TEST_GEOZONE_ID}")
        assert response.status_code == 204

if __name__ == "__main__":
    # Запуск тестов вручную
    import traceback
    
    tests = [
        ("Health check", test_health_check),
        ("Root redirect", test_root_redirect),
        ("Get all geozones", test_get_all_geozones),
        ("Create rectangle geozone", test_create_geozone_rectangle),
        ("Check point in geozones", test_check_point_in_geozones),
        ("Create rule", test_create_rule),
        ("Create incident", test_create_incident),
        ("Get incidents", test_get_incidents),
        ("Acknowledge incidents", test_acknowledge_incidents),
        ("Generate alert", test_generate_alert),
        ("Get alert history", test_get_alert_history),
        ("Delete rule", test_delete_rule),
        ("Delete geozone", test_delete_geozone),
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    print("🧪 Running Alert Service Tests...")
    print("=" * 60)
    
    for name, test_func in tests:
        try:
            test_func()
            print(f"✅ {name}")
            passed += 1
        except AssertionError as e:
            print(f"❌ {name}: AssertionError - {e}")
            failed += 1
        except Exception as e:
            print(f"⚠️  {name}: Skipped - {e}")
            skipped += 1
    
    print("=" * 60)
    print(f"📊 Results: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed == 0:
        print("🎉 All tests passed successfully!")
    else:
        print("❌ Some tests failed")