# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QFrame, QDialog, QFormLayout, QLineEdit,
                             QDateEdit, QDoubleSpinBox, QMessageBox, QGridLayout, QComboBox)
from PyQt6.QtCore import Qt, QDate, QSize
from PyQt6.QtGui import QFont, QColor
from src.utils.theme_colors import theme_qss
from src.utils.currency_helper import CurrencyHelper
from src.utils.exchange_rate_manager import ExchangeRateManager
from src.utils.toast_notification import show_success, show_error
from src.utils.message_helper import show_warning
from src.ui.pages.project_management.project_detail_page import ProjectDetailPage
from src.ui.widgets.modern_dialog import NoWheelScrollArea
from src.utils.language_manager import LanguageManager
from src.ui.dialogs.base_modern_dialog import BaseModernDialog


class ProjectsPage(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.lang = LanguageManager()
        self._all_projects = []
        self._current_page = 0
        self._page_size = 30
        self._total_projects = 0
        self.init_ui()
        self.lang.labels_updated.connect(self.update_texts)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QHBoxLayout()
        self.lbl_title = QLabel(self.lang.get("prj_page_title", "Proje Yönetimi"))
        self.lbl_title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        header.addWidget(self.lbl_title)
        header.addStretch()

        self.btn_new = QPushButton(self.lang.get("prj_btn_new", "➕ Yeni Proje Ekle"))
        self.btn_new.setFixedSize(160, 40)
        self.btn_new.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent; color: @selection_text;
                font-weight: bold; border-radius: 8px; font-size: 14px;
            }
            QPushButton:hover { background-color: @accent_hover; }
        """))
        self.btn_new.clicked.connect(self.open_new_project_dialog)
        header.addWidget(self.btn_new)
        layout.addLayout(header)

        # Search bar
        search_row = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Proje adı, müşteri veya referans numarasına göre ara...")
        self.txt_search.setFixedHeight(38)
        self.txt_search.setStyleSheet(theme_qss("""
            QLineEdit {
                background: @surface_alt; border: 1px solid @border;
                border-radius: 8px; padding: 0 12px; color: @text; font-size: 13px;
            }
            QLineEdit:focus { border-color: @accent; }
        """))
        self.txt_search.textChanged.connect(self._filter_projects)
        search_row.addWidget(self.txt_search)
        layout.addLayout(search_row)

        # Projects Grid
        scroll = NoWheelScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(theme_qss("QScrollArea { border: none; background: transparent; }"))

        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll)

        pager = QHBoxLayout()
        pager.addStretch()
        self.btn_prev_page = QPushButton("< \u00d6nceki")
        self.lbl_page = QLabel("Sayfa 1 / 1")
        self.lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_next_page = QPushButton("Sonraki >")
        self.btn_prev_page.clicked.connect(self._previous_page)
        self.btn_next_page.clicked.connect(self._next_page)
        pager.addWidget(self.btn_prev_page)
        pager.addWidget(self.lbl_page)
        pager.addWidget(self.btn_next_page)
        pager.addStretch()
        layout.addLayout(pager)

        self.load_projects()

    def update_texts(self):
        self.lbl_title.setText(self.lang.get("prj_page_title", "Proje Yönetimi"))
        self.btn_new.setText(self.lang.get("prj_btn_new", "➕ Yeni Proje Ekle"))

    def load_projects(self):
        search_query = self.txt_search.text().strip()
        offset = self._current_page * self._page_size
        projects, total = self.db.get_projects_paginated(
            limit=self._page_size,
            offset=offset,
            search_query=search_query,
        )
        self._all_projects = list(projects)
        self._total_projects = int(total or 0)
        max_page = max(0, (self._total_projects - 1) // self._page_size)
        if self._current_page > max_page:
            self._current_page = max_page
            return self.load_projects()
        self._render_projects(self._all_projects)
        self._update_pager()

    def _filter_projects(self, text):
        self._current_page = 0
        self.load_projects()

    def _update_pager(self):
        page_count = max(1, (self._total_projects + self._page_size - 1) // self._page_size)
        self.lbl_page.setText(
            f"Sayfa {self._current_page + 1} / {page_count}"
        )
        self.btn_prev_page.setEnabled(self._current_page > 0)
        self.btn_next_page.setEnabled(self._current_page + 1 < page_count)

    def _previous_page(self):
        if self._current_page <= 0:
            return
        self._current_page -= 1
        self.load_projects()

    def _next_page(self):
        page_count = max(1, (self._total_projects + self._page_size - 1) // self._page_size)
        if self._current_page + 1 >= page_count:
            return
        self._current_page += 1
        self.load_projects()

    def _render_projects(self, projects):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        col_count = 3
        for idx, proj in enumerate(projects):
            row = idx // col_count
            col = idx % col_count
            card = ProjectCard(proj, parent_page=self)
            self.grid_layout.addWidget(card, row, col)

    def open_new_project_dialog(self):
        dlg = NewProjectDialog(self.db, self)
        if dlg.exec():
            self.load_projects()

    def open_project_detail(self, project_id, project_name):
        detail_page = ProjectDetailPage(self.db, self.main_window, project_id, project_name)
        self.main_window.content_area.addWidget(detail_page)
        self.main_window.content_area.setCurrentWidget(detail_page)

    def confirm_delete_project(self, project_id, project_name):
        from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
        dlg = ModernConfirmDialog(
            "Projeyi Sil",
            f"'{project_name}' projesini ve tüm verilerini silmek istediğinize emin misiniz\nBu işlem geri alınamaz!",
            self,
            confirm_text="Evet, Sil",
            cancel_text="Vazgeç",
            destructive=True
        )
        if dlg.exec():
            if self.db.delete_project(project_id):
                show_success(self, "Proje silindi.")
                self.load_projects()
            else:
                show_error(self, "Proje silinirken bir hata oluştu.")

    def complete_project(self, project_id, project_name):
        from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
        dlg = ModernConfirmDialog(
            "Projeyi Tamamla",
            f"'{project_name}' projesini tamamlandı olarak işaretlemek istiyor musunuz?",
            self,
            confirm_text="Evet, Tamamlandı",
            cancel_text="Vazgeç",
        )
        if dlg.exec():
            if self.db.update_project_status(project_id, "Tamamlandı"):
                show_success(self, "Proje tamamlandı olarak işaretlendi.")
                self.load_projects()
            else:
                show_error(self, "Durum güncellenirken hata oluştu.")

    def archive_project(self, project_id, project_name):
        from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
        dlg = ModernConfirmDialog(
            "Projeyi Arşivle",
            f"'{project_name}' projesini arşive taşımak istiyor musunuz?\nArşivlenen projeler Proje Arşivi menüsünden görüntülenebilir.",
            self,
            confirm_text="Arşivle",
            cancel_text="Vazgeç",
        )
        if dlg.exec():
            if self.db.archive_project(project_id, archived=True):
                show_success(self, "Proje arşive taşındı.")
                self.load_projects()
            else:
                show_error(self, "Arşivleme sırasında hata oluştu.")


class ProjectCard(QFrame):
    def __init__(self, project_data, parent_page):
        super().__init__()
        self.project = project_data
        self.parent_page = parent_page
        self.setFixedSize(300, 210)
        status = self.project['status']
        is_done = status in ("Tamamlandı", "İptal")
        border_color = "@border" if not is_done else "@disabled_text"
        self.setStyleSheet(theme_qss(f"""
            QFrame {{
                background-color: @surface;
                border-radius: 12px;
                border: 1px solid {border_color};
            }}
            QFrame:hover {{
                border: 2px solid @accent;
            }}
        """))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(3)

        keys = self.project.keys() if hasattr(self.project, 'keys') else []

        # Header row: name + delete
        lbl_name = QLabel(self.project['name'])
        lbl_name.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_name.setStyleSheet(theme_qss("border: none; color: @text;"))
        lbl_name.setWordWrap(True)

        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(28, 28)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet(theme_qss("""
            QPushButton {
                background: transparent; color: @disabled_text;
                border: none; font-size: 15px;
            }
            QPushButton:hover { color: @danger; background: @surface_alt; border-radius: 14px; }
        """))
        btn_del.clicked.connect(self.on_delete)

        h_head = QHBoxLayout()
        h_head.addWidget(lbl_name, stretch=1)
        h_head.addWidget(btn_del)
        layout.addLayout(h_head)

        # Ref No
        ref_no = self.project['ref_no'] if 'ref_no' in keys else None
        if ref_no:
            lbl_ref = QLabel(f"🔖 {ref_no}")
            lbl_ref.setStyleSheet(theme_qss("color: @accent; font-size: 10px; font-weight: bold; border: none;"))
            layout.addWidget(lbl_ref)

        # Customer
        cust_name = self.project['customer_name'] if 'customer_name' in keys else None
        if cust_name:
            lbl_cust = QLabel(f"👤 {cust_name}")
            lbl_cust.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
            layout.addWidget(lbl_cust)

        # Budget
        budget = self.project['budget'] or 0
        cost   = self.project['cost'] if 'cost' in keys else 0
        currency = (self.project['currency'] if 'currency' in keys else 'TRY') or 'TRY'
        lbl_budget = QLabel(f"💰 {CurrencyHelper.format_original_and_try(budget, currency, db=self.parent_page.db)}")
        lbl_budget.setStyleSheet(theme_qss("color: @success; font-weight: bold; border: none; font-size: 11px;"))
        layout.addWidget(lbl_budget)
        if cost and float(cost) > 0:
            lbl_cost = QLabel(f"🔧 {CurrencyHelper.format_original_and_try(float(cost), currency, db=self.parent_page.db)} maliyet")
            lbl_cost.setStyleSheet(theme_qss("color: @warning; font-size: 10px; border: none;"))
            layout.addWidget(lbl_cost)

        # Status badge
        lbl_status = QLabel(status)
        if status == "Devam Ediyor":
            sc = "color: @warning; font-weight: bold; border: none;"
        elif status == "Tamamlandı":
            sc = "color: @success; font-weight: bold; border: none;"
        else:
            sc = "color: @disabled_text; font-weight: bold; border: none;"
        lbl_status.setStyleSheet(theme_qss(sc))
        layout.addWidget(lbl_status)

        layout.addStretch()

        # Bottom action row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        btn_open = QPushButton("Detay ➔")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent; color: @selection_text;
                border: none; border-radius: 6px; padding: 4px 8px;
                font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background-color: @accent_hover; }
        """))
        btn_open.clicked.connect(self.on_click)
        btn_row.addWidget(btn_open)

        if status == "Devam Ediyor":
            btn_done = QPushButton("✅ Tamamla")
            btn_done.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_done.setStyleSheet(theme_qss("""
                QPushButton {
                    background-color: @success; color: @selection_text;
                    border: none; border-radius: 6px; padding: 4px 8px; font-size: 11px;
                }
                QPushButton:hover { opacity: 0.85; }
            """))
            btn_done.clicked.connect(self.on_complete)
            btn_row.addWidget(btn_done)

        btn_arch = QPushButton("📦")
        btn_arch.setFixedSize(28, 28)
        btn_arch.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_arch.setToolTip("Arşive Taşı")
        btn_arch.setStyleSheet(theme_qss("""
            QPushButton {
                background: @surface_alt; color: @text_muted;
                border: 1px solid @border; border-radius: 6px; font-size: 13px;
            }
            QPushButton:hover { background: @border; color: @text; }
        """))
        btn_arch.clicked.connect(self.on_archive)
        btn_row.addWidget(btn_arch)

        layout.addLayout(btn_row)

    def on_click(self):
        self.parent_page.open_project_detail(self.project['id'], self.project['name'])

    def on_delete(self):
        self.parent_page.confirm_delete_project(self.project['id'], self.project['name'])

    def on_complete(self):
        self.parent_page.complete_project(self.project['id'], self.project['name'])

    def on_archive(self):
        self.parent_page.archive_project(self.project['id'], self.project['name'])

    def mousePressEvent(self, event):
        self.on_click()


