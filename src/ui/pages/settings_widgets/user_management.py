# -*- coding: utf-8 -*-

"""
User Management Widget
Kullanıcı yönetimi için ayarlar sayfası widget'ı
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QDialog, QLabel,
                             QLineEdit, QComboBox, QHeaderView, QGroupBox,
                             QGraphicsDropShadowEffect, QFrame, QCheckBox, QScrollArea, QMenu,
                             QAbstractItemView, QGridLayout)
from PyQt6.QtCore import Qt
from src.utils.theme_colors import theme_qss, tc, qc
from PyQt6.QtGui import QFont, QColor, QAction, QFontDatabase
from datetime import datetime
import re
import hashlib
import json
import logging
from src.ui.widgets.toast_notification import show_toast
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.ui.widgets.reference_checkbox import ReferenceCheckBox
from src.ui.widgets.modern_inputs import ModernComboBox
from src.ui.widgets.financial_reference_controls import ReferenceMetricValueLabel
from src.utils.role_utils import is_admin_role, normalize_role
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.design_system import DesignTokens
from src.utils.user_permission_catalog import USER_PERMISSION_SECTIONS, parse_saved_page_permissions
from src.utils.user_account_actions import set_user_account_active, current_account_administrator, save_user_page_permissions
import hashlib


from src.ui.pages.settings_widgets.user_management_dialogs import NewUserDialog, UserDialog

logger = logging.getLogger("AYECProLogger")

class UserManagementWidget(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._loading = False
        self._personnel_map = {}
        self.page = 1
        self.page_size = 6
        self.total_count = 0
        self.search_text = ""
        self._last_user_sort = "ASC"
        self.filter_role = "Tümü"
        self.filter_status = "Tümü"
        try:
            from src.utils.auth_manager import AuthManager
            self.auth_manager = AuthManager(self.db)
        except Exception:
            self.auth_manager = None
        self.init_ui()
        # Defer data load to improve responsiveness
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self.load_users)

    def _safe_identifier(self, name):
        text = str(name or "").strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text):
            raise ValueError(f"Invalid identifier: {name}")
        return text
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.setObjectName("UserManagementCanvas")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(theme_qss(
            "QWidget#UserManagementCanvas { background: @finance_canvas; }"
        ))
        
        # Header
        header = QLabel("Kullan\u0131c\u0131 Y\u00f6netimi & Yetki Matrisi")
        header.setFont(QFont(DesignTokens.FONT_NAME, 14, QFont.Weight.Bold))
        header.setFixedHeight(28)
        header_row = QHBoxLayout()
        header_row.addWidget(header)
        header_row.addStretch()
        layout.addLayout(header_row)
        
        # Description
        desc = QLabel("Personel için kullanıcı hesapları oluşturun ve yönetin.")
        desc.setStyleSheet(theme_qss("color: @text_muted; margin-bottom: 10px;"))
        layout.addWidget(desc)
        header.setToolTip(desc.text())
        desc.hide()

        header_actions = QHBoxLayout()
        header_actions.addStretch()
        security_report = QPushButton("Guvenlik Raporu")
        self.security_report_button = security_report
        security_report.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        security_report.clicked.connect(self._open_security_report)
        header_actions.addWidget(security_report)
        reset_passwords = QPushButton("Toplu Sifre Sifirla")
        self.bulk_password_button = reset_passwords
        reset_passwords.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        reset_passwords.clicked.connect(self._open_bulk_password_dialog)
        header_actions.addWidget(reset_passwords)
        header_new_user = QPushButton("Yeni Personel / Kullanici Ekle")
        header_new_user.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        header_new_user.clicked.connect(self.add_user)
        self.btn_add = header_new_user
        header_actions.addWidget(header_new_user)
        header_row.addLayout(header_actions)

        summary = QGridLayout()
        summary.setSpacing(8)
        self.reference_metric_values = {}
        for column, (title, value, detail, color) in enumerate((
            ("TOPLAM KULLANICI", "-", "Hesap kaydi", "@finance_primary"),
            ("ROL DAGILIMI", "-", "Kayitli roller", "@finance_secondary"),
            ("CANLI OTURUMLAR", "-", "Oturum telemetrisi yok", "@finance_tertiary"),
            ("GUVENLIK SKORU", "-", "Guvenlik olcumu yok", "@finance_secondary"),
        )):
            metric = QFrame()
            metric.setFixedHeight(96)
            metric.setStyleSheet(theme_qss(f"""
                QFrame {{ background: @finance_surface_alt; border: 1px solid @finance_outline; border-top: 2px solid {color}; border-radius: 6px; }}
                QLabel {{ border: none; }}
            """))
            metric_layout = QVBoxLayout(metric)
            metric_layout.setContentsMargins(10, 7, 10, 7)
            metric_layout.setSpacing(1)
            title_label = QLabel(title)
            title_label.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px; font-weight: 700;"))
            value_label = ReferenceMetricValueLabel(value, primary_size=18, primary_token=color.lstrip("@"))
            value_label.setToolTip(value)
            self.reference_metric_values[column] = value_label
            value_label.setStyleSheet(theme_qss(f"color: {color}; font-size: 18px; font-weight: 800;"))
            detail_label = QLabel(detail)
            detail_label.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px;"))
            metric_layout.addWidget(title_label); metric_layout.addWidget(value_label); metric_layout.addWidget(detail_label)
            summary.addWidget(metric, 0, column)
        layout.addLayout(summary)
        
        filter_layout = QHBoxLayout()
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Kullanıcı adı, e-posta veya personel ara...")
        self.inp_search.textChanged.connect(self.on_search_changed)
        self.cmb_role_filter = ModernComboBox()
        self.cmb_role_filter.addItems(["Tümü", "Master", "Admin", "Yönetici", "Teknisyen", "Muhasebe", "Personel"])
        self.cmb_role_filter.currentTextChanged.connect(self.on_filter_changed)
        self.cmb_role_filter.set_reference_chevron()
        self.cmb_status_filter = ModernComboBox()
        self.cmb_status_filter.addItems(["Tümü", "Aktif", "Pasif"])
        self.cmb_status_filter.currentTextChanged.connect(self.on_filter_changed)
        self.cmb_status_filter.set_reference_chevron()
        filter_layout.addWidget(QLabel("Rol:"))
        filter_layout.addWidget(self.cmb_role_filter)
        filter_layout.addWidget(QLabel("Durum:"))
        filter_layout.addWidget(self.cmb_status_filter)
        self.user_sort_order = ModernComboBox()
        self.user_sort_order.addItem("Kayit Sirasi", "ASC")
        self.user_sort_order.addItem("Son Eklenenler", "DESC")
        self.user_sort_order.currentIndexChanged.connect(self.on_filter_changed)
        self.user_sort_order.set_reference_chevron()
        filter_layout.addWidget(self.user_sort_order)
        
        # Buttons
        self.btn_refresh = QPushButton("Yenile")
        self.btn_refresh.clicked.connect(self.load_users)
        self.btn_refresh.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        
        # Users Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Kullanıcı Adı", "Rol", "Personel", "Oluşturma Tarihi", "Durum", "Arayüz", "DÜZENLE", "SİL"
        ])
        
        # Table styling - Modern and aligned
        self.table.setStyleSheet(theme_qss("""
            QTableWidget {
                border: 1px solid @border;
                border-radius: 12px;
                background: @surface;
                gridline-color: @surface_alt;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 2px solid @surface_alt; 
            }
            QHeaderView::section {
                background: @surface;
                padding: 14px 8px;
                border: none;
                border-bottom: 2px solid @border;
                font-weight: 800;
                color: @text_muted;
                text-align: center;
                text-transform: uppercase;
            }
            QTableWidget::item:selected {
                background: @selection_bg;
                color: @text;
            }
        """))
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Username
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Role
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Personnel
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Created
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Status
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Interface
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)  # Edit
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)  # Delete
        
        self.table.setColumnWidth(0, 50)   # ID
        self.table.setColumnWidth(2, 100)  # Role
        self.table.setColumnWidth(4, 140)  # Created
        self.table.setColumnWidth(5, 100)  # Status
        self.table.setColumnWidth(6, 120)  # Interface
        self.table.setColumnWidth(7, 120)  # Edit
        self.table.setColumnWidth(8, 100)  # Delete
        for hidden_column in (0, 4, 6, 7, 8):
            self.table.setColumnHidden(hidden_column, True)
        
        # Context Menu Policy
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Increase row height
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.table.itemChanged.connect(self._handle_item_changed)
        self.table.cellClicked.connect(self._update_detail_panel)
        
        users_header = QHBoxLayout()
        users_title = QLabel("Sistem Kullan\u0131c\u0131lar\u0131")
        users_title.setStyleSheet(theme_qss("font-size: 12px; font-weight: 800; color: @text;"))
        users_count = QLabel("- Kay\u0131t")
        self.users_count_label = users_count
        users_count.setStyleSheet(theme_qss(
            "color: @text_muted; background: @surface_alt; border-radius: 4px; padding: 3px 8px;"
        ))
        users_header.addWidget(users_title)
        users_header.addStretch()
        users_header.addWidget(users_count)
        self.user_table_toggle = QPushButton("Tablo")
        self.user_table_toggle.setToolTip("Tablo / Tum Alanlar")
        self.user_table_toggle.setCheckable(True)
        self.user_table_toggle.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.user_table_toggle.toggled.connect(self._set_user_table_mode)
        users_header.addWidget(self.user_table_toggle)
        users_header.addWidget(self.btn_refresh)

        content = QHBoxLayout()
        content.setSpacing(12)
        user_list = QWidget()
        user_list_layout = QVBoxLayout(user_list)
        user_list_layout.setContentsMargins(0, 0, 0, 0)
        user_list_layout.addLayout(users_header)
        user_list_layout.addWidget(self.inp_search)
        user_list_layout.addLayout(filter_layout)
        self.user_cards_scroll = QScrollArea()
        self.user_cards_scroll.setWidgetResizable(True)
        self.user_cards_scroll.setFrameShape(QFrame.Shape.NoFrame)
        cards = QWidget()
        self.user_cards_layout = QVBoxLayout(cards)
        self.user_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.user_cards_layout.setSpacing(4)
        self.user_cards_scroll.setWidget(cards)
        self.user_card_buttons = {}
        user_list_layout.addWidget(self.user_cards_scroll)
        user_list_layout.addWidget(self.table)
        self.table.hide()
        content.addWidget(user_list, 2)
        content.addWidget(self._build_detail_panel(), 3)
        layout.addLayout(content, 1)
        
        pagination_layout = QHBoxLayout()
        self.btn_prev = QPushButton("◀︎ Önceki")
        self.btn_next = QPushButton("Sonraki ▶︎")
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.clicked.connect(lambda: self.change_page(-1))
        self.btn_next.clicked.connect(lambda: self.change_page(1))
        self.lbl_page = QLabel("Sayfa 1")
        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addWidget(self.lbl_page)
        pagination_layout.addWidget(self.btn_next)
        pagination_layout.addStretch()
        layout.addLayout(pagination_layout)
        
        self.setLayout(layout)

    def _set_user_table_mode(self, enabled):
        self.table.setVisible(enabled)
        self.user_cards_scroll.setVisible(not enabled)
        for column in (0, 4, 6, 7, 8):
            self.table.setColumnHidden(column, not enabled)

    def _create_security_report(self):
        from src.ui.pages.audit_log_page import AuditLogPage
        from src.ui.widgets.modern_dialog import ModernDialog
        from src.utils.audit_logger import AuditLogger

        dialog = ModernDialog(title="Guvenlik Raporu / Audit Log", parent=self, width=1100, height=760)
        dialog.audit_page = AuditLogPage(self.db, audit_logger=AuditLogger(self.db))
        dialog.content_layout.addWidget(dialog.audit_page)
        dialog.add_button("Kapat", "secondary", dialog.reject)
        return dialog

    def _open_bulk_password_dialog(self):
        context = current_account_administrator(self, self.db)
        if not context or not self._confirm_permission_discard():
            return
        from src.ui.dialogs.bulk_password_dialog import BulkPasswordDialog
        dialog = BulkPasswordDialog(self.db, context["id"], parent=self)
        if dialog.exec():
            self.load_users()
        dialog.deleteLater()

    def _open_security_report(self):
        dialog = self._create_security_report()
        dialog.exec()
        dialog.deleteLater()

    def _select_user_card(self, user_id):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == str(user_id):
                self.table.selectRow(row)
                self._update_detail_panel(row)
                return

    def _rebuild_user_cards(self, users):
        while self.user_cards_layout.count():
            item = self.user_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.user_card_buttons = {}
        for user in users:
            user_id = str(user[0])
            card = QFrame()
            card.setMinimumHeight(80)
            card.setObjectName("UserAccountCard")
            card.setStyleSheet(theme_qss(
                "QFrame#UserAccountCard { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 4px; }"
                "QFrame#UserAccountCard[selected=\"true\"] { background: @finance_surface_alt; border-color: @finance_primary; }"
                "QLabel { background: transparent; border: none; color: @finance_text_muted; font-size: 10px; }"
                "QPushButton { background: transparent; border: none; color: @finance_text; text-align: left; font-size: 12px; font-weight: 700; padding: 3px; }"
                "QPushButton:checked { background: transparent; color: @finance_primary; }"
            ))
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 5, 8, 5)
            card_layout.setSpacing(3)
            name = str(user[5] or user[1] or "-")
            select = QPushButton(name.replace("&", "&&"))
            select.setCheckable(True)
            select.setToolTip(f"{user[1]} | ID: {user_id}")
            select.clicked.connect(lambda _checked=False, uid=user_id: self._select_user_card(uid))
            card_layout.addWidget(select)
            role = normalize_role(user[2] or "Personel")
            account_label = QLabel(f"{role} | {user[1]}")
            account_label.setTextFormat(Qt.TextFormat.PlainText)
            card_layout.addWidget(account_label)
            status = QHBoxLayout()
            status.addWidget(QLabel("Hesap aktif" if user[6] else "Hesap pasif"))
            status.addStretch()
            edit = QPushButton("Duzenle")
            edit.clicked.connect(lambda _checked=False, uid=user_id: self.edit_user(uid))
            status.addWidget(edit)
            card_layout.addLayout(status)
            self.user_cards_layout.addWidget(card)
            self.user_card_buttons[user_id] = select
        self.user_cards_layout.addStretch()

    def _build_detail_panel(self):
        panel = QFrame()
        self.detail_panel = panel
        panel.setStyleSheet(theme_qss(
            "QFrame { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 4px; }"
            "QLabel { background: transparent; border: none; }"
        ))
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(14, 14, 14, 14)
        panel_layout.setSpacing(9)
        self.detail_title = QLabel("Kullanici secin")
        self.detail_title.setTextFormat(Qt.TextFormat.PlainText)
        self.detail_title.setStyleSheet(theme_qss("font-size: 18px; font-weight: 850; color: @text;"))
        panel_layout.addWidget(self.detail_title)
        self.detail_status = QLabel("Hesap ve erisim bilgileri")
        self.detail_status.setTextFormat(Qt.TextFormat.PlainText)
        self.detail_status.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; font-weight: 750;"))
        panel_layout.addWidget(self.detail_status)
        self.detail_values = {}
        profile_fields = QGridLayout()
        profile_fields.setHorizontalSpacing(8)
        profile_fields.setVerticalSpacing(8)
        for field_index, (key, label) in enumerate((
            ("personnel", "ATANAN PERSONEL"),
            ("role", "KULLANICI ROLU"),
            ("access", "HESAP ERISIMI"),
        )):
            row = QFrame()
            row.setStyleSheet(theme_qss(
                "QFrame { background: @finance_surface_alt; border: 1px solid @finance_outline; border-radius: 4px; }"
                "QLabel { background: transparent; border: none; }"
            ))
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(9, 6, 9, 6)
            key_label = QLabel(label)
            key_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 9px; font-weight: 800;"))
            val = QLabel("-")
            val.setTextFormat(Qt.TextFormat.PlainText)
            val.setWordWrap(True)
            val.setStyleSheet(theme_qss("color: @text; font-weight: 700;"))
            row_layout.addWidget(key_label)
            row_layout.addWidget(val)
            profile_fields.addWidget(row, field_index // 2, field_index % 2)
            self.detail_values[key] = val
        panel_layout.addLayout(profile_fields)
        matrix_heading = QLabel("INCE AYARLI YETKI MATRISI")
        matrix_heading.setStyleSheet(theme_qss("color: @text; font-size: 11px; font-weight: 800;"))
        panel_layout.addWidget(matrix_heading)
        self.detail_permission_rows = {}
        self.detail_permission_checks = {}
        self.detail_permission_note = QLabel("Sayfa izinleri kullanici hesabindan yuklenir.")
        self.detail_permission_note.setWordWrap(True)
        self.detail_permission_note.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px;"))
        panel_layout.addWidget(self.detail_permission_note)
        self.detail_permissions_scroll = QScrollArea()
        self.detail_permissions_scroll.setWidgetResizable(True)
        self.detail_permissions_scroll.setFrameShape(QFrame.Shape.NoFrame)
        permission_canvas = QWidget()
        permission_layout = QVBoxLayout(permission_canvas)
        permission_layout.setContentsMargins(0, 0, 4, 0)
        permission_layout.setSpacing(4)
        for group, entries in USER_PERMISSION_SECTIONS:
            page_ids = tuple(page_id for page_id, _title in entries)
            row = QHBoxLayout()
            title = QLabel(group)
            title.setStyleSheet(theme_qss("color: @text; font-size: 10px; font-weight: 700;"))
            count = QLabel("-")
            count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            count.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; font-weight: 700;"))
            row.addWidget(title)
            row.addStretch()
            row.addWidget(count)
            permission_layout.addLayout(row)
            self.detail_permission_rows[group] = (tuple(page_ids), count)
            for page_id, title in entries:
                item = QFrame()
                item.setStyleSheet(theme_qss(
                    "QFrame { background: @finance_surface_alt; border: none; border-radius: 4px; }"
                    "QLabel { background: transparent; border: none; color: @finance_text; font-size: 11px; }"
                ))
                item_layout = QHBoxLayout(item)
                item_layout.setContentsMargins(8, 6, 8, 6)
                item_layout.addWidget(QLabel(title), 1)
                indicator = ReferenceCheckBox(checked_token="finance_secondary")
                indicator.setAccessibleName(title)
                indicator.setEnabled(False)
                indicator.toggled.connect(lambda checked, pid=page_id: self._permission_changed(pid, checked))
                indicator.setToolTip("Kayitli sayfa izni. Kullanici / Yetkileri Duzenle ile degistirin.")
                indicator.setStyleSheet(theme_qss(
                    "QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid @finance_outline; border-radius: 4px; background: @finance_surface; }"
                    "QCheckBox::indicator:checked { background: @finance_secondary; border-color: @finance_secondary; }"
                ))
                item_layout.addWidget(indicator)
                permission_layout.addWidget(item)
                self.detail_permission_checks[page_id] = indicator
        permission_layout.addStretch()
        self.detail_permissions_scroll.setWidget(permission_canvas)
        panel_layout.addWidget(self.detail_permissions_scroll, 1)
        permission_actions = QHBoxLayout()
        self.permission_cancel_button = QPushButton("Degisiklikleri Iptal")
        self.permission_cancel_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.permission_cancel_button.clicked.connect(self._cancel_permission_changes)
        self.permission_cancel_button.setEnabled(False)
        permission_actions.addWidget(self.permission_cancel_button)
        self.permission_save_button = QPushButton("Yetkileri Kaydet")
        self.permission_save_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        self.permission_save_button.clicked.connect(self._save_permission_changes)
        self.permission_save_button.setEnabled(False)
        permission_actions.addWidget(self.permission_save_button)
        panel_layout.addLayout(permission_actions)
        self.detail_edit_button = QPushButton("Kullanici / Yetkileri Duzenle")
        self.detail_edit_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.detail_edit_button.clicked.connect(self._edit_selected_user)
        panel_layout.addWidget(self.detail_edit_button)
        self.detail_active_button = QPushButton("Erisimi Durdur")
        self.detail_active_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("danger", size="sm")))
        self.detail_active_button.clicked.connect(self._toggle_selected_user_active)
        panel_layout.addWidget(self.detail_active_button)
        return panel

    def _update_detail_panel(self, row, _column=0):
        id_item = self.table.item(row, 0)
        if not id_item:
            return
        user_id = id_item.text().strip()
        if str(getattr(self, "_selected_user_id", "")) != user_id and not self._confirm_permission_discard():
            for previous_row in range(self.table.rowCount()):
                previous_item = self.table.item(previous_row, 0)
                if previous_item and previous_item.text() == str(self._selected_user_id):
                    self.table.selectRow(previous_row)
                    break
            return
        try:
            user_columns = (
                set(self.db._get_table_columns("users"))
                if hasattr(self.db, "_get_table_columns")
                else set()
            )
            email_expr = "u.email" if not user_columns or "email" in user_columns else "''"
            personnel_expr = "u.personnel_id" if not user_columns or "personnel_id" in user_columns else "NULL"
            active_expr = "COALESCE(u.active, 1)" if not user_columns or "active" in user_columns else "1"
            interface_expr = (
                "COALESCE(u.interface_edit_access, 0)"
                if not user_columns or "interface_edit_access" in user_columns
                else "0"
            )
            permission_expr = "u.permissions" if not user_columns or "permissions" in user_columns else "NULL"
            self.db.cursor.execute(
                f"SELECT u.username, {email_expr}, u.role, {personnel_expr}, "
                f"{active_expr}, {interface_expr}, {permission_expr}, p.name "
                f"FROM users u LEFT JOIN personnel p ON p.id={personnel_expr} WHERE u.id=?",
                (user_id,),
            )
            user = self.db.cursor.fetchone()
        except Exception:
            user = None
        if not user:
            return
        username, email, role, personnel_id, active, interface_access, raw_permissions, personnel_name = user
        is_active = bool(active)
        is_admin = is_admin_role(normalize_role(role or ""))
        self._selected_user_id = str(user_id)
        self._selected_user_active = is_active
        self._selected_user_role = role
        for card_id, button in self.user_card_buttons.items():
            button.setChecked(card_id == str(user_id))
            card = button.parentWidget()
            selected = card_id == str(user_id)
            if card.property("selected") != selected:
                card.setProperty("selected", selected)
                card.style().unpolish(card)
                card.style().polish(card)
                card.update()
        self.detail_edit_button.setEnabled(True)
        self.detail_active_button.setEnabled(True)
        self.detail_title.setText(str(personnel_name or username or "-"))
        self.detail_status.setText(
            f"{'ACTIVE' if is_active else 'SUSPENDED'}  |  {email or 'No email'}  |  {username or '-'}"
        )
        self.detail_status.setToolTip("Hesap durumu; canli oturum bilgisi mevcut degil.")
        self.detail_status.setStyleSheet(theme_qss(
            f"color: {'@success' if is_active else '@danger'}; font-size: 10px; font-weight: 750;"
        ))
        self.detail_values["personnel"].setText(str(personnel_name or "Atanmadi"))
        self.detail_values["role"].setText(normalize_role(role or "Personel"))
        self.detail_values["access"].setText(
            f"{'Aktif' if is_active else 'Pasif'}  |  "
            f"{'Arayuz duzenleme izni' if interface_access or is_admin else 'Standart arayuz erisimi'}"
        )
        decoded_permissions = parse_saved_page_permissions(raw_permissions)
        if is_admin:
            allowed = {page_id for ids, _label in self.detail_permission_rows.values() for page_id in ids}
            self.detail_permission_note.setText("Yonetici rolu tum sayfalara erisim saglar.")
        elif decoded_permissions is not None:
            allowed = decoded_permissions
            self.detail_permission_note.setText("Izinler kayitli kullanici sayfa erisimlerinden gosterilir.")
        else:
            allowed = set()
            self.detail_permission_note.setText("Bu kullanici icin kayitli sayfa izinleri bulunamadi.")
        for _group, (page_ids, label) in self.detail_permission_rows.items():
            granted = len(allowed.intersection(page_ids))
            label.setText(f"{granted} / {len(page_ids)} izin")
            label.setStyleSheet(theme_qss(
                f"color: {'@success' if granted == len(page_ids) else '@text_muted'}; "
                "font-size: 10px; font-weight: 700;"
            ))
        self._permission_baseline = set(allowed)
        self._permission_draft = set(allowed)
        self._sync_permission_draft()
        self.detail_active_button.setText("Erisimi Durdur" if is_active else "Erisimi Etkinlestir")
        self.detail_active_button.setStyleSheet(theme_qss(
            DesignTokens.get_button_qss("danger" if is_active else "success", size="sm")
        ))

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_permission_editing()

    def _can_edit_page_permissions(self):
        return bool(current_account_administrator(self, self.db) and getattr(self, "_selected_user_id", None)
                    and not is_admin_role(getattr(self, "_selected_user_role", "")))

    def _refresh_permission_editing(self):
        self.bulk_password_button.setEnabled(current_account_administrator(self, self.db) is not None)
        editable = self._can_edit_page_permissions()
        dirty = getattr(self, "_permission_draft", set()) != getattr(self, "_permission_baseline", set())
        for indicator in self.detail_permission_checks.values():
            indicator.setEnabled(editable)
            indicator.setToolTip("Degisiklikler Yetkileri Kaydet ile uygulanir." if editable else "Kayitli sayfa izni; duzenleme icin yonetici erisimi gerekir.")
        self.permission_save_button.setEnabled(editable and dirty)
        self.permission_cancel_button.setEnabled(dirty)

    def _sync_permission_draft(self):
        draft = getattr(self, "_permission_draft", set())
        for page_id, indicator in self.detail_permission_checks.items():
            previous = indicator.blockSignals(True)
            indicator.setChecked(page_id in draft)
            indicator.blockSignals(previous)
        for page_ids, label in self.detail_permission_rows.values():
            granted = len(draft.intersection(page_ids))
            label.setText(f"{granted} / {len(page_ids)} izin")
            label.setStyleSheet(theme_qss(
                f"color: {'@success' if granted == len(page_ids) else '@text_muted'}; font-size: 10px; font-weight: 700;"
            ))
        self._refresh_permission_editing()

    def _permission_changed(self, page_id, enabled):
        if not self._can_edit_page_permissions():
            self._cancel_permission_changes()
            return
        if enabled:
            self._permission_draft.add(page_id)
        else:
            self._permission_draft.discard(page_id)
        self._sync_permission_draft()

    def _cancel_permission_changes(self):
        self._permission_draft = set(getattr(self, "_permission_baseline", set()))
        self._sync_permission_draft()

    def _confirm_permission_discard(self):
        if getattr(self, "_permission_draft", set()) == getattr(self, "_permission_baseline", set()):
            return True
        from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
        dialog = ModernConfirmDialog(
            "Kaydedilmeyen Yetkiler", "Kaydedilmemis yetki degisiklikleri atilsin mi?",
            self, confirm_text="Degisiklikleri At", cancel_text="Geri Don",
        )
        if not dialog.exec():
            return False
        self._cancel_permission_changes()
        return True

    def _save_permission_changes(self):
        if not self._can_edit_page_permissions():
            self._refresh_permission_editing()
            return
        try:
            save_user_page_permissions(self.db, self._selected_user_id, self._permission_draft)
            self._permission_baseline = set(self._permission_draft)
            self._refresh_permission_editing()
            show_toast(self, "Kayitli sayfa yetkileri guncellendi.", "success")
        except Exception as exc:
            show_toast(self, f"Yetkiler kaydedilemedi: {exc}", "error")

    def _edit_selected_user(self):
        if getattr(self, "_selected_user_id", None):
            self.edit_user(self._selected_user_id)

    def _toggle_selected_user_active(self):
        if not self._confirm_permission_discard():
            return
        user_id = getattr(self, "_selected_user_id", None)
        if user_id:
            self._toggle_user_active(user_id, not self._selected_user_active)
            self.load_users()
            if self.table.rowCount():
                self._update_detail_panel(0)
    
    def on_search_changed(self, text):
        if not self._confirm_permission_discard():
            previous = self.inp_search.blockSignals(True)
            self.inp_search.setText(self.search_text)
            self.inp_search.blockSignals(previous)
            return
        self.search_text = (text or "").strip()
        self.page = 1
        self.load_users()
    
    def on_filter_changed(self, _):
        if not self._confirm_permission_discard():
            for combo, index in (
                (self.cmb_role_filter, self.cmb_role_filter.findText(self.filter_role)),
                (self.cmb_status_filter, self.cmb_status_filter.findText(self.filter_status)),
                (self.user_sort_order, self.user_sort_order.findData(self._last_user_sort)),
            ):
                previous = combo.blockSignals(True)
                combo.setCurrentIndex(index)
                combo.blockSignals(previous)
            return
        self._last_user_sort = self.user_sort_order.currentData()
        self.filter_role = self.cmb_role_filter.currentText() or "Tümü"
        self.filter_status = self.cmb_status_filter.currentText() or "Tümü"
        self.page = 1
        self.load_users()
    
    def change_page(self, delta):
        new_page = self.page + delta
        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        if 1 <= new_page <= total_pages:
            if not self._confirm_permission_discard():
                return
            self.page = new_page
            self.load_users()
    
    def _update_pagination_label(self):
        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        self.lbl_page.setText(f"Sayfa {self.page} / {total_pages}")
        self.btn_prev.setEnabled(self.page > 1)
        self.btn_next.setEnabled(self.page < total_pages)
    
    def show_context_menu(self, pos):
        if not is_context_menu_enabled(self.db):
            return
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        item = self.table.itemAt(pos)
        if item:
            row = item.row()
            user_id = self.table.item(row, 0).text()
            
            action_edit = menu.addAction("✏️ Düzenle")
            action_edit.triggered.connect(lambda: self.edit_user(user_id))
            action_delete = menu.addAction("🗑️ Sil")
            action_delete.triggered.connect(lambda: self.delete_user(user_id))
        
        menu.exec(self.table.mapToGlobal(pos))

    def _refresh_reference_metrics(self):
        """Read account totals without inventing session or security telemetry."""
        try:
            self.db.cursor.execute("SELECT role FROM users")
            roles = [normalize_role(row[0] or "Personel") for row in self.db.cursor.fetchall()]
            self.reference_metric_values[0].setText(str(len(roles)))
            self.reference_metric_values[1].setText(str(len(set(roles))))
            filter_roles = {self.cmb_role_filter.itemText(index) for index in range(self.cmb_role_filter.count())}
            for role in sorted(set(roles) - filter_roles):
                self.cmb_role_filter.addItem(role)
            self.users_count_label.setText(f"{len(roles)} Kay\u0131t")
        except Exception:
            self.reference_metric_values[0].setText("-")
            self.reference_metric_values[1].setText("-")

    def load_users(self):
        if not self._confirm_permission_discard():
            return
        self._refresh_reference_metrics()
        self._loading = True
        self.table.setRowCount(0)
        self._refresh_personnel_map()
        try:
            where = []
            params = []
            if self.search_text:
                like = f"%{self.search_text}%"
                where.append("(u.username LIKE ? OR u.email LIKE ? OR p.name LIKE ?)")
                params.extend([like, like, like])
            if self.filter_role and self.filter_role != "Tümü":
                role_filter = normalize_role(self.filter_role)
                if role_filter == "Master":
                    where.append("LOWER(TRIM(u.role)) = 'master'")
                elif role_filter == "Admin":
                    where.append("LOWER(TRIM(u.role)) IN ('admin', 'yönetici', 'yonetici')")
                else:
                    where.append("LOWER(TRIM(u.role)) = ?")
                    params.append(role_filter.lower())
            if self.filter_status and self.filter_status != "Tümü":
                where.append("COALESCE(u.active, 1) = ?")
                params.append(1 if self.filter_status == "Aktif" else 0)
            where_sql = (" WHERE " + " AND ".join(where)) if where else ""
            self.db.cursor.execute("""
                SELECT COUNT(*) 
                FROM users u
                LEFT JOIN personnel p ON u.personnel_id = p.id
                {where_sql}
            """.format(where_sql=where_sql), tuple(params))
            self.total_count = int(self.db.cursor.fetchone()[0] or 0)
            offset = (self.page - 1) * self.page_size
            sort_order = "DESC" if self.user_sort_order.currentData() == "DESC" else "ASC"
            self.db.cursor.execute("""
                SELECT u.id, u.username, u.role, u.personnel_id, u.created_at,
                       p.name as personnel_name,
                       COALESCE(u.active, 1) AS active,
                       COALESCE(u.interface_edit_access, 0) AS interface_edit
                FROM users u
                LEFT JOIN personnel p ON u.personnel_id = p.id
                {where_sql}
                ORDER BY u.id {sort_order}
                LIMIT ? OFFSET ?
            """.format(where_sql=where_sql, sort_order=sort_order), tuple(params + [self.page_size, offset]))
            users = self.db.cursor.fetchall()
            for row_idx, user in enumerate(users):
                self.table.insertRow(row_idx)
                item_id = QTableWidgetItem(str(user[0]))
                item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item_id.setFlags(item_id.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_idx, 0, item_id)
                item_user = QTableWidgetItem(user[1] or "")
                item_user.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                item_user.setData(Qt.ItemDataRole.UserRole, item_user.text())
                self.table.setItem(row_idx, 1, item_user)
                normalized_role = normalize_role(user[2] or "")
                role_item = QTableWidgetItem(normalized_role)
                role_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                role_item.setData(Qt.ItemDataRole.UserRole, role_item.text())
                if normalized_role == "Master":
                    role_item.setForeground(qc("accent_pressed"))
                    role_item.setBackground(qc("selection_bg"))
                elif is_admin_role(normalized_role):
                    role_item.setForeground(qc("warning"))
                    role_item.setBackground(qc("warning_bg"))
                elif normalized_role == "Teknisyen":
                    role_item.setForeground(qc("success"))
                    role_item.setBackground(qc("success_bg"))
                self.table.setItem(row_idx, 2, role_item)
                personnel_name = user[5] if len(user) > 5 and user[5] else "Atanmadı"
                item_personnel = QTableWidgetItem(personnel_name)
                item_personnel.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                item_personnel.setData(Qt.ItemDataRole.UserRole, item_personnel.text())
                self.table.setItem(row_idx, 3, item_personnel)
                item_date = QTableWidgetItem(user[4] or "")
                item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item_date.setFlags(item_date.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_idx, 4, item_date)
                for column in (0, 4):
                    item = self.table.item(row_idx, column)
                    item.setFont(QFont(DesignTokens.MONO_FONT_NAME, 9))
                    item.setToolTip(item.text())
                # Status toggle
                status_widget = QWidget()
                status_layout = QHBoxLayout(status_widget)
                status_layout.setContentsMargins(0, 0, 0, 0)
                status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                status_toggle = AnimatedToggle(active_color=tc("success"))
                status_toggle.setChecked(bool(user[6] if len(user) > 6 else 1))
                status_toggle.clicked.connect(lambda checked, uid=user[0]: self._toggle_user_active(uid, checked))
                status_layout.addWidget(status_toggle)
                self.table.setCellWidget(row_idx, 5, status_widget)
                # Interface permission toggle
                iface_widget = QWidget()
                iface_layout = QHBoxLayout(iface_widget)
                iface_layout.setContentsMargins(0, 0, 0, 0)
                iface_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                iface_toggle = AnimatedToggle(active_color=tc("accent"))
                if is_admin_role(normalized_role):
                    iface_toggle.setChecked(True)
                    iface_toggle.setEnabled(False)
                else:
                    iface_toggle.setChecked(bool(user[7] if len(user) > 7 else 0))
                    iface_toggle.clicked.connect(lambda checked, uid=user[0]: self._toggle_interface_permission(uid, checked))
                iface_layout.addWidget(iface_toggle)
                self.table.setCellWidget(row_idx, 6, iface_widget)
                # Edit button
                edit_widget = QWidget()
                edit_layout = QHBoxLayout(edit_widget)
                edit_layout.setContentsMargins(5, 5, 5, 5)
                edit_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                btn_edit = QPushButton("📝 DÜZENLE")
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setFixedHeight(40)
                btn_edit.setStyleSheet(theme_qss("""
                    QPushButton { background-color: @warning; color: @selection_text; font-weight: bold; border-radius: 8px; font-size: 13px; padding: 0 10px; border: none; }
                    QPushButton:hover { background-color: @warning; }
                """))
                btn_edit.clicked.connect(lambda checked, uid=user[0]: self.edit_user(uid))
                edit_layout.addWidget(btn_edit)
                self.table.setCellWidget(row_idx, 7, edit_widget)
                # Delete button
                delete_widget = QWidget()
                delete_layout = QHBoxLayout(delete_widget)
                delete_layout.setContentsMargins(5, 5, 5, 5)
                delete_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                btn_delete = QPushButton("🗑️ SİL")
                btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_delete.setFixedHeight(40)
                btn_delete.setStyleSheet(theme_qss("""
                    QPushButton { background-color: @danger; color: @selection_text; font-weight: bold; border-radius: 8px; font-size: 13px; padding: 0 10px; border: none; }
                    QPushButton:hover { background-color: @danger; }
                """))
                btn_delete.clicked.connect(lambda checked, uid=user[0]: self.delete_user(uid))
                delete_layout.addWidget(btn_delete)
                self.table.setCellWidget(row_idx, 8, delete_widget)
            self._rebuild_user_cards(users)
            if self.table.rowCount():
                self.table.selectRow(0)
                self._update_detail_panel(0)
            else:
                self._selected_user_id = None
                self.detail_title.setText("Kullanici secin")
                self.detail_status.setText("Filtreye uygun hesap bulunamadi.")
                self.detail_status.setToolTip("")
                for label in self.detail_values.values():
                    label.setText("-")
                for _page_ids, label in self.detail_permission_rows.values():
                    label.setText("-")
                for indicator in self.detail_permission_checks.values():
                    previous = indicator.blockSignals(True)
                    indicator.setChecked(False)
                    indicator.blockSignals(previous)
                self._permission_baseline = set()
                self._permission_draft = set()
                self._refresh_permission_editing()
                self.detail_permission_note.setText("Yetkileri gormek icin bir hesap secin.")
                self.detail_edit_button.setEnabled(False)
                self.detail_active_button.setEnabled(False)
            self._update_pagination_label()
        except Exception as e2:
            show_toast(self, f"Kullanıcılar yüklenemedi: {e2}", "error")
        finally:
            self._loading = False
    
    def _toggle_user_active(self, user_id, enabled):
        try:
            set_user_account_active(self.db, user_id, enabled)
            show_toast(self, "Durum güncellendi", "success")
        except Exception as e:
            show_toast(self, f"Durum güncellenemedi: {e}", "error")
            self.load_users()
    
    def _toggle_interface_permission(self, user_id, enabled):
        try:
            self.db.cursor.execute("UPDATE users SET interface_edit_access=? WHERE id=?", (1 if enabled else 0, user_id))
            self.db.conn.commit()
            show_toast(self, "Arayüz yetkisi güncellendi", "success")
        except Exception as e:
            show_toast(self, f"Yetki güncellenemedi: {e}", "error")
            self.load_users()

    def _refresh_personnel_map(self):
        self._personnel_map = {}
        try:
            self.db.cursor.execute("SELECT id, name FROM personnel")
            for pid, name in self.db.cursor.fetchall():
                if name:
                    self._personnel_map[str(name).strip().lower()] = pid
        except Exception:
            pass

    def _handle_item_changed(self, item):
        if self._loading or not item:
            return
        row = item.row()
        col = item.column()
        if col not in (1, 2, 3):
            return
        id_item = self.table.item(row, 0)
        if not id_item:
            return
        user_id = id_item.text().strip()
        new_value = (item.text() or "").strip()
        old_value = item.data(Qt.ItemDataRole.UserRole) or ""
        if col in (1, 2) and not new_value:
            self._loading = True
            item.setText(old_value)
            self._loading = False
            return
        if col == 1:
            field = "username"
            value = new_value
        elif col == 2:
            field = "role"
            value = normalize_role(new_value)
        else:
            field = "personnel_id"
            if not new_value or new_value.lower() == "atanmadı":
                value = None
            else:
                if not self._personnel_map:
                    self._refresh_personnel_map()
                value = self._personnel_map.get(new_value.strip().lower())
                if value is None:
                    self._loading = True
                    item.setText(old_value)
                    self._loading = False
                    return
        try:
            valid_user_fields = set(self.db._get_table_columns("users")) if hasattr(self.db, "_get_table_columns") else set()
            if field not in valid_user_fields:
                raise ValueError(f"Invalid users column: {field}")
            self.db.cursor.execute(
                f"UPDATE users SET {self._safe_identifier(field)}=? WHERE id=?",
                (value, user_id),
            )
            self.db.conn.commit()
            item.setData(Qt.ItemDataRole.UserRole, new_value)
        except Exception:
            self._loading = True
            item.setText(old_value)
            self._loading = False
            
    def add_user(self):
        """Open dialog to add new user"""
        if not self._confirm_permission_discard():
            return
        dialog = NewUserDialog(self.db, parent=self)
        if dialog.exec():
            self.user_sort_order.setCurrentIndex(1)
            self.load_users()
    
    def edit_user(self, user_id):
        """Open dialog to edit user"""
        if not self._confirm_permission_discard():
            return
        dialog = UserDialog(self.db, user_id=user_id, parent=self)
        if dialog.exec():
            self.load_users()
    
    def delete_user(self, user_id):
        """Delete user"""
        from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
        dlg = ModernConfirmDialog(
            "Kullanıcı Sil",
            "Bu kullanıcıyı silmek istediğinize emin misiniz",
            self,
            confirm_text="Sil",
            cancel_text="İptal",
            destructive=True,
        )
        if dlg.exec():
            try:
                cols = set(self.db._get_table_columns("users")) if hasattr(self.db, "_get_table_columns") else set()
                active_col = "active" if "active" in cols else ("is_active" if "is_active" in cols else None)
                deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
                deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if deleted_col and deleted_col in cols:
                    self.db.cursor.execute(
                        f"UPDATE users SET {self._safe_identifier(deleted_col)}=1 WHERE id=?",
                        (user_id,),
                    )
                elif active_col and active_col in cols:
                    if "deleted_at" in cols:
                        self.db.cursor.execute(
                            f"UPDATE users SET {self._safe_identifier(active_col)}=0, deleted_at=? WHERE id=?",
                            (deleted_at, user_id),
                        )
                    else:
                        self.db.cursor.execute(
                            f"UPDATE users SET {self._safe_identifier(active_col)}=0 WHERE id=?",
                            (user_id,),
                        )
                else:
                    self.db.cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
                self.db.conn.commit()
                show_toast(self, "Kullanıcı başarıyla silindi.", "success")
                self.load_users()
            except Exception as e:
                show_toast(self, f"Kullanıcı silinemedi: {e}", "error")
