# -*- coding: utf-8 -*-

"""Dialogs extracted from modern_login_window for modularity."""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
                             QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QStackedWidget,
                             QCheckBox, QApplication, QScrollArea, QProgressBar,
                             QFormLayout, QTextEdit, QInputDialog, QTableWidget, QTableWidgetItem,
                             QHeaderView, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QSize, QThread, QUrl, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush, QPainterPath, QPixmap, QAction, QDesktopServices, QKeySequence, QShortcut

from src.utils.theme_colors import theme_qss, qc, tc
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.auth_manager import AuthManager
from src.utils.security_manager import SecurityManager
from src.ui.dialogs.license_keygen_dialog import LicenseKeygenDialog
from src.utils.design_system import DesignTokens
import sys
import shutil
from datetime import datetime
import os
import ctypes
import re
from src.ui.widgets.modern_dialog import ModernDialog

class DeletedRecordsDialog(ModernDialog):
    def __init__(self, db, on_scan=None, on_restore=None, parent=None):
        super().__init__(title="Silinen Kayıtlar", parent=parent, width=760, height=460)
        self.db = db
        self.on_scan = on_scan
        self.on_restore = on_restore
        self.set_footer_visible(False)

        shell = QFrame()
        shell.setStyleSheet(theme_qss("background: @window; border: 1px solid @border; border-radius: 16px;"))
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(18, 18, 18, 18)
        shell_layout.setSpacing(12)

        title = QLabel("SİLİNEN KAYITLAR")
        title.setStyleSheet(theme_qss("color: @warning; font-size: 16px; font-weight: 700;"))
        subtitle = QLabel("Gizli kayıtları listele ve geri yükle")
        subtitle.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
        shell_layout.addWidget(title)
        shell_layout.addWidget(subtitle)

        type_row = QHBoxLayout()
        type_label = QLabel("Kayıt Türü")
        type_label.setStyleSheet(theme_qss("color: @text; font-size: 12px; font-weight: 600;"))
        self.cmb_record = QComboBox()
        self.cmb_record.addItems([
            "Tümü",
            "Cihazlar",
            "Kullanıcılar",
            "Müşteriler",
            "Banka Hesapları",
            "Stok Ürünleri",
            "Hizmetler",
            "Finans Kayıtları",
            "Stok Hareketleri",
            "Randevular",
            "Hatırlatıcılar",
            "Duyurular"
        ])
        self.cmb_record.setFixedHeight(30)
        self.cmb_record.setStyleSheet(theme_qss("""
            QComboBox {
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 4px 10px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: @surface;
                color: @text;
                selection-background-color: @accent;
                selection-color: @selection_text;
                border: 1px solid @border;
                outline: 0;
            }
        """))
        type_row.addWidget(type_label)
        type_row.addStretch()
        type_row.addWidget(self.cmb_record)
        shell_layout.addLayout(type_row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Takip No", "Müşteri", "Cihaz", "Durum", "Tarih"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(theme_qss("""
            QTableWidget {
                background: @surface_alt;
                color: @text;
                gridline-color: @border;
                border: 1px solid @border;
                border-radius: 10px;
            }
            QHeaderView::section {
                background: @surface;
                color: @text_muted;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                background: @accent;
                color: @selection_text;
            }
        """))
        shell_layout.addWidget(self.table)

        btns = QHBoxLayout()
        btn_refresh = QPushButton("Yenile")
        btn_restore_all = QPushButton("Tümünü Geri Yükle")
        btn_restore = QPushButton("Geri Yükle")
        btn_close = QPushButton("Kapat")
        for b in (btn_refresh, btn_restore_all, btn_restore, btn_close):
            b.setFixedHeight(34)
            
        btn_refresh.setStyleSheet(theme_qss("""
            QPushButton {
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 10px;
                padding: 0 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: @border;
            }
        """))
        btn_restore_all.setStyleSheet(theme_qss("""
            QPushButton {
                background: @danger;
                color: @selection_text;
                border: none;
                border-radius: 10px;
                padding: 0 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: @danger_bg;
            }
        """))
        btn_restore.setStyleSheet(theme_qss("""
            QPushButton {
                background: @warning;
                color: @selection_text;
                border: none;
                border-radius: 10px;
                padding: 0 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: @warning_bg;
            }
        """))
        btn_close.setStyleSheet(theme_qss("""
            QPushButton {
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 10px;
                padding: 0 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: @border;
            }
        """))
        btn_close.clicked.connect(self.reject)
        btn_refresh.clicked.connect(self.load_data)
        btn_restore.clicked.connect(self.restore_selected)
        btn_restore_all.clicked.connect(self.restore_all)
        btns.addWidget(btn_refresh)
        btns.addWidget(btn_restore_all)
        btns.addWidget(btn_restore)
        btns.addStretch()
        btns.addWidget(btn_close)
        shell_layout.addLayout(btns)

        root_layout = self.content_layout
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.addWidget(shell)

        self._device_deleted_col = None
        self._device_date_col = None
        self._user_active_col = None
        self._user_deleted_col = None
        self._user_date_col = None
        self._customer_deleted_col = None
        self._customer_date_col = None
        self._bank_deleted_col = None
        self._bank_date_col = None
        self._part_deleted_col = None
        self._service_deleted_col = None
        self._service_date_col = None
        self._accounting_deleted_col = None
        self._accounting_date_col = None
        self._stock_movement_deleted_col = None
        self._stock_movement_date_col = None
        self._appointment_deleted_col = None
        self._appointment_date_col = None
        self._reminder_deleted_col = None
        self._reminder_date_col = None
        self._announcement_deleted_col = None
        self._announcement_date_col = None
        self._init_columns()
        self.cmb_record.currentTextChanged.connect(self.load_data)
        self.load_data()

    def _safe_identifier(self, name):
        text = str(name or "").strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text):
            raise ValueError(f"Invalid identifier: {name}")
        return text

    def _init_columns(self):
        try:
            self.db.cursor.execute("PRAGMA table_info(devices)")
            cols = [row[1] for row in self.db.cursor.fetchall()]
            if self.on_scan:
                self.on_scan(0, f"Kolonlar tespit edildi: {', '.join(cols[:10])}..." if len(cols) > 10 else f"Kolonlar: {', '.join(cols)}")
        except Exception as e:
            cols = []
            if self.on_scan:
                self.on_scan(0, f"Kolon tespiti başarısız: {e}")
        if "is_deleted" in cols:
            self._device_deleted_col = "is_deleted"
        elif "is_archived" in cols:
            self._device_deleted_col = "is_archived"
        else:
            self._device_deleted_col = None
            if self.on_scan:
                self.on_scan(0, "UYARI: devices tablosunda is_deleted veya is_archived yok!")
        if "deleted_at" in cols:
            self._device_date_col = "deleted_at"
        elif "exit_date" in cols:
            self._device_date_col = "exit_date"
        elif "entry_date" in cols:
            self._device_date_col = "entry_date"

        try:
            self.db.cursor.execute("PRAGMA table_info(users)")
            ucols = [row[1] for row in self.db.cursor.fetchall()]
        except Exception:
            ucols = []
        if "active" in ucols:
            self._user_active_col = "active"
        elif "is_active" in ucols:
            self._user_active_col = "is_active"
        if "is_deleted" in ucols:
            self._user_deleted_col = "is_deleted"
        elif "is_archived" in ucols:
            self._user_deleted_col = "is_archived"
        if "deleted_at" in ucols:
            self._user_date_col = "deleted_at"
        elif "created_at" in ucols:
            self._user_date_col = "created_at"

        try:
            self.db.cursor.execute("PRAGMA table_info(customers)")
            ccols = [row[1] for row in self.db.cursor.fetchall()]
        except Exception:
            ccols = []
        if "is_deleted" in ccols:
            self._customer_deleted_col = "is_deleted"
        elif "is_archived" in ccols:
            self._customer_deleted_col = "is_archived"
        if "deleted_at" in ccols:
            self._customer_date_col = "deleted_at"
        elif "created_at" in ccols:
            self._customer_date_col = "created_at"

        try:
            self.db.cursor.execute("PRAGMA table_info(bank_accounts)")
            bcols = [row[1] for row in self.db.cursor.fetchall()]
        except Exception:
            bcols = []
        if "is_deleted" in bcols:
            self._bank_deleted_col = "is_deleted"
        elif "is_archived" in bcols:
            self._bank_deleted_col = "is_archived"
        if "deleted_at" in bcols:
            self._bank_date_col = "deleted_at"
        elif "created_at" in bcols:
            self._bank_date_col = "created_at"

        try:
            self.db.cursor.execute("PRAGMA table_info(parts)")
            pcols = [row[1] for row in self.db.cursor.fetchall()]
        except Exception:
            pcols = []
        if "is_deleted" in pcols:
            self._part_deleted_col = "is_deleted"
        elif "is_archived" in pcols:
            self._part_deleted_col = "is_archived"

        try:
            self.db.cursor.execute("PRAGMA table_info(appointments)")
            acols = [row[1] for row in self.db.cursor.fetchall()]
        except Exception:
            acols = []
        if "is_deleted" in acols:
            self._appointment_deleted_col = "is_deleted"
        elif "is_archived" in acols:
            self._appointment_deleted_col = "is_archived"
        if "deleted_at" in acols:
            self._appointment_date_col = "deleted_at"
        elif "date" in acols:
            self._appointment_date_col = "date"

        try:
            self.db.cursor.execute("PRAGMA table_info(reminders)")
            rcols = [row[1] for row in self.db.cursor.fetchall()]
        except Exception:
            rcols = []
        if "is_deleted" in rcols:
            self._reminder_deleted_col = "is_deleted"
        elif "is_archived" in rcols:
            self._reminder_deleted_col = "is_archived"
        if "deleted_at" in rcols:
            self._reminder_date_col = "deleted_at"
        elif "date" in rcols:
            self._reminder_date_col = "date"

        try:
            self.db.cursor.execute("PRAGMA table_info(announcements)")
            accols = [row[1] for row in self.db.cursor.fetchall()]
        except Exception:
            accols = []
        if "is_deleted" in accols:
            self._announcement_deleted_col = "is_deleted"
        elif "is_archived" in accols:
            self._announcement_deleted_col = "is_archived"
        if "deleted_at" in accols:
            self._announcement_date_col = "deleted_at"
        elif "date" in accols:
            self._announcement_date_col = "date"

        try:
            self.db.cursor.execute("PRAGMA table_info(services)")
            svcols = [row[1] for row in self.db.cursor.fetchall()]
        except Exception:
            svcols = []
        if "is_deleted" in svcols:
            self._service_deleted_col = "is_deleted"
        elif "is_archived" in svcols:
            self._service_deleted_col = "is_archived"
        if "deleted_at" in svcols:
            self._service_date_col = "deleted_at"
        elif "created_at" in svcols:
            self._service_date_col = "created_at"

        try:
            self.db.cursor.execute("PRAGMA table_info(accounting)")
            actcols = [row[1] for row in self.db.cursor.fetchall()]
        except Exception:
            actcols = []
        if "is_deleted" in actcols:
            self._accounting_deleted_col = "is_deleted"
        elif "is_archived" in actcols:
            self._accounting_deleted_col = "is_archived"
        if "deleted_at" in actcols:
            self._accounting_date_col = "deleted_at"
        elif "date" in actcols:
            self._accounting_date_col = "date"

        try:
            self.db.cursor.execute("PRAGMA table_info(stock_movements)")
            smcols = [row[1] for row in self.db.cursor.fetchall()]
        except Exception:
            smcols = []
        if "is_deleted" in smcols:
            self._stock_movement_deleted_col = "is_deleted"
        elif "is_archived" in smcols:
            self._stock_movement_deleted_col = "is_archived"
        if "deleted_at" in smcols:
            self._stock_movement_date_col = "deleted_at"
        elif "created_at" in smcols:
            self._stock_movement_date_col = "created_at"

    def _set_table_headers(self, headers):
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

    def load_data(self):
        self.table.setRowCount(0)
        record_type = self.cmb_record.currentText() if self.cmb_record else "Cihazlar"
        if record_type == "Tümü":
            self._set_table_headers(["Bilgi"])
            info_item = QTableWidgetItem("Tüm veritabanındaki silinmiş kayıtları toplu geri yüklemek için 'Tümünü Geri Yükle' butonunu kullanın.")
            self.table.insertRow(0)
            self.table.setItem(0, 0, info_item)
        elif record_type == "Kullanıcılar":
            self._load_users()
        elif record_type == "Müşteriler":
            self._load_customers()
        elif record_type == "Banka Hesapları":
            self._load_bank_accounts()
        elif record_type == "Stok Ürünleri":
            self._load_parts()
        elif record_type == "Hizmetler":
            self._load_services()
        elif record_type == "Finans Kayıtları":
            self._load_accounting()
        elif record_type == "Stok Hareketleri":
            self._load_stock_movements()
        elif record_type == "Randevular":
            self._load_appointments()
        elif record_type == "Hatırlatıcılar":
            self._load_reminders()
        elif record_type == "Duyurular":
            self._load_announcements()
        else:
            self._load_devices()

    def _load_bank_accounts(self):
        self._set_table_headers(["ID", "Banka", "Şube", "Hesap Adı", "IBAN", "Tarih"])
        if not self._bank_deleted_col:
            if self.on_scan:
                self.on_scan(0, "Silinme alanı bulunamadı (bank_accounts.is_deleted/is_archived).")
            return
        date_col = self._safe_identifier(self._bank_date_col or "created_at")
        deleted_col = self._safe_identifier(self._bank_deleted_col)
        query = (
            "SELECT id, bank_name, branch_name, account_name, iban, {date_col} "
            "FROM bank_accounts WHERE {deleted_col}=1"
        ).format(date_col=date_col, deleted_col=deleted_col)
        try:
            if self.on_scan:
                self.on_scan(0, f"Query: {query}")
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall() or []
            if self.on_scan:
                self.on_scan(len(rows), f"Query başarılı: {len(rows)} kayıt bulundu.")
        except Exception as e:
            rows = []
            if self.on_scan:
                self.on_scan(0, f"Query hatası: {str(e)}")
        for i, row in enumerate(rows):
            self.table.insertRow(i)
            try:
                rid = row["id"]
                bank_name = row["bank_name"]
                branch_name = row.get("branch_name", "")
                acc_name = row.get("account_name", "")
                iban = row.get("iban", "")
                date_val = row[date_col]
            except Exception:
                rid, bank_name, branch_name, acc_name, iban, date_val = row
            values = [
                str(rid),
                str(bank_name or ""),
                str(branch_name or ""),
                str(acc_name or ""),
                str(iban or ""),
                str(date_val or "")
            ]
            for c, v in enumerate(values):
                self.table.setItem(i, c, QTableWidgetItem(v))

    def _load_parts(self):
        self._set_table_headers(["ID", "Ürün", "Stok", "Fiyat", "Kategori"])
        if not self._part_deleted_col:
            if self.on_scan:
                self.on_scan(0, "Silinme alanı bulunamadı (parts.is_deleted/is_archived).")
            return
        deleted_col = self._safe_identifier(self._part_deleted_col)
        query = "SELECT id, name, stock, price, category FROM parts WHERE {deleted_col}=1".format(
            deleted_col=deleted_col
        )
        try:
            if self.on_scan:
                self.on_scan(0, f"Query: {query}")
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall() or []
            if self.on_scan:
                self.on_scan(len(rows), f"Query başarılı: {len(rows)} kayıt bulundu.")
        except Exception as e:
            rows = []
            if self.on_scan:
                self.on_scan(0, f"Query hatası: {str(e)}")
        for i, row in enumerate(rows):
            self.table.insertRow(i)
            try:
                rid = row["id"]
                name = row["name"]
                stock = row["stock"]
                price = row["price"]
                category = row.get("category", "")
            except Exception:
                rid, name, stock, price, category = row
            values = [
                str(rid),
                str(name or ""),
                str(stock or ""),
                str(price or ""),
                str(category or "")
            ]
            for c, v in enumerate(values):
                self.table.setItem(i, c, QTableWidgetItem(v))

    def _load_services(self):
        self._set_table_headers(["ID", "Hizmet Adı", "Fiyat", "Açıklama", "Barkod", "Tarih"])
        if not self._service_deleted_col:
            if self.on_scan:
                self.on_scan(0, "Silinme alanı bulunamadı (services.is_deleted/is_archived).")
            return
        date_col = self._safe_identifier(self._service_date_col or "created_at")
        deleted_col = self._safe_identifier(self._service_deleted_col)
        query = (
            "SELECT id, name, price, description, barcode, {date_col} "
            "FROM services WHERE {deleted_col}=1"
        ).format(date_col=date_col, deleted_col=deleted_col)
        try:
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall() or []
        except Exception as e:
            rows = []
            if self.on_scan:
                self.on_scan(0, f"Query hatası: {str(e)}")
        for i, row in enumerate(rows):
            self.table.insertRow(i)
            try:
                rid = row["id"]
                name = row["name"]
                price = row["price"]
                desc = row.get("description", "")
                barcode = row.get("barcode", "")
                date_val = row[date_col]
            except Exception:
                rid, name, price, desc, barcode, date_val = row
            values = [
                str(rid), str(name or ""), str(price or ""),
                str(desc or ""), str(barcode or ""), str(date_val or "")
            ]
            for c, v in enumerate(values):
                self.table.setItem(i, c, QTableWidgetItem(v))

    def _load_accounting(self):
        self._set_table_headers(["ID", "Tür", "Kategori", "Tutar", "Açıklama", "Tarih"])
        if not self._accounting_deleted_col:
            if self.on_scan:
                self.on_scan(0, "Silinme alanı bulunamadı (accounting.is_deleted/is_archived).")
            return
        date_col = self._safe_identifier(self._accounting_date_col or "date")
        deleted_col = self._safe_identifier(self._accounting_deleted_col)
        query = (
            "SELECT id, type, category, amount, description, {date_col} "
            "FROM accounting WHERE {deleted_col}=1"
        ).format(date_col=date_col, deleted_col=deleted_col)
        try:
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall() or []
        except Exception as e:
            rows = []
            if self.on_scan:
                self.on_scan(0, f"Query hatası: {str(e)}")
        for i, row in enumerate(rows):
            self.table.insertRow(i)
            try:
                rid = row["id"]
                t_type = row["type"]
                category = row["category"]
                amount = row["amount"]
                desc = row["description"]
                date_val = row[date_col]
            except Exception:
                rid, t_type, category, amount, desc, date_val = row
            values = [
                str(rid), str(t_type or ""), str(category or ""),
                str(amount or ""), str(desc or ""), str(date_val or "")
            ]
            for c, v in enumerate(values):
                self.table.setItem(i, c, QTableWidgetItem(v))

    def _load_stock_movements(self):
        self._set_table_headers(["ID", "Parça ID", "Hareket Tipi", "Miktar", "Açıklama", "Tarih"])
        if not self._stock_movement_deleted_col:
            if self.on_scan:
                self.on_scan(0, "Silinme alanı bulunamadı (stock_movements.is_deleted/is_archived).")
            return
        date_col = self._safe_identifier(self._stock_movement_date_col or "created_at")
        deleted_col = self._safe_identifier(self._stock_movement_deleted_col)
        query = (
            "SELECT id, part_id, movement_type, amount, description, {date_col} "
            "FROM stock_movements WHERE {deleted_col}=1"
        ).format(date_col=date_col, deleted_col=deleted_col)
        try:
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall() or []
        except Exception as e:
            rows = []
            if self.on_scan:
                self.on_scan(0, f"Query hatası: {str(e)}")
        for i, row in enumerate(rows):
            self.table.insertRow(i)
            try:
                rid = row["id"]
                part_id = row["part_id"]
                move_type = row["movement_type"]
                amount = row["amount"]
                desc = row["description"]
                date_val = row[date_col]
            except Exception:
                rid, part_id, move_type, amount, desc, date_val = row
            values = [
                str(rid), str(part_id or ""), str(move_type or ""),
                str(amount or ""), str(desc or ""), str(date_val or "")
            ]
            for c, v in enumerate(values):
                self.table.setItem(i, c, QTableWidgetItem(v))

    def _load_appointments(self):
        self._set_table_headers(["ID", "Müşteri", "Telefon", "Tarih", "Saat", "Durum"])
        if not self._appointment_deleted_col:
            if self.on_scan:
                self.on_scan(0, "Silinme alanı bulunamadı (appointments.is_deleted/is_archived).")
            return
        date_col = self._safe_identifier(self._appointment_date_col or "date")
        deleted_col = self._safe_identifier(self._appointment_deleted_col)
        query = (
            "SELECT id, customer_name, phone, {date_col}, time, status "
            "FROM appointments WHERE {deleted_col}=1"
        ).format(date_col=date_col, deleted_col=deleted_col)
        try:
            if self.on_scan:
                self.on_scan(0, f"Query: {query}")
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall() or []
            if self.on_scan:
                self.on_scan(len(rows), f"Query başarılı: {len(rows)} kayıt bulundu.")
        except Exception as e:
            rows = []
            if self.on_scan:
                self.on_scan(0, f"Query hatası: {str(e)}")
        for i, row in enumerate(rows):
            self.table.insertRow(i)
            try:
                rid = row["id"]
                cname = row["customer_name"]
                phone = row.get("phone", "")
                date_val = row[date_col]
                time_val = row["time"]
                status = row["status"]
            except Exception:
                rid, cname, phone, date_val, time_val, status = row
            values = [
                str(rid),
                str(cname or ""),
                str(phone or ""),
                str(date_val or ""),
                str(time_val or ""),
                str(status or "")
            ]
            for c, v in enumerate(values):
                self.table.setItem(i, c, QTableWidgetItem(v))

    def _load_reminders(self):
        self._set_table_headers(["ID", "Mesaj", "Tarih", "Okundu", "Takip No", "Oluşturma"])
        if not self._reminder_deleted_col:
            if self.on_scan:
                self.on_scan(0, "Silinme alanı bulunamadı (reminders.is_deleted/is_archived).")
            return
        date_col = self._safe_identifier(self._reminder_date_col or "date")
        deleted_col = self._safe_identifier(self._reminder_deleted_col)
        query = (
            "SELECT id, message, {date_col}, is_read, tracking_no, created_at "
            "FROM reminders WHERE {deleted_col}=1"
        ).format(date_col=date_col, deleted_col=deleted_col)
        try:
            if self.on_scan:
                self.on_scan(0, f"Query: {query}")
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall() or []
            if self.on_scan:
                self.on_scan(len(rows), f"Query başarılı: {len(rows)} kayıt bulundu.")
        except Exception as e:
            rows = []
            if self.on_scan:
                self.on_scan(0, f"Query hatası: {str(e)}")
        for i, row in enumerate(rows):
            self.table.insertRow(i)
            try:
                rid = row["id"]
                msg = row["message"]
                date_val = row[date_col]
                is_read = row["is_read"]
                tracking_no = row.get("tracking_no", "")
                created_at = row.get("created_at", "")
            except Exception:
                rid, msg, date_val, is_read, tracking_no, created_at = row
            values = [
                str(rid),
                str(msg or ""),
                str(date_val or ""),
                "Evet" if int(is_read or 0) else "Hayır",
                str(tracking_no or ""),
                str(created_at or "")
            ]
            for c, v in enumerate(values):
                self.table.setItem(i, c, QTableWidgetItem(v))

    def _load_announcements(self):
        self._set_table_headers(["ID", "Tarih", "Öncelik", "Başlık", "Yazar"])
        if not self._announcement_deleted_col:
            if self.on_scan:
                self.on_scan(0, "Silinme alanı bulunamadı (announcements.is_deleted/is_archived).")
            return
        date_col = self._safe_identifier(self._announcement_date_col or "date")
        deleted_col = self._safe_identifier(self._announcement_deleted_col)
        query = (
            "SELECT id, {date_col}, priority, title, author "
            "FROM announcements WHERE {deleted_col}=1"
        ).format(date_col=date_col, deleted_col=deleted_col)
        try:
            if self.on_scan:
                self.on_scan(0, f"Query: {query}")
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall() or []
            if self.on_scan:
                self.on_scan(len(rows), f"Query başarılı: {len(rows)} kayıt bulundu.")
        except Exception as e:
            rows = []
            if self.on_scan:
                self.on_scan(0, f"Query hatası: {str(e)}")
        for i, row in enumerate(rows):
            self.table.insertRow(i)
            try:
                rid = row["id"]
                date_val = row[date_col]
                priority = row["priority"]
                title = row["title"]
                author = row.get("author", "")
            except Exception:
                rid, date_val, priority, title, author = row
            values = [
                str(rid),
                str(date_val or ""),
                str(priority or ""),
                str(title or ""),
                str(author or "")
            ]
            for c, v in enumerate(values):
                self.table.setItem(i, c, QTableWidgetItem(v))

    def _load_devices(self):
        self._set_table_headers(["ID", "Takip No", "Müşteri", "Cihaz", "Durum", "Tarih"])
        if not self._device_deleted_col:
            if self.on_scan:
                self.on_scan(0, "Silinme alanı bulunamadı (devices.is_deleted/is_archived).")
            return
        date_col = self._safe_identifier(self._device_date_col or "entry_date")
        deleted_col = self._safe_identifier(self._device_deleted_col)
        query = (
            "SELECT id, tracking_no, customer_name, device_brand, device_model, status, {date_col} "
            "FROM devices WHERE {deleted_col}=1"
        ).format(date_col=date_col, deleted_col=deleted_col)
        try:
            if self.on_scan:
                self.on_scan(0, f"Query: {query}")
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall() or []
            if self.on_scan:
                self.on_scan(len(rows), f"Query başarılı: {len(rows)} kayıt bulundu.")
        except Exception as e:
            rows = []
            if self.on_scan:
                self.on_scan(0, f"Query hatası: {str(e)}")
        for i, row in enumerate(rows):
            self.table.insertRow(i)
            try:
                rid = row["id"]
                tracking = row["tracking_no"]
                customer = row["customer_name"]
                brand = row["device_brand"]
                model = row["device_model"]
                status = row["status"]
                date_val = row[date_col]
            except Exception:
                rid, tracking, customer, brand, model, status, date_val = row
            device_name = f"{brand or ''} {model or ''}".strip()
            values = [
                str(rid),
                str(tracking or ""),
                str(customer or ""),
                device_name,
                str(status or ""),
                str(date_val or "")
            ]
            for c, v in enumerate(values):
                self.table.setItem(i, c, QTableWidgetItem(v))

    def _load_users(self):
        self._set_table_headers(["ID", "Kullanıcı", "Ad Soyad", "Rol", "E-posta", "Tarih"])
        if not self._user_active_col and not self._user_deleted_col:
            if self.on_scan:
                self.on_scan(0, "Silinme alanı bulunamadı (users.active/is_active/is_deleted).")
            return
        date_col = self._safe_identifier(self._user_date_col or "created_at")
        if self._user_deleted_col:
            where_sql = "{column}=1".format(
                column=self._safe_identifier(self._user_deleted_col)
            )
        else:
            where_sql = "COALESCE({column}, 1)=0".format(
                column=self._safe_identifier(self._user_active_col)
            )
        query = (
            "SELECT id, username, full_name, role, email, {date_col} "
            "FROM users WHERE {where_sql}"
        ).format(date_col=date_col, where_sql=where_sql)
        try:
            if self.on_scan:
                self.on_scan(0, f"Query: {query}")
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall() or []
            if self.on_scan:
                self.on_scan(len(rows), f"Query başarılı: {len(rows)} kayıt bulundu.")
        except Exception as e:
            rows = []
            if self.on_scan:
                self.on_scan(0, f"Query hatası: {str(e)}")
        for i, row in enumerate(rows):
            self.table.insertRow(i)
            try:
                rid = row["id"]
                username = row["username"]
                full_name = row["full_name"]
                role = row["role"]
                email = row["email"]
                date_val = row[date_col]
            except Exception:
                rid, username, full_name, role, email, date_val = row
            values = [
                str(rid),
                str(username or ""),
                str(full_name or ""),
                str(role or ""),
                str(email or ""),
                str(date_val or "")
            ]
            for c, v in enumerate(values):
                self.table.setItem(i, c, QTableWidgetItem(v))

    def _load_customers(self):
        self._set_table_headers(["ID", "Ad", "Telefon", "E-posta", "Tip", "Tarih"])
        if not self._customer_deleted_col:
            if self.on_scan:
                self.on_scan(0, "Silinme alanı bulunamadı (customers.is_deleted/is_archived).")
            return
        date_col = self._safe_identifier(self._customer_date_col or "created_at")
        deleted_col = self._safe_identifier(self._customer_deleted_col)
        query = (
            "SELECT id, name, phone, email, type, {date_col} "
            "FROM customers WHERE {deleted_col}=1"
        ).format(date_col=date_col, deleted_col=deleted_col)
        try:
            if self.on_scan:
                self.on_scan(0, f"Query: {query}")
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall() or []
            if self.on_scan:
                self.on_scan(len(rows), f"Query başarılı: {len(rows)} kayıt bulundu.")
        except Exception as e:
            rows = []
            if self.on_scan:
                self.on_scan(0, f"Query hatası: {str(e)}")
        for i, row in enumerate(rows):
            self.table.insertRow(i)
            try:
                rid = row["id"]
                name = row["name"]
                phone = row["phone"]
                email = row["email"]
                ctype = row["type"]
                date_val = row[date_col]
            except Exception:
                rid, name, phone, email, ctype, date_val = row
            values = [
                str(rid),
                str(name or ""),
                str(phone or ""),
                str(email or ""),
                str(ctype or ""),
                str(date_val or "")
            ]
            for c, v in enumerate(values):
                self.table.setItem(i, c, QTableWidgetItem(v))

    def restore_selected(self):
        row = self.table.currentRow()
        if row < 0:
            show_warning(self, "Lütfen bir kayıt seçin.")
            return
        item = self.table.item(row, 0)
        if not item:
            show_warning(self, "Geçerli bir kayıt seçin.")
            return
        record_id = item.text()
        try:
            record_type = self.cmb_record.currentText() if self.cmb_record else "Cihazlar"
            if record_type == "Tümü":
                show_warning(self, "Tek bir kayıt yerine 'Tümünü Geri Yükle' butonunu kullanın.")
                return
            if record_type == "Kullanıcılar":
                if self._user_deleted_col:
                    self.db.cursor.execute(
                        "UPDATE users SET {column}=0 WHERE id=?".format(
                            column=self._safe_identifier(self._user_deleted_col)
                        ),
                        (record_id,),
                    )
                elif self._user_active_col:
                    self.db.cursor.execute(
                        "UPDATE users SET {column}=1 WHERE id=?".format(
                            column=self._safe_identifier(self._user_active_col)
                        ),
                        (record_id,),
                    )
                if self._user_date_col == "deleted_at":
                    self.db.cursor.execute("UPDATE users SET deleted_at=NULL WHERE id=?", (record_id,))
                self.db.conn.commit()
                if self.on_restore:
                    username = self.table.item(row, 1).text()
                    self.on_restore(record_id, username)
                self.load_data()
            elif record_type == "Müşteriler":
                if not self._customer_deleted_col:
                    show_warning(self, "Silinme alanı bulunamadı.")
                    return
                self.db.cursor.execute(
                    "UPDATE customers SET {column}=0 WHERE id=?".format(
                        column=self._safe_identifier(self._customer_deleted_col)
                    ),
                    (record_id,),
                )
                if self._customer_date_col == "deleted_at":
                    self.db.cursor.execute("UPDATE customers SET deleted_at=NULL WHERE id=?", (record_id,))
                self.db.conn.commit()
                if self.on_restore:
                    name = self.table.item(row, 1).text()
                    self.on_restore(record_id, name)
                self.load_data()
            elif record_type == "Banka Hesapları":
                if not self._bank_deleted_col:
                    show_warning(self, "Silinme alanı bulunamadı.")
                    return
                if not self.db.restore_record("bank_accounts", "id", record_id):
                    show_error(self, "Geri yükleme başarısız.")
                    return
                if self.on_restore:
                    label = self.table.item(row, 1).text()
                    self.on_restore(record_id, label)
                self.load_data()
            elif record_type == "Stok Ürünleri":
                if not self._part_deleted_col:
                    show_warning(self, "Silinme alanı bulunamadı.")
                    return
                if not self.db.restore_record("parts", "id", record_id):
                    show_error(self, "Geri yükleme başarısız.")
                    return
                self.load_data()
            elif record_type == "Hizmetler":
                if not self._service_deleted_col:
                    show_warning(self, "Silinme alanı bulunamadı.")
                    return
                if not self.db.restore_record("services", "id", record_id):
                    show_error(self, "Geri yükleme başarısız.")
                    return
                self.load_data()
            elif record_type == "Finans Kayıtları":
                if not self._accounting_deleted_col:
                    show_warning(self, "Silinme alanı bulunamadı.")
                    return
                if not self.db.restore_record("accounting", "id", record_id):
                    show_error(self, "Geri yükleme başarısız.")
                    return
                self.load_data()
            elif record_type == "Stok Hareketleri":
                if not self._stock_movement_deleted_col:
                    show_warning(self, "Silinme alanı bulunamadı.")
                    return
                if not self.db.restore_record("stock_movements", "id", record_id):
                    show_error(self, "Geri yükleme başarısız.")
                    return
                self.load_data()
            elif record_type == "Randevular":
                if not self._appointment_deleted_col:
                    show_warning(self, "Silinme alanı bulunamadı.")
                    return
                if not self.db.restore_record("appointments", "id", record_id):
                    show_error(self, "Geri yükleme başarısız.")
                    return
                self.load_data()
            elif record_type == "Hatırlatıcılar":
                if not self._reminder_deleted_col:
                    show_warning(self, "Silinme alanı bulunamadı.")
                    return
                if not self.db.restore_record("reminders", "id", record_id):
                    show_error(self, "Geri yükleme başarısız.")
                    return
                self.load_data()
            elif record_type == "Duyurular":
                if not self._announcement_deleted_col:
                    show_warning(self, "Silinme alanı bulunamadı.")
                    return
                if not self.db.restore_record("announcements", "id", record_id):
                    show_error(self, "Geri yükleme başarısız.")
                    return
                self.load_data()
            else:
                if not self._device_deleted_col:
                    show_warning(self, "Silinme alanı bulunamadı.")
                    return
                self.db.cursor.execute(
                    "UPDATE devices SET {column}=0 WHERE id=?".format(
                        column=self._safe_identifier(self._device_deleted_col)
                    ),
                    (record_id,),
                )
                self.db.conn.commit()
                if self.on_restore:
                    tracking = self.table.item(row, 1).text()
                    self.on_restore(record_id, tracking)
                self.load_data()
        except Exception as e:
            show_error(self, f"Hata: {e}")

    def restore_all(self):
        from src.utils.message_helper import show_question
        reply = show_question(
            self,
            "Onay",
            "Tüm modüllerde silinmiş durumdaki kayıtlar geri yüklenecek. Devam etmek istiyor musunuz?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            summary = self.db.restore_all_soft_deleted() or {}
            total = sum(summary.values())
            if total <= 0:
                show_warning(self, "Geri yüklenecek silinmiş kayıt bulunamadı.")
            else:
                show_success(self, f"Toplam {total} kayıt geri yüklendi.")
            self.load_data()
        except Exception as e:
            show_error(self, f"Toplu geri yükleme hatası: {e}")