class NewProjectDialog(BaseModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)

    def __init__(self, db, parent=None):
        super().__init__(parent, title="🏗️ Yeni Proje Oluştur", width=480, height=700)
        self.db = db
        self._customer_id   = None
        self._customer_name = None
        self._contract_path = None
        self.setup_ui()

        self._wire_ui_signals()
    def setup_ui(self):
        from src.utils.design_system import DesignTokens

        def _spin():
            s = QDoubleSpinBox()
            s.setRange(0, 1_000_000_000)
            s.setSuffix(f" {CurrencyHelper.get_label(db=self.db)}")
            s.setDecimals(2)
            s.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
            s.setFixedHeight(38)
            return s

        def _inp(ph=""):
            i = QLineEdit()
            i.setPlaceholderText(ph)
            i.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
            i.setFixedHeight(38)
            return i

        def _date():
            d = QDateEdit()
            d.setCalendarPopup(True)
            d.setStyleSheet(theme_qss(
                DesignTokens.get_input_qss() + """
                QDateEdit::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 26px;
                    border-left: 1px solid @border;
                    background: @surface;
                    border-top-right-radius: 6px;
                    border-bottom-right-radius: 6px;
                }
                """
            ))
            d.setFixedHeight(38)
            return d

        def _lbl(txt):
            l = QLabel(txt)
            l.setStyleSheet(theme_qss("color: @text_muted; font-weight: bold; font-size: 11px;"))
            return l

        layout = self.content_layout
        layout.setSpacing(8)

        layout.addWidget(_lbl("Proje Adı *"))
        self.txt_name = _inp("Örn. Villa A - Akıllı Ev Kurulumu")
        layout.addWidget(self.txt_name)

        layout.addWidget(_lbl("👤 İlgili Müşteri"))
        cust_row = QHBoxLayout()
        cust_row.setSpacing(6)

        self._customer_frame = QFrame()
        self._customer_frame.setStyleSheet(theme_qss(
            "QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 6px; }"
        ))
        self._customer_frame.setFixedHeight(38)
        _cf_layout = QHBoxLayout(self._customer_frame)
        _cf_layout.setContentsMargins(10, 0, 10, 0)

        self.lbl_customer = QLabel("— Müşteri seçilmedi —")
        self.lbl_customer.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; border: none; background: transparent;"))
        _cf_layout.addWidget(self.lbl_customer)

        cust_row.addWidget(self._customer_frame, stretch=1)

        btn_pick_cust = QPushButton("🔍 Seç")
        btn_pick_cust.setFixedHeight(38)
        btn_pick_cust.setStyleSheet(theme_qss(
            "QPushButton { background: @accent; color: @selection_text; border-radius: 6px; padding: 0 12px; font-weight: bold; }"
            "QPushButton:hover { background: @accent_hover; }"
        ))
        btn_pick_cust.clicked.connect(self._pick_customer)
        cust_row.addWidget(btn_pick_cust)

        self.btn_clear_cust = QPushButton("✕")
        self.btn_clear_cust.setFixedSize(38, 38)
        self.btn_clear_cust.setVisible(False)
        self.btn_clear_cust.setStyleSheet(theme_qss(
            "QPushButton { background: @danger; color: @selection_text; border-radius: 6px; font-weight: bold; }"
        ))
        self.btn_clear_cust.clicked.connect(self._clear_customer)
        cust_row.addWidget(self.btn_clear_cust)
        layout.addLayout(cust_row)

        date_row = QHBoxLayout()
        date_row.setSpacing(10)
        left_col = QVBoxLayout()
        left_col.addWidget(_lbl("Başlangıç"))
        self.date_start = _date()
        self.date_start.setDate(QDate.currentDate())
        left_col.addWidget(self.date_start)
        right_col = QVBoxLayout()
        right_col.addWidget(_lbl("Bitiş (Tahmini)"))
        self.date_end = _date()
        self.date_end.setDate(QDate.currentDate().addYears(1))
        right_col.addWidget(self.date_end)
        date_row.addLayout(left_col)
        date_row.addLayout(right_col)
        layout.addLayout(date_row)

        # Para Birimi + Kur
        cur_row = QHBoxLayout()
        cur_row.setSpacing(8)
        cur_left = QVBoxLayout()
        cur_left.addWidget(_lbl("💱 Para Birimi"))
        self.cmb_currency = QComboBox()
        self.cmb_currency.addItems([
            "TRY  ₺ (Türk Lirası)",
            "USD  $ (Dolar)",
            "EUR  € (Euro)",
            "GBP  £ (Sterlin)",
            "AED  د.إ (Dirhem)",
            "CAD  C$ (Kanada Doları)",
            "CHF  Fr (İsviçre Frangı)",
            "JPY  ¥ (Japon Yeni)",
        ])
        self.cmb_currency.setStyleSheet(theme_qss(
            DesignTokens.get_input_qss() + """
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                border-left: 1px solid @border;
                background: @surface;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox QAbstractItemView {
                background: @surface;
                color: @text;
                selection-background-color: @selection_bg;
                selection-color: @selection_text;
                border: 1px solid @border;
            }
            """
        ))
        self.cmb_currency.setFixedHeight(38)
        self.cmb_currency.currentIndexChanged.connect(self._on_currency_changed)
        cur_left.addWidget(self.cmb_currency)
        cur_row.addLayout(cur_left)

        cur_right = QVBoxLayout()
        self._lbl_rate = _lbl(f"Kur (1 yab. = ? {CurrencyHelper.get_label(db=self.db)})")
        cur_right.addWidget(self._lbl_rate)
        self.spin_rate = QDoubleSpinBox()
        self.spin_rate.setRange(0.0001, 99999.9999)
        self.spin_rate.setDecimals(4)
        self.spin_rate.setValue(1.0)
        self.spin_rate.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.spin_rate.setFixedHeight(38)
        cur_right.addWidget(self.spin_rate)
        cur_row.addLayout(cur_right)

        self._cur_right_widget = cur_right
        self._lbl_rate.setVisible(False)
        self.spin_rate.setVisible(False)
        layout.addLayout(cur_row)

        layout.addWidget(_lbl("💰 Toplam Bütçe (Müşteriden alınacak)"))
        self.spin_budget = _spin()
        layout.addWidget(self.spin_budget)

        layout.addWidget(_lbl("🔧 Maliyet (Bize maliyeti)"))
        self.spin_cost = _spin()
        layout.addWidget(self.spin_cost)

        layout.addWidget(_lbl("💳 Ödeme Şekli"))
        self.cmb_payment = QComboBox()
        self.cmb_payment.addItems([
            "Peşin",
            "Borçlu / Vadeli",
            "Kısmi Peşin + Vade",
            "Havale / EFT",
            "Çek",
            "Kredi Kartı",
            "Diğer",
        ])
        self.cmb_payment.setStyleSheet(theme_qss(
            DesignTokens.get_input_qss() + """
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                border-left: 1px solid @border;
                background: @surface;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox QAbstractItemView {
                background: @surface;
                color: @text;
                selection-background-color: @selection_bg;
                selection-color: @selection_text;
                border: 1px solid @border;
            }
            """
        ))
        self.cmb_payment.setFixedHeight(38)
        layout.addWidget(self.cmb_payment)

        layout.addWidget(_lbl("Açıklama"))
        self.txt_desc = _inp("Proje açıklaması, özel notlar...")
        layout.addWidget(self.txt_desc)

        # ── Sözleşme Ekle (PDF) ──────────────────────────────────
        layout.addSpacing(10)
        lbl_contract = QLabel("📜 Sözleşme Ekle (PDF)")
        lbl_contract.setStyleSheet(theme_qss("color: @text; font-weight: bold; font-size: 13px;"))
        layout.addWidget(lbl_contract)

        contract_layout = QHBoxLayout()
        self.lbl_contract_file = QLabel("Seçilmedi")
        self.lbl_contract_file.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; border: 1px solid @border; border-radius: 5px; padding: 5px;"))
        
        btn_browse_contract = QPushButton("Gözat...")
        btn_browse_contract.setFixedWidth(80)
        btn_browse_contract.setFixedHeight(32)
        btn_browse_contract.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline")))
        btn_browse_contract.clicked.connect(self._browse_contract)

        contract_layout.addWidget(self.lbl_contract_file, stretch=1)
        contract_layout.addWidget(btn_browse_contract)
        layout.addLayout(contract_layout)

        btn_box = self.footer_layout
        btn_cancel = QPushButton("❌ İptal")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(theme_qss(
            "background-color: @disabled_text; color: @selection_text; border-radius: 8px; padding: 10px 20px; font-weight: bold;"
        ))
        btn_save = QPushButton("✨ Oluştur")
        btn_save.clicked.connect(self.save)
        btn_save.setStyleSheet(theme_qss(
            "background-color: @success; color: @selection_text; border-radius: 8px; padding: 10px 24px; font-weight: bold; font-size: 13px;"
        ))
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        self._on_currency_changed()

    def _wire_ui_signals(self):
        self.cmb_payment.currentIndexChanged.connect(self._on_ui_widget_changed)

    def _get_selected_currency_code(self):
        text = self.cmb_currency.currentText().strip()
        return text.split()[0] if text else "TRY"

    def _on_currency_changed(self):
        code = self._get_selected_currency_code()
        base_label = CurrencyHelper.get_label(db=self.db)
        symbol_map = {
            "TRY": "₺",
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "AED": "د.إ",
            "CAD": "C$",
            "CHF": "Fr",
            "JPY": "¥",
        }
        symbol = symbol_map.get(code, code)

        for spin in (self.spin_budget, self.spin_cost):
            spin.setSuffix(f" {symbol}")

        is_try = code == "TRY"
        self._lbl_rate.setVisible(not is_try)
        self.spin_rate.setVisible(not is_try)
        self._lbl_rate.setText(f"Kur (1 {code} = ? {base_label})")
        if is_try:
            self.spin_rate.setValue(1.0)
        else:
            try:
                rate = float(ExchangeRateManager.get_current_rate(self.db, code, "selling") or 1.0)
                self.spin_rate.setValue(rate if rate > 0 else 1.0)
            except Exception:
                self.spin_rate.setValue(1.0)

    def _pick_customer(self):
        from src.ui.dialogs.customer_select_dialog import CustomerSelectDialog
        dlg = CustomerSelectDialog(self.db, self)
        if dlg.exec() and dlg.selected_customer:
            c = dlg.selected_customer
            try:
                self._customer_id   = c[0]
                self._customer_name = c[1]
            except (IndexError, TypeError, KeyError):
                self._customer_id   = c['id']
                self._customer_name = c['name']
            self.lbl_customer.setText(f"👤  {self._customer_name}")
            self.lbl_customer.setStyleSheet(theme_qss(
                "color: @text; font-size: 12px; font-weight: bold; border: none; background: transparent;"
            ))
            self.btn_clear_cust.setVisible(True)

    def _clear_customer(self):
        self._customer_id   = None
        self._customer_name = None
        self.lbl_customer.setText("— Müşteri seçilmedi —")
        self.lbl_customer.setStyleSheet(theme_qss(
            "color: @text_muted; font-size: 12px; border: none; background: transparent;"
        ))
        self.btn_clear_cust.setVisible(False)

    def _browse_contract(self):
        from PyQt6.QtWidgets import QFileDialog
        import os
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Sözleşme PDF Seçin", "", "PDF Dosyaları (*.pdf)"
        )
        if file_path:
            self._contract_path = file_path
            self.lbl_contract_file.setText(os.path.basename(file_path))

    def save(self):
        if not self.txt_name.text().strip():
            show_warning(self, "Hata", "Proje adı zorunludur.")
            return

        data = {
            'name':           self.txt_name.text().strip(),
            'start_date':     self.date_start.date().toString("yyyy-MM-dd"),
            'end_date':       self.date_end.date().toString("yyyy-MM-dd"),
            'budget':         self.spin_budget.value(),
            'cost':           self.spin_cost.value(),
            'currency':       self._get_selected_currency_code(),
            'exchange_rate':  self.spin_rate.value() if self._get_selected_currency_code() != 'TRY' else 1.0,
            'payment_method': self.cmb_payment.currentText(),
            'description':    self.txt_desc.text().strip(),
            'customer_id':    self._customer_id,
            'customer_name':  self._customer_name,
        }

        # Sözleşme PDF'ini kopyala
        import os, shutil, time
        if self._contract_path and os.path.exists(self._contract_path):
            try:
                # data/contracts dizinini oluştur
                contracts_dir = os.path.join(os.getcwd(), "data", "contracts")
                if not os.path.exists(contracts_dir):
                    os.makedirs(contracts_dir, exist_ok=True)
                
                # Benzersiz dosya adı oluştur
                ext = os.path.splitext(self._contract_path)[1]
                target_filename = f"contract_{int(time.time())}{ext}"
                target_path = os.path.join(contracts_dir, target_filename)
                
                # Kopyala
                shutil.copy2(self._contract_path, target_path)
                
                # DB'ye göreceli yolu kaydet
                data['contract_path'] = os.path.join("data", "contracts", target_filename).replace("\\", "/")
            except Exception as e:
                from src.utils.logger import logger
                logger.error(f"Error copying contract file: {e}")

        if self.db.add_project(data):
            msg = "Proje oluşturuldu ve finansa kaydedildi."
            if self._customer_name:
                pmethod = self.cmb_payment.currentText()
                _instant = {'Peşin', 'Havale / EFT', 'Kredi Kartı'}
                if pmethod in _instant:
                    msg = f"Proje oluşturuldu. {self._customer_name} cari hesabına tahsilat kaydedildi."
                else:
                    msg = f"Proje oluşturuldu. {self._customer_name} cari hesabına borç olarak eklendi."
            if self._customer_name:
                msg = (
                    f"Proje olu\u015fturuldu. {self._customer_name} cari "
                    "hesab\u0131na bor\u00e7 olarak eklendi."
                )
            main_window = getattr(self.parent(), "main_window", None)
            signal = getattr(main_window, "financial_data_changed", None)
            if signal is not None:
                try:
                    signal.emit()
                except Exception:
                    pass
            show_success(self.parent(), msg)
            self.accept()
        else:
            show_error(self.parent(), "Proje oluşturulurken hata oluştu.")
