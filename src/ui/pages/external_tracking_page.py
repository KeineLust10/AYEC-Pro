# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QDialog, QFormLayout, QLineEdit, QDateEdit, QTextEdit, 
                             QFrame, QMessageBox, QGraphicsDropShadowEffect, QComboBox, QMenu,
                             QGridLayout, QFileDialog, QSizePolicy)
from src.utils.theme_colors import theme_qss, tc
from src.utils.design_system import DesignTokens
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.logger import logger
from PyQt6.QtGui import QFont, QColor, QPixmap
from datetime import datetime
import os

from src.utils.toast_notification import show_success, show_error, show_info
from src.utils.date_utils import format_turkish_date

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens
from src.ui.widgets.modern_inputs import ValidatedLineEdit, ModernComboBox
from src.ui.dialogs.unified_documents_center_dialog import UnifiedDocumentsCenterDialog
from src.utils.context_menu_settings import is_context_menu_enabled


class ExternalTrackingDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None, data=None):
        self.db = db
        self.data = data
        super().__init__("Lojistik & Garanti Takip Ekle", parent, width=1000, height=850)
        self.setup_content()
        if data:
            self.load_data()
        self._wire_ui_signals()

    def _wire_ui_signals(self):
        self.inp_customer.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_status.currentIndexChanged.connect(self._on_ui_widget_changed)

    def setup_content(self):
        # Header text and icon are handled by ModernDialog, 
        # but we can customize if needed. We'll use the default ModernDialog structure.
        
        content = QWidget()
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        form_layout = QVBoxLayout(content)
        form_layout.setContentsMargins(30, 20, 30, 20)
        form_layout.setSpacing(20)
        
        # Input Background Frame
        main_frame = QFrame()
        main_frame.setObjectName("ExternalTrackingForm")
        main_frame.setStyleSheet(theme_qss("""
            QFrame#ExternalTrackingForm {
                background: @surface_alt; border-radius: 15px; border: 1px solid @border;
            }
            QFrame#ExternalTrackingForm QLabel {
                background: transparent; border: none; color: @text_muted;
                font-size: 13px; font-weight: 700;
            }
        """))
        main_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_frame.setMinimumHeight(520)
        grid = QGridLayout(main_frame)
        grid.setContentsMargins(25, 25, 25, 25)
        grid.setSpacing(15)
        
        # Helper to add field
        def add_form_field(label_text, widget, row, col=0, colspan=1):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(theme_qss("background: transparent; color: @text_muted; font-size: 13px; font-weight: 700; border: none;"))
            vbox = QVBoxLayout()
            vbox.setSpacing(5)
            vbox.addWidget(lbl)
            vbox.addWidget(widget)
            grid.addLayout(vbox, row, col, 1, colspan)

        # Emanet No
        self.inp_internal_no = ValidatedLineEdit("Örn: M.NO 1025 / Cihaz Takip No")
        add_form_field("Müşteri Emanet No:", self.inp_internal_no, 0, 0, 2)
        
        # Müşteri (Editable ComboBox with Customer List)
        self.inp_customer = QComboBox()
        self.inp_customer.setEditable(True)
        self.inp_customer.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.inp_customer.setPlaceholderText("Müşteri seçin veya yazın...")
        self.inp_customer.setMinimumHeight(45)
        self.inp_customer.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self._load_customers()  # Load from database
        add_form_field("Müşteri Bilgisi:", self.inp_customer, 1, 0)
        
        # Ürün
        self.inp_product = ValidatedLineEdit("Marka / Model / Parça Adı")
        add_form_field("Ürün / Parça:", self.inp_product, 1, 1)
        
        # Servis
        self.inp_service = ValidatedLineEdit("Asus Servis, Penta, vb.")
        add_form_field("Gönderilen Yer:", self.inp_service, 2, 0)
        
        # Servis No
        self.inp_service_no = ValidatedLineEdit("Karşı tarafın verdiği servis no")
        add_form_field("Servis Kayıt No:", self.inp_service_no, 2, 1)
        
        # Tarih
        self.inp_date = QDateEdit(QDate.currentDate())
        self.inp_date.setCalendarPopup(True)
        self.inp_date.setDisplayFormat("dd.MM.yyyy")
        self.inp_date.setFixedHeight(45)
        self.inp_date.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        add_form_field("Gönderim Tarihi:", self.inp_date, 3, 0)
        
        # Durum
        self.cmb_status = ModernComboBox(items=["Hazırlanıyor", "Kargoya Verildi", "Servise Ulaştı", "Onarımda", "İade Bekleniyor", "Geri Geldi", "Müşteriye Teslim Edildi"])
        add_form_field("Güncel Durum:", self.cmb_status, 3, 1)
        
        # Kargo Group
        kargo_box = QFrame()
        kargo_box.setStyleSheet(theme_qss("background: @surface; border-radius: 12px; border: 1px solid @border;"))
        k_lay = QHBoxLayout(kargo_box)
        k_lay.setContentsMargins(15, 15, 15, 15)
        k_lay.setSpacing(15)
        
        self.inp_out_cargo = ValidatedLineEdit("Gidiş Kargo Takip No")
        self.inp_in_cargo = ValidatedLineEdit("Dönüş Kargo Takip No")
        
        v1 = QVBoxLayout()
        v1.addWidget(QLabel("↗ Gidiş Kargo No:"))
        v1.addWidget(self.inp_out_cargo)
        
        v2 = QVBoxLayout()
        v2.addWidget(QLabel("↙ Dönüş Kargo No:"))
        v2.addWidget(self.inp_in_cargo)
        
        k_lay.addLayout(v1)
        k_lay.addLayout(v2)
        
        grid.addWidget(kargo_box, 4, 0, 1, 2)

        photos_box = QFrame()
        photos_box.setStyleSheet(theme_qss("background: @surface; border-radius: 12px; border: 1px dashed @border;"))
        photos_layout = QHBoxLayout(photos_box)
        photos_layout.setContentsMargins(15, 15, 15, 15)
        photos_layout.setSpacing(15)

        self.photo_preview = QLabel("Önizleme")
        self.photo_preview.setFixedSize(180, 135)
        self.photo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo_preview.setStyleSheet(theme_qss("""
            QLabel {
                background: @surface_alt;
                color: @text_muted;
                border: 1px solid @border;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 700;
            }
        """))
        photos_layout.addWidget(self.photo_preview)

        lbl_photos = QLabel("📸 Garanti sürecine ait fotoğraflar")
        lbl_photos.setStyleSheet(theme_qss("background: transparent; color: @text; font-size: 13px; font-weight: 700; border: none;"))
        photos_layout.addWidget(lbl_photos)
        photos_layout.addStretch()

        self.btn_photos = QPushButton("➕ Fotoğraf Ekle / Galeri")
        self.btn_photos.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_photos.setFixedHeight(40)
        self.btn_photos.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        self.btn_photos.clicked.connect(self.open_photo_gallery)
        photos_layout.addWidget(self.btn_photos)

        grid.addWidget(photos_box, 5, 0, 1, 2)
        
        form_layout.addWidget(main_frame, 1)
        form_layout.setStretch(0, 1)
        self.add_widget(content)
        
        # Footer
        self.add_cancel_button("Vazgeç")
        self.add_button("💾 KAYDI TAMAMLA", "primary", self.save)
        self._update_photo_preview()
    
    def _load_customers(self):
        """Load customers into combobox"""
        try:
            customers = self.db.get_customers()
            self.inp_customer.clear()
            self.inp_customer.addItem("")
            for c in customers:
                if isinstance(c, dict):
                    name = c.get('name', '')
                else:
                    name = c[1] if len(c) > 1 else ''
                if name:
                    self.inp_customer.addItem(str(name))
        except Exception as e:
            logger.error(f"ExternalTrackingDialog customer load error: {e}")

    def load_data(self):
        d = self.data
        # d indexes: id=0, internal=1, cust=2, prod=3, serv=4, serv_no=5, date=6, out_cargo=7, in_cargo=8, status=9, notes=10
        self.inp_internal_no.setText(str(d[1] or ""))
        # Set ComboBox current text (editable)
        self.inp_customer.setCurrentText(str(d[2] or ""))
        self.inp_product.setText(str(d[3] or ""))
        self.inp_service.setText(str(d[4] or ""))
        self.inp_service_no.setText(str(d[5] or ""))
        if d[6]: self.inp_date.setDate(QDate.fromString(d[6], "yyyy-MM-dd"))
        self.inp_out_cargo.setText(str(d[7] or ""))
        self.inp_in_cargo.setText(str(d[8] or ""))
        self.cmb_status.setCurrentText(str(d[9] or "Hazırlanıyor"))
        self._update_photo_preview()

    def save(self):
        new_data = {
            'internal_no': self.inp_internal_no.text(),
            'customer': self.inp_customer.currentText(),
            'product': self.inp_product.text(),
            'service': self.inp_service.text(),
            'service_no': self.inp_service_no.text(),
            'date': self.inp_date.date().toString("yyyy-MM-dd"),
            'out_cargo': self.inp_out_cargo.text(),
            'in_cargo': self.inp_in_cargo.text(),
            'status': self.cmb_status.currentText(),
            'notes': ""
        }
        try:
            if self.data:
                self.db.update_external_tracking(self.data[0], new_data)
                show_success(self, "Kayıt başarıyla güncellendi.")
            else:
                self.db.add_external_tracking(new_data)
                show_success(self, "Yeni dış servis kaydı oluşturuldu.")
            self.accept()
        except Exception as e:
            show_error(self, f"Hata: {e}")

    def open_photo_gallery(self):
        tracking_no = self.inp_internal_no.text().strip()
        if not tracking_no:
            show_info(self, "Lütfen önce Müşteri Emanet No alanını doldurun.")
            return
        try:
            from src.ui.dialogs.photo_gallery_dialog import PhotoGalleryDialog
            dlg = PhotoGalleryDialog(self.db, tracking_no, self, read_only=False, stage="İşlem")
            dlg.exec()
            self._update_photo_preview()
        except Exception as e:
            show_error(self, f"Fotoğraf galerisi açılamadı: {e}")

    def _update_photo_preview(self):
        if not hasattr(self, "photo_preview"):
            return
        tracking_no = self.inp_internal_no.text().strip()
        if not tracking_no:
            self.photo_preview.setText("Önizleme")
            self.photo_preview.setPixmap(QPixmap())
            return
        photo_path = ""
        try:
            rows = self.db.get_photos(tracking_no, "İşlem") or []
            if not rows:
                rows = self.db.get_photos(tracking_no) or []
            for r in rows:
                p = r[1]
                if p and os.path.exists(p):
                    photo_path = p
                    break
        except Exception:
            photo_path = ""
        if photo_path and os.path.exists(photo_path):
            target = self.photo_preview.size()
            pix = QPixmap(photo_path).scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.photo_preview.setPixmap(pix)
            self.photo_preview.setText("")
        else:
            self.photo_preview.setText("Önizleme")
            self.photo_preview.setPixmap(QPixmap())

class ExternalTrackingPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setup_ui()
        self.refresh_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setStyleSheet(theme_qss("background-color: @surface_alt;"))

        # Modern Header with Gradient
        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(140)
        self.header_frame.setStyleSheet(theme_qss("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1e293b, stop:0.5 #334155, stop:1 #475569);
                border-bottom: 3px solid @warning;
            }
        """))
        
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(40, 20, 40, 20)
        
        # Left side - Title & Description
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(8)
        
        # Icon + Title
        title_row = QHBoxLayout()
        icon_lbl = QLabel("📦")
        icon_lbl.setStyleSheet(theme_qss("font-size: 42px; background: transparent; border: none;"))
        title_row.addWidget(icon_lbl)
        
        lbl_title = QLabel("Lojistik & Garanti Yönetimi")
        lbl_title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        lbl_title.setStyleSheet(theme_qss("color: white; background: transparent; border: none;"))
        title_row.addWidget(lbl_title)
        title_row.addStretch()
        title_vbox.addLayout(title_row)
        
        lbl_sub = QLabel("Anlaşmalı servisler ve garanti süreçlerinin merkezi takip sistemi")
        lbl_sub.setFont(QFont("Segoe UI", 13))
        lbl_sub.setStyleSheet(theme_qss("color: #94a3b8; background: transparent; border: none; margin-left: 55px;"))
        title_vbox.addWidget(lbl_sub)
        self.lbl_title = lbl_title
        self.lbl_sub = lbl_sub
        
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        # Excel Buttons
        excel_layout = QHBoxLayout()
        excel_layout.setSpacing(12)
        
        def _hbtn(icon, tooltip):
            b = QPushButton(icon)
            b.setFixedSize(40, 40)
            b.setToolTip(tooltip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                theme_qss(DesignTokens.get_icon_btn_qss())
            )
            return b

        btn_import = _hbtn("\U0001f4e5", "Excel \u0130\u00e7e Aktar")
        btn_import.clicked.connect(self.import_from_csv)
        excel_layout.addWidget(btn_import)

        btn_export = _hbtn("\U0001f4e4", "Excel D\u0131\u015fa Aktar")
        btn_export.clicked.connect(self.export_to_csv)
        excel_layout.addWidget(btn_export)

        btn_docs = _hbtn("\U0001f5c2\ufe0f", "Belge Merkezi")
        btn_docs.clicked.connect(self.open_documents_center)
        excel_layout.addWidget(btn_docs)

        header_layout.addLayout(excel_layout)

        self.btn_multi = _hbtn("\U0001f532", "\u00c7oklu Se\u00e7im")
        self.btn_multi.setCheckable(True)
        self.btn_multi.clicked.connect(self.toggle_multiselect)
        header_layout.addWidget(self.btn_multi)

        btn_add = QPushButton("➕ Yeni Takip Başlat")
        btn_add.setFixedSize(240, 50)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("warning")))
        
        # Add shadow to button
        shadow_add = QGraphicsDropShadowEffect()
        shadow_add.setColor(QColor(245, 158, 11, 100))
        shadow_add.setBlurRadius(20)
        shadow_add.setOffset(0, 4)
        btn_add.setGraphicsEffect(shadow_add)
        
        btn_add.clicked.connect(self.add_record)
        header_layout.addWidget(btn_add)
        
        layout.addWidget(self.header_frame)

        # Content Area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(25)

        # Statistics Cards Row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        # We'll populate these after loading data
        self.stats_layout = stats_layout
        content_layout.addLayout(stats_layout)

        # Table Container
        table_frame = QFrame()
        table_frame.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(0, 5)
        table_frame.setGraphicsEffect(shadow)
        
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Emanet No", "Müşteri & Ürün", "Dış Servis / Yer", 
            "Gidiş Tarihi", "Kargo Takip", "Durum", "İşlemler"
        ])
        
        # Modern Table Style
        self.table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        header_view = self.table.horizontalHeader()
        header_view.setHighlightSections(False)
        
        # Column width adjustments
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 100)  # Emanet No
        self.table.setColumnWidth(1, 230)  # Müşteri & Ürün
        self.table.setColumnWidth(2, 200)  # Dış Servis / Yer
        self.table.setColumnWidth(3, 110)  # Gidiş Tarihi
        self.table.setColumnWidth(4, 180)  # Kargo Takip
        self.table.setColumnWidth(5, 150)  # Durum
        header_view.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        self.table.verticalHeader().setDefaultSectionSize(70)  # Satır yüksekliği azaltıldı
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.cellDoubleClicked.connect(self.open_selected_record)
        
        table_layout.addWidget(self.table)
        content_layout.addWidget(table_frame)
        
        layout.addWidget(content)
        self.apply_theme_styles()


    def apply_theme_styles(self):
        if hasattr(self, "lbl_title"):
            self.lbl_title.setText("Lojistik & Garanti Yönetimi")
            self.lbl_title.setStyleSheet(theme_qss("color: @text; background: transparent; border: none;"))
        if hasattr(self, "lbl_sub"):
            self.lbl_sub.setText("Anlaşmalı servisler ve garanti süreçlerinin merkezi takip sistemi")
            self.lbl_sub.setStyleSheet(theme_qss("color: @text_muted; background: transparent; border: none; margin-left: 55px;"))

    def refresh_theme(self):
        self.apply_theme_styles()

    def open_documents_center(self):
        dlg = UnifiedDocumentsCenterDialog(self.db, None, self)
        dlg.exec()

    def refresh_data(self):
        try:
            records = self.db.get_external_trackings()
            
            # Update Statistics Cards
            while self.stats_layout.count():
                item = self.stats_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            total_count = len(records)
            active_count = sum(1 for r in records if r[9] not in ["Müşteriye Teslim Edildi", "Geri Geldi"])
            completed_count = sum(1 for r in records if r[9] == "Müşteriye Teslim Edildi")
            
            # Create stat cards
            self.stats_layout.addWidget(self.create_stat_card("Toplam Kayıt", str(total_count), "📦", tc("accent")))
            self.stats_layout.addWidget(self.create_stat_card("Aktif Takip", str(active_count), "🔄", tc("warning")))
            self.stats_layout.addWidget(self.create_stat_card("Teslim Edilen", str(completed_count), "✅", tc("success")))
            self.stats_layout.addStretch()
            
            # Update Table
            self.table.setRowCount(len(records))
            
            for i, r in enumerate(records):
                # r: id, internal, cust, prod, serv, serv_no, date, out_cargo, in_cargo, status, notes
                
                # Emanet No
                item_no = QTableWidgetItem(str(r[1] or "-"))
                item_no.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                self.table.setItem(i, 0, item_no)
                
                # Müşteri & Ürün
                cust_prod = f"<b style='font-size: 13px;'>{r[2]}</b><br><span style='color: @text_muted; font-size: 11px;'>{r[3]}</span>"
                lbl_cp = QLabel(cust_prod)
                lbl_cp.setMargin(8)
                lbl_cp.setStyleSheet(theme_qss("border: none; background: transparent;"))
                self.table.setCellWidget(i, 1, lbl_cp)

                # Servis Info
                serv_info = f"<b style='font-size: 12px;'>{r[4]}</b><br><span style='color: @text_muted; font-size: 10px;'>No: {r[5]}</span>"
                lbl_serv = QLabel(serv_info)
                lbl_serv.setMargin(8)
                lbl_serv.setStyleSheet(theme_qss("border: none; background: transparent;"))
                self.table.setCellWidget(i, 2, lbl_serv)

                # Tarih
                date_item = QTableWidgetItem(format_turkish_date(str(r[6] or ""), "short"))
                date_item.setFont(QFont("Segoe UI", 11))
                self.table.setItem(i, 3, date_item)
                
                # Kargo
                cargo = f"<span style='font-size: 10px;'>↗ {r[7] or '-'}<br>↙ {r[8] or '-'}</span>"
                lbl_cargo = QLabel(cargo)
                lbl_cargo.setMargin(8)
                lbl_cargo.setStyleSheet(theme_qss("border: none; background: transparent; color: @text_muted;"))
                self.table.setCellWidget(i, 4, lbl_cargo)

                status_palette = {
                    "Onarımda": (DesignTokens.STATUS_WARNING_BG, DesignTokens.STATUS_WARNING_FG),
                    "İade Bekleniyor": (DesignTokens.MUTED, tc("text")),
                    "Hazır": (DesignTokens.STATUS_SUCCESS_BG, DesignTokens.STATUS_SUCCESS_FG),
                    "Geri Geldi": (DesignTokens.STATUS_INFO_BG, DesignTokens.STATUS_INFO_FG),
                    "Kargoya Verildi": (tc("danger_bg"), tc("danger")),
                    "Servise Ulaştı": (tc("surface_alt"), tc("accent_pressed")),
                    "Müşteriye Teslim Edildi": (DesignTokens.STATUS_SUCCESS_BG, tc("success")),
                    "Hazırlanıyor": (DesignTokens.MUTED, DesignTokens.MUTED_FOREGROUND)
                }
                st_bg, st_fg = status_palette.get(r[9], (DesignTokens.MUTED, DesignTokens.MUTED_FOREGROUND))
                st_lbl = QLabel(str(r[9] or "-"))
                st_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                st_lbl.setStyleSheet(theme_qss(f"""
                    QLabel {{
                        background-color: {st_bg};
                        color: {st_fg};
                        border-radius: 10px;
                        padding: 6px 10px;
                        font-weight: 800;
                        font-size: 11px;
                    }}
                """))
                self.table.setCellWidget(i, 5, st_lbl)

                btn_container = QWidget()
                btn_container.setStyleSheet(theme_qss(f"""
                    QWidget {{
                        background-color: {DesignTokens.SECONDARY};
                        border: 1px solid {DesignTokens.BORDER};
                        border-radius: 12px;
                    }}
                """))
                btn_layout = QHBoxLayout(btn_container)
                btn_layout.setContentsMargins(8, 8, 8, 8)
                btn_layout.setSpacing(8)
                
                btn_edit = QPushButton("✏️ Düzenle")
                btn_edit.setFixedSize(110, 44)
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
                btn_edit.clicked.connect(lambda ch, rec=r: self.edit_record(rec))
                btn_layout.addWidget(btn_edit)
                
                btn_delete = QPushButton("🗑️")
                btn_delete.setToolTip("Sil")
                btn_delete.setFixedSize(44, 44)
                btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_delete.setStyleSheet(theme_qss(DesignTokens.get_button_qss("destructive", size="sm")))
                btn_delete.clicked.connect(lambda ch, rec_id=r[0]: self.delete_record(rec_id))
                btn_layout.addWidget(btn_delete)
                
                self.table.setCellWidget(i, 6, btn_container)

        except Exception as e:
            logger.error(f"ExternalTrackingPage refresh_data error: {e}")

    def _selected_rows(self):
        return sorted(set(index.row() for index in self.table.selectionModel().selectedRows()))

    def toggle_multiselect(self, checked: bool):
        self.table.clearSelection()
        if checked:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            self.btn_multi.setToolTip("\u00c7oklu Se\u00e7im Ac\u0131k")
        else:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.btn_multi.setToolTip("\u00c7oklu Se\u00e7im")
    
    def create_stat_card(self, title, value, icon, color):
        """Modern istatistik kartı oluştur"""
        card = QFrame()
        card.setFixedHeight(100)
        card.setStyleSheet(theme_qss(f"""
            QFrame {{
                background-color: @surface;
                border-radius: 12px;
                border-left: 4px solid {color};
                border-right: 1px solid @border;
                border-top: 1px solid @border;
                border-bottom: 1px solid @border;
            }}
        """))
        
        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 6)
        card.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)
        
        # Icon
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(50, 50)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(theme_qss(f"""
            background-color: {color}20;
            color: {color};
            font-size: 24px;
            border-radius: 25px;
        """))
        layout.addWidget(icon_lbl)
        
        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(theme_qss("font-size: 24px; font-weight: 800; color: @text; border: none; background: transparent;"))
        
        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(theme_qss("font-size: 11px; font-weight: 700; color: @text_muted; border: none; background: transparent; letter-spacing: 0.5px;"))
        
        text_layout.addWidget(val_lbl)
        text_layout.addWidget(title_lbl)
        layout.addLayout(text_layout)
        layout.addStretch()
        
        return card
    
    def delete_record(self, record_id):
        """Kaydı sil"""
        from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
        if SimpleConfirmDialog(self, "Silme Onayı", "Bu kaydı silmek istediğinize emin misiniz", ok_text="Sil").exec():
            try:
                self.db.delete_external_tracking(record_id)
                show_success(self, "Kayıt başarıyla silindi.")
                self.refresh_data()
            except Exception as e:
                show_error(self, f"Silme hatası: {e}")

    def add_record(self):
        dlg = ExternalTrackingDialog(self.db, self)
        if dlg.exec():
            self.refresh_data()

    def edit_record(self, data):
        dlg = ExternalTrackingDialog(self.db, self, data=data)
        if dlg.exec():
            self.refresh_data()

    def open_selected_record(self, row, _column=0):
        try:
            records = self.db.get_external_trackings()
            if 0 <= row < len(records):
                self.edit_record(records[row])
        except Exception as e:
            logger.error(f"ExternalTrackingPage open_selected_record error: {e}")

    def open_context_menu(self, position):
        if not is_context_menu_enabled(self.db, page_id=65):
            return
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        if self.table.selectionMode() == QAbstractItemView.SelectionMode.SingleSelection:
            self.table.selectRow(row)
        try:
            records = self.db.get_external_trackings()
            selected_rows = self._selected_rows() or [row]
            valid_rows = [r for r in selected_rows if 0 <= r < len(records)]
            if not valid_rows:
                return
            record = records[row]
        except Exception as e:
            logger.error(f"ExternalTrackingPage context menu data error: {e}")
            return

        menu = QMenu(self)
        act_edit = menu.addAction("Düzenle")
        act_delete = menu.addAction("Sil")
        act_gallery = menu.addAction("Fotoğraf Galerisi")
        act_export_selected = menu.addAction("Secilileri Excel Dışa Aktar")
        chosen = menu.exec(self.table.viewport().mapToGlobal(position))

        if chosen == act_edit:
            self.edit_record(record)
        elif chosen == act_delete:
            self.delete_record(record[0])
        elif chosen == act_gallery:
            try:
                dlg = ExternalTrackingDialog(self.db, self, data=record)
                dlg.open_photo_gallery()
            except Exception as e:
                logger.error(f"ExternalTrackingPage context gallery error: {e}")
        elif chosen == act_export_selected:
            self.export_selected_to_excel(valid_rows)

    def export_selected_to_excel(self, selected_rows=None):
        try:
            selected_rows = selected_rows or self._selected_rows()
            if not selected_rows:
                show_warning(self, "Disa aktarmak icin en az bir kayit secin.")
                return
            records = self.db.get_external_trackings() or []
            export_rows = []
            for row in selected_rows:
                if 0 <= row < len(records):
                    r = records[row]
                    export_rows.append({
                        "emanet_no": r[1],
                        "musteri": r[2],
                        "urun": r[3],
                        "servis": r[4],
                        "servis_no": r[5],
                        "gidis_tarihi": r[6],
                        "gidis_kargo": r[7],
                        "donus_kargo": r[8],
                        "durum": r[9],
                        "notlar": r[10],
                    })
            if not export_rows:
                show_warning(self, "Secili kayitlar disa aktarilamadi.")
                return
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Secili Dis Takip Kayitlarini Disa Aktar",
                "dis_takip_secili.xlsx",
                "Excel Dosyasi (*.xlsx)",
            )
            if not path:
                return
            import pandas as pd
            pd.DataFrame(export_rows).to_excel(path, index=False)
            show_success(self, "Secili dis takip kayitlari Excel olarak disa aktarildi.")
        except Exception as e:
            logger.error(f"ExternalTrackingPage export_selected_to_excel error: {e}")
            show_error(self, f"Excel disa aktarimi basarisiz: {e}")

    def import_from_csv(self):
        try:
            from PyQt6.QtWidgets import QFileDialog
            from src.ui.utils.ui_helpers import show_success, show_error
            path, _ = QFileDialog.getOpenFileName(
                self, "İçe Aktar (Dış Takip)", "", "Excel Dosyasi (*.xlsx *.xls)",
            )
            if not path:
                return

            import pandas as pd
            try:
                df = pd.read_excel(path, dtype=str, keep_default_na=False)
            except Exception as e:
                show_error(self, f"Excel okunamadi: {e}")
                return

            if df is None or df.empty:
                show_error(self, "Dosya bos veya okunamadi.")
                return

            def _norm_col(c):
                c = str(c).lower().strip()
                for src_char, dst_char in [("?","i"),("?","g"),("?","u"),("?","s"),("?","o"),("?","c")]:
                    c = c.replace(src_char, dst_char)
                return c.replace("_", " ").replace("-", " ")

            col_map = {
                "emanet no": "internal_no", "emanet": "internal_no", "no": "internal_no", "internal no": "internal_no",
                "musteri": "customer", "customer": "customer", "musteri adi": "customer",
                "urun": "product", "product": "product", "parca": "product", "urun parca": "product", "malzeme": "product",
                "servis": "service", "service": "service", "gonderilen yer": "service", "yer": "service", "firma": "service",
                "servis no": "service_no", "service no": "service_no", "kayit no": "service_no", "servis kayit no": "service_no",
                "tarih": "date", "date": "date", "gonderim tarihi": "date",
                "gidis kargo": "out_cargo", "out cargo": "out_cargo", "gidis": "out_cargo", "gonderim": "out_cargo",
                "donus kargo": "in_cargo", "in cargo": "in_cargo", "donus": "in_cargo", "gelis": "in_cargo",
                "durum": "status", "status": "status",
                "notlar": "notes", "not": "notes", "notes": "notes", "aciklama": "notes"
            }

            header_found = False
            matched_cols = {}
            for col in df.columns:
                n = _norm_col(col)
                if n in col_map:
                    matched_cols[col_map[n]] = str(col)

            if "product" in matched_cols or "customer" in matched_cols:
                header_found = True
            else:
                for idx, row in df.head(10).iterrows():
                    test_matched = {}
                    for col in df.columns:
                        n = _norm_col(row[col])
                        if n in col_map:
                            test_matched[col_map[n]] = str(col)
                    if "product" in test_matched or "customer" in test_matched:
                        matched_cols = test_matched
                        header_found = True
                        df = df.iloc[idx+1:].reset_index(drop=True)
                        break

            if not header_found or ("product" not in matched_cols and "customer" not in matched_cols):
                show_error(self, "Dosyada uygun basliklar ('Urun', 'Musteri' vb.) bulunamadi!")
                return

            def _get_val(row_s, key, default=""):
                if key not in matched_cols:
                    return default
                val = str(row_s[matched_cols[key]]).strip()
                return val if val.lower() not in ["nan", "nat", "null", "none"] else default

            success, fails = 0, 0
            for _, row in df.iterrows():
                try:
                    product = _get_val(row, "product")
                    customer = _get_val(row, "customer")
                    if not product and not customer:
                        continue
                    data = {
                        "internal_no": _get_val(row, "internal_no"),
                        "customer": customer,
                        "product": product,
                        "service": _get_val(row, "service"),
                        "service_no": _get_val(row, "service_no"),
                        "date": _get_val(row, "date", __import__("datetime").datetime.now().strftime("%Y-%m-%d")),
                        "out_cargo": _get_val(row, "out_cargo"),
                        "in_cargo": _get_val(row, "in_cargo"),
                        "status": _get_val(row, "status", "Hazirlaniyor"),
                        "notes": _get_val(row, "notes"),
                    }
                    if not data["status"]:
                        data["status"] = "Hazirlaniyor"
                    self.db.add_external_tracking(data)
                    success += 1
                except Exception:
                    fails += 1

            show_success(self, f"Ice aktarma tamamlandi:\nBasarili: {success}\nHatali: {fails}")
            self.refresh_data()
        except Exception as e:
            show_error(self, f"Ice Aktarma Hatasi: {e}")

    def export_to_csv(self):
        try:
            from PyQt6.QtWidgets import QFileDialog
            from src.ui.utils.ui_helpers import show_success, show_error, show_warning
            path, _ = QFileDialog.getSaveFileName(
                self, "Disa Aktar", "Dis_Takip_Listesi.xlsx", "Excel Dosyasi (*.xlsx)"
            )
            if not path:
                return

            records = self.db.get_external_tracking() or []
            if not records:
                show_warning(self, "Disa aktarilacak kayit bulunamadi.")
                return

            import pandas as pd
            dict_rows = []
            for s in records:
                if isinstance(s, dict) or hasattr(s, "keys"):
                    dict_rows.append(dict(s))
                else:
                    dict_rows.append({
                        "id": s[0], "internal_no": s[1], "customer": s[2], "product": s[3],
                        "service": s[4], "service_no": s[5], "date": s[6], "out_cargo": s[7],
                        "in_cargo": s[8], "status": s[9], "notes": s[10]
                    })

            df = pd.DataFrame(dict_rows)
            rename_map = {
                "id": "ID", "internal_no": "Emanet No", "customer": "Musteri", "product": "Urun",
                "service": "Servis", "service_no": "Servis No", "date": "Tarih",
                "out_cargo": "Gidis Kargo", "in_cargo": "Donus Kargo", "status": "Durum", "notes": "Notlar"
            }
            df = df.rename(columns=rename_map)
            keep_cols = [rename_map[k] for k in rename_map if rename_map[k] in df.columns]
            df = df[keep_cols]
            df.to_excel(path, index=False)
            show_success(self, f"Disa aktarma tamamlandi:\n{path}")
        except Exception as e:
            show_error(self, f"Disa aktarma hatasi: {e}")

