import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QApplication, QPushButton

from src.database import Database
from src.ui.pages.personnel_page import PersonnelPage
from src.utils.design_system import DesignTokens
from src.utils.reference_typography import apply_reference_font
from src.ui.widgets.financial_reference_controls import ReferenceMetricValueLabel
from tools.quality.desktop_visual_acceptance import seed_visual_fixture


def test_personnel_reference_keeps_fields_selection_filters_payroll_and_live_metrics(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    apply_reference_font(app)
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    db = Database(str(tmp_path / "personnel_reference.db"))
    seed_visual_fixture(db)
    page = PersonnelPage(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    page.resize(1100, 988)
    page.show()
    app.processEvents()
    try:
        baseline = [tuple(row) for row in db.conn.execute("SELECT * FROM personnel ORDER BY id")]
        assert page.table.columnCount() == 14
        assert page.table.rowCount() == 6
        assert not page.table.alternatingRowColors()
        assert page.personnel_role_filter.property("referenceChevron")
        assert page.personnel_role_filter.height() == 32
        assert page.table.item(0, 9).text() == "48,500.00 TL"
        assert page.table.item(0, 10).text() == "14,250.00 TL"
        assert [label.text() for label in page.personnel_metric_values] == ["6 Personel", "268,000.00 TL", "35,050.00 TL", "-"]
        for row in range(6):
            for column in (0, 4, 7, 9, 10):
                item = page.table.item(row, column)
                assert item.font().family() == DesignTokens.MONO_FONT_NAME
                assert item.toolTip() == item.text()
                if column in (9, 10):
                    assert page.table.columnWidth(column) >= QFontMetrics(item.font()).horizontalAdvance(item.text()) + 8
            actions = page.table.cellWidget(row, 13).findChildren(QPushButton)
            assert [button.glyph for button in actions] == ["document", "bookmark"]
            assert [button.accessibleName() for button in actions] == ["personnel_payroll", "personnel_detail"]
            page.table.selectRow(row)
            assert page.personnel_detail_name.text() == page.table.item(row, 1).text()
            assert page.table.item(row, 7).text() in page.table.cellWidget(row, 1).text()
            assert page.table.item(row, 3).text() in page.table.cellWidget(row, 2).text()
            assert page.personnel_detail_contact.text() == page.table.item(row, 4).text() + " | " + page.table.item(row, 5).text()
        page.personnel_role_filter.setCurrentText("Muhendis")
        assert [page.table.item(row, 1).text() for row in range(6) if not page.table.isRowHidden(row)] == ["Eren Uysal"]
        page.personnel_role_filter.setCurrentIndex(0)
        page.personnel_search.setText("TK-084")
        assert sum(not page.table.isRowHidden(row) for row in range(6)) == 1
        assert page.personnel_detail_name.text() == "Selim Celik"
        page.personnel_search.setText("No matching employee")
        assert page.personnel_detail_name.text() == "Personel secin"
        assert page.personnel_detail_contact.text() == "-"
        page.personnel_search.clear()
        assert len(page.personnel_leaderboard_buttons) == 3
        for button in page.personnel_leaderboard_buttons.values():
            assert button.text() == button.name_label.text() + "    " + button.amount_label.text()
            assert button.name_label.font().family() == DesignTokens.FONT_NAME
            assert button.name_label.textFormat() == Qt.TextFormat.PlainText
            assert button.amount_label.textFormat() == Qt.TextFormat.PlainText
            assert button.amount_label.toolTip() == button.amount_label.text()
            assert button.name_label.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            assert button.amount_label.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        for label in page.personnel_metric_values[1:3]:
            assert isinstance(label, ReferenceMetricValueLabel)
            assert label.textFormat() == Qt.TextFormat.PlainText
            assert label.toolTip() == label.text()
        selected_id = list(page.personnel_leaderboard_buttons)[1]
        page.personnel_search.setText("TK-084")
        page.personnel_leaderboard_buttons[selected_id].click()
        assert int(page.table.item(page.table.currentRow(), 0).text()) == selected_id
        assert page.personnel_search.text() == ""
        page.personnel_detail_payroll_button.click()
        assert page.cmb_personnel.currentData() == selected_id
        page.tabs.setCurrentWidget(page.tab_personnel)
        page.btn_personnel_fields.click()
        assert all(not page.table.isColumnHidden(column) for column in range(14))
        page.btn_personnel_fields.click()
        assert page.table.isColumnHidden(0)
        assert page.table.isColumnHidden(4)
        personnel_id = int(page.table.item(0, 0).text())
        page.table.cellWidget(0, 13).findChildren(QPushButton)[0].click()
        assert page.tabs.currentWidget() is page.tab_payroll
        assert page.cmb_personnel.currentData() == personnel_id
        page.tabs.setCurrentWidget(page.tab_personnel)
        page.personnel_detail_payroll_button.click()
        assert page.tabs.currentWidget() is page.tab_payroll
        assert [tuple(row) for row in db.conn.execute("SELECT * FROM personnel ORDER BY id")] == baseline
        db.conn.execute("UPDATE personnel SET salary=50000,commission=15000 WHERE id=?", (personnel_id,))
        db.conn.commit()
        page.refresh_personnel_list()
        assert page.personnel_metric_values[1].text() == "269,500.00 TL"
        assert page.personnel_metric_values[2].text() == "35,800.00 TL"
        assert not page.grab().isNull()
    finally:
        page.close()
        db.close()
