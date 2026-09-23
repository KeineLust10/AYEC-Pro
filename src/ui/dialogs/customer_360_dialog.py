# -*- coding: utf-8 -*-

from datetime import datetime
import os
import re

from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QTextListFormat
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QComboBox,
    QColorDialog,
    QFontComboBox,
    QFileDialog,
    QTextEdit,
)

from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.ui.dialogs.customer_vehicle_dialog import CustomerVehicleDialog
from src.ui.dialogs.payment_dialog import ModernPaymentDialog
from src.ui.dialogs.modern_input_dialog import ModernInputDialog
from src.utils.theme_colors import tc, theme_qss
from src.utils.currency_helper import CurrencyHelper
from src.utils.logger import logger
from src.utils.date_formatter import format_date
from src.utils.system_config import SystemConfig
from src.utils.path_helper import PathHelper
from src.utils.offer_pdf_data import load_offer_pdf_data
from src.utils.service_work_details import clean_offer_line_description
from src.utils.toast_notification import show_error, show_success, show_warning


class StatBox(QFrame):
    def __init__(self, title, value, icon_char, color, parent=None):
        super().__init__(parent)
        self.setFixedSize(250, 85)
        self.setStyleSheet(
            theme_qss(
                """
                QFrame {
                    background-color: @surface;
                    border: 1px solid @border;
                    border-radius: 12px;
                }
                """
            )
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(12)

        icon_frame = QFrame()
        icon_frame.setFixedSize(45, 45)
        icon_frame.setStyleSheet(f"background-color: {color}; border-radius: 8px;")
        if_layout = QVBoxLayout(icon_frame)
        if_layout.setContentsMargins(0, 0, 0, 0)

        lbl_icon = QLabel(icon_char)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet(
            theme_qss(
                "color: @selection_text; font-size: 20px; background: transparent;"
            )
        )
        if_layout.addWidget(lbl_icon)

        txt_layout = QVBoxLayout()
        txt_layout.setSpacing(2)

        lbl_title = QLabel(title.upper())
        lbl_title.setStyleSheet(
            theme_qss(
                "color: @text_muted; font-size: 10px; font-weight: bold; background: transparent;"
            )
        )

        lbl_val = QLabel(str(value))
        lbl_val.setToolTip(str(value))
        lbl_val.setStyleSheet(
            theme_qss(
                "color: @text; font-size: 16px; font-weight: 800; background: transparent;"
            )
        )

        txt_layout.addWidget(lbl_title)
        txt_layout.addWidget(lbl_val)

        layout.addWidget(icon_frame)
        layout.addLayout(txt_layout)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)


class CustomerNoteDialog(BaseModernDialog):
    def __init__(self, db, customer_id, customer_name, parent=None):
        super().__init__(parent, title=f"M\u00fc\u015fteri Notu - {customer_name}", width=850, height=650)
        self.db = db
        self.customer_id = customer_id
        self.note_id = None
        self.setup_editor_ui()
        self.load_note()

    def setup_editor_ui(self):
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        toolbar.setContentsMargins(0, 0, 0, 6)

        self.btn_bold = QPushButton("B")
        self.btn_bold.setCheckable(True)
        self.btn_bold.setFixedSize(30, 30)
        self.btn_bold.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_bold.clicked.connect(self.set_bold)
        toolbar.addWidget(self.btn_bold)

        self.btn_italic = QPushButton("I")
        self.btn_italic.setCheckable(True)
        self.btn_italic.setFixedSize(30, 30)
        font_i = QFont("Segoe UI", 10)
        font_i.setItalic(True)
        self.btn_italic.setFont(font_i)
        self.btn_italic.clicked.connect(self.set_italic)
        toolbar.addWidget(self.btn_italic)

        self.btn_underline = QPushButton("U")
        self.btn_underline.setCheckable(True)
        self.btn_underline.setFixedSize(30, 30)
        font_u = QFont("Segoe UI", 10)
        font_u.setUnderline(True)
        self.btn_underline.setFont(font_u)
        self.btn_underline.clicked.connect(self.set_underline)
        toolbar.addWidget(self.btn_underline)

        self.combo_font = QFontComboBox()
        self.combo_font.setFixedWidth(140)
        self.combo_font.currentFontChanged.connect(self.set_font_family)
        toolbar.addWidget(self.combo_font)

        self.combo_size = QComboBox()
        self.combo_size.setFixedWidth(60)
        for s in [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 28, 36, 48, 72]:
            self.combo_size.addItem(str(s))
        self.combo_size.setCurrentText("12")
        self.combo_size.currentTextChanged.connect(self.set_font_size)
        toolbar.addWidget(self.combo_size)

        self.btn_color = QPushButton("Renk")
        self.btn_color.setFixedSize(60, 30)
        self.btn_color.clicked.connect(self.set_text_color)
        toolbar.addWidget(self.btn_color)

        self.btn_list = QPushButton("\u2022 Liste")
        self.btn_list.setFixedSize(60, 30)
        self.btn_list.clicked.connect(self.insert_list)
        toolbar.addWidget(self.btn_list)

        self.btn_align_left = QPushButton("Sola")
        self.btn_align_left.setFixedSize(50, 30)
        self.btn_align_left.clicked.connect(lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignLeft))
        toolbar.addWidget(self.btn_align_left)

        self.btn_align_center = QPushButton("Orta")
        self.btn_align_center.setFixedSize(60, 30)
        self.btn_align_center.clicked.connect(lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter))
        toolbar.addWidget(self.btn_align_center)

        self.btn_align_right = QPushButton("Sa\u011fa")
        self.btn_align_right.setFixedSize(50, 30)
        self.btn_align_right.clicked.connect(lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignRight))
        toolbar.addWidget(self.btn_align_right)

        toolbar.addStretch()
        self.content_layout.addLayout(toolbar)

        self.editor = QTextEdit()
        self.editor.setFont(QFont("Segoe UI", 12))
        self.editor.setStyleSheet(theme_qss("""
            QTextEdit {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 10px;
            }
        """))
        self.content_layout.addWidget(self.editor, 1)

        for btn in [self.btn_bold, self.btn_italic, self.btn_underline, self.btn_color, self.btn_list, self.btn_align_left, self.btn_align_center, self.btn_align_right]:
            btn.setStyleSheet(theme_qss("""
                QPushButton {
                    background-color: @surface_alt;
                    color: @text;
                    border: 1px solid @border;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: @hover_bg;
                }
                QPushButton:checked {
                    background-color: @accent;
                    color: @selection_text;
                }
            """))

        self.combo_font.setStyleSheet(theme_qss("""
            QFontComboBox {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 4px;
            }
        """))
        self.combo_size.setStyleSheet(theme_qss("""
            QComboBox {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 4px;
            }
        """))

        self.add_cancel_button("\u0130ptal")
        self.btn_save = self.add_button("Kaydet", "primary", self.save_note)

    def set_bold(self):
        weight = QFont.Weight.Bold if self.btn_bold.isChecked() else QFont.Weight.Normal
        self.editor.setFontWeight(weight)

    def set_italic(self):
        self.editor.setFontItalic(self.btn_italic.isChecked())

    def set_underline(self):
        self.editor.setFontUnderline(self.btn_underline.isChecked())

    def set_font_family(self, font):
        self.editor.setCurrentFont(font)

    def set_font_size(self, size_str):
        try:
            self.editor.setFontPointSize(max(1.0, float(size_str)))
        except:
            pass

    def set_text_color(self):
        color = QColorDialog.getColor(self.editor.textColor(), self, "Renk Se\u00e7")
        if color.isValid():
            self.editor.setTextColor(color)

    def insert_list(self):
        cursor = self.editor.textCursor()
        cursor.insertList(QTextListFormat.Style.ListDisc)

    def load_note(self):
        try:
            notes = self.db.get_customer_notes(self.customer_id)
            for nid, ntype, content, created_at in notes:
                if ntype == 'Note':
                    self.note_id = nid
                    self.editor.setHtml(content)
                    break
        except Exception as e:
            logger.error(f"Load note error: {e}")

    def save_note(self):
        content = self.editor.toHtml()
        try:
            if self.note_id:
                self.db.cursor.execute(
                    "UPDATE customer_notes SET content=?, created_at=datetime('now','localtime') WHERE id=?",
                    (content, self.note_id)
                )
                self.db.conn.commit()
            else:
                self.db.add_customer_note(self.customer_id, 'Note', content)
            show_success(self, "Not ba\u015far\u0131yla kaydedildi.")
            self.accept()
        except Exception as e:
            logger.error(f"Save note error: {e}")
            show_error(self, f"Not kaydedilemedi: {e}")


