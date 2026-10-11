import os
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.database import Database
from src.ui.pages.accounting_page import AccountingPage
from src.ui.widgets.financial_flow_sparkline import FinancialFlowSparkline
from src.utils.currency_helper import CurrencyHelper
from tools.quality.desktop_visual_acceptance import seed_visual_fixture


def test_reference_metrics_follow_finance_data_and_keep_filter_callbacks(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    monkeypatch.setattr(AccountingPage, "refresh_data", lambda self: None)
    db = Database(str(tmp_path / "accounting_metrics.db"))
    seed_visual_fixture(db)
    page = AccountingPage(db, None)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    try:
        original = [tuple(row) for row in db.cursor.execute("SELECT * FROM accounting ORDER BY id")]
        assert set(page.reference_metric_values) == {"gross_revenue", "expenses", "pocket_net", "hot_cash", "pending"}
        assert all(label.text() == "-" for label in page.reference_metric_values.values())
        summary = page.finance_manager.get_financial_summary("fiscal")
        page._update_summary_cards(summary)
        assert "48,200.00" in page.reference_side_values["cash"].text()
        assert "1,425,240.20" in page.reference_side_values["cash"].text()
        assert "73,205.10" not in page.reference_side_values["vat"].text()
        assert "verisi yok" in page.reference_side_values["vat"].text()
        db.conn.execute("INSERT INTO exchange_rates(currency,buying_rate,selling_rate,effective_date,created_at) VALUES ('EUR',66.1,66.1234,'2026-10-01','2026-10-01 10:00:00')")
        db.conn.commit()
        page._update_reference_side_panels()
        assert "66.1234" in page.reference_side_values["rates"].text()
        for key, label in page.reference_metric_values.items():
            assert label.text() == CurrencyHelper.format_try_for_display(summary.get(key, 0), db=db, include_try_reference=False)
        ledger = page.finance_manager.get_unified_ledger(100)
        page.on_data_loaded(ledger, summary, False)
        assert page.reference_record_count.text() == f"{len(ledger)} Kay\u0131t Y\u00fckl\u00fc"
        assert len(page.reference_flow_chart.values) == 14
        assert page.reference_flow_chart.values[-1] == 40570.0
        assert "439.9K" not in page.reference_flow_volume.text()
        assert "2026-09-29" in page.reference_flow_chart.toolTip()
        group = page.table.item(0, 0).data(Qt.ItemDataRole.UserRole)
        assert group["kind"] == "date_group"
        assert group["display_date"] in page._expanded_ledger_dates
        assert page.table.columnSpan(0, 0) == 8
        assert page.table.rowHeight(0) == 30
        assert page.table.item(1, 0).data(Qt.ItemDataRole.UserRole).get("kind") != "date_group"
        assert page.table.columnSpan(1, 0) == 1
        assert page.table.rowHeight(1) >= 55
        for row_index in range(1, page.table.rowCount()):
            entry = page.table.item(row_index, 0).data(Qt.ItemDataRole.UserRole)
            if entry.get("kind") == "date_group":
                continue
            if entry.get("type_label") == "Gider":
                expected = CurrencyHelper.format_try_for_display(-abs(float(entry["amount_try"])), db=db, include_try_reference=False)
                assert page.table.item(row_index, 5).text() == expected
                assert float(entry["amount_try"]) > 0
            if entry.get("balance_value") is None:
                from src.utils.theme_colors import qc
                assert page.table.item(row_index, 7).foreground().color() == qc("finance_text_muted")
        page.on_table_double_click(0, 0)
        assert group["display_date"] not in page._expanded_ledger_dates
        assert all(page.table.item(row, 0).data(Qt.ItemDataRole.UserRole).get("kind") == "date_group" for row in range(page.table.rowCount()))
        updated = {"gross_revenue": 101.25, "net_revenue": 80, "expenses": 12.50, "pocket_net": 88.75, "hot_cash": 33.50, "pending": 17.75}
        page._update_summary_cards(updated)
        for key, label in page.reference_metric_values.items():
            assert label.text() == CurrencyHelper.format_try_for_display(updated[key], db=db, include_try_reference=False)
        filters = []
        monkeypatch.setattr(page, "apply_filter", filters.append)
        for card in page.card_widgets:
            card.clicked.emit()
        assert filters == ["INCOME", "EXPENSE", "ALL", "ALL", "ALL"]
        assert [tuple(row) for row in db.cursor.execute("SELECT * FROM accounting ORDER BY id")] == original
        QTest.qWait(150)
        app.processEvents()
    finally:
        page.close()
        db.close()


def test_native_flow_chart_handles_empty_negative_and_invalid_values():
    app = QApplication.instance() or QApplication([])
    chart = FinancialFlowSparkline()
    chart.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    chart.resize(240, 32)
    chart.show()
    try:
        for values in ([], [0], [-12.5, 0, 14.25]):
            chart.set_values(values)
            app.processEvents()
            assert not chart.grab().isNull()
        for invalid in (float("nan"), float("inf")):
            with pytest.raises(ValueError):
                chart.set_values([invalid])
            assert chart.values == [-12.5, 0, 14.25]
    finally:
        chart.close()


def test_reference_quick_actions_and_collapsible_panel_keep_existing_slots(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    monkeypatch.setattr(AccountingPage, "refresh_data", lambda self: None)
    actions = []
    for method, action in (("export_to_excel", "excel"), ("export_to_pdf", "pdf"), ("print_ledger", "print"), ("open_collection_dialog", "collection"), ("open_income_dialog", "income"), ("open_expense_dialog", "expense"), ("open_transfer_dialog", "transfer"), ("open_tax_dialog", "tax")):
        monkeypatch.setattr(AccountingPage, method, lambda self, checked=False, key=action: actions.append(key))
    db = Database(str(tmp_path / "accounting_actions.db"))
    seed_visual_fixture(db)
    page = AccountingPage(db, None)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    page.resize(1088, 988)
    page.show()
    app.processEvents()
    try:
        for button in page.quick_action_buttons:
            button.click()
        assert actions == ["excel", "pdf", "print", "collection", "income", "expense", "transfer", "tax"]
        page.right_panel.removeEventFilter(page)
        page.btn_pin.click()
        assert not page.btn_pin.isChecked(), (page.btn_pin.isEnabled(), page.btn_pin.isVisible(), page.btn_pin.isCheckable())
        page.anim.setCurrentTime(page.anim.duration())
        page.anim_max.setCurrentTime(page.anim_max.duration())
        QTest.qWait(250)
        assert page.right_panel.minimumWidth() == page.right_panel.maximumWidth() == 35
        assert page.collapsed_handle.isVisible()
        assert all(label.parentWidget().isHidden() for label in page.reference_side_values.values())
        page.btn_pin_collapsed.click()
        page.anim.setCurrentTime(page.anim.duration())
        page.anim_max.setCurrentTime(page.anim_max.duration())
        QTest.qWait(250)
        assert page.right_panel.minimumWidth() == page.right_panel.maximumWidth() == 262
        assert not page.collapsed_handle.isVisible()
        assert all(label.parentWidget().isVisible() for label in page.reference_side_values.values())
        assert not page.grab().isNull()
    finally:
        page.close()
        db.close()
