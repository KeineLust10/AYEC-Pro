# -*- coding: utf-8 -*-

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication
from src.utils.logger import logger
from src.utils.page_ids import PageIds
from src.utils.performance_monitor import perf_span

class DashboardDialogMixin:
    def open_service_form_shortcut(self):
        try:
            if self._is_automotive():
                if self.main_window and hasattr(self.main_window, "switch_page"):
                    self.main_window.switch_page(PageIds.VEHICLE_MAINTENANCE)
                    def _open_vehicle_card():
                        try:
                            page = self.main_window.get_page(PageIds.VEHICLE_MAINTENANCE) if hasattr(self.main_window, "get_page") else None
                            if page and hasattr(page, "open_new_card"): page.open_new_card()
                        except Exception as inner_e: self.notify(f"Araç kartı açılamadı: {inner_e}", "error")
                    QTimer.singleShot(150, _open_vehicle_card)
                    return
            self.open_new_service_dialog()
        except Exception as e: self.notify(f"Kısayol açılamadı: {e}", "error")

    def open_new_service_dialog(self):
        QTimer.singleShot(0, self._open_new_service_dialog_deferred)

    def _open_new_service_dialog_deferred(self):
        try:
            sector_manager = getattr(self, "sector_manager", None)
            if self._is_automotive():
                from src.ui.dialogs.automotive_new_service_dialog import AutomotiveNewServiceDialog as dialog_cls
                dlg = dialog_cls(self.db, self, sector_manager=sector_manager)
            else:
                from src.ui.dialogs.add_device_dialog import AddDeviceDialog
                dlg = AddDeviceDialog(self.db, self)
            if dlg.exec():
                self.refresh_data()
                self.notify("Yeni servis kaydı oluşturuldu.", "success")
        except Exception as e: self.notify(f"Kayıt ekranı açılamadı: {e}", "error")

    def open_new_customer_dialog(self):
        QTimer.singleShot(0, self._open_new_customer_dialog_deferred)

    def _open_new_customer_dialog_deferred(self):
        try:
            sector_manager = getattr(self, "sector_manager", None)
            if self._is_automotive():
                from src.ui.dialogs.automotive_customer_dialog import AutomotiveCustomerDialog as dialog_cls
            else:
                from src.ui.dialogs.technical_service_customer_dialog import TechnicalServiceCustomerDialog as dialog_cls
            dlg = dialog_cls(self.db, self, sector_manager=sector_manager)
            if dlg.exec():
                if hasattr(self, "refresh_data"): self.refresh_data()
                if self.main_window and hasattr(self.main_window, "refresh_loaded_page"): self.main_window.refresh_loaded_page(21)
                self.notify("Yeni müşteri kaydı oluşturuldu.", "success")
        except Exception as e: self.notify(f"Müşteri ekranı hatası: {e}", "error")

    def open_customer_360_dialog(self, customer_name, tracking_no=None):
        QTimer.singleShot(0, lambda: self._open_customer_360_dialog_deferred(customer_name, tracking_no))

    def _open_customer_360_dialog_deferred(self, customer_name, tracking_no=None):
        customer_id = None
        try:
            self.db.cursor.execute("SELECT id FROM customers WHERE name=?", (customer_name,))
            row = self.db.cursor.fetchone()
            if row: customer_id = row[0]
            elif tracking_no:
                self.db.cursor.execute("SELECT customer_id FROM devices WHERE tracking_no=? AND COALESCE(is_deleted,0)=0", (tracking_no,))
                row = self.db.cursor.fetchone()
                if row: customer_id = row[0]
        except Exception as e: logger.error(f"Customer ID lookup error: {e}")

        if customer_id:
            from src.ui.dialogs.customer_360_dialog import Customer360Dialog
            dlg = Customer360Dialog(self.db, customer_id, customer_name, self.main_window, sector_manager=getattr(self, "sector_manager", None))
            dlg.exec()
        else: self.notify(f"'{customer_name}' için müşteri kaydı bulunamadı.", "warning")

    def open_technician_panel(self, tracking_no):
        recent = getattr(self, "_technician_panel_recent_tracking", None)
        if recent == str(tracking_no):
            return
        self._technician_panel_recent_tracking = str(tracking_no)
        # Keep the latch longer than the modal dialog's nested event loop so
        # queued mouse events cannot reopen the same panel after it closes.
        QTimer.singleShot(10000, lambda: setattr(self, "_technician_panel_recent_tracking", None))
        # Route through the main window guard so rapid double clicks cannot
        # queue multiple technician panel dialogs during startup.
        main_opener = getattr(self.main_window, "open_technician_panel", None)
        if callable(main_opener) and main_opener is not self.open_technician_panel:
            main_opener(tracking_no)
            return
        if getattr(self, "_opening_technician_panel", False): return
        self._opening_technician_panel = True
        QTimer.singleShot(0, lambda: self._open_technician_panel_deferred(tracking_no))

    def _open_technician_panel_deferred(self, tracking_no):
        try:
            with perf_span("Dashboard.technician_panel.device_lookup", extra=str(tracking_no)):
                if hasattr(self.db, "get_device_by_tracking_no"): row = self.db.get_device_by_tracking_no(tracking_no)
                else:
                    cur = self.db.conn.cursor()
                    cur.execute("SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0", (tracking_no,))
                    row = cur.fetchone()
            if row:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                sector_manager = getattr(self, "sector_manager", None)
                panel_cls = self._resolve_technician_panel_class()
                # TechnicianPanel.__init__ takes (db, tracking_no, parent, ...).
                # We already have the tracking_no string from the outer scope.
                try:
                    with perf_span("Dashboard.technician_panel.create", extra=str(tracking_no)):
                        dialog = panel_cls(self.db, tracking_no, self.main_window, sector_manager=sector_manager)
                finally:
                    try: QApplication.restoreOverrideCursor()
                    except: pass
                dialog.exec()
                QTimer.singleShot(0, self.refresh_data)
                QTimer.singleShot(250, self._refresh_service_board)
            else: self.notify(f"Servis kaydı bulunamadı: {tracking_no}", "warning")
        except Exception as e:
            try: QApplication.restoreOverrideCursor()
            except: pass
            self.notify(f"Panel açılırken hata: {e}", "error")
        finally: self._opening_technician_panel = False

    def open_add_stock_dialog(self):
        QTimer.singleShot(0, self._open_add_stock_dialog_deferred)

    def _open_add_stock_dialog_deferred(self):
        try:
            from src.ui.dialogs.add_stock_dialog import AddStockDialog
            try: dlg = AddStockDialog(self.db, parent=self)
            except TypeError:
                dlg = AddStockDialog(self.db)
                if hasattr(dlg, "setParent"): dlg.setParent(self)
            if dlg.exec(): self.notify("Yeni ürün/stok eklendi.", "success")
        except Exception as e: self.notify(f"Stok penceresi açılamadı: {e}", "error")

    def open_edit_dialog(self, tracking_no):
        QTimer.singleShot(0, lambda: self._open_edit_dialog_deferred(tracking_no))

    def _open_edit_dialog_deferred(self, tracking_no):
        try:
            if hasattr(self.db, "get_device_by_tracking_no"): device = self.db.get_device_by_tracking_no(tracking_no)
            else:
                self.db.cursor.execute("SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0", (tracking_no,))
                device = self.db.cursor.fetchone()
            if device:
                sector_manager = getattr(self, "sector_manager", None)
                if self._is_automotive():
                    from src.ui.dialogs.automotive_new_service_dialog import AutomotiveNewServiceDialog as dialog_cls
                    dlg = dialog_cls(self.db, self, device_data=device, sector_manager=sector_manager)
                else:
                    from src.ui.dialogs.technical_service_new_service_dialog import TechnicalServiceNewServiceDialog as dialog_cls
                    dlg = dialog_cls(self.db, self, device_data=device, sector_manager=sector_manager)
                if dlg.exec(): self.refresh_data()
            else: self.notify("Kayıt bulunamadı.", "warning")
        except Exception as e: logger.error(f"Edit error: {e}"); self.notify(f"Düzeltme hatası: {e}", "error")

    def _refresh_service_board(self):
        try:
            if hasattr(self.main_window, "page_service_board") and hasattr(self.main_window.page_service_board, "refresh_data"):
                self.main_window.page_service_board.refresh_data(); return
            if hasattr(self.main_window, "service_board_page") and hasattr(self.main_window.service_board_page, "refresh_data"):
                self.main_window.service_board_page.refresh_data(); return
            page = getattr(self.main_window, "pages", {}).get(41)
            if page and hasattr(page, "refresh_data"): page.refresh_data()
        except Exception as e: logger.debug(f"Service board refresh skipped: {e}")
