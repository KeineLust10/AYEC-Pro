# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt
from PyQt6.QtPrintSupport import QPrinterInfo
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from src.ui.widgets.modern_dialog import ModernDialog


class ServicePrintOptionsDialog(ModernDialog):
    """Collect document, label and printer choices before PDF generation."""

    def __init__(self, db, parent=None, profile="document", title=None):
        self.db = db
        self.profile = profile
        self.direct_print = False
        dialog_title = title or "Yazd\u0131rma Ayarlar\u0131"
        super().__init__(dialog_title, parent, width=620, height=430)

        self.printer_combo = QComboBox()
        self.printer_combo.setMinimumHeight(38)
        self.printer_combo.addItem(
            "Windows varsay\u0131lan yaz\u0131c\u0131s\u0131",
            "",
        )
        for printer_name in QPrinterInfo.availablePrinterNames():
            self.printer_combo.addItem(printer_name, printer_name)

        self.paper_combo = QComboBox()
        self.paper_combo.setMinimumHeight(38)
        self.orientation_combo = QComboBox()
        self.orientation_combo.setMinimumHeight(38)
        self.orientation_combo.addItem("Dikey", "portrait")
        self.orientation_combo.addItem("Yatay", "landscape")

        self.width_spin = self._dimension_spin()
        self.height_spin = self._dimension_spin()

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.addRow("Yaz\u0131c\u0131:", self.printer_combo)

        if profile == "document":
            self.paper_combo.addItems(["A4", "A3", "A5"])
            form.addRow("Ka\u011f\u0131t Boyutu:", self.paper_combo)
            form.addRow("Y\u00f6n:", self.orientation_combo)
        elif profile.startswith("label"):
            size_row = QHBoxLayout()
            size_row.addWidget(self.width_spin)
            size_row.addWidget(QLabel("x"))
            size_row.addWidget(self.height_spin)
            size_holder = QWidget()
            size_holder.setLayout(size_row)
            form.addRow("Etiket (mm):", size_holder)
        else:
            receipt_text = QLabel(
                "Fi\u015fin sayfa boyutu yaz\u0131c\u0131ya uygun olarak PDF i\u00e7inde korunur."
            )
            receipt_text.setWordWrap(True)
            form.addRow("Ka\u011f\u0131t:", receipt_text)

        self.add_layout(form)
        self._load_defaults()
        self.add_cancel_button("\u0130ptal")
        self.add_button(
            "PDF Olu\u015ftur / \u00d6nizle",
            "secondary",
            self._accept_preview,
        )
        self.add_button(
            "Se\u00e7ili Yaz\u0131c\u0131ya G\u00f6nder",
            "primary",
            self._accept_direct,
        )

    @staticmethod
    def _dimension_spin():
        spin = QDoubleSpinBox()
        spin.setRange(20.0, 320.0)
        spin.setDecimals(1)
        spin.setSuffix(" mm")
        spin.setMinimumHeight(38)
        return spin

    @property
    def printer_name(self):
        return self.printer_combo.currentData() or ""

    @property
    def page_size(self):
        return self.paper_combo.currentText() or "A4"

    @property
    def orientation(self):
        return self.orientation_combo.currentData() or "portrait"

    @property
    def label_width_mm(self):
        return float(self.width_spin.value())

    @property
    def label_height_mm(self):
        return float(self.height_spin.value())

    def _setting_key(self):
        if self.profile == "document":
            return "print_document_printer"
        if self.profile.startswith("label"):
            return "print_label_printer"
        return "print_receipt_printer"

    def _select_data(self, combo, value):
        index = combo.findData(value)
        if index < 0:
            index = combo.findText(str(value))
        if index >= 0:
            combo.setCurrentIndex(index)

    def _load_defaults(self):
        self._select_data(
            self.printer_combo,
            self.db.get_setting(self._setting_key(), ""),
        )
        if self.profile == "document":
            self._select_data(
                self.paper_combo,
                self.db.get_setting("print_document_page_size", "A4"),
            )
            self._select_data(
                self.orientation_combo,
                self.db.get_setting("print_document_orientation", "portrait"),
            )
        elif self.profile.startswith("label"):
            width_key, height_key, default_width, default_height = self._label_keys()
            self.width_spin.setValue(
                float(self.db.get_setting(width_key, default_width) or default_width)
            )
            self.height_spin.setValue(
                float(self.db.get_setting(height_key, default_height) or default_height)
            )

    def _save_defaults(self):
        self.db.set_setting(self._setting_key(), self.printer_name)
        if self.profile == "document":
            self.db.set_setting("print_document_page_size", self.page_size)
            self.db.set_setting("print_document_orientation", self.orientation)
        elif self.profile.startswith("label"):
            width_key, height_key, _, _ = self._label_keys()
            self.db.set_setting(
                width_key,
                f"{self.label_width_mm:.1f}",
            )
            self.db.set_setting(
                height_key,
                f"{self.label_height_mm:.1f}",
            )

    def _label_keys(self):
        if self.profile == "label_a":
            return (
                "print_label_a_width_mm",
                "print_label_a_height_mm",
                "100",
                "28",
            )
        return (
            "print_label_width_mm",
            "print_label_height_mm",
            "70",
            "45",
        )

    def _accept_preview(self):
        self.direct_print = False
        self._save_defaults()
        self.accept()

    def _accept_direct(self):
        self.direct_print = True
        self._save_defaults()
        self.accept()

    @classmethod
    def get_options(cls, db, parent=None, profile="document", title=None):
        dialog = cls(db, parent=parent, profile=profile, title=title)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        return dialog if accepted else None
