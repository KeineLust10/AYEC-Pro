"""
AYEC Pro Admin Konsol - Uygulama Giris Noktasi
"""
import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

import config
from login_window import LoginWindow
from main_window import MainWindow


def run():
    log_path = Path.home() / "AppData" / "Local" / "AYECAdmin" / "admin_console_crash.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=str(log_path), level=logging.INFO, encoding="utf-8")
    def _excepthook(exc_type, exc_value, exc_traceback):
        logging.getLogger("ayec_admin").critical("Unhandled Admin Console error", exc_info=(exc_type, exc_value, exc_traceback))
    sys.excepthook = _excepthook
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    app.setOrganizationName("AYEC Pro")

    # Ikon
    import os
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "admin_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Giris dongusu
    while True:
        login = LoginWindow()
        result = login.exec()
        if result != LoginWindow.DialogCode.Accepted:
            break

        try:
            main_win = MainWindow()
            main_win.show()
        except Exception as exc:
            logging.getLogger("ayec_admin").exception("Main window initialization failed")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "AYEC Pro Admin", f"Ana pencere acilamadi.\\n{type(exc).__name__}: {exc}\\n\\nAyrinti: {log_path}")
            break

        # Cikis sinyali beklenir
        logged_out = [False]

        def on_logged_out():
            logged_out[0] = True
            main_win.close()

        main_win.logged_out.connect(on_logged_out)
        app.exec()

        if not logged_out[0]:
            break

    sys.exit(0)


if __name__ == "__main__":
    run()
