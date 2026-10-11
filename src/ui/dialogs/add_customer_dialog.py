# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, 
                             QRadioButton, QCheckBox, QGridLayout, QTextEdit, 
                             QScrollArea, QFrame, QCompleter, QLineEdit, QGraphicsDropShadowEffect,
                             QTabWidget, QWidget, QSpacerItem, QSizePolicy, QPushButton, QComboBox, QDialog)
from PyQt6.QtCore import Qt, QTimer, QSignalBlocker
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QPainterPath
from datetime import datetime
from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.modern_inputs import ValidatedLineEdit, ModernComboBox
from src.utils.theme_colors import theme_qss, qc
from src.utils.design_system import DesignTokens
from src.utils.currency_helper import CurrencyHelper
from src.utils.validators import Validators
from src.utils.address_data import GONEN_MAHALLELER, GONEN_CADDELER, BALIKESIR_ILCELER, get_mahalleler
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.logger import logger
from src.services.tomtom_geocoder import TomTomGeocoder
from src.utils.local_secret_store import load_secret

from src.utils.mail_manager import MailWorker
import webbrowser
import os

class CustomerReferenceGlyph(QWidget):
    """Native palette-aware glyphs for the reference customer canvas."""

    def __init__(self, kind="customer", token="finance_primary", framed=False, parent=None):
        super().__init__(parent)
        self.kind, self.token, self.framed = kind, token, framed
        self.setObjectName("customerReferenceGlyph")
        self.setFixedSize(24 if framed else 14, 24 if framed else 14)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(self.width() / 24, self.height() / 24)
        color = qc(self.token)
        if self.framed:
            fill, border = QColor(color), QColor(color)
            fill.setAlpha(24)
            border.setAlpha(80)
            painter.setPen(QPen(border, 1))
            painter.setBrush(fill)
            painter.drawRoundedRect(1, 1, 22, 22, 4, 4)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color, 1.6))
        if self.kind == "customer":
            painter.drawEllipse(6, 4, 6, 6)
            painter.drawArc(4, 12, 11, 9, 0, 180 * 16)
            painter.drawLine(18, 8, 18, 14)
            painter.drawLine(15, 11, 21, 11)
        elif self.kind == "address":
            painter.drawEllipse(5, 3, 14, 14)
            painter.drawEllipse(10, 8, 4, 4)
            painter.drawLine(7, 15, 12, 21)
            painter.drawLine(17, 15, 12, 21)
        elif self.kind == "phone":
            path = QPainterPath()
            path.moveTo(5, 4)
            path.lineTo(9, 4)
            path.lineTo(10, 9)
            path.lineTo(8, 11)
            path.cubicTo(10, 15, 12, 17, 15, 17)
            path.lineTo(17, 14)
            path.lineTo(21, 16)
            path.lineTo(21, 20)
            path.cubicTo(10, 24, 1, 10, 5, 4)
            painter.drawPath(path)
        elif self.kind == "finance":
            painter.drawEllipse(3, 3, 18, 18)
            painter.drawLine(12, 6, 12, 18)
            painter.drawLine(8, 8, 16, 8)
            painter.drawLine(8, 12, 16, 12)
            painter.drawLine(8, 16, 16, 16)
        elif self.kind == "notes":
            painter.drawRect(4, 4, 14, 16)
            for y in (8, 12, 16):
                painter.drawLine(7, y, 15, y)
        else:
            painter.drawRoundedRect(5, 5, 14, 14, 2, 2)
            painter.drawRect(9, 9, 6, 6)
            for edge in (8, 16):
                painter.drawLine(edge, 2, edge, 5)
                painter.drawLine(edge, 19, edge, 22)


class CustomerReferenceInput(ValidatedLineEdit):
    """Keep validation colors while applying the compact reference density."""

    DENSITY_MARKER = "/* customer-reference-density */"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_reference_density()

    def _apply_reference_density(self):
        base = self.styleSheet().split(self.DENSITY_MARKER)[0]
        self.setStyleSheet(base + self.DENSITY_MARKER + "QLineEdit { min-height: 18px; padding: 5px 8px; border-radius: 4px; font-size: 11px; }")
        self.setFixedHeight(32)

    def validate(self):
        super().validate()
        self._apply_reference_density()


