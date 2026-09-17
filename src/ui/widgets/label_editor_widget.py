# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QHeaderView,
    QLineEdit,
    QComboBox,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from src.utils.theme_colors import theme_qss, qc
from src.utils.language_manager import LanguageManager
from src.ui.widgets.modern_dialog import ModernDialog


class _EditLabelDialog(ModernDialog):
    def __init__(self, key, value, parent=None):
        super().__init__(title="Menu Ismini Duzenle", parent=parent, width=420, height=170)
        self.setModal(True)
        self.set_footer_visible(False)

        lay = self.content_layout
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        lbl = QLabel(f"Anahtar: {key}")
        lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        lay.addWidget(lbl)

        self.input = QLineEdit(value)
        self.input.setPlaceholderText("Yeni menü ismini yazın...")
        self.input.setStyleSheet(theme_qss("background:@surface_alt; color:@text; border:1px solid @border; border-radius:8px; padding:8px;"))
        lay.addWidget(self.input)

        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_cancel = QPushButton("İptal")
        self.btn_ok = QPushButton("Tamam")
        self.btn_cancel.setStyleSheet(theme_qss("background:@surface_alt; color:@text; border:1px solid @border; border-radius:8px; padding:8px 14px;"))
        self.btn_ok.setStyleSheet(theme_qss("background:@accent; color:@selection_text; border:none; border-radius:8px; padding:8px 14px;"))
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self.accept)
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_ok)
        lay.addLayout(btns)


class LabelEditorWidget(QWidget):
    def __init__(self, page_context="Global", main_window=None, default_filter=None):
        super().__init__()
        self.main_window = main_window
        self.lang_manager = LanguageManager()
        self.page_context = page_context
        self.default_filter = default_filter
        self.items = []

        self.init_ui()
        self.load_labels()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        filter_box = QHBoxLayout()
        self.cmb_filter = QComboBox()
        self.cmb_filter.addItems(["Mevcut Sayfa", "Menüler", "Tümü (Global)"])
        self.cmb_filter.currentTextChanged.connect(self.load_labels)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Etiket Ara...")
        self.txt_search.textChanged.connect(self.filter_table)

        filter_box.addWidget(QLabel("Filtre:"))
        filter_box.addWidget(self.cmb_filter)
        filter_box.addWidget(self.txt_search)
        layout.addLayout(filter_box)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Anahtar (Key)", "Metin (Değer)", "İşlem"])
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setWordWrap(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 170)
        self.table.setColumnWidth(2, 90)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(theme_qss("""
            QTableWidget { border: 1px solid @border; border-radius: 6px; background: @surface; }
            QHeaderView::section { background-color: @surface_alt; border: none; padding: 6px; font-weight: bold; color: @text; }
            QTableWidget::item { color: @text; padding: 4px; }
        """))
        self.table.cellChanged.connect(self.on_cell_changed)
        layout.addWidget(self.table)

        if self.default_filter and self.default_filter in [self.cmb_filter.itemText(i) for i in range(self.cmb_filter.count())]:
            self.cmb_filter.blockSignals(True)
            self.cmb_filter.setCurrentText(self.default_filter)
            self.cmb_filter.blockSignals(False)

        inf = QLabel("İpucu: Kalem ile düzenleyebilir veya hücreyi doğrudan değiştirebilirsiniz.")
        inf.setStyleSheet(theme_qss("color: @text_muted; font-style: italic;"))
        layout.addWidget(inf)

    def set_current_page(self, page_name):
        self.page_context = page_name
        self.load_labels()

    def load_labels(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        filter_mode = self.cmb_filter.currentText()
        all_labels = self.lang_manager.db.get_all_labels()

        self.items = []
        for key, val in all_labels.items():
            if filter_mode == "Menüler":
                if not key.startswith("menu_"):
                    continue
                self.items.append((key, val))
                continue

            if filter_mode == "Mevcut Sayfa" and self.page_context != "Global":
                import re
                prefix = re.sub(r'(?<!^)(?=[A-Z])', '_', self.page_context).lower()
                if not key.startswith(prefix) and not key.startswith("common_"):
                    continue
            self.items.append((key, val))

        self.populate_table(self.items)
        self.table.blockSignals(False)

    def populate_table(self, data):
        self.table.setRowCount(len(data))
        for row, (key, val) in enumerate(data):
            k_item = QTableWidgetItem(key)
            k_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            k_item.setForeground(qc("text_muted"))
            self.table.setItem(row, 0, k_item)

            v_item = QTableWidgetItem(val)
            v_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 1, v_item)

            btn_edit = QPushButton("✏")
            btn_edit.setFixedSize(30, 24)
            btn_edit.setToolTip("Düzenle")
            btn_edit.setStyleSheet(theme_qss("background:@surface_alt; color:@text; border:1px solid @border; border-radius:6px;"))
            btn_edit.clicked.connect(lambda _, k=key, v=val: self.open_edit_dialog(k, v))

            btn_reset = QPushButton("↺")
            btn_reset.setFixedSize(30, 24)
            btn_reset.setToolTip("Varsayılan değere dön")
            btn_reset.setStyleSheet(theme_qss("background:@surface_alt; color:@text; border:1px solid @border; border-radius:6px;"))
            btn_reset.clicked.connect(lambda _, k=key: self.reset_label(k))

            action = QFrame()
            al = QHBoxLayout(action)
            al.setContentsMargins(0, 0, 0, 0)
            al.setSpacing(4)
            al.addWidget(btn_edit)
            al.addWidget(btn_reset)
            self.table.setCellWidget(row, 2, action)

    def filter_table(self, text):
        txt = text.lower().strip()
        rows = [(k, v) for k, v in self.items if txt in k.lower() or txt in str(v).lower()]
        self.table.blockSignals(True)
        self.populate_table(rows)
        self.table.blockSignals(False)

    def open_edit_dialog(self, key, current_value):
        dlg = _EditLabelDialog(key, current_value, self)
        if dlg.exec():
            new_val = dlg.input.text().strip()
            if new_val:
                self.lang_manager.update_label(key, new_val)
                self.load_labels()

    def on_cell_changed(self, row, col):
        # Inline edit kapalı; düzenleme kalem dialogu ile yapılır.
        return

    def reset_label(self, key):
        self.lang_manager.db.reset_label(key)
        self.lang_manager.reload_labels()
        self.load_labels()
