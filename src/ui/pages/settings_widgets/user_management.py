# -*- coding: utf-8 -*-

"""
User Management Widget
Kullanıcı yönetimi için ayarlar sayfası widget'ı
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QDialog, QLabel,
                             QLineEdit, QComboBox, QHeaderView, QGroupBox,
                             QGraphicsDropShadowEffect, QFrame, QCheckBox, QScrollArea, QMenu,
                             QAbstractItemView)
from PyQt6.QtCore import Qt
from src.utils.theme_colors import theme_qss, tc, qc
from PyQt6.QtGui import QFont, QColor, QAction
from datetime import datetime
import re
import hashlib
import json
import logging
from src.ui.widgets.toast_notification import show_toast
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.utils.role_utils import is_admin_role, normalize_role
from src.utils.context_menu_settings import is_context_menu_enabled
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
        self.page_size = 20
        self.total_count = 0
        self.search_text = ""
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
        
        # Header
        header = QLabel("👥 Kullanıcı Yönetimi")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Description
        desc = QLabel("Personel için kullanıcı hesapları oluşturun ve yönetin.")
        desc.setStyleSheet(theme_qss("color: @text_muted; margin-bottom: 10px;"))
        layout.addWidget(desc)
        
        filter_layout = QHBoxLayout()
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Kullanıcı adı, e-posta veya personel ara...")
        self.inp_search.textChanged.connect(self.on_search_changed)
        self.cmb_role_filter = QComboBox()
        self.cmb_role_filter.addItems(["Tümü", "Master", "Admin", "Yönetici", "Teknisyen", "Muhasebe", "Personel"])
        self.cmb_role_filter.currentTextChanged.connect(self.on_filter_changed)
        self.cmb_status_filter = QComboBox()
        self.cmb_status_filter.addItems(["Tümü", "Aktif", "Pasif"])
        self.cmb_status_filter.currentTextChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.inp_search)
        filter_layout.addWidget(QLabel("Rol:"))
        filter_layout.addWidget(self.cmb_role_filter)
        filter_layout.addWidget(QLabel("Durum:"))
        filter_layout.addWidget(self.cmb_status_filter)
        layout.addLayout(filter_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("➕ Yeni Kullanıcı")
        self.btn_add.clicked.connect(self.add_user)
        self.btn_add.setStyleSheet(theme_qss("""
            QPushButton {
                background: @accent_hover;
                color: @selection_text;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: @accent_pressed;
            }
        """))
        btn_layout.addWidget(self.btn_add)
        
        self.btn_refresh = QPushButton("🔄 Yenile")
        self.btn_refresh.clicked.connect(self.load_users)
        self.btn_refresh.setStyleSheet(theme_qss("""
            QPushButton {
                background: @text_muted;
                color: @selection_text;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: @text_muted;
            }
        """))
        btn_layout.addWidget(self.btn_refresh)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
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
        
        # Context Menu Policy
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Increase row height
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.table.itemChanged.connect(self._handle_item_changed)
        
        layout.addWidget(self.table)
        
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
    
    def on_search_changed(self, text):
        self.search_text = (text or "").strip()
        self.page = 1
        self.load_users()
    
    def on_filter_changed(self, _):
        self.filter_role = self.cmb_role_filter.currentText() or "Tümü"
        self.filter_status = self.cmb_status_filter.currentText() or "Tümü"
        self.page = 1
        self.load_users()
    
    def change_page(self, delta):
        new_page = self.page + delta
        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        if 1 <= new_page <= total_pages:
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

    def load_users(self):
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
            self.db.cursor.execute("""
                SELECT u.id, u.username, u.role, u.personnel_id, u.created_at,
                       p.name as personnel_name,
                       COALESCE(u.active, 1) AS active,
                       COALESCE(u.interface_edit_access, 0) AS interface_edit
                FROM users u
                LEFT JOIN personnel p ON u.personnel_id = p.id
                {where_sql}
                ORDER BY u.id DESC
                LIMIT ? OFFSET ?
            """.format(where_sql=where_sql), tuple(params + [self.page_size, offset]))
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
            self._update_pagination_label()
        except Exception as e2:
            show_toast(self, f"Kullanıcılar yüklenemedi: {e2}", "error")
        finally:
            self._loading = False
    
    def _toggle_user_active(self, user_id, enabled):
        try:
            self.db.cursor.execute("UPDATE users SET active=? WHERE id=?", (1 if enabled else 0, user_id))
            self.db.conn.commit()
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
        dialog = NewUserDialog(self.db, parent=self)
        if dialog.exec():
            self.load_users()
    
    def edit_user(self, user_id):
        """Open dialog to edit user"""
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
