# -*- coding: utf-8 -*-

import html
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QComboBox,
    QAbstractItemView,
    QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter

from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.utils.toast_notification import show_success, show_error


class BrandsPage(QWidget):
    PAGE_SIZE = 100

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.current_page = 0
        self.total_count = 0
        self.init_schema()
        self.init_ui()
        self.load_data()

    def init_schema(self):
        try:
            # Table creation is now handled globally in src/database.py
            if hasattr(self.db, 'create_device_brands_table'):
                self.db.create_device_brands_table()
        except Exception as e:
            from src.utils.logger import logger
            logger.debug(f"BrandsPage local schema init skipped: {e}")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(18)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("📱 Cihaz Bilgisi & Markalar")
        lbl_title.setStyleSheet(theme_qss(
            f"font-size: 22px; font-weight: 800; color: {DesignTokens.PRIMARY};"
        ))
        lbl_sub = QLabel(
            "Servis formu ve Teknisyen Panelinde kullanılacak cihaz türü ve marka listesini buradan yönetin."
        )
        lbl_sub.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;"))
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box)
        header.addStretch()

        btn_catalog = QPushButton("Web Katalogunu Guncelle")
        btn_catalog.setFixedHeight(40)
        btn_catalog.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_catalog.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_catalog.clicked.connect(self.refresh_reviewed_catalog)
        header.addWidget(btn_catalog)

        btn_add = QPushButton("✨ Yeni Marka / Cihaz Türü")
        btn_add.setFixedHeight(40)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_add.clicked.connect(self.open_add_dialog)
        header.addWidget(btn_add)

        layout.addLayout(header)

        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Cihaz türü veya marka ara...")
        self.inp_search.setFixedHeight(36)
        self.inp_search.textChanged.connect(self._reset_and_filter)
        search_row.addWidget(self.inp_search, 1)
        self.cmb_group = QComboBox()
        self.cmb_group.setMinimumWidth(210)
        self.cmb_group.setFixedHeight(36)
        self.cmb_group.currentTextChanged.connect(self._reset_and_filter)
        search_row.addWidget(QLabel("\u00dcr\u00fcn Grubu:"))
        search_row.addWidget(self.cmb_group)
        for label, callback in (
            ("Excel \u00c7\u0131kt\u0131", self.export_excel),
            ("PDF Kaydet", self.export_pdf),
            ("Yazd\u0131r", self.print_list),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            search_row.addWidget(button)
        layout.addLayout(search_row)

        table_frame = QFrame()
        table_frame.setStyleSheet(theme_qss(DesignTokens.get_card_qss()))
        tlay = QVBoxLayout(table_frame)
        tlay.setContentsMargins(10, 10, 10, 10)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            [
                "\u00dcr\u00fcn Grubu",
                "Marka",
                "Durum",
                "D\u00fczenle",
                "Sil",
            ]
        )
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setHighlightSections(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setStyleSheet(theme_qss(
            """
            QTableWidget { border-radius: 10px; border: 1px solid @border; background: @surface; }
            QTableWidget:focus { outline: none; }
            QHeaderView::section { background-color: @surface_alt; color: @text; padding: 12px; font-weight: bold; border: none; }
            QTableWidget::item { padding: 8px; color: @text; border-bottom: 1px solid @surface_alt; }
            QTableWidget::item:hover { background-color: @selection_bg; color: @accent_pressed; }
            QTableWidget::item:selected { background-color: @accent; color: @selection_text; }
            QTableWidget::item:focus { outline: none; }
            """
        ))
        tlay.addWidget(self.table)
        layout.addWidget(table_frame)

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
        layout.addLayout(footer)

    def load_data(self):
        try:
            cur = self.db.cursor
            cur.execute(
                "SELECT device_type, brand, is_active FROM device_brands ORDER BY device_type, brand"
            )
            self._all_rows = cur.fetchall() or []
        except Exception:
            self._all_rows = []
        self._populate_group_filter()
        self.apply_filter()

    def refresh_reviewed_catalog(self):
        try:
            self.db.refresh_device_model_catalog()
            show_success(
                self,
                "Marka ve model kataloglari guncellendi.",
                "Bilgisayar, cep telefonu ve akilli ev secimleri Yeni Cihaz Ekle alaninda kullanilabilir.",
            )
            self.load_data()
        except Exception as exc:
            show_error(self, f"Katalog guncellenemedi: {exc}")

    def _populate_group_filter(self):
        selected = self.cmb_group.currentData()
        groups = sorted(
            {
                str(self._row_value(row, "device_type", 0) or "").strip()
                for row in self._all_rows
                if str(self._row_value(row, "device_type", 0) or "").strip()
            },
            key=str.casefold,
        )
        self.cmb_group.blockSignals(True)
        self.cmb_group.clear()
        self.cmb_group.addItem("T\u00fcm \u00dcr\u00fcn Gruplar\u0131", "")
        for group in groups:
            self.cmb_group.addItem(group, group)
        if selected:
            index = self.cmb_group.findData(selected)
            if index >= 0:
                self.cmb_group.setCurrentIndex(index)
        self.cmb_group.blockSignals(False)

    def _reset_and_filter(self):
        self.current_page = 0
        self.apply_filter()

    @staticmethod
    def _row_value(row, key, index):
        if hasattr(row, "keys"):
            return row[key]
        return row[index] if index < len(row) else None

    def _filtered_rows(self):
        text = (self.inp_search.text() or "").strip().casefold()
        selected_group = str(self.cmb_group.currentData() or "").casefold()
        rows = []
        for row in self._all_rows:
            device_type = str(
                self._row_value(row, "device_type", 0) or ""
            )
            brand = str(self._row_value(row, "brand", 1) or "")
            if selected_group and device_type.casefold() != selected_group:
                continue
            if text and text not in f"{device_type} {brand}".casefold():
                continue
            rows.append(row)
        return rows

    def apply_filter(self):
        rows = self._filtered_rows()
        self.total_count = len(rows)
        max_page = max(0, (self.total_count - 1) // self.PAGE_SIZE)
        self.current_page = min(self.current_page, max_page)
        offset = self.current_page * self.PAGE_SIZE
        page_rows = rows[offset:offset + self.PAGE_SIZE]
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for i, r in enumerate(page_rows):
            self.table.insertRow(i)
            device_type = str(
                self._row_value(r, "device_type", 0) or ""
            )
            brand = str(self._row_value(r, "brand", 1) or "")
            item_type = QTableWidgetItem(device_type)
            item_type.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            item_type.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(i, 0, item_type)

            item_brand = QTableWidgetItem(brand)
            item_brand.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.setItem(i, 1, item_brand)

            active = int(self._row_value(r, "is_active", 2) or 0)
            status_text = "Aktif" if active else "Pasif"
            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 2, item_status)

            btn_edit = QPushButton("D\u00fczenle")
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setFixedHeight(28)
            btn_edit.clicked.connect(
                lambda _checked=False, dt=device_type, br=brand: (
                    self.open_edit_dialog(dt, br)
                )
            )
            self.table.setCellWidget(i, 3, btn_edit)

            btn_delete = QPushButton("Sil")
            btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_delete.setFixedHeight(28)
            btn_delete.setStyleSheet(theme_qss(DesignTokens.get_button_qss("destructive", size="sm")))
            btn_delete.clicked.connect(
                lambda _checked=False, dt=device_type, br=brand: (
                    self.delete_row(dt, br)
                )
            )
            self.table.setCellWidget(i, 4, btn_delete)
        self.table.setSortingEnabled(True)
        start = offset + 1 if self.total_count else 0
        end = min(offset + len(page_rows), self.total_count)
        self.count_label.setText(
            f"{self.total_count} kay\u0131ttan {start}-{end} "
            "aras\u0131 g\u00f6steriliyor."
        )
        self.page_label.setText(
            f"{self.current_page + 1} / {max_page + 1}"
        )
        self.btn_previous.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < max_page)

    def open_add_dialog(self):
        from src.ui.dialogs.brand_edit_dialog import BrandEditDialog

        dlg = BrandEditDialog(self.db, self)
        if dlg.exec():
            show_success(self, "Marka kaydedildi.")
            self.load_data()

    def open_edit_dialog(self, device_type, brand):
        from src.ui.dialogs.brand_edit_dialog import BrandEditDialog

        dialog = BrandEditDialog(
            self.db,
            self,
            initial_device_type=device_type,
            initial_brand=brand,
            edit_mode=True,
        )
        if dialog.exec():
            show_success(self, "Marka g\u00fcncellendi.")
            self.load_data()

    def previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.apply_filter()

    def next_page(self):
        if (self.current_page + 1) * self.PAGE_SIZE < self.total_count:
            self.current_page += 1
            self.apply_filter()

    def _output_rows(self):
        return [
            (
                str(self._row_value(row, "device_type", 0) or ""),
                str(self._row_value(row, "brand", 1) or ""),
                (
                    "Aktif"
                    if int(self._row_value(row, "is_active", 2) or 0)
                    else "Pasif"
                ),
            )
            for row in self._filtered_rows()
        ]

    def export_excel(self):
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "Excel \u00c7\u0131kt\u0131",
            "markalar.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            from openpyxl import Workbook

            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Markalar"
            sheet.append(["Cihaz Turu", "Marka", "Durum"])
            for row in self._output_rows():
                sheet.append(list(row))
            workbook.save(path)
            show_success(self, f"Excel kaydedildi: {path}")
        except Exception as exc:
            show_error(self, f"Excel olusturulamadi: {exc}")

    def _html_document(self):
        rows = "".join(
            "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                html.escape(device_type),
                html.escape(brand),
                html.escape(status),
            )
            for device_type, brand, status in self._output_rows()
        )
        return (
            "<h2>Marka Adlari Yonetimi</h2>"
            "<table border='1' cellspacing='0' cellpadding='6' "
            "width='100%'><tr><th>Cihaz Turu</th><th>Marka</th>"
            f"<th>Durum</th></tr>{rows}</table>"
        )

    def export_pdf(self):
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "PDF Kaydet",
            "markalar.pdf",
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

    def delete_row(self, device_type, brand):
        try:
            self.db.cursor.execute(
                "DELETE FROM device_brands WHERE device_type=? AND brand=?",
                (device_type, brand),
            )
            self.db.conn.commit()
            show_success(self, "Kayıt silindi.")
            self.load_data()
        except Exception as e:
            show_error(self, f"Silme hatası: {e}")

