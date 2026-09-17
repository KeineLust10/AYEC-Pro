import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog, QPushButton

from src.ui.modern_login_window import ModernLoginWindow


def test_login_page_does_not_expose_legacy_kernel_access():
    app = QApplication.instance() or QApplication([])
    window = ModernLoginWindow.__new__(ModernLoginWindow)
    QDialog.__init__(window)

    page = window.create_login_page()
    button_texts = {button.text() for button in page.findChildren(QPushButton)}

    assert "Teknik Servis" not in button_texts
    assert "+ Hesap Ekle" in button_texts
    assert "+ Firma Ekle" in button_texts
    assert not hasattr(ModernLoginWindow, "open_technical_service")
    assert not hasattr(ModernLoginWindow, "open_technical_service_cover")

    page.deleteLater()
    window.deleteLater()
    app.processEvents()