class Customer360Dialog(BaseModernDialog):
    def __init__(
        self, db, customer_id, customer_name, parent=None, sector_manager=None
    ):
        self.db = db
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.sector_manager = sector_manager
        try:
            if self.sector_manager and self.sector_manager.get_current_plugin():
                self.is_automotive = (
                    self.sector_manager.get_current_plugin().sector_id == "otomotiv"
                )
            else:
                self.is_automotive = (
                    SystemConfig.get_current_sector(self.db) == "otomotiv"
                )
        except Exception:
            self.is_automotive = False

        self._history_page_size = 50
        self._history_pages = {
            "service": 0,
            "cari": 0,
            "ledger": 0,
            "sales": 0,
        }
        self._history_totals = {
            "service": 0,
            "cari": 0,
            "ledger": 0,
            "sales": 0,
        }

        super().__init__(
            parent, title=f"Müşteri 360° - {customer_name}", width=1500, height=920
        )

        self.set_wheel_scroll_enabled(True)
        self.setup_modern_content()
        self.load_stats()
        self.load_cari_table()
        self.load_service_table()
        self.load_currency_ledger()
        self.load_sales_table()
        self.load_offer_table()
        if self.is_automotive:
            self.load_vehicle_table()
        signal_owner = self._financial_signal_owner()
        if signal_owner:
            try:
                signal_owner.financial_data_changed.connect(self.refresh_financial_views)
            except Exception:
                pass

    def _financial_signal_owner(self):
        for owner in (getattr(self, "main_window", None), self.parent(), self.window()):
            if owner and hasattr(owner, "financial_data_changed"):
                return owner
            nested = getattr(owner, "main_window", None) if owner else None
            if nested and hasattr(nested, "financial_data_changed"):
                return nested
        return None

    def _emit_financial_data_changed(self):
        owner = self._financial_signal_owner()
        if owner:
            try:
                owner.financial_data_changed.emit()
            except Exception:
                pass

    def _announce_payment_received(self, customer_name=None, currency=None):
        show_success(self, "\u00d6deme al\u0131nd\u0131.")
        try:
            from src.utils.asistan_motoru import sesli_cevap_ver_async
            balance = self.db.get_customer_currency_balance(self.customer_id, currency or "TRY")
            name = customer_name or self.customer_name
            manager = getattr(self.main_window, "assistant_manager", None)
            def spoken(value):
                if manager and hasattr(manager, "_amount_in_words"):
                    return manager._amount_in_words(value, currency or "TRY")
                return f"{value:.2f} {currency or 'TRY'}"
            if balance < -0.009:
                text = f"\u00d6deme al\u0131nd\u0131. {name} i\u00e7in kalan bor\u00e7 {spoken(abs(balance))}."
            elif balance > 0.009:
                text = f"\u00d6deme al\u0131nd\u0131. {name} alacakl\u0131 duruma ge\u00e7ti. Bakiye {spoken(balance)}."
            else:
                text = f"\u00d6deme al\u0131nd\u0131. {name} borcu bitmi\u015ftir."
            sesli_cevap_ver_async(text)
        except Exception:
            pass

    def refresh_financial_views(self):
        self.load_stats()
        self.load_service_table()
        self.load_cari_table()
        self.load_currency_ledger()
        self.load_sales_table()

    def open_customer_note_dialog(self):
        dlg = CustomerNoteDialog(self.db, self.customer_id, self.customer_name, parent=self)
        dlg.exec()

    def setup_modern_content(self):
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 10)

        avatar = QLabel(self.customer_name[0].upper() if self.customer_name else "")
        avatar.setFixedSize(64, 64)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            theme_qss(
                """
                background-color: @accent;
                color: @selection_text;
                border-radius: 32px;
                font-size: 28px;
                font-weight: bold;
                """
            )
        )
        header.addWidget(avatar)

        info_layout = QVBoxLayout()
        name_lbl = QLabel(self.customer_name)
        name_lbl.setStyleSheet(
            theme_qss("font-size: 22px; font-weight: bold; color: @text;")
        )

        phone = "Bilinmiyor"
        try:
            cur = self.db.cursor
            device_filter, device_params = self._customer_device_filter()
            cur.execute(
                f"""
                SELECT phone_number
                FROM devices
                WHERE {device_filter}
                ORDER BY entry_date DESC
                LIMIT 1
                """,
                device_params,
            )
            row = cur.fetchone()
            if row and row[0]:
                phone = row[0]
        except Exception as e:
            logger.debug(f"Customer360 phone lookup fallback used: {e}")

        sub_lbl = QLabel(f"Telefon: {phone}")
        sub_lbl.setStyleSheet(theme_qss("font-size: 14px; color: @text_muted;"))

        info_layout.addWidget(name_lbl)
        info_layout.addWidget(sub_lbl)
        header.addLayout(info_layout)
        header.addStretch()

        self.btn_customer_note = QPushButton("\U0001f4dd M\u00fc\u015fteri Notlar\u0131")
        self.btn_customer_note.setFixedSize(160, 36)
        self.btn_customer_note.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_customer_note.setStyleSheet(
            theme_qss(
                "background-color: @accent; color: @selection_text; border-radius: 6px; font-weight: bold;"
            )
        )
        self.btn_customer_note.clicked.connect(self.open_customer_note_dialog)
        header.addWidget(self.btn_customer_note)

        self.content_layout.addLayout(header)

        self.stats_layout = QHBoxLayout()
        self.stats_layout.setSpacing(20)
        self.content_layout.addLayout(self.stats_layout)

        self.currency_layout = QHBoxLayout()
        self.currency_layout.setSpacing(20)
        self.currency_layout.setContentsMargins(0, 10, 0, 10)
        self.content_layout.addLayout(self.currency_layout)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            theme_qss(
                """
                QTabWidget::pane {
                    border: 1px solid @border;
                    background: @surface;
                    border-radius: 12px;
                    top: -1px;
                }
                QTabBar::tab {
                    background: @surface_alt;
                    color: @text_muted;
                    padding: 10px 20px;
                    margin-right: 5px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    font-weight: 600;
                }
                QTabBar::tab:selected {
                    background: @surface;
                    color: @text;
                    border: 1px solid @border;
                    border-bottom: none;
                }
                """
            )
        )

        self.tab_service = QWidget()
        self.setup_service_tab()
        self.tabs.addTab(self.tab_service, "Servis Geçmişi")

        self.tab_cari = QWidget()
        self.setup_cari_tab()
        self.tabs.addTab(self.tab_cari, "Cari İşlem Geçmişi")

        self.tab_ledger = QWidget()
        self.setup_ledger_tab()
        self.tabs.addTab(self.tab_ledger, "Döviz Defteri")

        self.tab_sales = QWidget()
        self.setup_sales_tab()
        self.tabs.addTab(self.tab_sales, "Ürün Satışları")

        self.tab_offers = QWidget()
        self.setup_offer_tab()
        self.tabs.addTab(self.tab_offers, "Verilen Teklifler")

        if self.is_automotive:
            self.tab_vehicles = QWidget()
            self.setup_vehicle_tab()
            self.tabs.addTab(self.tab_vehicles, "Araclar")

        self.content_layout.addWidget(self.tabs)

        footer = QHBoxLayout()
        self.btn_offer = QPushButton("Teklif Olu\u015ftur")
        self.btn_xlsx = QPushButton("Excel'e Aktar")
        self.btn_pdf = QPushButton("PDF'e Aktar")
        for b in (self.btn_offer, self.btn_xlsx, self.btn_pdf):
            b.setFixedSize(140, 36)
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_offer.setStyleSheet(
            theme_qss(
                "background-color: @accent; color: @selection_text; border-radius: 6px; font-weight: bold;"
            )
        )
        self.btn_offer.clicked.connect(self.create_offer_from_selected_history)
        self.btn_xlsx.setStyleSheet(
            theme_qss(
                "background-color: @success; color: @selection_text; border-radius: 6px; font-weight: bold;"
            )
        )
        self.btn_xlsx.clicked.connect(self.export_excel)
        self.btn_pdf.setStyleSheet(
            theme_qss(
                "background-color: @danger; color: @selection_text; border-radius: 6px; font-weight: bold;"
            )
        )
        self.btn_pdf.clicked.connect(self.export_pdf)

        footer.addStretch()
        footer.addWidget(self.btn_offer)
        footer.addWidget(self.btn_xlsx)
        footer.addWidget(self.btn_pdf)

        btn_close = QPushButton("Kapat")
        btn_close.setFixedSize(120, 36)
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet(
            theme_qss(
                "background-color: @surface_alt; border: 1px solid @border; border-radius: 6px; color: @text;"
            )
        )
        footer.addWidget(btn_close)

        self.content_layout.addLayout(footer)

    def _table_qss(self):
        return theme_qss(
            """
            QTreeWidget {
                border: 1px solid @border;
                border-radius: 10px;
                background: @surface;
                color: @text;
            }
            QHeaderView::section {
                background: @surface_alt;
                color: @text;
                border: none;
                border-bottom: 1px solid @border;
                padding: 8px;
                font-weight: 700;
            }
            """
        )

    def _add_history_pager(self, layout, key):
        pager = QHBoxLayout()
        pager.addStretch()
        previous_button = QPushButton("< \u00d6nceki")
        next_button = QPushButton("Sonraki >")
        page_label = QLabel("Sayfa 1 / 1")
        previous_button.clicked.connect(
            lambda _checked=False, page_key=key: self._change_history_page(
                page_key, -1
            )
        )
        next_button.clicked.connect(
            lambda _checked=False, page_key=key: self._change_history_page(
                page_key, 1
            )
        )
        setattr(self, f"_{key}_previous_button", previous_button)
        setattr(self, f"_{key}_next_button", next_button)
        setattr(self, f"_{key}_page_label", page_label)
        pager.addWidget(previous_button)
        pager.addWidget(page_label)
        pager.addWidget(next_button)
        layout.addLayout(pager)
        self._update_history_pager(key, 0)

    def _update_history_pager(self, key, total):
        total = max(0, int(total or 0))
        self._history_totals[key] = total
        page_count = max(
            1,
            (total + self._history_page_size - 1) // self._history_page_size,
        )
        current_page = min(self._history_pages.get(key, 0), page_count - 1)
        self._history_pages[key] = current_page
        previous_button = getattr(self, f"_{key}_previous_button", None)
        next_button = getattr(self, f"_{key}_next_button", None)
        page_label = getattr(self, f"_{key}_page_label", None)
        if previous_button:
            previous_button.setEnabled(current_page > 0)
        if next_button:
            next_button.setEnabled(current_page + 1 < page_count)
        if page_label:
            page_label.setText(f"Sayfa {current_page + 1} / {page_count}")

    def _change_history_page(self, key, delta):
        total = self._history_totals.get(key, 0)
        page_count = max(
            1,
            (total + self._history_page_size - 1) // self._history_page_size,
        )
        target = max(
            0,
            min(self._history_pages.get(key, 0) + int(delta), page_count - 1),
        )
        if target == self._history_pages.get(key, 0):
            return
        self._history_pages[key] = target
        loaders = {
            "service": self.load_service_table,
            "cari": self.load_cari_table,
            "ledger": self.load_currency_ledger,
            "sales": self.load_sales_table,
        }
        loader = loaders.get(key)
        if loader:
            loader()

    def setup_service_tab(self):
        l = QVBoxLayout(self.tab_service)
        self.table_service = QTreeWidget()
        self.table_service.setColumnCount(5)
        self.table_service.setHeaderLabels(
            ["Tarih", "Cihaz / Detay", "Durum", "Tutar", "Ödeme"]
        )
        self.table_service.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table_service.header().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_service.setStyleSheet(self._table_qss())
        l.addWidget(self.table_service)
        self._add_history_pager(l, "service")

    def setup_cari_tab(self):
        l = QVBoxLayout(self.tab_cari)
        self.table_cari = QTreeWidget()
        self.table_cari.setColumnCount(7)
        self.table_cari.setHeaderLabels(
            [
                "Tarih / Zaman",
                "İşlem / Ürün Detayı",
                "Döviz",
                "Kur",
                "Tutar",
                "Durum",
                "Ödeme",
            ]
        )
        self.table_cari.setIndentation(12)
        self.table_cari.setRootIsDecorated(False)
        self.table_cari.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_cari.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_cari.header().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_cari.header().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_cari.header().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_cari.header().setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_cari.header().setSectionResizeMode(
            6, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_cari.setStyleSheet(self._table_qss())
        l.addWidget(self.table_cari)
        self._add_history_pager(l, "cari")

    def setup_ledger_tab(self):
        l = QVBoxLayout(self.tab_ledger)
        self.table_ledger = QTreeWidget()
        self.table_ledger.setColumnCount(5)
        self.table_ledger.setHeaderLabels(
            ["Tarih", "Döviz", "İşlem Tipi", "Miktar", "Kalan Bakiye"]
        )
        self.table_ledger.setStyleSheet(self._table_qss())
        l.addWidget(self.table_ledger)
        self._add_history_pager(l, "ledger")

    def setup_sales_tab(self):
        l = QVBoxLayout(self.tab_sales)
        self.table_sales = QTreeWidget()
        self.table_sales.setColumnCount(5)
        self.table_sales.setHeaderLabels(
            ["Tarih", "Satış / Detay", "Ödeme", "Tutar", "Kaynak"]
        )
        self.table_sales.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table_sales.header().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_sales.header().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_sales.header().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_sales.setStyleSheet(self._table_qss())
        l.addWidget(self.table_sales)
        self._add_history_pager(l, "sales")

    def setup_offer_tab(self):
        l = QVBoxLayout(self.tab_offers)
        self.table_offers = QTreeWidget()
        self.table_offers.setColumnCount(7)
        self.table_offers.setHeaderLabels(
            [
                "Tarih",
                "Teklif No",
                "Firma / Proje",
                "Yetkili",
                "Toplam",
                "Durum",
                "PDF",
            ]
        )
        self.table_offers.header().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        for idx in (0, 1, 3, 4, 5, 6):
            self.table_offers.header().setSectionResizeMode(
                idx, QHeaderView.ResizeMode.ResizeToContents
            )
        self.table_offers.setStyleSheet(self._table_qss())
        self.table_offers.itemDoubleClicked.connect(self.open_selected_offer_pdf)
        l.addWidget(self.table_offers)

        actions = QHBoxLayout()
        actions.addStretch()
        self.btn_open_offer = QPushButton("Teklifi A\u00e7")
        self.btn_edit_offer = QPushButton("Teklifi D\u00fczenle")
        self.btn_reverse_offer = QPushButton("\u0130\u015flemi Geri Al ve Revize Et")
        self.btn_process_offer = QPushButton(
            "Teklifi M\u00fc\u015fteri Hesab\u0131na \u0130\u015fle"
        )
        for button in (
            self.btn_open_offer,
            self.btn_edit_offer,
            self.btn_reverse_offer,
            self.btn_process_offer,
        ):
            button.setMinimumHeight(36)
        self.btn_open_offer.clicked.connect(self.open_selected_offer_from_button)
        self.btn_edit_offer.clicked.connect(self.edit_selected_offer)
        self.btn_reverse_offer.clicked.connect(self.reverse_selected_offer)
        self.btn_process_offer.clicked.connect(self.process_selected_offer)
        actions.addWidget(self.btn_open_offer)
        actions.addWidget(self.btn_edit_offer)
        actions.addWidget(self.btn_reverse_offer)
        actions.addWidget(self.btn_process_offer)
        l.addLayout(actions)

    def setup_vehicle_tab(self):
        l = QVBoxLayout(self.tab_vehicles)
        tools = QHBoxLayout()
        self.btn_add_vehicle = QPushButton("Yeni Arac Ekle")
        self.btn_edit_vehicle = QPushButton("Arac Duzenle")
        self.btn_refresh_vehicle = QPushButton("Bakim Gecmisi")
        for btn in (
            self.btn_add_vehicle,
            self.btn_edit_vehicle,
            self.btn_refresh_vehicle,
        ):
            btn.setFixedHeight(34)
        self.btn_add_vehicle.clicked.connect(self.open_add_vehicle)
        self.btn_edit_vehicle.clicked.connect(self.open_edit_vehicle)
        self.btn_refresh_vehicle.clicked.connect(self.load_vehicle_table)
        tools.addWidget(self.btn_add_vehicle)
        tools.addWidget(self.btn_edit_vehicle)
        tools.addWidget(self.btn_refresh_vehicle)
        tools.addStretch()
        l.addLayout(tools)

        self.table_vehicles = QTreeWidget()
        self.table_vehicles.setColumnCount(7)
        self.table_vehicles.setHeaderLabels(
            ["Plaka", "Marka", "Model", "Yil", "Arac Tipi", "Yakit", "KM"]
        )
        self.table_vehicles.header().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table_vehicles.setStyleSheet(self._table_qss())
        self.table_vehicles.itemSelectionChanged.connect(self.load_vehicle_history)
        self.table_vehicles.itemDoubleClicked.connect(lambda item, col: self.open_edit_vehicle())
        l.addWidget(self.table_vehicles)

        self.table_vehicle_history = QTreeWidget()
        self.table_vehicle_history.setColumnCount(5)
        self.table_vehicle_history.setHeaderLabels(
            ["Bakim Tarihi", "Sonraki Bakim", "Randevu", "Hatirlatma", "Foto"]
        )
        self.table_vehicle_history.setStyleSheet(self._table_qss())
        l.addWidget(self.table_vehicle_history)

    def load_stats(self):
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        while self.currency_layout.count():
            item = self.currency_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cur = self.db.conn.cursor()

        def _scalar(default=0):
            row = cur.fetchone()
            if not row:
                return default
            try:
                return row[0] if row[0] is not None else default
            except Exception:
                return default

        device_filter, device_params = self._customer_device_filter()
        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM devices
            WHERE {device_filter}
            """,
            device_params,
        )
        total_serv = _scalar(0)

        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM devices
            WHERE {device_filter}
              AND status NOT IN ('Teslim Edildi', 'İptal', 'Bitti')
            """,
            device_params,
        )
        active_serv = _scalar(0)

        cur.execute(
            """
            SELECT SUM(try_equivalent)
            FROM currency_transactions
            WHERE customer_id=? AND transaction_type='DEBIT'
            """,
            (self.customer_id,),
        )
        total_ciro = _scalar(0.0)

        self.stats_layout.addWidget(
            StatBox("Toplam İşlem", total_serv, "🔧", tc("accent", default="#3B82F6"))
        )
        self.stats_layout.addWidget(
            StatBox("Aktif İşlem", active_serv, "⚡", tc("warning", default="#F59E0B"))
        )
        self.stats_layout.addWidget(
            StatBox(
                "Toplam Ciro",
                CurrencyHelper.format_from_try(
                    total_ciro,
                    db=self.db,
                    currency_code=CurrencyHelper.get_code(self.db),
                ),
                "💰",
                tc("success", default="#10B981"),
            )
        )
        self.stats_layout.addStretch()

        def create_cur_box(label, val, currency_code, color):
            box = QFrame()
            box.setFixedSize(220, 80)
            box.setStyleSheet(
                theme_qss(
                    "background-color: @surface; border: 1px solid @border; border-radius: 12px;"
                )
            )
            l = QVBoxLayout(box)
            title = QLabel(label)
            title.setStyleSheet(
                theme_qss("color: @text_muted; font-size: 9px; font-weight: bold;")
            )
            v = QLabel(CurrencyHelper.format_amount(val, currency_code=currency_code))
            v.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: 800;")
            l.addWidget(title)
            l.addWidget(v)
            return box

        try:
            cur.execute(
                """
                SELECT currency, balance
                FROM customer_currency_balances
                WHERE customer_id=?
                """,
                (self.customer_id,),
            )
            balances_by_currency = {
                str(row[0] or "TRY").upper(): float(row[1] or 0.0)
                for row in (cur.fetchall() or [])
            }
        except Exception as e:
            logger.debug(f"Customer360 balance lookup failed: {e}")
            balances_by_currency = {}

        def _bal(cur_code):
            return balances_by_currency.get(cur_code, 0.0)

        display_currency = CurrencyHelper.get_code(self.db)
        display_balance = 0.0
        missing_rate_codes = []
        for code in ("TRY", "USD", "EUR"):
            balance = float(_bal(code) or 0.0)
            if abs(balance) < 0.0001:
                continue
            try:
                display_balance += CurrencyHelper.convert_amount(
                    self.db,
                    balance,
                    from_currency=code,
                    to_currency=display_currency,
                )
            except ValueError as exc:
                missing_rate_codes.append(code)
                logger.warning(
                    "Customer360 balance conversion skipped for %s: %s",
                    code,
                    exc,
                )
        balance_color = (
            tc("success", default="#10B981")
            if display_balance >= 0
            else tc("danger", default="#EF4444")
        )
        balance_label = f"AKTIF BAKIYE ({display_currency})"
        if display_balance < 0:
            balance_label = f"MUSTERI NET BORCU ({display_currency})"
        elif display_balance > 0:
            balance_label = f"MUSTERI ALACAGI ({display_currency})"
        if missing_rate_codes:
            balance_label = "KUR EKSIK (" + ", ".join(missing_rate_codes) + ")"
            balance_color = tc("danger", default="#EF4444")
        self.currency_layout.addWidget(
            create_cur_box(
                balance_label,
                abs(display_balance),
                display_currency,
                balance_color,
            )
        )
        self.currency_layout.addStretch()

    def _customer_device_filter(self):
        if self.customer_id:
            return "customer_id=? AND is_deleted=0", (self.customer_id,)
        return (
            "TRIM(UPPER(customer_name))=TRIM(UPPER(?)) AND is_deleted=0",
            (self.customer_name,),
        )

    def _used_part_try_value(self, price, currency, exchange_rate, price_try):
        price = float(price or 0.0)
        currency = str(currency or "TRY").upper()
        stored_try = float(price_try or 0.0)
        if stored_try > 0:
            return stored_try
        if currency == "TRY":
            return price
        rate = float(exchange_rate or 0.0)
        if rate > 1.0:
            return price * rate
        return CurrencyHelper.convert_amount(self.db, price, currency, "TRY")

    def load_service_table(self):
        self.table_service.clear()
        cur = self.db.conn.cursor()
        display_currency = CurrencyHelper.get_code(self.db)
        device_filter, device_params = self._customer_device_filter()
        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM devices
            WHERE {device_filter}
            """,
            device_params,
        )
        total_rows = int((cur.fetchone() or [0])[0] or 0)
        self._update_history_pager("service", total_rows)
        offset = self._history_pages["service"] * self._history_page_size
        cur.execute(
            f"""
            SELECT tracking_no, device_brand, device_model, status, entry_date, labor_cost, cargo_fee
            FROM devices
            WHERE {device_filter}
            ORDER BY entry_date DESC
            LIMIT ? OFFSET ?
            """,
            (
                *device_params,
                self._history_page_size,
                offset,
            ),
        )
        rows = cur.fetchall()
        tracking_numbers = [str(row[0]) for row in rows if row[0]]
        parts_by_tracking = {}
        transactions_by_tracking = {}

        if tracking_numbers:
            placeholders = ", ".join("?" for _ in tracking_numbers)
            try:
                cur.execute("PRAGMA table_info(used_parts)")
                cols = {str(row[1]) for row in (cur.fetchall() or [])}
                deleted_col = (
                    "is_deleted"
                    if "is_deleted" in cols
                    else ("is_archived" if "is_archived" in cols else None)
                )
                used_parts_query = (
                    "SELECT tracking_no, part_name, price, {quantity}, "
                    "{currency}, {rate}, {price_try} FROM used_parts "
                    "WHERE tracking_no IN ({placeholders})"
                ).format(
                    quantity=(
                        "COALESCE(quantity, 1)" if "quantity" in cols else "1"
                    ),
                    currency=(
                        "COALESCE(currency, 'TRY')"
                        if "currency" in cols
                        else "'TRY'"
                    ),
                    rate=(
                        "COALESCE(exchange_rate, 1)"
                        if "exchange_rate" in cols
                        else "1"
                    ),
                    price_try=(
                        "COALESCE(price_try, 0)" if "price_try" in cols else "0"
                    ),
                    placeholders=placeholders,
                )
                if deleted_col:
                    used_parts_query += f" AND COALESCE({deleted_col}, 0) = 0"
                cur.execute(used_parts_query, tuple(tracking_numbers))
                for part_row in cur.fetchall() or []:
                    parts_by_tracking.setdefault(str(part_row[0]), []).append(
                        part_row[1:]
                    )
            except Exception as e:
                logger.debug(f"Customer360 bulk part lookup failed: {e}")

            try:
                cur.execute(
                    f"""
                    SELECT
                        tracking_no,
                        currency,
                        MAX(amount) AS debit_amount,
                        MAX(CASE WHEN transaction_type='DEBIT' THEN
                            CASE WHEN links.paid IS NOT NULL THEN MAX(amount-links.paid, 0)
                                 WHEN legacy.paid IS NOT NULL THEN MAX(amount-legacy.paid, 0)
                                 ELSE MAX(COALESCE(-current_balance, 0), 0) END
                            ELSE 0 END) AS remaining_amount
                    FROM currency_transactions ct
                    LEFT JOIN (SELECT debt_txn_id, SUM(amount) AS paid FROM payment_debt_links GROUP BY debt_txn_id) links
                      ON links.debt_txn_id=ct.id
                    LEFT JOIN (SELECT d.id, SUM(c.amount) AS paid
                               FROM currency_transactions d JOIN currency_transactions c
                                 ON c.customer_id=d.customer_id AND c.currency=d.currency
                                AND c.transaction_type='CREDIT'
                                AND (c.tracking_no=d.tracking_no OR c.tracking_no=d.tracking_no || '-PAY')
                               WHERE d.transaction_type='DEBIT' GROUP BY d.id) legacy
                      ON legacy.id=ct.id
                    WHERE ct.customer_id=?
                      AND ct.tracking_no IN ({placeholders})
                    GROUP BY tracking_no, currency
                    """,
                    (self.customer_id, *tracking_numbers),
                )
                for tx_row in cur.fetchall() or []:
                    transactions_by_tracking.setdefault(
                        str(tx_row[0]), []
                    ).append(tx_row[1:])
            except Exception as e:
                logger.debug(f"Customer360 bulk transaction lookup failed: {e}")

        for tno, brand, model, status, date, labor, cargo_fee in rows:
            part_rows = parts_by_tracking.get(str(tno), [])
            part_sum = sum(
                self._used_part_try_value(row[1], row[3], row[4], row[5])
                * float(row[2] or 1)
                for row in part_rows
            )
            raw_total = float(labor or 0) + float(cargo_fee or 0) + float(part_sum)

            tx_rows = transactions_by_tracking.get(str(tno), [])
            tx_rows.sort(
                key=lambda row: (
                    str(row[0] or "TRY").upper() != display_currency,
                    str(row[0] or "TRY"),
                )
            )

            if tx_rows:
                # Keep the currency of the service debit. Parts may be priced
                # in USD/EUR; the service ledger must not rewrite that amount
                # based on unrelated customer-cari transactions.
                primary_currency = tx_rows[0][0] or display_currency
                total = float(tx_rows[0][1] or 0.0)
                remaining = max(0.0, float(tx_rows[0][2] or 0.0))
            else:
                primary_currency = display_currency
                total = raw_total
                remaining = raw_total

            item = QTreeWidgetItem(self.table_service)
            item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                {
                    "source": "service",
                    "tracking_no": tno,
                    "currency": primary_currency,
                    "amount": total,
                    "try_amount": raw_total,
                    "remaining": remaining,
                    "title": f"{brand} {model}",
                },
            )
            item.setText(0, format_date(date, self.db) if date else "")
            item.setText(1, f"{brand} {model} (#{tno})")
            item.setText(2, status)
            item.setText(
                3,
                CurrencyHelper.format_amount(
                    total,
                    db=self.db,
                    currency_code=primary_currency,
                ),
            )

            if remaining > 0.01:
                btn_pay = QPushButton(
                    "Ödeme Al ({amount})".format(
                        amount=CurrencyHelper.format_amount(
                            remaining,
                            db=self.db,
                            currency_code=primary_currency,
                        )
                    )
                )
                btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_pay.setFixedHeight(28)
                btn_pay.setStyleSheet(
                    theme_qss(
                        """
                        QPushButton {
                            background: @success;
                            color: @selection_text;
                            border: none;
                            border-radius: 8px;
                            padding: 0 10px;
                            font-size: 11px;
                            font-weight: 700;
                        }
                        QPushButton:hover { background: @accent; }
                        """
                    )
                )
                btn_pay.clicked.connect(
                    lambda _=False, t=tno, a=remaining, c=primary_currency, b=brand, m=model: (
                        self._pay_service(t, a, c, f"{b} {m}")
                    )
                )
                self.table_service.setItemWidget(item, 4, btn_pay)

            if float(labor or 0) > 0:
                child = QTreeWidgetItem(item)
                child.setText(1, "↳ Servis İşçilik Ücreti")
                child.setText(
                    3,
                    CurrencyHelper.format_amount(
                        float(labor or 0),
                        db=self.db,
                        currency_code=primary_currency,
                    ),
                )
                child.setForeground(1, QColor(tc("text_muted", default="#64748B")))

            if float(cargo_fee or 0) > 0:
                child = QTreeWidgetItem(item)
                child.setText(1, "↳ Kargo Ücreti")
                child.setText(
                    3,
                    CurrencyHelper.format_amount(
                        float(cargo_fee or 0),
                        db=self.db,
                        currency_code=primary_currency,
                    ),
                )
                child.setForeground(1, QColor(tc("text_muted", default="#64748B")))

            for p_name, p_price, p_qty, p_currency, p_rate, p_price_try in part_rows:
                child = QTreeWidgetItem(item)
                qty_text = f" x{int(p_qty or 1)}" if int(p_qty or 1) > 1 else ""
                child.setText(1, f"\u21b3 {p_name}{qty_text}")
                original_total = float(p_price or 0) * float(p_qty or 1)
                part_try_total = self._used_part_try_value(
                    p_price, p_currency, p_rate, p_price_try
                ) * float(p_qty or 1)
                original_text = CurrencyHelper.format_amount(
                    original_total,
                    db=self.db,
                    currency_code=str(p_currency or "TRY").upper(),
                )
                if str(p_currency or "TRY").upper() != "TRY":
                    original_text += " ({})".format(
                        CurrencyHelper.format_amount(
                            part_try_total, db=self.db, currency_code="TRY"
                        )
                    )
                child.setText(
                    3,
                    original_text,
                )
                child.setForeground(1, QColor(tc("text_muted", default="#64748B")))

            item.setExpanded(True)

    def load_cari_table(self):
        self.table_cari.clear()
        cur = self.db.conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM currency_transactions WHERE customer_id=?",
            (self.customer_id,),
        )
        total_rows = int((cur.fetchone() or [0])[0] or 0)
        self._update_history_pager("cari", total_rows)
        offset = self._history_pages["cari"] * self._history_page_size
        cur.execute(
            """
            SELECT created_at, description, amount, currency, exchange_rate, try_equivalent, transaction_type, id, tracking_no, current_balance
            FROM currency_transactions
            WHERE customer_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (self.customer_id, self._history_page_size, offset),
        )

        transaction_rows = list(cur.fetchall() or [])
        tracking_by_transaction = {}
        tracking_numbers = set()
        for transaction_row in transaction_rows:
            transaction_id = transaction_row[7]
            tracking_value = str(transaction_row[8] or "").strip()
            if not tracking_value:
                tracking_match = re.search(
                    r"#([A-Z]+-\d+|\d+)",
                    str(transaction_row[1] or ""),
                    re.IGNORECASE,
                )
                if tracking_match:
                    tracking_value = tracking_match.group(1)
            if tracking_value:
                tracking_by_transaction[transaction_id] = tracking_value
                tracking_numbers.add(tracking_value)
        parts_by_tracking = self._load_tracking_parts_map(tracking_numbers)

        for (
            date,
            desc,
            amt,
            curr,
            rate,
            try_val,
            t_type,
            tid,
            tracking_no,
            current_balance,
        ) in transaction_rows:
            parent = QTreeWidgetItem(self.table_cari)
            parent.setData(
                0,
                Qt.ItemDataRole.UserRole,
                {
                    "source": "cari",
                    "transaction_id": tid,
                    "tracking_no": tracking_no,
                    "currency": curr or "TRY",
                    "exchange_rate": float(rate or 1.0),
                    "amount": float(amt or 0),
                    "try_amount": float(try_val or 0),
                    "transaction_type": t_type,
                    "description": desc or "",
                },
            )
            parent.setText(0, format_date(date, self.db))
            description_lines = self._split_description_lines(desc)
            type_label = (
                description_lines[0]
                if description_lines
                else ("Satış İşlemi" if t_type == "DEBIT" else "Ödeme (Tahsilat)")
            )
            color_hex = (
                tc("accent", default="#3B82F6")
                if t_type == "DEBIT"
                else tc("success", default="#10B981")
            )
            parent.setText(1, type_label)
            parent.setForeground(1, QColor(color_hex))
            parent.setText(2, curr)
            parent.setText(3, f"{rate:.4f}" if rate else "1.0000")
            parent.setText(
                4,
                CurrencyHelper.format_amount(
                    float(amt or 0), currency_code=curr or "TRY"
                ),
            )

            is_settled = False
            remaining_debt = float(amt or 0)
            if t_type == "DEBIT":
                paid_row = self.db.conn.execute(
                    "SELECT SUM(amount) FROM payment_debt_links WHERE debt_txn_id=?",
                    (tid,),
                ).fetchone()
                if paid_row[0] is None:
                    legacy_row = self.db.conn.execute(
                        """SELECT SUM(amount) FROM currency_transactions
                           WHERE customer_id=? AND currency=? AND transaction_type='CREDIT'
                             AND (tracking_no=? OR tracking_no=? || '-PAY')""",
                        (self.customer_id, curr, tracking_no, tracking_no),
                    ).fetchone()
                    paid_value = legacy_row[0] if legacy_row and legacy_row[0] is not None else None
                    remaining_debt = max(0.0, float(amt or 0) - float(paid_value or 0)) if paid_value is not None else max(0.0, -float(current_balance or 0.0))
                else:
                    remaining_debt = max(0.0, float(amt or 0) - float(paid_row[0] or 0))
                is_settled = remaining_debt <= 0.01

            if t_type == "DEBIT":
                status = "Tahsil Edildi" if is_settled else "Tahsilat Bekliyor"
                status_color = tc("success") if is_settled else tc("warning")
            else:
                status = "Tamamlandı"
                status_color = tc("success")

            parent.setText(5, status)
            parent.setForeground(5, QColor(status_color))
            parent.setText(6, "")

            if t_type == "DEBIT" and not is_settled:
                btn_pay = QPushButton(
                    f"Odeme Al ({CurrencyHelper.format_amount(remaining_debt, currency_code=curr or 'TRY')})"
                )
                btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_pay.setFixedSize(160, 30)
                btn_pay.setStyleSheet(
                    theme_qss(
                        """
                        QPushButton {
                            background: @success;
                            color: @selection_text;
                            border: none;
                            border-radius: 10px;
                            padding: 0 12px;
                            font-size: 11px;
                            font-weight: 800;
                        }
                        QPushButton:hover {
                            background: @accent;
                        }
                        """
                    )
                )
                btn_pay.clicked.connect(
                    lambda _=False, currency=curr, amount=remaining_debt, ref_tracking=tracking_no, ref_desc=desc, debt_id=tid: (
                        self.open_payment_dialog(
                            currency,
                            amount,
                            ref_tracking,
                            ref_desc,
                            preselected_debt_ids=[debt_id],
                        )
                    )
                )
                self.table_cari.setItemWidget(parent, 6, btn_pay)

            for line in description_lines[1:]:
                child = QTreeWidgetItem(parent)
                child.setText(1, f"-> {line}")
                child.setForeground(1, QColor(tc("text_muted", default="#64748B")))

            detail_tracking = tracking_by_transaction.get(tid)
            if detail_tracking:
                self._append_tracking_parts(
                    parent,
                    detail_tracking,
                    parts_by_tracking=parts_by_tracking,
                )

            parent.setExpanded(True)

    def _split_description_lines(self, description):
        return [
            line.strip() for line in str(description or "").splitlines() if line.strip()
        ]

    def _load_tracking_parts_map(self, tracking_numbers):
        normalized = sorted(
            {
                str(tracking_no or "").strip()
                for tracking_no in (tracking_numbers or [])
                if str(tracking_no or "").strip()
            }
        )
        if not normalized:
            return {}
        try:
            cur = self.db.conn.cursor()
            cur.execute("PRAGMA table_info(used_parts)")
            cols = {str(row[1]) for row in cur.fetchall() or []}
            deleted_col = (
                "is_deleted"
                if "is_deleted" in cols
                else ("is_archived" if "is_archived" in cols else None)
            )
            placeholders = ", ".join("?" for _ in normalized)
            query = (
                "SELECT tracking_no, part_name, price, {quantity}, "
                "{currency}, {rate}, {price_try} "
                "FROM used_parts WHERE tracking_no IN ({placeholders})"
            ).format(
                quantity=(
                    "COALESCE(quantity, 1)" if "quantity" in cols else "1"
                ),
                currency=(
                    "COALESCE(currency, 'TRY')"
                    if "currency" in cols
                    else "'TRY'"
                ),
                rate=(
                    "COALESCE(exchange_rate, 1)"
                    if "exchange_rate" in cols
                    else "1"
                ),
                price_try=(
                    "COALESCE(price_try, 0)" if "price_try" in cols else "0"
                ),
                placeholders=placeholders,
            )
            if deleted_col:
                query += f" AND COALESCE({deleted_col}, 0)=0"
            cur.execute(query, tuple(normalized))
            result = {}
            for row in cur.fetchall() or []:
                result.setdefault(str(row[0]), []).append(row[1:])
            return result
        except Exception as exc:
            logger.debug(
                f"Customer360 bulk tracking part lookup skipped: {exc}"
            )
            return {}

    def _append_tracking_parts(
        self,
        parent,
        tracking_no,
        parts_by_tracking=None,
    ):
        try:
            if parts_by_tracking is None:
                parts_by_tracking = self._load_tracking_parts_map([tracking_no])
            for (
                part_name,
                price,
                quantity,
                currency,
                exchange_rate,
                price_try,
            ) in parts_by_tracking.get(str(tracking_no), []):
                quantity = float(quantity or 1)
                quantity_text = (
                    f" x{quantity:g}" if abs(quantity - 1.0) > 0.0001 else ""
                )
                part_total_try = (
                    self._used_part_try_value(
                        price,
                        currency,
                        exchange_rate,
                        price_try,
                    )
                    * quantity
                )
                child = QTreeWidgetItem(parent)
                child.setText(1, f"-> {part_name}{quantity_text}")
                child.setText(
                    4,
                    CurrencyHelper.format_from_try(
                        part_total_try,
                        db=self.db,
                        currency_code=CurrencyHelper.get_code(self.db),
                    ),
                )
                child.setForeground(1, QColor(tc("text_muted", default="#64748B")))
        except Exception as exc:
            logger.debug(f"Customer360 tracking part detail append skipped: {exc}")

    def _service_is_closed(self, tracking_no):
        """Return whether a service reached a collection-eligible closed state."""
        row = self.db.conn.execute(
            "SELECT status FROM devices WHERE customer_id=? AND tracking_no=? LIMIT 1",
            (self.customer_id, tracking_no),
        ).fetchone()
        status = str(row[0] or "").strip().casefold() if row else ""
        return status in {"teslim edildi", "teslim", "bitti", "tamamlandi", "tamamland\u0131", "closed", "completed"}

    def _warn_service_must_close(self, tracking_no):
        show_warning(
            self,
            f"{self.customer_name} i\u00e7in \u00f6nce servisi kapat\u0131n. Tahsilat servis kapat\u0131ld\u0131ktan sonra al\u0131nabilir.",
        )

    def _pay_service(self, tracking_no, amount, currency, device_label):
        """Servis listesinden doğrudan ödeme al"""
        if not self._service_is_closed(tracking_no):
            self._warn_service_must_close(tracking_no)
            return
        desc = f"Servis tahsilatı - {device_label} (#{tracking_no})"
        preselected_debt_ids = self._get_open_debt_ids_for_tracking(
            tracking_no, currency
        )
        remaining_amount = self._get_remaining_debt_for_tracking(tracking_no, currency)
        self.open_payment_dialog(
            currency=currency,
            amount=remaining_amount if remaining_amount > 0 else amount,
            tracking_no=tracking_no,
            reference_desc=desc,
            preselected_debt_ids=preselected_debt_ids,
        )
        self.load_service_table()

    def _get_open_debt_ids_for_tracking(self, tracking_no, currency=None):
        try:
            query = """
                SELECT d.id
                FROM currency_transactions d
                LEFT JOIN (
                    SELECT debt_txn_id, SUM(amount) AS paid
                    FROM payment_debt_links GROUP BY debt_txn_id
                ) links ON links.debt_txn_id=d.id
                LEFT JOIN (
                    SELECT d2.id, SUM(c.amount) AS paid
                    FROM currency_transactions d2
                    JOIN currency_transactions c
                      ON c.customer_id=d2.customer_id AND c.currency=d2.currency
                     AND c.transaction_type='CREDIT'
                     AND (c.tracking_no=d2.tracking_no OR c.tracking_no=d2.tracking_no || '-PAY')
                    WHERE d2.transaction_type='DEBIT'
                    GROUP BY d2.id
                ) legacy ON legacy.id=d.id
                WHERE d.customer_id=? AND d.tracking_no=? AND d.transaction_type='DEBIT'
                  AND ROUND(CASE WHEN links.paid IS NOT NULL THEN MAX(d.amount-links.paid, 0)
                                 WHEN legacy.paid IS NOT NULL THEN MAX(d.amount-legacy.paid, 0)
                                 ELSE MAX(COALESCE(-d.current_balance, 0), 0) END, 2) > 0.009
            """
            params = [self.customer_id, tracking_no]
            if currency:
                query += " AND currency=?"
                params.append(currency)
            query += " ORDER BY created_at ASC, id ASC"
            cur = self.db.conn.cursor()
            cur.execute(query, tuple(params))
            return [row[0] for row in (cur.fetchall() or [])]
        except Exception as exc:
            logger.debug(
                f"Customer360 open debt lookup skipped for {tracking_no}: {exc}"
            )
            return []

    def _get_remaining_debt_for_tracking(self, tracking_no, currency=None):
        query = """
            SELECT COALESCE(SUM(CASE WHEN links.paid IS NOT NULL THEN MAX(ct.amount-links.paid, 0)
                WHEN legacy.paid IS NOT NULL THEN MAX(ct.amount-legacy.paid, 0)
                ELSE MAX(COALESCE(-ct.current_balance, 0), 0) END), 0)
            FROM currency_transactions ct
            LEFT JOIN (SELECT debt_txn_id, SUM(amount) AS paid FROM payment_debt_links GROUP BY debt_txn_id) links
              ON links.debt_txn_id=ct.id
            LEFT JOIN (
                SELECT d.id, SUM(c.amount) AS paid
                FROM currency_transactions d
                JOIN currency_transactions c
                  ON c.customer_id=d.customer_id AND c.currency=d.currency
                 AND c.transaction_type='CREDIT'
                 AND (c.tracking_no=d.tracking_no OR c.tracking_no=d.tracking_no || '-PAY')
                WHERE d.transaction_type='DEBIT' GROUP BY d.id
            ) legacy ON legacy.id=ct.id
            WHERE ct.customer_id=? AND ct.tracking_no=? AND ct.transaction_type='DEBIT'
              AND ROUND(CASE WHEN links.paid IS NOT NULL THEN MAX(ct.amount-links.paid, 0)
                             WHEN legacy.paid IS NOT NULL THEN MAX(ct.amount-legacy.paid, 0)
                             ELSE MAX(COALESCE(-ct.current_balance, 0), 0) END, 2) > 0.009
        """
        params=[self.customer_id, tracking_no]
        if currency:
            query += " AND ct.currency=?"; params.append(currency)
        row=self.db.conn.execute(query, tuple(params)).fetchone()
        return float(row[0] or 0.0) if row else 0.0

    def open_payment_dialog(
        self,
        currency=None,
        amount=None,
        tracking_no=None,
        reference_desc=None,
        preselected_debt_ids=None,
    ):
        if tracking_no:
            service_row = self.db.conn.execute(
                "SELECT 1 FROM devices WHERE customer_id=? AND tracking_no=? LIMIT 1",
                (self.customer_id, tracking_no),
            ).fetchone()
            if service_row and not self._service_is_closed(tracking_no):
                self._warn_service_must_close(tracking_no)
                return
        dlg = ModernPaymentDialog(
            self, self.db, {"id": self.customer_id, "name": self.customer_name}
        )
        if currency:
            dlg._apply_selected_currency(currency)
        if preselected_debt_ids:
            dlg.selected_debts = set(preselected_debt_ids)
            dlg._refresh_debt_list()
            dlg._update_selected_total()
        if amount and float(amount or 0) > 0:
            dlg.inp_amount.setText(
                f"{float(amount):,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
        dlg.reference_tracking_no = tracking_no
        dlg.reference_desc = reference_desc

        if dlg.exec():
            data = dlg.get_data() or {}
            if self._save_payment(data):
                self.refresh_financial_views()
                self._emit_financial_data_changed()
                self._announce_payment_received(currency=data.get("currency"))
                parent = self.parent()
                if parent and hasattr(parent, "request_reload"):
                    try:
                        parent.request_reload(delay_ms=0)
                    except TypeError:
                        parent.request_reload()

    def _save_payment(self, data):
        try:
            currency = data.get("currency", "TRY")
            exchange_rate = float(data.get("exchange_rate", 1.0) or 1.0)
            amount = float(data.get("amount", 0) or 0)
            if amount <= 0:
                return False

            base_desc = (data.get("notes") or "").strip()
            reference_tracking = data.get("reference_tracking_no") or None
            reference_desc = (data.get("reference_desc") or "").strip()
            ref_prefix = f"Ref: {reference_tracking}" if reference_tracking else ""
            full_desc = base_desc or "Cari borç kapatma tahsilatı"
            if ref_prefix:
                full_desc = f"{ref_prefix} | {full_desc}"
            if reference_desc:
                full_desc = (
                    f"{full_desc} | Borç Kaydı: {reference_desc.splitlines()[0][:120]}"
                )

            date_value = data.get("date")
            created_at = None
            accounting_date = None
            if date_value:
                parsed = QDate.fromString(str(date_value), "dd.MM.yyyy")
                if parsed.isValid():
                    accounting_date = parsed.toString("yyyy-MM-dd")
                    created_at = (
                        f"{accounting_date} {datetime.now().strftime('%H:%M:%S')}"
                    )

            if not self.db.create_payment_debt_links_table():
                show_error(
                    self,
                    "\u00d6deme da\u011f\u0131t\u0131m tablosu "
                    "haz\u0131rlanamad\u0131.",
                )
                return False

            saved = self.db.add_currency_transaction(
                customer_id=self.customer_id,
                amount=amount,
                currency=currency,
                transaction_type="CREDIT",
                exchange_rate=exchange_rate,
                description=full_desc,
                tracking_no=reference_tracking,
                created_at=created_at,
                commit=False,
            )
            if not saved:
                show_error(self, "Ödeme kaydedilemedi.")
                return False

            payment_txn_id = self.db.get_last_currency_transaction_id()
            if not payment_txn_id:
                logger.error(
                    "Customer360 payment was saved without a transaction id"
                )
                show_error(
                    self,
                    "\u00d6deme kaydedildi ancak i\u015flem kimli\u011fi "
                    "al\u0131namad\u0131.",
                )
                return True

            if payment_txn_id:
                allocation = self.db.apply_payment_to_debts(
                    customer_id=self.customer_id,
                    payment_amount=amount,
                    currency=currency,
                    payment_transaction_id=payment_txn_id,
                    selected_debt_ids=data.get("selected_debt_ids") or None,
                    commit=False,
                )
                if not allocation.get("ok", False):
                    logger.error(
                        "Customer360 debt allocation failed: %s",
                        allocation.get("error") or "unknown error",
                    )
                    show_error(
                        self,
                        "\u00d6deme kaydedildi ancak bor\u00e7lara "
                        "da\u011f\u0131t\u0131lamad\u0131. Uzla\u015ft\u0131rma "
                        "yeniden denenecek.",
                    )

            tl_amount = amount * (exchange_rate if currency != "TRY" else 1.0)

            try:
                accounting_id = self.db.add_transaction(
                    t_type="Gelir",
                    category="Tahsilat",
                    amount=tl_amount,
                    description=full_desc,
                    customer_name=self.customer_name,
                    customer_id=self.customer_id,
                    date=accounting_date,
                    payment_method=data.get("method"),
                    bank_account_id=data.get("bank_account_id"),
                    tracking_no=reference_tracking,
                    ref_no=reference_tracking,
                    currency=currency,
                    original_amount=amount,
                    commit=False,
                )
                if not accounting_id:
                    raise RuntimeError("Accounting transaction could not be recorded")
                self.db.conn.commit()
            except Exception as accounting_exc:
                self.db.conn.rollback()
                logger.error("Customer360 payment rolled back: %s", accounting_exc)
                show_error(self, "Tahsilat ve muhasebe kaydi birlikte kaydedilemedi.")
                return False

            return True
        except Exception as exc:
            logger.exception("Customer360 payment save failed")
            show_error(self, f"Ödeme kaydı sırasında hata: {exc}")
            return False

    def load_currency_ledger(self):
        self.table_ledger.clear()
        cur = self.db.conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*)
            FROM currency_transactions
            WHERE customer_id=? AND currency!='TRY'
            """,
            (self.customer_id,),
        )
        total_rows = int((cur.fetchone() or [0])[0] or 0)
        self._update_history_pager("ledger", total_rows)
        offset = self._history_pages["ledger"] * self._history_page_size
        cur.execute(
            """
            SELECT created_at, currency, transaction_type, amount, current_balance
            FROM currency_transactions
            WHERE customer_id = ? AND currency != 'TRY'
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (self.customer_id, self._history_page_size, offset),
        )
        for created_at, currency, tx_type, amount, balance in cur.fetchall():
            item = QTreeWidgetItem(self.table_ledger)
            item.setText(0, format_date(created_at, self.db))
            item.setText(1, currency)
            item.setText(2, "Borç" if tx_type == "DEBIT" else "Alacak")
            item.setText(3, f"{amount:,.2f}")
            item.setText(4, f"{balance:,.2f}")

    def load_sales_table(self):
        self.table_sales.clear()
        cur = self.db.conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*)
            FROM accounting
            WHERE customer_id=?
              AND type='Gelir'
              AND (
                    category='Sat\u0131\u015f'
                    OR description LIKE 'POS%'
                    OR description LIKE '%Sat\u0131\u015f%'
                  )
            """,
            (self.customer_id,),
        )
        total_rows = int((cur.fetchone() or [0])[0] or 0)
        self._update_history_pager("sales", total_rows)
        offset = self._history_pages["sales"] * self._history_page_size
        cur.execute(
            """
            SELECT id, date, description, amount, COALESCE(payment_method, ''), COALESCE(category, ''),
                   COALESCE(currency, 'TRY'), COALESCE(exchange_rate, 1),
                   COALESCE(try_equivalent, amount), COALESCE(tracking_no, '')
            FROM accounting
            WHERE customer_id = ?
              AND type = 'Gelir'
              AND (
                    category = 'Satış'
                    OR description LIKE 'POS%'
                    OR description LIKE '%Satış%'
                  )
            ORDER BY date DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (self.customer_id, self._history_page_size, offset),
        )
        for (
            txn_id,
            date,
            description,
            amount,
            payment_method,
            category,
            currency,
            exchange_rate,
            try_equivalent,
            tracking_no,
        ) in cur.fetchall():
            parent = QTreeWidgetItem(self.table_sales)
            parent.setData(
                0,
                Qt.ItemDataRole.UserRole,
                {
                    "source": "sale",
                    "transaction_id": txn_id,
                    "tracking_no": tracking_no,
                    "currency": currency or "TRY",
                    "exchange_rate": float(exchange_rate or 1.0),
                    "amount": float(amount or 0),
                    "try_amount": float(try_equivalent or amount or 0),
                    "description": description or "",
                },
            )
            parent.setText(0, format_date(date, self.db))
            lines = [
                line.strip()
                for line in str(description or "").splitlines()
                if line.strip()
            ]
            parent.setText(1, lines[0] if lines else "Ürün Satışı")
            parent.setText(2, payment_method or "Belirtilmedi")
            parent.setText(
                3,
                CurrencyHelper.format_amount(
                    float(amount or 0), currency_code=currency or "TRY"
                ),
            )
            parent.setText(4, category or "Satış")
            for line in lines[1:]:
                child = QTreeWidgetItem(parent)
                child.setText(1, f"↳ {line}")
                child.setForeground(1, QColor(tc("text_muted", default="#64748B")))
            parent.setExpanded(True)

    def load_offer_table(self):
        if not hasattr(self, "table_offers"):
            return
        self.table_offers.clear()
        if not hasattr(self.db, "get_customer_offers"):
            return
        try:
            rows = self.db.get_customer_offers(self.customer_id) or []
            for (
                offer_id,
                offer_no,
                created_at,
                company_name,
                contact_name,
                project_name,
                currency_symbol,
                total,
                status,
                pdf_path,
            ) in rows:
                parent = QTreeWidgetItem(self.table_offers)
                parent.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    {
                        "offer_id": offer_id,
                        "offer_no": offer_no or "",
                        "pdf_path": pdf_path or "",
                        "status": status or "",
                    },
                )
                parent.setText(0, format_date(created_at, self.db))
                parent.setText(1, str(offer_no or ""))
                parent.setText(
                    2,
                    " / ".join(
                        part
                        for part in [str(company_name or ""), str(project_name or "")]
                        if part
                    ),
                )
                parent.setText(3, str(contact_name or ""))
                parent.setText(4, f"{float(total or 0):,.2f} {currency_symbol or ''}")
                status_labels = {
                    "accepted": "Kabul Edildi",
                    "processed": "\u0130\u015flendi",
                    "processing": "\u0130\u015fleniyor",
                    "processing_error": "\u0130\u015flem Hatas\u0131",
                    "revision_pending": "Revizyon Bekliyor",
                    "created": "Teklif",
                    "draft": "Taslak",
                }
                parent.setText(
                    5,
                    status_labels.get(
                        str(status or "").strip().lower(),
                        str(status or ""),
                    ),
                )
                parent.setText(
                    6,
                    "Hazir" if pdf_path and os.path.exists(str(pdf_path)) else "Olusturulur",
                )
                for service, description, qty, unit_price, line_total in (
                    self.db.get_offer_items(offer_id) or []
                ):
                    child = QTreeWidgetItem(parent)
                    child.setText(1, str(service or ""))
                    child.setText(
                        2,
                        clean_offer_line_description(
                            description,
                            service=service,
                        ),
                    )
                    child.setText(3, f"Adet: {float(qty or 0):g}")
                    child.setText(4, f"{float(line_total or 0):,.2f} {currency_symbol or ''}")
                    child.setForeground(1, QColor(tc("text_muted", default="#64748B")))
                try:
                    reversal_rows = self.db.cursor.execute(
                        "SELECT reason, reversed_by, created_at FROM offer_reversals "
                        "WHERE offer_id=? ORDER BY id DESC",
                        (int(offer_id),),
                    ).fetchall()
                    for reason, reversed_by, reversed_at in reversal_rows:
                        child = QTreeWidgetItem(parent)
                        child.setText(1, "Islem geri alindi / revizyon")
                        child.setText(2, str(reason or ""))
                        child.setText(3, str(reversed_by or "System"))
                        child.setText(4, str(reversed_at or ""))
                        child.setForeground(1, QColor(tc("danger", default="#DC2626")))
                except Exception:
                    pass
                parent.setExpanded(True)
        except Exception as exc:
            logger.error(f"Customer360 offer table load failed: {exc}")

    def open_selected_offer_pdf(self, item, _column):
        while item and not item.data(0, Qt.ItemDataRole.UserRole):
            item = item.parent()
        data = item.data(0, Qt.ItemDataRole.UserRole) if item else {}
        pdf_path = str((data or {}).get("pdf_path") or "").strip()
        offer_id = (data or {}).get("offer_id")
        if not offer_id:
            if pdf_path and os.path.exists(pdf_path):
                os.startfile(pdf_path)
                return
            show_error(self, "Teklif kaydi secilemedi.")
            return
        try:
            self._generate_offer_pdf(
                offer_id,
                save_path=pdf_path if pdf_path else None,
                open_after=True,
            )
            self.load_offer_table()
        except Exception as exc:
            logger.exception("Customer360 synchronized offer PDF generation failed")
            if pdf_path and os.path.exists(pdf_path):
                os.startfile(pdf_path)
                return
            show_error(self, f"Teklif PDF dosyasi olusturulamadi: {exc}")

    def _selected_offer_item(self):
        item = self.table_offers.currentItem() if hasattr(self, "table_offers") else None
        while item and not item.data(0, Qt.ItemDataRole.UserRole):
            item = item.parent()
        if item:
            return item
        if hasattr(self, "table_offers") and self.table_offers.topLevelItemCount():
            return self.table_offers.topLevelItem(0)
        return None

    def _selected_offer_data(self):
        item = self._selected_offer_item()
        data = item.data(0, Qt.ItemDataRole.UserRole) if item else {}
        return dict(data or {})

    def open_selected_offer_from_button(self):
        item = self._selected_offer_item()
        if not item:
            show_error(self, "L\u00fctfen bir teklif se\u00e7in.")
            return
        self.open_selected_offer_pdf(item, 0)

    def _main_window_for_offer_action(self):
        candidate = self.parent()
        visited = set()
        while candidate and id(candidate) not in visited:
            visited.add(id(candidate))
            if hasattr(candidate, "on_menu_click") and hasattr(candidate, "get_page"):
                return candidate
            nested = getattr(candidate, "main_window", None)
            if nested and hasattr(nested, "on_menu_click"):
                return nested
            candidate = candidate.parent() if hasattr(candidate, "parent") else None
        return getattr(self, "main_window", None)

    def edit_selected_offer(self):
        data = self._selected_offer_data()
        offer_id = data.get("offer_id")
        if not offer_id:
            show_error(self, "L\u00fctfen d\u00fczenlenecek teklifi se\u00e7in.")
            return
        status = str(data.get("status") or "").strip().lower()
        status = (
            status.replace("\u0131", "i")
            .replace("\u015f", "s")
            .replace("\u0130", "i")
            .replace("\u015e", "s")
            .replace("\u0307", "")
        )
        if status in {"accepted", "processed", "islenmis", "kabul edildi"}:
            show_error(
                self,
                "Kabul edilmi\u015f teklif de\u011fi\u015ftirilemez. Yeni teklif olu\u015fturun.",
            )
            return

        main_window = self._main_window_for_offer_action()
        if not main_window:
            show_error(self, "Sat\u0131\u015f sayfas\u0131na ula\u015f\u0131lamad\u0131.")
            return
        try:
            main_window.on_menu_click(150)
            hub = main_window.get_page(150)
            sales_page = getattr(hub, "sales_page", None)
            if sales_page is None and hasattr(hub, "_ensure_tab_loaded"):
                hub._ensure_tab_loaded(0)
                sales_page = getattr(hub, "sales_page", None)
            if not sales_page or not hasattr(sales_page, "load_offer_for_edit"):
                raise RuntimeError("Sales Hub offer editor is unavailable.")
            sales_page.load_offer_for_edit(int(offer_id))
            self.accept()
        except Exception as exc:
            logger.exception("Customer360 offer edit navigation failed")
            show_error(self, f"Teklif d\u00fczenlemeye a\u00e7\u0131lamad\u0131: {exc}")

    def reverse_selected_offer(self):
        data = self._selected_offer_data()
        offer_id = data.get("offer_id")
        if not offer_id:
            show_error(self, "L\u00fctfen geri al\u0131nacak teklifi se\u00e7in.")
            return
        reason, accepted = ModernInputDialog.get_multiline(
            self,
            "\u0130\u015flemi Geri Al ve Revize Et",
            "Geri alma/revizyon gerek\u00e7esini yaz\u0131n:",
        )
        if not accepted or not str(reason or "").strip():
            return
        try:
            from src.services.offer_acceptance_service import OfferAcceptanceService

            main_window = self._main_window_for_offer_action()
            current_user = getattr(main_window, "current_user", {}) if main_window else {}
            reversed_by = ""
            if isinstance(current_user, dict):
                reversed_by = str(
                    current_user.get("username")
                    or current_user.get("full_name")
                    or ""
                )
            result = OfferAcceptanceService(self.db).reverse_for_revision(
                int(offer_id), str(reason), reversed_by=reversed_by
            )
            self.load_offer_table()
            self.refresh_financial_views()
            self._emit_financial_data_changed()
            if main_window:
                try:
                    main_window.stock_updated.emit()
                except Exception:
                    pass
                for page_id in (21, 40, 50, 60, 101, 150):
                    try:
                        main_window.refresh_loaded_page(page_id)
                    except Exception:
                        pass
            show_success(
                self,
                "Teklif i\u015flemi geri al\u0131nd\u0131. Stok ve cari hareketler ters kay\u0131tland\u0131; teklif revizyona a\u00e7\u0131l\u0131yor.",
            )
            self.edit_selected_offer()
        except Exception as exc:
            logger.exception("Customer360 offer reversal failed")
            show_error(self, f"Teklif i\u015flemi geri al\u0131namad\u0131: {exc}")

    def process_selected_offer(self):
        data = self._selected_offer_data()
        offer_id = data.get("offer_id")
        if not offer_id:
            show_error(self, "L\u00fctfen i\u015flenecek teklifi se\u00e7in.")
            return
        try:
            offer = self.db.get_offer_record(int(offer_id))
            if not offer:
                raise RuntimeError("Offer record was not found.")
            status = str(offer["status"] or "").strip().lower()
            status = (
                status.replace("\u0131", "i")
                .replace("\u015f", "s")
                .replace("\u0130", "i")
                .replace("\u015e", "s")
                .replace("\u0307", "")
            )
            if status in {"accepted", "processed", "islenmis", "kabul edildi"}:
                show_error(self, "Bu teklif daha \u00f6nce m\u00fc\u015fteri hesab\u0131na i\u015flendi.")
                return

            from src.ui.dialogs.offer_acceptance_dialog import OfferAcceptanceDialog

            dialog = OfferAcceptanceDialog(
                total=float(offer["total"] or 0),
                currency_code=str(offer["currency_code"] or "TRY"),
                offer_no=str(offer["offer_no"] or ""),
                parent=self,
            )
            if not dialog.exec():
                return

            main_window = self._main_window_for_offer_action()
            current_user = getattr(main_window, "current_user", {}) if main_window else {}
            accepted_by = ""
            if isinstance(current_user, dict):
                accepted_by = str(
                    current_user.get("username")
                    or current_user.get("full_name")
                    or ""
                )

            from src.services.offer_acceptance_service import (
                OfferAcceptanceService,
            )

            result = OfferAcceptanceService(self.db).accept(
                int(offer_id),
                payment_amount=dialog.payment_amount,
                payment_method=dialog.payment_method,
                accepted_by=accepted_by,
            )
            self.load_offer_table()
            self.refresh_financial_views()
            self._emit_financial_data_changed()
            if main_window:
                try:
                    main_window.stock_updated.emit()
                except Exception:
                    pass
                for page_id in (21, 40, 50, 60, 101, 150):
                    try:
                        main_window.refresh_loaded_page(page_id)
                    except Exception:
                        pass
            show_success(
                self,
                "Teklif kabul edildi. "
                f"Pe\u015finat: {result['payment']:,.2f} {result['currency']} | "
                f"Cari bakiye: {result['remaining']:,.2f} {result['currency']}",
            )
        except Exception as exc:
            logger.exception("Customer360 offer processing failed")
            show_error(self, f"Teklif m\u00fc\u015fteri hesab\u0131na i\u015flenemedi: {exc}")

    def _generate_offer_pdf(self, offer_id, save_path=None, open_after=False):
        data = load_offer_pdf_data(self.db, offer_id)
        offer = data["offer"]
        offer_no = str(offer.get("offer_no") or f"PRF-{offer_id}").strip()
        safe_offer_no = re.sub(r"[^A-Za-z0-9_-]+", "-", offer_no).strip("-")
        if not safe_offer_no:
            safe_offer_no = f"PRF-{offer_id}"

        if not save_path:
            offer_dir = os.path.join(PathHelper.get_app_data_dir(), "offers")
            os.makedirs(offer_dir, exist_ok=True)
            save_path = os.path.join(offer_dir, f"Teklif_{safe_offer_no}.pdf")
        save_path = os.path.abspath(str(save_path))
        if not save_path.lower().endswith(".pdf"):
            save_path += ".pdf"

        template = str(offer.get("template_type") or "modern").strip().lower()
        if template not in {"modern", "corporate", "minimal"}:
            template = "modern"
        configured_company = str(self.db.get_setting("company_name", "") or "").strip()
        company_name = configured_company or str(offer.get("company_name") or "AYEC Pro")

        from src.utils.pdf_manager import PDFManagerQt

        manager = PDFManagerQt(self.db)
        manager._open_file = lambda _filename: None
        success, result = manager.create_proforma(
            template_type=template,
            cart_items=data["items"],
            totals=data["totals"],
            company_name=company_name,
            customer_name=str(offer.get("customer_name") or self.customer_name),
            project_name=str(offer.get("project_name") or ""),
            contact_name=str(offer.get("contact_name") or offer.get("customer_name") or ""),
            reference_no=offer_no,
            offer_date=offer.get("created_at"),
            customer_company=data.get("customer_company") or "",
            currency_code=data.get("currency_code") or "TRY",
            save_path=save_path,
            currency=data["currency_symbol"],
        )
        if not success or not os.path.exists(save_path):
            raise RuntimeError(str(result or "PDF uretimi basarisiz."))

        self.db.cursor.execute(
            "UPDATE offers SET pdf_path=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (save_path, int(offer_id)),
        )
        self.db.conn.commit()
        if open_after:
            os.startfile(save_path)
        return save_path

    def load_vehicle_table(self):
        if not self.is_automotive:
            return
        self.table_vehicles.clear()
        vehicles = list(self.db.get_customer_vehicles(self.customer_id) or [])
        for row in vehicles:
            item = QTreeWidgetItem(self.table_vehicles)
            item.setData(0, Qt.ItemDataRole.UserRole, row["id"])
            item.setText(0, str(row["plate"] or ""))
            item.setText(1, str(row["brand"] or ""))
            item.setText(2, str(row["model"] or ""))
            item.setText(3, str(row["year"] or ""))
            item.setText(4, str(row["vehicle_type"] or ""))
            item.setText(5, str(row["fuel_type"] or ""))
            item.setText(6, str(row["last_known_odometer"] or 0))
        self.load_vehicle_history()

    def load_vehicle_history(self):
        if not self.is_automotive:
            return
        self.table_vehicle_history.clear()
        selected = self.table_vehicles.currentItem()
        if not selected:
            return
        plate = selected.text(0).strip()
        for row in self.db.get_vehicle_maintenance_cards(plate):
            if str(row["vehicle_plate"] or "").strip().upper() != plate.upper():
                continue
            item = QTreeWidgetItem(self.table_vehicle_history)
            item.setText(0, str(row["service_date"] or ""))
            item.setText(1, str(row["next_maintenance_date"] or ""))
            item.setText(2, str(row["appointment_date"] or ""))
            item.setText(3, str(row["reminder_date"] or ""))
            item.setText(4, str(row["photo_count"] or 0))

    def open_add_vehicle(self):
        if not self.is_automotive:
            return
        dlg = CustomerVehicleDialog(
            self.db, self.customer_id, self.customer_name, parent=self
        )
        if dlg.exec():
            self.load_vehicle_table()
            show_success(self, "Arac kaydedildi.")

    def open_edit_vehicle(self):
        if not self.is_automotive:
            return
        selected = self.table_vehicles.currentItem()
        if not selected:
            show_error(self, "Duzenlemek icin bir arac secin.")
            return
        vehicle_id = selected.data(0, Qt.ItemDataRole.UserRole)
        row = self.db.get_customer_vehicle(vehicle_id)
        dlg = CustomerVehicleDialog(
            self.db, self.customer_id, self.customer_name, vehicle_row=row, parent=self
        )
        if dlg.exec():
            self.load_vehicle_table()
            show_success(self, "Arac guncellendi.")

    def export_excel(self):
        from src.utils.toast_notification import show_info

        show_info(self, "Veriler Excel'e aktarılıyor...")

    def export_pdf(self):
        if self.tabs.currentWidget() is not self.tab_offers:
            show_error(
                self,
                "PDF'e aktarmak icin Verilen Teklifler sekmesinden bir teklif secin.",
            )
            return
        item = self._selected_offer_item()
        data = item.data(0, Qt.ItemDataRole.UserRole) if item else {}
        offer_id = (data or {}).get("offer_id")
        if not offer_id:
            show_error(self, "PDF'e aktarmak icin bir teklif secin.")
            return
        offer_no = item.text(1).strip() or f"PRF-{offer_id}"
        safe_offer_no = re.sub(r"[^A-Za-z0-9_-]+", "-", offer_no).strip("-")
        default_name = f"Teklif_{safe_offer_no or offer_id}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Teklif PDF Kaydet",
            default_name,
            "PDF Dosyalari (*.pdf)",
        )
        if not save_path:
            return

        from src.ui.utils.background_task import run_cancellable_task

        def produce_pdf(is_cancelled):
            if is_cancelled():
                return ""
            return self._generate_offer_pdf(
                offer_id,
                save_path=save_path,
                open_after=False,
            )

        def pdf_ready(generated_path):
            self.load_offer_table()
            show_success(
                self,
                f"PDF dosyasi olusturuldu: {generated_path}",
            )
            try:
                os.startfile(generated_path)
            except OSError:
                pass

        run_cancellable_task(
            owner=self,
            title="PDF olusturuluyor...",
            target=produce_pdf,
            on_success=pdf_ready,
            on_error=lambda message: show_error(
                self,
                f"PDF aktarim hatasi: {message}",
            ),
            output_path=save_path,
        )

    def _selected_history_item(self):
        current_tab = self.tabs.currentWidget()
        if current_tab is self.tab_service:
            item = self.table_service.currentItem()
        elif current_tab is self.tab_cari:
            item = self.table_cari.currentItem()
        elif current_tab is self.tab_sales:
            item = self.table_sales.currentItem()
        else:
            item = None
        while item and not item.data(0, Qt.ItemDataRole.UserRole):
            item = item.parent()
        return item

    def _customer_company_name(self):
        try:
            cur = self.db.conn.cursor()
            cur.execute(
                "SELECT COALESCE(company_name, '') FROM customers WHERE id=?",
                (self.customer_id,),
            )
            row = cur.fetchone()
            return str(row[0] or "").strip() if row else ""
        except Exception as exc:
            logger.debug(f"Customer360 company lookup skipped: {exc}")
            return ""

    def _tracking_cart_items(self, tracking_no):
        items = []
        try:
            from src.utils.service_work_details import (
                format_numbered_work_lines,
                load_service_work_lines,
            )

            cur = self.db.conn.cursor()
            cur.execute(
                """
                SELECT COALESCE(device_brand, ''), COALESCE(device_model, ''),
                       COALESCE(labor_cost, 0), COALESCE(cargo_fee, 0),
                       COALESCE(fault_description, ''), COALESCE(repair_details, '')
                FROM devices
                WHERE tracking_no=?
                LIMIT 1
                """,
                (tracking_no,),
            )
            row = cur.fetchone()
            if row:
                brand, model, labor, cargo, fault, repair = row
                label = " ".join(part for part in [brand, model] if part).strip()
                work_lines = load_service_work_lines(
                    self.db,
                    tracking_no,
                    repair_details=repair,
                    fault_description=fault,
                )
                if float(labor or 0) > 0:
                    items.append(
                        {
                            "service": f"Servis Iscilik - {label or tracking_no}",
                            "description": format_numbered_work_lines(work_lines)
                            or repair
                            or fault
                            or f"Ref: {tracking_no}",
                            "qty": 1,
                            "price": float(labor or 0),
                            "tracking_no": tracking_no,
                        }
                    )
                if float(cargo or 0) > 0:
                    items.append(
                        {
                            "service": "Kargo Ucreti",
                            "description": f"Ref: {tracking_no}",
                            "qty": 1,
                            "price": float(cargo or 0),
                        }
                    )

            cur.execute("PRAGMA table_info(used_parts)")
            cols = [col[1] for col in cur.fetchall() or []]
            has_qty = "quantity" in cols
            deleted_col = (
                "is_deleted"
                if "is_deleted" in cols
                else ("is_archived" if "is_archived" in cols else None)
            )
            query = "SELECT part_name, price, COALESCE(quantity, 1) FROM used_parts WHERE tracking_no=?"
            if not has_qty:
                query = "SELECT part_name, price, 1 FROM used_parts WHERE tracking_no=?"
            if deleted_col:
                query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
            cur.execute(query, (tracking_no,))
            for name, price, qty in cur.fetchall() or []:
                items.append(
                    {
                        "service": str(name or "Parca"),
                        "description": f"Ref: {tracking_no}",
                        "qty": int(qty or 1),
                        "price": float(price or 0),
                    }
                )
        except Exception as exc:
            logger.warning(f"Customer360 offer tracking items skipped: {exc}")
        return items

    def _description_cart_items(self, description, fallback_amount):
        lines = self._split_description_lines(description)
        item_lines = []
        for line in lines:
            clean = line.lstrip("-").lstrip(">").strip()
            if not clean or clean.lower().startswith("ref:"):
                continue
            item_lines.append(clean)
        if not item_lines:
            item_lines = ["Musteri islem kaydi"]
        amount = float(fallback_amount or 0)
        if len(item_lines) == 1:
            return [
                {
                    "service": item_lines[0],
                    "description": "Musteri 360 kaydindan olusturuldu",
                    "qty": 1,
                    "price": amount,
                }
            ]
        per_line = amount / len(item_lines) if amount else 0.0
        return [
            {
                "service": line,
                "description": "Musteri 360 kaydindan olusturuldu",
                "qty": 1,
                "price": per_line,
            }
            for line in item_lines
        ]

    def create_offer_from_selected_history(self):
        item = self._selected_history_item()
        if not item:
            show_error(self, "Teklif olusturmak icin once bir islem satiri secin.")
            return
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        if data.get("transaction_type") == "CREDIT":
            show_error(
                self,
                "Odeme/tahsilat satirindan teklif olusturulamaz. Lutfen satis veya borc satirini secin.",
            )
            return

        tracking_no = str(data.get("tracking_no") or "").strip()
        cart_items = self._tracking_cart_items(tracking_no) if tracking_no else []

        amount_try = float(data.get("try_amount") or 0)
        if amount_try <= 0:
            amount = float(data.get("amount") or 0)
            currency = str(data.get("currency") or "TRY").upper()
            rate = float(data.get("exchange_rate") or 1.0)
            amount_try = amount if currency == "TRY" else amount * rate

        if not cart_items:
            cart_items = self._description_cart_items(
                data.get("description") or item.text(1),
                amount_try,
            )

        subtotal = sum(
            float(row.get("price") or 0) * int(row.get("qty") or 1)
            for row in cart_items
        )
        if subtotal <= 0 and amount_try > 0:
            subtotal = amount_try
        from src.utils.tax_settings import TaxSettings

        vat_ratio = TaxSettings.get_ratio(self.db)
        vat_amount = subtotal * vat_ratio
        totals = (
            subtotal,
            0.0,
            vat_ratio,
            vat_amount,
            subtotal + vat_amount,
        )

        try:
            from src.ui.pages.transaction.dialogs.proforma_dialog import ProformaDialog

            company = self._customer_company_name()
            dlg = ProformaDialog(
                self,
                self.db,
                cart_items,
                totals,
                self.customer_name,
                currency_mode=CurrencyHelper.get_code(self.db),
                totals_try=totals,
                parent_currency="TRY",
                customer_id=self.customer_id,
                customer_company=company,
                initial_company=company,
                initial_project=tracking_no or "Musteri 360 Islem Teklifi",
                preferred_template="modern",
                source="customer_360",
            )
            dlg.exec()
            self.load_offer_table()
        except Exception as exc:
            logger.exception("Customer360 offer creation failed")
            show_error(self, f"Teklif olusturulamadi: {exc}")
