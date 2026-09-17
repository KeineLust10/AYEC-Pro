# -*- coding: utf-8 -*-

"""
Wizard Page 3: Parts Usage and Status
Part of the modernized Technician Panel wizard interface
Includes parts table, status, and cost management
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
                             QPushButton, QFrame, QGroupBox, QTableWidget, QHeaderView,
                             QTableWidgetItem, QDateEdit, QLineEdit, QComboBox, QSizePolicy)
from PyQt6.QtCore import Qt, QDate, QEvent
from PyQt6.QtGui import QFont

from src.ui.widgets.modern_inputs import ValidatedLineEdit, ModernComboBox
from src.utils.theme_colors import theme_qss
from src.utils.status_utils import CANONICAL_DEVICE_STATUSES, normalize_device_status
from src.utils.validators import Validators
from src.utils.design_system import DesignTokens
from src.utils.currency_helper import CurrencyHelper
from src.utils.logger import logger
from datetime import datetime



class TechnicianWizardPage3(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    """Page 3: Parts Usage and Status"""
    
    def __init__(self, db, tracking_no, device_dict, parent=None):
        super().__init__(parent)
        self.db = db
        self.tracking_no = tracking_no
        self.device_dict = device_dict
        self.parent_dialog = parent
        
        # Get existing data
        self.cargo_fee = device_dict.get('cargo_fee', 0.0)
        self.delivery_type = device_dict.get('delivery_type', 'Elden')
        self.payment_status = device_dict.get('payment_status', '\u00d6denmedi')
        self.warranty_date = device_dict.get('warranty_end_date', '')
        self.warranty_status = device_dict.get('warranty_status', 'Yok')
        self._parts_loaded = False
        
        self.setup_ui()
        
        self._wire_ui_signals()
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 2)
        main_layout.setSpacing(6)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Page Title
        title = QLabel("Par\u00e7a Kullan\u0131m\u0131 ve Durum G\u00fcncelleme")
        title.setFont(QFont(DesignTokens.FONT_FAMILY, 11, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text; font-weight: bold; border: none; background: transparent;"))
        main_layout.addWidget(title)
        
        # Top section: Status and Finance
        status_finance_layout = QHBoxLayout()
        status_finance_layout.setSpacing(12)
        
        self.status_group = self.create_status_section()
        status_finance_layout.addWidget(self.status_group, 50)
        
        self.finance_group = self.create_finance_section()
        status_finance_layout.addWidget(self.finance_group, 50)
        
        main_layout.addLayout(status_finance_layout)
        
        # Parts section
        self.parts_group = self.create_parts_section()
        main_layout.addWidget(self.parts_group)

    def _wire_ui_signals(self):
        self.combo_status.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.combo_warranty.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.combo_delivery.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.combo_payment.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.combo_parts.currentIndexChanged.connect(self._on_ui_widget_changed)

    def _is_classic_appearance(self):
        try:
            return self.parent_dialog and self.parent_dialog._is_classic_appearance()
        except Exception:
            return False

    def _classic_group_qss(self):
        return """
            QGroupBox {
                background-color: #FFFFFF;
                color: #111827;
                border: 1px solid #B8C0CC;
                border-radius: 0px;
                margin-top: 12px;
                padding: 18px 8px 8px 8px;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 8px;
                padding: 0 4px;
                background-color: #FFFFFF;
                color: #111827;
                border: 0px;
            }
            QGroupBox QLabel {
                background: transparent;
                color: #111827;
                border: none;
            }
        """

    def _classic_input_qss(self):
        return """
            QLineEdit, QComboBox, QDateEdit {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #AEB4BD;
                border-radius: 2px;
                padding: 5px 7px;
                min-height: 24px;
                selection-background-color: #DCEBFF;
                selection-color: #111827;
            }
            QComboBox::drop-down {
                width: 24px;
                border-left: 1px solid #B8C0CC;
                background: #E5E7EB;
            }
        """

    def _classic_button_qss(self, primary=False):
        if primary:
            return """
                QPushButton {
                    background: #2F7DEB;
                    color: #FFFFFF;
                    border: 1px solid #1D5FB8;
                    border-radius: 2px;
                    padding: 5px 10px;
                    font-weight: 700;
                }
                QPushButton:hover { background: #2469C9; }
            """
        return """
            QPushButton {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #AEB4BD;
                border-radius: 2px;
                padding: 5px 10px;
                font-weight: 700;
            }
            QPushButton:hover { background: #F3F4F6; border-color: #1F4E79; }
        """

    def _classic_table_qss(self):
        return """
            QTableWidget {
                background: #FFFFFF;
                color: #111827;
                alternate-background-color: #F7F8FA;
                gridline-color: #D1D5DB;
                border: 1px solid #B8C0CC;
                border-radius: 0px;
                selection-background-color: #DCEBFF;
                selection-color: #111827;
            }
            QTableWidget::item {
                color: #111827;
                padding: 6px;
                border-bottom: 1px solid #E5E7EB;
            }
            QTableWidget::item:selected {
                background: #DCEBFF;
                color: #111827;
            }
            QHeaderView {
                background: #E5E7EB;
                color: #111827;
                border: none;
            }
            QHeaderView::section {
                background: #E5E7EB;
                color: #111827;
                padding: 6px;
                border: 1px solid #B8C0CC;
                font-weight: 700;
            }
        """

    def apply_classic_styles(self):
        if not self._is_classic_appearance():
            return
        self.setProperty("skipThemeTransform", False)
        self.setAutoFillBackground(True)
        self.setStyleSheet("QWidget { background: #F3F4F6; color: #111827; } QLabel { background: transparent; color: #111827; border: none; }")
        for group in self.findChildren(QGroupBox):
            group.setProperty("skipThemeTransform", False)
            group.setAutoFillBackground(True)
            group.setStyleSheet(self._classic_group_qss())
        for frame in self.findChildren(QFrame):
            frame.setProperty("skipThemeTransform", False)
            frame.setAutoFillBackground(True)
            frame.setStyleSheet("QFrame { background: #FFFFFF; color: #111827; border: 1px solid #B8C0CC; border-radius: 0px; }")
        for label in self.findChildren(QLabel):
            label.setProperty("skipThemeTransform", False)
            label.setStyleSheet("color: #111827; background: transparent; border: none;")
        for editor_type in (QLineEdit, QComboBox, QDateEdit):
            for editor in self.findChildren(editor_type):
                editor.setProperty("skipThemeTransform", False)
                editor.setStyleSheet(self._classic_input_qss())
        for table in self.findChildren(QTableWidget):
            table.setProperty("skipThemeTransform", False)
            table.horizontalHeader().setProperty("skipThemeTransform", False)
            table.verticalHeader().setProperty("skipThemeTransform", False)
            table.setStyleSheet(self._classic_table_qss())
        for button in self.findChildren(QPushButton):
            button.setProperty("skipThemeTransform", False)
            is_primary = button.text() in {"Se\u00e7iliyi Kullan", "Se\u00e7iliyi Kullan", "Manuel \u00dcr\u00fcn/Hizmet", "Manuel \u00dcr\u00fcn/Hizmet"}
            button.setStyleSheet(self._classic_button_qss(primary=is_primary))
        
    
    def create_status_section(self):
        """Create status and delivery section"""
        group = QGroupBox("\U0001f4e6 Servis Durumu ve Teslimat")
        group.setTitle("Servis Durumu ve Teslimat")
        group.setFont(QFont(DesignTokens.FONT_FAMILY, 10, QFont.Weight.Bold))
        group.setStyleSheet(theme_qss(f"""
            QGroupBox {{
                background: transparent;
                border: none;
                border-top: 1px solid {DesignTokens.BORDER};
                border-radius: 0;
                padding: 4px 0 0 0;
                margin-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 0px;
                padding: 0 8px 4px 0;
                color: {DesignTokens.FOREGROUND};
            }}
        """))

        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(6)
        
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setVerticalSpacing(6)
        
        # Servis Durumu
        lbl_status = QLabel("Servis Durumu:")
        lbl_status.setStyleSheet(theme_qss(f"color: {DesignTokens.FOREGROUND}; font-weight: 600; border: none; background: transparent;"))
        grid.addWidget(lbl_status, 0, 0)
        
        self.combo_status = ModernComboBox(items=CANONICAL_DEVICE_STATUSES)
        self.combo_status.setCurrentText(normalize_device_status(self.device_dict.get('status', 'Bekliyor')))
        self.combo_status.setAccessibleName("servis_durumu")
        self.combo_status.setMinimumHeight(32)
        grid.addWidget(self.combo_status, 1, 0)
        
        # Garanti Durumu
        lbl_warranty = QLabel("Garanti Durumu:")
        lbl_warranty.setStyleSheet(theme_qss(f"color: {DesignTokens.FOREGROUND}; font-weight: 600; border: none; background: transparent;"))
        grid.addWidget(lbl_warranty, 0, 1)
        
        self.combo_warranty = ModernComboBox(items=["Yok", "Var", "Devam Ediyor", "Bitti"])
        if self.warranty_status:
            self.combo_warranty.setCurrentText(self.warranty_status)
        self.combo_warranty.setAccessibleName("garanti_durumu")
        self.combo_warranty.setMinimumHeight(32)
        grid.addWidget(self.combo_warranty, 1, 1)
        
        # Garanti Biti\u015f
        lbl_warranty_end = QLabel("Garanti Biti\u015f Tarihi:")
        lbl_warranty_end.setStyleSheet(theme_qss(f"color: {DesignTokens.FOREGROUND}; font-weight: 600; border: none; background: transparent;"))
        grid.addWidget(lbl_warranty_end, 2, 0)
        
        self.date_warranty = QDateEdit()
        self.date_warranty.setCalendarPopup(True)
        if self.warranty_date:
            try:
                self.date_warranty.setDate(QDate.fromString(self.warranty_date, "yyyy-MM-dd"))
            except Exception:
                self.date_warranty.setDate(QDate.currentDate())
        else:
            self.date_warranty.setDate(QDate.currentDate())
        self.date_warranty.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.date_warranty.setAccessibleName("garanti_bitis_tarihi")
        self.date_warranty.setMinimumHeight(32)
        grid.addWidget(self.date_warranty, 3, 0)
        
        # Teslimat T\u00fcr\u00fc
        lbl_delivery = QLabel("Teslimat T\u00fcr\u00fc:")
        lbl_delivery.setStyleSheet(theme_qss(f"color: {DesignTokens.FOREGROUND}; font-weight: 600; border: none; background: transparent;"))
        grid.addWidget(lbl_delivery, 2, 1)
        
        self.combo_delivery = ModernComboBox(items=["Elden", "Kargo", "Servis Arac\u0131", "Kurye"])
        if self.delivery_type:
            self.combo_delivery.setCurrentText(self.delivery_type)
        self.combo_delivery.setAccessibleName("teslimat_t\u00fcr\u00fc")
        self.combo_delivery.setMinimumHeight(32)
        grid.addWidget(self.combo_delivery, 3, 1)
        
        layout.addLayout(grid)
        return group
    
    def create_finance_section(self):
        """Create finance section"""
        group = QGroupBox("\U0001f4b0 Finansal Bilgiler")
        group.setTitle("Finansal Bilgiler")
        group.setFont(QFont(DesignTokens.FONT_FAMILY, 10, QFont.Weight.Bold))
        group.setStyleSheet(theme_qss(f"""
            QGroupBox {{
                background: transparent;
                border: none;
                border-top: 1px solid {DesignTokens.BORDER};
                border-radius: 0;
                padding: 4px 0 0 0;
                margin-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 0px;
                padding: 0 8px 4px 0;
                color: {DesignTokens.FOREGROUND};
            }}
        """))

        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(6)
        
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setVerticalSpacing(6)
        
        # \u0130\u015f\u00e7ilik
        lbl_labor = QLabel(f"Servis \u00dccreti ({CurrencyHelper.get_label(db=self.db)}):")
        lbl_labor.setStyleSheet(theme_qss(f"color: {DesignTokens.FOREGROUND}; font-weight: 600; border: none; background: transparent;"))
        lbl_labor.setContentsMargins(0, 0, 0, 6)
        grid.addWidget(lbl_labor, 0, 0)
        
        self.inp_labor = ValidatedLineEdit("0.00", validator_func=Validators.is_numeric)
        self.inp_labor.setText(str(self.device_dict.get('labor_cost', "0.00")))
        self.inp_labor.setStyleSheet(theme_qss(f"color: @text;"))
        self.inp_labor.setMinimumHeight(32)
        self.inp_labor.setAccessibleName("servis_ucreti")
        grid.addWidget(self.inp_labor, 1, 0)
        
        # Par\u00e7a Maliyeti (read-only, TRY e\u015fde\u011feri)
        lbl_part_cost = QLabel(f"Par\u00e7a Maliyeti ({CurrencyHelper.get_label(db=self.db)} toplam):")
        lbl_part_cost.setStyleSheet(theme_qss(f"color: {DesignTokens.FOREGROUND}; font-weight: 600; border: none; background: transparent;"))
        lbl_part_cost.setContentsMargins(0, 0, 0, 6)
        grid.addWidget(lbl_part_cost, 0, 1)
        
        self.inp_part_cost = ValidatedLineEdit("0.00")
        self.inp_part_cost.setReadOnly(True)
        self.inp_part_cost.setStyleSheet(theme_qss(f"background: {DesignTokens.BORDER}20; color: {DesignTokens.MUTED_FOREGROUND};"))
        self.inp_part_cost.setMinimumHeight(32)
        self.inp_part_cost.setAccessibleName("parca_maliyeti")
        grid.addWidget(self.inp_part_cost, 1, 1)
        
        # Kargo \u00dccreti
        lbl_cargo = QLabel(f"Kargo \u00dccreti ({CurrencyHelper.get_label(db=self.db)}):")
        lbl_cargo.setStyleSheet(theme_qss(f"color: {DesignTokens.FOREGROUND}; font-weight: 600; border: none; background: transparent;"))
        lbl_cargo.setContentsMargins(0, 0, 0, 6)
        grid.addWidget(lbl_cargo, 2, 0)
        
        self.inp_cargo = ValidatedLineEdit("0.00", validator_func=Validators.is_numeric)
        if self.cargo_fee:
            self.inp_cargo.setText(str(self.cargo_fee))
        self.inp_cargo.setStyleSheet(theme_qss(f"color: @text;"))
        self.inp_cargo.setMinimumHeight(32)
        self.inp_cargo.setAccessibleName("kargo_ucreti")
        grid.addWidget(self.inp_cargo, 3, 0)
        
        # \u00d6deme Durumu
        lbl_payment = QLabel("\u00d6deme Tipi:")
        lbl_payment.setStyleSheet(theme_qss(f"color: {DesignTokens.FOREGROUND}; font-weight: 600; border: none; background: transparent;"))
        lbl_payment.setContentsMargins(0, 0, 0, 6)
        grid.addWidget(lbl_payment, 2, 1)
        
        self.combo_payment = ModernComboBox(items=[
            "Cari Hesap", "Pe\u015fin", "Kredi Kart\u0131", "Havale", "\u00d6denmedi"
        ])
        if self.payment_status:
            self.combo_payment.setCurrentText(self.payment_status)
        self.combo_payment.setMinimumHeight(32)
        self.combo_payment.setAccessibleName("odeme_tipi")
        grid.addWidget(self.combo_payment, 3, 1)
        
        layout.addLayout(grid)
        return group
    
    def create_parts_section(self):
        """Create parts usage section"""
        group = QGroupBox("\U0001f527 Kullan\u0131lan Par\u00e7alar")
        group.setTitle("Kullan\u0131lan Par\u00e7alar")
        group.setFont(QFont(DesignTokens.FONT_FAMILY, 10, QFont.Weight.Bold))
        group.setStyleSheet(theme_qss(f"""
            QGroupBox {{
                background: transparent;
                border: none;
                border-top: 1px solid {DesignTokens.BORDER};
                border-radius: 0;
                padding: 4px 0 0 0;
                margin-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 0px;
                padding: 0 8px 4px 0;
                color: {DesignTokens.FOREGROUND};
            }}
        """))

        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(6)
        
        # Part selection row
        part_row = QHBoxLayout()
        part_row.setSpacing(8)

        self.combo_stock_location = ModernComboBox()
        self.combo_stock_location.setMinimumWidth(150)
        self.combo_stock_location.setAccessibleName("stok_kaynagi")
        for location in self.db.get_stock_locations(active_only=True):
            self.combo_stock_location.addItem(location["name"], location["id"])
        self.combo_stock_location.currentIndexChanged.connect(
            self._on_stock_location_changed
        )
        part_row.addWidget(self.combo_stock_location, 1)
        
        self.combo_parts = ModernComboBox()
        self.combo_parts.addItem("-- Parca Secin --", 0)
        self.combo_parts.installEventFilter(self)
        self.combo_parts.setAccessibleName("parca_secimi")
        part_row.addWidget(self.combo_parts, 2)
        
        btn_use = QPushButton("+ Se\u00e7iliyi Kullan")
        btn_use.setFixedHeight(36)
        btn_use.setMinimumWidth(130)
        btn_use.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        btn_use.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_use.clicked.connect(self.use_part)
        part_row.addWidget(btn_use)
        
        # Barcode input
        self.inp_barcode_part = ValidatedLineEdit("Barkod okutun...")
        self.inp_barcode_part.setFixedWidth(112)
        self.inp_barcode_part.setFixedHeight(36)
        self.inp_barcode_part.returnPressed.connect(self.scan_part_barcode)
        self.inp_barcode_part.setAccessibleName("parca_barkodu")
        part_row.addWidget(self.inp_barcode_part)
        
        btn_manual = QPushButton("\ud83d\uded2 Manuel \u00dcr\u00fcn/Hizmet")
        btn_manual.setFixedHeight(36)
        btn_manual.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        btn_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_manual.clicked.connect(self.add_manual_product)
        part_row.addWidget(btn_manual)
        
        layout.addLayout(part_row)
        
        # Parts table
        self.table_used_parts = QTableWidget()
        self.table_used_parts.setMinimumHeight(280)
        self.table_used_parts.setMaximumHeight(450)
        self.table_used_parts.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table_used_parts.setColumnCount(4)
        self.table_used_parts.setHorizontalHeaderLabels(["Par\u00e7a / Hizmet", "Tutar", "Tarih", "\u0130\u015flem"])
        self.table_used_parts.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_used_parts.verticalHeader().setVisible(False)
        self.table_used_parts.setShowGrid(False)
        self.table_used_parts.setAccessibleName("kullanilan_parcalar_tablosu")
        self.table_used_parts.setStyleSheet(theme_qss(f"""
            QTableWidget {{
                border: 1px solid {DesignTokens.BORDER};
                border-radius: 8px;
                background: @surface;
            }}
            QTableWidget::item {{
                color: @text;
                padding: 8px;
            }}
            QTableWidget::item:selected {{
                background: @border;
                color: @selection_text;
            }}
            QHeaderView::section {{
                background: {DesignTokens.SECONDARY};
                padding: 12px;
                border: none;
                font-weight: 700;
                color: {DesignTokens.MUTED_FOREGROUND};
                border-bottom: 2px solid {DesignTokens.BORDER};
            }}
        """))
        
        layout.addWidget(self.table_used_parts)
        self.load_used_parts()
        
        return group

    def eventFilter(self, obj, event):
        if obj is getattr(self, "combo_parts", None) and event.type() in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.FocusIn,
        ):
            self.ensure_parts_loaded()
        return super().eventFilter(obj, event)

    def ensure_parts_loaded(self):
        if not self._parts_loaded:
            self.load_parts()

    def _on_stock_location_changed(self, _index=None):
        self._parts_loaded = False
        self.load_parts()

    def load_parts(self):
        """Load parts from stock database"""
        try:
            if self._parts_loaded:
                return
            self.combo_parts.clear()
            self.combo_parts.addItem("-- Parca Secin --", 0)

            location_id = self.combo_stock_location.currentData()
            cur = self.db.conn.cursor()
            cur.execute("""
                SELECT p.id, p.name, p.price, COALESCE(b.quantity, 0),
                       COALESCE(p.currency, 'TRY') AS currency
                FROM parts p
                JOIN stock_location_balances b ON b.part_id=p.id
                WHERE b.location_id=?
                  AND (p.is_deleted=0 OR p.is_deleted IS NULL)
                  AND COALESCE(b.quantity, 0)>0
                ORDER BY p.name
                LIMIT 250
            """, (location_id,))
            parts = cur.fetchall()
            for p in parts:
                currency = str(p[4] or 'TRY').upper()
                self.combo_parts.addItem(
                    f"{p[1]} (Stok: {p[3]}) - {CurrencyHelper.format_amount(p[2], currency_code=currency)}",
                    p[0],
                )
            self._parts_loaded = True

        except Exception as e:
            logger.error(f"TechnicianWizardPage3.load_parts error: {e}")
    
    def load_used_parts(self):
        """Load used parts table"""
        try:
            self.table_used_parts.setRowCount(0)

            # Detect schema (currency column may or may not exist)
            try:
                cur = self.db.conn.cursor()
                cur.execute("PRAGMA table_info(used_parts)")
                _cols = [r[1] for r in cur.fetchall()]
            except Exception:
                _cols = []
            has_currency = "currency" in _cols
            has_quantity = "quantity" in _cols
            has_rate = "exchange_rate" in _cols
            has_price_try = "price_try" in _cols
            deleted_col = "is_deleted" if "is_deleted" in _cols else ("is_archived" if "is_archived" in _cols else None)

            query = (
                "SELECT id, part_name, price, created_at, {currency}, "
                "{quantity}, {rate}, {price_try} FROM used_parts "
                "WHERE tracking_no=? ORDER BY id DESC"
            ).format(
                currency="COALESCE(currency,'TRY')" if has_currency else "'TRY'",
                quantity="COALESCE(quantity,1)" if has_quantity else "1",
                rate="COALESCE(exchange_rate,1)" if has_rate else "1",
                price_try="COALESCE(price_try,0)" if has_price_try else "0",
            )
            if deleted_col:
                query = query.replace("WHERE tracking_no=?", f"WHERE tracking_no=? AND ({deleted_col}=0 OR {deleted_col} IS NULL)")

            cur = self.db.conn.cursor()
            cur.execute(query, (self.tracking_no,))
            parts = cur.fetchall()

            total_cost_try = 0.0

            for p in parts:
                row = self.table_used_parts.rowCount()
                self.table_used_parts.insertRow(row)

                part_currency = str(p[4] or 'TRY').upper()
                price_val = float(p[2] or 0)
                quantity = float(p[5] or 1)
                stored_rate = float(p[6] or 0)
                stored_price_try = float(p[7] or 0)

                self.table_used_parts.setItem(row, 0, QTableWidgetItem(str(p[1])))
                self.table_used_parts.setItem(
                    row,
                    1,
                    QTableWidgetItem(
                        CurrencyHelper.format_amount(
                            price_val * quantity, currency_code=part_currency
                        )
                    ),
                )
                self.table_used_parts.setItem(row, 2, QTableWidgetItem(str(p[3])))

                # Delete button
                btn_del = QPushButton("\U0001f5d1")
                btn_del.setFixedSize(35, 35)
                btn_del.setStyleSheet(theme_qss("""
                    QPushButton { background: @danger; color: @selection_text; border-radius: 4px; }
                    QPushButton:hover { background: @danger; }
                """))
                btn_del.clicked.connect(lambda checked, part_id=p[0]: self.delete_part(part_id))
                self.table_used_parts.setCellWidget(row, 3, btn_del)

                # Convert to TRY for running total
                unit_try = stored_price_try
                if unit_try <= 0:
                    if part_currency == "TRY":
                        unit_try = price_val
                    elif stored_rate > 1:
                        unit_try = price_val * stored_rate
                    else:
                        unit_try = CurrencyHelper.convert_amount(
                            self.db, price_val, part_currency, "TRY"
                        )
                total_cost_try += unit_try * quantity

            self.inp_part_cost.setText(
                CurrencyHelper.format_try_for_display(
                    total_cost_try,
                    db=self.db,
                    include_try_reference=False,
                )
            )

        except Exception as e:
            logger.error(f"TechnicianWizardPage3.load_used_parts error: {e}")
    
    def use_part(self):
        """Use selected part from stock"""
        if self.combo_parts.currentIndex() == 0:
            from src.utils.toast_notification import show_warning
            show_warning(self, "L\u00fctfen bir par\u00e7a se\u00e7in")
            return
        
        part_id = self.combo_parts.currentData()
        
        try:
            # use_part handles stock check, stock reduction, and used_parts snapshot
            success = self.db.use_part(
                part_id,
                1,
                self.tracking_no,
                location_id=self.combo_stock_location.currentData(),
            )
            
            if success:
                from src.utils.toast_notification import show_success
                show_success(self, "Par\u00e7a ba\u015far\u0131yla eklendi")
                self._parts_loaded = False
                self.load_parts()
                self.load_used_parts()
                if self.parent_dialog and hasattr(self.parent_dialog, "refresh_logs"):
                    self.parent_dialog.refresh_logs()
            else:
                from src.utils.toast_notification import show_error
                show_error(self, "Stok yetersiz veya par\u00e7a bulunamad\u0131")
            
        except Exception as e:
            from src.utils.toast_notification import show_error
            show_error(self, f"Par\u00e7a kullanamad\u0131: {e}")
    
    def scan_part_barcode(self):
        """Scan part barcode"""
        barcode = self.inp_barcode_part.text().strip()
        if not barcode:
            return
        
        try:
            cur = self.db.conn.cursor()
            cur.execute("SELECT id, name FROM parts WHERE barcode=?", (barcode,))
            part = cur.fetchone()
            
            if part:
                part_id, part_name = part
                # use_part handles everything
                if self.db.use_part(
                    part_id,
                    1,
                    self.tracking_no,
                    location_id=self.combo_stock_location.currentData(),
                ):
                    from src.utils.toast_notification import show_success
                    show_success(self, f"{part_name} eklendi")
                    self.inp_barcode_part.clear()
                    self._parts_loaded = False
                    self.load_parts()
                    self.load_used_parts()
                    if self.parent_dialog and hasattr(self.parent_dialog, "refresh_logs"):
                        self.parent_dialog.refresh_logs()
                else:
                    from src.utils.toast_notification import show_error
                    show_error(self, "Stok yetersiz!")
            else:
                from src.utils.toast_notification import show_warning
                show_warning(self, "Barkod bulunamad\u0131")
                
        except Exception as e:
            logger.error(f"TechnicianWizardPage3.scan_part_barcode error: {e}")
    
    def add_manual_product(self):
        """Add manual product/service"""
        from src.ui.dialogs.technician_panel import ModernManualProductDialog
        
        dialog = ModernManualProductDialog(self)
        if dialog.exec():
            if dialog.result_data:
                name, price = dialog.result_data
                
                try:
                    # Use add_used_part for manual entries (no stock deduction)
                    self.db.add_used_part(self.tracking_no, name, price)
                    
                    from src.utils.toast_notification import show_success
                    show_success(self, f"{name} eklendi")
                    self.load_used_parts()
                    if self.parent_dialog and hasattr(self.parent_dialog, "refresh_logs"):
                        self.parent_dialog.refresh_logs()
                    
                except Exception as e:
                    from src.utils.toast_notification import show_error
                    show_error(self, f"Eklenemedi: {e}")
    
    def delete_part(self, part_id):
        """Delete used part"""
        try:
            remove_ok = self.db.remove_used_part(part_id) if hasattr(self.db, "remove_used_part") else self.db.soft_delete_record("used_parts", "id", part_id)
            if not remove_ok:
                raise RuntimeError("Parca kaydi silinemedi")
            
            from src.utils.toast_notification import show_success
            show_success(self, "Par\u00e7a silindi")
            
            self.load_used_parts()
            if self.parent_dialog and hasattr(self.parent_dialog, "refresh_logs"):
                self.parent_dialog.refresh_logs()
            
        except Exception as e:
            from src.utils.toast_notification import show_error
            show_error(self, f"Silinemedi: {e}")
    
    def get_data(self):
        """Collect data from this page"""
        labor = Validators.parse_numeric(self.inp_labor.text(), default=0.0) or 0.0
        cargo = Validators.parse_numeric(self.inp_cargo.text(), default=0.0) or 0.0
        
        return {
            'status': self.combo_status.currentText(),
            'labor_cost': labor,
            'cargo_fee': cargo,
            'delivery_type': self.combo_delivery.currentText(),
            'payment_status': self.combo_payment.currentText(),
            'warranty_status': self.combo_warranty.currentText(),
            'warranty_end_date': self.date_warranty.date().toString("yyyy-MM-dd")
        }
