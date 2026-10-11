import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.database import Database
from src.ui.pages.accounting_page import AccountingPage
from src.ui.pages._accounting_data_mixin import LedgerWorker
from src.ui.pages._accounting_func_mixin import AccountingFuncMixin
from src.utils.finance_manager import FinanceManager
import src.utils.finance_manager as finance_module
from tests.test_financial_reference_periods import FixedDateTime


def test_search_filters_both_sources_before_limit_and_preserves_literal_query(monkeypatch, tmp_path):
    monkeypatch.setattr(finance_module, "datetime", FixedDateTime)
    path = tmp_path / "search.db"
    db = Database(str(path))
    try:
        db.conn.execute("INSERT INTO customers(name) VALUES (?)", ("\u0130SMA\u0130L I\u015eIK",))
        customer = db.conn.execute("SELECT id FROM customers").fetchone()[0]
        for number in range(120):
            timestamp = "2026-10-01" if number else "2026-09-30"
            description = "Needle literal %_'" if number < 4 else "Unrelated"
            db.conn.execute("INSERT INTO accounting(date,created_at,description,amount,type,category,currency) VALUES (?,?,?,10,'Gelir','Fixture','TRY')", (timestamp, timestamp, description))
            db.conn.execute("INSERT INTO currency_transactions(customer_id,transaction_type,amount,currency,exchange_rate,try_equivalent,created_at,description,tracking_no) VALUES (?,'CREDIT',20,'TRY',1,20,?,?,?)", (customer, timestamp, description, "REF-" + str(number)))
        db.conn.commit()
        manager = FinanceManager(db)
        entries = manager.get_unified_ledger(100, search="needle")
        assert len(entries) == 8
        assert {row["source"] for row in entries} == {"accounting", "currency"}
        paged = [row for offset in range(0, 8, 2) for row in manager.get_unified_ledger(2, offset=offset, search="needle")]
        assert [(row["source"], row["id"]) for row in paged] == [(row["source"], row["id"]) for row in entries]
        assert len(manager.get_unified_ledger(100, search="%_'")) == 8
        assert manager.get_unified_ledger(100, search="' OR 1=1 --") == []
        assert len(manager.get_unified_ledger(100, period="today", search="needle")) == 6
        page = SimpleNamespace(finance_manager=manager, _ledger_period="today", _ledger_search="needle", _current_filter_key="ALL")
        exported = AccountingFuncMixin._collect_ledger_export_rows(page)
        assert len(exported) == 6
        assert {row["Kaynak"] for row in exported} == {"accounting", "currency"}
        assert all("2026-10-01" in row["Tarih"] for row in exported)
        assert all("Needle" in row["Aciklama"] for row in exported)
        page._current_filter_key = "EXPENSE"
        assert AccountingFuncMixin._collect_ledger_export_rows(page) == []
        page._current_filter_key = "INCOME"
        assert len(AccountingFuncMixin._collect_ledger_export_rows(page)) == 6
        assert len(manager.get_unified_ledger(200, search="ismail i\u015fik")) == 120
        ref = manager.get_unified_ledger(100, search="REF-119")
        assert len(ref) == 1 and ref[0]["source"] == "currency"
        with pytest.raises(ValueError, match="200 characters"):
            manager.get_unified_ledger(search="x" * 201)
        assert not db.conn.in_transaction
        results = []
        worker = LedgerWorker(str(path), limit=2, offset=2, period="today", search="needle")
        worker.finished.connect(lambda *args: results.append(args))
        worker.run()
        assert results[0][0] == manager.get_unified_ledger(2, offset=2, period="today", search="needle")
        assert results[0][2] is True
        isolated = Database(str(tmp_path / "isolated.db"))
        try:
            assert FinanceManager(isolated).get_unified_ledger(search="needle") == []
        finally:
            isolated.close()
    finally:
        db.close()


def test_native_search_debounces_resets_page_and_rejects_stale_signals(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    requests = []
    monkeypatch.setattr(AccountingPage, "refresh_data", lambda self: requests.append(self._ledger_search))
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    db = Database(str(tmp_path / "search_controls.db"))
    page = AccountingPage(db, None)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        QTest.qWait(120)
        requests.clear()
        page.ledger_current_page = 3
        page._expanded_ledger_dates.add("old")
        page.reference_ledger_search.setText("first")
        page.reference_ledger_search.setText(" final ")
        assert page._ledger_search == "final"
        assert page.ledger_current_page == 0
        assert page._expanded_ledger_dates == set()
        assert requests == []
        QTest.qWait(300)
        assert requests == ["final"]
        received = []
        monkeypatch.setattr(page, "on_data_loaded", lambda *args: received.append(args))
        worker = LedgerWorker(str(tmp_path / "search_controls.db"), search="first")
        worker.request_page = 0
        worker.finished.connect(page._handle_ledger_worker_finished)
        worker.finished.emit([{"description": "stale"}], {}, False)
        assert received == []
        worker.search = "final"
        worker.finished.emit([{"description": "current"}], {}, False)
        assert received[0][0] == [{"description": "current"}]
        page.reference_ledger_search.clear()
        QTest.qWait(300)
        assert requests[-1] == ""
        assert page.reference_ledger_search.maxLength() == 200
    finally:
        page._ledger_search_timer.stop()
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()
