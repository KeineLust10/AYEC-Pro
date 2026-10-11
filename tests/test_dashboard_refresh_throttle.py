from types import SimpleNamespace

from src.ui.pages import _dashboard_base_mixin as dashboard_base
from src.ui.pages._dashboard_base_mixin import DashboardBaseMixin


def test_dashboard_navigation_refresh_is_throttled_but_resumes_when_stale(monkeypatch):
    clock = {"now": 100.0}
    calls = []
    monkeypatch.setattr(dashboard_base.time, "monotonic", lambda: clock["now"])
    page = SimpleNamespace(
        _last_dashboard_refresh_monotonic=100.0,
        refresh_data=lambda: calls.append(clock["now"]),
    )

    assert not DashboardBaseMixin.refresh_data_if_stale(page, minimum_interval=10)
    assert calls == []

    clock["now"] = 111.0
    assert DashboardBaseMixin.refresh_data_if_stale(page, minimum_interval=10)
    assert calls == [111.0]
