import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QPushButton, QLabel, QDialog
from PyQt6.QtTest import QTest

from src.database import Database
from src.ui.pages.service_board_page import ServiceBoardPage
from src.ui.widgets.kanban_board import KanbanCard, get_kanban_colors
from src.utils.theme_manager import ThemeManager
from src.utils.theme_colors import tc
from src.utils.status_utils import normalize_device_status
from src.ui.widgets.financial_reference_controls import FinancialMetricGlyph
from src.utils.page_ids import PageIds
from tools.quality.desktop_visual_acceptance import ROOT, seed_visual_fixture


def test_board_reference_header_preserves_filters_and_action_routes(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    old_font = app.font()
    font_id = QFontDatabase.addApplicationFont(str(ROOT / ".venv_active" / "Lib" / "site-packages" / "imgaug" / "DejaVuSans.ttf"))
    assert font_id >= 0
    app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0], 9))
    calls = []
    monkeypatch.setattr(ServiceBoardPage, "refresh_data", lambda self: calls.append("refresh"))
    monkeypatch.setattr(ServiceBoardPage, "open_new_service_dialog", lambda self: calls.append("new"))
    monkeypatch.setattr(ServiceBoardPage, "open_bulk_action_dialog", lambda self: calls.append("bulk"))
    db = Database(str(tmp_path / "board_header.db"))
    page = ServiceBoardPage(db, SimpleNamespace(switch_page=lambda index: calls.append(index)))
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        page.resize(1268, 1220)
        page.show()
        app.processEvents()
        calls.clear()
        changes = db.conn.total_changes
        assert [page.board_filter.itemData(i) for i in range(page.board_filter.count())] == ["all", "urgent", "today", "parts", "test"]
        assert page.board_filter.property("referenceChevron")
        assert page.board_filter.height() == 30
        assert page.board_search.height() == 30
        assert page.kpi_bar.height() == 100
        assert len(page.kpi_bar.findChildren(FinancialMetricGlyph)) == 4
        controls = [page.board_search, page.board_filter, page.btn_urgent_filter, page.btn_today_filter, page.btn_new_service]
        for button in page.header_widget.findChildren(QPushButton):
            controls.append(button)
        for control in controls:
            assert page.header_widget.rect().contains(QRect(control.mapTo(page.header_widget, QPoint()), control.size()))
        assert page.btn_new_service.mapTo(page.header_widget, QPoint()).y() > page.board_search.mapTo(page.header_widget, QPoint()).y()
        page.board_search.setText("DEMO")
        assert calls[-1] == "refresh"
        QTest.mouseClick(page.btn_urgent_filter, Qt.MouseButton.LeftButton)
        assert page.board_filter.currentData() == "urgent"
        QTest.mouseClick(page.btn_today_filter, Qt.MouseButton.LeftButton)
        assert page.board_filter.currentData() == "today"
        QTest.mouseClick(page.btn_new_service, Qt.MouseButton.LeftButton)
        assert calls[-1] == "new"
        routes = {"Panoyu Yenile": "refresh", "Toplu \u0130\u015flem": "bulk", "T\u00fcm \u0130\u015flemler / Ar\u015fiv": PageIds.JOB_TRACKING}
        for tooltip, expected in routes.items():
            button = next(b for b in page.header_widget.findChildren(QPushButton) if b.toolTip() == tooltip)
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            assert calls[-1] == expected
        assert db.conn.total_changes == changes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()
        app.setFont(old_font)


