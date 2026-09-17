from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSpinBox

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.logger import logger


class ModernInputDialog(ModernDialog):
    def __init__(self, parent=None, title="Giris", label="Deger:", mode="text", default_value=None):
        super().__init__(title=title, parent=parent, width=450, height=300)
        self.mode = mode
        self.value = None
        self.set_footer_visible(False)

        lbl_desc = QLabel(label)
        lbl_desc.setWordWrap(True)
        self.content_layout.addWidget(lbl_desc)

        if mode == "multiline":
            self.input_field = QPlainTextEdit()
            self.input_field.setPlainText(str(default_value) if default_value else "")
            self.input_field.setFixedHeight(120)
        elif mode == "int":
            self.input_field = QSpinBox()
            self.input_field.setRange(1, 999999999)
            self.input_field.setValue(max(1, int(float(default_value or 1))))
            self.input_field.setGroupSeparatorShown(False)
            self.input_field.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.input_field.setFixedHeight(46)
        else:
            self.input_field = QLineEdit()
            self.input_field.setText(str(default_value) if default_value is not None else "")
            self.input_field.setFixedHeight(46)

        self.content_layout.addWidget(self.input_field)
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
        try:
            if self.mode == "multiline":
                self.value = self.input_field.toPlainText()
            elif self.mode == "int":
                self.value = int(self.input_field.value())
            elif self.mode == "double":
                val_str = self.input_field.text().replace(",", ".") or "0"
                self.value = float(val_str)
            else:
                self.value = self.input_field.text()
            self.accept()
        except Exception as exc:
            logger.error("ModernInputDialog value parse error: %s", exc)
            self.value = 0 if self.mode in ["int", "double"] else ""
            self.accept()

    def get_value(self):
        return self.value

    @staticmethod
    def get_text(parent, title, label, default=""):
        dlg = ModernInputDialog(parent, title, label, mode="text", default_value=default)
        if dlg.exec():
            return dlg.get_value(), True
        return "", False

    @staticmethod
    def get_double(parent, title, label, default=0.0):
        dlg = ModernInputDialog(parent, title, label, mode="double", default_value=default)
        if dlg.exec():
            return dlg.get_value(), True
        return 0.0, False

    @staticmethod
    def get_int(parent, title, label, default=0):
        dlg = ModernInputDialog(parent, title, label, mode="int", default_value=default)
        if dlg.exec():
            return dlg.get_value(), True
        return 0, False

    @staticmethod
    def get_multiline(parent, title, label, default=""):
        dlg = ModernInputDialog(parent, title, label, mode="multiline", default_value=default)
        if dlg.exec():
            return dlg.get_value(), True
        return "", False
