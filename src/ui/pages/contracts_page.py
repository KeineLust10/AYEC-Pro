# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
                             QDialog, QFormLayout, QLineEdit, QComboBox, 
                             QDateEdit, QFileDialog, QListWidget, QListWidgetItem, QGroupBox, QFrame,
                             QTextEdit, QScrollArea, QAbstractItemView)

# ... (Previous imports kept if not replaced by above block, but since I am targeting imports line 1-5, I need to be careful.
# Wait, I can target the method call instead of imports if I use fully qualified name
# No, simpler to target line 334 and add import to top.
# But multi-chunk replace is better.

# Let's do it in ONE Replace call with chukns.)

# ... Actually, replace_file_content takes chunks.
# I'll replace imports AND the line.


from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from PyQt6.QtCore import Qt, QDate, QUrl
from PyQt6.QtGui import QFont, QIcon, QDesktopServices, QColor, QAction

import os
import shutil
import uuid

from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
from src.utils.design_system import DesignTokens
from src.utils.logger import logger
from src.utils.currency_helper import CurrencyHelper


class ContractDetailsDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, contract_id, parent=None):
        super().__init__("Sözleşme Detayları & Ekleri", parent, width=650, height=600)
        self.db = db
        self.contract_id = contract_id
        self.setup_content()
        
    def setup_content(self):
        # Fetch details
        self.db.cursor.execute("""
            SELECT c.title, cust.name, c.contract_type, c.description 
            FROM contracts c
            LEFT JOIN customers cust ON c.customer_id = cust.id
            WHERE c.id=?
        """, (self.contract_id,))
        row = self.db.cursor.fetchone()
        
        container = QFrame()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)

        if row:
            info_card = QFrame()
            info_card.setStyleSheet(theme_qss(f"background: {DesignTokens.SECONDARY}; border-radius: 12px; padding: 10px;"))
            form = QFormLayout(info_card)
            form.addRow("BAŞLIK:", QLabel(row[0]))
            form.addRow("MÜŞTERİ:", QLabel(row[1]))
            form.addRow("TÜR:", QLabel(row[2]))
            form.addRow("AÇIKLAMA:", QLabel(row[3]))
            layout.addWidget(info_card)
            
        # Attachments
        layout.addWidget(QLabel("DOSYA EKLERİ"))
        self.list_files = QListWidget()
        self.list_files.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.refresh_files()
        self.list_files.itemDoubleClicked.connect(self.open_file)
        layout.addWidget(self.list_files)
        
        btn_box = QHBoxLayout()
        btn_open = QPushButton("📂 Aç/Görüntüle")
        btn_open.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_open.clicked.connect(self.open_selected)
        
        btn_del_file = QPushButton("🗑️ Ekini Sil")
        btn_del_file.setStyleSheet(theme_qss(DesignTokens.get_button_qss("destructive")))
        btn_del_file.clicked.connect(self.delete_file)
        
        btn_box.addWidget(btn_open)
        btn_box.addWidget(btn_del_file)
        layout.addLayout(btn_box)
        
        btn_add_new = QPushButton("➕ Yeni Dosya Yükle")
        btn_add_new.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_add_new.clicked.connect(self.add_new_file)
        layout.addWidget(btn_add_new)
        
        self.add_widget(container)

    def refresh_files(self):
        self.list_files.clear()
        files = self.db.get_contract_attachments(self.contract_id)
        for f in files:
            item = QListWidgetItem(f"{f[3]} ({f[4]})")
            item.setData(Qt.ItemDataRole.UserRole, f[2]) # path
            item.setData(Qt.ItemDataRole.UserRole + 1, f[0]) # id
            self.list_files.addItem(item)
            
    def open_selected(self):
        item = self.list_files.currentItem()
        if item: self.open_file(item)
            
    def open_file(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            show_warning(self, "Dosya bulunamadı!")

    def delete_file(self):
        item = self.list_files.currentItem()
        if not item: return
        
        confirm = ModernConfirmDialog("Eki Sil", "Dosya eki kalıcı olarak silinecek. Emin misiniz", self, destructive=True)
        
        if confirm.exec() == QDialog.DialogCode.Accepted:
            att_id = item.data(Qt.ItemDataRole.UserRole + 1)
            path = item.data(Qt.ItemDataRole.UserRole)
            self.db.cursor.execute("DELETE FROM contract_attachments WHERE id=?", (att_id,))
            self.db.conn.commit()
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.debug(f"Contract attachment delete fallback: {e}")
            self.refresh_files()
            show_success(self, "Dosya silindi.")

    def add_new_file(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Dosya Seç", "", "All Files (*)")
        if files:
            dest_dir = "contract_docs"
            if not os.path.exists(dest_dir): os.makedirs(dest_dir)
            for file in files:
                filename = os.path.basename(file)
                new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
                dest_path = os.path.join(dest_dir, new_name)
                shutil.copy2(file, dest_path)
                self.db.add_contract_attachment(self.contract_id, dest_path, filename)
            self.refresh_files()
            show_success(self, "Dosyalar eklendi.")


from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.modern_inputs import ValidatedLineEdit, ModernComboBox
from src.ui.widgets.empty_state import EmptyState
from src.utils.design_system import DesignTokens
from src.utils.logger import logger
from src.utils.validators import Validators

class AddContractDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None):
        super().__init__("Yeni Sözleşme Oluştur", parent, width=650, height=800)
        self.db = db
        self.files_to_upload = []
        self.setup_content()
        self._wire_ui_signals()

    def _wire_ui_signals(self):
        self.cmb_customer.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_type.currentIndexChanged.connect(self._on_ui_widget_changed)

    def setup_content(self):
        # NO SCROLL AREA - Fit to screen
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Customer Selection
        layout.addWidget(QLabel("MÜŞTERİ SEÇİMİ"))
        self.cmb_customer = ModernComboBox()
        self.load_customers()
        layout.addWidget(self.cmb_customer)

        # 2. Title
        layout.addWidget(QLabel("SÖZLEŞME BAŞLIĞI"))
        self.inp_title = ValidatedLineEdit("Örn: Kurumsal Bakım Sözleşmesi", validator_func=Validators.is_not_empty)
        layout.addWidget(self.inp_title)

        # 3. Type & Price
        row2 = QHBoxLayout()
        v1 = QVBoxLayout(); v1.addWidget(QLabel("TÜR")); self.cmb_type = ModernComboBox(items=["Bakım", "Kiralama", "Servis", "Lisans", "Proje"]); v1.addWidget(self.cmb_type); row2.addLayout(v1)
        v2 = QVBoxLayout(); v2.addWidget(QLabel(f"BEDEL ({CurrencyHelper.get_label(db=self.db)})")); self.inp_price = ValidatedLineEdit("0.00", validator_func=Validators.is_numeric); v2.addWidget(self.inp_price); row2.addLayout(v2)
        layout.addLayout(row2)

        # 4. Dates
        row3 = QHBoxLayout()
        v3 = QVBoxLayout(); v3.addWidget(QLabel("BAŞLANGIÇ")); self.date_start = QDateEdit(); self.date_start.setCalendarPopup(True); self.date_start.setDate(QDate.currentDate()); self.date_start.setStyleSheet(theme_qss(DesignTokens.get_input_qss())); v3.addWidget(self.date_start); row3.addLayout(v3)
        v4 = QVBoxLayout(); v4.addWidget(QLabel("BİTİŞ")); self.date_end = QDateEdit(); self.date_end.setCalendarPopup(True); self.date_end.setDate(QDate.currentDate().addYears(1)); self.date_end.setStyleSheet(theme_qss(DesignTokens.get_input_qss())); v4.addWidget(self.date_end); row3.addLayout(v4)
        layout.addLayout(row3)

        # 5. Description
        layout.addWidget(QLabel("AÇIKLAMA"))
        self.txt_desc = QTextEdit()
        self.txt_desc.setFixedHeight(60) # Reduced height
        self.txt_desc.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        layout.addWidget(self.txt_desc)

        # 6. Files (Compact)
        self.btn_add_f = QPushButton("📎 Sözleşme Dosyası / Eki Ekle")
        self.btn_add_f.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_f.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface_alt; border: 1px dashed @border; border-radius: 8px;
                color: @text_muted; font-weight: bold; padding: 10px;
            }
            QPushButton:hover { border-color: @accent; color: @accent; background-color: @selection_bg; }
        """))
        self.btn_add_f.clicked.connect(self.select_files)
        layout.addWidget(self.btn_add_f)
        
        self.lbl_files = QLabel("")
        self.lbl_files.setStyleSheet(theme_qss("color: @accent; font-size: 11px;"))
        layout.addWidget(self.lbl_files)
        
        # Spacer
        layout.addStretch()

        self.add_widget(container)
        
        # Buttons
        self.add_cancel_button()
        self.add_button("Sözleşmeyi Kaydet", "primary", self.save)

    # Helper update label
    def update_file_label(self):
        if not self.files_to_upload:
            self.lbl_files.setText("")
        else:
            names = [os.path.basename(f) for f in self.files_to_upload]
            self.lbl_files.setText(f"Seçilen Dosyalar: {', '.join(names)}")

    def search_web_template(self):
        """Web'de ara (Google)"""
        import webbrowser
        text = self.inp_title.text().strip() or "Hizmet Sözleşmesi"
        url = f"https://www.google.com/search?q={text}+örneği+word+pdf"
        webbrowser.open(url)
        
    def mousePressEvent(self, event):
        # Pencereyi sürükleyebilmek için
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if hasattr(self, "old_pos"):
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
        
    def load_customers(self):
        customers = self.db.get_customers()
        for c in customers:
            self.cmb_customer.addItem(c[1], c[0]) # Name, ID
            
    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Dosya Seç", "", "Images/PDF (*.png *.jpg *.jpeg *.pdf);;All Files (*)")
        if files:
            for f in files:
                self.files_to_upload.append(f)
            self.update_file_label()

    def save(self):
        customer_id = self.cmb_customer.currentData()
        title = self.inp_title.text()
        start = self.date_start.date().toString("yyyy-MM-dd")
        end = self.date_end.date().toString("yyyy-MM-dd")
        c_type = self.cmb_type.currentText()
        try:
            price = float(self.inp_price.text()) if self.inp_price.text() else 0.0
        except ValueError:
            price = 0.0
        desc = self.txt_desc.toPlainText()
        
        try:
            cur = self.db.cursor
            cur.execute("""
                INSERT INTO contracts (customer_id, title, start_date, end_date, contract_type, price, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (customer_id, title, start, end, c_type, price, desc))

            contract_id = cur.lastrowid
            self.db.conn.commit()
            
            # Handle Files
            if self.files_to_upload:
                dest_dir = "contract_docs"
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                    
                for file_path in self.files_to_upload:
                    try:
                        filename = os.path.basename(file_path)
                        # Avoid overwriting by adding UUID prefix
                        import uuid
                        ext = os.path.splitext(filename)[1]
                        unique_name = f"{uuid.uuid4()}{ext}"
                        dest_path = os.path.join(dest_dir, unique_name)
                        
                        shutil.copy2(file_path, dest_path)
                        
                        self.db.add_contract_attachment(contract_id, dest_path, filename)
                    except Exception as fe:
                        logger.error(f"Contract file upload error: {fe}")

            # show_info(self, "Sözleşme ve ekleri kaydedildi.")
            self.accept()
        except Exception as e:
            show_error(self, f"Ekleme hatası: {e}")

class ContractsPage(QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        self.setStyleSheet(theme_qss("background: @window;"))
        
        header_card = QFrame()
        header_card.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 12px;"))
        header_card.setFixedHeight(80)
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 6, 16, 6)
        header_layout.setSpacing(16)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(4)
        title_vbox.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        header = QLabel("S\u00f6zle\u015fme Y\u00f6netimi")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.setStyleSheet(theme_qss("color: @text; border: none; background: transparent;"))
        title_vbox.addWidget(header)
        
        sub = QLabel("S\u00f6zle\u015fme detaylar\u0131n\u0131 ve eklerini g\u00f6r\u00fcnt\u00fclemek i\u00e7in tablo sat\u0131r\u0131na \u00e7ift t\u0131klay\u0131n\u0131z.")
        sub.setWordWrap(True)
        sub.setStyleSheet(theme_qss("color: @text_muted; border: none; background: transparent;"))
        title_vbox.addWidget(sub)
        header_layout.addLayout(title_vbox)
        
        header_layout.addStretch()

        # Actions in the same header row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        btn_add = QPushButton("➕ Yeni S\u00f6zle\u015fme")
        btn_add.clicked.connect(self.open_add_dialog)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        
        btn_delete = QPushButton("\U0001f5d1\ufe0f S\u00f6zle\u015fme Sil")
        btn_delete.clicked.connect(self.delete_contract)
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setStyleSheet(theme_qss(DesignTokens.get_button_qss("destructive", size="sm")))
        
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_delete)
        header_layout.addLayout(btn_layout)
        
        layout.addWidget(header_card)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Müşteri", "Başlık", "Tür", "Başlangıç", "Bitiş", "Durum"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme_qss("""
            QTableWidget {
                background: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 12px;
            }
            QHeaderView::section {
                background: @surface_alt;
                color: @text;
                padding: 10px 8px;
                border: none;
                border-bottom: 1px solid @border;
                font-weight: 700;
            }
            QTableWidget::item {
                background: @surface;
                color: @text;
                border-bottom: 1px solid @border;
                padding: 8px;
            }
            QTableWidget::item:alternate {
                background: @surface_alt;
            }
            QTableWidget::item:selected {
                background: @selection_bg;
                color: @selection_text;
            }
        """))
        self.table.doubleClicked.connect(self.open_details)
        layout.addWidget(self.table)
        self.empty_state = EmptyState(
            "Henüz sözleşme yok",
            "Kaydedilmiş bir sözleşme bulunamadı.",
            parent=self,
        )
        self.empty_state.setMinimumHeight(240)
        self.empty_state.hide()
        layout.addWidget(self.empty_state)
        
        self.load_contracts()
        
    def open_add_dialog(self):
        dlg = AddContractDialog(self.db, self)
        if dlg.exec():
            self.load_contracts()
            if self.main_window and hasattr(self.main_window, 'show_notification'):
                self.main_window.show_notification("Sözleşme başarıyla eklendi.", "success")
            
    def open_details(self):
        row = self.table.currentRow()
        if row < 0: return
        
        try:
            cid = int(self.table.item(row, 0).text())
            dlg = ContractDetailsDialog(self.db, cid, self)
            dlg.exec()
        except Exception as e:
            logger.error(f"Contract details dialog error: {e}")
    
    def delete_contract(self):
        """Delete selected contract and its attachments"""
        row = self.table.currentRow()
        if row < 0:
            show_warning(self, "Lütfen silinecek bir sözleşme seçin.")
            return
        
        try:
            cid = int(self.table.item(row, 0).text())
            title = self.table.item(row, 2).text()
            
            from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
            confirm = ModernConfirmDialog(
                "Sözleşmeyi Sil",
                f"<b>{title}</b> sözleşmesini ve tüm eklerini silmek istediğinize emin misiniz<br>Bu işlem geri alınamaz.",
                self,
                confirm_text="Evet, Sil",
                destructive=True
            )
            
            if confirm.exec() == QDialog.DialogCode.Accepted:

                # Delete attachments first
                attachments = self.db.get_contract_attachments(cid)
                for att in attachments:
                    # att: id, contract_id, file_path, filename, created_at
                    try:
                        if os.path.exists(att[2]):
                            os.remove(att[2])
                    except Exception as e:
                        logger.debug(f"Contract attachment cleanup fallback: {e}")
                
                # Delete from database
                self.db.cursor.execute("DELETE FROM contract_attachments WHERE contract_id=?", (cid,))
                self.db.cursor.execute("DELETE FROM contracts WHERE id=?", (cid,))
                self.db.conn.commit()
                
                self.load_contracts()
                if self.main_window and hasattr(self.main_window, 'show_notification'):
                    self.main_window.show_notification("Sözleşme başarıyla silindi.", "success")
                    
        except Exception as e:
            show_error(self, f"Silme hatası: {e}")

    def load_contracts(self):
        try:
            self.db.cursor.execute("""
                SELECT c.id, cust.name, c.title, c.contract_type, c.start_date, c.end_date, c.status 
                FROM contracts c
                LEFT JOIN customers cust
                    ON c.customer_id = cust.id
                   AND COALESCE(cust.is_deleted, 0) = 0
                ORDER BY c.end_date ASC
            """)
            rows = self.db.cursor.fetchall()
            
            self.table.setRowCount(0)
            for i, row in enumerate(rows):
                self.table.insertRow(i)
                for j, val in enumerate(row):
                    item = QTableWidgetItem(str(val) if val else "")
                    self.table.setItem(i, j, item)
            has_rows = self.table.rowCount() > 0
            self.table.setVisible(has_rows)
            self.empty_state.setVisible(not has_rows)
        except Exception as e:
            logger.error(f"Load contracts error: {e}")


