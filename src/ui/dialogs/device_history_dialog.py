# -*- coding: utf-8 -*-


from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QAction
from src.utils.toast_notification import show_info, show_error
from src.utils.logger import logger

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens

class DeviceHistoryDialog(ModernDialog):
    def __init__(self, db, serial_no, current_tracking_no, parent=None):
        super().__init__(f"Cihaz Geçmişi - S/N: {serial_no}", parent, width=900, height=600)
        self.db = db
        self.serial_no = serial_no
        self.current_tracking_no = current_tracking_no
        self.setup_content()
        self.load_history()

    def setup_content(self):
        # Header Info Card
        header_card = QFrame()
        header_card.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignTokens.SECONDARY};
                border-radius: 12px;
                border: 1px solid {DesignTokens.BORDER};
            }}
        """)
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(20, 15, 20, 15)
        
        lbl_icon = QLabel("🔍")
        lbl_icon.setFont(QFont(DesignTokens.FONT_FAMILY, 24))
        
        lbl_info = QLabel(f"Bu seri numarasına ({self.serial_no}) ait geçmiş servis kayıtları listelenmektedir.")
        lbl_info.setFont(QFont(DesignTokens.FONT_FAMILY, 11))
        lbl_info.setStyleSheet(f"color: {DesignTokens.PRIMARY};")
        lbl_info.setWordWrap(True)
        
        h_layout.addWidget(lbl_icon)
        h_layout.addWidget(lbl_info, 1)
        self.add_widget(header_card)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Takip No", "Tarih", "Müşteri", "Arıza", "Durum"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Modern Table Styling
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: white;
                border: 1px solid {DesignTokens.BORDER};
                border-radius: 12px;
                gridline-color: transparent;
            }}
            QHeaderView::section {{
                background-color: {DesignTokens.SECONDARY};
                padding: 12px;
                border: none;
                font-weight: bold;
                color: {DesignTokens.MUTED_FOREGROUND};
                border-bottom: 2px solid {DesignTokens.BORDER};
            }}
            QTableWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {DesignTokens.BORDER};
            }}
            QTableWidget::item:selected {{
                background-color: {DesignTokens.ACCENT}15;
                color: {DesignTokens.PRIMARY};
            }}
        """)
        
        self.add_widget(self.table)
        
        # Footer
        self.add_cancel_button("Kapat")


    def load_history(self):
        try:
            # Fetch devices with same serial_no but different tracking_no
            # Table schema assumption based on previous context: 
            # devices table. columns: tracking_no(1), customer_name(2), entry_date(5), fault_desc(18), status(8)
            # We need to SELECT * FROM devices WHERE serial_no = 
            
            # Since I don't know the exact column name for serial_no (it was index 14 in technician panel load),
            # In TechnicianPanel load: self.device[14] is serial_no.
            # I'll use index 14 logic if I fetch all, but cleaner to use WHERE.
            # Assuming column name is 'serial_no'. If not, I'll fetch all and filter in python (safer if column name unknown)
            # But earlier code used `db.get_all_devices` and filtered.
            # Wait, `database.py` likely has `get_devices_by_serial`.
            # If not, I will do a raw query assuming 'serial_no' column exists as seen in previous steps.
            
            # Let's try raw query, if it fails, catch it.
            cursor = self.db.conn.cursor()
            
            # Check column name for serial
            # In TechnicianPanel logs/code: device[14]
            # In create_table: 
            # 469: serial_no TEXT
            
            query = "SELECT tracking_no, entry_date, customer_name, fault_description, status FROM devices WHERE serial_no=? AND tracking_no!=? ORDER BY entry_date DESC"
            cursor.execute(query, (self.serial_no, self.current_tracking_no))
            results = cursor.fetchall()
            
            self.table.setRowCount(0)
            
            if not results:
                show_info(self, "Bu seri numarasına ait başka kayıt bulunamadı.")
                return

            for row_idx, row_data in enumerate(results):
                self.table.insertRow(row_idx)
                # row_data: tracking, date, customer, fault, status
                
                self.table.setItem(row_idx, 0, QTableWidgetItem(str(row_data[0])))
                self.table.setItem(row_idx, 1, QTableWidgetItem(str(row_data[1])))
                self.table.setItem(row_idx, 2, QTableWidgetItem(str(row_data[2])))
                self.table.setItem(row_idx, 3, QTableWidgetItem(str(row_data[3])))
                
                # Status with style
                status_item = QTableWidgetItem(str(row_data[4]))
                status = str(row_data[4])
                if status == "Teslim Edildi":
                    status_item.setForeground(QColor("#27ae60"))
                elif status == "İptal":
                    status_item.setForeground(QColor("#c0392b"))
                else:
                    status_item.setForeground(QColor("#e67e22"))
                
                self.table.setItem(row_idx, 4, status_item)
                
        except Exception as e:
            # If serial_no column doesn't exist or other error, fallback
            logger.error("DeviceHistoryDialog load_history error: %s", e)
            show_error(self, "Geçmiş kayıtlar yüklenirken hata oluştu.")
