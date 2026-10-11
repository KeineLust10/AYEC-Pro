"""Reference settings navigation behavior without a visible desktop."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QWidget

from src.ui.pages.settings_sidebar import PremiumSettingsSidebar, SETTINGS_GLYPHS
from src.utils.theme_manager import ThemeManager


def test_settings_routes_metadata_and_role_isolation():
    app = QApplication.instance() or QApplication([])
    sidebar = PremiumSettingsSidebar(lambda _page: None, current_user={"role": "Admin"})
    staff = PremiumSettingsSidebar(lambda _page: None, current_user={"role": "Personel"})
    try:
        assert sidebar.header_label.font().family() == "Inter"
        for row in sidebar._category_rows:
            assert sidebar.list_widget.item(row).font().family() == "Inter"
        assert {item['page_id'] for item in sidebar.iter_items()} == set(SETTINGS_GLYPHS)
        assert 24 not in staff.items_map
        for entry in sidebar.iter_items():
            item = sidebar.list_widget.item(entry['row'])
            assert entry['title'] == item.text()
            assert not item.icon().isNull()
            assert item.toolTip() == item.text()
            assert item.data(Qt.ItemDataRole.UserRole + 1) == SETTINGS_GLYPHS[entry['page_id']]
        assert not sidebar.grab().isNull()
        row = sidebar.items_map.index(6)
        sidebar.list_widget.item(row).setText("Custom   Theme Label")
        assert next(entry for entry in sidebar.iter_items() if entry['page_id'] == 6)['title'] == "Custom   Theme Label"
    finally:
        sidebar.deleteLater()
        staff.deleteLater()
        app.processEvents()


def test_accordion_search_restores_active_leaf_without_duplicate_navigation():
    app = QApplication.instance() or QApplication([])
    changes = []
    sidebar = PremiumSettingsSidebar(changes.append, current_user={"role": "Admin"})
    try:
        target_row = sidebar.items_map.index(6)
        category = next(row for row, children in sidebar._category_rows.items() if target_row in children)
        sidebar.list_widget.setCurrentRow(target_row)
        assert changes == [6]
        sidebar._toggle_category(category)
        assert sidebar.list_widget.item(target_row).isHidden()
        sidebar.search_inp.setText("Temalar")
        assert not sidebar.list_widget.item(target_row).isHidden()
        assert sidebar.list_widget.currentRow() == target_row
        assert changes == [6]
        sidebar.search_inp.clear()
        assert sidebar.list_widget.item(target_row).isHidden()
        sidebar._toggle_category(category)
        assert not sidebar.list_widget.item(target_row).isHidden()
        assert sidebar.list_widget.currentRow() == target_row
        assert changes == [6]
        sidebar.list_widget.setCurrentRow(sidebar.items_map.index(5))
        assert changes == [6, 5]
    finally:
        sidebar.deleteLater()
        app.processEvents()


def test_company_settings_hides_tabs_and_keeps_section_navigation(monkeypatch, tmp_path):
    from PyQt6.QtTest import QSignalSpy
    from PyQt6.QtWidgets import QLabel, QPushButton
    from src.database import Database
    from src.ui.pages.settings_widgets.company_settings_base import CompanySettingsWidget
    from src.utils.design_system import DesignTokens
    from src.utils.reference_typography import apply_reference_font
    from src.utils.theme_colors import tc
    from tools.quality.desktop_visual_acceptance import seed_visual_fixture

    app = QApplication.instance() or QApplication([])
    apply_reference_font(app)
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    saved = []
    monkeypatch.setattr(CompanySettingsWidget, "save_data", lambda self: saved.append(self.db))
    db = Database(str(tmp_path / "company_reference.db"))
    seed_visual_fixture(db)
    changes = db.conn.total_changes
    page = CompanySettingsWidget(db, None)
    try:
        ThemeManager.apply_theme(app, "Koyu Mavi", window=page, animate=False)
        assert page.tabs.count() == 5
        assert page.tabs.isHidden()
        assert page.tabs.tabText(4) == "Stok - Banka E\u015fle\u015ftirme"
        assert page.loaded_tabs == {2, 3, 4}
        assert len(page.section_frames) == 5
        assert not hasattr(page, "proforma_layout")
        assert page.stock_widget.table.rowCount() == 4
        assert page.stock_widget.table.item(0, 0).text() == "Stok Y\u00f6netimi"
        assert 132 < page.stock_widget.table.maximumHeight() <= 280
        original_prefix = page.number_widget.inp_job_prefix.text()
        original_vat = page.stock_widget.table.cellWidget(0, 2).value()
        page.number_widget.inp_job_prefix.setText("UNSAVED")
        changed_vat = original_vat + 1 if original_vat < 100 else original_vat - 1
        page.stock_widget.table.cellWidget(0, 2).setValue(changed_vat)
        cancel = next(
            button for button in page.findChildren(QPushButton)
            if button.text() == "Vazge\u00e7"
        )
        cancel.click()
        assert page.number_widget.inp_job_prefix.text() == original_prefix
        assert page.stock_widget.table.cellWidget(0, 2).value() == original_vat
        assert page.findChild(QPushButton, "company_settings_save").height() == 30
        assert page.tabs.currentIndex() == 0
        assert page.title_label.font().family() == DesignTokens.FONT_NAME
        assert not any(
            button.text() == "\u2713 Kaydet (Ctrl+S)"
            for button in page.findChildren(QPushButton)
        )
        assert any(
            label.text() == "Firma Profili"
            for label in page.findChildren(QLabel)
        )
        title = next(
            label for label in page.findChildren(QLabel)
            if label.text() == "Firma Bilgileri & Resmi Kimlik Y\u00f6netimi"
        )
        assert title.font().family() == DesignTokens.FONT_NAME
        page.resize(1280, 720)
        page.show()
        app.processEvents()
        tab_changes = QSignalSpy(page.tabs.currentChanged)
        for tab_index in range(page.tabs.count()):
            page.tabs.setCurrentIndex(tab_index)
        assert page.tabs.currentIndex() == 4
        assert len(tab_changes) == 4
        assert page.company_sections_scroll.verticalScrollBar().value() > 0
        page.tabs.setCurrentIndex(0)
        assert page.company_sections_scroll.verticalScrollBar().value() == 0
        save = page.findChild(QPushButton, "company_settings_save")
        assert save.text() == "G\u00dcNCELLE & KAYDET"
        assert tc("accent") in save.styleSheet()
        save.click()
        assert saved == [db]
        assert db.conn.total_changes == changes
        assert not page.grab().isNull()
    finally:
        page.close()
        db.close()


def test_company_dialog_loading_does_not_trigger_save(monkeypatch, tmp_path):
    from PyQt6.QtWidgets import QLabel
    from src.database import Database
    from src.ui.pages.settings_widgets.company_settings_dialog import CompanySettingsDialog

    app = QApplication.instance() or QApplication([])
    calls = []
    monkeypatch.setattr(CompanySettingsDialog, "save_data", lambda self, close_dialog=False: calls.append(close_dialog))
    monkeypatch.setattr(CompanySettingsDialog, "_migrate_setup_company_info", lambda self: None)
    db = Database(str(tmp_path / "company_dialog_load.db"))
    db.set_setting("currency_precision", "3")
    db.set_setting("online_payment_active", "0")
    dialog = CompanySettingsDialog(db, None)
    try:
        assert dialog.settings_tabs.count() == 4
        assert dialog.footer.height() == 56
        assert any(
            label.text() == "TEMEL F\u0130RMA B\u0130LG\u0130LER\u0130 & SOSYAL MEDYA"
            for label in dialog.findChildren(QLabel)
        )
        assert dialog.cmb_currency_precision.currentIndex() == 3
        assert dialog.cmb_online_payment.currentIndex() == 1
        assert calls == []
    finally:
        dialog.close()
        db.close()


def test_settings_page_is_parented_during_construction(tmp_path):
    from src.database import Database
    from src.ui.pages.settings_page import SettingsPage

    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    db = Database(str(tmp_path / "settings_page_parent.db"))
    page = SettingsPage(db, parent)
    try:
        assert page.parentWidget() is parent
        assert not page.isWindow()
    finally:
        page.deleteLater()
        parent.deleteLater()
        app.processEvents()
        db.close()
        app.processEvents()


def test_settings_icons_refresh_with_theme_without_changing_routes():
    app = QApplication.instance() or QApplication([])
    previous = ThemeManager._current_theme
    sidebar = PremiumSettingsSidebar(lambda _page: None, current_user={"role": "Admin"})
    try:
        original = sidebar.iter_items()
        item = sidebar.list_widget.item(sidebar.items_map.index(6))
        keys = []
        for theme in ("AYEC", "Koyu Mavi"):
            ThemeManager._activate_runtime_cache(theme)
            sidebar.apply_theme_styles()
            keys.append(item.icon().cacheKey())
            assert sidebar.iter_items() == original
            assert not sidebar.grab().isNull()
        assert keys[0] != keys[1]
    finally:
        ThemeManager._activate_runtime_cache(previous)
        sidebar.deleteLater()
        app.processEvents()

