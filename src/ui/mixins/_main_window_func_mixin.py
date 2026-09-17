# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QDialog, QApplication, QLineEdit
from PyQt6.QtCore import Qt, QTimer
from src.utils.logger import logger
from src.utils.theme_colors import theme_qss

class MainWindowFuncMixin:
    """Specialized functional dialogs and user actions."""

    def init_assistant_fab(self):
        from src.ui.components.assistant_fab import DraggableAssistantFabButton
        self.assistant_fab = DraggableAssistantFabButton("🤖", self)
        self.assistant_fab.setObjectName("AssistantFAB")
        self.assistant_fab.setFixedSize(60, 60)
        self.assistant_fab.setCursor(Qt.CursorShape.PointingHandCursor)
        self.assistant_fab.clicked.connect(self.toggle_assistant)
        self.assistant_fab.setStyleSheet(theme_qss("QPushButton#AssistantFAB { background-color: @accent; color: white; border-radius: 30px; font-size: 28px; padding-bottom: 2px; }"))
        fab_enabled = str(self.db.get_setting("assistant_fab_enabled", "1")) == "1"
        self.assistant_fab.setVisible(fab_enabled)
        if fab_enabled:
            self.reposition_fab()

    def reposition_fab(self):
        if not hasattr(self, "assistant_fab"):
            return
        # Reserve the lower-right notification lane above the assistant.
        self.assistant_fab.move(self.width() - 90, self.height() - 90)

    def toggle_assistant(self):
        from src.ui.widgets.assistant_sidebar import AssistantSidebarDialog
        if self.assistant_sidebar and self.assistant_sidebar.isVisible():
            self.assistant_sidebar.close()
        else:
            if not self.assistant_sidebar:
                self.assistant_sidebar = AssistantSidebarDialog(self.db, self)
                self.assistant_sidebar.closed.connect(self.toggle_assistant)
            self.assistant_sidebar.show()
            self.assistant_sidebar.raise_()

    def toggle_voice_assistant(self):
        return self._ensure_assistant_manager().toggle_voice_assistant()

    def is_assistant_silent_mode(self):
        try:
            return self.db.get_setting("voice_assistant_active", "1") != "1"
        except Exception:
            return False

    def set_assistant_silent_mode(self, silent):
        try:
            self.db.set_setting("voice_assistant_active", "0" if silent else "1")
        except Exception:
            pass

        if silent:
            if getattr(self, "assistant", None) is not None:
                self.assistant.stop_voice_assistant(notify=True)
            return True

        assistant = self._ensure_assistant_manager()
        started = bool(assistant.start_voice_assistant(notify=True))
        if not started:
            try:
                self.db.set_setting("voice_assistant_active", "0")
            except Exception:
                pass
        return started

    def handle_logout_requested(self):
        from src.ui.modern_login_window import ModernLoginWindow
        from src.utils.auth_manager import AuthManager
        try:
            auth = AuthManager(self.db)
            auth.clear_token()
            uid = None
            if hasattr(self, "user_data") and self.user_data:
                uid = self.user_data.get("id")
            if uid:
                self.db.cursor.execute("UPDATE users SET auto_login = 0 WHERE id = ?", (uid,))
                self.db.conn.commit()
            self.hide()
            login_window = ModernLoginWindow(self.db)
            if login_window.exec() == QDialog.DialogCode.Accepted:
                self.user_data = getattr(login_window, "user_data", {})
                self.username = self.user_data.get("username", "Kullan\u0131c\u0131")
                self._reload_all_pages()
                self.refresh_side_menu()
                self._refresh_active_page(40)
                self.show()
                self.showMaximized()
                return True
            else:
                self.close()
                QApplication.instance().quit()
                return False
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False

    def _is_automotive(self):
        try:
            if hasattr(self, "sector_manager") and self.sector_manager:
                if hasattr(self.sector_manager, "get_current_plugin") and self.sector_manager.get_current_plugin():
                    return self.sector_manager.get_current_plugin().sector_id == "otomotiv"
            from src.utils.system_config import SystemConfig
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def open_technician_panel(self, tracking_no=None):
        tracking_key = str(tracking_no or "")
        if tracking_key and getattr(self, "_last_technician_tracking", None) == tracking_key:
            return
        if tracking_key:
            self._last_technician_tracking = tracking_key
            QTimer.singleShot(10000, lambda: setattr(self, "_last_technician_tracking", None))
        if getattr(self, "_dialog_open", False):
            return
        self._dialog_open = True
        try:
            device = None
            if tracking_no:
                device = self.db.get_device_by_tracking_no(tracking_no)
            # A row-triggered open must never fall back to the device picker.
            # A transient lookup miss would otherwise create the small picker
            # window repeatedly before the technician panel appears.
            if not device and not tracking_no:
                from src.ui.dialogs.device_selection_dialog import DeviceSelectionDialog
                dlg = DeviceSelectionDialog(self.db, self)
                if dlg.exec() and getattr(dlg, "selected_device", None):
                    device = dlg.selected_device
            if device:
                # Sector based panel logic
                if self._is_automotive():
                    from src.ui.dialogs.automotive_technician_panel import AutomotiveTechnicianPanel
                    panel = AutomotiveTechnicianPanel(self.db, device, self, sector_manager=self.sector_manager)
                else:
                    from src.ui.dialogs.technical_service_technician_panel import TechnicalServiceTechnicianPanel
                    panel = TechnicalServiceTechnicianPanel(self.db, device, self, sector_manager=self.sector_manager)
                panel.exec()
        finally:
            self._dialog_open = False

    def open_customer_360_by_id(self, customer_id):
        try:
            from src.ui.dialogs.technical_customer_360_dialog import TechnicalCustomer360Dialog
            dlg = TechnicalCustomer360Dialog(self.db, customer_id, "Müşteri", self, sector_manager=self.sector_manager)
            dlg.exec()
        except Exception as e:
            logger.error(f"Customer360 error: {e}")

    def open_interface_layout_editor(self):
        from src.ui.widgets.modern_dialog import ModernDialog
        from src.ui.widgets.page_layout_editor import PageLayoutEditorWidget
        try:
            dlg = ModernDialog(title="Arayüz Düzenle", parent=self, width=1080, height=840)
            dlg.set_footer_visible(False)
            dlg.set_wheel_scroll_enabled(True)
            editor = PageLayoutEditorWidget(self)
            editor.layout_updated.connect(self.refresh_side_menu)
            dlg.add_widget(editor)
            dlg.exec()
        except Exception as e:
            logger.error(f"Interface layout editor error: {e}")

    def perform_search_on_page(self, query):
        active_page = self.content_area.currentWidget()
        if not active_page:
            return
        search_box = active_page.findChild(QLineEdit)
        if search_box:
            search_box.setText(query)
            search_box.returnPressed.emit()
