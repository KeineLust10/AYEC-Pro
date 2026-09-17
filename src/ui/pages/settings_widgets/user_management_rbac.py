# -*- coding: utf-8 -*-

"""
User Management Widget for RBAC Permissions
Allows admin to manage user permissions and roles
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QPushButton, QFrame, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from src.utils.theme_colors import theme_qss, qc, tc
from src.utils.design_system import DesignTokens
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.utils.toast_notification import show_success, show_error
from src.utils.role_utils import is_admin_role, normalize_role


class UserManagementRBACWidget(QWidget):
    """User Management Widget with RBAC Permission Control"""
    
    def __init__(self, db, auth_manager, main_window=None):
        super().__init__()
        self.db = db
        self.auth_manager = auth_manager
        self.main_window = main_window
        self.init_ui()
        self.load_users()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("👥 Kullanıcı Yetkileri Yönetimi")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(header)
        
        desc = QLabel("Kullanıcı arayüz düzenleme yetkilerini buradan yönetebilirsiniz.")
        desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px;"))
        layout.addWidget(desc)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "KULLANICI ADI",
            "ROL",
            "E-POSTA",
            "ARAYÜZ DÜZENLEYEBİLİR",
            "SON GİRİŞ",
            "OTOMATİK GİRİŞ"
        ])
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 180)  # Username
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 100)  # Role
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Email
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 180)  # Interface Edit
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 180)  # Last Login
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, 120)  # Auto Login
        
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # Modern styling
        self.table.setStyleSheet(theme_qss("""
            QTableWidget {
                background-color: @surface;
                border: none;
                border-radius: 12px;
                gridline-color: @surface_alt;
                color: @text;
                outline: none;
            }
            QHeaderView::section {
                background-color: @surface_alt;
                color: @text_muted;
                font-family: 'Segoe UI', 'Segoe UI Emoji';
                padding: 14px 12px;
                border: none;
                border-bottom: 2px solid @border;
                font-weight: 700;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QHeaderView::section:hover {
                background-color: @surface_alt;
                color: @text;
            }
            QTableWidget::item {
                padding: 14px 12px;
                border-bottom: 1px solid @surface_alt;
                color: @text;
                font-size: 12px;
            }
            QTableWidget::item:selected {
                background-color: @selection_bg;
                color: @accent_pressed;
                font-weight: 500;
            }
        """))
        
        layout.addWidget(self.table)
        
        # Info Note
        note = QLabel("💡 Not: Admin kullanıcıları otomatik olarak tüm yetkilere sahiptir.")
        note.setStyleSheet(theme_qss("""
            QLabel {
                color: @accent;
                background-color: @selection_bg;
                padding: 12px;
                border-left: 4px solid @accent;
                border-radius: 6px;
                font-size: 12px;
            }
        """))
        layout.addWidget(note)
    
    def load_users(self):
        """Load all users and populate table"""
        try:
            # Get users with permission info
            self.db.cursor.execute("""
                SELECT 
                    id,
                    username,
                    role,
                    email,
                    interface_edit_access,
                    last_login,
                    auto_login
                FROM users
                ORDER BY role DESC, username ASC
            """)
            users = self.db.cursor.fetchall()
        except Exception as e:
            show_error(self.main_window, f"Kullanıcılar yüklenemedi: {e}")
            users = []
        
        self.table.setRowCount(0)
        
        for i, user in enumerate(users):
            self.table.insertRow(i)
            
            # Username
            username_item = QTableWidgetItem(str(user['username'] or ''))
            username_item.setForeground(qc("text"))
            username_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            self.table.setItem(i, 0, username_item)
            
            # Role with color coding
            role = normalize_role(str(user['role'] or 'user'))
            role_lower = role.lower()
            role_item = QTableWidgetItem(role.upper())
            if is_admin_role(role):
                role_item.setForeground(qc("accent") if role_lower == "master" else qc("danger"))
                role_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            else:
                role_item.setForeground(qc("text_muted"))
            self.table.setItem(i, 1, role_item)
            
            # Email
            email_item = QTableWidgetItem(str(user['email'] or '-'))
            email_item.setForeground(qc("text_muted"))
            self.table.setItem(i, 2, email_item)
            
            # Interface Edit Permission Toggle
            try:
                has_permission = bool(user['interface_edit_access'] if 'interface_edit_access' in user.keys() else 0)
                if is_admin_role(role):
                    has_permission = True  # Admin always has permission
            except Exception:
                has_permission = is_admin_role(role)
            
            toggle = AnimatedToggle(active_color=tc("success"))
            toggle.setChecked(has_permission)
            toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Disable toggle for admin (they always have permission)
            if is_admin_role(role):
                toggle.setEnabled(False)
            else:
                toggle.toggled.connect(
                    lambda checked, uid=user['id']: self.on_permission_toggled(uid, checked)
                )
            
            w_toggle = QWidget()
            lt = QHBoxLayout(w_toggle)
            lt.setContentsMargins(0, 0, 0, 0)
            lt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lt.addWidget(toggle)
            self.table.setCellWidget(i, 3, w_toggle)
            
            # Last Login
            last_login = user['last_login'] or '-'
            if last_login != '-':
                try:
                    # Format datetime if it's a full timestamp
                    from datetime import datetime
                    dt = datetime.fromisoformat(last_login)
                    from src.utils.date_utils import format_datetime_turkish
                    last_login = format_datetime_turkish(dt)
                except Exception:
                    pass
            
            login_item = QTableWidgetItem(last_login)
            login_item.setForeground(qc("disabled_text"))
            login_item.setFont(QFont("Segoe UI", 10))
            self.table.setItem(i, 4, login_item)
            
            # Auto Login
            auto_login = bool(user['auto_login'] if 'auto_login' in user.keys() else 0)
            auto_item = QTableWidgetItem("✓ Aktif" if auto_login else "✗ Pasif")
            auto_item.setForeground(qc("success") if auto_login else qc("disabled_text"))
            auto_item.setFont(QFont("Segoe UI", 10))
            self.table.setItem(i, 5, auto_item)
    
    def on_permission_toggled(self, user_id, granted):
        """Handle permission toggle"""
        try:
            if self.auth_manager.grant_interface_permission(user_id, granted):
                action = "verildi" if granted else "kaldırıldı"
                if self.main_window:
                    self.main_window.show_notification(
                        f"Arayüz düzenleme yetkisi {action}.",
                        "success"
                    )
                else:
                    show_success(self, f"Yetki {action}.")
            else:
                # Revert toggle on failure
                self.load_users()
                show_error(self, "Yetki güncelleme başarısız.")
        except Exception as e:
            self.load_users()
            show_error(self, f"Hata: {e}")
