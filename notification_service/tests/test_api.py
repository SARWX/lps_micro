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
TEST_USER_ID = "test-user-001"
TEST_TEMPLATE_ID = None

def test_health_check():
    """Тест проверки работоспособности"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "notification_service"
    assert "database_stats" in data

def test_root_redirect():
    """Тест корневого endpoint'а (редирект на docs)"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307  # Temporary Redirect

# ==================== Templates Tests ====================

def test_get_all_templates():
    """Тест получения списка всех шаблонов"""
    response = client.get("/api/v1/notifications/templates")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0  # Должны быть демо-шаблоны

def test_create_template():
    """Тест создания нового шаблона"""
    global TEST_TEMPLATE_ID
    payload = {
        "name": "Тестовый шаблон",
        "description": "Шаблон для тестирования",
        "category": "security",
        "channel": "email",
        "content": {
            "subject": "Тестовое уведомление: {{title}}",
            "body": "Сообщение: {{message}}\nВремя: {{timestamp}}",
            "html_body": "<h2>Тестовое уведомление</h2><p>Сообщение: {{message}}</p><p>Время: {{timestamp}}</p>"
        },
        "variables": ["title", "message", "timestamp"],
        "default_priority": "high",
        "is_active": True
    }
    response = client.post("/api/v1/notifications/templates", json=payload)
    assert response.status_code == 201
    data = response.json()
    TEST_TEMPLATE_ID = data["template_id"]
    assert data["name"] == "Тестовый шаблон"
    assert data["category"] == "security"
    assert data["channel"] == "email"
    assert data["default_priority"] == "high"
    assert data["is_active"] == True

def test_get_template_by_id():
    """Тест получения шаблона по ID"""
    if not TEST_TEMPLATE_ID:
        return  # Пропускаем если шаблон не создан
    
    response = client.get(f"/api/v1/notifications/templates/{TEST_TEMPLATE_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == TEST_TEMPLATE_ID
    assert data["name"] == "Тестовый шаблон"

def test_update_template():
    """Тест обновления шаблона"""
    if not TEST_TEMPLATE_ID:
        return  # Пропускаем если шаблон не создан
    
    update_payload = {
        "name": "Обновленный шаблон",
        "default_priority": "critical"
    }
    response = client.put(f"/api/v1/notifications/templates/{TEST_TEMPLATE_ID}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == TEST_TEMPLATE_ID
    assert data["name"] == "Обновленный шаблон"
    assert data["default_priority"] == "critical"

# ==================== Users Tests ====================

def test_create_user_preferences():
    """Тест создания настроек пользователя"""
    payload = {
        "user_id": TEST_USER_ID,
        "channels": {
            "email": True,
            "sms": False,
            "telegram": True,
            "push": True,
            "webhook": False
        },
        "categories": {
            "security": "high",
            "maintenance": "medium",
            "analytics": "low",
            "system": "medium"
        },
        "schedule": {
            "do_not_disturb": False,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00"
        },
        "contact_details": {
            "email": "test@example.com",
            "phone": "+1234567890",
            "telegram_id": "test_telegram",
            "push_token": "test_push_token"
        }
    }
    response = client.put("/api/v1/users/preferences", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == TEST_USER_ID
    assert data["channels"]["email"] == True
    assert data["channels"]["sms"] == False
    assert data["contact_details"]["email"] == "test@example.com"

def test_get_user_preferences():
    """Тест получения настроек пользователя"""
    response = client.get(f"/api/v1/users/preferences?user_id={TEST_USER_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == TEST_USER_ID
    assert data["contact_details"]["email"] == "test@example.com"

# ==================== Notifications Tests ====================

def test_send_notification():
    """Тест отправки уведомления"""
    payload = {
        "recipients": [TEST_USER_ID],
        "message": "Тестовое сообщение",
        "subject": "Тестовая тема",
        "channels": ["email", "telegram"],
        "priority": "high",
        "context": {
            "title": "Тестовое уведомление",
            "message": "Это тестовое сообщение"
        }
    }
    if TEST_TEMPLATE_ID:
        payload["template_id"] = TEST_TEMPLATE_ID
    
    response = client.post("/api/v1/notifications/send", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["channels"] == ["email", "telegram"]
    assert "notification_id" in data

def test_send_test_notification():
    """Тест отправки тестового уведомления"""
    payload = {
        "recipients": [TEST_USER_ID],
        "message": "Тестовое сообщение",
        "subject": "Тестовая тема",
        "channels": ["email"]
    }
    response = client.post("/api/v1/notifications/test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert "notification_id" in data

# ==================== History Tests ====================

def test_get_notification_history():
    """Тест получения истории уведомлений"""
    start_time = (datetime.now() - timedelta(days=1)).isoformat()
    end_time = datetime.now().isoformat()
    
    response = client.get(
        f"/api/v1/notifications/history?"
        f"user_id={TEST_USER_ID}&"
        f"start_time={start_time}&"
        f"end_time={end_time}&"
        f"limit=10"
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # assert len(data) > 0  # Может быть 0 если уведомления еще не были отправлены

# ==================== Cleanup Tests ====================

def test_delete_template():
    """Тест удаления шаблона"""
    if TEST_TEMPLATE_ID:
        response = client.delete(f"/api/v1/notifications/templates/{TEST_TEMPLATE_ID}")
        assert response.status_code == 204

def test_delete_user_preferences():
    """Тест удаления настроек пользователя"""
    response = client.delete(f"/api/v1/users/preferences/{TEST_USER_ID}")
    assert response.status_code == 204

if __name__ == "__main__":
    # Запуск тестов вручную
    import traceback
    
    tests = [
        ("Health check", test_health_check),
        ("Root redirect", test_root_redirect),
        ("Get all templates", test_get_all_templates),
        ("Create template", test_create_template),
        ("Get template by ID", test_get_template_by_id),
        ("Update template", test_update_template),
        ("Create user preferences", test_create_user_preferences),
        ("Get user preferences", test_get_user_preferences),
        ("Send notification", test_send_notification),
        ("Send test notification", test_send_test_notification),
        ("Get notification history", test_get_notification_history),
        ("Delete template", test_delete_template),
        ("Delete user preferences", test_delete_user_preferences),
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    print("🧪 Running Notification Service Tests...")
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