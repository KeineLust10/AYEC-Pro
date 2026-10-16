# -*- coding: utf-8 -*-
# stock_page.py - Ana stok yönetimi sayfası (modülerleştirilmiş)

import os

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QFrame,
    QLabel,
    QPushButton,
)
from PyQt6.QtCore import Qt, QTimer
from src.utils.theme_colors import theme_qss, tc
from src.utils.currency_helper import CurrencyHelper
from src.utils.logger import logger
from src.utils.system_config import SystemConfig
from src.utils.page_ids import PageIds
from src.ui.widgets.loading_overlay import LoadingOverlay
from src.ui.widgets.empty_state import EmptyState
from src.ui.dialogs.add_stock_dialog import AddStockDialog
from ._stock_widgets import StockStatCard
from ._stock_workers import StockWorker, HistoryWorker, ParseWorker
from ._stock_mixins import StockPageConstantsMixin, StockPageUtilitiesMixin
from ._stock_list_tab import StockListTabMixin
from ._stock_history_tab import StockHistoryTabMixin
from ._stock_export import StockExportMixin
from ._stock_import import StockImportMixin
from ._stock_context_menus import StockContextMenusMixin


class StockPage(
    StockPageConstantsMixin,
    StockPageUtilitiesMixin,
    StockListTabMixin,
    StockHistoryTabMixin,
    StockExportMixin,
    StockImportMixin,
    StockContextMenusMixin,
    QWidget,
):
    def __init__(self, db, main_window=None, sector_manager=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.sector_manager = sector_manager
        self.is_automotive = self._detect_automotive_mode()

        # State
        self.current_page = 0
        self.page_limit = 50
        self.total_count = 0
        self.history_current_page = 0
        self.history_page_limit = 100
        self.history_total_count = 0
        self.selected_category = "Tümü"
        self._raw_categories = []
        self.search_query = ""
        self.critical_filter = False
        self.metric_filter = "all"
        self.worker = None
        self._reload_pending = False

        # Worker references
        self.history_worker = None
        self.parse_worker = None

        # Search debounce timer
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.reload_data)

        # Loading overlay
        try:
            _firm = self.db.get_setting("company_name", "") or "AYEC Pro"
            _logo = self.db.get_setting("logo_path", "")
        except Exception:
            _firm = "AYEC Pro"
            _logo = ""
        self._loading_overlay = LoadingOverlay(self, text="Dosya analiz ediliyor...",
                                               firm_name=_firm)
        if _logo:
            self._loading_overlay.set_company_logo(_logo)

        self.init_ui()

        # Delayed DB setup
        QTimer.singleShot(50, self._delayed_db_setup)

    def _detect_automotive_mode(self):
        try:
            if self.sector_manager and self.sector_manager.get_current_plugin():
                return self.sector_manager.get_current_plugin().sector_id == "otomotiv"
        except Exception:
            pass
        try:
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def _delayed_db_setup(self):
        self.load_stock_list()

    def _on_tab_changed(self, index):
        if index == 1 and not (self.history_worker and self.history_worker.isRunning()):
            self.load_history()

    def request_reload(self):
        self.is_automotive = self._detect_automotive_mode()
        self.refresh_data()

    def showEvent(self, event):
        super().showEvent(event)
        self.is_automotive = self._detect_automotive_mode()

    def init_ui(self):
        self.setStyleSheet(theme_qss("background-color: @surface_alt;"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 8, 8)
        layout.setSpacing(10)

        self._setup_hero(layout)

        header = QFrame()
        header.setFixedHeight(76)
        header.setStyleSheet(theme_qss("QFrame { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 8px; }"))
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)
        title_block = QVBoxLayout()
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title = QLabel("Stok & Envanter Takibi")
        title.setStyleSheet(theme_qss("color: @finance_text; font-size: 18px; font-weight: 800; border: none;"))
        title_row.addWidget(title)
        self.lbl_active_stock = QLabel("0 Kalem Aktif")
        self.lbl_active_stock.setStyleSheet(theme_qss("color: @finance_primary; background: @finance_surface_high; border: 1px solid @finance_outline; border-radius: 12px; padding: 4px 10px; font-size: 11px; font-weight: 700;"))
        title_row.addWidget(self.lbl_active_stock)
        title_row.addStretch()
        title_block.addLayout(title_row)
        subtitle = QLabel("\u00dcr\u00fcn ve par\u00e7a stoklar\u0131n\u0131, kategori da\u011f\u0131l\u0131m\u0131n\u0131, kritik seviyeleri ve anl\u0131k k\u00e2rl\u0131l\u0131k marjlar\u0131n\u0131 takip edin.")
        subtitle.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 11px; border: none;"))
        title_block.addWidget(subtitle)
        header_layout.addLayout(title_block, 1)
        btn_refresh = QPushButton("Envanteri Yenile")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(theme_qss("QPushButton { background: @finance_primary; color: @selection_text; border-radius: 6px; padding: 6px 12px; font-weight: 700; } QPushButton:hover { background: @accent_hover; }"))
        btn_refresh.clicked.connect(self.refresh_data)
        header_layout.addWidget(btn_refresh)
        btn_add_header = QPushButton("+ Yeni \u00dcr\u00fcn Ekle")
        btn_add_header.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_header.setStyleSheet(theme_qss("QPushButton { background: @finance_primary; color: @selection_text; border-radius: 6px; padding: 6px 12px; font-weight: 700; } QPushButton:hover { background: @accent_hover; }"))
        btn_add_header.clicked.connect(lambda: self.open_add_stock_dialog(None))
        header_layout.addWidget(btn_add_header)
        layout.addWidget(header)

        # Stats area
        self.stats_layout = QHBoxLayout()
        self.stats_layout.setSpacing(8)
        layout.addLayout(self.stats_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.tab_list = QWidget()
        self.setup_list_tab()
        self.tab_history = QWidget()
        self.setup_history_tab()
        self.tabs.addTab(self.tab_list, "📦 Stok Durumu")
        self.tabs.addTab(self.tab_history, "📋 Stok Hareketleri")
        self.tab_transfers = QWidget()
        transfer_layout = QVBoxLayout(self.tab_transfers)
        transfer_layout.setContentsMargins(18, 18, 18, 18)
        transfer_layout.setSpacing(12)
        transfer_title = QLabel("Depo Transferleri")
        transfer_title.setStyleSheet(theme_qss(
            "color: @finance_text; font-size: 16px; font-weight: 800; border: none;"
        ))
        transfer_description = QLabel(
            "Depolar, servis ara\u00e7lar\u0131 ve konsinye noktalar\u0131 aras\u0131ndaki stok hareketlerini y\u00f6netin."
        )
        transfer_description.setWordWrap(True)
        transfer_description.setStyleSheet(theme_qss(
            "color: @finance_text_muted; font-size: 12px; border: none;"
        ))
        transfer_open = QPushButton("Depo Transferlerini A\u00e7")
        transfer_open.setCursor(Qt.CursorShape.PointingHandCursor)
        transfer_open.setStyleSheet(theme_qss(
            "QPushButton { background: @finance_primary; color: @finance_primary_text; "
            "border: none; border-radius: 4px; padding: 8px 14px; font-weight: 700; }"
        ))
        transfer_open.clicked.connect(
            lambda: self.main_window.on_menu_click(PageIds.STOCK_LOCATIONS)
            if self.main_window and hasattr(self.main_window, "on_menu_click") else None
        )
        transfer_layout.addWidget(transfer_title)
        transfer_layout.addWidget(transfer_description)
        transfer_layout.addWidget(transfer_open, 0, Qt.AlignmentFlag.AlignLeft)
        transfer_layout.addStretch(1)
        self.tabs.addTab(self.tab_transfers, "Depo Transferleri")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Usage guide tab
        if SystemConfig.is_feature_active(self.db, "usage_guides"):
            self.tab_guide = QWidget()
            self.setup_usage_guide_tab()
            self.tabs.addTab(self.tab_guide, "❓ Nasıl Kullanılır?")

        layout.addWidget(self.tabs)
        summary = QHBoxLayout()
        summary.setSpacing(10)
        for title_text, body_text, accent, page_id in (
            ("Son Fiziksel Depo Sayimi", "Sayim detaylarini ac", "@finance_primary", PageIds.STOCK_LOCATIONS),
            ("Santiye / Servis Konsinye Cikisi", "Konsinye islemlerini ac", "@finance_secondary", PageIds.CONSIGNMENT),
            ("Muhasebe Entegrasyonu", "Entegrasyon durumunu ac", "@finance_tertiary", PageIds.INCOME_EXPENSE),
        ):
            card = QPushButton()
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setMinimumHeight(30)
            card.clicked.connect(
                lambda _checked=False, target=page_id: self.main_window.on_menu_click(target)
                if self.main_window and hasattr(self.main_window, "on_menu_click") else None
            )
            card.setStyleSheet(theme_qss(
                f"QPushButton {{ text-align: left; background: @finance_surface; border: 1px solid @finance_outline; "
                f"border-left: 2px solid {accent}; border-radius: 5px; }}"
                f"QPushButton:hover {{ background: @finance_surface_alt; }}"
            ))
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(8, 4, 8, 4)
            card_layout.setSpacing(6)
            heading = QLabel(title_text)
            heading.setStyleSheet(theme_qss("color: @finance_text; font-size: 9px; font-weight: 800; border: none;"))
            heading.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            detail = QLabel(body_text)
            detail.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 9px; border: none;"))
            detail.setWordWrap(False)
            detail.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            card_layout.addWidget(heading)
            card_layout.addWidget(detail)
            summary.addWidget(card, 1)
        layout.addLayout(summary)
        self._normalize_ui_texts()

    def _setup_hero(self, parent_layout):
        # Hidden hero panel, kept for sector-specific text normalization code
        from PyQt6.QtWidgets import QLabel
        self.hero_title = QLabel()
        self.hero_subtitle = QLabel()
        self.hero_badge = QLabel()

    def _normalize_ui_texts(self):
        if self.is_automotive:
            self.tabs.setTabText(0, "Yedek Parca Durumu")
            self.tabs.setTabText(1, "Parca Hareketleri")
        else:
            self.tabs.setTabText(0, "Stok Durumu")
            self.tabs.setTabText(1, "Stok Hareketleri")
        if hasattr(self, "tab_guide"):
            self.tabs.setTabText(
                self.tabs.indexOf(self.tab_guide), "❓ Nasıl Kullanılır?"
            )

    def load_stock_list(self):
        self.reload_data()

    def reload_data(self):
        if self.worker and self.worker.isRunning():
            # Coalesce refresh requests instead of terminating a live DB task.
            self._reload_pending = True
            return

        self.stock_content_stack.setCurrentWidget(self.loading_label)
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)

        self.worker = StockWorker(
            self.db,
            self.page_limit,
            self.current_page * self.page_limit,
            self.search_query,
            self._get_category_filters(self.selected_category),
            self.critical_filter,
            self.metric_filter,
        )
        self.worker.finished.connect(self.on_data_loaded)
        self.worker.error.connect(lambda e: show_error(self, f"Hata: {e}"))
        if (
            getattr(self.db, "_db_name", "") == ":memory:"
            or os.environ.get("AYECPRO_SAFE_UI") == "1"
            or os.environ.get("QT_QPA_PLATFORM") == "offscreen"
        ):
            self.worker.run()
        else:
            self.worker.start()

    def on_data_loaded(self, parts, total_count, stats):
        self.total_count = total_count
        self.lbl_active_stock.setText(f"{int(total_count)} Kalem Aktif")
        self._update_stats_ui(stats)

        if self.cat_layout.count() <= 1:
            self._load_categories_fresh()

        if not parts:
            self.stock_content_stack.setCurrentWidget(self.stock_empty_state)
        else:
            self.stock_content_stack.setCurrentWidget(self.table_stock)
            self._fill_table(parts)

        self._update_pagination_controls()
        if self._reload_pending:
            self._reload_pending = False
            QTimer.singleShot(0, self.reload_data)

    def _update_stats_ui(self, stats):
        while self.stats_layout.count():
            w = self.stats_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        display_currency = stats.get("display_currency") or CurrencyHelper.get_code(
            self.db
        )
        display_value = CurrencyHelper.format_amount(
            stats.get("total_value", 0), db=self.db, currency_code=display_currency
        )
        try_value = CurrencyHelper.format_amount(
            stats.get("total_value_try", 0), db=self.db, currency_code="TRY"
        )
        potential_profit = CurrencyHelper.format_amount(
            stats.get("potential_profit_try", 0),
            db=self.db,
            currency_code="TRY",
        )
        value_text = (
            display_value
            if display_currency == "TRY"
            else f"{display_value} | {try_value}"
        )

        cards = [
            ("Toplam \u00dcr\u00fcn \u00c7e\u015fidi", stats.get("total_types", 0), "\U0001f4e6", tc("accent"), "all"),
            (f"Toplam Stok De\u011feri (Maliyet)", value_text, "\U0001f4b0", tc("success"), "value"),
            ("Kritik Stok Uyar\u0131s\u0131", stats.get("critical_count", 0), "\u26a0\ufe0f", tc("danger"), "critical"),
            ("Potansiyel Net K\u00e2r / Kazan\u00e7", potential_profit, "P", tc("warning"), "profit"),
        ]
        variants = {
            'all': ('finance_text', 'inventory'),
            'value': ('finance_secondary', 'wallet'),
            'critical': (
                'finance_text' if not stats.get('critical_count') else 'finance_expense',
                'collection' if not stats.get('critical_count') else 'warning',
            ),
            'profit': ('finance_primary', 'tax'),
        }
        for title, value, icon, color, metric in cards:
            token, glyph = variants[metric]
            card = StockStatCard(title, value, icon, color, token=token, glyph=glyph)
            card.clicked.connect(lambda metric=metric: self.toggle_metric_filter(metric))
            self.stats_layout.addWidget(card, 1)

    def load_history(self):
        if self.history_worker and self.history_worker.isRunning():
            return
        self.history_worker = HistoryWorker(
            self.db,
            limit=self.history_page_limit,
            offset=self.history_current_page * self.history_page_limit,
        )
        self.history_worker.finished.connect(self._on_history_loaded)
        self.history_worker.error.connect(
            lambda e: logger.error(f"StockPage history load error: {e}")
        )
        if (
            getattr(self.db, "_db_name", "") == ":memory:"
            or os.environ.get("AYECPRO_SAFE_UI") == "1"
            or os.environ.get("QT_QPA_PLATFORM") == "offscreen"
        ):
            self.history_worker.run()
        else:
            self.history_worker.start()

    def refresh_data(self):
        self.load_stock_list()
        if self.tabs.currentIndex() == 1:
            self.load_history()

    def on_stock_search_changed(self, text):
        self.search_query = str(text or "").strip()
        self.search_timer.stop()
        self.search_timer.start(300)

    def toggle_critical_filter(self, checked):
        self.critical_filter = bool(checked)
        self.metric_filter = "critical" if self.critical_filter else "all"
        self.current_page = 0
        self.reload_data()

    def toggle_metric_filter(self, metric):
        self.metric_filter = "all" if self.metric_filter == metric else metric
        self.critical_filter = self.metric_filter == "critical"
        if hasattr(self, "btn_critical"):
            self.btn_critical.setChecked(self.critical_filter)
        self.current_page = 0
        self.reload_data()



    def on_stock_double_click(self, item):
        if not item:
            return
        item_id = self._stock_part_id_from_row(item.row())
        if item_id:
            self.open_add_stock_dialog(item_id)

    def open_add_stock_dialog(self, item_id=None):
        if item_id is False or str(item_id).lower() == "false":
            item_id = None

        try:
            if AddStockDialog(
                self.db, self, item_id, sector_manager=self.sector_manager
            ).exec():
                self.refresh_data()
        except Exception as e:
            logger.error(f"AddStockDialog open error: {e}", exc_info=True)
            show_error(self, f"Yeni ürün ekleme penceresi açılamadı: {e}")

    def setup_usage_guide_tab(self):
        from PyQt6.QtWidgets import QVBoxLayout, QTextBrowser
        from src.utils.design_system import DesignTokens

        ly = QVBoxLayout(self.tab_guide)
        ly.setContentsMargins(0, 10, 0, 0)

        guide_text = QTextBrowser()
        guide_text.setStyleSheet(
            theme_qss(
                "border: none; background: transparent; color: @text; padding: 20px;"
            )
        )

        if self.is_automotive:
            html_content = f"""
        <div style="font-family: {DesignTokens.FONT_FAMILY}; color: @text;">
            <h1 style="color: @accent;">🔩 Yedek Parça Yönetimi Kullanım Kılavuzu</h1>
            <p>Bu modül, otomotiv yedek parçalarının stok takibini, OEM/muadil kodlarını, uyumlu araç bilgilerini ve tedarikçi kayıtlarını yönetir.</p>

            <h2 style="color: @primary;">1. Yedek Parça Durumu Sekmesi</h2>
            <ul>
                <li><b>Parça Listesi:</b> OEM kodu, muadil kodu, uyumlu araç, raf/konum ve fiyat bilgisiyle tüm parçaları listeler.</li>
                <li><b>Kritik Parçalar:</b> Belirlediğiniz limitin altına düşen parçalar sarı/kırmızı uyarı ile işaretlenir.</li>
                <li><b>Yeni Parça:</b> Sağ üstteki butonu kullanarak yeni yedek parça tanımlayabilirsiniz.</li>
            </ul>

            <h2 style="color: @primary;">2. Parça Hareketleri Sekmesi</h2>
            <ul>
                <li><b>Geçmiş:</b> Tüm giriş ve çıkış işlemleri tarih sırasına göre listelenir.</li>
                <li><b>İşlem Türü:</b> Satın alma, servis tüketimi ve manuel düzeltmeler ayrı ayrı izlenir.</li>
            </ul>

            <h2 style="color: @primary;">3. İpuçları ve Kısayollar</h2>
            <p>💡 <b>Hızlı Arama:</b> Parça adı, OEM kodu veya stok kodu ile arama yapabilirsiniz.</p>
            <p>💡 <b>Düzenleme:</b> Parçaya çift tıklayarak bilgilerini güncelleyebilir veya sağ tıklayarak stok ekleyip çıkarabilirsiniz.</p>
            <p>💡 <b>İçe Aktarma:</b> Excel, CSV veya fotoğraftan akıllı tanıma ile toplu parça girebilirsiniz.</p>

            <hr style="border: 0; border-top: 1px solid @border; margin: 20px 0;">
            <p style="color: @text_muted; font-style: italic;">AYEC Pro Otomotiv Yönetimi - Yedek Parça Modülü</p>
        </div>
        """
        else:
            html_content = f"""
        <div style="font-family: {DesignTokens.FONT_FAMILY}; color: @text;">
            <h1 style="color: @accent;">📦 Stok ve Envanter Yönetimi Kullanım Kılavuzu</h1>
            <p>Bu modül, parçaların, ürünlerin ve aksesuarların miktar takibini, maliyet analizini ve kritik stok uyarılarını yönetir.</p>

            <h2 style="color: @primary;">1. Stok Durumu Sekmesi</h2>
            <ul>
                <li><b>Ürün Listesi:</b> Mevcut stoklarınızı barkod, alış/satış fiyatı ve miktar bilgisiyle listeler.</li>
                <li><b>Kritik Stok:</b> Belirlediğiniz limitin altına düşen ürünler uyarı verir.</li>
                <li><b>Yeni Ürün:</b> Sağ üstteki butonu kullanarak yeni bir ürün veya parça tanımlayabilirsiniz.</li>
            </ul>

            <h2 style="color: @primary;">2. Stok Hareketleri Sekmesi</h2>
            <ul>
                <li><b>Geçmiş:</b> Tüm giriş ve çıkış işlemleri burada tarih sırasına göre listelenir.</li>
                <li><b>İşlem Türü:</b> Giriş, çıkış ve servis tüketimleri ayrı ayrı izlenir.</li>
            </ul>

            <h2 style="color: @primary;">3. İpuçları ve Kısayollar</h2>
            <p>💡 <b>Hızlı Arama:</b> Arama çubuğuna barkod okutarak veya isim yazarak ürüne hızlıca ulaşabilirsiniz.</p>
            <p>💡 <b>Düzenleme:</b> Ürüne çift tıklayarak bilgilerini güncelleyebilir veya sağ tıklayarak miktar ekleyip çıkarabilirsiniz.</p>

            <hr style="border: 0; border-top: 1px solid @border; margin: 20px 0;">
            <p style="color: @text_muted; font-style: italic;">AYEC Pro Teknik Servis Yönetimi - Envanter Gücü</p>
        </div>
        """
        final_html = (
            html_content.replace("@text_muted", tc("text_muted"))
            .replace("@text", tc("text"))
            .replace("@accent", tc("accent"))
            .replace("@primary", tc("primary"))
            .replace("@border", tc("border"))
        )

        guide_text.setHtml(final_html)
        ly.addWidget(guide_text)

    def _update_pagination_controls(self):
        import math
        total_pages = max(1, math.ceil(self.total_count / self.page_limit))
        self.lbl_page_info.setText(f"Sayfa {self.current_page + 1} / {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled((self.current_page + 1) * self.page_limit < self.total_count)

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.reload_data()

    def next_page(self):
        if (self.current_page + 1) * self.page_limit < self.total_count:
            self.current_page += 1
            self.reload_data()



# Import after class definition to avoid circular import
from src.utils.toast_notification import show_error
