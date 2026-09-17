# -*- coding: utf-8 -*-

"""
Quick Stats Widget
Gerçek zamanlı istatistikler için dashboard widget'ı
"""
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QFrame, QLabel, QVBoxLayout,
                             QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from src.utils.date_formatter import format_date
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import theme_qss
import logging

logger = logging.getLogger("AYECProLogger")

class QuickStatsWidget(QWidget):
    """Hızlı istatistik widget'ı - Dashboard için"""
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setup_ui()
        
        # Auto-refresh every 30 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_stats)
        self.timer.start(30_000)  # 30 seconds
        
        # Initial load
        self.refresh_stats()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Container
        container = QFrame()
        container.setObjectName("StatsCard")
        container.setStyleSheet(theme_qss("""
            #StatsCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 @accent, stop:1 @accent_hover);
                border-radius: 12px;
                padding: 20px;
            }
        """))
        
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(15)
        
        # Header
        header = QLabel("📊 BUGÜNKÜ İSTATİSTİKLER")
        header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        header.setStyleSheet("color: white; letter-spacing: 1px;")
        container_layout.addWidget(header)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background: rgba(255, 255, 255, 0.3); height: 1px; border: none;")
        container_layout.addWidget(divider)
        
        # Stats Grid
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        # Stat 1: İşlemler
        self.lbl_transactions = self.create_stat_label("0", "İşlem")
        stats_layout.addWidget(self.lbl_transactions)
        
        # Stat 2: Gelir
        self.lbl_revenue = self.create_stat_label(
            CurrencyHelper.format_try_for_display(0, db=self.db, include_try_reference=False),
            "Gelir",
        )
        stats_layout.addWidget(self.lbl_revenue)
        
        container_layout.addLayout(stats_layout)
        
        # Second Row
        stats_layout2 = QHBoxLayout()
        stats_layout2.setSpacing(20)
        
        # Stat 3: Aktif Servisler
        self.lbl_services = self.create_stat_label("0", "Aktif Servis")
        stats_layout2.addWidget(self.lbl_services)
        
        # Stat 4: Yeni Müşteriler
        self.lbl_customers = self.create_stat_label("0", "Yeni Müşteri")
        stats_layout2.addWidget(self.lbl_customers)
        
        container_layout.addLayout(stats_layout2)
        
        # Last Update
        self.lbl_update = QLabel("Son güncelleme: --:--")
        self.lbl_update.setFont(QFont("Segoe UI", 8))
        self.lbl_update.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        self.lbl_update.setAlignment(Qt.AlignmentFlag.AlignRight)
        container_layout.addWidget(self.lbl_update)
        
        layout.addWidget(container)
    
    def create_stat_label(self, value, label):
        """Create a stat display"""
        widget = QFrame()
        widget_layout = QVBoxLayout(widget)
        widget_layout.setContentsMargins(0, 0, 0, 0)
        widget_layout.setSpacing(5)
        
        # Value
        lbl_value = QLabel(value)
        lbl_value.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        lbl_value.setStyleSheet("color: white;")
        lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget_layout.addWidget(lbl_value)
        
        # Label
        lbl_label = QLabel(label)
        lbl_label.setFont(QFont("Segoe UI", 9))
        lbl_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        lbl_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget_layout.addWidget(lbl_label)
        
        # Store reference to value label
        widget.value_label = lbl_value
        
        return widget
    
    def refresh_stats(self):
        """Refresh statistics from database - FIXED: Handle missing tables gracefully"""
        from datetime import datetime, date
        
        try:
            today = date.today().strftime("%Y-%m-%d")
            
            # 1. Today's Transactions - Safely check if table exists
            transactions = 0
            try:
                self.db.cursor.execute("""
                    SELECT COUNT(*) FROM sqlite_master 
                    WHERE type='table' AND name='transactions'
                """)
                if self.db.cursor.fetchone()[0] > 0:
                    self.db.cursor.execute("""
                        SELECT COUNT(*) FROM transactions 
                        WHERE DATE(created_at) = ?
                    """, (today,))
                    transactions = self.db.cursor.fetchone()[0] or 0
            except Exception as e:
                logger.debug("Quick stats transactions count unavailable: %s", e)
            self.lbl_transactions.value_label.setText(str(transactions))
            
            # 2. Today's Revenue - Transactions table may not exist
            revenue = 0
            self.lbl_revenue.value_label.setText(
                CurrencyHelper.format_try_for_display(revenue, db=self.db, include_try_reference=False)
            )
            
            # 3. Active Services
            services = 0
            try:
                self.db.cursor.execute("""
                    SELECT COUNT(*) FROM devices 
                    WHERE status IN ('Beklemede', 'İşlemde', 'Parça Bekliyor')
                """)
                services = self.db.cursor.fetchone()[0] or 0
            except Exception as e:
                logger.debug("Quick stats active services unavailable: %s", e)
            self.lbl_services.value_label.setText(str(services))
            
            # 4. New Customers (This Week)
            customers = 0
            try:
                self.db.cursor.execute("""
                    SELECT COUNT(*) FROM customers 
                    WHERE DATE(created_at) >= DATE('now', '-7 days')
                """)
                customers = self.db.cursor.fetchone()[0] or 0
            except Exception as e:
                logger.debug("Quick stats customer count unavailable: %s", e)
            self.lbl_customers.value_label.setText(str(customers))
            
            # Update timestamp
            self.lbl_update.setText(f"Son güncelleme: {format_date(datetime.now(), self.db, include_time=True)}")
            
        except Exception as e:
            logger.error("Quick stats refresh error: %s", e)
    
    def stop_timer(self):
        """Stop auto-refresh"""
        if self.timer:
            self.timer.stop()
