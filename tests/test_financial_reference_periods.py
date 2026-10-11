import os
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.database import Database
from src.ui.pages.accounting_page import AccountingPage
from src.ui.pages._accounting_data_mixin import LedgerWorker
from src.utils.finance_manager import FinanceManager
import src.utils.finance_manager as finance_module
import src.ui.pages._accounting_data_mixin as accounting_data_module


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 1, 12, 0, 0, tzinfo=tz)


def test_reference_periods_query_both_sources_and_keep_pagination(monkeypatch, tmp_path):
    monkeypatch.setattr(finance_module, "datetime", FixedDateTime)
    db = Database(str(tmp_path / "financial_periods.db"))
    dates = ["2026-09-24 23:59:59", "2026-09-25", "2026-09-30T23:59:59",
             "2026-10-01", "2026-10-01 23:59:59.999", "2026-10-02"]
    try:
        db.conn.execute("INSERT INTO customers(name) VALUES ('Period Customer')")
        customer_id = db.conn.execute("SELECT id FROM customers").fetchone()[0]
        for number, timestamp in enumerate(dates):
            db.conn.execute("INSERT INTO accounting(date,created_at,description,amount,type,category,currency) VALUES (?,?,?,10,'Gelir','Fixture','TRY')",
                            (timestamp, timestamp, "Accounting " + str(number)))
            db.conn.execute("INSERT INTO currency_transactions(customer_id,transaction_type,amount,currency,exchange_rate,try_equivalent,created_at,description) VALUES (?,'CREDIT',20,'TRY',1,20,?,?)",
                            (customer_id, timestamp, "Currency " + str(number)))
        db.conn.commit()
        manager = FinanceManager(db)
        for period, numbers in (("today", {3, 4}), ("month", {3, 4, 5}), ("last7", {1, 2, 3, 4})):
            entries = manager.get_unified_ledger(100, period=period)
            assert {entry["description"] for entry in entries} == {
                prefix + str(number) for prefix in ("Fixture - Accounting ", "Currency ") for number in numbers}
            assert {entry["source"] for entry in entries} == {"accounting", "currency"}
            paged = [entry for offset in range(0, len(entries), 2)
                     for entry in manager.get_unified_ledger(2, offset=offset, period=period)]
            assert [(entry["source"], entry["id"]) for entry in paged] == [(entry["source"], entry["id"]) for entry in entries]
        assert manager.get_unified_ledger(100) == manager.get_unified_ledger(100, period="fiscal")
        results = []
        worker = LedgerWorker(str(tmp_path / "financial_periods.db"), limit=2, offset=2, period="last7")
        worker.finished.connect(lambda *args: results.append(args))
        worker.run()
        expected_page = manager.get_unified_ledger(2, offset=2, period="last7")
        assert results[0][0] == expected_page
        assert results[0][2] is True
        with pytest.raises(ValueError, match="Unsupported ledger period"):
            manager.get_unified_ledger(period="unknown")
    finally:
        db.close()


def test_reference_period_controls_reset_page_and_discard_stale_results(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    requests = []
    monkeypatch.setattr(AccountingPage, "refresh_data", lambda self: requests.append((self._ledger_period, self.ledger_current_page)))
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    db = Database(str(tmp_path / "financial_period_controls.db"))
    page = AccountingPage(db, None)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        assert page.reference_period_buttons["fiscal"].isChecked()
        for period in ("today", "last7", "month", "fiscal"):
            page.ledger_current_page = 3
            page._expanded_ledger_dates.add("old")
            page.reference_period_buttons[period].click()
            assert page._ledger_period == period
            assert page.ledger_current_page == 0
            assert page._expanded_ledger_dates == set()
            assert requests[-1] == (period, 0)
        received = []
        monkeypatch.setattr(page, "on_data_loaded", lambda *args: received.append(args))
        page._refresh_lock = True
        page._on_ledger_result("today", 0, [{"description": "stale"}], {}, False)
        assert received == []
        assert not page._refresh_lock
        assert requests[-1] == ("fiscal", 0)
        page._on_ledger_result("fiscal", 0, [{"description": "current"}], {}, False)
        assert received[0][0] == [{"description": "current"}]
        worker = LedgerWorker(str(tmp_path / "financial_period_controls.db"), period="today")
        worker.request_page = 0
        worker.finished.connect(page._handle_ledger_worker_finished)
        worker.finished.emit([{"description": "stale signal"}], {}, False)
        assert len(received) == 1
        worker.period = "fiscal"
        worker.finished.emit([{"description": "current signal"}], {}, False)
        assert received[-1][0] == [{"description": "current signal"}]
        page.ledger_current_page = 1
        worker.finished.emit([{"description": "stale page"}], {}, False)
        assert len(received) == 2
        worker.request_page = 1
        worker.finished.emit([{"description": "current page"}], {}, False)
        assert received[-1][0] == [{"description": "current page"}]
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_period_switch_keeps_running_workers_alive_until_native_thread_finish(monkeypatch, tmp_path):
    from PyQt6.QtTest import QTest
    from PyQt6 import sip

    app = QApplication.instance() or QApplication([])
    created = []

    class SlowLedgerWorker(LedgerWorker):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created.append(self)

        def run(self):
            self.result_ready.emit(
                [], {}, False, self.period, self.request_page, self.search
            )
            self.msleep(80)

    monkeypatch.setattr(accounting_data_module, "LedgerWorker", SlowLedgerWorker)
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    db = Database(str(tmp_path / "financial_worker_lifetime.db"))
    page = AccountingPage(db, None)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    accepted = []
    original_loaded = page.on_data_loaded
    monkeypatch.setattr(page, "on_data_loaded", lambda *args: (accepted.append(page._ledger_period), original_loaded(*args)))
    try:
        page.refresh_data()
        assert created[0].parent() is app
        for period in ("today", "month", "fiscal", "last7"):
            page.reference_period_buttons[period].click()
        QTest.qWait(500)
        app.processEvents()
        assert len(created) >= 2
        assert page._ledger_period == "last7"
        assert accepted and set(accepted) == {"last7"}
        assert page.worker is None
        assert all(sip.isdeleted(worker) for worker in created)
    finally:
        for worker in created:
            if not sip.isdeleted(worker):
                worker.wait(1000)
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()
