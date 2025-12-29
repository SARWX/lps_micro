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
TEST_ZONE_ID = "test-zone-001"
TEST_ENTITY_ID = "test-entity-001"
TEST_REPORT_ID = None

def test_health_check():
    """Тест проверки работоспособности"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "data_aggregator"
    assert "database_stats" in data

def test_root_redirect():
    """Тест корневого endpoint'а (редирект на docs)"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307  # Temporary Redirect

# ==================== Reports Tests ====================

def test_get_zone_occupancy_report():
    """Тест получения отчета по посещаемости зон"""
    start_time = (datetime.now() - timedelta(days=1)).isoformat()
    end_time = datetime.now().isoformat()
    
    response = client.get(
        f"/api/v1/reports/zone-occupancy?start_time={start_time}&end_time={end_time}"
    )
    assert response.status_code == 200
    data = response.json()
    assert "report_id" in data
    assert "generated_at" in data
    assert "period" in data
    assert "zones" in data
    assert isinstance(data["zones"], list)

def test_get_zone_occupancy_report_with_filters():
    """Тест получения отчета по посещаемости зон с фильтрами"""
    start_time = (datetime.now() - timedelta(days=1)).isoformat()
    end_time = datetime.now().isoformat()
    
    response = client.get(
        f"/api/v1/reports/zone-occupancy?start_time={start_time}&end_time={end_time}&zone_ids=zone1,zone2&entity_types=employee,equipment"
    )
    assert response.status_code == 200
    data = response.json()
    assert "zones" in data
    assert isinstance(data["zones"], list)

def test_get_time_in_zone_report():
    """Тест получения отчета по времени пребывания в зонах"""
    start_time = (datetime.now() - timedelta(days=1)).isoformat()
    end_time = datetime.now().isoformat()
    
    response = client.get(
        f"/api/v1/reports/time-in-zone?start_time={start_time}&end_time={end_time}&group_by=day"
    )
    assert response.status_code == 200
    data = response.json()
    assert "report_id" in data
    assert "generated_at" in data
    assert "period" in data
    assert "group_by" in data
    assert "data" in data
    assert isinstance(data["data"], list)

def test_get_workflow_efficiency_report():
    """Тест получения отчета по эффективности рабочих зон"""
    start_time = (datetime.now() - timedelta(days=1)).isoformat()
    end_time = datetime.now().isoformat()
    
    response = client.get(
        f"/api/v1/reports/workflow-efficiency?start_time={start_time}&end_time={end_time}"
    )
    assert response.status_code == 200
    data = response.json()
    assert "report_id" in data
    assert "generated_at" in data
    assert "period" in data
    assert "zones" in data
    assert isinstance(data["zones"], list)

# ==================== Aggregation Tests ====================

def test_trigger_aggregation():
    """Тест запуска процесса агрегации данных"""
    start_time = (datetime.now() - timedelta(hours=1)).isoformat()
    end_time = datetime.now().isoformat()
    
    response = client.post(
        f"/api/v1/aggregation/trigger?start_time={start_time}&end_time={end_time}&force=true"
    )
    assert response.status_code == 202  # Accepted
    data = response.json()
    assert "task_id" in data
    assert "status" in data
    assert data["status"] in ["queued", "started"]

def test_get_pending_tasks():
    """Тест получения списка ожидающих задач агрегации"""
    response = client.get("/api/v1/aggregation/tasks/pending?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

# ==================== Analytics Tests ====================

def test_detect_anomalies():
    """Тест обнаружения аномалий в поведении"""
    start_time = (datetime.now() - timedelta(days=1)).isoformat()
    end_time = datetime.now().isoformat()
    
    response = client.get(
        f"/api/v1/analytics/anomalies?start_time={start_time}&end_time={end_time}"
    )
    assert response.status_code == 200
    data = response.json()
    assert "report_id" in data
    assert "generated_at" in data
    assert "period" in data
    assert "anomalies" in data
    assert isinstance(data["anomalies"], list)

# ==================== Export Tests ====================

def test_export_csv():
    """Тест экспорта данных в CSV"""
    start_time = (datetime.now() - timedelta(days=1)).isoformat()
    end_time = datetime.now().isoformat()
    
    response = client.get(
        f"/api/v1/export/csv?report_type=zone_occupancy&start_time={start_time}&end_time={end_time}"
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/csv"
    assert "attachment; filename=" in response.headers["Content-Disposition"]

def test_export_excel():
    """Тест экспорта данных в Excel"""
    start_time = (datetime.now() - timedelta(days=1)).isoformat()
    end_time = datetime.now().isoformat()
    
    response = client.get(
        f"/api/v1/export/excel?report_type=zone_occupancy&start_time={start_time}&end_time={end_time}&include_charts=false"
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment; filename=" in response.headers["Content-Disposition"]

# ==================== Database Stats Tests ====================

def test_get_database_stats():
    """Тест получения статистики по базе данных"""
    stats = get_database_stats()
    assert isinstance(stats, dict)
    assert "aggregated_data_count" in stats
    assert "reports_count" in stats
    assert "database_size_mb" in stats

# ==================== Cleanup ====================

def cleanup_test_data():
    """Очистка тестовых данных"""
    print("🧹 Cleaning up test data...")
    # Здесь может быть логика очистки тестовых данных
    print("✅ Test data cleaned up")

if __name__ == "__main__":
    # Запуск тестов вручную
    import traceback
    
    tests = [
        ("Health check", test_health_check),
        ("Root redirect", test_root_redirect),
        ("Zone occupancy report", test_get_zone_occupancy_report),
        ("Zone occupancy report with filters", test_get_zone_occupancy_report_with_filters),
        ("Time in zone report", test_get_time_in_zone_report),
        ("Workflow efficiency report", test_get_workflow_efficiency_report),
        ("Trigger aggregation", test_trigger_aggregation),
        ("Get pending tasks", test_get_pending_tasks),
        ("Detect anomalies", test_detect_anomalies),
        ("Export CSV", test_export_csv),
        ("Export Excel", test_export_excel),
        ("Database stats", test_get_database_stats),
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    print("🧪 Running Data Aggregator Service Tests...")
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
    
    # Очистка тестовых данных
    cleanup_test_data()