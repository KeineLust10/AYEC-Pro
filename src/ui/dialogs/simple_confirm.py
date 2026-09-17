from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton

from src.ui.widgets.modern_dialog import ModernDialog


class SimpleConfirmDialog(ModernDialog):
    def __init__(self, parent=None, title="Onay", text="Bu islemi yapmak istediginize emin misiniz", ok_text="Sil", cancel_text="Iptal", btn_color="#ef4444"):
        super().__init__(title=title, parent=parent, width=350, height=180)
        self.set_footer_visible(False)

        lbl_text = QLabel(text)
        lbl_text.setWordWrap(True)
        self.content_layout.addWidget(lbl_text)
        self.content_layout.addStretch()

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton(cancel_text)
        btn_cancel.clicked.connect(self.reject)
        btn_confirm = QPushButton(ok_text)
        btn_confirm.setStyleSheet(f"background-color: {btn_color}; color: white;")
        btn_confirm.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addStretch()
        btn_box.addWidget(btn_confirm)
        self.content_layout.addLayout(btn_box)
