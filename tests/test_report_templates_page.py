import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHeaderView

from src.ui.pages.report_templates_page import ReportTemplatesPage
from src.utils.page_config import PAGE_MAPPING, PAGE_NAMES


APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


class _Db:
    def get_fast_notes(self):
        return [
            (index, "Process Detail", f"Report sentence {index:02d}", 1, index)
            for index in range(1, 14)
        ]


def test_report_templates_page_is_registered_and_paginated():
    assert PAGE_MAPPING[147][1] == "ReportTemplatesPage"
    assert PAGE_NAMES[147] == "Rapor C\u00fcmle Kal\u0131plar\u0131"

    page = ReportTemplatesPage(_Db())
    try:
        assert page.total_count == 13
        assert page.table.rowCount() == 10
        assert page.table.verticalHeader().defaultSectionSize() == 64
        assert page.table.horizontalHeader().sectionResizeMode(1) == QHeaderView.ResizeMode.Stretch
        assert page.btn_next.isEnabled()

        page.next_page()

        assert page.current_page == 2
        assert page.table.rowCount() == 3
    finally:
        page.close()


def test_report_template_rows_have_visible_hover_feedback(tmp_path):
    from PyQt6.QtCore import QPoint
    from PyQt6.QtTest import QTest

    from src.utils.theme_manager import ThemeManager

    previous_theme = ThemeManager._current_theme
    ThemeManager.apply_theme(APP, "Koyu Mavi", animate=False)
    page = ReportTemplatesPage(_Db())
    try:
        page.resize(1600, 900)
        page.show()
        APP.processEvents()
        stylesheet = ThemeManager.get_stylesheet("Koyu Mavi")
        assert "QTableWidget::item:hover" in stylesheet
        hover_rule = stylesheet.split("QTableWidget::item:hover", 1)[1].split("}", 1)[0]
        assert "background-color:" in hover_rule
        assert "color:" in hover_rule
        QTest.mouseMove(page.table.viewport(), QPoint(200, 90))
        APP.processEvents()
        page.grab().save(str(tmp_path / "report_template_hover.png"))
    finally:
        page.close()
        if previous_theme:
            ThemeManager.apply_theme(APP, previous_theme, animate=False)


def test_report_table_uses_preview_space_and_preserves_long_template_text():
    from src.utils.reference_typography import apply_reference_font
    apply_reference_font(APP)
    message = 'Long template sentence with all retained business details. ' * 200

    class LongDb:
        def get_fast_notes(self):
            return [(1, 'Teknik Servis::Bilgisayar::Ariza', message, 1, 0)]

    page = ReportTemplatesPage(LongDb())
    try:
        page.resize(1600, 900)
        page.show()
        APP.processEvents()
        assert page.search.width() == 650
        assert page.device_filter.width() == 270
        assert page.status_filter.width() == 120
        assert not page.template_splitter.widget(1).isHidden()
        assert page.table_panel.width() < page.template_splitter.width()
        category_cell = page.table.cellWidget(0, 0)
        scope_label = category_cell.layout().itemAt(0).widget()
        assert scope_label.geometry().bottom() < category_cell.height()

        page.resize(800, 900)
        page.show()
        page.table.selectRow(0)
        APP.processEvents()
        assert page.width() == 800
        assert page.template_splitter.orientation() == Qt.Orientation.Vertical
        assert page.preview_text.text() == "\u00bb  " + message
        assert page.preview_text.isReadOnly()
        assert not page.template_splitter.widget(1).isHidden()
        assert page.search.geometry().bottom() < page.device_filter.y()
        assert page.copy_button.isEnabled()
    finally:
        page.close()


def test_report_template_text_uses_theme_palette_in_light_theme(tmp_path):
    from src.utils.theme_manager import ThemeManager

    previous_theme = ThemeManager._current_theme
    ThemeManager.apply_theme(APP, "AYEC", animate=False)
    page = ReportTemplatesPage(_Db())
    try:
        page.resize(1600, 900)
        page.show()
        APP.processEvents()
        page.grab().save(str(tmp_path / "report_templates_light.png"))
        assert page.table.rowCount() > 0
    finally:
        page.close()
        if previous_theme:
            ThemeManager.apply_theme(APP, previous_theme, animate=False)


