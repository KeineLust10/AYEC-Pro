import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.database import Database
from src.ui.pages.audit_log_page import AuditLogPage


def test_audit_log_polling_only_runs_while_page_is_visible(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    db = Database(str(tmp_path / "audit_timer.db"))
    page = AuditLogPage(db)
    calls = {"count": 0}
    monkeypatch.setattr(page, "load_logs", lambda: calls.__setitem__("count", calls["count"] + 1))

    try:
        assert not page.timer.isActive()
        page._refresh_logs_if_live_stream_paused()
        assert calls["count"] == 0

        page.show()
        app.processEvents()
        assert page.timer.isActive()
        page.timer.stop()
        page._refresh_logs_if_live_stream_paused()
        assert calls["count"] == 1

        page.btn_live_stream.setChecked(True)
        page._refresh_logs_if_live_stream_paused()
        assert calls["count"] == 1

        page.hide()
        app.processEvents()
        assert not page.timer.isActive()
    finally:
        page.close()
        db.close()
