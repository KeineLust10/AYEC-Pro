import csv
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QFileDialog, QWidget
from PyQt6.QtCore import Qt

from src.database import Database
from src.ui.pages.audit_log_page import AuditLogPage
from src.ui.pages.audit_log_page import _audit_record_metadata
from src.utils.audit_export import export_audit_csv, audit_event_text
from src.utils.audit_logger import AuditLogger
from tools.quality.desktop_visual_acceptance import seed_visual_fixture


def test_audit_buttons_export_only_visible_real_events_and_selected_pdf(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    db = Database(str(tmp_path / "audit_export.db"))
    seed_visual_fixture(db)
    page = AuditLogPage(db, audit_logger=AuditLogger(db))
    users = [tuple(row) for row in db.conn.execute("SELECT * FROM users ORDER BY id")]
    audit_rows = [tuple(row) for row in db.conn.execute("SELECT * FROM audit_logs ORDER BY id")]
    csv_path = tmp_path / "audit.csv"
    pdf_path = tmp_path / "audit.pdf"
    try:
        assert page.table.columnCount() == 7
        assert page.table.isColumnHidden(2)
        page.raw_columns_button.setChecked(True)
        assert not page.table.isColumnHidden(2)
        page.raw_columns_button.setChecked(False)
        for row in range(page.table.rowCount()):
            raw = page.table.item(row, 0).data(256)
            assert page.table.item(row, 1).text() == str(raw[1])
            assert str(raw[2]) in page.table.cellWidget(row, 3).text()
            assert page.table.item(row, 4).text() == str(raw[4])
            severity, station = _audit_record_metadata(raw)
            assert page.table.item(row, 5).text() == severity
            assert page.table.item(row, 6).text() == station
        known_name = page.table.cellWidget(0, 1).text().split("\n")[0]
        page.audit_search.setText(known_name)
        assert not page.table.isRowHidden(0)
        page._reset_audit_filters()
        page.audit_scope.setCurrentText("Finans")
        finance_tables = [page.table.item(row, 2).text() for row in range(page.table.rowCount()) if not page.table.isRowHidden(row)]
        assert set(finance_tables) == {"CURRENCY_TRANSACTIONS", "E_INVOICE"}
        page.audit_scope.setCurrentText("Servis")
        service_tables = [page.table.item(row, 2).text() for row in range(page.table.rowCount()) if not page.table.isRowHidden(row)]
        assert service_tables == ["SRV_REPAIR_JOB"]
        page.audit_severity_buttons["WARN"].click()
        assert page.audit_severity == "WARN"
        assert sum(button.isChecked() for button in page.audit_severity_buttons.values()) == 1
        page._reset_audit_filters()
        assert page.audit_severity_buttons["Tumu"].isChecked()
        assert page.audit_scope.currentIndex() == 0
        page.audit_search.setText("currency_transactions")
        visible = [page.table.item(row, 0).data(256) for row in range(page.table.rowCount()) if not page.table.isRowHidden(row)]
        assert visible
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(csv_path), "CSV (*.csv)"))
        page.export_logs_button.click()
        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            exported = list(csv.reader(stream))
        assert len(exported) == len(visible) + 1
        assert exported[1:] == [[str(value or "") for value in row] for row in visible]
        selected = page.inspector_log
        assert selected in visible
        assert str(selected[0]) in audit_event_text(selected)
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(pdf_path), "PDF (*.pdf)"))
        page.event_report_button.click()
        assert pdf_path.read_bytes().startswith(b"%PDF-")
        assert pdf_path.stat().st_size > 1000
        page.audit_search.setText("not-a-record")
        assert page.inspector_log is None
        assert not page.event_report_button.isEnabled()
        assert users == [tuple(row) for row in db.conn.execute("SELECT * FROM users ORDER BY id")]
        assert audit_rows == [tuple(row) for row in db.conn.execute("SELECT * FROM audit_logs ORDER BY id")]
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: ("", ""))
        page.export_logs_button.click()
    finally:
        page.timer.stop()
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_csv_cells_preserve_text_without_spreadsheet_formula_execution(tmp_path):
    target = tmp_path / "safe_audit.csv"
    export_audit_csv(target, [(1, "=SUM(1,2)", "users", "UPDATE", "+external-command", "2026-09-30")])
    with target.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    assert rows[1][1] == "'=SUM(1,2)"
    assert rows[1][4] == "'+external-command"


def test_audit_metadata_uses_recorded_values_only():
    assert _audit_record_metadata((1, "user", "users", "UPDATE", "plain text", "timestamp")) == ("-", "-")
    assert _audit_record_metadata((1, "user", "users", "UPDATE", '{"severity":"WARN","station":"depot","client_ip":"192.0.2.1"}', "timestamp")) == ("WARN", "depot / 192.0.2.1")
    assert _audit_record_metadata((1, "user", "users", "UPDATE", "[]", "timestamp")) == ("-", "-")


