import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QLabel
from PyQt6.QtTest import QTest

from src.database import Database
from src.ui.pages.offer_pages import OffersPage, _money
from src.ui.widgets.financial_reference_controls import FinancialMetricGlyph
from src.utils.theme_manager import ThemeManager
from tools.quality.desktop_visual_acceptance import ROOT, seed_visual_fixture


def test_offer_canvas_keeps_all_columns_actions_metrics_and_pagination(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    old_font = app.font()
    old_theme = ThemeManager._current_theme
    font_id = QFontDatabase.addApplicationFont(str(ROOT / ".venv_active" / "Lib" / "site-packages" / "imgaug" / "DejaVuSans.ttf"))
    assert font_id >= 0
    app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0], 9))
    calls = []
    monkeypatch.setattr(OffersPage, "export_csv", lambda self: calls.append("export"))
    monkeypatch.setattr(OffersPage, "_open_offer", lambda self, offer_id: calls.append(("open", offer_id)))
    monkeypatch.setattr(OffersPage, "_edit_offer", lambda self, offer_id: calls.append(("edit", offer_id)))
    db = Database(str(tmp_path / "offers_canvas.db"))
    seed_visual_fixture(db)
    page = OffersPage(db, SimpleNamespace(on_menu_click=lambda page_id: calls.append(page_id)))
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        changes = db.conn.total_changes
        ThemeManager.apply_theme(app, "Koyu Mavi", window=page, animate=False)
        ThemeManager.refresh_widget_tree(page)
        page.resize(1088, 988)
        page.show()
        QTest.qWait(50)
        app.processEvents()
        page.table.clearSelection()
        page.table.setCurrentCell(-1, -1)
        page._on_offer_selection_changed()
        app.processEvents()
        assert page.preview_fields["customer"].text() == "-"
        assert not page.btn_add_to_basket.isEnabled()
        assert abs(page.btn_add_to_basket.width() - page.btn_bulk_select.width()) <= 1
        assert page.btn_add_to_basket.y() == page.btn_bulk_select.y()
        assert len(page.reference_header_actions) == 4
        for button in page.reference_header_actions:
            assert button.height() == 28
            assert page.header_frame.rect().contains(QRect(button.mapTo(page.header_frame, QPoint()), button.size()))
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert calls == [150, "export", 314, 150]
        assert len(page.findChildren(FinancialMetricGlyph)) == 5
        assert all(card.height() == 90 for card in page.cards)
        assert page.cards[4].findChild(QLabel, "count").text() == _money(page.store.offer_summary()[4], "TRY")
        assert page.table.columnCount() == 10
        assert page.table.rowCount() == 6
        assert page.table.verticalScrollBar().maximum() == 0
        for column in range(10):
            assert page.table.columnWidth(column) >= 44
            assert not page.table.isColumnHidden(column)
        for row in range(6):
            for column in range(8):
                item = page.table.item(row, column)
                assert page.table.viewport().rect().contains(page.table.visualItemRect(item))
                assert item.toolTip().replace("\n", "") == item.text().replace("\n", "")
            offer_id = page.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            for column, action in ((8, "open"), (9, "edit")):
                button = page.table.cellWidget(row, column)
                assert page.table.viewport().rect().contains(QRect(button.mapTo(page.table.viewport(), QPoint()), button.size()))
                QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                assert calls[-1] == (action, offer_id)
        assert page.page_info.mapTo(page, QPoint()).y() >= page.table.mapTo(page, QPoint()).y() + page.table.height()
        assert page.page_info.mapTo(page, QPoint()).y() < page.table.mapTo(page, QPoint()).y() + page.table.height() + 40
        page.btn_next.click()
        assert page.table.rowCount() == 4
        assert page.table.height() == 34 + 4 * 46
        assert page.page_number.text() == "2 / 2"
        page.btn_previous.click()
        assert page.table.rowCount() == 6
        assert page.page_number.text() == "1 / 2"
        assert db.conn.total_changes == changes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()
        ThemeManager.apply_theme(app, old_theme, animate=False)
        app.setFont(old_font)
