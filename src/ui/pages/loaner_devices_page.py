# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                             QTabWidget, QLineEdit, QFormLayout, QComboBox, QMessageBox,
                             QDateTimeEdit, QMenu, QAbstractItemView)
from PyQt6.QtCore import Qt, QDateTime, QTimer
from PyQt6.QtGui import QFont, QColor, QCursor
from PyQt6.QtCore import QThread, pyqtSignal
import sqlite3

from src.utils.theme_colors import tc, theme_qss
from src.utils.currency_helper import CurrencyHelper
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens
from src.utils.path_helper import PathHelper
from src.utils.logger import logger
from src.utils.message_helper import show_error, show_question, show_warning
from src.utils.system_config import SystemConfig


class LoanerDataWorker(QThread):
    loaded = pyqtSignal(list, list)
    error = pyqtSignal(str)

    def __init__(self, db_name="ayecpro.db"):
        super().__init__()
        self.db_name = db_name

    def run(self):
        try:
            db_path = PathHelper.get_db_path(self.db_name)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            inventory = cur.execute("SELECT * FROM loaner_devices ORDER BY id DESC").fetchall()
            active = cur.execute(
                """
                SELECT t.*, d.brand_model, d.daily_penalty_fee
                FROM loaner_transactions t
                JOIN loaner_devices d ON t.device_id = d.id
                WHERE t.status = 'Aktif'
                """
            ).fetchall()
            conn.close()
            self.loaded.emit(list(inventory), list(active))
        except (sqlite3.Error, OSError, RuntimeError) as e:
            self.error.emit(str(e))

