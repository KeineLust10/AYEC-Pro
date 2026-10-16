import sys
from pathlib import Path
from PyQt6.QtWidgets import QLabel, QPushButton
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtTest import QSignalSpy

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from pages.database_manager import DatabaseManagerPage


def test_database_workspace_and_results_expand_with_desktop_viewport(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(DatabaseManagerPage, "_load_companies", lambda self: None)
    page = DatabaseManagerPage()
    page.resize(1440, 1080)
    page.show()
    QCoreApplication.processEvents()

    assert page._workspace.maximumHeight() == 16777215
    assert page._table.height() > page._table.minimumHeight()
    assert page._workspace.width() == page._scroll.viewport().width() - 32

    page.resize(390, 844)
    QCoreApplication.processEvents()
    assert page._result_panel.maximumHeight() == 116
    assert page._table.maximumHeight() == 104

    page.close()


def test_sql_reference_sections_bind_status_audit_and_navigation(persistent_qapplication, monkeypatch, tmp_path):
    monkeypatch.setattr(DatabaseManagerPage, "_load_companies", lambda self: None)
    page = DatabaseManagerPage()
    assert page._module_nav_scroll.widget() is page._module_nav
    assert page._module_nav_scroll.height() == 40
    assert page._telemetry_table.columnCount() == 6
    assert page._backup_table.columnCount() == 6
    assert [button.text() for button in page._module_buttons] == [
        "Merkezi Konsol",
        "Yedekleme & Kurtarma",
        "G\u00fcncelleme Da\u011f\u0131t\u0131m\u0131",
        "Kota & Limitler",
        "SQL Sorgu Y\u00f6neticisi",
        "Hata & Telemetri",
        "Denetim (Audit)",
        "Sunucu Ayarlar\u0131",
    ]
    spy = QSignalSpy(page.navigate_requested)
    page._module_buttons[2].click()
    assert len(spy) == 1
    assert spy[0][0] == "updates"
    page._module_buttons[4].click()
    assert spy[1][0] == "database_manager"
    page._module_buttons[5].click()
    assert spy[2][0] == "error_logs"
    page._module_buttons[6].click()
    assert spy[3][0] == "audit_logs"
    page._module_buttons[7].click()
    assert spy[4][0] == "server_settings"
    page._deploy_button.click()
    assert spy[5][0] == "updates"
    page._module_buttons[1].click()
    assert spy[6][0] == "backups"
    assert page._release_input.text() == "2.0.1-rc3"
    assert page._channel_combo.currentText() == "Pilot M\u00fc\u015fteriler"

    page._populate_companies({
        "companies": [
            {"id": "tenant-1", "company_name": "ASLAN TIC"},
            {"id": "tenant-2", "company_name": "Babali Servis"},
        ],
        "server": {"cpu_percent": 23, "ram_percent": 51, "disk_percent": 30, "tenant_count": 2, "db_path": "C:/data/admin.db", "uptime": "4 days"},
        "audit": [{"timestamp": "2026-10-14 08:00", "action": "BACKUP_CREATED", "company_name": "ASLAN TIC", "status": "OK", "detail": {"size": "2 MB"}}],
        "backups": [{"filename": "ASLAN_TIC.db", "size_bytes": 2048, "source": "server"}],
    })
    assert page._firm_combo.currentData() == "tenant-1"
    assert [label.text() for label in page._platform_values] == [
        "C:/data/admin.db",
        "CPU 23%  |  RAM 51%  |  Disk 30%",
        "200 OK",
    ]
    assert page._platform_details[2].text().endswith("Aktif tenant: 2")
    assert page._telemetry_table.rowCount() == 1
    assert page._telemetry_table.item(0, 2).text() == "BACKUP_CREATED"
    assert page._telemetry_table.item(0, 4).text() == "size: 2 MB"
    assert page._backup_table.item(0, 0).text() == "ASLAN_TIC.db"

    backup_calls = []
    monkeypatch.setattr(
        "pages.database_manager.api_client.backups",
        lambda tenant_id: backup_calls.append(tenant_id) or [{"filename": "BABALI.db", "size_bytes": 4096}],
    )
    page._firm_combo.setCurrentIndex(1)
    worker = page._backup_threads[-1]
    worker.wait(1000)
    persistent_qapplication.processEvents()
    assert backup_calls == ["tenant-2"]
    assert page._backup_table.item(0, 0).text() == "BABALI.db"
    actions = page._backup_table.cellWidget(0, 5).findChildren(QPushButton)
    actions_by_text = {button.text(): button for button in actions}
    actions_by_text["Kurtar"].click()
    assert spy[7][0] == "backups"

    download_calls = []
    destination = tmp_path / "downloaded.db"
    monkeypatch.setattr(
        "pages.database_manager.QFileDialog.getSaveFileName",
        lambda *args: (str(destination), ""),
    )
    monkeypatch.setattr(
        "pages.database_manager.api_client.download_backup",
        lambda tenant, index, backup_id=0: download_calls.append((tenant, index, backup_id)) or b"backup-data",
    )
    page._download_backup(0)
    download_worker = page._download_threads[-1]
    download_worker.wait(1000)
    persistent_qapplication.processEvents()
    assert download_calls == [("tenant-2", 0, 0)]
    assert destination.read_bytes() == b"backup-data"


def test_sql_diagnostics_results_and_query_history(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(DatabaseManagerPage, "_load_companies", lambda self: None)
    page = DatabaseManagerPage()
    assert not page.findChild(QLabel, "sqlQueryKicker").wordWrap()
    assert page._sql_input.toPlainText().splitlines() == [
        "SELECT id, username, role, last_login, disk_usage_mb",
        "FROM users",
        "WHERE status = 'active'",
        "ORDER BY id ASC",
        "LIMIT 50;",
    ]
    assert page._root_layout.contentsMargins().left() == 16
    page._sql_input.setPlainText("SELECT id FROM users LIMIT 5")
    page._show_results({"columns": ["id"], "rows": [[1], [2]], "truncated": False})

    assert page._table.rowCount() == 2
    assert page._table.columnCount() == 1
    assert page._status_lbl.text().endswith("2 satir.")
    assert page._history_combo.count() == 2
    page._sql_input.clear()
    page._history_combo.setCurrentIndex(1)
    assert page._sql_input.toPlainText() == "SELECT id FROM users LIMIT 5"
    page.resize(390, 844)
    page.show()
    persistent_qapplication.processEvents()
    assert page._root_layout.contentsMargins().left() == 12
    page._show_results({"columns": ["id", "username", "role"], "rows": [[1, "operator", "admin"]], "truncated": False})
    assert page._result_stack.currentWidget() is page._mobile_results
    assert [label.text() for label in page._mobile_results.findChildren(QLabel) if label.objectName() == "sqlResultValue"] == ["1", "operator", "admin"]
    assert page._scroll.horizontalScrollBar().maximum() == 0


def test_sql_actions_send_readonly_and_explain_queries(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(DatabaseManagerPage, "_load_companies", lambda self: None)
    calls = []
    monkeypatch.setattr(
        "pages.database_manager.api_client.readonly_query",
        lambda tenant, sql: calls.append((tenant, sql)) or {
            "columns": ["id"], "rows": [[1]], "truncated": False
        },
    )
    page = DatabaseManagerPage()
    page._firm_combo.addItem("ASLAN TIC", "tenant-a")
    page._sql_input.setPlainText("SELECT id FROM users LIMIT 1;")
    page._run_btn.click()
    assert page._thread is not None
    page._thread.wait(1000)
    persistent_qapplication.processEvents()
    assert calls == [("tenant-a", "SELECT id FROM users LIMIT 1;")]
    assert page._table.rowCount() == 1
    assert page._result_count.text() == "1 satir / 1 sutun"

    page._sql_input.setPlainText("SELECT id FROM users LIMIT 1;")
    page._explain_btn.click()
    page._thread.wait(1000)
    persistent_qapplication.processEvents()
    assert calls[-1] == ("tenant-a", "EXPLAIN QUERY PLAN SELECT id FROM users LIMIT 1")
    page._clear_query()
    assert page._table.rowCount() == 0
    assert page._status_lbl.text() == "Sorgu temizlendi."
