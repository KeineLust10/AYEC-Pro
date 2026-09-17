from src.ui.pages.accounting_dialogs.transaction_details_dialog import (
    _format_service_item_total,
)
from src.utils.finance_manager import FinanceManager
from src.database import Database
from src.ui.pages.accounting_dialogs.transaction_details_dialog import TransactionDetailsDialog


class FakeCursor:
    def execute(self, *args, **kwargs):
        return self

    def fetchone(self):
        return (0.0,)


class FakeDb:
    def __init__(self):
        self.cursor = FakeCursor()

    def get_setting(self, key, default=""):
        return default

    def get_internal_setting(self, key, default=""):
        return default


def test_stock_detail_uses_line_total_and_currency():
    value = _format_service_item_total(
        FakeDb(),
        {"currency": "USD"},
        {
            "kind": "stock_purchase",
            "name": "M2 SSD 1 TB",
            "quantity": 10,
            "unit_price": 120,
            "line_total": 1200,
            "currency": "USD",
        },
        10,
    )

    assert value == "1,200.00 $"


def test_income_tax_does_not_invent_blanket_vat():
    manager = FinanceManager(FakeDb())

    result = manager.calculate_income_tax(0, 56484.60, period="fiscal")

    assert result["expense_excl_vat"] == 56484.60
    assert result["vat_paid"] == 0.0
    assert result["net_after_tax"] == -56484.60


def test_dashboard_net_profit_uses_actual_ledger_totals(monkeypatch):
    manager = FinanceManager(FakeDb())
    monkeypatch.setattr(manager, "_calculate_revenue", lambda *_: 0.0)
    monkeypatch.setattr(manager, "_calculate_expenses", lambda *_: 56484.60)
    monkeypatch.setattr(manager, "_calculate_hot_cash", lambda *_: -56484.60)
    monkeypatch.setattr(manager, "_calculate_service_revenue", lambda *_: 0.0)
    monkeypatch.setattr(manager, "_calculate_pending_collections", lambda: (0.0, {}))
    monkeypatch.setattr(
        manager,
        "_calculate_uninvoiced_stats",
        lambda *_: {"count": 0, "sum": 0.0},
    )

    result = manager.get_financial_summary("fiscal")

    assert result["expenses"] == 56484.60
    assert result["net_revenue"] == 0.0
    assert result["pocket_net"] == -56484.60


def test_dashboard_does_not_apply_blanket_vat_to_revenue(monkeypatch):
    manager = FinanceManager(FakeDb())
    monkeypatch.setattr(manager, "_calculate_revenue", lambda *_: 1200.0)
    monkeypatch.setattr(manager, "_calculate_expenses", lambda *_: 0.0)
    monkeypatch.setattr(manager, "_calculate_hot_cash", lambda *_: 1200.0)
    monkeypatch.setattr(manager, "_calculate_service_revenue", lambda *_: 0.0)
    monkeypatch.setattr(manager, "_calculate_pending_collections", lambda: (0.0, {}))
    monkeypatch.setattr(
        manager,
        "_calculate_uninvoiced_stats",
        lambda *_: {"count": 0, "sum": 0.0},
    )

    result = manager.get_financial_summary("fiscal")

    assert result["gross_revenue"] == 1200.0
    assert result["net_revenue"] == 1200.0
    assert result["pocket_net"] == 1200.0


def test_collection_detail_resolves_service_work_and_parts(tmp_path):
    db = Database(str(tmp_path / "finance-service-detail.db"))
    customer_id = db.add_customer({"name": "Finance Detail Customer"})
    tracking_no = "SRV-FIN-001"
    db.add_device(
        {
            "tracking_no": tracking_no,
            "customer_id": customer_id,
            "customer_name": "Finance Detail Customer",
            "device_type": "Arac",
            "device_brand": "Ford",
            "device_model": "Courier",
            "status": "Bekliyor",
            "repair_details": "Yag ve filtre degistirildi",
            "labor_cost": 2500,
        }
    )
    part_id = db.add_part("Yag Filtresi", "Filtre", 3, 500, purchase_price=250)
    assert db.use_part(part_id, 1, tracking_no)
    assert db.add_currency_transaction(
        customer_id=customer_id,
        amount=1500,
        currency="TRY",
        transaction_type="CREDIT",
        description=f"Ref: {tracking_no} | Cari borc kapatma tahsilat",
        tracking_no=tracking_no,
    )

    entry = next(
        row
        for row in FinanceManager(db).get_unified_ledger()
        if row["source"] == "currency" and row["type_label"] == "Tahsilat"
    )
    assert entry["tracking_no"] == tracking_no
    assert entry["customer_name"] == "Finance Detail Customer"

    detail = TransactionDetailsDialog.__new__(TransactionDetailsDialog)
    detail.db = db
    detail.entry = entry
    rows = detail._load_device_service_rows()
    names = [row[0] for row in rows]
    assert any("Yap\u0131lan \u0130\u015flem" in name for name in names)
    assert any("\u0130\u015f\u00e7ilik" in name for name in names)
    assert "Yag Filtresi" in names
    db.close()


def test_collection_detail_restores_all_maintenance_items(tmp_path):
    db = Database(str(tmp_path / "finance-maintenance-detail.db"))
    customer_id = db.add_customer({"name": "Maintenance Detail Customer"})
    tracking_no = "SRV-MAINT-001"
    device_id = db.add_device(
        {
            "tracking_no": tracking_no,
            "customer_id": customer_id,
            "customer_name": "Maintenance Detail Customer",
            "device_type": "Arac",
            "status": "Bekliyor",
            "fault_description": "Bakim kalemleri: Yag, Filtre ve 4 kalem daha",
        }
    )
    db.cursor.execute(
        "INSERT INTO vehicle_maintenance_cards "
        "(customer_id, customer_name, linked_device_tracking_no, linked_device_id) "
        "VALUES (?, ?, ?, ?)",
        (customer_id, "Maintenance Detail Customer", tracking_no, device_id),
    )
    card_id = db.cursor.lastrowid
    labels = ["Yag", "Yag Filtresi", "Hava Filtresi", "Polen Filtresi", "Antifriz", "Buji"]
    for label in labels:
        db.cursor.execute(
            "INSERT INTO vehicle_maintenance_items "
            "(card_id, item_type, item_label, performed) VALUES (?, ?, ?, 1)",
            (card_id, label.lower().replace(" ", "_"), label),
        )
    db.cursor.execute(
        "UPDATE devices SET vehicle_maintenance_card_id=? WHERE id=?",
        (card_id, device_id),
    )
    db.conn.commit()

    detail = TransactionDetailsDialog.__new__(TransactionDetailsDialog)
    detail.db = db
    detail.entry = {"tracking_no": tracking_no}
    rows = detail._load_device_service_rows()
    work_rows = [row[0].split(": ", 1)[1] for row in rows if ": " in row[0]]

    assert work_rows == labels
    assert all("kalem daha" not in row for row in work_rows)
    db.close()
