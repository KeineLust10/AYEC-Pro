# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QMenu

from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.role_utils import is_admin_role
from src.utils.theme_colors import tc, theme_qss


class DashboardUIMixin:
    def open_context_menu(self, position):
        """Tablo için sağ tık menüsü."""
        if not is_context_menu_enabled(self.db, page_id=40):
            return
        row = self.table.currentRow()
        if row == -1:
            return

        tracking_no = self.table.item(row, 0).text()
        customer_item = self.table.item(row, 2) if self.table.columnCount() > 2 else self.table.item(row, 1)
        customer_name = customer_item.text() if customer_item else ""

        role = "Personel"
        if hasattr(self.main_window, "user_data") and self.main_window.user_data:
            user_data = self.main_window.user_data
            if isinstance(user_data, dict):
                role = user_data.get("role", role)
            elif isinstance(user_data, (list, tuple)) and len(user_data) > 3:
                role = user_data[3]

        # Resolve colors before Qt parses the menu stylesheet.  This avoids
        # stale token values after a live theme switch.
        menu = QMenu(self.table)
        menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: {tc("surface")};
                color: {tc("text")};
                border: 1px solid {tc("border")};
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 10px 25px;
                color: {tc("text")};
                font-size: 13px;
                font-weight: 500;
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: {tc("hover_bg")};
                color: {tc("text")};
            }}
            QMenu::item:disabled {{
                color: {tc("muted")};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {tc("surface_alt")};
                margin: 4px 10px;
            }}
            """
        )

        def add_act(text, cb):
            action = menu.addAction(text)
            action.triggered.connect(cb)
            return action

        panel_label = "Bakım / Servis Paneli" if self._is_automotive() else "Teknisyen Paneli"
        add_act(panel_label, lambda: self.open_technician_panel(tracking_no))

        has_update_permission = self.db.check_permission(role, "update_status")
        if has_update_permission:
            form_label = "Araç İş Emri" if self._is_automotive() else "Servis Formu"
            add_act(form_label, lambda: self.open_edit_dialog(tracking_no))
            add_act("Düzenle", lambda: self.open_edit_dialog(tracking_no))

            status_menu = menu.addMenu("Durumu Değiştir")
            status_menu.setStyleSheet(menu.styleSheet())
            statuses = ["Bekliyor", "Tamirde", "Parça Bekliyor", "Test Sürecinde", "Hazır", "Teslim Edildi", "İptal"]
            if self._is_automotive():
                statuses = ["Bekliyor", "Serviste", "Parça Bekliyor", "Test Sürecinde", "Hazır", "Teslim Edildi", "İptal"]
            for status in statuses:
                action = status_menu.addAction(status)
                action.triggered.connect(lambda checked=False, value=status: self.change_status(tracking_no, value))

            menu.addSeparator()
            close_label = "İş Emrini Kapat" if self._is_automotive() else "İşlemi Kapat"
            add_act(close_label, lambda: self.quick_close_service(tracking_no))

        menu.addSeparator()
        add_act("Müşteri 360° Karne", lambda: self.open_customer_360_dialog(customer_name, tracking_no))
        add_act("Müşteri Bilgileri", lambda: self.open_context_menu_action("customer", tracking_no))

        if self.db.check_permission(role, "add_transaction") or is_admin_role(role):
            add_act("SMS Gönder", lambda: self.open_context_menu_action("sms", tracking_no))
            add_act("WhatsApp", lambda: self.open_context_menu_action("whatsapp", tracking_no))

        menu.addSeparator()
        add_act("Ödeme Al", lambda: self.open_context_menu_action("payment", tracking_no))
        add_act("Fotoğraflar / Medya", lambda: self.open_context_menu_action("photos", tracking_no))
        add_act(
            "Detayli Fis Yazdir",
            lambda: self.print_detailed_receipt(tracking_no),
        )
        add_act(
            "E-Fatura Kes",
            lambda: self.open_context_menu_action("invoice", tracking_no),
        )
        print_menu = menu.addMenu("Fi\u015f / Yazd\u0131r")
        print_menu.setStyleSheet(menu.styleSheet())
        print_actions = [
            ("K\u0131sa Fi\u015f", self.print_short_receipt),
            ("Detayl\u0131 Fi\u015f Yazd\u0131r", self.print_detailed_receipt),
            ("Kargo Fi\u015fi", self.print_cargo_receipt),
            ("Cihaz Etiketi", self._print_service_label_a),
        ]
        print_actions[-1] = ("Cihaz Etiketi A", self._print_service_label_a)
        print_actions.append(("Cihaz Etiketi B", self._print_service_label_b))
        print_actions.append(("Yazd\u0131r", self.print_service_form))
        for label, callback in print_actions:
            action = print_menu.addAction(label)
            action.triggered.connect(
                lambda checked=False, fn=callback: fn(tracking_no)
            )

        if is_admin_role(role):
            menu.addSeparator()
            add_act("Sil", lambda: self.delete_service(tracking_no))

        menu.exec(self.table.viewport().mapToGlobal(position))

    def on_table_double_click(self, row, column):
        if row < 0 or getattr(self, "_dashboard_double_click_busy", False):
            return
        self._dashboard_double_click_busy = True
        item_id = self.table.item(row, 0)
        if not item_id:
            self._dashboard_double_click_busy = False
            return
        tracking_no = item_id.text()
        try:
            if column == 2:
                customer_item = self.table.item(row, 2)
                customer_name = customer_item.text() if customer_item else ""
                self.open_customer_360_dialog(customer_name, tracking_no=tracking_no)
            elif column == 5 or self._is_automotive() or column in {1, 3}:
                self.open_technician_panel(tracking_no)
            else:
                self.open_edit_dialog(tracking_no)
        finally:
            QTimer.singleShot(250, lambda: setattr(self, "_dashboard_double_click_busy", False))

    def apply_filter(self, category):
        self.current_filter_category = category
        if hasattr(self, "lbl_table_title"):
            title = self._table_title(category) if hasattr(self, "_table_title") else "Servis Listesi"
            self.lbl_table_title.setText(title)
        self.update_filter_buttons_style()
        self.populate_table()

    def update_filter_buttons_style(self):
        if not hasattr(self, "filter_buttons"):
            return
        for key, btn in self.filter_buttons.items():
            active = key == self.current_filter_category
            accent = btn.property("accent") or tc("accent")
            classic = bool(hasattr(self, "_is_classic_appearance") and self._is_classic_appearance())
            text = btn.property("filterText") or btn.text()
            icon = btn.property("filterIcon") or ""
            action = btn.property("filterAction") or "filter"
            btn.setText(str(text))
            btn.setFixedSize(112 if classic else 118, 30 if classic else 44)

            if classic:
                btn.setObjectName("DashboardFilterButton")
                btn.setProperty("skipThemeTransform", False)
                btn.setCheckable(True)
                btn.setChecked(active)
                bg = tc("selection_bg") if active else tc("surface")
                border = tc("accent") if active else tc("border")
                if action == "add" and not active:
                    border = tc("success")
                fg = tc("text")
                btn.setStyleSheet(f"""
                    QPushButton#DashboardFilterButton {{
                        background-color: {bg};
                        color: {fg};
                        border: 1px solid {border};
                        border-radius: 0px;
                        font-size: 11px;
                        font-weight: 700;
                        text-align: center;
                        padding: 3px 8px;
                    }}
                    QPushButton#DashboardFilterButton:hover {{
                        background-color: {tc("hover_bg")};
                        color: {tc("text")};
                        border-color: {tc("accent")};
                    }}
                    QPushButton#DashboardFilterButton:pressed {{
                        background-color: {tc("selection_bg")};
                        color: {tc("selection_text")};
                        border-color: {tc("accent")};
                    }}
                """)
                palette = btn.palette()
                for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
                    palette.setColor(group, QPalette.ColorRole.ButtonText, QColor(fg))
                btn.setPalette(palette)
                continue

            if active:
                bg = accent
                fg = self._contrast_on(accent) if hasattr(self, "_contrast_on") else "#ffffff"
                hover_bg = self._hover_on(accent) if hasattr(self, "_hover_on") else "#111827"
                hover_fg = fg
                border = accent
            else:
                bg = "@surface"
                fg = accent
                hover_bg = "@surface_alt"
                hover_fg = accent
                border = "@border"

            btn.setStyleSheet(theme_qss(f"""
                QPushButton {{
                    background-color: {bg};
                    color: {fg};
                    border: 1px solid {border};
                    border-radius: 12px;
                    font-size: 10px;
                    font-weight: 800;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: {hover_bg};
                    border-color: {accent};
                    color: {hover_fg};
                    padding-bottom: 2px;
                }}
                QPushButton:pressed {{
                    padding-top: 2px;
                }}
            """))
            palette = btn.palette()
            for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
                palette.setColor(group, QPalette.ColorRole.ButtonText, QColor(fg))
            btn.setPalette(palette)
