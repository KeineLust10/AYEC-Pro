import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

from src.ui.main_window import MainWindow


class _ShellHarness(QMainWindow):
    def __init__(self):
        super().__init__()
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.shell_layout = QVBoxLayout(self.central_widget)
        self.shell_layout.setContentsMargins(0, 0, 0, 0)
        self.app_header = QLabel("Shared application header", self.central_widget)
        self.shell_layout.addWidget(self.app_header)
        self.shell_layout.addWidget(QWidget(self.central_widget), 1)
        self._service_list_shell_active = False


def test_service_list_keeps_the_shared_header_in_the_global_shell():
    app = QApplication.instance() or QApplication([])
    window = _ShellHarness()
    window.setMinimumWidth(1280)

    MainWindow._set_service_list_shell(window, True)
    app.processEvents()
    assert window.app_header.parentWidget() is window.central_widget
    assert window.shell_layout.indexOf(window.app_header) == 0
    assert window.minimumWidth() == 991

    MainWindow._set_service_list_shell(window, False)
    app.processEvents()
    assert window.app_header.parentWidget() is window.central_widget
    assert window.shell_layout.indexOf(window.app_header) == 0
    assert window.minimumWidth() == 1280
    window.close()
