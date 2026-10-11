import os
import logging
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication

from src.database import Database
from src.ui.dialogs.new_service_dialog import NewServiceDialog


def main():
    logging.disable(logging.CRITICAL)
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="ayec-service-preview-") as temp_dir:
        db = Database(str(Path(temp_dir) / "preview.db"))
        dialog = NewServiceDialog(db)
        dialog.set_dialog_size(1440, 1184)
        dialog.show()
        for _ in range(12):
            app.processEvents()
        target = Path.home() / "Desktop" / "Figma tasar\u0131m" / "Servis kayd\u0131 olu\u015ftur" / "screen-after.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        canvas = QPixmap(1600, 1280)
        canvas.fill(QColor("#03060a"))
        painter = QPainter(canvas)
        painter.drawPixmap(QPoint(80, 48), dialog.grab())
        painter.end()
        if not canvas.save(str(target)):
            raise RuntimeError("Screenshot could not be saved")
        dialog.close()
        db.close()


if __name__ == "__main__":
    main()
