import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton

from src.database import Database
from src.ui.pages.finance.bank_accounts_widget import (
    AccountDetailDialog, BankAccountsWidget, EditBankAccountDialog, TransferDialog,
)
from tools.quality.desktop_visual_acceptance import seed_visual_fixture
from src.ui.widgets.financial_reference_controls import ReferenceMetricValueLabel
from src.utils.design_system import DesignTokens
from src.utils.currency_helper import CurrencyHelper
from src.utils.reference_typography import apply_reference_font


def test_bank_fields_use_actual_schema_and_preserve_selection_filters_and_actions(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    apply_reference_font(app)
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    actions = []
    for method, action in (("open_add_dialog", "add"), ("import_statement", "statement"), ("import_accounts", "import"), ("export_accounts", "export"), ("_open_transfer_dialog", "transfer")):
        monkeypatch.setattr(BankAccountsWidget, method, lambda self, checked=False, event=action: actions.append(event))
    db = Database(str(tmp_path / "bank_reference.db"))
    seed_visual_fixture(db)
    original = [tuple(row) for row in db.cursor.execute("SELECT * FROM bank_accounts ORDER BY id")]
    columns = list(db._get_table_columns("bank_accounts"))
    expected = {row[columns.index("id")]: dict(zip(columns, row)) for row in original}
    page = BankAccountsWidget(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    page.resize(1280, 1024)
    page.show()
    app.processEvents()
    try:
        assert page.table.columnCount() == 7
        assert page.table.rowCount() == len(original)
        assert not page.table.isVisible()
        assert page.account_cards_scroll.isVisible()
        assert set(page.account_card_buttons) == set(expected)
        assert sum(page.fund_distribution.values()) == 1473440.2
        assert set(page.fund_distribution) == set(expected)
        for label in (page.lbl_total_balance, page.lbl_bank_balance, page.lbl_cash_balance, page.lbl_pos_balance):
            assert isinstance(label, ReferenceMetricValueLabel)
            assert label.textFormat() == Qt.TextFormat.PlainText
            assert label.toolTip() == label.text()
            original_text = label.text()
            label.setText("123,456,789,012.34 TRY")
            label.resize(160, 32)
            font = label.amount_font(label.text(), label.primary_size)
            assert font.family() == DesignTokens.MONO_FONT_NAME
            assert QFontMetrics(font).horizontalAdvance(label.text()) <= label.contentsRect().width() - 4
            label.setText(original_text)
        for account_id, button in page.account_card_buttons.items():
            amount = button.findChild(ReferenceMetricValueLabel)
            record = expected[account_id]
            assert amount.text() == CurrencyHelper.format_amount(record["current_balance"], db=db, currency_code=record["currency"])
            assert amount.toolTip() == amount.text()
            assert all(label.textFormat() == Qt.TextFormat.PlainText for label in button.findChildren(QLabel))
            button.click()
            assert page._selected_account_id() == account_id
            assert button.isChecked()
            assert page.sum_name.text() == expected[account_id]["account_holder"]
        page.btn_account_table.click()
        assert page.table.isVisible()
        assert page.account_summary.isVisible()
        assert not page.account_cards_scroll.isVisible()
        assert page.table.columnCount() == 7
        page.btn_account_table.click()
        assert not page.table.isVisible()
        assert page.lbl_bank_balance.text() == "1,180,240.00 \u20ba"
        assert page.lbl_cash_balance.text() == "48,200.00 \u20ba"
        page.btn_account_filters.click()
        assert page.account_filter_panel.isVisible()
        assert page.btn_bulk_toggle.isVisible()
        assert page.btn_bulk_delete.isVisible()
        assert page.search.isVisible()
        page.btn_account_filters.click()
        for row in range(page.table.rowCount()):
            record = expected[int(page.table.item(row, 0).text())]
            assert page.table.item(row, 1).text() == record["bank_name"]
            assert page.table.item(row, 2).text() == (record.get("branch_name") or record.get("branch_code") or "")
            assert page.table.item(row, 3).text() == record["account_holder"]
            assert page.table.item(row, 4).text() == record["account_number"]
            assert page.table.item(row, 5).text() == record["iban"]
            for column in (0, 4, 5, 6):
                item = page.table.item(row, column)
                assert item.font().family() == DesignTokens.MONO_FONT_NAME
                assert item.toolTip() == item.text()
            page.table.selectRow(row)
            app.processEvents()
            assert page.sum_name.text() == record["account_holder"]
            assert page.sum_iban.text() == record["iban"]
            assert page._selected_account_id() == record["id"]
            assert page._selected_source_row()[0] == record["id"]
        record = next(item for item in expected.values() if item["iban"])
        page.search.setText(record["iban"])
        assert page.table.rowCount() == 1
        assert page._selected_account_id() == record["id"]
        page.search.setText("")
        assert page.table.rowCount() == len(original)
        for button in (page.btn_add, page.btn_statement, page.btn_transfer, page.btn_import, page.btn_export):
            button.click()
        assert actions == ["add", "statement", "transfer", "import", "export"]
        page.btn_refresh.click()
        assert page.table.rowCount() == len(original)
        assert [tuple(row) for row in db.cursor.execute("SELECT * FROM bank_accounts ORDER BY id")] == original
        saved_columns = page._bank_cols
        page._bank_cols = []
        assert page._account_display_fields((91, "Legacy bank", "Legacy branch", "Legacy name", "Legacy number", "Legacy IBAN")) == ("Legacy bank", "Legacy branch", "Legacy name", "Legacy number", "Legacy IBAN")
        page._bank_cols = saved_columns
        assert not page.grab().isNull()
    finally:
        page.close()
        db.close()


def test_account_dialogs_map_raw_schema_without_swapping_holder_and_iban(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    db = Database(str(tmp_path / "bank_dialogs.db"))
    seed_visual_fixture(db)
    rows = db.get_bank_accounts()
    columns = list(db._get_table_columns("bank_accounts"))
    row = next(row for row in rows if row[columns.index("iban")])
    record = dict(zip(columns, row))
    original = [tuple(item) for item in db.cursor.execute("SELECT * FROM bank_accounts ORDER BY id")]
    saved = []
    monkeypatch.setattr(db, "update_bank_account", lambda *args: saved.append(args) or True)
    monkeypatch.setattr(db, "set_bank_account_active", lambda *args: True)
    monkeypatch.setattr("src.ui.pages.finance.bank_accounts_widget.SystemConfig.is_feature_active", lambda *args: False)
    edit = EditBankAccountDialog(db, row)
    detail = AccountDetailDialog(db, row)
    transfer = TransferDialog(db, row, rows)
    try:
        assert edit.inp_bank.text() == record["bank_name"]
        assert edit.inp_name.text() == record["account_holder"]
        assert edit.inp_iban.text() == record["iban"]
        assert edit.inp_no.text() == record["account_number"]
        assert edit.inp_branch.text() == (record.get("branch_name") or record.get("branch_code") or "")
        texts = [label.text() for label in detail.findChildren(QLabel)]
        assert record["account_holder"] in texts
        assert record["iban"] in texts
        for index, account_id in enumerate(transfer._target_ids):
            target = dict(zip(columns, next(item for item in rows if item[0] == account_id)))
            assert target["account_holder"] in transfer.cmb_target.itemText(index)
            assert target["iban"] in transfer.cmb_target.itemText(index)
        edit._save()
        assert saved[0][:6] == (record["id"], record["bank_name"], record.get("branch_name", record.get("branch_code")), record["account_holder"], record["account_number"], record["iban"])
        assert [tuple(item) for item in db.cursor.execute("SELECT * FROM bank_accounts ORDER BY id")] == original
        app.processEvents()
    finally:
        for dialog in (edit, detail, transfer):
            dialog.close()
        db.close()


def test_bank_ledger_filters_use_actual_receipts_and_keep_original_fields(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    db = Database(str(tmp_path / "bank_ledger.db"))
    seed_visual_fixture(db)
    page = BankAccountsWidget(db)
    try:
        assert page.history_table.columnCount() == 8
        assert page.history_table.rowCount() == 5
        assert not page.history_table.alternatingRowColors()
        for row in range(page.history_table.rowCount()):
            assert page.history_table.item(row, 0).font().family() == DesignTokens.MONO_FONT_NAME
            amount = page.history_table.item(row, 3)
            assert amount.font().family() == DesignTokens.MONO_FONT_NAME
            assert amount.font().bold()
            assert amount.toolTip() == amount.text()
        ids = {int(page.history_table.item(row, 6).text()) for row in range(5)}
        expected = {row[0] for row in db.cursor.execute("SELECT id FROM accounting WHERE bank_account_id IS NOT NULL AND COALESCE(is_deleted,0)=0")}
        assert ids == expected
        details = []
        monkeypatch.setattr(page, "_show_account_detail", lambda: details.append(page._selected_account_id()))
        account_id = int(page.history_table.item(0, 5).text())
        actions = page.history_table.cellWidget(0, 7).findChildren(QPushButton)
        assert [button.glyph for button in actions] == ["document", "transfer"]
        assert [button.accessibleName() for button in actions] == ["ledger_account_detail", "ledger_account_movements"]
        actions[0].click()
        assert details == [account_id]
        page.history_table.cellWidget(0, 7).findChildren(QPushButton)[1].click()
        assert page.history_selected_account.isChecked()
        assert all(int(page.history_table.item(row, 5).text()) == account_id for row in range(page.history_table.rowCount()))
        page.history_selected_account.setChecked(False)
        for kind, count in (("income", 3), ("expense", 2), ("cash", 2), ("pos", 1), ("all", 5)):
            page.history_filter_buttons[kind].click()
            assert page.history_table.rowCount() == count
        page.history_search.setText("POS gun sonu")
        assert page.history_table.rowCount() == 1
        page.history_search.clear()
        page.history_selected_account.setChecked(True)
        assert page.history_table.rowCount() == 1
        cash = next(account_id for account_id, button in page.account_card_buttons.items() if "Kasasi" in button.accessibleName())
        page.account_card_buttons[cash].click()
        assert page.history_table.rowCount() == 2
        page.history_selected_account.setChecked(False)
        db.cursor.execute("INSERT INTO accounting(type,category,amount,try_equivalent,currency,description,date,bank_account_id) VALUES ('Gelir','FX',5,220,'USD','Converted receipt','2026-10-01 10:00',?)", (cash,))
        receipt_id = db.cursor.lastrowid
        db.cursor.execute("INSERT INTO accounting(type,category,amount,currency,description,date,bank_account_id,is_deleted) VALUES ('Gelir','FX',5,'USD','Deleted receipt','2026-10-01',?,1)", (cash,))
        db.conn.commit()
        page.load_data()
        assert page.history_table.rowCount() == 6
        row = next(row for row in range(6) if int(page.history_table.item(row, 6).text()) == receipt_id)
        assert page.history_table.item(row, 3).text() == "+220.00 \u20ba"
        assert page.history_table.item(row, 4).text() == "Converted receipt"
        assert page.history_table.item(row, 1).text() == "Gelir"
        assert page.history_table.item(row, 2).text() == "FX"
        assert page.history_table.item(row, 5).text() == str(cash)
        assert "Converted receipt" in page.history_table.cellWidget(row, 4).text()
        detail = AccountDetailDialog(db, page._selected_source_row())
        detail._load_history(cash)
        receipts = {detail.history_table.item(index, 4).text(): detail.history_table.item(index, 3).text() for index in range(detail.history_table.rowCount())}
        assert receipts["Converted receipt"] == "220.00 \u20ba"
        assert "Deleted receipt" not in receipts
        detail.close()
        app.processEvents()
    finally:
        page.close()
        db.close()


def test_edit_account_save_preserves_real_field_mapping_and_other_accounts(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    monkeypatch.setattr("src.ui.pages.finance.bank_accounts_widget.SystemConfig.is_feature_active", lambda *args: False)
    db = Database(str(tmp_path / "bank_save.db"))
    seed_visual_fixture(db)
    columns = list(db._get_table_columns("bank_accounts"))
    row = db.get_bank_accounts()[0]
    original = {item[0]: tuple(item) for item in db.cursor.execute("SELECT * FROM bank_accounts")}
    edit = EditBankAccountDialog(db, row)
    try:
        edit.inp_name.setText("Updated account owner")
        edit._save()
        actual = {item[0]: tuple(item) for item in db.cursor.execute("SELECT * FROM bank_accounts")}
        assert dict(zip(columns, actual[row[0]]))["account_holder"] == "Updated account owner"
        for index, name in enumerate(columns):
            if name != "account_holder":
                assert actual[row[0]][index] == original[row[0]][index]
        assert {key: value for key, value in actual.items() if key != row[0]} == {key: value for key, value in original.items() if key != row[0]}
        app.processEvents()
    finally:
        edit.close()
        db.close()


def test_bank_reference_keeps_credit_navigation_and_more_actions(monkeypatch, tmp_path):
    from src.ui.pages.finance.bank_page import BankPage

    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    calls = []
    monkeypatch.setattr(
        BankAccountsWidget, "load_data", lambda self: calls.append("refresh")
    )
    db = Database(str(tmp_path / "bank_navigation.db"))
    seed_visual_fixture(db)
    db.cursor.executemany(
        "INSERT INTO exchange_rates (currency, buying_rate, selling_rate) VALUES (?, ?, ?)",
        [("USD", 35, 36), ("EUR", 38, 39)],
    )
    db.conn.commit()
    page = BankPage(db, None)
    try:
        assert page.tabs.tabBar().isHidden()
        page.accounts_tab.btn_loans.click()
        assert page.tabs.currentIndex() == 1
        page.loans_tab.btn_accounts.click()
        assert page.tabs.currentIndex() == 0
        more = next(
            button for button in page.accounts_tab.findChildren(QPushButton)
            if button.text() == "Diger"
        )
        more.menu().actions()[0].trigger()
        assert calls.count("refresh") >= 2
    finally:
        page.close()
        db.close()
        app.processEvents()