class LoanerDevicesPage(QWidget):
    """
    Emanet (Konsinye) Cihaz Takip Modülü Ana Sayfası
    """
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.right_click_setting_key = "rc_loaner"
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.setup_ui()
        self._worker = None
        self._refresh_pending = False
        self._pending_inventory_rows = []
        self._pending_active_rows = []
        QTimer.singleShot(0, self._prepare_initial_view)
        QTimer.singleShot(140, self.request_refresh)

    def _prepare_initial_view(self):
        if hasattr(self, "table_inventory"):
            self.table_inventory.setRowCount(0)
        if hasattr(self, "table_active"):
            self.table_active.setRowCount(0)

    def setup_ui(self):
        # Header
        header_widget = QWidget()
        header_widget.setFixedHeight(80)
        header_widget.setStyleSheet(f"background-color: {tc('surface_alt')}; border-bottom: 1px solid {tc('border')};")
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(30, 0, 30, 0)
        
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title = QLabel("📱 Emanet (Konsinye) Cihazlar")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Light))
        title.setStyleSheet(f"color: {tc('text')};")
        
        subtitle = QLabel("Müşterilere verilen geçici (ikame) cihazların depo ve durum takibi.")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet(f"color: {tc('text_muted')};")
        
        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        title_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        self.btn_refresh = QPushButton("\U0001f504")
        self.btn_refresh.setFixedSize(40, 40)
        self.btn_refresh.setToolTip("Yenile")
        self.btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_refresh.setStyleSheet(theme_qss(
            DesignTokens.get_button_qss("secondary", size="sm")
        ))
        self.btn_refresh.setFont(QFont("Segoe UI", 16))
        self.btn_refresh.clicked.connect(self.request_refresh)
        header_layout.addWidget(self.btn_refresh)

        btn_add_device = QPushButton("\u2795")
        btn_add_device.setFixedSize(40, 40)
        btn_add_device.setToolTip("Yeni Cihaz Ekle")
        btn_add_device.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_add_device.setStyleSheet(theme_qss(
            DesignTokens.get_button_qss("success", size="sm")
        ))
        btn_add_device.setFont(QFont("Segoe UI", 16))
        btn_add_device.clicked.connect(self.add_new_device)
        header_layout.addWidget(btn_add_device)
        
        self.layout.addWidget(header_widget)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; border-top: 1px solid {tc('border')}; }}
            QTabBar::tab {{ 
                background: {tc('surface')}; 
                color: {tc('text_muted')}; 
                padding: 12px 25px; 
                font-size: 14px; 
                font-weight: 600;
                border: 1px solid {tc('border')};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{ 
                background: {tc('surface_alt')};
                color: {tc('primary')}; 
                border-bottom: 3px solid {tc('primary')};
            }}
            QTabBar::tab:hover {{ color: {tc('text')}; }}
        """)
        
        # Tab 1: Aktif Emanetler (Müşteride Olanlar)
        self.tab_active = QWidget()
        self.setup_active_tab()
        
        # Tab 2: Depo Envanteri (Tüm Cihazlar)
        self.tab_inventory = QWidget()
        self.setup_inventory_tab()
        
        self.tabs.addTab(self.tab_active, "Müşterideki Cihazlar (Aktif)")
        self.tabs.addTab(self.tab_inventory, "Emanet Cihaz Deposu")
        
        # Tab 3: Nasıl Kullanılır? (Usage Guide)
        if SystemConfig.is_feature_active(self.db, "usage_guides"):
            self.tab_guide = QWidget()
            self.setup_usage_guide_tab()
            self.tabs.addTab(self.tab_guide, "❓ Nasıl Kullanılır?")
        
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.addWidget(self.tabs)
        self.layout.addWidget(content_container)

    def setup_active_tab(self):
        ly = QVBoxLayout(self.tab_active)
        ly.setContentsMargins(0, 10, 0, 0)
        
        self.table_active = QTableWidget(0, 8)
        self.table_active.setHorizontalHeaderLabels([
            "İşlem ID", "Cihaz Marka/Model", "Teslim Alan", "Veriliş Tarihi", "Beklenen İade", "Geçen Süre", "Gecikme Cezası", "İşlemler"
        ])
        for table in [self.table_active]:
            self._configure_table(table)
            self._configure_active_columns(table)
        self.table_active.customContextMenuRequested.connect(self.open_active_context_menu)
        ly.addWidget(self.table_active)

    def setup_inventory_tab(self):
        ly = QVBoxLayout(self.tab_inventory)
        ly.setContentsMargins(0, 10, 0, 0)
        
        self.table_inventory = QTableWidget(0, 8)
        self.table_inventory.setHorizontalHeaderLabels([
            "ID", "Cihaz Tipi", "Marka/Model", "Seri/MAC", "Raf No", "Durum", "Günlük Ceza", "İşlemler"
        ])
        for table in [self.table_inventory]:
            self._configure_table(table)
            self._configure_inventory_columns(table)
        self.table_inventory.customContextMenuRequested.connect(self.open_inventory_context_menu)
        self.table_inventory.cellDoubleClicked.connect(self._handle_inventory_double_click)
        ly.addWidget(self.table_inventory)

    def _configure_table(self, table):
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.setAlternatingRowColors(True)
        table.setWordWrap(True)
        table.setTextElideMode(Qt.TextElideMode.ElideRight)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(62)
        table.verticalHeader().setMinimumSectionSize(56)
        table.setStyleSheet(theme_qss("""
            QTableWidget {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                gridline-color: @border;
                outline: none;
            }
            QTableWidget::item {
                padding: 8px 10px;
                border: none;
                outline: none;
            }
            QTableWidget::item:selected {
                background-color: @selection_bg;
                color: @selection_text;
                border: none;
                outline: none;
            }
            QHeaderView::section {
                background-color: @surface_alt;
                color: @text;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid @border;
                padding: 9px;
            }
            QPushButton {
                min-height: 30px;
                border-radius: 5px;
                padding: 5px 9px;
                font-weight: 700;
            }
        """))

    def _configure_active_columns(self, table):
        header = table.horizontalHeader()
        for col in range(table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(7, 150)

    def _configure_inventory_columns(self, table):
        header = table.horizontalHeader()
        for col in range(table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(7, 270)

    def _is_context_menu_enabled(self):
        if self.db.get_setting("enable_right_click", "1") == "0":
            return False
        return self.db.get_setting(self.right_click_setting_key, "1") == "1"

    def open_inventory_context_menu(self, position):
        if not self._is_context_menu_enabled():
            show_warning(self, "Hata", "Marka/Model ve Seri No alanları zorunludur.")
            return

        row = self.table_inventory.rowAt(position.y())
        menu = QMenu(self)
        menu.addAction("➕ Yeni Cihaz Ekle", self.add_new_device)
        menu.addAction("🔄 Yenile", self.refresh_data)

        if row >= 0:
            self.table_inventory.selectRow(row)
            dev_id_item = self.table_inventory.item(row, 0)
            status_item = self.table_inventory.item(row, 5)
            if dev_id_item:
                dev_id = dev_id_item.text().strip()
                status_text = status_item.text().strip() if status_item else ""
                menu.addSeparator()
                if status_text == "Depoda":
                    menu.addAction("📤 Cihazı Zimmetle", lambda did=dev_id: self.assign_device(did))
                menu.addAction("Düzenle", lambda did=dev_id: self.edit_device(did))
                menu.addAction("🗑️ Cihazı Sil", lambda did=dev_id: self.delete_device(did))

        menu.exec(self.table_inventory.viewport().mapToGlobal(position))

    def open_active_context_menu(self, position):
        if not self._is_context_menu_enabled():
            return

        row = self.table_active.rowAt(position.y())
        menu = QMenu(self)
        menu.addAction("🔄 Yenile", self.refresh_data)

        if row >= 0:
            self.table_active.selectRow(row)
            trans_id_item = self.table_active.item(row, 0)
            if trans_id_item:
                trans_id = trans_id_item.text().strip()
                try:
                    rec = self.db.cursor.execute(
                        "SELECT device_id FROM loaner_transactions WHERE id = ?",
                        (trans_id,)
                    ).fetchone()
                    if rec:
                        menu.addSeparator()
                        menu.addAction(
                            "📥 Cihazı İade Al",
                            lambda tid=trans_id, did=rec["device_id"]: self.return_device(tid, did)
                        )
                except (TypeError, ValueError, sqlite3.Error):
                    pass

        menu.exec(self.table_active.viewport().mapToGlobal(position))

    def _handle_inventory_double_click(self, row, column):
        if column == 7:
            return
        dev_id = self._inventory_device_id(row)
        if dev_id:
            self.edit_device(dev_id)

    def _inventory_device_id(self, row):
        if row < 0:
            return None
        item = self.table_inventory.item(row, 0)
        return item.text().strip() if item else None

    def request_refresh(self, delay_ms=0):
        if self._worker and self._worker.isRunning():
            self._refresh_pending = True
            return
        QTimer.singleShot(delay_ms, self.refresh_data)

    def refresh_data(self):
        if self._worker and self._worker.isRunning():
            self._refresh_pending = True
            return
        self.btn_refresh.setEnabled(False)
        self._worker = LoanerDataWorker(getattr(self.db, "_db_name", "ayecpro.db"))
        self._worker.loaded.connect(self._on_data_loaded)
        self._worker.error.connect(self._on_worker_error)
        self._worker.finished.connect(lambda: self.btn_refresh.setEnabled(True))
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_worker_error(self, err_msg):
        try:
            if self.main_window and hasattr(self.main_window, "show_notification"):
                self.main_window.show_notification(f"Emanet veri yükleme hatası: {err_msg}", "error")
        except (AttributeError, RuntimeError):
            pass

    def _on_worker_finished(self):
        self._worker = None
        if self._refresh_pending:
            self._refresh_pending = False
            QTimer.singleShot(0, self.refresh_data)

    def _on_data_loaded(self, inventory_rows, active_rows):
        self._pending_inventory_rows = list(inventory_rows or [])
        self._pending_active_rows = list(active_rows or [])
        # UI önce çizilsin, tablolar bir sonraki event turunda doldurulsun.
        QTimer.singleShot(0, self._load_inventory_deferred)
        QTimer.singleShot(0, self._load_active_deferred)

    def _load_inventory_deferred(self):
        self.load_inventory(self._pending_inventory_rows)

    def _load_active_deferred(self):
        self.load_active_loans(self._pending_active_rows)

    def load_inventory(self, records=None):
        self.table_inventory.setRowCount(0)
        try:
            if records is None:
                records = self.db.cursor.execute("SELECT * FROM loaner_devices ORDER BY id DESC").fetchall()
            for r in records:
                row = self.table_inventory.rowCount()
                self.table_inventory.insertRow(row)
                d_id = str(r['id'])
                dev_type = str(r['device_type'] or '')
                brand_model = str(r['brand_model'] or '')
                serial_mac = str(r['serial_mac'] or '')
                shelf_no = str(r['shelf_no'] or '')
                status = str(r['status'] or 'Depoda')
                penalty = str(r['daily_penalty_fee'] or '0.0')

                self.table_inventory.setItem(row, 0, QTableWidgetItem(d_id))
                self.table_inventory.setItem(row, 1, QTableWidgetItem(dev_type))
                self.table_inventory.setItem(row, 2, QTableWidgetItem(brand_model))
                self.table_inventory.setItem(row, 3, QTableWidgetItem(serial_mac))
                self.table_inventory.setItem(row, 4, QTableWidgetItem(shelf_no))
                
                status_item = QTableWidgetItem(status)
                if status == 'Depoda':
                    status_item.setForeground(QColor("#10B981"))
                elif status == 'Müşteride':
                    status_item.setForeground(QColor("#F59E0B"))
                else:
                    status_item.setForeground(QColor("#EF4444"))
                    
                self.table_inventory.setItem(row, 5, status_item)
                self.table_inventory.setItem(row, 6, QTableWidgetItem(f"{CurrencyHelper.format_try_for_display(penalty, db=self.db, include_try_reference=False)} / Gün"))

                actions_container = QWidget()
                actions_layout = QHBoxLayout(actions_container)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(6)
                
                if status == 'Depoda':
                    btn_assign = QPushButton("Zimmet")
                    btn_assign.setMinimumWidth(72)
                    btn_assign.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    btn_assign.setStyleSheet(f"background: {tc('success')}; color: white; border:none; padding: 6px; border-radius:4px; font-weight: bold;")
                    btn_assign.clicked.connect(lambda checked, did=d_id: self.assign_device(did))
                    actions_layout.addWidget(btn_assign)

                btn_edit = QPushButton("Düzenle")
                btn_edit.setMinimumWidth(78)
                btn_edit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                btn_edit.setStyleSheet(f"background: {tc('primary')}; color: white; border:none; padding: 6px; border-radius:4px; font-weight: bold;")
                btn_edit.clicked.connect(lambda checked, did=d_id: self.edit_device(did))
                actions_layout.addWidget(btn_edit)
                
                btn_del = QPushButton("Sil")
                btn_del.setMinimumWidth(52)
                btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                btn_del.setStyleSheet(f"background: {tc('danger')}; color: white; border:none; padding: 6px; border-radius:4px; font-weight: bold;")
                btn_del.clicked.connect(lambda checked, did=d_id: self.delete_device(did))
                actions_layout.addWidget(btn_del)
                
                self.table_inventory.setCellWidget(row, 7, actions_container)
                self.table_inventory.setRowHeight(row, 62)
        except (sqlite3.Error, RuntimeError, TypeError, ValueError) as e:
            logger.error(f"Envanter yükleme hatası: {e}")

    def load_active_loans(self, records=None):
        self.table_active.setRowCount(0)
        try:
            if records is None:
                records = self.db.cursor.execute('''
                    SELECT t.*, d.brand_model, d.daily_penalty_fee 
                    FROM loaner_transactions t
                    JOIN loaner_devices d ON t.device_id = d.id
                    WHERE t.status = 'Aktif'
                ''').fetchall()
            
            for r in records:
                row = self.table_active.rowCount()
                self.table_active.insertRow(row)
                t_id = str(r['id'])
                brand = str(r['brand_model'])
                customer = f"{r['customer_name']}\\n{r['customer_phone']}"
                expected = r['expected_return']
                given = r['date_given']
                
                # Check delay
                penalty_calc = CurrencyHelper.format_try_for_display(0, db=self.db, include_try_reference=False)
                delay_str = "Süre Devam Ediyor"
                is_delayed = False
                if expected:
                    dt_exp = QDateTime.fromString(expected[:19], "yyyy-MM-dd HH:mm:ss")
                    dt_now = QDateTime.currentDateTime()
                    if dt_now > dt_exp:
                        days_late = dt_exp.daysTo(dt_now)
                        if days_late > 0:
                            is_delayed = True
                            delay_str = f"{days_late} Gün Gecikti"
                            fee = float(r['daily_penalty_fee'] or 0)
                            penalty_calc = CurrencyHelper.format_try_for_display(fee * days_late, db=self.db, include_try_reference=False)

                self.table_active.setItem(row, 0, QTableWidgetItem(t_id))
                self.table_active.setItem(row, 1, QTableWidgetItem(brand))
                self.table_active.setItem(row, 2, QTableWidgetItem(customer))
                self.table_active.setItem(row, 3, QTableWidgetItem(given[:16] if given else "-"))
                
                exp_item = QTableWidgetItem(expected[:16] if expected else "Belirsiz")
                if is_delayed:
                    exp_item.setForeground(QColor("#EF4444"))
                self.table_active.setItem(row, 4, exp_item)
                
                delay_item = QTableWidgetItem(delay_str)
                if is_delayed:
                    delay_item.setForeground(QColor("#EF4444"))
                self.table_active.setItem(row, 5, delay_item)
                
                self.table_active.setItem(row, 6, QTableWidgetItem(penalty_calc))

                btn_return = QPushButton("İade Al")
                btn_return.setMinimumWidth(96)
                btn_return.setMinimumHeight(32)
                btn_return.setStyleSheet(f"background: {tc('warning')}; color: white; border:none; padding: 4px; border-radius:4px;")
                btn_return.clicked.connect(lambda checked, tid=t_id, did=r['device_id']: self.return_device(tid, did))
                self.table_active.setCellWidget(row, 7, btn_return)
                self.table_active.setRowHeight(row, 66)

        except (sqlite3.Error, RuntimeError, TypeError, ValueError) as e:
            logger.error(f"Aktif konsinye yükleme hatası: {e}")

    def add_new_device(self):
        dialog = ModernDialog("Yeni İkame Cihaz Ekle", self, width=540, height=580)
        form = QFormLayout()
        form.setSpacing(15)
        form.setVerticalSpacing(15)

        type_w = QComboBox()
        type_w.addItems(["Akıllı Telefon", "Dizüstü Bilgisayar", "Tablet", "Router/Modem", "Yedek Parça", "Diğer"])

        brand_w = QLineEdit()
        brand_w.setPlaceholderText("Örn: Apple iPhone 15")
        
        serial_w = QLineEdit()
        serial_w.setPlaceholderText("Seri No veya MAC Adresi")
        
        shelf_w = QLineEdit()
        shelf_w.setPlaceholderText("Örn: A-12, Raf 3")
        
        penalty_w = QLineEdit("50.0")
        penalty_w.setPlaceholderText("Günlük gecikme bedeli")
        
        from PyQt6.QtWidgets import QTextEdit
        notes_w = QTextEdit()
        notes_w.setPlaceholderText("Cihaz kondisyonu, aksesuarlar ve diğer notlar...")
        notes_w.setMinimumHeight(100)

        form.addRow("Cihaz Tipi:", type_w)
        form.addRow("Marka & Model:", brand_w)
        form.addRow("Seri / MAC No:", serial_w)
        form.addRow("Raf No:", shelf_w)
        form.addRow(f"Günlük Ceza ({CurrencyHelper.get_label(db=self.db)}):", penalty_w)
        form.addRow("Demirbaş Notu:", notes_w)
        
        dialog.add_layout(form)

        dialog.add_cancel_button("Vazgeç")
        dialog.add_button("Envantere Kaydet", "primary", lambda: self._save_device(
            dialog, 
            type_w.currentText(), 
            brand_w.text(), 
            serial_w.text(), 
            shelf_w.text(),
            penalty_w.text(), 
            notes_w.toPlainText()
        ))
        dialog.exec()

    
    def _save_device(self, dialog, c_type, brand, serial, shelf, penalty, notes):
        if not brand or not serial:
            show_warning(self, "Hata", "Marka/Model ve Seri No alanları zorunludur.")
            return
        try:
            p_val = float(penalty)
        except (TypeError, ValueError) as e:
            logger.debug(f"Loaner device penalty parse fallback: {e}")
            p_val = 0.0
            
        try:
            self.db.cursor.execute(
                "INSERT INTO loaner_devices (device_type, brand_model, serial_mac, shelf_no, daily_penalty_fee, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (c_type, brand, serial, shelf, p_val, notes)
            )
            self.db.conn.commit()
            if self.main_window and hasattr(self.main_window, "show_notification"):
                self.main_window.show_notification("Yeni emanet cihazı depoya başarıyla eklendi.", "success")
            dialog.accept()
            self.request_refresh()
        except (sqlite3.Error, ValueError, TypeError) as e:
            show_error(self, "Hata", f"Kayıt eklenemedi: {e}")

    def edit_device(self, dev_id):
        try:
            record = self.db.cursor.execute(
                "SELECT * FROM loaner_devices WHERE id=?",
                (dev_id,),
            ).fetchone()
        except (sqlite3.Error, RuntimeError) as e:
            show_error(self, "Hata", f"Emanet cihaz bilgisi okunamadı: {e}")
            return

        if not record:
            show_warning(self, "Hata", "Düzenlenecek emanet cihaz bulunamadı.")
            return

        dialog = ModernDialog("Emanet Cihazı Düzenle", self, width=540, height=580)
        form = QFormLayout()
        form.setSpacing(15)
        form.setVerticalSpacing(15)

        type_w = QComboBox()
        type_w.addItems(["Akıllı Telefon", "Dizüstü Bilgisayar", "Tablet", "Router/Modem", "Yedek Parça", "Diğer"])
        current_type = str(record["device_type"] or "")
        type_idx = type_w.findText(current_type)
        if type_idx >= 0:
            type_w.setCurrentIndex(type_idx)
        elif current_type:
            type_w.addItem(current_type)
            type_w.setCurrentText(current_type)

        brand_w = QLineEdit(str(record["brand_model"] or ""))
        serial_w = QLineEdit(str(record["serial_mac"] or ""))
        shelf_w = QLineEdit(str(record["shelf_no"] or ""))
        penalty_w = QLineEdit(str(record["daily_penalty_fee"] or "0.0"))

        from PyQt6.QtWidgets import QTextEdit
        notes_w = QTextEdit()
        notes_w.setPlainText(str(record["notes"] or ""))
        notes_w.setMinimumHeight(100)

        form.addRow("Cihaz Tipi:", type_w)
        form.addRow("Marka & Model:", brand_w)
        form.addRow("Seri / MAC No:", serial_w)
        form.addRow("Raf No:", shelf_w)
        form.addRow(f"Günlük Ceza ({CurrencyHelper.get_label(db=self.db)}):", penalty_w)
        form.addRow("Demirbaş Notu:", notes_w)
        dialog.add_layout(form)

        dialog.add_cancel_button("Vazgeç")
        dialog.add_button("Değişiklikleri Kaydet", "primary", lambda: self._update_device(
            dialog,
            dev_id,
            type_w.currentText(),
            brand_w.text(),
            serial_w.text(),
            shelf_w.text(),
            penalty_w.text(),
            notes_w.toPlainText(),
        ))
        dialog.exec()

    def _update_device(self, dialog, dev_id, c_type, brand, serial, shelf, penalty, notes):
        if not brand or not serial:
            show_warning(self, "Hata", "Marka/Model ve Seri No alanları zorunludur.")
            return
        try:
            p_val = float(penalty)
        except (TypeError, ValueError) as e:
            logger.debug(f"Loaner device penalty parse fallback: {e}")
            p_val = 0.0

        try:
            self.db.cursor.execute(
                """
                UPDATE loaner_devices
                SET device_type=?, brand_model=?, serial_mac=?, shelf_no=?, daily_penalty_fee=?, notes=?
                WHERE id=?
                """,
                (c_type, brand, serial, shelf, p_val, notes, dev_id),
            )
            self.db.conn.commit()
            if self.main_window and hasattr(self.main_window, "show_notification"):
                self.main_window.show_notification("Emanet cihaz bilgileri güncellendi.", "success")
            dialog.accept()
            self.request_refresh()
        except (sqlite3.Error, ValueError, TypeError) as e:
            show_error(self, "Hata", f"Kayıt güncellenemedi: {e}")

    def delete_device(self, dev_id):
        reply = show_question(
            self,
            "Onay",
            "Bu emanet cihazını envanterden tamamen silmek istediğinize emin misiniz",
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.cursor.execute("DELETE FROM loaner_devices WHERE id=?", (dev_id,))
                self.db.conn.commit()
                self.request_refresh()
            except (sqlite3.Error, RuntimeError) as e:
                show_error(self, "Hata", f"Silme başarısız: {e}")

    def assign_device(self, dev_id):
        dialog = ModernDialog("Müşteriye Tesis Et (Zimmetle)", self, width=560, height=520)
        form = QFormLayout()
        form.setSpacing(15)
        form.setVerticalSpacing(15)

        f_name = QLineEdit()
        f_name.setPlaceholderText("Müşteri Adı Soyadı")
        
        f_phone = QLineEdit()
        f_phone.setPlaceholderText("Telefon Numarası")
        
        f_track = QLineEdit()
        f_track.setPlaceholderText("Servis Takip Numarası (Opsiyonel)")
        
        from PyQt6.QtWidgets import QTextEdit
        f_cond = QTextEdit()
        f_cond.setPlaceholderText("Örn: Ekranda çizik yok, şarj aletiyle verildi")
        f_cond.setMinimumHeight(80)

        f_date = QDateTimeEdit(QDateTime.currentDateTime().addDays(3))
        f_date.setCalendarPopup(True)
        f_date.setMinimumHeight(40)

        form.addRow("Müşteri Adı:", f_name)
        form.addRow("Telefon:", f_phone)
        form.addRow("Servis Kaydı (Fiş):", f_track)
        form.addRow("Veriliş Durumu (Not):", f_cond)
        form.addRow("Beklenen İade Tarihi:", f_date)
        dialog.add_layout(form)

        dialog.add_cancel_button("Vazgeç")
        dialog.add_button("Zimmetle ve Teslim Et", "success", lambda: self._save_assignment(
            dialog, dev_id, f_name.text(), f_phone.text(), f_track.text(), f_cond.toPlainText(), 
            f_date.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        ))
        dialog.exec()

    
    def _save_assignment(self, dialog, dev_id, name, phone, track, cond, target_date):
        if not name:
            show_warning(self, "Hata", "Müşteri adı zorunludur.")
            return
        
        try:
            self.db.cursor.execute("""
                INSERT INTO loaner_transactions (device_id, customer_name, customer_phone, tracking_no, condition_out, expected_return)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (dev_id, name, phone, track, cond, target_date))
             
            self.db.cursor.execute("UPDATE loaner_devices SET status='Müşteride' WHERE id=?", (dev_id,))
            self.db.conn.commit()
            
            if self.main_window and hasattr(self.main_window, "show_notification"):
                self.main_window.show_notification("Cihaz müşteriye başarıyla zimmetlendi.", "success")
            
            dialog.accept()
            self.request_refresh()
        except (sqlite3.Error, RuntimeError, TypeError, ValueError) as e:
            show_error(self, "Hata", f"Kayıt işlemi başarısız: {e}")

    def return_device(self, trans_id, dev_id):
        dialog = ModernDialog("Cihazı İade Al", self, width=540, height=400)
        form = QFormLayout()
        form.setSpacing(15)
        form.setVerticalSpacing(15)

        f_cond = QLineEdit()
        f_cond.setPlaceholderText("İade alınırkenki cihaz durumu (Örn: Sağlam / Kamera Kırık)")

        f_penalty = QLineEdit("0")
        f_penalty.setPlaceholderText(f"Ek ceza / hasar ücreti ({CurrencyHelper.get_label(db=self.db)})")

        form.addRow("İade Durumu:", f_cond)
        form.addRow("Kesilecek Hasar/Ceza Ücreti:", f_penalty)
        dialog.add_layout(form)

        lbl_info = QLabel("ℹ️ Bu işlem sonrası cihaz tekrar 'Depoda' statüsüne geçer.")
        lbl_info.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; margin-top: 5px;"))
        dialog.add_widget(lbl_info)

        dialog.add_cancel_button("Vazgeç")
        dialog.add_button("İşlemi Tamamla & İade Al", "warning", lambda: self._save_return(
            dialog, trans_id, dev_id, f_cond.text(), f_penalty.text()
        ))
        dialog.exec()

    
    def _save_return(self, dialog, trans_id, dev_id, cond, penalty):
        try:
            p_val = float(penalty) if penalty else 0.0
        except (TypeError, ValueError) as e:
            logger.debug(f"Loaner return penalty parse fallback: {e}")
            p_val = 0.0
            
        try:
            now_str = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
            self.db.cursor.execute("""
                UPDATE loaner_transactions 
                SET date_returned=?, condition_in=?, penalty_applied=?, status='Tamamlandı'
                WHERE id=?
            """, (now_str, cond, p_val, trans_id))
             
            self.db.cursor.execute("UPDATE loaner_devices SET status='Depoda' WHERE id=?", (dev_id,))
            self.db.conn.commit()
            
            if self.main_window and hasattr(self.main_window, "show_notification"):
                if p_val > 0:
                    self.main_window.show_notification(
                        "Cihaz iade alındı. Tahakkuk eden ceza: "
                        f"{CurrencyHelper.format_try_for_display(p_val, db=self.db, include_try_reference=False)}",
                        "warning",
                    )
                else:
                    self.main_window.show_notification("Cihaz sorunsuz şekilde iade alındı ve depoya döndü.", "success")
                    
            dialog.accept()
            self.request_refresh()
        except (sqlite3.Error, RuntimeError, TypeError, ValueError) as e:
            show_error(self, "Hata", f"İade işlemi sırasında hata: {e}")

    def setup_usage_guide_tab(self):
        ly = QVBoxLayout(self.tab_guide)
        ly.setContentsMargins(0, 10, 0, 0)
        
        from PyQt6.QtWidgets import QTextBrowser
        guide_text = QTextBrowser()
        guide_text.setOpenExternalLinks(True)
        guide_text.setStyleSheet(theme_qss("border: none; background: transparent; color: @text; padding: 20px;"))
        
        html_content = f"""
        <div style="font-family: {DesignTokens.FONT_FAMILY}; color: @text;">
            <h1 style="color: @accent;">📖 Emanet (Konsinye) Cihaz Takip Modülü Kullanım Kılavuzu</h1>
            <p>Bu modül, teknik servis sürecinde müşterilere verilen geçici cihazların stok ve durum takibini yapmak için tasarlanmıştır.</p>
            
            <h2 style="color: @primary;">1. Müşterideki Cihazlar (Aktif) Sekmesi</h2>
            <ul>
                <li><b>Takip:</b> Şu an müşterilerde olan tüm cihazları listeler.</li>
                <li><b>Gecikme:</b> İade tarihi geçen cihazlar otomatik olarak <b>kırmızı</b> ile işaretlenir.</li>
                <li><b>İade Al:</b> Müşteri cihazı getirdiğinde bu butonu kullanarak cihazı depoya geri alabilirsiniz.</li>
            </ul>
            
            <h2 style="color: @primary;">2. Emanet Cihaz Deposu Sekmesi</h2>
            <ul>
                <li><b>Envanter:</b> Elinizdeki tüm emanet cihazları ve raf numaralarını görebilirsiniz.</li>
                <li><b>Yeni Cihaz:</b> Üstteki <b>"+ Yeni Cihaz Ekle"</b> butonu ile depoya yeni ikame cihazlar girebilirsiniz.</li>
                <li><b>Zimmetle:</b> Bir cihazı müşteriye vereceğiniz zaman bu butona basarak müşteri bilgilerini girmeniz yeterlidir.</li>
            </ul>
            
            <h2 style="color: @primary;">3. İpuçları ve Kısayollar</h2>
            <p>💡 Cihazları eklerken <b>"Raf No"</b> bilgisini girmek, yoğun zamanlarda cihazı hızlıca bulmanızı sağlar.</p>
            <p>💡 <b>Gecikme Cezası:</b> Cihazı tanımlarken günlük gecikme bedeli belirlerseniz, sistem otomatik olarak borç hesaplaması yapar.</p>
            
            <hr style="border: 0; border-top: 1px solid @border; margin: 20px 0;">
            <p style="color: @text_muted; font-style: italic;">AYEC Pro Teknik Servis Yönetimi - Akıllı İkame Çözümleri</p>
        </div>
        """
        # theme_qss doesn't process HTML, we should replace tokens manually or use theme_manager helper if exists.
        # But for now, we'll use literal colors or basic CSS.
        # Let's fix tokens in HTML:
        final_html = html_content.replace("@text_muted", tc("text_muted")).replace("@text", tc("text")).replace("@accent", tc("accent")).replace("@primary", tc("primary")).replace("@border", tc("border"))
        
        guide_text.setHtml(final_html)
        ly.addWidget(guide_text)
