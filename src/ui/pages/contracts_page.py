# -*- coding: utf-8 -*-
import csv
import unicodedata

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
                             QDialog, QFormLayout, QLineEdit, QComboBox, 
                             QDateEdit, QFileDialog, QListWidget, QListWidgetItem, QGroupBox, QFrame,
                             QTextEdit, QScrollArea, QAbstractItemView, QGridLayout, QButtonGroup, QProgressBar)

# ... (Previous imports kept if not replaced by above block, but since I am targeting imports line 1-5, I need to be careful.
# Wait, I can target the method call instead of imports if I use fully qualified name
# No, simpler to target line 334 and add import to top.
# But multi-chunk replace is better.

# Let's do it in ONE Replace call with chukns.)

# ... Actually, replace_file_content takes chunks.
# I'll replace imports AND the line.


from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.utils.theme_colors import theme_qss, tc
from src.ui.widgets.loaner_summary_visuals import LoanerMetricIcon
from src.ui.widgets.financial_reference_controls import FinancialReferenceActionButton, ReferenceMetricValueLabel
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from PyQt6.QtCore import Qt, QDate, QUrl
from PyQt6.QtGui import QFont, QIcon, QDesktopServices, QColor, QAction, QShortcut, QKeySequence

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
        self.current_page = 0
        self.page_size = 4
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(8)
        self.setStyleSheet(theme_qss("background: @window;"))
        
        header_card = QFrame()
        header_card.setStyleSheet(theme_qss("background: @background; border: none;"))
        header_card.setFixedHeight(80)
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(4)
        title_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        breadcrumb = QLabel("M\u00dc\u015eTER\u0130 HUB > S\u00d6ZLE\u015eME Y\u00d6NET\u0130M\u0130")
        breadcrumb.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:10px;font-weight:700;"))
        title_vbox.addWidget(breadcrumb)
        header = QLabel("S\u00f6zle\u015fme Y\u00f6netimi")
        header_font = self.font()
        header_font.setPointSize(18)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setStyleSheet(theme_qss("color: @text; border: none; background: transparent;"))
        title_vbox.addWidget(header)
        
        sub = QLabel("S\u00f6zle\u015fme detaylar\u0131n\u0131 ve eklerini g\u00f6r\u00fcnt\u00fclemek i\u00e7in tablo sat\u0131r\u0131na \u00e7ift t\u0131klay\u0131n\u0131z.")
        sub.setWordWrap(True)
        sub.setStyleSheet(theme_qss("color: @text_muted; border: none; background: transparent;"))
        title_vbox.addWidget(sub)
        header_layout.addLayout(title_vbox, 1)

        # Actions in the same header row
        btn_layout = QGridLayout()
        btn_layout.setSpacing(6)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        btn_add = QPushButton("+ Yeni S\u00f6zle\u015fme")
        btn_add.clicked.connect(self.open_add_dialog)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        
        btn_delete = FinancialReferenceActionButton(
            "S\u00f6zle\u015fme Sil", 'delete', stacked=False, centered_inline=True,
        )
        btn_delete.clicked.connect(self.delete_contract)
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setStyleSheet(theme_qss(
            'QPushButton { background: @danger_bg; color: @danger; border: 1px solid @danger; '
            'border-radius: 4px; padding: 0 8px; font-size: 11px; font-weight: 600; min-height: 28px; } '
            'QPushButton:hover { background: @finance_surface_high; }'
        ))
        btn_delete.setMinimumWidth(btn_delete.fontMetrics().horizontalAdvance(btn_delete.text()) + 36)
        
        self.contract_plan_button = QPushButton("Periyodik Bak\u0131m Planla")
        self.contract_plan_button.clicked.connect(self._open_contract_calendar)
        self.contract_export_button = QPushButton("Excel Raporu")
        self.contract_export_button.clicked.connect(self.export_contract_report)
        for button in (self.contract_plan_button, self.contract_export_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        btn_layout.addWidget(self.contract_plan_button, 0, 0)
        btn_layout.addWidget(self.contract_export_button, 0, 1)
        btn_layout.addWidget(btn_add, 1, 0)
        btn_layout.addWidget(btn_delete, 1, 1)
        header_layout.addLayout(btn_layout)
        
        layout.addWidget(header_card)

        metrics = QGridLayout()
        metrics.setSpacing(8)
        self.contract_metric_values = []
        for column, (title, value, detail, color) in enumerate((
            ("AKTIF SOZLESMELER", "0", "Yururlukte olan kurumsal SLA", "@finance_secondary"),
            ("YAKLASAN YENILEMELER", "0", "30 gun icinde bitecekler", "@danger"),
            ("SOZLESME HACMI", "0", "Kayitli sozlesme bedelleri", "@finance_primary"),
            ("ORTALAMA SLA YANIT SURESI", "-", "SLA olcumu bekleniyor", "@finance_tertiary"),
        )):
            metric = QFrame()
            metric.setFixedHeight(112)
            metric.setStyleSheet(theme_qss(f"""
                QFrame {{ background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }}
                QLabel {{ border: none; }}
            """))
            metric_layout = QVBoxLayout(metric)
            metric_layout.setContentsMargins(10, 8, 10, 8)
            metric_layout.setSpacing(2)
            metric_title = QLabel(title)
            metric_title.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px; font-weight: 700;"))
            metric_value = (
                ReferenceMetricValueLabel(value, primary_token=color.lstrip('@'), primary_size=20)
                if column == 2 else QLabel(value)
            )
            self.contract_metric_values.append(metric_value)
            value_size = 20 if column == 2 else 26
            metric_value.setStyleSheet(theme_qss(f"color: {color}; font-size: {value_size}px; font-weight: 800;"))
            metric_detail = QLabel(detail)
            metric_detail.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px;"))
            metric_layout.addWidget(metric_title)
            metric_value_row = QHBoxLayout()
            metric_value_row.addWidget(metric_value, 1)
            metric_value_row.addWidget(LoanerMetricIcon(("shield", "clock", "outbound", "check")[column], color.lstrip("@")))
            metric_layout.addLayout(metric_value_row)
            metric_layout.addWidget(metric_detail)
            metrics.addWidget(metric, 0, column)
        layout.addLayout(metrics)

        status_chips = QHBoxLayout()
        status_chips.setSpacing(6)
        self.contract_status_filter = "Tum"
        self.contract_status_group = QButtonGroup(self)
        self.contract_status_group.setExclusive(True)
        self.contract_status_buttons = {}
        self.contract_status_captions = {
            "Tum": "T\u00fcm\u00fc", "Aktif": "Aktif",
            "Yenileme": "Yenileme Bekleyen", "Suresi": "S\u00fcresi Dolanlar", "Taslaklar": "Taslaklar",
        }
        for key, caption in self.contract_status_captions.items():
            label = "{} (0)".format(caption)
            chip = QPushButton(label)
            chip.setCheckable(True)
            chip.setChecked(key == "Tum")
            self.contract_status_group.addButton(chip)
            self.contract_status_buttons[key] = chip
            chip.setStyleSheet(theme_qss(
                "QPushButton { background: @surface; color: @text_muted; border: 1px solid @border; "
                "border-radius: 6px; padding: 6px 10px; font-weight: 700; } "
                "QPushButton:checked { background: @accent; color: @selection_text; border-color: @accent; }"
            ))
            chip.clicked.connect(lambda checked, value=key: self._set_contract_status_filter(value))
            status_chips.addWidget(chip)

        filter_card = QFrame()
        filter_card.setStyleSheet(theme_qss("background: @surface_alt; border: 1px solid @border; border-radius: 8px;"))
        filter_card.setFixedHeight(84)
        filter_box = QVBoxLayout(filter_card)
        filter_box.setContentsMargins(10, 6, 10, 6)
        filter_box.setSpacing(6)
        filter_top = QHBoxLayout()
        filter_top.setSpacing(8)
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)
        self.contract_search = QLineEdit()
        self.contract_search.setPlaceholderText("Sozlesme, musteri veya baslik ara...")
        self.contract_search.setClearButtonEnabled(True)
        self.contract_search.textChanged.connect(self._on_contract_filter_changed)
        self.contract_search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        self.contract_search_shortcut.activated.connect(self.contract_search.setFocus)
        self.contract_type_filter = QComboBox()
        self.contract_type_filter.addItems(["Tum turler", "SLA", "Bakim", "Lisans", "Diger"])
        self.contract_type_filter.currentTextChanged.connect(self._on_contract_filter_changed)
        filter_top.addWidget(self.contract_search, 1)
        filter_top.addLayout(status_chips)
        filter_box.addLayout(filter_top)
        filter_layout.addWidget(self.contract_type_filter)
        self.contract_sla_filter = QComboBox()
        self.contract_sla_filter.addItem("SLA Seviyesi: T\u00fcm\u00fc", "")
        self.contract_sla_filter.currentIndexChanged.connect(self._on_contract_filter_changed)
        filter_layout.addWidget(self.contract_sla_filter)
        filter_layout.addStretch()
        refresh_button = QPushButton("Yenile")
        refresh_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        refresh_button.clicked.connect(self.load_contracts)
        filter_layout.addWidget(refresh_button)
        filter_box.addLayout(filter_layout)
        layout.addWidget(filter_card)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "M\u00fc\u015fteri", "Ba\u015fl\u0131k", "SLA / T\u00fcr",
            "Ba\u015flang\u0131\u00e7", "Biti\u015f", "Durum", "Kalan S\u00fcre",
            "S\u00f6zle\u015fme Bedeli", "\u0130\u015flemler",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header_view = self.table.horizontalHeader()
        for column, width in ((0, 52), (3, 105), (4, 104), (5, 104), (6, 118), (7, 114), (8, 118), (9, 70)):
            header_view.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(column, width)
        header_view.moveSection(6, 8)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(theme_qss("""
            QTableWidget {
                background: @finance_surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 6px;
            }
            QHeaderView::section {
                background: @background;
                color: @finance_text_muted;
                padding: 10px 8px;
                border: none;
                border-bottom: 1px solid @border;
                font-weight: 700;
            }
            QTableWidget::item {
                background: @finance_surface;
                border-bottom: 1px solid @finance_surface_high;
                padding: 8px;
            }
            QTableWidget::item:alternate {
                background: @background;
            }
            QTableWidget::item:selected {
                background: @selection_bg;
                color: @selection_text;
            }
        """))
        self.table.doubleClicked.connect(self.open_details)
        self.table.setMinimumHeight(96)
        self.table.setMaximumHeight(372)
        layout.addWidget(self.table)
        pager = QHBoxLayout()
        pager.setContentsMargins(4, 0, 4, 0)
        self.contract_result_label = QLabel()
        self.contract_result_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
        pager.addWidget(self.contract_result_label)
        pager.addStretch()
        self.contract_previous = QPushButton("<")
        self.contract_page_label = QLabel("1 / 1")
        self.contract_page_label.setMinimumWidth(54)
        self.contract_page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.contract_next = QPushButton(">")
        for button in (self.contract_previous, self.contract_next):
            button.setFixedSize(34, 30)
            button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm") + "QPushButton{padding:0;min-height:24px;min-width:24px;}"))
        self.contract_previous.clicked.connect(lambda: self._change_contract_page(-1))
        self.contract_next.clicked.connect(lambda: self._change_contract_page(1))
        pager.addWidget(self.contract_previous)
        pager.addWidget(self.contract_page_label)
        pager.addWidget(self.contract_next)
        layout.addLayout(pager)
        footer_grid = QGridLayout()
        footer_grid.setSpacing(8)
        self.contract_footer_details = {}
        self.contract_footer_actions = {}
        for column, (title, detail, accent) in enumerate((
            ("Bu Haftaki Periyodik Bak\u0131m & Saha Ziyaretleri", "Bak\u0131m plan\u0131 bulunmuyor.", "@finance_primary"),
            ("SLA / Yenileme Takibi", "Yenileme bekleyen kay\u0131t bulunmuyor.", "@finance_secondary"),
        )):
            card = QFrame()
            card.setObjectName("ContractFooterCard")
            card.setFixedHeight(128)
            card.setStyleSheet(theme_qss(f"QFrame#ContractFooterCard {{ background: @surface_alt; border: 1px solid @border; border-radius: 6px; border-top: 2px solid {accent}; }} QFrame#ContractFooterCard QLabel {{ background: transparent; border: none; }}"))
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)
            title_label = QLabel(title)
            title_label.setStyleSheet(theme_qss("color: @text; font-weight: 800; font-size: 11px;"))
            detail_label = QLabel(detail)
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px;"))
            self.contract_footer_details[column] = detail_label
            card_layout.addWidget(title_label)
            card_layout.addWidget(detail_label)
            action = QPushButton("T\u00fcm Takvimi A\u00e7" if column == 0 else "Yenileme Bekleyenleri G\u00f6r")
            action.setFixedHeight(28)
            action.setCursor(Qt.CursorShape.PointingHandCursor)
            action.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
            if column == 0:
                action.clicked.connect(self._open_contract_calendar)
            else:
                action.clicked.connect(lambda: self.contract_status_buttons["Yenileme"].click())
            card_layout.addWidget(action)
            self.contract_footer_actions[column] = action
            footer_grid.addWidget(card, 0, column)
        footer_grid.setColumnStretch(0, 2)
        footer_grid.setColumnStretch(1, 1)
        layout.addLayout(footer_grid)
        self.empty_state = EmptyState(
            "Henüz sözleşme yok",
            "Kaydedilmiş bir sözleşme bulunamadı.",
            parent=self,
        )
        self.empty_state.setMinimumHeight(240)
        self.empty_state.hide()
        layout.addWidget(self.empty_state)
        layout.addStretch(1)
        
        self.load_contracts()
        
    def open_add_dialog(self):
        dlg = AddContractDialog(self.db, self)
        if dlg.exec():
            self.load_contracts()
            if self.main_window and hasattr(self.main_window, 'show_notification'):
                self.main_window.show_notification("Sözleşme başarıyla eklendi.", "success")

    def _on_contract_filter_changed(self, *_args):
        self.current_page = 0
        self._filter_contract_rows()

    def _set_contract_status_filter(self, value):
        self.contract_status_filter = value.split(" ")[0]
        self.current_page = 0
        self._filter_contract_rows()

    def _change_contract_page(self, delta):
        self.current_page += delta
        self._filter_contract_rows()

    def _filter_contract_rows(self):
        query = self._contract_search_key(self.contract_search.text())
        selected_type = self.contract_type_filter.currentText()
        selected_status = getattr(self, "contract_status_filter", "Tum")
        matching_rows = []
        for row in range(self.table.rowCount()):
            values = [self._contract_search_key(self.table.item(row, column).text()) for column in range(self.table.columnCount()) if self.table.item(row, column)]
            type_value = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
            matches_query = not query or any(query in value for value in values)
            matches_type = selected_type == "Tum turler" or self._contract_search_key(selected_type) in self._contract_search_key(type_value)
            selected_sla = self.contract_sla_filter.currentData()
            matches_sla = not selected_sla or selected_sla == type_value
            matches_status = self._contract_categories(row).get(selected_status, False)
            if matches_query and matches_type and matches_sla and matches_status:
                matching_rows.append(row)
        self._matching_contract_rows = matching_rows
        total_pages = max(1, (len(matching_rows) + self.page_size - 1) // self.page_size)
        self.current_page = max(0, min(self.current_page, total_pages - 1))
        start = self.current_page * self.page_size
        page_rows = set(matching_rows[start:start + self.page_size])
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, row not in page_rows)
        header_height = self.table.horizontalHeader().height()
        row_height = max(44, self.table.verticalHeader().defaultSectionSize())
        self.table.setFixedHeight(max(96, min(372, header_height + len(page_rows) * row_height + 4)))
        self.contract_result_label.setText(
            f"Listelenen: {len(page_rows)} / {len(matching_rows)} kayit"
        )
        self.contract_page_label.setText(f"{self.current_page + 1} / {total_pages}")
        self.contract_previous.setEnabled(self.current_page > 0)
        self.contract_next.setEnabled(self.current_page + 1 < total_pages)

    @staticmethod
    def _contract_search_key(value):
        text = unicodedata.normalize("NFKD", str(value or "").strip().casefold().replace("\u0131", "i"))
        return "".join(character for character in text if not unicodedata.combining(character))

    def _update_contract_sla_options(self):
        previous = self.contract_sla_filter.currentData()
        values = {self.table.item(row, 3).text() for row in range(self.table.rowCount()) if self.table.item(row, 3)}
        self.contract_sla_filter.blockSignals(True)
        self.contract_sla_filter.clear()
        self.contract_sla_filter.addItem("SLA Seviyesi: T\u00fcm\u00fc", "")
        for value in sorted(values - {""}, key=self._contract_search_key):
            self.contract_sla_filter.addItem(value, value)
        self.contract_sla_filter.setCurrentIndex(max(0, self.contract_sla_filter.findData(previous)))
        self.contract_sla_filter.blockSignals(False)

    def _set_contract_status_badge(self, row):
        categories = self._contract_categories(row)
        if categories["Yenileme"] or categories["Suresi"]:
            color = "finance_tertiary"
        elif categories["Aktif"]:
            color = "finance_secondary"
        else:
            color = "finance_text_muted"
        container = QWidget()
        container.setObjectName("ContractStatusCell")
        container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        background = "background" if row % 2 else "finance_surface"
        container.setStyleSheet(theme_qss("QWidget#ContractStatusCell{background:@" + background + ";border:none;padding:0;}"))
        box = QHBoxLayout(container)
        box.setContentsMargins(5, 0, 5, 0)
        label = QLabel(self.table.item(row, 6).text())
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedHeight(36)
        label.setStyleSheet(theme_qss("QLabel{background:@finance_surface_alt;color:@" + color + ";border:none;border-radius:4px;padding:0;min-height:36px;max-height:36px;font-size:10px;font-weight:700;}"))
        box.addWidget(label)
        self.table.setCellWidget(row, 6, container)

    def _contract_categories(self, row):
        status_item = self.table.item(row, 6)
        status = status_item.text().lower() if status_item else ""
        date_item = self.table.item(row, 5)
        end_date = QDate.fromString(date_item.text()[:10], "yyyy-MM-dd") if date_item else QDate()
        days = QDate.currentDate().daysTo(end_date) if end_date.isValid() else None
        draft = "taslak" in status
        expired = days is not None and days < 0
        return {
            "Tum": True,
            "Aktif": "aktif" in status and not expired and not draft,
            "Yenileme": not expired and not draft and ("yenileme" in status or (days is not None and 0 <= days <= 30)),
            "Suresi": expired,
            "Taslaklar": draft,
        }

    def _update_contract_metrics(self, volume):
        counts = {key: 0 for key in self.contract_status_buttons}
        for row in range(self.table.rowCount()):
            for key, matches in self._contract_categories(row).items():
                counts[key] += int(matches)
        for key, button in self.contract_status_buttons.items():
            button.setText("{} ({})".format(self.contract_status_captions[key], counts[key]))
        self.contract_metric_values[0].setText(str(counts["Aktif"]))
        self.contract_metric_values[1].setText(str(counts["Yenileme"]))
        self.contract_metric_values[2].setText(CurrencyHelper.format_amount(volume, db=self.db))
        self._refresh_contract_footer()

    def _open_contract_calendar(self):
        if self.main_window and hasattr(self.main_window, "on_menu_click"):
            self.main_window.on_menu_click(30)

    def export_contract_report(self):
        rows = getattr(self, "_matching_contract_rows", [])
        if not rows:
            show_warning(self, "D\u0131\u015fa aktar\u0131lacak s\u00f6zle\u015fme bulunamad\u0131.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "S\u00f6zle\u015fme Raporunu Kaydet", "sozlesmeler.csv", "CSV (*.csv)"
        )
        if not path:
            return
        columns = [0, 1, 2, 3, 4, 5, 7, 8, 6]
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as report:
                writer = csv.writer(report, delimiter=";")
                writer.writerow([self.table.horizontalHeaderItem(column).text() for column in columns])
                writer.writerows([
                    [self.table.item(row, column).text() if self.table.item(row, column) else "" for column in columns]
                    for row in rows
                ])
            show_success(self, "S\u00f6zle\u015fme raporu kaydedildi.")
        except (OSError, ValueError) as exc:
            logger.error("Contract report export failed: %s", exc)
            show_error(self, "S\u00f6zle\u015fme raporu kaydedilemedi.")

    def _refresh_contract_footer(self):
        renewals = []
        for row in range(self.table.rowCount()):
            if self._contract_categories(row)["Yenileme"]:
                renewals.append("{} | {}".format(self.table.item(row, 1).text(), self.table.item(row, 5).text()))
        renewal_label = self.contract_footer_details[1]
        renewal_label.setText(
            "Yenileme Bekleyen: {}\n{}".format(len(renewals), "\n".join(renewals[:2]))
            if renewals else "Yenileme bekleyen kay\u0131t bulunmuyor."
        )
        renewal_label.setToolTip("\n".join(renewals))
        self.contract_footer_actions[1].setEnabled(bool(renewals))
        plans = []
        connection = getattr(self.db, "conn", None)
        if connection is not None:
            try:
                columns = {item[1] for item in connection.execute("PRAGMA table_info(appointments)").fetchall()}
                if {"date", "time", "customer_name", "description", "status"}.issubset(columns):
                    personnel_column = "COALESCE(personnel_name, '')" if "personnel_name" in columns else "''"
                    deleted_filter = " AND COALESCE(is_deleted, 0)=0" if "is_deleted" in columns else ""
                    query = (
                        "SELECT date, time, customer_name, " + personnel_column
                        + " FROM appointments WHERE date BETWEEN ? AND ?"
                        + " AND description LIKE ? AND COALESCE(status, '') NOT IN (?, ?)"
                        + deleted_filter + " ORDER BY date, time LIMIT 20"
                    )
                    today = QDate.currentDate()
                    rows = connection.execute(query, (
                        today.toString("yyyy-MM-dd"), today.addDays(6).toString("yyyy-MM-dd"),
                        "%Bak%", "\u0130ptal", "Tamamland\u0131",
                    )).fetchall()
                    plans = ["{} {} | {} | {}".format(row[0], row[1], row[2], row[3]) for row in rows]
            except Exception as exc:
                logger.warning("Contract maintenance overview failed: %s", exc)
        plan_label = self.contract_footer_details[0]
        plan_label.setText("\n".join(plans[:2]) if plans else "Bu hafta i\u00e7in planlanm\u0131\u015f bak\u0131m bulunmuyor.")
        plan_label.setToolTip("\n".join(plans))
            
    def open_details(self):
        row = self.table.currentRow()
        if row < 0: return
        
        try:
            cid = int(self.table.item(row, 0).text())
            dlg = ContractDetailsDialog(self.db, cid, self)
            dlg.exec()
        except Exception as e:
            logger.error(f"Contract details dialog error: {e}")

    def _open_contract_row(self, row):
        self.table.setCurrentCell(row, 0)
        self.open_details()
    
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
                SELECT c.id, cust.name, c.title, c.contract_type, c.start_date, c.end_date, c.status, c.price
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
                self.table.setRowHeight(i, 76)
                for j, val in enumerate(row[:7]):
                    item = QTableWidgetItem(str(val) if val else "")
                    if j in (0, 4, 5):
                        item.setFont(self._reference_record_font())
                        item.setToolTip(item.text())
                    self.table.setItem(i, j, item)
                end_date = QDate.fromString(str(row[5] or "")[:10], "yyyy-MM-dd")
                remaining = QTableWidgetItem("-")
                if end_date.isValid():
                    days = QDate.currentDate().daysTo(end_date)
                    remaining.setText(
                        "{} G\u00fcn Kald\u0131".format(days) if days >= 0
                        else "{} G\u00fcn Ge\u00e7ti".format(abs(days))
                    )
                    remaining.setForeground(QColor(tc("danger" if days <= 30 else "success")))
                self.table.setItem(i, 7, remaining)
                if end_date.isValid():
                    duration = QDate.fromString(str(row[4] or "")[:10], "yyyy-MM-dd").daysTo(end_date)
                    duration = max(1, duration)
                    color = "@danger" if days <= 30 else "@success"
                    indicator = QWidget()
                    indicator.setObjectName("ContractDurationCell")
                    indicator.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                    cell_background = "@background" if i % 2 else "@finance_surface"
                    indicator.setStyleSheet(theme_qss(f"QWidget#ContractDurationCell {{ background: {cell_background}; border: none; }}"))
                    indicator_layout = QVBoxLayout(indicator)
                    indicator_layout.setContentsMargins(8, 16, 8, 16)
                    indicator_layout.setSpacing(4)
                    days_label = QLabel(remaining.text())
                    days_label.setStyleSheet(theme_qss(f"color: {color}; background: transparent; border: none; font-weight: 700; font-size: 11px;"))
                    progress = QProgressBar()
                    progress.setRange(0, duration)
                    progress.setValue(min(duration, max(0, days)))
                    progress.setTextVisible(False)
                    progress.setFixedHeight(3)
                    progress.setStyleSheet(theme_qss(f"QProgressBar {{ background: @surface_alt; border: none; border-radius: 1px; }} QProgressBar::chunk {{ background: {color}; }}"))
                    indicator_layout.addWidget(days_label)
                    indicator_layout.addWidget(progress)
                    self.table.setCellWidget(i, 7, indicator)
                price = CurrencyHelper.format_amount(row[7], db=self.db) if len(row) > 7 else "-"
                price_item = QTableWidgetItem(price)
                price_item.setFont(self._reference_record_font(bold=True))
                price_item.setToolTip(price)
                self.table.setItem(i, 8, price_item)
                open_button = QPushButton("A\u00e7")
                open_button.setFixedHeight(28)
                open_button.setCursor(Qt.CursorShape.PointingHandCursor)
                open_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
                open_button.clicked.connect(lambda _checked=False, row_index=i: self._open_contract_row(row_index))
                self.table.setCellWidget(i, 9, open_button)
                self._set_contract_status_badge(i)
            has_rows = self.table.rowCount() > 0
            self.table.setVisible(has_rows)
            self.empty_state.setVisible(not has_rows)
            self.current_page = 0
            self._update_contract_sla_options()
            self._update_contract_metrics(sum(float(row[7] or 0) for row in rows if len(row) > 7))
            self._filter_contract_rows()
        except Exception as e:
            logger.error(f"Load contracts error: {e}")

    @staticmethod
    def _reference_record_font(*, bold=False):
        font = QFont(DesignTokens.MONO_FONT_NAME)
        font.setPixelSize(11)
        font.setBold(bold)
        return font


