# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                             QPushButton, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal
from src.utils.theme_colors import theme_qss, tc, qc
from PyQt6.QtGui import QColor, QFont, QCursor

class KPICard(QFrame):
    """
    Modern KPI Card with Title, Value, Icon and optional Trend.
    Used for showing big metrics like Revenue, Open Jobs, etc.
    """
    clicked = pyqtSignal()

    def __init__(self, title, value, icon_text, color=tc("accent"), trend=None, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setObjectName("KPICard")
        self.setToolTip(f"{title} detaylarını görmek için tıklayın")
        self.setStatusTip(f"{title} verisi: {value}")
        
        # We use a very light background and no border for intentional minimalism
        self.setStyleSheet(theme_qss("#KPICard { border: none; background: transparent; }"))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)

        # Bespoke Layout: Value first, then Title and Icon in a row
        self.lbl_value = QLabel(str(value))
        self.lbl_value.setObjectName("KPIValue")
        self.lbl_value.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        layout.addWidget(self.lbl_value)

        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)
        
        self.lbl_icon = QLabel(icon_text)
        self.lbl_icon.setFont(QFont("Segoe UI Emoji", 14))
        footer_layout.addWidget(self.lbl_icon)

        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setObjectName("KPITitle")
        self.lbl_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet(theme_qss("letter-spacing: 1.2px; opacity: 0.7;"))
        footer_layout.addWidget(self.lbl_title)
        
        footer_layout.addStretch()
        
        if trend:
            self.lbl_trend = QLabel(trend)
            self.lbl_trend.setStyleSheet(theme_qss(f"color: {'@success' if '+' in trend else '@danger'}; font-weight: bold; font-size: 10px; background: rgba(0,0,0,0.05); padding: 2px 6px; border-radius: 4px;"))
            footer_layout.addWidget(self.lbl_trend)
            
        layout.addLayout(footer_layout)

    def mousePressEvent(self, event):
        self.clicked.emit()

class QuickActionTile(QPushButton):
    """
    Modern Action Tile for common tasks.
    """
    def __init__(self, title, icon, color=tc("accent"), parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedSize(160, 120)
        self.setObjectName("QuickActionTile")
        self.setToolTip(f"{title} sayfasını aç")
        self.setStatusTip(f"{title} işlemini başlatır")
        self.setStyleSheet(theme_qss("#QuickActionTile { border: none; background: transparent; }"))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_icon = QLabel(icon)
        self.lbl_icon.setFont(QFont("Segoe UI Emoji", 26))
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setStyleSheet(theme_qss("background: transparent; color: inherit;"))
        layout.addWidget(self.lbl_icon)
        
        self.lbl_text = QLabel(title)
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_text.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_text.setWordWrap(True)
        self.lbl_text.setStyleSheet(theme_qss("background: transparent; color: inherit; opacity: 0.8;"))
        layout.addWidget(self.lbl_text)

class ServiceStatusCard(QFrame):
    """
    Service Status Card showing device count by status.
    Clickable to filter Kanban board.
    """
    clicked = pyqtSignal(str)  # status name
    
    def __init__(self, status, count, icon, color=tc("accent"), parent=None):
        super().__init__(parent)
        self.status = status
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setObjectName("ServiceStatusCard")
        self.setToolTip(f"{status} durumundaki cihazları görmek için tıklayın")
        self.setStatusTip(f"{count} cihaz {status} durumunda")
        
        # Modern card styling
        self.setStyleSheet(theme_qss(f"""
            #ServiceStatusCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {color}, stop:1 {self._darken_color(color)});
                border-radius: 12px;
                border: none;
            }}
            #ServiceStatusCard:hover {{
                background: {color};
            }}
        """))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        
        # Icon
        lbl_icon = QLabel(icon)
        lbl_icon.setFont(QFont("Segoe UI Emoji", 24))
        lbl_icon.setStyleSheet(theme_qss("color: white; background: transparent;"))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_icon)
        
        # Count
        lbl_count = QLabel(str(count))
        lbl_count.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        lbl_count.setStyleSheet(theme_qss("color: white; background: transparent;"))
        lbl_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_count)
        
        # Status name
        lbl_status = QLabel(status.upper())
        lbl_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_status.setStyleSheet(theme_qss("color: rgba(255,255,255,0.9); background: transparent; letter-spacing: 1px;"))
        lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_status.setWordWrap(True)
        layout.addWidget(lbl_status)
    
    def _darken_color(self, hex_color):
        """Darken a hex color by 10%."""
        color = QColor(hex_color)
        h, s, v, a = color.getHsv()
        color.setHsv(h, s, int(v * 0.9), a)
        return color.name()
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.status)

