from types import SimpleNamespace

from src.ui.pages import _accounting_data_mixin as accounting_data
from src.ui.pages._accounting_data_mixin import AccountingDataMixin


class _Db:
    def get_setting(self, key, default=""):
        return default


def test_first_ledger_load_expands_latest_date_and_keeps_user_choice(monkeypatch):
    monkeypatch.setattr(
        accounting_data,
        "format_date",
        lambda value, _db, include_time=False: str(value)[:10],
    )
    state = SimpleNamespace(
        _refresh_lock=True,
        ledger_has_more=False,
        db=_Db(),
        _financial_summary={},
        ledger_data=[],
        _expanded_ledger_dates=set(),
        _ledger_groups_initialized=False,
        _current_filter_key="ALL",
        _pending_refresh=False,
        _update_ledger_pagination=lambda: None,
        _update_summary_cards=lambda _summary: None,
        apply_filter=lambda _filter: None,
    )
    rows = [
        {"date": "2026-09-29 10:00:00", "sort_ts": 10, "currency": "TRY"},
        {"date": "2026-09-30 09:00:00", "sort_ts": 20, "currency": "TRY"},
    ]

    AccountingDataMixin.on_data_loaded(state, rows, {}, False)

    assert state._expanded_ledger_dates == {"2026-09-30"}
    state._expanded_ledger_dates.clear()
    state._expanded_ledger_dates.add("2026-09-29")
    AccountingDataMixin.on_data_loaded(state, rows, {}, False)
    assert state._expanded_ledger_dates == {"2026-09-29"}
