from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.context_menu_settings import is_context_menu_enabled


class ManualLocationDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__(title="Konuma Git", parent=parent, width=400, height=320)
        self.set_footer_visible(False)

        desc = QLabel("Gitmek istediginiz nokta icin koordinat giriniz.")
        desc.setWordWrap(True)
        self.content_layout.addWidget(desc)

        self.inp_lat = QLineEdit()
        self.inp_lat.setPlaceholderText("Enlem (Lat) orn: 39.6484")
        self.content_layout.addWidget(self.inp_lat)

        self.inp_lng = QLineEdit()
        self.inp_lng.setPlaceholderText("Boylam (Lng) orn: 27.8826")
        self.content_layout.addWidget(self.inp_lng)
        self.content_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Vazgec")
        btn_cancel.clicked.connect(self.reject)
        btn_confirm = QPushButton("Isinla")
        btn_confirm.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_confirm)
        self.content_layout.addLayout(btn_layout)

    def get_coordinates(self):
        try:
            lat = float(self.inp_lat.text().replace(",", "."))
            lng = float(self.inp_lng.text().replace(",", "."))
            return lat, lng
        except ValueError:
            return None


class PersonnelCard(QFrame):
    def __init__(self, t_data, callback, finish_callback, parent=None):
        super().__init__(parent)
        self.t_data = t_data
        self.callback = callback
        self.finish_callback = finish_callback
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            """
            QFrame {
                background: white;
                border-radius: 8px;
                border: 1px solid #f1f5f9;
            }
            QFrame:hover {
                background: #f8fafc;
                border-color: #cbd5e1;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        name_lbl = QLabel(t_data["name"])
        name_lbl.setStyleSheet("border: none; background: transparent;")
        name_lbl.setFont(QFont("Outfit", 10, QFont.Weight.Bold))

        status_text = t_data.get("status", "Bosta")
        status_color = "#10b981" if status_text in ["Bosta", "Bosta"] else "#f59e0b"
        status_lbl = QLabel(f"* {status_text}")
        status_lbl.setStyleSheet(f"color: {status_color}; border: none; background: transparent; font-size: 12px;")

        layout.addWidget(name_lbl)
        layout.addWidget(status_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.callback(self.t_data)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        db = None
        owner = self.parent()
        while owner is not None:
            db = getattr(owner, "db", None)
            if db is not None:
                break
            owner = owner.parent()
        if not is_context_menu_enabled(db):
            return
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        finish_action = menu.addAction("Gorevi Tamamla / Bosa Cikar")
        action = menu.exec(event.globalPos())
        if action == finish_action and self.finish_callback:
            self.finish_callback(self.t_data)


class ModernConfirmDialog(ModernDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(title=title, parent=parent, width=360, height=220)
        self.set_footer_visible(False)

        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        self.content_layout.addWidget(lbl_msg)
        self.content_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("Iptal")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Onayla")
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        self.content_layout.addLayout(btn_layout)
