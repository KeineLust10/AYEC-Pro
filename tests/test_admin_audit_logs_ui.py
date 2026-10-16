import sys
from pathlib import Path
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from pages.audit_logs import AuditLogsPage


def test_audit_risk_uses_explicit_severity_and_high_impact_actions():
    assert AuditLogsPage._risk_for({"action": "admin_password_reset"}) == "low"
    assert AuditLogsPage._risk_for({"action": "admin_readonly_query"}) == "low"
    assert AuditLogsPage._risk_for({"action": "admin_license_cancelled"}) == "critical"
    assert AuditLogsPage._risk_for({"severity": "critical"}) == "critical"
    assert AuditLogsPage._risk_for({"detail": "legacy text"}) == "low"


def test_audit_stream_search_and_detail(persistent_qapplication, monkeypatch, tmp_path):
    monkeypatch.setattr(AuditLogsPage, "_load_companies", lambda self: None)
    page = AuditLogsPage()
    page._populate_logs(
        [
            {"id": "AUD-1", "created_at": "2026-10-14 09:00", "action": "admin_license_updated", "company_name": "ASLAN TIC", "actor_user_id": 7, "ip_address": "192.168.1.108", "record_hash": "e3b0c44298fc1c149afbf4c8996fb924", "previous_hash": "9a7b1402", "detail": {"description": "The license plan changed.", "before": {"plan": "basic"}, "after": {"plan": "pro"}, "user_agent": "AYEC Pro Desktop"}},
            {"id": "AUD-2", "created_at": "2026-10-14 09:10", "action": "admin_notification_sent", "company_name": "Babali Servis", "actor_user_id": 8, "detail": {"title": "Maintenance"}},
        ]
    )

    assert page._table.rowCount() == 2
    assert page._table.columnCount() == 7
    assert len(page._event_cards) == 2
    assert "Lisans g\u00fcncellendi" in page._event_cards[0].findChild(QLabel, "auditAction").text()
    assert page._table.item(0, 4).text() == "Dusuk"
    assert page._metric_values["total"][0].text() == "2"
    assert page._metric_values["actors"][0].text() == "2"
    page._set_category("license")
    assert not page._table.isRowHidden(0)
    assert page._table.isRowHidden(1)
    assert not page._event_cards[0].isHidden()
    assert page._event_cards[1].isHidden()
    page._set_category("all")
    page._search.setText("aslan")
    assert not page._table.isRowHidden(0)
    assert page._table.isRowHidden(1)
    page._show_detail(0, 0, -1, -1)
    assert "AUD-1" in page._detail.toPlainText()
    assert "basic" in page._detail.toPlainText()
    assert "pro" in page._detail.toPlainText()
    assert "192.168.1.108" in page._detail.toPlainText()
    assert "e3b0c442" in page._detail.toPlainText()
    assert page._event_cards[0].property("selected") == "true"
    export_path = tmp_path / "audit.csv"
    monkeypatch.setattr("pages.audit_logs.QFileDialog.getSaveFileName", lambda *args: (str(export_path), "CSV"))
    page._export_csv()
    exported = export_path.read_text(encoding="utf-8-sig")
    assert "SHA-256," in exported
    assert len(exported.rstrip().split(",")[-1]) == 64
    assert page._metric_values["exports"][0].text() == "1 Rapor"


def test_audit_reference_copy_maps_privileged_actions_and_category_labels(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(AuditLogsPage, "_load_companies", lambda self: None)
    page = AuditLogsPage()
    page._populate_logs([
        {"id": "AUD-9942", "action": "admin_password_reset_link", "company_name": "ASLAN TIC"}
    ])

    assert page._event_cards[0].findChild(QLabel, "auditAction").text() == "Kullan\u0131c\u0131 Ge\u00e7ici Parola Atama"
    assert page._category_buttons["identity"].property("baseLabel") == "Kimlik && Parola"
    assert page._category_buttons["license"].property("baseLabel") == "Lisans && Yetki"
    assert page._category_buttons["backup"].property("baseLabel") == "Yedekleme && Restore"
    assert page._search.placeholderText() == "Islem adi, yonetici kimligi, IP veya kayit numarasi ara (#AUD-9942)..."
    page.close()


def test_audit_layout_stacks_and_reflows_without_mobile_page_overflow(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(AuditLogsPage, "_load_companies", lambda self: None)
    page = AuditLogsPage()
    page._populate_logs(
        [{"id": "AUD-1", "created_at": "2026-10-14 09:00", "action": "admin_license_updated", "company_name": "ASLAN TIC", "actor_user_id": 7}]
    )
    page.resize(1440, 1000)
    page.show()
    persistent_qapplication.processEvents()
    assert page._root_layout.contentsMargins().left() == 40
    assert page._root_layout.contentsMargins().right() == 16

    page.resize(390, 844)
    persistent_qapplication.processEvents()

    assert page._audit_splitter.orientation() == Qt.Orientation.Vertical
    assert page._page_scroll.horizontalScrollBar().maximum() == 0
    assert page._metrics_grid.itemAtPosition(0, 1) is not None
    assert page._metrics_grid.itemAtPosition(0, 2) is None
    assert page._category_buttons["all"].text().startswith("T")
    assert page._category_scroll.horizontalScrollBar().value() == 0
    assert page._search.width() <= page._page_scroll.viewport().width()
    assert page._company.width() <= page._page_scroll.viewport().width()
    page.close()


def test_hash_integrity_button_reports_verified_mismatched_and_missing_links(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(AuditLogsPage, "_load_companies", lambda self: None)
    page = AuditLogsPage()
    assert not page._verify_integrity_button.icon().isNull()
    page._logs = [
        {"id": "new", "record_hash": "new-hash", "previous_hash": "old-hash"},
        {"id": "old", "record_hash": "old-hash"},
    ]
    page._verify_integrity_button.click()
    assert "1 ba\u011flant\u0131 do\u011fruland\u0131" in page._status.text()

    page._logs[0]["previous_hash"] = "wrong-hash"
    page._verify_integrity_button.click()
    assert "1 tutars\u0131z ba\u011flant\u0131" in page._status.text()

    page._logs = [{"id": "single", "record_hash": "hash"}]
    page._verify_integrity_button.click()
    assert "Do\u011frulanabilir hash ba\u011flant\u0131s\u0131 bulunamad\u0131" in page._status.text()
    page.close()
