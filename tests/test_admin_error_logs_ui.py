import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QPushButton

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from pages.error_logs import ErrorLogsPage


def test_error_telemetry_metrics_search_and_detail(persistent_qapplication, monkeypatch, tmp_path):
    monkeypatch.setattr(ErrorLogsPage, "_load_companies", lambda self: None)
    monkeypatch.setattr(ErrorLogsPage, "_load_logs", lambda self: None)
    page = ErrorLogsPage()
    page._populate(
        [
            {
                "timestamp": "2026-10-14 09:20",
                "company": "ASLAN TIC",
                "machine": "WS-01",
                "level": "ERROR",
                "line": 42,
                "message": "Database is locked",
                "traceback": "sqlite3.OperationalError",
            },
            {
                "timestamp": "2026-10-14 09:21",
                "company": "Babali Servis",
                "machine": "WS-02",
                "level": "WARNING",
                "line": 18,
                "message": "Retry scheduled",
            },
        ]
    )

    assert page._metric_total.text() == "2"
    assert len(page._metric_cards) == 4
    assert page._metric_stability.text() == "98.5%"
    assert page._content.objectName() == "errorTelemetryContent"
    assert not page._table.verticalHeader().isVisible()
    assert page._metric_errors.text() == "1"
    assert page._metric_warnings.text() == "1"
    assert page._table_count.text() == "Son 2 Hata Olayi"
    page._search.setText("aslan")
    assert [
        (page._table.item(row, 1).text(), not page._table.isRowHidden(row))
        for row in range(page._table.rowCount())
    ] == [("ASLAN TIC", True), ("Babali Servis", False)], (page._search.text(), page._level_filter)
    assert page._table_count.text() == "Son 1 Hata Olayi"
    page._show_detail(0, 0)
    assert "sqlite3.OperationalError" in page._detail.toPlainText()
    assert page._detail_title.text() == "Database is locked"
    page._search.clear()
    page._set_level_filter("warning")
    assert [not page._table.isRowHidden(row) for row in range(page._table.rowCount())] == [False, True]
    page._set_level_filter("all")
    page._show_detail(1, 0)
    assert "Babali Servis" in page._detail_meta.text()
    page._copy_trace()
    assert "Retry scheduled" in page._detail.toPlainText()
    assert "Retry scheduled" in QApplication.clipboard().text()
    page._populate([{"level": "FATAL", "message": "Process stopped"}])
    assert page._metric_errors.text() == "1"
    assert page._filter_buttons["critical"].text().endswith("1")
    export_path = tmp_path / "error-logs.csv"
    monkeypatch.setattr("pages.error_logs.QFileDialog.getSaveFileName", lambda *args: (str(export_path), "CSV (*.csv)"))
    page._export_logs()
    assert "Process stopped" in export_path.read_text(encoding="utf-8-sig")
    page.resize(1200, 850)
    page.show()
    persistent_qapplication.processEvents()
    assert page._splitter.orientation().name == "Vertical"
    page.resize(390, 844)
    persistent_qapplication.processEvents()
    assert page._result_stack.currentWidget() is page._mobile_logs
    assert page._splitter.orientation().name == "Vertical"
    assert page._scroll.horizontalScrollBar().maximum() == 0
    page._log_cards[0].findChild(QPushButton).click()
    assert page._detail_title.text() == "Process stopped"
