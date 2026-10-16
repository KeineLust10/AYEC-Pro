import sys
from pathlib import Path

from PyQt6.QtWidgets import QFrame, QLineEdit, QMainWindow, QLabel, QProgressBar

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from main_window import MainWindow
import api_client


def test_admin_header_metrics_bind_live_server_status(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(api_client, "server_status", lambda: {"cpu_percent": 23, "ram_percent": 51, "disk_percent": 30})
    class HeaderHarness(MainWindow):
        def __init__(self):
            QMainWindow.__init__(self)

    window = HeaderHarness()
    window._header_status_thread = None
    window._header_metric_widgets = {
        key: (QProgressBar(window), QLabel("--", window))
        for key in ("cpu_percent", "ram_percent", "disk_percent")
    }

    MainWindow._refresh_header_status(window)
    assert window._header_status_thread.wait(3000)
    persistent_qapplication.processEvents()

    assert [(bar.value(), value.text()) for bar, value in window._header_metric_widgets.values()] == [
        (23, "23%"), (51, "51%"), (30, "30%")
    ]
    MainWindow._update_header_metrics(window, {})
    assert [value.text() for _bar, value in window._header_metric_widgets.values()] == ["--", "--", "--"]
    window.close()


def test_admin_header_height_matches_each_reference_shell(persistent_qapplication):
    class HeaderHarness(QMainWindow):
        def __init__(self):
            QMainWindow.__init__(self)
            self._top_bar = QFrame(self)
            self._global_search = QLineEdit(self)

    window = HeaderHarness()
    MainWindow._apply_reference_header_layout(window, "dashboard")
    assert window._top_bar.minimumHeight() == 56
    assert window._top_bar.maximumHeight() == 56
    assert window._top_bar.property("referenceStyle") == "standard"
    assert window._global_search.width() == 320
    MainWindow._apply_reference_header_layout(window, "license_requests")
    assert window._top_bar.minimumHeight() == 48
    assert window._top_bar.maximumHeight() == 48
    assert window._top_bar.property("referenceStyle") == "license"
    assert window._global_search.width() == 256
    window.close()
