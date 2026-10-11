import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QPushButton, QDialog

from src.database import Database
from src.ui.dialogs.technician_panel import TechnicalServiceTechnicianPanel
from src.ui.dialogs._tp_operations import _TpOperations
from tools.quality.desktop_visual_acceptance import seed_visual_fixture


def test_reference_footer_saves_each_moved_field_and_preserves_other_devices(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    audit_events, status_events, debt_events, errors = [], [], [], []
    monkeypatch.setattr("src.utils.audit_logger.get_audit_logger", lambda db: SimpleNamespace(log_action=lambda *args: audit_events.append(args)))
    monkeypatch.setattr("src.ui.dialogs._tp_operations.show_success", lambda *args: None)
    monkeypatch.setattr("src.ui.dialogs._tp_operations.show_error", lambda *args: errors.append(args))
    db = Database(str(tmp_path / "save_mapping.db"))
    seed_visual_fixture(db)
    monkeypatch.setattr(db, "update_status", lambda tracking, status: status_events.append((tracking, status)) or True)
    monkeypatch.setattr(db, "_sync_service_debt_from_tracking", lambda tracking, **kwargs: debt_events.append((tracking, kwargs)))
    other_before = tuple(db.cursor.execute("SELECT * FROM devices WHERE tracking_no='DEMO-SRV-0007'").fetchone())
    panel = TechnicalServiceTechnicianPanel(db, "DEMO-SRV-0008")
    panel.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    panel.resize(1280, 837)
    panel.show()
    QTest.qWait(80)
    try:
        notes = panel.wizard_page2
        notes.txt_fault.setPlainText("Actual fault description")
        notes.txt_public_notes.setPlainText("Actual repair report")
        notes.txt_private_notes.setText("Actual private report")
        for index, toggle in enumerate(panel.wizard_page1.accessory_toggles.values()):
            toggle.setChecked(index == 0)
        finance = panel.wizard_page3
        finance.inp_labor.setText("123.45")
        finance.inp_cargo.setText("6.75")
        finance.combo_warranty.setCurrentText("Var")
        finance.date_warranty.setDate(QDate(2026, 10, 15))
        finance.combo_delivery.setCurrentText("Kargo")
        finance.combo_payment.setCurrentText("Cari Hesap")
        if notes.process_toggles:
            notes.process_toggles[0][1].setChecked(True)
        if panel.test_toggles:
            panel.test_toggles[0][1].setChecked(True)
        expected = {**panel.wizard_page1.get_data(), **notes.get_data(), **finance.get_data()}
        expected["device_type"] = panel.get_technical_service_profile()
        save_button = next(button for button in panel.footer.findChildren(QPushButton) if "Kaydet" in button.text())
        save_button.click()
        assert not errors
        assert panel.result() == QDialog.DialogCode.Accepted
        columns = ("status", "labor_cost", "fault_description", "repair_details", "internal_notes", "warranty_end_date", "warranty_status", "accessories", "cargo_fee", "delivery_type", "payment_status", "device_type")
        values = db.cursor.execute("SELECT " + ",".join(columns) + " FROM devices WHERE tracking_no=?", ("DEMO-SRV-0008",)).fetchone()
        assert dict(zip(columns, values)) == {key: expected[key] for key in columns}
        checklist = db.cursor.execute("SELECT checklist_status FROM devices WHERE tracking_no='DEMO-SRV-0008'").fetchone()[0]
        assert notes.process_toggles[0][0] in checklist
        assert panel.test_toggles[0][0] in checklist
        assert status_events == [("DEMO-SRV-0008", expected["status"])]
        assert debt_events == [("DEMO-SRV-0008", {"create_if_missing": True, "reason": "technician_panel_save"})]
        assert audit_events and audit_events[0][:2] == ("devices", "UPDATE")
        assert tuple(db.cursor.execute("SELECT * FROM devices WHERE tracking_no='DEMO-SRV-0007'").fetchone()) == other_before
    finally:
        panel.close()
        db.close()


def test_read_only_save_slot_does_not_collect_fields_or_touch_database():
    def forbidden():
        raise AssertionError("Read-only save must not collect fields")
    panel = SimpleNamespace(read_only=True, wizard_page1=SimpleNamespace(get_data=forbidden), wizard_page2=SimpleNamespace(get_data=forbidden), wizard_page3=SimpleNamespace(get_data=forbidden))
    _TpOperations.save_update(panel)
