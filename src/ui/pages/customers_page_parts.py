# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer
from src.ui.pages.customers.logic.customer_manager import CustomerManager

# Standalone classes
from src.ui.pages._cpp_worker import CustomerWorker
from src.ui.pages._cpp_legacy import LegacyPartnersPageListUnused
from src.ui.pages._cpp_dialog import PartnerDialog

# Mixins
from src.ui.pages._cpp_db_mixin import PartnersPageDbMixin
from src.ui.pages._cpp_style_mixin import PartnersPageStyleMixin
from src.ui.pages._cpp_ui_mixin import PartnersPageUiMixin
from src.ui.pages._cpp_logic_mixin import PartnersPageLogicMixin

class PartnersPage(QWidget, PartnersPageDbMixin, PartnersPageStyleMixin, PartnersPageUiMixin, PartnersPageLogicMixin):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.customer_manager = CustomerManager(db)

        self.all_partners = []
        self.filtered_partners = []
        self.selected_partner = None
        self.current_service_type = None
        self.current_commission_filter = None

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filters)

        self.setup_ui()
        QTimer.singleShot(100, self.load_data)

    def notify(self, message, level="info"):
        from src.utils.toast_notification import show_success, show_error, show_warning, show_info
        if self.main_window and hasattr(self.main_window, "show_notification"):
            self.main_window.show_notification(message, level)
            return
        funcs = {"error": show_error, "success": show_success, "warning": show_warning, "info": show_info}
        funcs.get(level, show_info)(self, message)

    def load_data(self):
        try:
            raw_rows = self.customer_manager.get_customers() or []
            rows = [dict(r) if hasattr(r, "keys") else r for r in raw_rows]
            self.all_partners = [r for r in rows if self._is_partner_row(r)]
        except Exception as e:
            self.all_partners = []
            self.notify(f"Calisma ortaklari yuklenemedi: {e}", "error")
        self.rebuild_service_type_filter()
        self.apply_filters()
