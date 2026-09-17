from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PyQt6.QtGui import QPixmap, QImage, QPainter
from PyQt6.QtCore import Qt
import qrcode
import io
import logging

logger = logging.getLogger("AYECProLogger")

class QRWidget(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.setFixedSize(150, 150)
        self.pixmap = None
        self.generate_qr()

    def generate_qr(self):
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=1)
            qr.add_data(self.data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            qimg = QImage.fromData(buffer.getvalue())
            self.pixmap = QPixmap.fromImage(qimg)
        except Exception as e:
            logger.error("QR generation error: %s", e)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawRect(self.rect())
        if self.pixmap:
            painter.drawPixmap(0, 0, self.width(), self.height(), self.pixmap)
        else:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "QR Hata")
