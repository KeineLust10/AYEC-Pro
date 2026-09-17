# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QTabWidget, QVBoxLayout
from PyQt6.QtCore import QTimer
import logging

from src.utils.logger import logger
from src.utils.theme_colors import theme_qss
from src.utils.system_config import SystemConfig

# Import Mixins
from ._customers_base_mixin import CustomersBaseMixin
from ._customers_data_mixin import CustomersDataMixin
from ._customers_ui_mixin import CustomersUIMixin
from ._customers_func_mixin import CustomersFuncMixin

class CustomersPage(QWidget, CustomersBaseMixin, CustomersDataMixin, CustomersUIMixin, CustomersFuncMixin):
    """
    AYEC Pro M\u00fc\u015fteri ve Cari Y\u00f6netimi Sayfas\u0131.
    Mixin yap\u0131land\u0131rmas\u0131 ile mod\u00fcler hale getirilmi\u015ftir.
    """

    @staticmethod
    def _looks_like_partner_row(data):
        try:
            keys = data.keys() if hasattr(data, "keys") else []
            if "is_partner" in keys and int(data["is_partner"] or 0) == 1:
                return True
            row_type = str(data["type"] or "").strip().casefold() if "type" in keys else ""
            return row_type in {"bayi", "tedarikçi", "tedarikci"}
        except Exception:
            return False

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.current_filter_type = None

        # Pagination State
        self.current_page = 0
        self.limit = 50
        self.total_count = 0
        self.search_query = None
        self.worker = None
        self._reload_pending = False
        self._pending_customers = []
        self._render_index = 0
        self._render_batch_size = 25
        self._multi_select = False
        self._opening_customer_360 = False
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self.refresh_data)
        if self.main_window and hasattr(self.main_window, "financial_data_changed"):
            self.main_window.financial_data_changed.connect(
                lambda: self.request_reload(0)
            )

        # Arama optimizasyonu (Debounce)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.execute_search)

        try:
            self.setup_ui()
            self._prepare_initial_view()
            logger.debug("CustomersPage init complete, scheduling refresh_data in 300ms")
            if getattr(self.db, "_db_name", "") == ":memory:":
                self.refresh_data()
            else:
                QTimer.singleShot(300, self.refresh_data)
        except Exception as e:
            logger.error(f"CustomersPage Init Error: {e}", exc_info=True)
            error_text = str(e)
            QTimer.singleShot(
                500,
                lambda message=error_text: self.notify(f"Hata: {message}", "error"),
            )

    def _is_automotive(self):
        try:
            sector_manager = getattr(self.main_window, "sector_manager", None)
            if sector_manager and sector_manager.get_current_plugin():
                return sector_manager.get_current_plugin().sector_id == "otomotiv"
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def notify(self, message, level="info"):
        if self.main_window and hasattr(self.main_window, "show_notification"):
            self.main_window.show_notification(message, level)
        else:
            from src.utils.toast_notification import show_error, show_success, show_warning, show_info
            if level == "error": show_error(self, message)
            elif level == "success": show_success(self, message)
            elif level == "warning": show_warning(self, message)
            else: show_info(self, message)

    def request_reload(self, delay_ms=50):
        self._reload_timer.stop()
        self._reload_timer.start(max(0, int(delay_ms)))

    def load_data(self, customers=None):
        """Legacy alias needed for some dialog callbacks"""
        self.request_reload()


class PartnersPage(CustomersPage):
    """
    \u00c7al\u0131\u015fma Ortaklar\u0131 sayfas\u0131 \u2014 CustomersPage'in bayi/tedarik\u00e7i filtreli versiyonu.
    PAGE_MAPPING'de page 26 i\u00e7in bu s\u0131n\u0131f kullan\u0131l\u0131r.
    """
    def __init__(self, db, main_window=None):
        super().__init__(db, main_window)
        # Varsay\u0131lan filtre olarak is_partner=1 tiplerini g\u00f6ster
        self.current_filter_type = "PARTNERS"

    def _setup_banners(self):
        """Override banners for partners context."""
        from PyQt6.QtWidgets import QFrame, QHBoxLayout
        from src.utils.theme_colors import tc
        banner_card = QFrame()
        banner_card.setObjectName("CustomerFilterBar")
        banner_card.setFixedHeight(52)
        from src.utils.theme_colors import theme_qss
        banner_card.setStyleSheet(
            theme_qss(
                "QFrame#CustomerFilterBar { background: @surface; border: 1px solid @border; border-radius: 12px; }"
            )
        )
        banner_layout = QHBoxLayout(banner_card)
        banner_layout.setContentsMargins(14, 8, 14, 8)
        banner_layout.setSpacing(12)

        configs = [
            ("T\u00dcM ORTAKLAR", tc("accent"), lambda: self.filter_by_type("PARTNERS"), 1),
            ("BAY\u0130LER", tc("warning"), lambda: self.filter_by_type("DEALERS"), 1),
            ("TEDAR\u0130K\u00c7\u0130LER", tc("secondary"), lambda: self.filter_by_type("SUPPLIERS"), 1),
            ("+ YEN\u0130 ORTAK EKLE", tc("success"), self.add_customer, 1),
        ]

        for text_value, color, cb, stretch in configs:
            btn = self._create_banner_btn(text_value, color)
            btn.clicked.connect(cb)
            banner_layout.addWidget(btn, stretch)

        self.layout.addWidget(banner_card)
