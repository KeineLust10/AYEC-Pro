# -*- coding: utf-8 -*-

from src.utils.design_system import DesignTokens
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QDialog as QtDialog, QLineEdit,
                             QCheckBox, QFormLayout, QGroupBox, QScrollArea, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QAction
from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.message_helper import show_error, show_info, show_warning

class AuthorizationGroupsWidget(QWidget):
    """Yetki Grubu Oluşturma ve Yönetim Modülü"""
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_groups()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        title = QLabel("🔑 Yetki Grupları Yönetimi")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Add Group Button
        btn_add = QPushButton("➕ Yeni Grup Ekle")
        btn_add.setFixedSize(160, 45)
        btn_add.setStyleSheet(DesignTokens.get_button_qss("success"))
        btn_add.clicked.connect(self.add_group)
        header.addWidget(btn_add)
        
        layout.addLayout(header)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Grup Adı", "Açıklama", "Kullanıcı Sayısı", "Düzenle", "Sil"])
        
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        
        # Satır yüksekliğini artır - butonlar için
        self.table.verticalHeader().setDefaultSectionSize(60)
        
        self.table.setStyleSheet(DesignTokens.get_table_qss())
        
        layout.addWidget(self.table)

    def load_groups(self):
        """Yetki gruplarını yükle"""
        self.table.setRowCount(0)
        
        try:
            # Check if auth_groups table exists
            self.db.cursor.execute("""
                SELECT name FROM sqlite_master WHERE type='table' AND name='auth_groups'
            """)
            if not self.db.cursor.fetchone():
                # Create table if not exists
                self.db.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS auth_groups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        permissions TEXT,
                        created_date TEXT
                    )
                """)
                self.db.conn.commit()
                
                # Add default groups
                default_groups = [
                    ("Yönetici", "Tüm yetkilere sahip", "all", "2026-01-04"),
                    ("Teknisyen", "Servis işlemleri ve stok yönetimi", "service,stock", "2026-01-04"),
                    ("Muhasebe", "Finans ve muhasebe işlemleri", "finance,reports", "2026-01-04"),
                    ("Satış", "Müşteri ve satış işlemleri", "customers,sales", "2026-01-04")
                ]
                for group in default_groups:
                    self.db.cursor.execute("""
                        INSERT INTO auth_groups (name, description, permissions, created_date)
                        VALUES (?, ?, ?, ?)
                    """, group)
                self.db.conn.commit()
            
            # Load groups
            self.db.cursor.execute("SELECT id, name, description FROM auth_groups ORDER BY name")
            groups = self.db.cursor.fetchall()
            
            for row_data in groups:
                group_id, name, description = row_data
                row_num = self.table.rowCount()
                self.table.insertRow(row_num)
                
                # Group Name
                name_item = QTableWidgetItem(name)
                name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                name_item.setForeground(QColor("#2c3e50"))
                self.table.setItem(row_num, 0, name_item)
                
                # Description
                desc_item = QTableWidgetItem(description or "")
                desc_item.setFont(QFont("Segoe UI", 10))
                self.table.setItem(row_num, 1, desc_item)
                
                # User Count (placeholder)
                count_item = QTableWidgetItem("0")
                count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_num, 2, count_item)
                
                # Edit Button
                btn_edit = QPushButton("📝 Düzenle")
                btn_edit.setFixedSize(110, 40)  # Büyütüldü
                btn_edit.setStyleSheet(DesignTokens.get_button_qss("warning", size="sm"))
                btn_edit.clicked.connect(lambda checked, gid=group_id: self.edit_group(gid))
                self.table.setCellWidget(row_num, 3, btn_edit)
                
                # Delete Button
                btn_delete = QPushButton("🗑️ Sil")
                btn_delete.setFixedSize(90, 40)  # Büyütüldü
                btn_delete.setStyleSheet(DesignTokens.get_button_qss("destructive", size="sm"))
                btn_delete.clicked.connect(lambda checked, gid=group_id: self.delete_group(gid))
                self.table.setCellWidget(row_num, 4, btn_delete)
                
        except Exception as e:
            show_error(self, f"Gruplar yüklenirken hata oluştu:\n{e}")

    def add_group(self):
        """Yeni yetki grubu ekle"""
        dialog = AddAuthGroupDialog(self.db, self)
        if dialog.exec():
            self.load_groups()

    def edit_group(self, group_id):
        """Yetki grubunu düzenle"""
        dialog = AddAuthGroupDialog(self.db, self, group_id)
        if dialog.exec():
            self.load_groups()

    def delete_group(self, group_id):
        """Yetki grubunu sil"""
# TODO: Convert to custom confirmation dialog
        reply = SimpleConfirmDialog(

            "Silme Onayı",

            "Bu yetki grubunu silmek istediğinizden emin misiniz"

        )
        
        if reply.exec():
            try:
                self.db.cursor.execute("DELETE FROM auth_groups WHERE id=?", (group_id,))
                self.db.conn.commit()
                show_info(self, "Yetki grubu silindi.")
                self.load_groups()
            except Exception as e:
                show_error(self, f"Grup silinirken hata oluştu:\n{e}")


class AddAuthGroupDialog(ModernDialog):
    """Yetki Grubu Ekleme/Düzenleme Dialogu"""
    def __init__(self, db, parent=None, group_id=None):
        super().__init__(parent)
        self.db = db
        self.group_id = group_id
        self.setWindowTitle("Yetki Grubu Düzenle" if group_id else "Yeni Yetki Grubu")
        self.setFixedSize(600, 700)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #2c3e50;
                font-weight: 600;
            }
            QLineEdit, QTextEdit {
                border: 2px solid #dfe6e9;
                border-radius: 6px;
                padding: 10px;
                background-color: white;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
            QCheckBox {
                color: #2c3e50;
                font-size: 10pt;
            }
        """)
        
        self.init_ui()
        
        if group_id:
            self.load_group_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("🔑 " + ("Yetki Grubu Düzenle" if self.group_id else "Yeni Yetki Grubu Oluştur"))
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Group Name
        layout.addWidget(QLabel("Grup Adı *"))
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Örn: Satış Ekibi")
        self.inp_name.setFixedHeight(40)
        layout.addWidget(self.inp_name)
        
        # Description
        layout.addWidget(QLabel("Açıklama"))
        self.inp_description = QLineEdit()
        self.inp_description.setPlaceholderText("Grup hakkında kısa açıklama")
        self.inp_description.setFixedHeight(40)
        layout.addWidget(self.inp_description)
        
        # Permissions
        layout.addWidget(QLabel("Yetkiler"))
        
        # Scroll area for permissions
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        perm_widget = QWidget()
        perm_layout = QVBoxLayout(perm_widget)
        perm_layout.setSpacing(10)
        
        # Permission checkboxes
        self.permissions = {}
        permission_groups = {
            "Genel": ["dashboard", "summary", "settings"],
            "Müşteri İşlemleri": ["customers_view", "customers_add", "customers_edit", "customers_delete"],
            "Servis İşlemleri": ["services_view", "services_add", "services_edit", "services_delete"],
            "Personel İşlemleri": ["personnel_view", "personnel_add", "personnel_edit", "personnel_delete"],
            "Finans İşlemleri": ["finance_view", "finance_add", "finance_edit", "reports"],
            "Stok İşlemleri": ["stock_view", "stock_add", "stock_edit", "stock_delete"],
            "Sistem": ["audit_logs", "system_settings", "backup_restore"]
        }
        
        for group_name, perms in permission_groups.items():
            group_label = QLabel(f"📁 {group_name}")
            group_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            group_label.setStyleSheet("color: #3498db; margin-top: 10px;")
            perm_layout.addWidget(group_label)
            
            for perm in perms:
                chk = QCheckBox(perm.replace("_", " ").title())
                chk.setMinimumHeight(40)  # Minimum yükseklik
                chk.setStyleSheet("""
                    QCheckBox {
                        color: #2c3e50;
                        font-size: 11pt;
                        padding: 8px;
                        spacing: 12px;
                    }
                    QCheckBox::indicator {
                        width: 24px;
                        height: 24px;
                        border: 2px solid #95a5a6;
                        border-radius: 4px;
                        background-color: white;
                    }
                    QCheckBox::indicator:hover {
                        border: 2px solid #3498db;
                        background-color: #ecf0f1;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #27ae60;
                        border: 2px solid #229954;
                        image: url(none);
                    }
                    QCheckBox::indicator:checked:hover {
                        background-color: #2ecc71;
                    }
                    QCheckBox:hover {
                        background-color: #f8f9fa;
                        border-radius: 4px;
                    }
                """)
                self.permissions[perm] = chk
                perm_layout.addWidget(chk)
        
        scroll.setWidget(perm_widget)
        layout.addWidget(scroll)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedSize(120, 45)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("💾 Kaydet")
        btn_save.setFixedSize(120, 45)
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        btn_save.clicked.connect(self.save_group)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def load_group_data(self):
        """Mevcut grup verilerini yükle"""
        try:
            self.db.cursor.execute("""
                SELECT name, description, permissions FROM auth_groups WHERE id=?
            """, (self.group_id,))
            row = self.db.cursor.fetchone()
            
            if row:
                name, description, permissions = row
                self.inp_name.setText(name)
                self.inp_description.setText(description or "")
                
                # Set permissions
                if permissions:
                    perm_list = permissions.split(",")
                    for perm, chk in self.permissions.items():
                        if perm in perm_list or permissions == "all":
                            chk.setChecked(True)
        except Exception as e:
            show_error(self, f"Grup verileri yüklenirken hata oluştu:\n{e}")

    def save_group(self):
        """Grubu kaydet"""
        if not self.inp_name.text().strip():
            show_warning(self, "Lütfen grup adı giriniz.")
            return
        
        # Get selected permissions
        selected_perms = [perm for perm, chk in self.permissions.items() if chk.isChecked()]
        perm_str = ",".join(selected_perms) if selected_perms else ""
        
        try:
            from datetime import datetime
            date_str = datetime.now().strftime("%Y-%m-%d")
            
            if self.group_id:
                # Update
                self.db.cursor.execute("""
                    UPDATE auth_groups 
                    SET name=?, description=?, permissions=?
                    WHERE id=?
                """, (self.inp_name.text().strip(), self.inp_description.text().strip(), perm_str, self.group_id))
            else:
                # Insert
                self.db.cursor.execute("""
                    INSERT INTO auth_groups (name, description, permissions, created_date)
                    VALUES (?, ?, ?, ?)
                """, (self.inp_name.text().strip(), self.inp_description.text().strip(), perm_str, date_str))
            
            self.db.conn.commit()
            show_info(self, "Yetki grubu kaydedildi.")
            self.accept()
        except Exception as e:
            show_error(self, f"Kayıt sırasında hata oluştu:\n{e}")
