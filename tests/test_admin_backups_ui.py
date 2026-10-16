import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Admin_Konsol"))

from PyQt6.QtWidgets import QApplication

from pages import backups as backups_module


def _wait_for_backups(page, app):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        app.processEvents()
        if not page._workers and page._table.rowCount() == 2:
            return
        for worker in tuple(page._workers):
            worker.wait(50)
        app.processEvents()
    raise AssertionError("Backup workers did not populate the page")


def test_backup_filters_checksum_binding_and_restore_acknowledgement(monkeypatch):
    app = QApplication.instance() or QApplication([])
    today = datetime.now().strftime("%Y-%m-%d")
    older = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")
    rows = [
        {
            "backup_id": 10,
            "index": 10,
            "filename": "alpha.db",
            "source": "server",
            "created_at": f"{today} 08:00:00",
            "size_bytes": 1024,
            "product_code": "teknik_servis",
            "hardware_id": "device-a",
            "sha256": "abcd1234",
        },
        {
            "backup_id": 11,
            "index": 11,
            "filename": "beta.db",
            "source": "desktop",
            "created_at": f"{older} 08:00:00",
            "size_bytes": 2048,
            "product_code": "teknik_servis",
            "hardware_id": "device-b",
        },
    ]
    restore_calls = []
    monkeypatch.setattr(
        backups_module.api_client,
        "companies",
        lambda: [{"id": "tenant-a", "company_name": "Alpha"}],
    )
    monkeypatch.setattr(backups_module.api_client, "backups", lambda _tenant: rows)
    monkeypatch.setattr(
        backups_module.api_client,
        "restore_backup",
        lambda *args: restore_calls.append(args) or {"command_id": "restore-1"},
    )

    page = backups_module.BackupsPage()
    _wait_for_backups(page, app)
    assert page._metric_count.text() == "2"
    assert page._metric_size.text() == "1 / 2"

    page._date_filter.setCurrentIndex(2)
    app.processEvents()
    page._search.setText("device-b")
    app.processEvents()
    assert page._table.isRowHidden(0)
    assert not page._table.isRowHidden(1)

    page._search.clear()
    page._date_filter.setCurrentIndex(0)
    page._on_backup_filter_changed(0)
    assert not page._table.isRowHidden(0)
    assert page._table.isRowHidden(1)

    page._restore_selected()
    assert not restore_calls
    assert not page._restore_button.isEnabled()
    page._table.cellWidget(0, 6).click()
    assert page._table.currentRow() == 0
    assert not page._restore_button.isEnabled()
    page._restore_ack.setChecked(True)
    assert page._restore_button.isEnabled()
    page._restore_ack.setChecked(False)
    assert not page._restore_button.isEnabled()
    assert not restore_calls

    for worker in tuple(page._workers):
        worker.wait(1000)
    page.close()
    app.processEvents()
