# -*- coding: utf-8 -*-

import os
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_info, show_success


class PartnerDocumentsDialog(ModernDialog):
    def __init__(self, db, partner, parent=None, shipment_id=None):
        self.db = db
        self.partner = self._partner_to_dict(partner)
        self.shipment_id = shipment_id
        super().__init__("Partner Belgeleri", parent, width=860, height=700)
        self._ensure_table()
        self._build_ui()
        self.load_rows()

    @staticmethod
    def _partner_to_dict(partner):
        if isinstance(partner, dict):
            return partner
        if hasattr(partner, "keys"):
            try:
                return {key: partner[key] for key in partner.keys()}
            except Exception:
                return {}
        return partner or {}

    def _ensure_table(self):
        self.db.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS partner_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id INTEGER NOT NULL,
                shipment_id INTEGER,
                title TEXT NOT NULL,
                category TEXT,
                file_path TEXT NOT NULL,
                added_at TEXT NOT NULL
            )
            """
        )
        self.db.cursor.execute("PRAGMA table_info(partner_documents)")
        existing = {row[1] for row in (self.db.cursor.fetchall() or [])}
        for column_name, column_sql in (
            ("partner_id", "INTEGER DEFAULT 0"),
            ("shipment_id", "INTEGER"),
            ("title", "TEXT DEFAULT ''"),
            ("category", "TEXT"),
            ("file_path", "TEXT DEFAULT ''"),
            ("added_at", "TEXT DEFAULT ''"),
        ):
            if column_name not in existing:
                self.db.cursor.execute(
                    f"ALTER TABLE partner_documents ADD COLUMN {column_name} {column_sql}"
                )
        self.db.conn.commit()

    def _partner_id(self):
        try:
            return int(self.partner.get("id") or 0)
        except Exception:
            return 0

    def _build_ui(self):
        card = QFrame()
        card.setStyleSheet(theme_qss(DesignTokens.get_card_qss()))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        info = QLabel("Sozlesme, teklif PDF, fatura, kargo fisleri ve diger partner dokumanlarini buradan yonetin.")
        info.setWordWrap(True)
        info.setStyleSheet(theme_qss("color: @text_muted;"))
        layout.addWidget(info)

        action_row = QHBoxLayout()
        self.btn_add = QPushButton("Belge Ekle")
        self.btn_open = QPushButton("Ac")
        self.btn_remove = QPushButton("Kaydi Sil")
        for btn in (self.btn_add, self.btn_open, self.btn_remove):
            btn.setFixedHeight(38)
            btn.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
            action_row.addWidget(btn)
        action_row.addStretch()
        layout.addLayout(action_row)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Baslik", "Kategori", "Dosya", "Eklenme"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        layout.addWidget(self.table)

        self.btn_add.clicked.connect(self.add_document)
        self.btn_open.clicked.connect(self.open_document)
        self.btn_remove.clicked.connect(self.remove_document)

        self.add_widget(card)
        self.add_cancel_button("Kapat")

    def load_rows(self):
        partner_id = self._partner_id()
        if self.shipment_id:
            self.db.cursor.execute(
                "SELECT id, title, COALESCE(category, ''), file_path, added_at FROM partner_documents WHERE partner_id = ? AND shipment_id = ? ORDER BY added_at DESC, id DESC",
                (partner_id, self.shipment_id),
            )
        else:
            self.db.cursor.execute(
                "SELECT id, title, COALESCE(category, ''), file_path, added_at FROM partner_documents WHERE partner_id = ? ORDER BY added_at DESC, id DESC",
                (partner_id,),
            )
        rows = self.db.cursor.fetchall() or []
        self.table.setRowCount(0)
        for row_idx, row in enumerate(rows):
            self.table.insertRow(row_idx)
            for col_idx, value in enumerate(row[1:]):
                item = QTableWidgetItem(str(value))
                if col_idx == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setData(Qt.ItemDataRole.UserRole, int(row[0]))
                self.table.setItem(row_idx, col_idx, item)
        self.table.resizeColumnsToContents()

    def add_document(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Belge Sec", "", "Tum Dosyalar (*.*)")
        if not file_path:
            return
        title = os.path.basename(file_path)
        category = "Sevk Belgesi" if self.shipment_id else "Partner Belgesi"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.db.cursor.execute(
                """
                INSERT INTO partner_documents (partner_id, shipment_id, title, category, file_path, added_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (self._partner_id(), self.shipment_id, title, category, file_path, now),
            )
            self.db.conn.commit()
            self.load_rows()
            show_success(self, "Belge eklendi.")
        except Exception as exc:
            show_error(self, f"Belge eklenemedi: {exc}")

    def _selected_row_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def open_document(self):
        row = self.table.currentRow()
        if row < 0:
            show_info(self, "Acmak icin bir belge secin.")
            return
        file_item = self.table.item(row, 2)
        file_path = file_item.text() if file_item else ""
        if not file_path or not os.path.exists(file_path):
            show_error(self, "Belge dosyasi bulunamadi.")
            return
        os.startfile(file_path)

    def remove_document(self):
        row_id = self._selected_row_id()
        if not row_id:
            show_info(self, "Silmek icin bir belge secin.")
            return
        try:
            self.db.cursor.execute("DELETE FROM partner_documents WHERE id = ?", (int(row_id),))
            self.db.conn.commit()
            self.load_rows()
            show_success(self, "Belge kaydi silindi.")
        except Exception as exc:
            show_error(self, f"Belge silinemedi: {exc}")