def test_report_templates_page_filters_category_and_sentence():
    page = ReportTemplatesPage(_Db())
    try:
        page.search.setText("sentence 12")
        assert page.total_count == 1
        assert page.table.rowCount() == 1
        assert page.table.item(0, 1).text() == "Report sentence 12"
    finally:
        page.close()


def test_category_tabs_and_preview_follow_filtered_selection():
    class MixedDb:
        def get_fast_notes(self):
            return [(1, "Fault", "No display", 1, 1),
                    (2, "Repair", "Panel replaced", 1, 2)]

    page = ReportTemplatesPage(MixedDb())
    try:
        page.category_tabs.setCurrentIndex(page.category_filter.findData("Repair"))
        assert page.table.rowCount() == 1
        page.table.selectRow(0)
        assert page.preview_category.text() == "Repair"
        assert page.preview_text.text() == "\u00bb  Panel replaced"
        page.search.setText("missing")
        assert page.table.rowCount() == 0
        assert page.preview_category.text() == ""
        assert page.preview_text.text() == "\u00d6nizlemek i\u00e7in bir \u015fablon se\u00e7in."
    finally:
        page.close()


def test_status_filter_combines_with_category_and_clears_preview():
    class MixedDb:
        def get_fast_notes(self):
            return [(1, "Repair", "Active repair", 1, 1),
                    (2, "Repair", "Archived repair", 0, 2),
                    (3, "Fault", "Archived fault", 0, 3)]

    page = ReportTemplatesPage(MixedDb())
    try:
        page.category_filter.setCurrentIndex(page.category_filter.findData("Repair"))
        page.status_filter.setCurrentIndex(page.status_filter.findData("inactive"))
        assert page.table.rowCount() == 1
        assert page.table.item(0, 1).text() == "Archived repair"
        assert page.current_page == 1
        page.table.selectRow(0)
        assert page.preview_text.text() == "\u00bb  Archived repair"
        page.search.setText("Active repair")
        assert page.total_count == 0
        assert page.preview_category.text() == ""
    finally:
        page.close()


def test_device_scope_preview_copy_and_editor_keep_selected_template_identity(monkeypatch):
    class ScopedDb:
        def get_fast_notes(self):
            return [(1, 'Teknik Servis::Bilgisayar::Ariza', 'No display', 1, 0),
                    (2, 'Teknik Servis::Cep Telefonu::Aksesuar', 'SIM card', '0', 1),
                    (3, 'Teknik Servis::Cep Telefonu::Aksesuar', 'Charging cable', 1, 2)]

        def get_setting(self, name, default):
            return 'Actual Company' if name == 'company_name' else default

    editors = []

    class Editor:
        def __init__(self, db, parent, **options):
            editors.append(options)

        def exec(self):
            return 0

    monkeypatch.setattr('src.ui.pages.report_templates_page.QuickNotesEditor', Editor)
    page = ReportTemplatesPage(ScopedDb())
    old_clipboard = APP.clipboard().text()
    try:
        assert page.preview_company.text() == 'Actual Company'
        assert not page.copy_button.isEnabled()
        page.status_filter.setCurrentIndex(page.status_filter.findData('all'))
        page.device_filter.setCurrentIndex(page.device_filter.findData('Cep Telefonu'))
        assert page.table.rowCount() == 2
        page.status_filter.setCurrentIndex(page.status_filter.findData('inactive'))
        assert page.table.rowCount() == 1
        assert page.table.item(0, 2).text() == 'Pasif'
        page.table.selectRow(0)
        assert page.preview_id.text() == 'Se\u00e7ili \u015eablon #02'
        assert page.preview_status.text() == 'PASIF KALIP'
        assert page.preview_text.text() == '\u00bb  SIM card'
        page.copy_button.click()
        assert APP.clipboard().text() == 'SIM card'
        page.open_editor()
        assert editors == [{'initial_category': 'Aksesuar', 'profile_name': 'Cep Telefonu'}]
        assert page.device_filter.currentData() == 'Cep Telefonu'
        page.search.setText('missing')
        assert page.table.rowCount() == 0
        assert page.preview_id.text() == 'Se\u00e7ili \u015eablon #--'
        assert not page.copy_button.isEnabled()
        page._copy_selected_template()
        assert APP.clipboard().text() == 'SIM card'
    finally:
        APP.clipboard().setText(old_clipboard)
        page.close()