class MiniChartWidget(QFrame):
    """
    Custom-drawn performance chart (7-day bars).
    No external libraries needed.
    """
    def __init__(self, data=None, color=tc("accent"), parent=None):
        super().__init__(parent)
        self.data = data or [10, 25, 15, 30, 20, 45, 35] # Default mock data
        self.color = color
        self.setMinimumHeight(150)
        self.setObjectName("MiniChartWidget")
        self.setStyleSheet(theme_qss("background: transparent; border-radius: 15px; border: 1px solid transparent;"))
        
    def setData(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QBrush, QPen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        margin = 30
        
        if not self.data: return
        
        max_val = max(self.data) if max(self.data) > 0 else 1
        bar_count = len(self.data)
        bar_spacing = 15
        bar_width = (width - 2*margin - (bar_count-1)*bar_spacing) / bar_count
        
        # Draw Axis (Subtle)
        axis_color = qc("border")
        text_color = qc("text_muted")

        painter.setPen(QPen(axis_color, 1))
        painter.drawLine(margin, height-margin, width-margin, height-margin)
        
        for i, val in enumerate(self.data):
            bar_height = (val / max_val) * (height - 2*margin)
            x = margin + i * (bar_width + bar_spacing)
            y = height - margin - bar_height
            
            # Bar
            painter.setBrush(QBrush(QColor(self.color)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(bar_width), int(bar_height), 5, 5)
            
            # Value Text
            painter.setPen(QPen(text_color))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(int(x), int(y-18), int(bar_width), 15, Qt.AlignmentFlag.AlignCenter, str(val))
            
            # X-Axis Labels (Day names if possible, but for now 1-7)
            painter.drawText(int(x), int(height-margin+5), int(bar_width), 15, Qt.AlignmentFlag.AlignCenter, str(i+1))

class AgendaItem(QFrame):
    """
    Item for the Dashboard Agenda list.
    """
    def __init__(self, time, title, subtitle, color=tc("accent"), parent=None):
        super().__init__(parent)
        self.setObjectName("AgendaItem")
        self.setStyleSheet(theme_qss(f"""
            #AgendaItem {{
                background-color: transparent;
                border-left: 4px solid {color};
            }}
        """))
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        
        # Time Column
        time_vbox = QVBoxLayout()
        lbl_time = QLabel(time)
        lbl_time.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_time.setStyleSheet(theme_qss("color: @text; border: none;"))
        time_vbox.addWidget(lbl_time)
        layout.addLayout(time_vbox)
        
        layout.addSpacing(15)
        
        # Content Column
        content_vbox = QVBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet(theme_qss("color: @text; border: none;"))
        content_vbox.addWidget(lbl_title)
        
        lbl_sub = QLabel(subtitle)
        lbl_sub.setFont(QFont("Segoe UI", 9))
        lbl_sub.setStyleSheet(theme_qss("color: @disabled_text; border: none;"))
        content_vbox.addWidget(lbl_sub)
        
        layout.addLayout(content_vbox)
        layout.addStretch()

class QuickActionBadge(QWidget):
    clicked = pyqtSignal()

    def __init__(self, title, icon_text, count=-1, color=tc("text")):
        super().__init__()
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 5, 0, 5)
        
        # Parent this frame to the badge widget so it cannot flash as an
        # independent top-level helper window during Dashboard construction.
        self.frame = QFrame(self)
        self.frame.setObjectName("QuickActionBadgeFrame")
        self.frame.setStyleSheet(theme_qss(f"background: transparent; border-radius: 10px; border: 1px solid transparent;"))
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 10))
        self.frame.setGraphicsEffect(shadow)

        # Layout
        content_layout = QVBoxLayout(self.frame)
        content_layout.setSpacing(2)
        
        # Icon Group
        icon_row = QHBoxLayout()
        self.lbl_icon = QLabel(icon_text)
        self.lbl_icon.setFont(QFont("Segoe UI Emoji", 20))
        self.lbl_icon.setStyleSheet(theme_qss("background: transparent;"))
        icon_row.addWidget(self.lbl_icon)
        
        if count >= 0:
            self.lbl_badge = QLabel(str(count))
            self.lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_badge.setStyleSheet(theme_qss(f"""
                background-color: {color}; color: white; border-radius: 10px; 
                padding: 2px 6px; font-size: 9px; font-weight: bold;
            """))
            icon_row.addStretch()
            icon_row.addWidget(self.lbl_badge)
        
        content_layout.addLayout(icon_row)
        
        # Title
        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet(theme_qss("border: none; color: @text;"))
        self.lbl_title.setWordWrap(True)
        content_layout.addWidget(self.lbl_title)
        
        main_layout.addWidget(self.frame)

    def mousePressEvent(self, event):
        self.clicked.emit()

class TableActionButtons(QWidget):
    def __init__(self, row_index, callback_map):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        
        actions = [
            ("ℹ️", "Detay", "info"),
            ("⚙️", "İşlem", "process"),
            ("👤", "Müşteri", "customer"),
            ("💬", "SMS/Mail", "contact"),
            ("🖨️", "Yazdır", "print"),
            ("❌", "Sil", "delete")
        ]
        
        colors = {
            "info": tc("warning"), "process": tc("success"), "customer": tc("text"),
            "contact": tc("accent_hover"), "print": tc("warning"), "delete": tc("danger")
        }

        for icon, tooltip, key in actions:
            btn = QPushButton(icon)
            btn.setFixedSize(28, 28)
            btn.setToolTip(tooltip)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            bg = colors.get(key, tc("text_muted"))
            btn.setStyleSheet(theme_qss(f"""
                QPushButton {{
                    background-color: {bg};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                }}
                QPushButton:hover {{ background-color: rgba(255,255,255,0.8); color: black; }}
            """))
            if key in callback_map:
                btn.clicked.connect(lambda checked, k=key, r=row_index: callback_map[k](r))
            layout.addWidget(btn)
