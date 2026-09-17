from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.dialogs.quick_notes_editor import QuickNotesEditor
from src.utils.theme_colors import theme_qss


class ReportTemplatesPage(QWidget):
    PAGE_SIZE = 10

    def __init__(self, db, main_window=None):
        super().__init__(main_window)
        self.db = db
        self.main_window = main_window
        self.current_page = 1
        self.total_count = 0
        self._rows = []
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(12)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Rapor C\u00fcmle Kal\u0131plar\u0131")
        title.setStyleSheet(
            theme_qss("font-size: 22px; font-weight: 800; color: @text;")
        )
        description = QLabel(
            "Servis kay\u0131tlar\u0131nda kullan\u0131lan haz\u0131r "
            "ar\u0131za, i\u015flem ve rapor c\u00fcmlelerini y\u00f6netin."
        )
        description.setStyleSheet(theme_qss("color: @text_muted;"))
        title_box.addWidget(title)
        title_box.addWidget(description)
        header.addLayout(title_box)
        header.addStretch()
        manage_button = QPushButton("Kal\u0131plar\u0131 Y\u00f6net")
        manage_button.clicked.connect(self.open_editor)
        header.addWidget(manage_button)
        root.addLayout(header)

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Kategori veya c\u00fcmle ara...")
        self.search.textChanged.connect(self._search_changed)
        refresh_button = QPushButton("Yenile")
        refresh_button.clicked.connect(self.refresh_data)
        search_row.addWidget(self.search, 1)
        search_row.addWidget(refresh_button)
        root.addLayout(search_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Kategori", "C\u00fcmle Kal\u0131b\u0131", "Durum", "S\u0131ra"]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        root.addWidget(self.table, 1)

        footer = QHBoxLayout()
        self.lbl_info = QLabel("")
        footer.addWidget(self.lbl_info)
        footer.addStretch()
        self.btn_previous = QPushButton("\u00d6nceki")
        self.lbl_page = QLabel("1 / 1")
        self.btn_next = QPushButton("Sonraki")
        self.btn_previous.clicked.connect(self.previous_page)
        self.btn_next.clicked.connect(self.next_page)
        footer.addWidget(self.btn_previous)
        footer.addWidget(self.lbl_page)
        footer.addWidget(self.btn_next)
        root.addLayout(footer)

    @staticmethod
    def _value(row, key, index, default=""):
        if isinstance(row, dict):
            return row.get(key, default)
        if hasattr(row, "keys") and key in row.keys():
            return row[key]
        try:
            return row[index]
        except (IndexError, TypeError):
            return default

    def refresh_data(self):
        try:
            rows = list(self.db.get_fast_notes() or [])
        except Exception:
            rows = []
        self._rows = [
            {
                "id": self._value(row, "id", 0),
                "category": self._value(row, "category", 1),
                "label": self._value(row, "label", 2),
                "is_active": self._value(row, "is_active", 3, 1),
                "display_order": self._value(row, "display_order", 4, 0),
            }
            for row in rows
        ]
        self._render()

    def _filtered_rows(self):
        query = self.search.text().strip().lower()
        if not query:
            return list(self._rows)
        return [
            row
            for row in self._rows
            if query in str(row["category"]).lower()
            or query in str(row["label"]).lower()
        ]

    def _render(self):
        rows = self._filtered_rows()
        self.total_count = len(rows)
        total_pages = max(1, (self.total_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.current_page = min(max(1, self.current_page), total_pages)
        start = (self.current_page - 1) * self.PAGE_SIZE
        page_rows = rows[start:start + self.PAGE_SIZE]
        self.table.setRowCount(len(page_rows))
        for index, row in enumerate(page_rows):
            self.table.setItem(index, 0, QTableWidgetItem(str(row["category"] or "")))
            self.table.setItem(index, 1, QTableWidgetItem(str(row["label"] or "")))
            status = "Aktif" if bool(row["is_active"]) else "Pasif"
            self.table.setItem(index, 2, QTableWidgetItem(status))
            order_item = QTableWidgetItem(str(row["display_order"] or 0))
            order_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(index, 3, order_item)
        first = start + 1 if self.total_count else 0
        last = min(start + len(page_rows), self.total_count)
        self.lbl_info.setText(
            f"{self.total_count} kay\u0131ttan {first} - {last} aras\u0131 g\u00f6steriliyor."
        )
        self.lbl_page.setText(f"{self.current_page} / {total_pages}")
        self.btn_previous.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)

    def _search_changed(self):
        self.current_page = 1
        self._render()

    def previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._render()

    def next_page(self):
        total_pages = max(1, (self.total_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        if self.current_page < total_pages:
            self.current_page += 1
            self._render()

    def open_editor(self):
        editor = QuickNotesEditor(
            self.db,
            self,
            initial_category="\u0130\u015flem Detay\u0131",
        )
        editor.exec()
        self.refresh_data()