def test_real_board_cards_fit_reference_columns_and_keep_original_signals(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    old_font = app.font()
    font_id = QFontDatabase.addApplicationFont(str(ROOT / ".venv_active" / "Lib" / "site-packages" / "imgaug" / "DejaVuSans.ttf"))
    assert font_id >= 0
    app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0], 9))
    calls = []
    monkeypatch.setattr(ServiceBoardPage, "open_device_detail", lambda self, tracking: calls.append(("detail", tracking)))
    monkeypatch.setattr(ServiceBoardPage, "on_board_action", lambda self, action, tracking: calls.append((action, tracking)))
    db = Database(str(tmp_path / "board_cards.db"))
    seed_visual_fixture(db)
    db.conn.execute("UPDATE devices SET urgency='Acil' WHERE tracking_no='DEMO-SRV-0008'")
    db.conn.commit()
    page = ServiceBoardPage(db, None)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        changes = db.conn.total_changes
        page.resize(1268, 1220)
        page.show()
        page.refresh_data()
        app.processEvents()
        QTest.qWait(50)
        app.processEvents()
        assert page.btn_urgent_filter.text() == "Acil (1)"
        for column in page.board.columns.values():
            assert column.header.height() == 48
            assert column.lbl_count.size().width() == 26
            assert column.lbl_count.size().height() == 24
            assert column.lbl_icon.text() == ""
            assert column.lbl_icon.width() == 10
            assert column.lbl_icon.height() == 10
        for value in page._kpi_values.values():
            assert value.parentWidget().rect().contains(QRect(value.mapTo(value.parentWidget(), QPoint()), value.size()))
            assert value.fontMetrics().horizontalAdvance(value.text()) <= value.width()
        cards = [card for card in page.board.findChildren(KanbanCard) if card.isVisible()]
        assert len(cards) == 8
        for card in cards:
            stage = normalize_device_status(card.status)
            if stage == "Teslime Hazir":
                stage = "Teslim Edildi"
            assert card._accent == get_kanban_colors()[stage]
            viewport = card.parentWidget().parentWidget()
            assert card.width() <= viewport.width()
            for name in ("KanbanTrackingBadge", "KanbanTitle", "KanbanCustomer", "KanbanStatusPill", "KanbanTrack", "KanbanDate", "KanbanAvatar"):
                label = card.findChild(QLabel, name)
                if label is not None:
                    assert card.rect().contains(QRect(label.mapTo(card, QPoint()), label.size())), name
            assert card.findChild(QLabel, "KanbanTrackingBadge").toolTip() == card.tracking_no
        first = cards[0]
        first.clicked.emit(first.tracking_no)
        first.action_triggered.emit("info", first.tracking_no)
        assert calls == [("detail", first.tracking_no), ("info", first.tracking_no)]
        delivery_cards = [card for card in cards if normalize_device_status(card.status) == "Teslime Hazir"]
        assert len(delivery_cards) == 1
        delivery_card = delivery_cards[0]
        button = delivery_card.findChild(QPushButton, "KanbanDeliverAction")
        assert button is not None
        assert delivery_card.rect().contains(QRect(button.mapTo(delivery_card, QPoint()), button.size()))
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert calls[-1] == ("update_status:Teslim Edildi", delivery_card.tracking_no)
        for card in cards:
            if card not in delivery_cards:
                assert card.findChild(QPushButton, "KanbanDeliverAction") is None
        page.btn_urgent_filter.click()
        assert sum(len(column.all_devices) for column in page.board.columns.values()) == 1
        assert next(row for column in page.board.columns.values() for row in column.all_devices)["tracking_no"] == "DEMO-SRV-0008"
        page.board_filter.setCurrentIndex(0)
        page.board_search.setText("DEMO-SRV-0013")
        assert sum(len(column.all_devices) for column in page.board.columns.values()) == 1
        assert page.btn_urgent_filter.text() == "Acil (1)"
        assert db.conn.total_changes == changes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()
        app.setFont(old_font)


def test_kanban_stage_colors_are_managed_tokens_in_every_theme(monkeypatch):
    mapping = {"Bekliyor": "finance_action_expense", "Tamirde": "finance_action_collection", "Par\u00e7a Bekliyor": "finance_secondary", "Test S\u00fcrecinde": "finance_primary", "Teslim Edildi": "finance_secondary", "\u0130ptal": "finance_tertiary"}
    for theme in ThemeManager.DISPLAY_THEMES:
        monkeypatch.setattr(ThemeManager, "_current_theme", theme)
        colors = get_kanban_colors()
        assert colors == {key: tc(token) for key, token in mapping.items()}
        assert all(colors.values())


def test_reference_delivery_action_uses_existing_payment_handler():
    calls = []
    state = SimpleNamespace(_handle_delivery_status_change=lambda tracking: calls.append(tracking))
    ServiceBoardPage.on_board_action(state, "update_status:Teslim Edildi", "READY-1")
    assert calls == ["READY-1"]


def test_reference_delivery_cancel_keeps_existing_status_and_payment_unchanged(monkeypatch):
    calls = []
    context = {"tracking_no": "READY-1"}
    db = SimpleNamespace(update_status=lambda *args: calls.append(("status", args)))
    state = SimpleNamespace(db=db, main_window=None, _build_delivery_context=lambda tracking: context)

    class RejectedPaymentDialog:
        def __init__(self, parent, supplied_context, supplied_db):
            assert parent is state
            assert supplied_context is context
            assert supplied_db is db

        def exec(self):
            calls.append("cancel")
            return QDialog.DialogCode.Rejected

        def get_data(self):
            raise AssertionError("A rejected delivery must not access payment data")

    monkeypatch.setattr("src.ui.pages.service_board_page.DeliveryPaymentDialog", RejectedPaymentDialog)
    ServiceBoardPage._handle_delivery_status_change(state, "READY-1")
    assert calls == ["cancel"]
