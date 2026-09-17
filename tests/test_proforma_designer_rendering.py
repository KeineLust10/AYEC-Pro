import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QPainter, QPdfWriter
from PyQt6.QtWidgets import QApplication

from src.ui.pages.settings_widgets.proforma_designer import (
    ProformaTemplateDesignerDialog,
)


APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


class FakeSettings:
    def __init__(self):
        self.values = {}

    def get_setting(self, key, default=None):
        return self.values.get(key, default)

    def set_setting(self, key, value):
        self.values[key] = value


def test_pdf_template_page_is_rendered_to_canvas(tmp_path):
    pdf_path = tmp_path / "template.pdf"
    writer = QPdfWriter(str(pdf_path))
    painter = QPainter(writer)
    painter.drawText(100, 100, "AYEC Pro template")
    painter.end()

    dialog = ProformaTemplateDesignerDialog(
        FakeSettings(),
        str(pdf_path),
    )
    APP.processEvents()

    assert dialog.pdf_doc.pageCount() == 1
    assert dialog.canvas.image is not None
    assert not dialog.canvas.image.isNull()
    assert dialog.canvas.width() > 0
    assert dialog.canvas.height() > 0
    dialog.close()
