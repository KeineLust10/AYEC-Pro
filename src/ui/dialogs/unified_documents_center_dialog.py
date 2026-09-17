# -*- coding: utf-8 -*-

import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_info

logger = logging.getLogger(__name__)


class UnifiedDocumentsCenterDialog(ModernDialog):
    def __init__(self, db, partner=None, parent=None):
        self.db = db
        self.partner = self._partner_to_dict(partner)
        super().__init__("Belge Merkezi", parent, width=980, height=760)
        self._ensure_tables()
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

    def _ensure_tables(self):
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
        document_columns = {row[1] for row in (self.db.cursor.fetchall() or [])}
        for column_name, column_sql in (
            ("partner_id", "INTEGER DEFAULT 0"),
            ("shipment_id", "INTEGER"),
            ("title", "TEXT DEFAULT ''"),
            ("category", "TEXT"),
            ("file_path", "TEXT DEFAULT ''"),
            ("added_at", "TEXT DEFAULT ''"),
        ):
            if column_name not in document_columns:
                self.db.cursor.execute(
                    f"ALTER TABLE partner_documents ADD COLUMN {column_name} {column_sql}"
                )

        self.db.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS partner_shipments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id INTEGER NOT NULL,
                partner_name TEXT NOT NULL,
                product_name TEXT,
                sent_at TEXT,
                created_at TEXT
            )
            """
        )
        self.db.cursor.execute("PRAGMA table_info(partner_shipments)")
        shipment_columns = {row[1] for row in (self.db.cursor.fetchall() or [])}
        for column_name, column_sql in (
            ("partner_id", "INTEGER DEFAULT 0"),
            ("partner_name", "TEXT DEFAULT ''"),
            ("product_name", "TEXT"),
            ("currency", "TEXT DEFAULT 'TRY'"),
            ("sent_at", "TEXT"),
            ("created_at", "TEXT"),
        ):
            if column_name not in shipment_columns:
                self.db.cursor.execute(
                    f"ALTER TABLE partner_shipments ADD COLUMN {column_name} {column_sql}"
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

        title = QLabel("Birlesik Belge Merkezi")
        title.setStyleSheet(theme_qss("color: @text; font-size: 20px; font-weight: 800;"))
        subtitle = QLabel(
            "Partner belgeleri, shipment ve lojistik fotograflari, stok fotograflari "
            "ve dosya tabanli sozlesmeler tek merkezde listelenir."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(theme_qss("color: @text_muted;"))
        layout.addWidget(title)
        layout.addWidget(subtitle)

        actions = QHBoxLayout()
        self.btn_open = QPushButton("Ac")
        self.btn_refresh = QPushButton("Yenile")
        for btn in (self.btn_open, self.btn_refresh):
            btn.setFixedHeight(38)
            btn.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
            actions.addWidget(btn)
        actions.addStretch()
        layout.addLayout(actions)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Kaynak", "Baslik", "Kategori", "Sevk", "Yol", "Tarih"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        layout.addWidget(self.table)

        self.btn_open.clicked.connect(self.open_selected)
        self.btn_refresh.clicked.connect(self.load_rows)

        self.add_widget(card)
        self.add_cancel_button("Kapat")

    def load_rows(self):
        partner_id = self._partner_id()
        rows = []
        if partner_id:
            try:
                self.db.cursor.execute(
                    """
                    SELECT 'Partner Belgesi', title, COALESCE(category, ''), COALESCE(shipment_id, ''),
                           file_path, added_at
                    FROM partner_documents
                    WHERE partner_id = ?
                    """,
                    (partner_id,),
                )
                rows.extend(self.db.cursor.fetchall() or [])
            except Exception as exc:
                logger.debug("Partner belgeleri yuklenemedi: %s", exc)

            try:
                self.db.cursor.execute(
                    """
                    SELECT id, COALESCE(product_name, ''), COALESCE(sent_at, '')
                    FROM partner_shipments
                    WHERE partner_id = ?
                    """,
                    (partner_id,),
                )
                shipments = self.db.cursor.fetchall() or []
                for shipment_id, product_name, sent_at in shipments:
                    tracking_key = f"partner-{partner_id}-{shipment_id}"
                    self.db.cursor.execute(
                        """
                        SELECT 'Partner Fotograf', COALESCE(photo_label, ''), COALESCE(stage, ''),
                               ?, photo_path, COALESCE(created_at, '')
                        FROM photos
                        WHERE tracking_no LIKE ?
                        ORDER BY id DESC
                        """,
                        (shipment_id, f"{tracking_key}%"),
                    )
                    for source, label, stage, shipment_ref, path, created_at in (self.db.cursor.fetchall() or []):
                        title = label or product_name or f"Sevk #{shipment_id}"
                        rows.append((source, title, stage, shipment_ref, path, created_at or sent_at))
            except Exception as exc:
                logger.debug("Partner sevk fotograflari yuklenemedi: %s", exc)

        try:
            self.db.cursor.execute(
                """
                SELECT 'Lojistik Fotograf',
                       COALESCE(NULLIF(photo_label, ''), tracking_no),
                       COALESCE(stage, 'Fotograf'),
                       tracking_no,
                       photo_path,
                       COALESCE(created_at, '')
                FROM photos
                WHERE tracking_no NOT LIKE 'partner-%'
                ORDER BY id DESC
                """
            )
            rows.extend(self.db.cursor.fetchall() or [])
        except Exception as exc:
            logger.debug("Lojistik fotograflar yuklenemedi: %s", exc)

        try:
            self.db.cursor.execute(
                """
                SELECT 'Stok Fotograf',
                       COALESCE(NULLIF(name, ''), code, id),
                       COALESCE(category, 'Stok'),
                       id,
                       photo_path,
                       COALESCE(created_at, '')
                FROM parts
                WHERE COALESCE(photo_path, '') <> ''
                """
            )
            rows.extend(self.db.cursor.fetchall() or [])
        except Exception as exc:
            logger.debug("Stok fotograflari yuklenemedi: %s", exc)

        try:
            self.db.cursor.execute(
                """
                SELECT 'Proje Sozlesmesi',
                       COALESCE(name, 'Proje'),
                       'Sozlesme',
                       id,
                       contract_path,
                       COALESCE(created_at, '')
                FROM projects
                WHERE COALESCE(contract_path, '') <> ''
                """
            )
            for source, title, category, ref_id, path, created_at in (self.db.cursor.fetchall() or []):
                full_path = path
                if full_path and not os.path.isabs(full_path):
                    full_path = os.path.join(os.getcwd(), full_path)
                rows.append((source, title, category, ref_id, full_path, created_at))
        except Exception as exc:
            logger.debug("Proje sozlesmeleri yuklenemedi: %s", exc)

        try:
            self.db.cursor.execute(
                """
                SELECT 'Sozlesme Eki',
                       COALESCE(filename, 'Ek'),
                       'Sozlesme Eki',
                       contract_id,
                       file_path,
                       COALESCE(created_at, '')
                FROM contract_attachments
                """
            )
            rows.extend(self.db.cursor.fetchall() or [])
        except Exception as exc:
            logger.debug("Sozlesme ekleri yuklenemedi: %s", exc)

        rows.sort(key=lambda row: str(row[5] or ""), reverse=True)
        self.table.setRowCount(0)
        for row_idx, row in enumerate(rows):
            self.table.insertRow(row_idx)
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value if value not in (None, "") else "-"))
                if col_idx in (0, 3, 5):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_idx, col_idx, item)
        self.table.resizeColumnsToContents()

    def open_selected(self):
        row = self.table.currentRow()
        if row < 0:
            show_info(self, "Acmak icin bir kayit secin.")
            return
        path_item = self.table.item(row, 4)
        file_path = path_item.text() if path_item else ""
        if not file_path or file_path == "-" or not os.path.exists(file_path):
            show_error(self, "Dosya bulunamadi.")
            return
        os.startfile(file_path)