def test_audit_paging_and_filters_cover_records_beyond_first_hundred(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    from src.utils.system_config import SystemConfig
    monkeypatch.setattr(SystemConfig, "is_feature_active", staticmethod(lambda *_args: False))
    db = Database(str(tmp_path / "audit_paging.db"))
    seed_visual_fixture(db)
    db.conn.executemany(
        "INSERT INTO audit_logs (user_id, table_name, action, details, created_at) VALUES (?, ?, ?, ?, ?)",
        [("1", "users", "UPDATE", '{"severity":"WARN","marker":"event-%03d"}' % index, "2026-09-30 12:00:00") for index in range(125)],
    )
    db.conn.commit()
    users = [tuple(row) for row in db.conn.execute("SELECT * FROM users ORDER BY id")]
    page = AuditLogPage(db, audit_logger=AuditLogger(db))
    try:
        assert not hasattr(page, "tab_guide")
        assert not page.timer.isActive()
        page.show()
        app.processEvents()
        assert page.timer.isActive()
        assert page.audit_filtered_count == 130
        assert page.table.rowCount() == 25
        first_ids = {page.table.item(row, 0).data(256)[0] for row in range(25)}
        page.audit_next_button.click()
        assert page.audit_page_index == 1
        second_ids = {page.table.item(row, 0).data(256)[0] for row in range(25)}
        assert first_ids.isdisjoint(second_ids)
        page.audit_search.setText("event-000")
        assert page.audit_page_index == 0
        assert page.audit_filtered_count == 1
        assert page.table.rowCount() == 1
        assert "event-000" in page.inspector_details.text()
        assert page.table.item(0, 5).text() == "WARN"
        page.audit_search.clear()
        page.audit_severity_buttons["WARN"].click()
        assert page.audit_filtered_count == 126
        page._reset_audit_filters()
        page.btn_live_stream.click()
        db.conn.execute("INSERT INTO audit_logs (user_id, table_name, action, details, created_at) VALUES ('1','users','UPDATE','timer-record','2026-09-30 13:00:00')")
        db.conn.commit()
        page.timer.timeout.emit()
        assert page.audit_filtered_count == 130
        page.btn_live_stream.click()
        page.timer.timeout.emit()
        assert page.audit_filtered_count == 131
        page.hide()
        app.processEvents()
        assert not page.timer.isActive()
        assert users == [tuple(row) for row in db.conn.execute("SELECT * FROM users ORDER BY id")]
    finally:
        page.timer.stop()
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_audit_account_suspension_requires_admin_confirmation_and_same_database(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
    db = Database(str(tmp_path / "audit_account_action.db"))
    seed_visual_fixture(db)
    page = AuditLogPage(db)
    owner = QWidget()
    owner.db = db
    owner.current_user = {"id": 3, "role": "Master"}
    owner.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    page.setParent(owner)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    page.show()
    owner.show()
    app.processEvents()
    before = {row["id"]: dict(row) for row in db.conn.execute("SELECT * FROM users")}
    try:
        assert page.audit_logger.db is db
        assert page.inspector_log[1] == "1"
        assert page.suspend_user_button.isEnabled()
        owner.current_user = {"id": 4, "role": "Muhasebe"}
        page._update_audit_inspector()
        assert not page.suspend_user_button.isEnabled()
        owner.current_user = {"id": 1, "role": "Admin"}
        page._update_audit_inspector()
        assert not page.suspend_user_button.isEnabled()
        owner.current_user = {"id": 3, "role": "Master"}
        owner.db = object()
        page._update_audit_inspector()
        assert not page.suspend_user_button.isEnabled()
        owner.db = db
        page._update_audit_inspector()
        assert page.suspend_user_button.isEnabled()
        monkeypatch.setattr(ModernConfirmDialog, "exec", lambda _dialog: 0)
        page.suspend_user_button.click()
        assert before == {row["id"]: dict(row) for row in db.conn.execute("SELECT * FROM users")}
        monkeypatch.setattr(ModernConfirmDialog, "exec", lambda _dialog: 1)
        page.suspend_user_button.click()
        expected = {key: dict(value) for key, value in before.items()}
        expected[1]["active"] = 0
        assert expected == {row["id"]: dict(row) for row in db.conn.execute("SELECT * FROM users")}
        assert not page.suspend_user_button.isEnabled()
    finally:
        page.timer.stop()
        page.close()
        page.deleteLater()
        owner.close()
        owner.deleteLater()
        app.processEvents()
        db.close()
