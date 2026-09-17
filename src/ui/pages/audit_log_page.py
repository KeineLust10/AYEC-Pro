# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QFrame, QHBoxLayout, QPushButton, QTabWidget, QScrollArea)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QAction
from src.utils.theme_colors import theme_qss, qc, tc
from src.utils.audit_logger import get_audit_logger
from src.utils.logger import logger
from src.ui.widgets.empty_state import EmptyState

class AuditLogPage(QWidget):
    """Sistem Günlükleri (Audit Log) Sayfası"""
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.audit_logger = get_audit_logger(db)
        self.setup_ui()
        
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tab_main = QWidget()
        self.setup_main_tab()
        self.tabs.addTab(self.tab_main, "🛡️ Sistem Günlükleri")
        
        # 2. How to Use? Tab
        from src.utils.system_config import SystemConfig
        if SystemConfig.is_feature_active(self.db, "usage_guides"):
            self.tab_guide = QWidget()
            self.setup_usage_guide_tab()
            self.tabs.addTab(self.tab_guide, "❓ Nasıl Kullanılır?")
            
        self.layout.addWidget(self.tabs)
        self.load_logs()

    def setup_main_tab(self):
        layout = QVBoxLayout(self.tab_main)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Main Background
        self.tab_main.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.tab_main.setStyleSheet(theme_qss("background-color: @surface_alt;"))

        # Card Container
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(theme_qss("""
            #Card {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 16px;
            }
        """))
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(15)
        
        # Header Box
        header_lay = QHBoxLayout()
        header = QLabel("🛡️ SİSTEM VE GÜVENLİK GÜNLÜĞÜ")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.setStyleSheet(theme_qss("color: @text; padding-bottom: 5px; border: none;"))
        header_lay.addWidget(header)
        header_lay.addStretch()
        
        self.btn_refresh = QPushButton("🔄 Listeyi Yenile")
        self.btn_refresh.setFixedSize(160, 40)
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface; color: @accent; border: 1px solid @accent; border-radius: 10px; font-weight: bold;
            }
            QPushButton:hover { background-color: @selection_bg; }
        """))
        self.btn_refresh.clicked.connect(self.load_logs)
        header_lay.addWidget(self.btn_refresh)
        
        card_layout.addLayout(header_lay)
        
        sub_header = QLabel("Uygulama genelinde yapılan kritik işlemler ve güvenlik kayıtları")
        sub_header.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px; border: none;"))
        card_layout.addWidget(sub_header)
        
        # Log Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Zaman", "Kullanıcı", "Tablo", "İşlem", "Detaylar"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        
        self.table.setStyleSheet(theme_qss("""
            QTableWidget {
                background: @surface; border: 1px solid @border; border-radius: 10px; gridline-color: transparent; font-size: 13px; color: @text;
            }
            QTableWidget::item { padding: 12px; border-bottom: 1px solid @surface_alt; }
            QHeaderView::section { background-color: @surface_alt; color: @text_muted; font-weight: 800; padding: 10px; border: none; border-bottom: 1px solid @border; }
        """))
        card_layout.addWidget(self.table)
        self.empty_state = EmptyState("Henüz günlük yok", "Sistem ve güvenlik hareketlerine ait kayıt bulunamadı.", parent=self)
        self.empty_state.hide()
        card_layout.addWidget(self.empty_state)
        layout.addWidget(card)

    def setup_usage_guide_tab(self):
        from src.utils.design_system import DesignTokens
        layout = QVBoxLayout(self.tab_guide)
        layout.setContentsMargins(40, 40, 40, 40)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setSpacing(20)
        
        guide_text = f"""
        <h1 style='color: {tc("accent")};'>🛡️ Sistem Günlükleri Kullanım Kılavuzu</h1>
        <p style='font-size: 14px; color: {tc("text")};'>Uygulama genelinde yapılan tüm kritik işlemler burada kayıt altına alınır.</p>
        
        <h3 style='color: {tc("accent")};'>📋 İzlenen İşlemler</h3>
        <ul style='color: {tc("text")}; line-height: 1.6;'>
            <li><b>Giriş/Çıkış:</b> Kullanıcıların sisteme giriş ve çıkış zamanları.</li>
            <li><b>Veri Değişiklikleri:</b> Stok ekleme, müşteri silme veya kasa hareketleri.</li>
            <li><b>Sistem Ayarları:</b> Genel konfigürasyon değişiklikleri.</li>
            <li><b>Hatalar:</b> Sistem tarafında oluşan kritik çalışma zamanı hataları.</li>
        </ul>
        """
        
        lbl = QLabel(guide_text)
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        cl.addWidget(lbl)
        cl.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Refresh Timer (Anlık takip için)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_logs)
        self.timer.start(10000) # 10 saniyede bir yenile
        
        self.load_logs()
        self._apply_dark_mode_if_needed()
        
    def load_logs(self):
        """Gerçek log verilerini veritabanından çeker"""
        try:
            self.table.setRowCount(0)
            logs = self.audit_logger.get_recent_activity(limit=100)
            has_logs = bool(logs)
            self.table.setVisible(has_logs)
            self.empty_state.setVisible(not has_logs)
            if not logs:
                return

            self.table.setRowCount(len(logs))
            for r, log in enumerate(logs):
                # audit_logs schema: id(0), user_id(1), table_name(2), action(3), details(4), created_at(5)
                
                # Zaman
                time_item = QTableWidgetItem(str(log[5]))
                self.table.setItem(r, 0, time_item)
                
                # Kullanıcı
                user_item = QTableWidgetItem(str(log[1]))
                user_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.table.setItem(r, 1, user_item)
                
                # Tablo
                tab_item = QTableWidgetItem(str(log[2] or "SİSTEM").upper())
                self.table.setItem(r, 2, tab_item)
                
                # İşlem
                action = str(log[3]).upper()
                act_item = QTableWidgetItem(action)
                act_item.setFont(QFont("Segoe UI", 9, QFont.Weight.ExtraBold))
                
                if not getattr(self, "_dark_mode", False):
                    if "LOGIN" in action or "INSERT" in action:
                        act_item.setForeground(qc("success"))
                    elif "DELETE" in action:
                        act_item.setForeground(qc("danger"))
                    elif "UPDATE" in action:
                        act_item.setForeground(qc("warning"))
                    else:
                        act_item.setForeground(qc("accent"))
                
                self.table.setItem(r, 3, act_item)
                
                # Detaylar
                det_item = QTableWidgetItem(str(log[4]))
                self.table.setItem(r, 4, det_item)
                
                if getattr(self, "_dark_mode", False):
                    for it in (time_item, user_item, tab_item, act_item, det_item):
                        it.setForeground(qc("surface_alt"))

            self.table.resizeColumnsToContents()
            self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
            
        except Exception as e:
            logger.error(f"AuditLogPage data load error: {e}")
    
    def _apply_dark_mode_if_needed(self):
        # ThemeManager now handles dark/light transitions globally.
        # Keep page-specific override disabled to avoid mixed "zebra" rendering.
        self._dark_mode = False