class AddCustomerDialog(ModernDialog):
    SECTOR_ID = None

    def __init__(self, db, parent=None, customer_data=None, sector_manager=None):
        title = "Yeni M\u00fc\u015fteri Ekle" if not customer_data else "M\u00fc\u015fteri D\u00fczenle"
        # Adjusted size for tabbed layout
        super().__init__(title, parent, width=900, height=680)
        self.db = db
        self.sector_manager = sector_manager  # 🆕 Plugin System
        self.customer_data = customer_data
        self.saved_customer_id = None
        self.saved_customer_name = None
        self.plugin_customer_fields = self.sector_manager.get_customer_fields() if self.sector_manager else []
        self.plugin_customer_widgets = {}
        self.location_coordinates = None
        self._geocode_serial = 0
        self._syncing_location_fields = False
        try:
            self.tomtom_api_key = load_secret("tomtom_traffic_api_key") or ""
        except Exception as error:
            logger.warning("Customer map key could not be loaded: %s", error)
            self.tomtom_api_key = ""
        self.geocoder = TomTomGeocoder(self.tomtom_api_key, self)
        self.geocoder.resolved.connect(self._on_geocode_resolved)
        self._address_geocode_timer = QTimer(self)
        self._address_geocode_timer.setSingleShot(True)
        self._address_geocode_timer.setInterval(900)
        self._address_geocode_timer.timeout.connect(self._geocode_current_address)

        self.setup_content()
        self.txt_address.textChanged.connect(self._schedule_address_geocode)
        self.cmb_city.currentTextChanged.connect(self._schedule_address_geocode)
        self.cmb_district.currentTextChanged.connect(self._schedule_address_geocode)
        self.cmb_neighborhood.currentTextChanged.connect(self._schedule_address_geocode)
        self.inp_street.textChanged.connect(self._schedule_address_geocode)
        # UI önce çizilsin, veri işlemleri sonraki event turunda başlasın.
        QTimer.singleShot(0, self._deferred_bootstrap)

    def _deferred_bootstrap(self):
        if self.customer_data:
            self.load_customer_data()
        else:
            self._apply_default_location_from_settings()

    def _make_field(self, label, placeholder, validator=None):
        v = QVBoxLayout(); v.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(theme_qss("color: @text_muted; font-weight: 700; font-size: 11px; border: none; background: transparent;"))
        inp = CustomerReferenceInput(placeholder, validator_func=validator)
        v.addWidget(lbl); v.addWidget(inp)
        return v, inp

    def _make_combo(self, label, items, editable=False):
        v = QVBoxLayout(); v.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(theme_qss("color: @text_muted; font-weight: 700; font-size: 11px; border: none; background: transparent;"))
        cmb = ModernComboBox(items=items, editable=editable)
        self._compact_combo(cmb)
        v.addWidget(lbl); v.addWidget(cmb)
        return v, cmb

    def _compact_combo(self, combo):
        combo.set_reference_chevron()
        combo.setStyleSheet(combo.styleSheet() + "QComboBox { min-height: 18px; padding: 4px 8px; border-radius: 4px; font-size: 11px; }")
        combo.setFixedHeight(32)
        if combo.lineEdit() is not None:
            editor = combo.lineEdit()
            editor.setMinimumHeight(0)
            editor.setMaximumHeight(24)
            editor.setStyleSheet(theme_qss("QLineEdit { background: transparent; color: @text; border: none; padding: 0; min-height: 0; font-size: 11px; }"))

    def _card(self, title, icon, inner_layout):
        frame = QFrame()
        frame.setObjectName("customerReferenceCard")
        frame.setStyleSheet(theme_qss("QFrame#customerReferenceCard { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"))
        lay = QVBoxLayout(frame); lay.setContentsMargins(1, 0, 1, 2); lay.setSpacing(6)
        hdr = QHBoxLayout()
        accent = {"Temel Bilgiler": "@finance_primary", "\u0130leti\u015fim Bilgileri": "@finance_tertiary", "Finans & Vergi": "@warning", "Adres Bilgileri": "@danger", "\u00d6zel Notlar": "@finance_primary", "Sekt\u00f6rel Bilgiler": "@finance_secondary"}.get(title, "@text")
        kind = {"Temel Bilgiler": "customer", "\u0130leti\u015fim Bilgileri": "phone", "Finans & Vergi": "finance", "Adres Bilgileri": "address", "\u00d6zel Notlar": "notes"}.get(title, "sector")
        lbl_icon = CustomerReferenceGlyph(kind, accent.lstrip("@"))
        lbl_title = QLabel(title.upper()); lbl_title.setStyleSheet(theme_qss(f"color: {accent}; font-size: 10px; font-weight: 800; letter-spacing: 0px; border: none; background: transparent;"))
        hdr.addWidget(lbl_icon); hdr.addWidget(lbl_title); hdr.addStretch()
        lay.addLayout(hdr); lay.addLayout(inner_layout)
        return frame

    def _active_sector_id(self):
        if self.SECTOR_ID:
            return self.SECTOR_ID
        try:
            if self.sector_manager and self.sector_manager.get_current_plugin():
                return self.sector_manager.get_current_plugin().sector_id
        except Exception:
            pass
        return "teknik_servis"

    def _create_plugin_input(self, field):
        field_type = str(field.get("type", "text") or "text").lower()
        if field_type == "select":
            widget = ModernComboBox(items=field.get("options", []), editable=True)
            self._compact_combo(widget)
            return widget
        widget = CustomerReferenceInput(field.get("placeholder", "") or field.get("title", ""))
        return widget

    def _build_plugin_customer_card(self):
        if not self.plugin_customer_fields:
            return None
        grid = QGridLayout()
        grid.setSpacing(8)
        for index, field in enumerate(self.plugin_customer_fields):
            column = index % 2
            row = index // 2
            wrapper = QVBoxLayout()
            wrapper.setSpacing(4)
            title = field.get("title", field.get("name", "Alan"))
            if field.get("required"):
                title = f"{title} *"
            lbl = QLabel(title)
            lbl.setStyleSheet(theme_qss("color: @text_muted; font-weight: 700; font-size: 11px; border: none; background: transparent;"))
            widget = self._create_plugin_input(field)
            self.plugin_customer_widgets[field["name"]] = widget
            wrapper.addWidget(lbl)
            wrapper.addWidget(widget)
            span = 2 if index == len(self.plugin_customer_fields) - 1 and column == 0 else 1
            grid.addLayout(wrapper, row, column, 1, span)
        return self._card("Sektörel Bilgiler", "🧩", grid)

    def _collect_plugin_customer_values(self):
        values = {}
        for field in self.plugin_customer_fields:
            widget = self.plugin_customer_widgets.get(field["name"])
            if widget is None:
                continue
            if isinstance(widget, (ModernComboBox, QComboBox)):
                values[field["name"]] = widget.currentText().strip()
            else:
                values[field["name"]] = widget.text().strip()
        return values

    def _set_plugin_customer_values(self, payload):
        for field in self.plugin_customer_fields:
            widget = self.plugin_customer_widgets.get(field["name"])
            if widget is None:
                continue
            value = payload.get(field["name"], "")
            if isinstance(widget, (ModernComboBox, QComboBox)):
                widget.setCurrentText("" if value is None else str(value))
            else:
                widget.setText("" if value is None else str(value))

    def _build_reference_header(self):
        row = self.header.layout()
        row.setContentsMargins(18, 0, 18, 0)
        row.setSpacing(8)
        row.removeWidget(self.logo_label)
        self.logo_label.hide()
        self.header.setObjectName("customerReferenceHeader")
        self.header.setStyleSheet(theme_qss(
            "QFrame#customerReferenceHeader { background: @finance_surface; border: none; border-bottom: 1px solid @finance_outline; border-top-left-radius: 6px; border-top-right-radius: 6px; }"))
        self.reference_header_glyph = CustomerReferenceGlyph(framed=True, parent=self.header)
        row.insertWidget(0, self.reference_header_glyph)
        self.lbl_title.setStyleSheet(theme_qss(
            "color: @text; font-size: 12px; font-weight: 700; letter-spacing: 0px; border: none; background: transparent;"))
        self.reference_header_badge = QLabel("Cari Kart Tan\u0131m\u0131")
        self.reference_header_badge.setFixedHeight(18)
        self.reference_header_badge.setStyleSheet(theme_qss(
            "color: @text_muted; background: @finance_surface_alt; border: 1px solid @finance_outline; border-radius: 4px; padding: 0 6px; font-size: 9px; letter-spacing: 0px;"))
        row.insertWidget(row.indexOf(self.lbl_title) + 1, self.reference_header_badge)
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setText("\u00d7")
        self.btn_close.setAccessibleName("Kapat")
        self.btn_close.setStyleSheet(theme_qss(
            "QPushButton { background: transparent; color: @text_muted; border: none; border-radius: 4px; padding: 0; font-size: 16px; }"
            "QPushButton:hover { background: @finance_surface_alt; color: @text; }"))

    def setup_content(self):
        self.set_footer_visible(True, 58)
        self.header.setFixedHeight(52)
        self.lbl_title.setFont(QFont(self.font().family(), 10, QFont.Weight.Bold))
        self._build_reference_header()
        self.clear_footer()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # Card boyutu
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        new_w = min(864, max(480, screen.width() - 32))
        new_h = min(820, max(480, screen.height() - 48))
        self.set_dialog_size(new_w, new_h)

        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # ══ ANA WIDGET ═══════════════════════════════════════════════════════
        main_widget = QWidget()
        main_widget.setObjectName("customerReferenceCanvas")
        main_widget.setStyleSheet(theme_qss("QWidget#customerReferenceCanvas { background: @finance_canvas; border: none; }"))
        root_lay = QVBoxLayout(main_widget)
        root_lay.setContentsMargins(18, 18, 18, 12)
        root_lay.setSpacing(16)

        # ── ÜST BAR: Müşteri Tipi + Checkboxlar ─────────────────────────────
        top_bar = QFrame()
        top_bar.setObjectName("customerTypeBar")
        top_bar.setStyleSheet(theme_qss("QFrame#customerTypeBar { background: @finance_surface; border: none; border-bottom: 1px solid @finance_outline; border-radius: 0px; }"))
        top_bar.setFixedHeight(48)
        top_lay = QHBoxLayout(top_bar); top_lay.setContentsMargins(18, 7, 18, 7); top_lay.setSpacing(10)

        self.rb_individual = QRadioButton("Bireysel")
        self.rb_corporate  = QRadioButton("Kurumsal")
        self.rb_individual.setChecked(True)
        for rb in (self.rb_individual, self.rb_corporate):
            rb.setMinimumHeight(24)
            rb.setMinimumWidth(70)
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            rb.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            rb.setStyleSheet(theme_qss("""
                QRadioButton { color: @text; font-weight: 700; font-size: 10px; padding: 2px 6px;
                               border: 1px solid @border; border-radius: 4px; background: @surface_alt; }
                QRadioButton:checked { background: @finance_primary; color: @finance_primary_text; border-color: @finance_primary; }
                QRadioButton::indicator { width: 0; height: 0; }
            """))

        self.chk_sms = QCheckBox("SMS Izni")
        self.chk_sms.setObjectName("SmsChip")
        self.chk_sms.setChecked(True)
        self.chk_sms.setMinimumHeight(24)
        self.chk_sms.setMinimumWidth(78)
        self.chk_sms.setFixedWidth(78)
        self.chk_sms.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_sms.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.chk_sms.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.chk_sms.setStyleSheet(theme_qss("""
            QCheckBox#SmsChip { color: @finance_secondary; font-weight: 700; font-size: 10px; spacing: 6px; padding: 4px 8px;
                        border: 1px solid @border; border-radius: 4px; background: @surface_alt; text-align: left; }
            QCheckBox#SmsChip:checked { background: @finance_success_bg; border-color: @finance_secondary; }
            QCheckBox#SmsChip::indicator { width: 12px; height: 12px; subcontrol-origin: padding; subcontrol-position: left center; }
        """))

        self.chk_problem = QCheckBox("Sorunlu M\u00fc\u015fteri")
        self.chk_problem.setObjectName("ProblemChip")
        self.chk_problem.setMinimumHeight(24)
        self.chk_problem.setMinimumWidth(104)
        self.chk_problem.setFixedWidth(104)
        self.chk_problem.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_problem.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.chk_problem.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.chk_problem.setStyleSheet(theme_qss("""
            QCheckBox#ProblemChip { color: @danger; font-weight: 700; font-size: 10px; spacing: 6px; padding: 4px 8px;
                        border: 1px solid @border; border-radius: 4px; background: @surface_alt; text-align: left; }
            QCheckBox#ProblemChip:checked { background: @finance_surface_alt; border-color: @danger; }
            QCheckBox#ProblemChip::indicator { width: 12px; height: 12px; subcontrol-origin: padding; subcontrol-position: left center; }
        """))

        customer_type_wrap = QWidget()
        customer_type_wrap.setStyleSheet("background: transparent;")
        customer_type_lay = QHBoxLayout(customer_type_wrap)
        customer_type_lay.setContentsMargins(0, 0, 0, 0)
        customer_type_lay.setSpacing(8)
        type_label = QLabel("M\u00fc\u015fteri Tipi:", styleSheet=theme_qss("color: @text_muted; font-weight: 700; font-size: 8px; border: none; background: transparent;"))
        type_label.setFixedWidth(55)
        customer_type_lay.addWidget(type_label)
        customer_type_lay.addWidget(self.rb_individual)
        customer_type_lay.addWidget(self.rb_corporate)

        status_wrap = QWidget()
        status_wrap.setStyleSheet("background: transparent;")
        status_lay = QHBoxLayout(status_wrap)
        status_lay.setContentsMargins(0, 0, 0, 0)
        status_lay.setSpacing(10)
        status_lay.addStretch()
        status_lay.addWidget(self.chk_sms)
        status_lay.addWidget(self.chk_problem)

        top_lay.addWidget(customer_type_wrap, 0)
        top_lay.addStretch(1)
        top_lay.addWidget(status_wrap, 1)
        self.card_layout.insertWidget(1, top_bar)

        # ── 2 KOLON ──────────────────────────────────────────────────────────
        cols_lay = QHBoxLayout(); cols_lay.setSpacing(16)

        # ── SOL KOLON (54%): Temel, İletişim, Finans ─────────────────────────
        left_col = QVBoxLayout(); left_col.setSpacing(16)

        # Temel Bilgiler
        temel_grid = QGridLayout(); temel_grid.setSpacing(8)
        lay_name, self.inp_name       = self._make_field("Müşteri Adı / Soyadı *", "Ad Soyad", Validators.is_not_empty)
        lay_company, self.inp_company = self._make_field("Firma Adı (Opsiyonel)", "Firma")
        lay_tc, self.inp_tc           = self._make_field("TC Kimlik No", "11 Hane", Validators.is_numeric)
        temel_grid.addLayout(lay_name, 0, 0)
        temel_grid.addLayout(lay_company, 0, 1)
        temel_grid.addLayout(lay_tc, 1, 0, 1, 2)
        left_col.addWidget(self._card("Temel Bilgiler", "👤", temel_grid))

        # İletişim
        ilet_grid = QGridLayout(); ilet_grid.setSpacing(8)
        lay_phone, self.inp_phone   = self._make_field("Telefon 1 *", "05xx...", Validators.is_phone)
        lay_phone2, self.inp_phone2 = self._make_field("Telefon 2", "Yedek No")
        lay_email, self.inp_email   = self._make_field("E-posta", "email@example.com", Validators.is_email)
        ilet_grid.addLayout(lay_phone, 0, 0)
        ilet_grid.addLayout(lay_phone2, 0, 1)
        ilet_grid.addLayout(lay_email, 1, 0, 1, 2)
        left_col.addWidget(self._card("İletişim Bilgileri", "📞", ilet_grid))

        # Finans & Vergi
        fin_grid = QGridLayout(); fin_grid.setSpacing(8)
        lay_tax_no, self.inp_tax_no         = self._make_field("Vergi Numarası", "Vergi No")
        lay_tax_office, self.inp_tax_office = self._make_field("Vergi Dairesi", "Daire")
        lay_zip, self.inp_zip               = self._make_field("Posta Kodu", "34XXX")
        lay_term, self.inp_term             = self._make_field("Vade (Gün)", "Örn: 30")
        lay_limit, self.inp_limit           = self._make_field(f"Borç Limiti ({CurrencyHelper.get_label(db=self.db)})", "Örn: 5000")
        lay_commission, self.inp_commission = self._make_field("Komisyon (%)", "Örn: 5.0")
        lay_service_type, self.cmb_service_type = self._make_combo(
            "Hizmet Türü", ["Genel", "Telefon Servisi", "Bilgisayar Servisi", "Aksesuar / Satış"], editable=True
        )
        fin_grid.addLayout(lay_tax_no, 0, 0)
        fin_grid.addLayout(lay_tax_office, 0, 1)
        fin_grid.addLayout(lay_zip, 1, 0)
        fin_grid.addLayout(lay_term, 1, 1)
        fin_grid.addLayout(lay_limit, 2, 0)
        fin_grid.addLayout(lay_commission, 2, 1)
        fin_grid.addLayout(lay_service_type, 3, 0, 1, 2)
        left_col.addWidget(self._card("Finans & Vergi", "💰", fin_grid))
        left_col.addStretch()

        cols_lay.addLayout(left_col, 1)

        # ── SAĞ KOLON (46%): Adres, Notlar ───────────────────────────────────
        right_col = QVBoxLayout(); right_col.setSpacing(16)

        # Adres
        addr_grid = QGridLayout(); addr_grid.setSpacing(8)
        lay_city, self.cmb_city               = self._make_combo("\u0130l", ["Bal\u0131kesir", "\u0130stanbul", "Ankara", "\u0130zmir"], editable=True)
        lay_dist, self.cmb_district           = self._make_combo("\u0130l\u00e7e", BALIKESIR_ILCELER, editable=True)
        lay_neigh, self.cmb_neighborhood      = self._make_combo("Mahalle", GONEN_MAHALLELER, editable=True)
        lay_street, self.inp_street           = self._make_field("Cadde / Sokak", "Cadde/Sokak")

        street_completer = QCompleter(GONEN_CADDELER)
        street_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.inp_street.setCompleter(street_completer)

        addr_grid.addLayout(lay_city, 0, 0)
        addr_grid.addLayout(lay_dist, 0, 1)
        addr_grid.addLayout(lay_neigh, 1, 0)
        addr_grid.addLayout(lay_street, 1, 1)
        addr_grid.setColumnStretch(0, 11)
        addr_grid.setColumnStretch(1, 9)

        addr_header = QHBoxLayout()
        addr_lbl = QLabel("Açık Adres")
        addr_lbl.setStyleSheet(theme_qss("color: @text_muted; font-weight: 700; font-size: 11px; border: none; background: transparent;"))
        self.btn_location = QPushButton("Lokasyon - Konum")
        self.btn_location.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_location.setStyleSheet(theme_qss(
            "QPushButton { color: @selection_text; background: @accent; border: 0; "
            "border-radius: 5px; padding: 5px 10px; font-size: 10px; font-weight: 700; } "
            "QPushButton:hover { background: @accent_hover; }"
        ))
        self.btn_location.clicked.connect(self.open_location_picker)
        addr_header.addWidget(addr_lbl)
        addr_header.addStretch()
        addr_header.addWidget(self.btn_location)
        self.txt_address = QTextEdit()
        self.txt_address.setPlaceholderText("Bina, daire, diğer adres detayları...")
        self.txt_address.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.txt_address.setFixedHeight(58)
        self.lbl_location_status = QLabel("Konum adres bilgisine gore otomatik bulunur.")
        self.lbl_location_status.setStyleSheet(theme_qss(
            "color: @text_muted; font-size: 9px; border: none; background: transparent;"
        ))
        addr_inner = QVBoxLayout(); addr_inner.setSpacing(8)
        addr_inner.addLayout(addr_grid)
        addr_inner.addLayout(addr_header)
        addr_inner.addWidget(self.txt_address)
        addr_inner.addWidget(self.lbl_location_status)
        right_col.addWidget(self._card("Adres Bilgileri", "📍", addr_inner))

        # Notlar (stretch=1)
        note_inner = QVBoxLayout(); note_inner.setSpacing(0)
        self.txt_note = QTextEdit()
        self.txt_note.setFixedHeight(72)
        self.txt_note.setPlaceholderText("Müşteri hakkında özel notlar, alışkanlıklar, teknik bilgiler...")
        self.txt_note.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        note_inner.addWidget(self.txt_note)
        right_col.addWidget(self._card("\u00d6zel Notlar", "\U0001f4dd", note_inner))

        plugin_card = self._build_plugin_customer_card()
        if plugin_card:
            right_col.addWidget(plugin_card)
        right_col.addStretch(1)
        cols_lay.addLayout(right_col, 1)
        root_lay.addLayout(cols_lay, 1)

        self.scroll_area.setWidget(main_widget)
        self.content_container = main_widget
        self.content_layout = root_lay

        # ── Footer ────────────────────────────────────────────────────────────
        self.footer_layout.setContentsMargins(24, 0, 24, 0)
        self.footer_layout.setSpacing(12)

        btn_cancel = QPushButton("\u0130ptal"); btn_cancel.setFixedSize(100, 36)
        self.btn_cancel = btn_cancel
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(theme_qss("background: @surface_alt; color: @text_muted; border: 1px solid @border; border-radius: 4px; font-weight: bold;"))
        btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("M\u00fc\u015fteriyi Kaydet"); self.btn_save.setFixedHeight(36); self.btn_save.setMinimumWidth(180)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(theme_qss("background-color: @finance_secondary; color: @finance_secondary_text; border-radius: 4px; font-weight: bold; border: none; font-size: 12px;"))
        self.btn_save.clicked.connect(self.save)

        self.footer_layout.addWidget(btn_cancel)
        self.footer_layout.addStretch()
        self.footer_layout.addWidget(self.btn_save)

        # Connect signals
        self.cmb_city.currentTextChanged.connect(self.city_changed)
        self.cmb_district.currentTextChanged.connect(self.district_changed)
        self.chk_sms.stateChanged.connect(self._on_sms_changed)
        self.chk_problem.stateChanged.connect(self._on_problem_changed)
        self.rb_individual.toggled.connect(self._on_customer_type_changed)
        self.rb_corporate.toggled.connect(self._on_customer_type_changed)
        self._on_customer_type_changed()
        self._on_sms_changed(self.chk_sms.checkState())
        self._on_problem_changed(self.chk_problem.checkState())

    def _get_last_login_username(self):
        try:
            return self.db.get_setting("last_login_user", "") or ""
        except Exception:
            return ""

    def _apply_default_location_from_settings(self):
        username = self._get_last_login_username()
        default_city = "Balıkesir"
        default_district = "Gönen"
        default_address = ""
        if username:
            try:
                city = self.db.get_setting(f"map_default_city_user_{username}", "")
                district = self.db.get_setting(f"map_default_district_user_{username}", "")
                address = self.db.get_setting(f"map_default_address_user_{username}", "")
                if city:
                    default_city = city
                if district:
                    default_district = district
                if address:
                    default_address = address
            except Exception as e:
                logger.debug(f"Default location settings fallback used: {e}")
        idx_city = self.cmb_city.findText(default_city)
        if idx_city >= 0:
            self.cmb_city.setCurrentIndex(idx_city)
        idx_dist = self.cmb_district.findText(default_district)
        if idx_dist >= 0:
            self.cmb_district.setCurrentIndex(idx_dist)
        if default_address:
            try:
                self.txt_address.setPlainText(default_address)
            except Exception:
                self.txt_address.setText(default_address)

    # Eski wizard navigasyon — artık kullanılmıyor (tek sayfa)
    def update_navigation(self): pass
    def next_step(self): pass
    def prev_step(self): pass

    def load_customer_data(self):
        if not self.customer_data: return
        c = self.customer_data
        try:
            # self.customer_data is already a sqlite3.Row or similar from the table
            # But let's fetch fresh data to be sure
            customer_id = c['id'] if hasattr(c, '__getitem__') and not isinstance(c, (list, tuple)) else c[0]
            if self.sector_manager and hasattr(self.db, "get_customer_with_extensions"):
                data = self.db.get_customer_with_extensions(customer_id, self._active_sector_id())
            else:
                try:
                    row = self.db.cursor.execute(
                        "SELECT * FROM customers WHERE id=? AND COALESCE(is_deleted, 0)=0",
                        (customer_id,),
                    ).fetchone()
                except Exception:
                    row = self.db.cursor.execute(
                        "SELECT * FROM customers WHERE id=?",
                        (customer_id,),
                    ).fetchone()
                data = dict(row) if row else None
            if not data: return
            
            self.inp_name.setText(data.get('name') or '')
            self.inp_phone.setText(data.get('phone') or '')
            self.inp_email.setText(data.get('email') or '')
            self.inp_tax_no.setText(data.get('tax_id') or data.get('tax_no') or '')
            self.txt_address.setText(data.get('address') or '')
            
            if data.get('type') == 'Kurumsal':
                self.rb_corporate.setChecked(True)
            else:
                self.rb_individual.setChecked(True)
                
            self.inp_company.setText(data.get('company_name') or '') 
            self.inp_tc.setText(data.get('tc_no') or '')
            self.inp_tax_office.setText(data.get('tax_office') or '')
            self.txt_note.setText(data.get('notes') or '')
            self.inp_term.setText(str(data.get('term_days') or '0'))
            self.inp_limit.setText(str(data.get('limit_amount') or '0.00'))
            
            self.chk_sms.setChecked(bool(data.get('sms_enabled')))
            self.chk_problem.setChecked(bool(data.get('is_problematic')))
            
            self.inp_phone2.setText(data.get('phone2') or '')
            self.inp_zip.setText(data.get('zip_code') or '')
            self.inp_street.setText(data.get('street') or '')
            self._set_location_coordinates(data.get('latitude'), data.get('longitude'))

            try:
                self.cmb_service_type.setCurrentText(data.get('service_type') or 'Genel')
            except Exception as e:
                logger.debug(f"Service type set fallback used: {e}")
            try:
                val = data.get('commission_rate')
                self.inp_commission.setText("" if val is None else str(val))
            except Exception:
                self.inp_commission.setText("")
            
            city = data['city'] or 'Balıkesir'
            idx = self.cmb_city.findText(city)
            if idx >= 0: self.cmb_city.setCurrentIndex(idx)
            
            dist = data['district'] or 'Gönen'
            idx2 = self.cmb_district.findText(dist)
            if idx2 >= 0: self.cmb_district.setCurrentIndex(idx2)
            self.cmb_neighborhood.setCurrentText(data['neighborhood'] or '')
            self._set_plugin_customer_values(data)
            if self.location_coordinates is None:
                self._schedule_address_geocode()



        except Exception as e:
            logger.warning(f"AddCustomerDialog load_customer_data error: {e}")


    def _on_customer_type_changed(self):
        is_corporate = self.rb_corporate.isChecked()
        self.inp_company.setEnabled(is_corporate)
        self.inp_tax_no.setEnabled(is_corporate)
        self.inp_tax_office.setEnabled(is_corporate)
        self.inp_tc.setEnabled(not is_corporate)

    def _on_sms_changed(self, state):
        state_value = state.value if hasattr(state, "value") else state
        is_checked = state == Qt.CheckState.Checked or state_value == Qt.CheckState.Checked.value
        self.chk_sms.setToolTip("SMS bildirimi açık" if is_checked else "SMS bildirimi kapalı")

    def _on_problem_changed(self, state):
        state_value = state.value if hasattr(state, "value") else state
        is_checked = state == Qt.CheckState.Checked or state_value == Qt.CheckState.Checked.value
        self.chk_problem.setToolTip("Sorunlu kayıt" if is_checked else "Normal kayıt")




    def validate_form(self):
        name = self.inp_name.text().strip()
        if len(name) < 2:
            show_error(self, "Müşteri/Firma adı en az 2 karakter olmalıdır.")
            return False
            
        phone = self.inp_phone.text().strip()
        if phone:
            digits = "".join(filter(str.isdigit, phone))
            if len(digits) < 10:
                show_error(self, "Geçerli bir telefon numarası giriniz.")
                return False
        
        email = self.inp_email.text().strip()
        if email:
            if "@" not in email:
                show_error(self, "Geçerli bir e-posta adresi giriniz.")
                return False
        else:
             # Opsiyonel: Eğer e-posta boşsa uyarı verilebilir veya zorunlu tutulabilir
             # Kullanıcı e-posta gelmeme sorunundan bahsettiği için burada bir uyarı mantıklı olabilir
             pass

        plugin_values = self._collect_plugin_customer_values()
        for field in self.plugin_customer_fields:
            if field.get("required") and not str(plugin_values.get(field["name"], "") or "").strip():
                show_error(self, f"{field.get('title', field['name'])} alani zorunludur.")
                return False

        return True

    def clear_form(self):
        for widget in self.findChildren(QLineEdit):
            widget.clear()
        for widget in self.findChildren(QTextEdit):
            widget.clear()
        self.cmb_city.setCurrentText("Balıkesir")
        self.cmb_district.setCurrentText("Gönen")
        self.chk_sms.setChecked(True)
        self.chk_problem.setChecked(False)

    def save(self):
        if not self.validate_form():
            return

        commission_text = (self.inp_commission.text() or "").strip().replace(",", ".")
        try:
            commission_val = float(commission_text) if commission_text else 0.0
        except Exception:
            commission_val = 0.0

        data = {
            "name": self.inp_name.text().strip(),
            "phone": self.inp_phone.text(),
            "email": self.inp_email.text(),
            "type": "Kurumsal" if self.rb_corporate.isChecked() else "Bireysel",
            "tax_id": self.inp_tax_no.text(),
            "address": self.txt_address.toPlainText(),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tax_office": self.inp_tax_office.text(),
            "district": self.cmb_district.currentText(),
            "city": self.cmb_city.currentText(),
            "neighborhood": self.cmb_neighborhood.currentText(),
            "notes": self.txt_note.toPlainText(),
            "term_days": int(self.inp_term.text()) if self.inp_term.text().isdigit() else 0,
            "limit_amount": float(self.inp_limit.text()) if self.inp_limit.text().replace('.', '', 1).isdigit() else 0.0,
            "sms_enabled": 1 if self.chk_sms.isChecked() else 0,
            "is_problematic": 1 if self.chk_problem.isChecked() else 0,
            "phone2": self.inp_phone2.text(),
            "zip_code": self.inp_zip.text(),
            "tc_no": self.inp_tc.text(),
            "company_name": self.inp_company.text(),
            "street": self.inp_street.text(),
            "service_type": self.cmb_service_type.currentText().strip(),
            "commission_rate": commission_val,
            "latitude": self.location_coordinates[0] if self.location_coordinates else 0,
            "longitude": self.location_coordinates[1] if self.location_coordinates else 0,
        }
        extension_data = {}
        if self.sector_manager:
            extension_data = self.sector_manager.map_core_to_extension_payload(
                "customer",
                self._collect_plugin_customer_values(),
            )

        try:
            if self.customer_data:
                self.db.cursor.execute("PRAGMA table_info(customers)")
                valid_columns = {row[1] for row in (self.db.cursor.fetchall() or [])}
                safe_items = [(k, v) for k, v in data.items() if k in valid_columns]
                set_clause = ", ".join([f"{k}=?" for k, _ in safe_items])
                values = [v for _, v in safe_items]
                customer_id = self.customer_data['id'] if hasattr(self.customer_data, '__getitem__') and not isinstance(self.customer_data, (list, tuple)) else self.customer_data[0]
                values.append(customer_id)
                self.db.cursor.execute(
                    "UPDATE customers SET {set_clause} WHERE id=?".format(set_clause=set_clause),
                    values,
                )
                self.db.conn.commit()
                if extension_data and hasattr(self.db, "upsert_sector_extension"):
                    self.db.upsert_sector_extension("customer", customer_id, extension_data, self._active_sector_id())
                self._save_customer_360_note(customer_id, data.get("notes"))
                self.saved_customer_id = customer_id
                self.saved_customer_name = data["name"]
                self.accept()
                show_info(self, "Müşteri başarıyla güncellendi.")
            else:
                try:
                    self.db.cursor.execute("PRAGMA table_info(customers)")
                    customer_columns = {
                        row[1] for row in (self.db.cursor.fetchall() or [])
                    }
                    for location_column in ("latitude", "longitude"):
                        if location_column not in customer_columns:
                            data.pop(location_column, None)
                except Exception:
                    pass
                new_customer_id = self.db.add_customer(data)
                if new_customer_id:
                    if extension_data and hasattr(self.db, "upsert_sector_extension"):
                        self.db.upsert_sector_extension("customer", new_customer_id, extension_data, self._active_sector_id())
                    self._save_customer_360_note(new_customer_id, data.get("notes"))
                    try:
                        row = self.db.cursor.execute("SELECT id, name FROM customers WHERE id=?", (new_customer_id,)).fetchone()
                        if row:
                            self.saved_customer_id = row[0]
                            self.saved_customer_name = row[1]
                    except Exception as e:
                        logger.debug(f"Saved customer lookup fallback used: {e}")
                        self.saved_customer_name = data["name"]
                    show_success(self, "Yeni müşteri başarıyla eklendi.")
                    
                    # Welcome Email logic
                    email = data.get('email', '').strip()
                    if email and "@" in email:
                        try:
                            subject = "AYEC Pro'ya Hoş Geldiniz!"
                            body = f"""
                            <html>
                            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: black;">
                                <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid lightgray; border-radius: 10px;">
                                    <h2 style="color: black;">AYEC Pro</h2>
                                    <p>Merhaba <b>{data['name']}</b>,</p>
                                    <p>Sistemimize kaydınız başarıyla tamamlanmıştır. Teknik servis süreçlerinizle ilgili bilgilendirmeler bu adres üzerinden yapılacaktır.</p>
                                    <hr style="border: 0; border-top: 1px solid lightgray;">
                                    <p style="font-size: 13px; color: dimgray; font-weight: bold; text-align: center;">
                                        © 2026 AYEC Pro - Tüm hakları saklıdır.
                                    </p>
                                </div>
                            </body>
                            </html>
                            """
                            
                            # Check if attachment exists before adding
                            attachment_path = os.path.join(os.getcwd(), "assets", "documents", "kurumsal_tanitim.pdf")
                            if not os.path.exists(attachment_path):
                                attachment_path = None  # Don't attach if file doesn't exist
                            
                            self.welcome_mail = MailWorker(
                                email, 
                                subject, 
                                body, 
                                is_html=True, 
                                attachment_path=attachment_path,
                                db=self.db
                            )
                            self.welcome_mail.finished.connect(self.on_mail_finished)
                            self.welcome_mail.start()
                        except Exception as e:
                            logger.error(f"Customer welcome email error: {e}")
                    self.accept()
                else:
                    show_error(self, "Müşteri eklenirken bir hata oluştu.")
        except Exception as e:
            show_error(self, f"Veritabanı hatası: {e}")

    def _save_customer_360_note(self, customer_id, content):
        """Mirror the registration note into the Customer 360 notes stream."""
        text = str(content or "").strip()
        if not text or not customer_id or not hasattr(self.db, "add_customer_note"):
            return
        try:
            existing = self.db.get_customer_notes(customer_id) if hasattr(self.db, "get_customer_notes") else ()
            if any(str(row[1]).casefold() == "note" and str(row[2] or "").strip() == text for row in (existing or ())):
                return
            self.db.add_customer_note(customer_id, "Note", text)
        except Exception:
            logger.exception("Customer 360 note could not be saved for customer %s", customer_id)

    def _address_query(self):
        parts = [
            self.cmb_neighborhood.currentText().strip(),
            self.inp_street.text().strip(),
            self.txt_address.toPlainText().strip(),
            self.cmb_district.currentText().strip(),
            self.cmb_city.currentText().strip(),
            "Turkiye",
        ]
        result = []
        seen = set()
        for part in parts:
            normalized = part.casefold()
            if part and normalized not in seen:
                result.append(part)
                seen.add(normalized)
        return ", ".join(result)

    def _schedule_address_geocode(self, *args):
        if self._syncing_location_fields:
            return
        if not self.tomtom_api_key:
            self.lbl_location_status.setText("TomTom API anahtar\u0131 bulunamad\u0131.")
            return
        if self._address_query().strip(" ,"):
            self.lbl_location_status.setText("Adres konumu aran\u0131yor...")
            self._address_geocode_timer.start()

    def _geocode_current_address(self):
        query = self._address_query()
        if len(query) < 8:
            return
        self._geocode_serial += 1
        request_id = "address:{}".format(self._geocode_serial)
        self.geocoder.geocode(query, request_id)

    def _set_location_coordinates(self, latitude, longitude):
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (TypeError, ValueError):
            return False
        if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
            return False
        self.location_coordinates = (lat, lon)
        self.btn_location.setText("Konum Belirlendi")
        self.btn_location.setToolTip("{:.6f}, {:.6f}".format(lat, lon))
        self.lbl_location_status.setText(
            "Kay\u0131tl\u0131 konum: {:.6f}, {:.6f}".format(lat, lon)
        )
        return True

    def _on_geocode_resolved(self, request_id, result, error):
        request_id = str(request_id or "")
        if request_id.startswith("address:"):
            try:
                serial = int(request_id.split(":", 1)[1])
            except (IndexError, ValueError):
                return
            if serial != self._geocode_serial:
                return
            if not result:
                self.lbl_location_status.setText(
                    "Adres konumu bulunamad\u0131: {}".format(error or "Sonu\u00e7 yok")
                )
                return
            position = result.get("position") or {}
            if self._set_location_coordinates(position.get("lat"), position.get("lon")):
                self.lbl_location_status.setText(
                    "Adres konumu bulundu: {:.6f}, {:.6f}".format(*self.location_coordinates)
                )
            return
        if request_id.startswith("reverse:"):
            if result:
                self._apply_reverse_geocode(result)
            elif error:
                self.lbl_location_status.setText(
                    "Konum kaydedildi; adres bilgisi getirilemedi."
                )

    def _apply_reverse_geocode(self, result):
        address = result.get("address") or {}
        lat, lon = self.location_coordinates or (None, None)
        self._syncing_location_fields = True
        blockers = [
            QSignalBlocker(self.cmb_city),
            QSignalBlocker(self.cmb_district),
            QSignalBlocker(self.cmb_neighborhood),
            QSignalBlocker(self.inp_street),
            QSignalBlocker(self.inp_zip),
            QSignalBlocker(self.txt_address),
        ]
        try:
            city = address.get("countrySubdivisionName") or address.get("countrySubdivision") or ""
            district = address.get("municipality") or ""
            neighborhood = address.get("neighbourhood") or address.get("municipalitySubdivision") or ""
            street = address.get("street") or ""
            street_number = address.get("streetNumber") or ""
            postal_code = address.get("postalCode") or ""
            full_address = address.get("freeformAddress") or ""
            if city:
                self.cmb_city.setCurrentText(str(city))
            if district:
                self.cmb_district.setCurrentText(str(district))
            if neighborhood:
                self.cmb_neighborhood.setCurrentText(str(neighborhood))
            self.inp_street.setText("{} {}".format(street, street_number).strip())
            if postal_code:
                self.inp_zip.setText(str(postal_code))
            if full_address:
                self.txt_address.setPlainText(str(full_address))
        finally:
            del blockers
            self._syncing_location_fields = False
        if lat is not None:
            self._set_location_coordinates(lat, lon)
        self.lbl_location_status.setText(
            "Konumdan adres bilgileri dolduruldu: {:.6f}, {:.6f}".format(lat, lon)
        )

    def open_location_picker(self):
        if not self.tomtom_api_key:
            show_warning(
                self,
                "TomTom haritas\u0131 i\u00e7in API anahtar\u0131 bulunamad\u0131. Saha Haritas\u0131 ayarlar\u0131ndan anahtar\u0131 kaydedin.",
            )
            return
        from src.ui.dialogs.customer_location_dialog import CustomerLocationDialog

        latitude, longitude = self.location_coordinates or (40.1044116, 27.6563981)
        dialog = CustomerLocationDialog(
            self.tomtom_api_key,
            latitude,
            longitude,
            self._address_query(),
            self,
        )
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._address_geocode_timer.stop()
                self._geocode_serial += 1
                self.location_coordinates = dialog.selected_coordinates
                self._set_location_coordinates(*self.location_coordinates)
                request_id = "reverse:{}".format(self._geocode_serial)
                self.geocoder.reverse_geocode(*self.location_coordinates, request_id)
        except Exception as error:
            logger.exception("Customer location picker failed: %s", error)
            show_error(self, "Konum se\u00e7me haritas\u0131 a\u00e7\u0131lamad\u0131: {}".format(error))
        finally:
            dialog.deleteLater()

    def on_mail_finished(self, success, message):
        if success:
            show_success(self, "Bilgilendirme maili gönderildi. ✅")
        else:
            show_error(self, f"Mail hatası: {message}")
    
    def city_changed(self, city):
        self.cmb_district.clear()
        if city == "Balıkesir":
            self.cmb_district.addItems(BALIKESIR_ILCELER)
            self.cmb_district.setCurrentText("Gönen")
        else:
            self.cmb_district.addItems(["Merkez", "Diğer"])
    
    def district_changed(self, district):
        self.cmb_neighborhood.clear()
        if district == "Gönen":
            mahalleler = get_mahalleler("Gönen")
            self.cmb_neighborhood.addItems(mahalleler)
            completer = QCompleter(mahalleler)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.cmb_neighborhood.setCompleter(completer)
        else:
            self.cmb_neighborhood.setPlaceholderText("Mahalle giriniz")

