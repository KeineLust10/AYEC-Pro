import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QScrollArea

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from pages.updates import UpdatesPage


def test_update_target_search_and_visible_select(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(UpdatesPage, "_load_companies", lambda self: None)
    page = UpdatesPage()
    page._populate_companies(
        [
            {"id": "tenant-1", "company_name": "ASLAN TIC", "active": 1, "station_name": "Pilot Yetkili", "station_id": 4802, "terminal_count": 3, "current_version": "v2.0.1"},
            {"id": "tenant-2", "company_name": "Babali Servis", "active": 1},
            {"id": "tenant-3", "company_name": "Inactive", "active": 0},
        ]
    )

    assert page._companies.rowCount() == 2
    assert page._companies.columnCount() == 5
    assert "Pilot Yetkili Istasyon #4802 3 Terminal" in page._companies.item(0, 1).data(Qt.ItemDataRole.UserRole + 1)
    assert "Pilot Yetkili" in page._companies.item(0, 1).data(Qt.ItemDataRole.UserRole + 2)
    page._company_search.setText("aslan")
    assert not page._companies.isRowHidden(0)
    assert page._companies.isRowHidden(1)

    page._set_all_checks(Qt.CheckState.Checked)
    assert page._selected_targets() == ["tenant-1"]
    assert page._target_summary.text() == "1 Firma Se\u00e7ili"
    assert page._metric_selected.text() == "1"

    page._company_search.clear()
    page._set_all_checks(Qt.CheckState.Checked)
    assert page._selected_targets() == ["tenant-1", "tenant-2"]
    assert page._target_summary.text() == "2 Firma Se\u00e7ili"
    page._version.setText("2.3.1-rc1")
    assert page._metric_release.text() == "2.3.1-rc1"
    page._deploy_done({"version": "2.3.1-rc1", "targets": ["tenant-1"], "deployment_id": "JOB-1", "status": "queued"})
    assert "JOB-1" in page._telemetry_status.text()
    assert "2.3.1-rc1" in page._telemetry_log.toPlainText()


def test_update_distribution_reflows_without_horizontal_overflow_on_mobile(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(UpdatesPage, "_load_companies", lambda self: None)
    page = UpdatesPage()
    page._populate_companies([{"id": "tenant-1", "company_name": "ASLAN TIC", "active": 1}])
    page.resize(1440, 1000)
    page.show()
    persistent_qapplication.processEvents()
    assert page._root_layout.contentsMargins().left() == 40
    assert page._metric_cards[0].minimumHeight() == 128
    assert page._params_panel.minimumHeight() == 208
    page.resize(390, 844)
    page.show()
    persistent_qapplication.processEvents()
    assert page._params_panel.minimumHeight() == 0

    metric_columns = {page._metric_grid.getItemPosition(index)[1] for index in range(page._metric_grid.count())}
    scroll = page.findChild(QScrollArea, "updatesScroll")
    assert metric_columns == {0}
    assert page._companies.isColumnHidden(2)
    assert page._companies.isColumnHidden(3)
    assert page._companies.isColumnHidden(4)
    assert scroll.horizontalScrollBar().maximum() == 0
    assert any(label.text() == "G\u00fcncelleme Da\u011f\u0131t\u0131m\u0131 & OTA S\u00fcr\u00fcm Y\u00f6netimi" and label.isVisible() for label in page.findChildren(QLabel))
