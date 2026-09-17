from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout

from src.ui.widgets.modern_dialog import ModernDialog


class TechnicianLoginDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__(title="Teknisyen Girisi", parent=parent, width=420, height=320)
        self.set_footer_visible(False)
        self.tracking_no = None

        layout = self.content_layout
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(24)

        lbl_title = QLabel("Teknisyen Paneli")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet("color: white; font-size: 24px; font-weight: 800; font-family: 'Segoe UI'; letter-spacing: 0.5px;")
        layout.addWidget(lbl_title)

        input_group = QVBoxLayout()
        input_group.setSpacing(8)
        lbl_desc = QLabel("Islem yapilacak Takip No veya ID:")
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: 600;")
        input_group.addWidget(lbl_desc)

        self.inp_id = QLineEdit()
        self.inp_id.setPlaceholderText("Orn: 1045...")
        self.inp_id.setFixedHeight(50)
        self.inp_id.setStyleSheet(
            """
            QLineEdit {
                border: 2px solid #334155;
                border-radius: 12px;
                padding: 0 15px;
                background-color: #0f172a;
                color: #f8fafc;
                font-size: 16px;
                font-weight: 600;
            }
            QLineEdit:focus {
                border: 2px solid #F59E0B;
                background-color: #0f172a;
            }
            """
        )
        input_group.addWidget(self.inp_id)
        layout.addLayout(input_group)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        btn_cancel = QPushButton("Iptal")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFixedSize(100, 45)
        btn_cancel.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                border: 2px solid #ef4444;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: rgba(239, 68, 68, 0.1); }
            """
        )
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Giris Yap")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setFixedHeight(45)
        btn_ok.setStyleSheet(
            """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F59E0B, stop:1 #D97706);
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #D97706, stop:1 #B45309);
            }
            """
        )
        btn_ok.clicked.connect(self.accept_data)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok, 1)
        layout.addLayout(btn_layout)

    def accept_data(self):
        val = self.inp_id.text().strip()
        if val:
            self.tracking_no = val
            self.accept()
            return
        self.inp_id.setStyleSheet(
            """
            QLineEdit {
                border: 2px solid #ef4444;
                border-radius: 12px;
                padding: 0 15px;
                background-color: #0f172a;
                color: #ef4444;
                font-size: 16px;
                font-weight: 600;
            }
            """
        )
        self.inp_id.setPlaceholderText("Lutfen ID Giriniz!")
        QTimer.singleShot(200, lambda: self.inp_id.setFocus())
