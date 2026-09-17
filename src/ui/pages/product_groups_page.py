import html
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
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

from src.ui.dialogs.modern_input_dialog import ModernInputDialog
from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import (
    show_error,
    show_info,
    show_success,
    show_warning,
)


class ProductGroupsPage(QWidget):
    PAGE_SIZE = 10

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.current_page = 0
        self.total_count = 0
        self._ensure_schema()
        self._seed_existing_groups()
        self._build_ui()
        self.load_data()

    def _ensure_schema(self):
        self.db.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS product_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        self.db.conn.commit()

    def _seed_existing_groups(self):
        names = set()
        for query in (
            """
            SELECT DISTINCT device_type
            FROM device_brands
            WHERE TRIM(COALESCE(device_type, '')) <> ''
            """,
            """
            SELECT DISTINCT device_type
            FROM devices
            WHERE TRIM(COALESCE(device_type, '')) <> ''
            """,
        ):
            try:
                self.db.cursor.execute(query)
                names.update(
                    str(row[0]).strip()
                    for row in (self.db.cursor.fetchall() or [])
                    if row[0]
                )
            except Exception:
                continue
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for name in sorted(names):
            self.db.cursor.execute(
                """
                INSERT OR IGNORE INTO product_groups (
                    name, is_active, created_at, updated_at
                )
                VALUES (?, 1, ?, ?)
                """,
                (name, now, now),
            )
        self.db.conn.commit()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("\u00dcr\u00fcn Grubu Y\u00f6netimi")
        title.setStyleSheet(
            theme_qss("font-size: 24px; font-weight: 800; color: @text;")
        )
        subtitle = QLabel(
            "Servis kay\u0131tlar\u0131nda kullan\u0131lacak cihaz ve "
            "\u00fcr\u00fcn gruplar\u0131n\u0131 y\u00f6netin."
        )
        subtitle.setStyleSheet(
            theme_qss("font-size: 12px; color: @text_muted;")
        )
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        btn_add = QPushButton("Yeni \u00dcr\u00fcn Grubu")
        btn_add.setStyleSheet(
            theme_qss(DesignTokens.get_button_qss("primary"))
        )
        btn_add.clicked.connect(self.add_group)
        header.addWidget(btn_add)
        root.addLayout(header)

        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("\u00dcr\u00fcn grubu ara...")
        self.search.setStyleSheet(
            theme_qss(DesignTokens.get_input_qss())
        )
        self.search.textChanged.connect(self._reset_and_load)
        toolbar.addWidget(self.search, 1)
        for label, callback in (
            ("Excel \u00c7\u0131kt\u0131", self.export_excel),
            ("PDF Kaydet", self.export_pdf),
            ("Yazd\u0131r", self.print_list),
        ):
            button = QPushButton(label)
            button.setStyleSheet(
                theme_qss(DesignTokens.get_button_qss("secondary"))
            )
            button.clicked.connect(callback)
            toolbar.addWidget(button)
        root.addLayout(toolbar)

        card = QFrame()
        card.setStyleSheet(
            theme_qss(DesignTokens.get_card_qss(hover=False))
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            [
                "\u00dcr\u00fcn Grubu",
                "Durum",
                "D\u00fczenle",
                "Sil",
            ]
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )
        for column in (1, 2, 3):
            self.table.horizontalHeader().setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )
        self.table.setStyleSheet(
            theme_qss(DesignTokens.get_table_qss())
        )
        card_layout.addWidget(self.table)
        root.addWidget(card, 1)

        footer = QHBoxLayout()
        self.count_label = QLabel()
        footer.addWidget(self.count_label)
        footer.addStretch()
        self.btn_previous = QPushButton("\u00d6nceki")
        self.btn_previous.clicked.connect(self.previous_page)
        self.page_label = QLabel()
        self.btn_next = QPushButton("Sonraki")
        self.btn_next.clicked.connect(self.next_page)
        page_button_qss = theme_qss(
            """
            QPushButton {
                min-width: 86px;
                min-height: 32px;
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                font-weight: 700;
                padding: 4px 10px;
            }
            QPushButton:hover {
                border-color: @accent;
                background: @surface;
            }
            QPushButton:disabled {
                background: @surface;
                color: @text_muted;
                border-color: @border;
            }
            """
        )
        self.btn_previous.setStyleSheet(page_button_qss)
        self.btn_next.setStyleSheet(page_button_qss)
        footer.addWidget(self.btn_previous)
        footer.addWidget(self.page_label)
        footer.addWidget(self.btn_next)
        root.addLayout(footer)

    def _reset_and_load(self):
        self.current_page = 0
        self.load_data()

    def _where_clause(self):
        query = self.search.text().strip()
        if not query:
            return "", []
        return "WHERE name LIKE ?", [f"%{query}%"]

    def load_data(self):
        where_sql, params = self._where_clause()
        self.db.cursor.execute(
            f"SELECT COUNT(*) FROM product_groups {where_sql}",
            tuple(params),
        )
        self.total_count = int(self.db.cursor.fetchone()[0] or 0)
        max_page = max(0, (self.total_count - 1) // self.PAGE_SIZE)
        self.current_page = min(self.current_page, max_page)
        offset = self.current_page * self.PAGE_SIZE
        self.db.cursor.execute(
            f"""
            SELECT id, name, is_active
            FROM product_groups
            {where_sql}
            ORDER BY name COLLATE NOCASE
            LIMIT ? OFFSET ?
            """,
            tuple(params + [self.PAGE_SIZE, offset]),
        )
        rows = self.db.cursor.fetchall() or []
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            group_id = int(row[0])
            name = str(row[1] or "")
            active = bool(row[2])
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.ItemDataRole.UserRole, group_id)
            self.table.setItem(row_index, 0, name_item)
            self.table.setItem(
                row_index,
                1,
                QTableWidgetItem(
                    "Aktif" if active else "Pasif"
                ),
            )
            btn_edit = QPushButton("D\u00fczenle")
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setMinimumWidth(88)
            btn_edit.setFixedHeight(30)
            btn_edit.setStyleSheet(
                theme_qss(DesignTokens.get_button_qss("secondary", size="sm"))
            )
            btn_edit.clicked.connect(
                lambda _checked=False, gid=group_id, value=name: (
                    self.edit_group(gid, value)
                )
            )
            self.table.setCellWidget(row_index, 2, btn_edit)
            btn_delete = QPushButton("Sil")
            btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_delete.setMinimumWidth(72)
            btn_delete.setFixedHeight(30)
            btn_delete.setStyleSheet(
                theme_qss(DesignTokens.get_button_qss("destructive", size="sm"))
            )
            btn_delete.clicked.connect(
                lambda _checked=False, gid=group_id, value=name: (
                    self.delete_group(gid, value)
                )
            )
            self.table.setCellWidget(row_index, 3, btn_delete)
        self.table.setSortingEnabled(True)
        start = offset + 1 if self.total_count else 0
        end = min(offset + len(rows), self.total_count)
        self.count_label.setText(
            f"{self.total_count} kay\u0131ttan {start}-{end} "
            "aras\u0131 g\u00f6steriliyor."
        )
        self.page_label.setText(
            f"{self.current_page + 1} / {max_page + 1}"
        )
        self.btn_previous.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < max_page)

    def add_group(self):
        name, accepted = ModernInputDialog.get_text(
            self,
            "Yeni \u00dcr\u00fcn Grubu",
            "\u00dcr\u00fcn grubu ad\u0131:",
        )
        if not accepted:
            return
        name = str(name or "").strip()
        if not name:
            show_warning(self, "Grup ad\u0131 bo\u015f olamaz.")
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.db.cursor.execute(
                """
                INSERT INTO product_groups (
                    name, is_active, created_at, updated_at
                )
                VALUES (?, 1, ?, ?)
                """,
                (name, now, now),
            )
            self.db.conn.commit()
            self.load_data()
            show_success(self, "\u00dcr\u00fcn grubu eklendi.")
        except Exception as exc:
            show_error(self, f"Kay\u0131t eklenemedi: {exc}")

    def edit_group(self, group_id, current_name):
        name, accepted = ModernInputDialog.get_text(
            self,
            "\u00dcr\u00fcn Grubunu D\u00fczenle",
            "\u00dcr\u00fcn grubu ad\u0131:",
            current_name,
        )
        if not accepted:
            return
        name = str(name or "").strip()
        if not name:
            show_warning(self, "Grup ad\u0131 bo\u015f olamaz.")
            return
        try:
            self.db.cursor.execute(
                "UPDATE product_groups SET name=?, updated_at=? WHERE id=?",
                (
                    name,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    group_id,
                ),
            )
            self.db.cursor.execute(
                """
                UPDATE device_brands
                SET device_type=?
                WHERE device_type=?
                """,
                (name, current_name),
            )
            self.db.conn.commit()
            self.load_data()
            show_info(self, "\u00dcr\u00fcn grubu g\u00fcncellendi.")
        except Exception as exc:
            self.db.conn.rollback()
            show_error(self, f"Kay\u0131t g\u00fcncellenemedi: {exc}")

    def delete_group(self, group_id, name):
        dialog = SimpleConfirmDialog(
            self,
            title="\u00dcr\u00fcn Grubunu Sil",
            text=f"'{name}' \u00fcr\u00fcn grubu silinsin mi?",
        )
        if not dialog.exec():
            return
        try:
            self.db.cursor.execute(
                "DELETE FROM product_groups WHERE id=?",
                (group_id,),
            )
            self.db.conn.commit()
            self.load_data()
            show_success(self, "\u00dcr\u00fcn grubu silindi.")
        except Exception as exc:
            self.db.conn.rollback()
            show_error(self, f"Kay\u0131t silinemedi: {exc}")

    def previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_data()

    def next_page(self):
        if (self.current_page + 1) * self.PAGE_SIZE < self.total_count:
            self.current_page += 1
            self.load_data()

    def _all_names(self):
        where_sql, params = self._where_clause()
        self.db.cursor.execute(
            f"""
            SELECT name, is_active
            FROM product_groups
            {where_sql}
            ORDER BY name COLLATE NOCASE
            """,
            tuple(params),
        )
        return [
            (str(row[0] or ""), "Aktif" if row[1] else "Pasif")
            for row in (self.db.cursor.fetchall() or [])
        ]

    def export_excel(self):
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "Excel \u00c7\u0131kt\u0131",
            "urun_gruplari.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            from openpyxl import Workbook

            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Urun Gruplari"
            sheet.append(["Urun Grubu", "Durum"])
            for row in self._all_names():
                sheet.append(list(row))
            workbook.save(path)
            show_success(self, f"Excel kaydedildi: {path}")
        except Exception as exc:
            show_error(self, f"Excel olusturulamadi: {exc}")

    def _html_document(self):
        rows = "".join(
            "<tr><td>{}</td><td>{}</td></tr>".format(
                html.escape(name),
                html.escape(status),
            )
            for name, status in self._all_names()
        )
        return (
            "<h2>Urun Grubu Yonetimi</h2>"
            "<table border='1' cellspacing='0' cellpadding='6' "
            "width='100%'><tr><th>Urun Grubu</th><th>Durum</th></tr>"
            f"{rows}</table>"
        )

    def export_pdf(self):
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "PDF Kaydet",
            "urun_gruplari.pdf",
            "PDF (*.pdf)",
        )
        if not path:
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(Path(path)))
        document = QTextDocument()
        document.setHtml(self._html_document())
        document.print(printer)
        show_success(self, f"PDF kaydedildi: {path}")

    def print_list(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if not dialog.exec():
            return
        document = QTextDocument()
        document.setHtml(self._html_document())
        document.print(printer)
