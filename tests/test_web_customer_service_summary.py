import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import Database
from Web_Arayuzu import Main as web_main


def test_customer_bootstrap_service_counts_match_desktop_filters(tmp_path, monkeypatch):
    database_path = tmp_path / "customer-service-summary.db"
    db = Database(str(database_path))
    customer_name = "Service Summary Customer"
    customer_id = db.add_customer({"name": customer_name, "phone": "5550100"})
    for tracking_no, status in (
        ("SUMMARY-TEST-1", "Test / Onay"),
        ("SUMMARY-REPAIR-1", "Tamirde"),
        ("SUMMARY-READY-1", "Teslimata Hazir"),
        ("SUMMARY-DONE-1", "Tamamlandi"),
        ("SUMMARY-ARCHIVED-1", "Bekliyor"),
    ):
        db.add_device({
            "tracking_no": tracking_no,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "device_type": "Laptop",
            "status": status,
        })
    db.add_device({
        "tracking_no": "SUMMARY-LEGACY-1",
        "customer_id": None,
        "customer_name": customer_name,
        "device_type": "Laptop",
        "status": "Test / Onay",
    })
    db.cursor.execute(
        "UPDATE devices SET is_archived=1 WHERE tracking_no=?",
        ("SUMMARY-ARCHIVED-1",),
    )
    other_customer_id = db.add_customer({"name": "Other Service Summary Customer"})
    db.cursor.executemany(
        "INSERT INTO offers (offer_no, customer_id, customer_name, status) VALUES (?, ?, ?, ?)",
        (
            ("SUMMARY-OFFER-PENDING", customer_id, customer_name, "sent"),
            ("SUMMARY-OFFER-DRAFT", customer_id, customer_name, "draft"),
            ("SUMMARY-OFFER-OTHER", other_customer_id, "Other Service Summary Customer", "waiting"),
        ),
    )
    db.conn.commit()
    db.close()

    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    payload = web_main.desktop_bootstrap()
    customer = next(item for item in payload["customers"] if item["id"] == customer_id)
    other_customer = next(item for item in payload["customers"] if item["id"] == other_customer_id)

    assert customer["service_counts"] == {
        "open": 4,
        "test": 2,
        "repair": 1,
        "maintenance": 0,
        "delivery_ready": 1,
        "delivered": 1,
        "pending_offers": 1,
    }
    assert other_customer["service_counts"]["pending_offers"] == 1
    web_main.clear_tenant_context()
