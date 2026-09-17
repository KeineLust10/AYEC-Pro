from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton

from src.ui.widgets.modern_dialog import ModernDialog


class ModernSelectDialog(ModernDialog):
    def __init__(self, parent=None, title="Secim", label="Seciniz:", items=None, current_index=0):
        super().__init__(title=title, parent=parent, width=450, height=280)
        self.value = None
        self.set_footer_visible(False)
        items = items or []

        lbl_desc = QLabel(label)
        lbl_desc.setWordWrap(True)
        self.content_layout.addWidget(lbl_desc)

        self.combo = QComboBox()
        self.combo.addItems([str(x) for x in items])
        if 0 <= int(current_index) < self.combo.count():
            self.combo.setCurrentIndex(int(current_index))
        self.combo.currentIndexChanged.connect(self.on_combo_changed)
        self.content_layout.addWidget(self.combo)
        self.content_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Vazgec")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Onayla")
        btn_ok.clicked.connect(self.accept_value)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        self.content_layout.addLayout(btn_layout)

    def accept_value(self):
        self.value = self.combo.currentText()
        self.accept()

    def on_combo_changed(self):
        self.value = self.combo.currentText()

    def get_value(self):
        return self.value

    @staticmethod
    def get_item(parent, title, label, items, current=0):
        dlg = ModernSelectDialog(parent, title, label, items=items, current_index=current)
        if dlg.exec():
            return dlg.get_value(), True
        return "", False
