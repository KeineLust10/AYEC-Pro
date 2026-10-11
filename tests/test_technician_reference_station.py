import os
from types import SimpleNamespace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QScrollArea, QLabel, QPushButton

from src.ui.dialogs.technician_panel import TechnicalServiceTechnicianPanel
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.currency_helper import CurrencyHelper
from src.ui.dialogs._tp_helpers import _TpHelpers
from src.utils.design_system import DesignTokens
from src.ui.widgets.reference_date_edit import ReferenceDateEdit
from src.utils.reference_typography import apply_reference_font
from src.utils.theme_manager import ThemeManager
from src.database import Database
from tools.quality.desktop_visual_acceptance import seed_visual_fixture


def test_station_summary_uses_actual_device_and_configuration_without_fake_telemetry(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    apply_reference_font(app)
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    db = Database(str(tmp_path / "technician_fixture.db"))
    seed_visual_fixture(db)
    location_id, location_name = db.cursor.execute("SELECT id,name FROM stock_locations ORDER BY id LIMIT 1").fetchone()
    used_part_ids = []
    for name, price, quantity in (("Actual fan", 7.25, 2), ("Actual paste", 4.0, 1)):
        db.cursor.execute("INSERT INTO used_parts (tracking_no,part_name,price,quantity,currency,exchange_rate,created_at,stock_location_id) VALUES (?,?,?,?,?,?,?,?)", ("DEMO-SRV-0008", name, price, quantity, "TRY", 1, "2026-09-21 10:35:00", location_id))
        used_part_ids.append(db.cursor.lastrowid)
    db.conn.commit()
    db.cursor.execute("UPDATE devices SET customer_name=?,technician=? WHERE tracking_no=?", ("Actual <Customer>", "Actual Technician", "DEMO-SRV-0008"))
    db.conn.commit()
    db.set_setting("technician_station_id", "ST-07")
    db.set_setting("technician_station_esd_status", "Inspection recorded")
    db.set_setting("technician_station_equipment", "Actual microscope")
    panel = TechnicalServiceTechnicianPanel(db, "DEMO-SRV-0008", read_only=True)
    ThemeManager.apply_theme(app, "Koyu Mavi", window=panel, animate=False)
    panel.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    panel.resize(1280, 1024)
    panel.show()
    app.processEvents()
    assert not [
        widget for widget in app.topLevelWidgets()
        if widget is not panel and widget.isVisible()
    ]
    assert panel.panel_summary_values["SERVIS KAYDI"].text() == "DEMO-SRV-0008"
    assert panel.panel_summary_values["SERVIS KAYDI"].font().family() == DesignTokens.MONO_FONT_NAME
    assert panel.panel_summary_values["SERVIS KAYDI"].toolTip() == "DEMO-SRV-0008"
    assert panel.panel_summary_values["MUSTERI"].text() == "Actual <Customer>"
    assert panel.panel_summary_values["MUSTERI"].textFormat() == Qt.TextFormat.PlainText
    assert panel.panel_summary_values["DURUM"].text() == panel.device_dict["status"]
    assert panel.station_values["ISTASYON"].text() == "ST-07 - Actual Technician"
    assert panel.station_values["GUVENLIK"].text() == "Inspection recorded"
    assert panel.station_values["DONANIM"].text() == "Actual microscope"
    panel.panel_elapsed = SimpleNamespace(elapsed=lambda: 3725000)
    panel._refresh_panel_elapsed()
    assert panel.station_values["PANEL SURESI"].text() == "01:02:05"
    assert panel.station_values["PANEL SURESI"].font().family() == DesignTokens.MONO_FONT_NAME
    scrolls = panel.general_widget.findChildren(QScrollArea)
    assert len(scrolls) >= 3
    assert all(scroll.horizontalScrollBarPolicy() != Qt.ScrollBarPolicy.ScrollBarAlwaysOff for scroll in scrolls)
    assert panel.general_loaded
    assert panel.wizard_page1.tracking_no == panel.wizard_page2.tracking_no == panel.wizard_page3.tracking_no == "DEMO-SRV-0008"
    assert panel.reference_hardware_values["CIHAZ MODELI"].text() == "AYEC Test Cihaz 08"
    assert panel.reference_hardware_values["KABUL TARIHI"].text() == panel.device_dict["entry_date"]
    for caption in ("KABUL TARIHI", "SERI NUMARASI"):
        label = panel.reference_hardware_values[caption]
        assert label.font().family() == DesignTokens.MONO_FONT_NAME
        assert label.toolTip() == label.text()
    parts = panel.wizard_page3
    assert isinstance(parts.date_warranty, ReferenceDateEdit)
    assert parts.date_warranty.displayFormat() == "dd.MM.yyyy"
    for editor in (parts.inp_labor, parts.inp_part_cost, parts.inp_cargo, parts.date_warranty):
        assert editor.font().family() == DesignTokens.MONO_FONT_NAME
    for combo in (parts.combo_status, parts.combo_warranty, parts.combo_delivery,
                  parts.combo_payment, parts.combo_stock_location, parts.combo_parts):
        assert combo.property("referenceChevron")
    assert not panel.wizard_page1.isHidden()
    for name in ("fault_grid", "process_grid", "private_grid"):
        grid = getattr(panel.wizard_page2, name)
        columns = 1 if name == "process_grid" else 2
        assert all(grid.getItemPosition(index)[1] < columns for index in range(grid.count()))
    notes = panel.wizard_page2
    note_position = notes.txt_fault.mapTo(notes.fault_group, QPoint(0, 0)).y()
    grid_position = notes.fault_grid.parentWidget().mapTo(notes.fault_group, QPoint(0, 0)).y()
    assert note_position < grid_position
    notes._suppress_ui_handlers = True
    if notes.fault_toggles:
        label, toggle = notes.fault_toggles[0]
        toggle.setChecked(False)
        notes.txt_fault.setPlainText("")
        toggle.setChecked(True)
        assert label in notes.txt_fault.toPlainText()
        assert label in notes.get_data()["checklist_status"]
    notes.txt_public_notes.setPlainText("Actual public note")
    notes.txt_private_notes.setText("Actual private note")
    assert notes.get_data()["repair_details"] == "Actual public note"
    assert notes.get_data()["internal_notes"] == "Actual private note"
    assert panel.wizard_page3.parts_group.parentWidget() != panel.wizard_page3
    assert panel.wizard_page3.table_used_parts.columnCount() == 5
    assert panel.wizard_page3.table_used_parts.horizontalHeader().visualIndex(4) == 1
    table = panel.wizard_page3.table_used_parts
    assert table.rowCount() == 2
    assert table.item(0, 0).text() == "Actual paste"
    assert table.item(0, 4).text() == location_name
    assert table.item(1, 4).text() == location_name
    deleted = []
    monkeypatch.setattr(panel.wizard_page3, "delete_part", deleted.append)
    for row, expected_id in enumerate(reversed(used_part_ids)):
        assert table.item(row, 0).data(Qt.ItemDataRole.UserRole) == expected_id
        for column in (1, 2):
            item = table.item(row, column)
            assert item.font().family() == DesignTokens.MONO_FONT_NAME
            assert item.toolTip() == item.text()
        assert table.cellWidget(row, 3).glyph == "delete"
        assert table.cellWidget(row, 3).accessibleName() == "delete_used_part"
        assert not table.cellWidget(row, 3).isEnabled()
        table.cellWidget(row, 3).clicked.emit(False)
        assert deleted[-1] == expected_id
    assert len(deleted) == 2
    assert panel.wizard_page3.inp_part_cost.text() == CurrencyHelper.format_try_for_display(18.50, db=db, include_try_reference=False)
    assert panel.wizard_page1.photos_grid.count() == 6
    assert all(panel.wizard_page1.photos_grid.getItemPosition(index)[0] == 0 for index in range(6))
    for group in (panel.wizard_page3.status_group, panel.wizard_page3.finance_group):
        grids = [group.layout().itemAt(index).layout() for index in range(group.layout().count())]
        grid = next(item for item in grids if item is not None)
        assert grid.columnCount() == 4
        assert grid.count() == 8
    for label in panel.general_widget.findChildren(QLabel):
        if label.accessibleName().startswith(("etiket_", "aksesuar_etiket_")):
            parent_toggles = label.parentWidget().findChildren(AnimatedToggle)
            if parent_toggles:
                toggle = parent_toggles[0]
                checked = toggle.isChecked()
                QTest.mouseClick(label, Qt.MouseButton.LeftButton)
                assert toggle.isChecked() == checked
    QTest.qWait(80)
    assert panel.test_toggles
    original_tests = tuple(panel.test_toggles)
    assert all(not toggle.isEnabled() for _, toggle in original_tests)
    original_test_widget = panel.test_widget
    panel.reference_tab_buttons[1].click()
    app.processEvents()
    assert panel.tabs.currentIndex() == 1
    assert panel.reference_tab_buttons[1].isChecked()
    assert panel.test_widget is original_test_widget
    assert panel.tabs.widget(1) is original_test_widget
    assert tuple(panel.test_toggles) == original_tests
    panel.reference_tab_buttons[0].click()
    app.processEvents()
    assert panel.test_widget is original_test_widget
    assert panel.tabs.widget(1) is original_test_widget
    assert tuple(panel.test_toggles) == original_tests
    assert not panel.cmb_technical_profile_main.isEnabled()
    station_parent = panel.station_bar.parentWidget()
    def station_exec(dialog):
        assert panel.station_bar.parentWidget() is dialog.content_container
        assert panel.station_values["ISTASYON"].text() == "ST-07 - Actual Technician"
        assert dialog.footer.isVisibleTo(dialog)
        assert dialog.footer.findChildren(QPushButton)
        return 0
    monkeypatch.setattr(ModernDialog, "exec", station_exec)
    panel._show_reference_station()
    assert panel.station_bar.parentWidget() is station_parent
    assert panel.station_bar.isHidden()
    changes_before = db.conn.total_changes
    cached_before = getattr(panel, "checklist_status", None)
    monkeypatch.setattr(panel, "_save_cached_checklist_status", lambda *_: (_ for _ in ()).throw(AssertionError("Read-only panel must not write cached state")))
    panel._persist_toggle_state("Unexpected mutation")
    assert getattr(panel, "checklist_status", None) == cached_before
    assert db.conn.total_changes == changes_before
    assert not panel.grab().isNull()
    panel.setMaximumSize(1280, 837)
    panel.resize(1280, 837)
    app.processEvents()
    for row in range(table.rowCount()):
        date_item = table.item(row, 2)
        assert table.visualItemRect(date_item).width() >= QFontMetrics(date_item.font()).horizontalAdvance(date_item.text()) + 16
    screenshot = Path(__file__).resolve().parents[1] / "artifacts" / "technician_reference_data.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    assert panel.grab().save(str(screenshot))
    panel.close()
    assert not panel.panel_elapsed_timer.isActive()
    db.close()


def test_visual_fixture_checklist_cache_does_not_read_or_write_production_preferences(monkeypatch):
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    def production_settings(*args):
        raise AssertionError("Visual fixture must not access production preferences")
    monkeypatch.setattr("src.ui.dialogs._tp_helpers.QSettings", production_settings)
    fixture_type = type("FixtureHelpers", (_TpHelpers,), {"_session_toggle_cache": {"existing": "Production value"}})
    first = fixture_type()
    first.tracking_no = "SAME-TRACKING-ID"
    first.device_dict = {"checklist_status": "Actual fixture result"}
    second = fixture_type()
    second.tracking_no = "SAME-TRACKING-ID"
    second.device_dict = {"checklist_status": "Second fixture result"}
    assert first._load_cached_checklist_status() == "Actual fixture result"
    first._save_cached_checklist_status("Temporary change")
    assert first._load_cached_checklist_status() == "Temporary change"
    assert second._load_cached_checklist_status() == "Second fixture result"
    assert fixture_type._session_toggle_cache == {"existing": "Production value"}
