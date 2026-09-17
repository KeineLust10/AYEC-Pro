from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.language_manager import LanguageManager
from src.utils.message_helper import show_error, show_warning
from src.utils.theme_colors import theme_qss


class LabelEditorDialog(ModernDialog):
    def __init__(self, current_category=None, parent=None):
        super().__init__(title="UI Metin Editoru", parent=parent, width=800, height=600)
        self.category = current_category
        self.lang_manager = LanguageManager()
        self.set_footer_visible(False)
        self.init_ui()

    def init_ui(self):
        layout = self.content_layout
        header = QHBoxLayout()
        icon = QLabel("Etiket")
        icon.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title = QLabel("Arayuz Isimlerini Duzenle")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.addWidget(icon)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        info = QLabel("Burada degistirdiginiz metinler tum program genelinde aninda guncellenir.")
        info.setStyleSheet(theme_qss("color: @text_muted; margin-bottom: 10px;"))
        layout.addWidget(info)

        filter_layout = QHBoxLayout()
        self.cmb_filter = QComboBox()
        self.cmb_filter.addItem("Tumu")
        if self.category:
            self.cmb_filter.addItem(f"Bu Sayfa ({self.category})")
        self.cmb_filter.currentTextChanged.connect(self.load_data)
        filter_layout.addWidget(QLabel("Filtre:"))
        filter_layout.addWidget(self.cmb_filter)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Ara...")
        self.txt_search.textChanged.connect(self.load_data)
        filter_layout.addWidget(self.txt_search)
        layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Kod", "Varsayilan", "Gorunen Isim", "Kategori", "Islemler"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_close = QPushButton("Kapat")
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        self.load_data()

    def load_data(self):
        self.table.setRowCount(0)
        search_text = self.txt_search.text().lower()
        filter_mode = self.cmb_filter.currentText()
        if not self.lang_manager.db:
            show_warning(self, "Hata", "Veritabanı bağlantısı yok.")
            return
        target_cat = self.category if "Bu Sayfa" in filter_mode else None
        labels = self.lang_manager.db.get_label_details(target_cat)
        for item in labels:
            if search_text and search_text not in item["default"].lower() and search_text not in (item["current"] or "").lower():
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(item["key"]))
            self.table.setItem(row, 1, QTableWidgetItem(item["default"]))
            txt_edit = QLineEdit(item["current"] if item["current"] else "")
            txt_edit.setPlaceholderText(item["default"])
            self.table.setCellWidget(row, 2, txt_edit)
            self.table.setItem(row, 3, QTableWidgetItem(item["category"]))

            btn_save = QPushButton("Kaydet")
            btn_save.setFixedWidth(60)
            btn_save.clicked.connect(lambda _, k=item["key"], t=txt_edit: self.save_label(k, t.text()))
            btn_reset = QPushButton("Sifirla")
            btn_reset.setFixedWidth(60)
            btn_reset.clicked.connect(lambda _, k=item["key"]: self.reset_label(k))
            action_widget = QWidget()
            h = QHBoxLayout(action_widget)
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(btn_save)
            h.addWidget(btn_reset)
            self.table.setCellWidget(row, 4, action_widget)

    def save_label(self, key, new_text):
        if not new_text.strip():
            self.reset_label(key)
            return
        if not self.lang_manager.update_label(key, new_text):
            show_error(self, "Hata", "Güncellenemedi.")

    def reset_label(self, key):
        if self.lang_manager.db.reset_label(key):
            self.lang_manager.reload_labels()
            self.load_data()
