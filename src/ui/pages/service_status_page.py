# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QFrame, QHBoxLayout, QPushButton, QGridLayout, QGraphicsDropShadowEffect, QFileDialog, QLineEdit, QComboBox, QCheckBox, QStyledItemDelegate, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QSize, QPoint, QByteArray, QDate
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QGradient
from datetime import datetime
import socket
import threading
import json
import logging
import csv
from http.server import HTTPServer, BaseHTTPRequestHandler
from src.utils.theme_colors import theme_qss, tc, qc
from src.utils.audit_logger import get_audit_logger
from src.ui.widgets.loaner_summary_visuals import LoanerMetricIcon
from src.ui.widgets.service_flow_chart import ServiceFlowChart
from src.ui.pages._dashboard_utils import render_svg_icon
from src.utils.design_system import DesignTokens
from src.ui.widgets.modern_inputs import ModernComboBox

logger = logging.getLogger("AYECProLogger")

class StatusDateDelegate(QStyledItemDelegate):
    def displayText(self, value, locale):
        text = str(value)
        if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-":
            return text[:8] + "\n" + text[8:10]
        return super().displayText(value, locale)

# --- UTILS ---
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# --- BROADCAST SERVER ---
class BroadcastHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/data":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            data = self.server.app_instance.get_broadcast_data()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = self.server.app_instance.get_broadcast_html()
            self.wfile.write(html.encode('utf-8'))
    def log_message(self, format, *args): return

# --- WIDGETS ---
class MarqueeLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.original_text = text
        self.scroll_pos = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_scroll)
        self.timer.start(30)
        self.setFont(QFont(DesignTokens.FONT_NAME, 22, QFont.Weight.Bold))
        self.setStyleSheet(theme_qss("color: @text; background: transparent;"))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Yazıyı değiştirmek için çift tıklayın")

    def update_scroll(self):
        self.scroll_pos += 1
        metrics = self.fontMetrics()
        text_width = metrics.horizontalAdvance(self.original_text + "          ")
        if self.scroll_pos >= max(1, text_width):
            self.scroll_pos = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = self.fontMetrics()
        text = self.original_text + "          "
        text_width = metrics.horizontalAdvance(text)
        
        x = -self.scroll_pos
        while x < self.width():
            painter.drawText(x, 0, text_width, self.height(), Qt.AlignmentFlag.AlignVCenter, text)
            x += text_width

    def setText(self, text):
        self.original_text = text
        self.scroll_pos = 0
        self.update()

    def mouseDoubleClickEvent(self, event):
        from src.ui.widgets.modern_dialog import ModernInputDialog
        dlg = ModernInputDialog("Duyuru Ayarı", "Kayıcı Alt Yazı Metni", self.original_text, self)
        if dlg.exec():
            new_text = dlg.get_text()
            if new_text:
                self.setText(new_text)
                # Find DB
                p = self.parent()
                while p:
                    if hasattr(p, 'db'):
                        p.db.set_setting("marquee_text", new_text)
                        break
                    p = p.parent()

class ModernInfoCard(QFrame):
    def __init__(self, title, value, icon, color, sparkline_points=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)
        self.setStyleSheet(theme_qss(f"""
            QFrame {{
                background-color: @surface;
                border-radius: 12px;
                border-left: 5px solid {color};
                border-right: 1px solid @border;
                border-top: 1px solid @border;
                border-bottom: 1px solid @border;
            }}
            QFrame:hover {{
                border-left: 5px solid {color};
                background-color: @surface_alt;
            }}
        """))
        
        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow_color = qc("text")
        shadow_color.setAlpha(20)
        shadow.setColor(shadow_color)
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Icon Box
        icon_box = QLabel(icon)
        icon_box.setFixedSize(50, 50)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setStyleSheet(theme_qss(f"""
            background-color: {color}20;
            color: {color};
            font-size: 24px;
            border-radius: 12px;
        """))
        layout.addWidget(icon_box)
        
        # Text Info
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.lbl_val = QLabel(str(value))
        self.lbl_val.setStyleSheet(theme_qss("font-size: 24px; font-weight: 800; color: @text; border:none; background:transparent;"))
        
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet(theme_qss("font-size: 11px; font-weight: 700; color: @text_muted; border:none; background:transparent; letter-spacing: 0.5px;"))
        
        text_layout.addWidget(self.lbl_val)
        text_layout.addWidget(self.lbl_title)
        layout.addLayout(text_layout)
        
        layout.addStretch()
        
        # Sparkline (Simulated SVG)
        if sparkline_points:
             pass # Future implementation of real chart
        
        # Static decorative sparkline for visual appeal
        spark_lbl = QLabel()
        spark_lbl.setFixedSize(60, 40)
        spark_lbl.setStyleSheet(theme_qss("border:none; background:transparent;"))
        # Simple SVG Polyline
        svg = f"""<svg viewBox="0 0 60 40" fill="none" stroke="{color}" stroke-width="2">
            <polyline points="0,30 10,25 20,35 30,15 40,20 50,5 60,15" />
        </svg>"""
        # Render SVG to pixmap
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPixmap
        renderer = QSvgRenderer(QByteArray(svg.encode()))
        pm = QPixmap(60, 40)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        renderer.render(p)
        p.end()
        spark_lbl.setPixmap(pm)
        layout.addWidget(spark_lbl)

    def update_value(self, val):
        self.lbl_val.setText(str(val))

class ServiceStatusPage(QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.audit_logger = get_audit_logger(db)
        self.httpd = None
        self.broadcast_thread = None
        self.is_broadcasting = False
        self.cards = {}
        self.status_page = 0
        self.status_page_size = 7
        self.setup_ui()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not hasattr(self, "table"):
            return
        page_size = max(6, min(14, (self.height() - 430) // 48))
        if self.status_page_size != page_size:
            self.status_page_size = page_size
            self.status_page = 0
            self._apply_status_filters()

    def setup_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)
        self.setObjectName("ServiceStatusCanvas")
        self.setStyleSheet(theme_qss("QWidget#ServiceStatusCanvas{background:@background;}"))

        # --- HEADER ---
        page_header = QFrame()
        page_header.setFixedHeight(88)
        page_header.setObjectName("StatusHeader")
        page_header.setStyleSheet(theme_qss("QFrame#StatusHeader{background:@background;border:none;}QLabel{background:transparent;border:none;}"))
        phl = QHBoxLayout(page_header)
        phl.setContentsMargins(12, 0, 12, 0)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        breadcrumb = QLabel("SERVIS OPERASYON / CANLI IZLEME / AYEC-STATUS-WALL")
        breadcrumb.setStyleSheet(theme_qss("font-size:10px; font-weight:800; color:@text_muted;"))
        breadcrumb.setWordWrap(True)
        title_box.addWidget(breadcrumb)
        lbl_head = QLabel("Durum Paneli")
        lbl_head.setStyleSheet(theme_qss("font-size: 20px; font-weight: 800; color: @text;"))
        lbl_sub = QLabel(
            "Atolye ve saha servis operasyonlarinin anlik hareket akisi, "
            "cihaz teslimat durumlari ve AI asistan bildirimleri"
        )
        lbl_sub.setStyleSheet(theme_qss("font-size: 13px; color: @text_muted;"))
        lbl_sub.setWordWrap(True)
        title_line = QHBoxLayout()
        title_line.addWidget(lbl_head)
        title_box.addWidget(lbl_sub)
        phl.addLayout(title_box, 1)
        live_badge = QLabel("CANLI AKIS (30S OTOMATIK YENILEME)")
        live_badge.setStyleSheet(theme_qss("background: @success_bg; color: @success; border-radius: 10px; padding: 6px 10px; font-weight: 800;"))
        title_line.addWidget(live_badge)
        title_line.addStretch()
        title_box.insertLayout(1, title_line)

        # Broadcast Buttons
        self.btn_share = QPushButton("📡 Ekranı Yayınla")
        self.btn_share.setFixedSize(160, 40)
        self.btn_share.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_share.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent; color: @selection_text; border-radius: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: @accent_hover; }
        """))
        self.btn_share.clicked.connect(self.toggle_broadcast)

        self.btn_manual = QPushButton("❓ Yardım")
        self.btn_manual.setFixedSize(100, 40)
        self.btn_manual.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface; color: @text_muted; border: 1px solid @border; border-radius: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: @surface_alt; }
        """))
        self.btn_manual.clicked.connect(self.show_manual)

        self.lbl_timer = QLabel("30s")
        self.lbl_timer.setFixedSize(60, 40)
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_timer.setStyleSheet(theme_qss("background: @finance_surface_alt; color: @finance_text; border: 1px solid @finance_outline; border-radius: 4px; font-weight: bold;"))

        self.root_layout.addWidget(page_header)

        action_bar = QHBoxLayout()
        action_bar.setContentsMargins(12, 0, 12, 6)
        action_bar.setSpacing(8)
        self.lbl_timer.setFixedSize(74, 28)
        action_bar.addWidget(self.lbl_timer)
        self.btn_share.setFixedSize(212, 28)
        self.btn_share.setText("Ekrani Yayinla (TV / Duvar Modu)")
        action_bar.addWidget(self.btn_share)
        self.btn_manual.setFixedSize(64, 28)
        self.btn_status_refresh = QPushButton("Yenile")
        self.btn_status_refresh.setStyleSheet(theme_qss(
            "QPushButton{background:@accent;color:@selection_text;border-radius:7px;padding:7px 14px;font-weight:700;}"
            "QPushButton:hover{background:@accent_hover;}"
        ))
        self.btn_status_refresh.clicked.connect(self.load_data)
        action_bar.addWidget(self.btn_status_refresh)
        self.btn_status_filter = QPushButton("Filtrele")
        self.btn_status_filter.setCheckable(True)
        self.btn_status_filter.setStyleSheet(theme_qss(
            "QPushButton{background:@surface_alt;color:@text;border:1px solid @border;border-radius:7px;padding:7px 14px;font-weight:700;}"
            "QPushButton:checked{background:@accent;color:@selection_text;}"
        ))
        self.btn_status_filter.toggled.connect(self.toggle_critical_filter)
        action_bar.addWidget(self.btn_status_filter)
        self.btn_status_export = QPushButton("Disa Aktar")
        self.btn_status_export.setStyleSheet(theme_qss(
            "QPushButton{background:@surface_alt;color:@text;border:1px solid @border;border-radius:7px;padding:7px 14px;font-weight:700;}"
            "QPushButton:hover{background:@selection_bg;color:@accent;}"
        ))
        self.btn_status_export.clicked.connect(self.export_status_snapshot)
        action_bar.addWidget(self.btn_status_export)
        action_hint = QLabel("Canli servis hareketleri ve parca uyarilari")
        action_hint.setStyleSheet(theme_qss("color:@text_muted;font-size:11px;"))
        action_bar.addWidget(action_hint)
        action_bar.addStretch()
        action_bar.addWidget(self.btn_manual)
        for control in (self.lbl_timer, self.btn_share, self.btn_manual, self.btn_status_refresh, self.btn_status_filter, self.btn_status_export):
            control.setFixedHeight(28)
            if isinstance(control, QPushButton):
                control.setStyleSheet(theme_qss(
                    "QPushButton{background:@finance_surface_alt;color:@finance_text;border:1px solid @finance_outline;"
                    "border-radius:4px;padding:0 8px;min-height:24px;font-size:11px;font-weight:700;}"
                    "QPushButton:checked{background:@accent;color:@selection_text;}"
                    "QPushButton:hover{border-color:@accent;}"
                ))
        self.btn_share.setStyleSheet(theme_qss("QPushButton{background:@accent;color:@selection_text;border:none;border-radius:4px;padding:0 8px;min-height:24px;font-size:11px;font-weight:700;}"))
        self.root_layout.addLayout(action_bar)

        # --- SCROLLABLE CONTENT ---
        # Only use scroll if height is an issue, generally TV screens are fixed. 
        # But let's use a widget container for layout flexibility.
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 8)
        content_layout.setSpacing(12)

        status_kpis = QHBoxLayout()
        status_kpis.setSpacing(10)
        self.status_kpi_values = []
        for title_text, value_text, accent in [
            ("Bugunku Islem Hacmi", "0 Cihaz", "@finance_primary"),
            ("Atolye Doluluk Orani", "%0", "@finance_secondary"),
            ("Kritik SLA ve Parca Uyarisi", "0 Cihaz Bekliyor", "@finance_tertiary"),
            ("Ortalama Tamir Suresi", "0 Gun", "@finance_primary"),
        ]:
            card = QFrame()
            card.setObjectName("StatusMetricCard")
            card.setFixedHeight(96)
            card.setStyleSheet(theme_qss("QFrame#StatusMetricCard{background:@finance_surface;border:1px solid @finance_outline;border-radius:6px;}QLabel{background:transparent;border:none;}"))
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)
            title_label = QLabel(title_text)
            title_label.setWordWrap(True)
            title_label.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px; font-weight: 800; border: none;"))
            value_label = QLabel(value_text)
            value_label.setStyleSheet(theme_qss(f"color: {accent}; font-size: 24px; font-weight: 800; border: none;"))
            card_heading = QHBoxLayout()
            card_heading.addWidget(title_label, 1)
            card_heading.addWidget(LoanerMetricIcon(("clipboard", "warehouse", "warning", "clock")[len(self.status_kpi_values)], accent.lstrip("@")))
            card_layout.addLayout(card_heading)
            card_layout.addWidget(value_label)
            self.status_kpi_values.append(value_label)
            status_kpis.addWidget(card, 1)
        content_layout.addLayout(status_kpis)

        # --- TABLE ---
        table_frame = QFrame()
        table_frame.setObjectName("StatusTableFrame")
        table_frame.setStyleSheet(theme_qss("QFrame#StatusTableFrame{background:@finance_surface;border:none;border-radius:6px;}QLabel{border:none;background:transparent;}"))
        # Shadow
        shadow_t = QGraphicsDropShadowEffect()
        shadow_t.setBlurRadius(20)
        shadow_t_color = qc("text")
        shadow_t_color.setAlpha(15)
        shadow_t.setColor(shadow_t_color)
        shadow_t.setOffset(0, 5)
        # Keep the status table crisp across light and dark themes.
        table_frame.setGraphicsEffect(None)
        
        tl = QVBoxLayout(table_frame)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(4)
        
        # Table Header custom
        lbl_tbl = QLabel("Son Servis Hareketleri")
        lbl_tbl.setFixedHeight(36)
        lbl_tbl.setStyleSheet(theme_qss("font-size:14px;font-weight:700;color:@finance_text;padding:6px 10px;border:none;"))

        self.status_filter_category = "all"
        self.status_filter_buttons = {}
        status_filters = QHBoxLayout()
        status_filters.setContentsMargins(0, 0, 8, 0)
        status_filters.setSpacing(4)
        status_filters.addWidget(lbl_tbl, 1)
        for key, label in (("all", "T\u00fcm"), ("delivered", "Teslim"), ("parts", "Par\u00e7a Bekleyen"), ("active", "\u0130\u015flemde")):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setChecked(key == "all")
            button.setFixedHeight(26)
            button.setStyleSheet(theme_qss(
                "QPushButton { background: @surface_alt; color: @text_muted; border: 1px solid @border; "
                "border-radius: 4px; padding: 0 6px; min-height:22px;font-size:10px; } "
                "QPushButton:checked { background: @accent; color: @selection_text; border-color: @accent; }"
            ))
            button.clicked.connect(lambda _checked=False, value=key: self.set_status_category(value))
            status_filters.addWidget(button)
            self.status_filter_buttons[key] = button
        tl.addLayout(status_filters)
        search_row = QHBoxLayout()
        search_row.setContentsMargins(10, 0, 10, 0)
        self.status_search = QLineEdit()
        self.status_search.setPlaceholderText("\u0130\u015f emri no, m\u00fc\u015fteri, seri no ara...")
        self.status_search.setClearButtonEnabled(True)
        self.status_search.textChanged.connect(self._status_filter_changed)
        search_row.addWidget(self.status_search, 1)
        self.status_sort = ModernComboBox()
        self.status_sort.setFixedHeight(30)
        self.status_sort.setStyleSheet(theme_qss(
            "QComboBox{background:@finance_surface_alt;color:@finance_text;"
            "border:1px solid @finance_outline;border-radius:4px;padding:0 8px;"
            "min-height:28px;max-height:28px;font-size:11px;}"
        ))
        self.status_sort.set_reference_chevron()
        self.status_sort.addItem("Kabul Tarihi (En Yeni)", "newest")
        self.status_sort.addItem("Kabul Tarihi (En Eski)", "oldest")
        self.status_sort.currentIndexChanged.connect(self._status_filter_changed)
        search_row.addWidget(self.status_sort)
        tl.addLayout(search_row)

        self.table = QTableWidget()
        cols = ["TAKIP NO", "M\u00dc\u015eTER\u0130", "CIHAZ / MODEL", "DURUM", "G\u0130R\u0130\u015e", "HEDEF TAR\u0130H", "\u00d6NCEL\u0130K", "\u0130\u015eLEMLER", "TESL\u0130M"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for column, width in {
            0: 130, 1: 120, 3: 100, 4: 105, 5: 105, 6: 72, 7: 96,
        }.items():
            self.table.setColumnWidth(column, width)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.moveSection(header.visualIndex(8), 5)
        self.table.setColumnWidth(8, 105)
        self.table.setColumnHidden(5, True)
        self.status_estimated_toggle = QCheckBox("Hedef Tarih")
        self.status_estimated_toggle.setToolTip("Eski aray\u00fczdeki tahmini teslim tarihini g\u00f6ster")
        self.status_estimated_toggle.toggled.connect(lambda enabled: self.table.setColumnHidden(5, not enabled))
        search_row.addWidget(self.status_estimated_toggle)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.status_date_delegate = StatusDateDelegate(self.table)
        for column in (4, 5, 8):
            self.table.setItemDelegateForColumn(column, self.status_date_delegate)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setMinimumHeight(240)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setStyleSheet(theme_qss("""
            QTableWidget { border: none; background: @finance_surface; alternate-background-color: @background; font-size: 11px; }
            QTableWidget::item { padding: 6px 4px; border:none; color: @finance_text; }
            QTableWidget::item:alternate { background:@background; }
            QHeaderView::section { background: @background; color: @finance_text_muted; font-weight:700; border:none; padding:8px 4px; font-size:10px; }
        """))
        tl.addWidget(self.table, 1)
        pager = QHBoxLayout()
        pager.setContentsMargins(10, 0, 10, 0)
        self.status_result_label = QLabel()
        pager.addWidget(self.status_result_label, 1)
        self.status_previous = QPushButton("<")
        self.status_next = QPushButton(">")
        self.status_page_label = QLabel("1 / 1")
        for button in (self.status_previous, self.status_next):
            button.setFixedSize(28, 26)
            button.setStyleSheet(theme_qss("QPushButton{background:@finance_surface_alt;color:@finance_text;border:1px solid @finance_outline;border-radius:4px;padding:0;min-height:22px;}"))
        self.status_previous.clicked.connect(lambda: self._change_status_page(-1))
        self.status_next.clicked.connect(lambda: self._change_status_page(1))
        pager.addWidget(self.status_previous)
        pager.addWidget(self.status_page_label)
        pager.addWidget(self.status_next)
        tl.addLayout(pager)
        flow_frame = QFrame()
        flow_frame.setObjectName("StatusFlowFrame")
        flow_layout = QVBoxLayout(flow_frame)
        flow_title = QLabel("Gunluk Cihaz Akis Yogunlugu (Saatlik)")
        flow_layout.addWidget(flow_title)
        self.status_flow_note = QLabel()
        flow_layout.addWidget(self.status_flow_note)
        self.status_flow_chart = ServiceFlowChart()
        flow_layout.addWidget(self.status_flow_chart)
        self.status_flow_frame = flow_frame
        flow_frame.hide()
        left_workspace = QVBoxLayout()
        left_workspace.setContentsMargins(0, 0, 0, 0)
        left_workspace.setSpacing(8)
        table_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_workspace.addWidget(table_frame, 3)
        workspace = QHBoxLayout()
        workspace.setSpacing(0)
        workspace.addLayout(left_workspace, 1)

        side_panel = QFrame()
        side_panel.setMinimumWidth(270)
        side_panel.setObjectName("StatusAssistant")
        side_panel.setStyleSheet(theme_qss("QFrame#StatusAssistant { background:@background;border:none;border-radius:4px; } QLabel { border:none; }"))
        side_groups = QVBoxLayout(side_panel)
        side_groups.setContentsMargins(0, 0, 0, 0)
        side_groups.setSpacing(8)
        assistant_group = QFrame()
        assistant_group.setObjectName("StatusAssistantGroup")
        assistant_group.setStyleSheet(theme_qss("QFrame#StatusAssistantGroup{background:@finance_surface;border:none;border-top:3px solid @finance_tertiary;border-radius:4px;}"))
        # Keep the operational appointment and stock actions out of this panel;
        # the assistant card crowds the live service table at desktop widths.
        assistant_group.setVisible(False)
        side_groups.addWidget(assistant_group)
        side_layout = QVBoxLayout(assistant_group)
        side_layout.setContentsMargins(10, 8, 10, 8)
        side_layout.setSpacing(8)
        side_title = QLabel("AYEC Servis Asistani")
        side_title.setStyleSheet(theme_qss("color: @text; font-size: 15px; font-weight: 800;"))
        side_layout.addWidget(side_title)
        notice = QLabel("Randevu kay\u0131tlar\u0131 okunuyor...")
        self.status_appointment_notice = notice
        notice.setTextFormat(Qt.TextFormat.PlainText)
        notice.setWordWrap(True)
        notice.setStyleSheet(theme_qss("color: @text_muted; background: @surface_alt; padding: 12px; border-radius: 8px;"))
        side_layout.addWidget(notice)
        self.status_appointment_button = QPushButton("Randevulara Git")
        self.status_appointment_button.clicked.connect(lambda: self._navigate_status_page(30))
        side_layout.addWidget(self.status_appointment_button)
        stock_notice = QLabel("Stok kay\u0131tlar\u0131 okunuyor...")
        self.status_stock_notice = stock_notice
        stock_notice.setTextFormat(Qt.TextFormat.PlainText)
        stock_notice.setWordWrap(True)
        stock_notice.setStyleSheet(theme_qss("color: @warning; background: @surface_alt; padding: 12px; border-radius: 8px;"))
        side_layout.addWidget(stock_notice)
        self.status_stock_button = QPushButton("Stok Listesini A\u00e7")
        self.status_stock_button.clicked.connect(lambda: self._navigate_status_page(50))
        side_layout.addWidget(self.status_stock_button)
        technician_group = QFrame()
        technician_group.setObjectName("StatusTechnicianGroup")
        technician_group.setStyleSheet(theme_qss("QFrame#StatusTechnicianGroup{background:@finance_surface;border:none;border-radius:4px;}"))
        side_groups.addWidget(technician_group)
        side_layout = QVBoxLayout(technician_group)
        side_layout.setContentsMargins(10, 8, 10, 8)
        side_layout.setSpacing(8)
        tech_title = QLabel("Teknisyen ve Saha Durumu")
        tech_title.setStyleSheet(theme_qss("color: @text; font-weight: 800;"))
        side_layout.addWidget(tech_title)
        self.status_personnel_layout = QVBoxLayout()
        self.status_personnel_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.addLayout(self.status_personnel_layout)
        self.status_personnel_button = QPushButton("T\u00fcm Teknisyenleri G\u00f6r")
        self.status_personnel_button.clicked.connect(lambda: self._navigate_status_page(10))
        side_layout.addWidget(self.status_personnel_button)
        for button in (self.status_appointment_button, self.status_stock_button, self.status_personnel_button):
            button.setEnabled(callable(getattr(self.main_window, "on_menu_click", None)))
            button.setFixedHeight(28)
            button.setStyleSheet(theme_qss("QPushButton{background:@finance_surface_alt;color:@finance_text;border:1px solid @finance_outline;border-radius:4px;padding:0 6px;min-height:24px;font-size:11px;font-weight:700;}QPushButton:disabled{color:@disabled_text;}QPushButton:hover{border-color:@accent;}"))
        camera_group = QFrame()
        camera_group.setObjectName("StatusCameraGroup")
        camera_group.setStyleSheet(theme_qss("QFrame#StatusCameraGroup{background:@finance_surface;border:none;border-radius:4px;}"))
        side_groups.addWidget(camera_group)
        side_layout = QVBoxLayout(camera_group)
        side_layout.setContentsMargins(10, 8, 10, 8)
        side_layout.setSpacing(8)
        camera_title = QLabel("At\u00f6lye Kameras\u0131 / BA\u011eLI DE\u011e\u0130L")
        camera_title.setStyleSheet(theme_qss("color: @text; font-weight: 800;"))
        side_layout.addWidget(camera_title)
        camera_preview = QLabel("Kamera kayna\u011f\u0131 yap\u0131land\u0131r\u0131lmam\u0131\u015f.\nCanl\u0131 g\u00f6r\u00fcnt\u00fc mevcut de\u011fil.")
        camera_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        camera_preview.setMinimumHeight(84)
        camera_preview.setStyleSheet(theme_qss("color: @text_muted; background: @finance_surface; border: 1px solid @finance_outline; border-radius: 4px; font-size: 11px; font-weight: 700;"))
        side_layout.addWidget(camera_preview)
        side_groups.addStretch()
        side_panel.hide()
        content_layout.addLayout(workspace, 1)
        content_layout.addWidget(side_panel, 0)
        content_layout.addWidget(flow_frame, 0)

        self.root_layout.addWidget(content, 1)

        # --- FOOTER (Marquee) ---
        footer_frame = QFrame()
        footer_frame.setFixedHeight(26)
        footer_frame.setStyleSheet(theme_qss("background-color: @surface_alt; border-top: 1px solid @border;"))
        flLayout = QVBoxLayout(footer_frame)
        flLayout.setContentsMargins(0, 0, 0, 0)
        
        initial_text = self.db.get_setting("marquee_text", "AYEC Pro Servis Yonetim Sistemi  |  Canli durum akisi")
        self.marquee = QLabel(initial_text, self)
        self.marquee.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.marquee.setFont(QFont(DesignTokens.FONT_NAME, 11, QFont.Weight.Bold))
        self.marquee.setStyleSheet(theme_qss("color: @text; background: transparent;"))
        
        flLayout.addWidget(self.marquee)
        self.root_layout.addWidget(footer_frame)

        # Timer
        self.timer_counter = 30
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.on_timer_tick)
        self.refresh_timer.start(1000)

        # Gecikmeli Başlatma (UI donmasını önlemek için)
        QTimer.singleShot(150, self.load_data)

    def on_timer_tick(self):
        self.timer_counter -= 1
        self.lbl_timer.setText(f"{self.timer_counter}s")
        if self.timer_counter <= 0:
            self.load_data()
            self.timer_counter = 30

    def load_data(self):
        self._refresh_status_assistant()
        self._refresh_status_flow()
        # Update Table
        self.table.setRowCount(0)
        try:
            services = self.db.cursor.execute("""
                SELECT tracking_no, customer_name, device_brand, device_model, status, entry_date, estimated_date, urgency,
                       COALESCE(NULLIF(delivered_at,''),exit_date)
                FROM devices 
                WHERE COALESCE(is_archived,0)=0 AND COALESCE(is_deleted,0)=0
                ORDER BY id DESC LIMIT 15
            """).fetchall()

            self._update_status_metrics()

            for row_idx, data in enumerate(services):
                self.table.insertRow(row_idx)
                # data: tracking, name, brand, model, status, entry, est, urgency
                tracking_no = str(data[0] or "-")
                c_name = data[1] or "-"
                
                device = f"{data[2] or ''} {data[3] or ''}".strip()
                status = (data[4] or "Bekliyor").upper()
                entry = data[5]
                est = data[6] or "-"
                urgency = (data[7] or "Normal").upper()
                
                # Items
                tracking_item = QTableWidgetItem(tracking_no)
                record_font = QFont(DesignTokens.MONO_FONT_NAME)
                record_font.setPixelSize(11)
                record_font.setBold(True)
                tracking_item.setFont(record_font)
                tracking_item.setToolTip(tracking_no)
                self.table.setItem(row_idx, 0, tracking_item)
                self.table.setItem(row_idx, 1, QTableWidgetItem(c_name))
                self.table.setItem(row_idx, 2, QTableWidgetItem(device))
                
                # Status with Color
                item_status = QTableWidgetItem(status)
                item_status.setFont(QFont(DesignTokens.FONT_NAME, 9, QFont.Weight.Bold))
                
                color = tc("text_muted")
                if "TAMİR" in status or "SERVİS" in status: color = tc("accent")
                elif "HAZIR" in status or "TAMAM" in status: color = tc("success")
                elif "BEKLİYOR" in status: color = tc("warning")
                elif "PARÇA" in status: color = tc("warning")
                elif "İPTAL" in status: color = tc("danger")
                
                item_status.setForeground(QColor(color))
                self.table.setItem(row_idx, 3, item_status)
                
                self.table.setItem(row_idx, 4, QTableWidgetItem(str(entry)))
                self.table.setItem(row_idx, 5, QTableWidgetItem(str(est)))
                self.table.setItem(row_idx, 8, QTableWidgetItem(str(data[8] or "-")))
                for column in (4, 5, 8):
                    item = self.table.item(row_idx, column)
                    item.setFont(record_font)
                    item.setToolTip(item.text())
                
                item_urgency = QTableWidgetItem(urgency)
                if "ACİL" in urgency: item_urgency.setForeground(qc("danger"))
                self.table.setItem(row_idx, 6, item_urgency)

                action = self._make_status_actions(tracking_no)
                self.table.setCellWidget(row_idx, 7, action)

            self._apply_status_filters()
                
        except Exception as e:
            logger.error("Service status table refresh error: %s", e)

    def _refresh_status_flow(self):
        counts = [0] * 24
        unknown = 0
        try:
            rows = self.db.cursor.execute(
                "SELECT entry_date FROM devices WHERE SUBSTR(entry_date,1,10)=? "
                "AND COALESCE(is_deleted,0)=0 AND COALESCE(is_archived,0)=0",
                (QDate.currentDate().toString("yyyy-MM-dd"),)).fetchall()
            for row in rows:
                value = str(row[0] or "")
                try:
                    if len(value) < 16:
                        raise ValueError("Admission time missing")
                    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    counts[moment.hour] += 1
                except ValueError:
                    unknown += 1
            if any(counts):
                peak = counts.index(max(counts))
                text = "Zirve: {:02d}:00 ({} cihaz)".format(peak, counts[peak])
            else:
                text = "Saat bilgili kabul kayd\u0131 yok"
            if unknown:
                text += " | {} kay\u0131tta saat yok".format(unknown)
            self.status_flow_note.setText(text)
        except Exception as error:
            self.status_flow_note.setText("Ak\u0131\u015f kay\u0131tlar\u0131 okunamad\u0131")
            self.status_flow_note.setToolTip(str(error))
        self.status_flow_chart.set_counts(counts)
        self.status_flow_chart.setVisible(False)

    def _navigate_status_page(self, page_id):
        navigator = getattr(self.main_window, "on_menu_click", None)
        if callable(navigator):
            navigator(page_id)

    def _status_table_columns(self, table):
        if table not in ("appointments", "parts", "personnel"):
            raise ValueError("Unsupported status data source")
        return {record[1] for record in self.db.cursor.execute("PRAGMA table_info({})".format(table)).fetchall()}

    def _refresh_status_assistant(self):
        try:
            columns = self._status_table_columns("appointments")
            if not {"date", "time", "customer_name", "description", "status"}.issubset(columns):
                raise ValueError("Randevu veri alanlar\u0131 mevcut de\u011fil.")
            deleted = " AND COALESCE(is_deleted,0)=0" if "is_deleted" in columns else ""
            records = self.db.cursor.execute(
                "SELECT time,customer_name,description,status FROM appointments WHERE SUBSTR(date,1,10)=?"
                + deleted + " ORDER BY time", (QDate.currentDate().toString("yyyy-MM-dd"),)).fetchall()
            pending = [row for row in records if str(row[3] or "").upper().replace("\u0130", "I") not in
                       ("TAMAMLANDI", "IPTAL", "COMPLETED", "CANCELLED", "CANCELED")]
            text = "Bug\u00fcn {} bekleyen randevu var.".format(len(pending))
            if pending:
                text += "\n{} | {}\n{}".format(pending[0][0] or "-", pending[0][1] or "-", pending[0][2] or "")
            self.status_appointment_notice.setText(text)
        except Exception as error:
            self.status_appointment_notice.setText("Randevu kay\u0131tlar\u0131 okunamad\u0131.")
            self.status_appointment_notice.setToolTip(str(error))
        try:
            columns = self._status_table_columns("parts")
            name = "name" if "name" in columns else "part_name"
            if not {name, "stock", "min_stock"}.issubset(columns):
                raise ValueError("Stok veri alanlar\u0131 mevcut de\u011fil.")
            deleted = " AND COALESCE(is_deleted,0)=0" if "is_deleted" in columns else ""
            rows = self.db.cursor.execute(
                "SELECT {},stock,min_stock FROM parts WHERE COALESCE(min_stock,0)>0 "
                "AND COALESCE(stock,0)<=min_stock".format(name) + deleted + " ORDER BY stock").fetchall()
            lines = ["{} | Stok: {} / E\u015fik: {}".format(*row) for row in rows]
            self.status_stock_notice.setText("Kritik stok: {} \u00fcr\u00fcn\n{}".format(len(rows), "\n".join(lines[:2]))
                                            if rows else "Kritik stok uyar\u0131s\u0131 bulunmuyor.")
            self.status_stock_notice.setToolTip("\n".join(lines))
        except Exception as error:
            self.status_stock_notice.setText("Stok kay\u0131tlar\u0131 okunamad\u0131.")
            self.status_stock_notice.setToolTip(str(error))
        while self.status_personnel_layout.count():
            item = self.status_personnel_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        personnel = []
        try:
            columns = self._status_table_columns("personnel")
            if not {"name", "role"}.issubset(columns):
                raise ValueError("Personel veri alanlar\u0131 mevcut de\u011fil.")
            state = "COALESCE(status,'')" if "status" in columns else "''"
            where = " WHERE COALESCE(is_deleted,0)=0" if "is_deleted" in columns else " WHERE 1=1"
            if "is_active" in columns:
                where += " AND COALESCE(is_active,1)=1"
            rows = self.db.cursor.execute("SELECT name,role," + state + " FROM personnel" + where + " ORDER BY name").fetchall()
            personnel = [row for row in rows if any(word in str(row[1] or "").casefold().replace("\u0131", "i").replace("\u0307", "")
                                                    for word in ("teknisyen", "saha", "destek", "personel"))]
        except Exception as error:
            logger.warning("Status personnel source could not be read: %s", error)
        for name, role, state in personnel[:3]:
            label = QLabel("{}\n{} | {}".format(name, role, state or "Durum bildirilmemi\u015f"))
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            label.setStyleSheet(theme_qss("color:@finance_text_muted;background:@finance_surface_alt;padding:8px;border:none;border-radius:4px;"))
            self.status_personnel_layout.addWidget(label)
        if not personnel:
            self.status_personnel_layout.addWidget(QLabel("Teknisyen kayd\u0131 bulunmuyor veya okunamad\u0131."))

    @staticmethod
    def _status_record_date(value):
        text = str(value or "")[:10]
        date = QDate.fromString(text, "yyyy-MM-dd")
        return date if date.isValid() else QDate.fromString(text, "dd.MM.yyyy")

    def _update_status_metrics(self):
        for label in self.status_kpi_values:
            label.setText("-")
        try:
            records = self.db.cursor.execute(
                "SELECT entry_date, COALESCE(NULLIF(delivered_at,''),exit_date), status, urgency "
                "FROM devices WHERE COALESCE(is_deleted,0)=0 AND COALESCE(is_archived,0)=0"
            ).fetchall()
            today = QDate.currentDate()
            volume, occupying, critical = 0, 0, 0
            durations = []
            for entry, delivery, status, urgency in records:
                start = self._status_record_date(entry)
                end = self._status_record_date(delivery)
                normalized = str(status or "").upper().replace("\u0130", "I").replace("\u00c7", "C")
                delivered = self._status_is_delivered(normalized)
                cancelled = "IPTAL" in normalized or "IADE" in normalized
                volume += int(start == today or (delivered and end == today))
                occupying += int(not delivered and not cancelled)
                urgent = str(urgency or "").upper().replace("\u0130", "I")
                critical += int(not delivered and not cancelled and ("PARCA" in normalized or "ACIL" in urgent))
                if delivered and start.isValid() and end.isValid() and end >= start:
                    durations.append(start.daysTo(end))
            self.status_kpi_values[0].setText("{} Cihaz".format(volume))
            self.status_kpi_values[0].setToolTip("Bug\u00fcn kabul edilen veya teslim edilen cihazlar")
            self.status_kpi_values[2].setText("{} Cihaz Bekliyor".format(critical))
            if durations:
                self.status_kpi_values[3].setText("{:.1f} G\u00fcn".format(sum(durations) / len(durations)))
            self.status_kpi_values[3].setToolTip("{} ge\u00e7erli kabul / teslim tarihli servis".format(len(durations)))
            try:
                capacity = float(self.db.get_setting("workshop_capacity", "") or 0)
            except (ValueError, TypeError, AttributeError):
                capacity = 0
            if capacity > 0:
                self.status_kpi_values[1].setText("%{}".format(round(occupying * 100 / capacity)))
                self.status_kpi_values[1].setToolTip("{} / {} cihaz kapasitesi".format(occupying, capacity))
            else:
                self.status_kpi_values[1].setToolTip("At\u00f6lye kapasitesi tan\u0131mlanmam\u0131\u015f. At\u00f6lyede: {} cihaz".format(occupying))
        except Exception as error:
            logger.warning("Status metrics could not be read: %s", error)

    def _service_action_handler(self, method):
        pages = getattr(self.main_window, "pages", {}) or {}
        candidates = pages.values() if hasattr(pages, "values") else pages
        for page in candidates:
            handler = getattr(page, method, None)
            if callable(handler):
                return handler
        handler = getattr(self.main_window, method, None)
        return handler if callable(handler) else None

    def _make_status_actions(self, tracking_no):
        cell = QWidget()
        cell.setStyleSheet("background:transparent;border:none;")
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(2)
        paths = {
            "view": '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="2.5"/>',
            "print": '<path d="M6 9V3h12v6"/><path d="M6 18H4V9h16v9h-2"/><path d="M6 14h12v7H6z"/>',
            "sms": '<path d="M3 3h18v14H8l-5 4V3Z"/><path d="M7 7h10M7 11h7"/>',
        }
        for name, caption in (("view", "Servis kaydini ac"), ("print", "Servis fisi yazdir"), ("sms", "SMS gonder")):
            button = QPushButton()
            button.setObjectName("status_" + name)
            button.setToolTip(caption)
            button.setFixedSize(24, 26)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(theme_qss(
                "QPushButton{background:transparent;color:@finance_text_muted;border:none;"
                "border-radius:4px;padding:0;min-height:22px;}"
                "QPushButton:hover{background:@finance_surface_alt;}"
            ))
            svg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">' + paths[name] + '</svg>'
            button.setIcon(render_svg_icon(svg, tc("finance_text_muted"), size=15))
            button.setIconSize(QSize(15, 15))
            if name == "view":
                button.clicked.connect(lambda checked=False, ref=tracking_no: self._open_service_detail(ref))
            else:
                method = "print_service" if name == "print" else "open_context_menu_action"
                button.setEnabled(self._service_action_handler(method) is not None)
                button.clicked.connect(lambda checked=False, ref=tracking_no, kind=name: self._invoke_status_action(kind, ref))
            layout.addWidget(button)
        return cell

    def _invoke_status_action(self, kind, tracking_no):
        method = "print_service" if kind == "print" else "open_context_menu_action"
        handler = self._service_action_handler(method)
        if handler is not None:
            if kind == "print":
                handler(tracking_no)
            else:
                handler("sms", tracking_no)

    def _open_service_detail(self, tracking_no):
        pages = getattr(self.main_window, "pages", {}) or {}
        candidates = pages.values() if hasattr(pages, "values") else pages
        for page in candidates:
            opener = getattr(page, "open_device_detail", None)
            if callable(opener):
                opener(tracking_no)
                return
        navigator = getattr(self.main_window, "open_service_list", None)
        if callable(navigator):
            navigator("all")

    def set_status_category(self, category):
        self.status_page = 0
        self.status_filter_category = category if category in self.status_filter_buttons else "all"
        for key, button in self.status_filter_buttons.items():
            button.setChecked(key == self.status_filter_category)
        self._apply_status_filters()

    @staticmethod
    def _status_is_delivered(status):
        normalized = str(status or "").upper().replace("\u0130", "I").replace("\u0131", "I")
        return "TESLIM" in normalized and "HAZIR" not in normalized

    def _apply_status_filters(self):
        if getattr(self, "status_sort", None) is not None:
            self._sort_status_rows()
        category = getattr(self, "status_filter_category", "all")
        critical_only = bool(getattr(self, "btn_status_filter", None) and self.btn_status_filter.isChecked())
        matching = []
        query = getattr(self, "status_search", None)
        query = query.text().strip().casefold() if query is not None else ""
        for row in range(self.table.rowCount()):
            status = self.table.item(row, 3)
            urgency = self.table.item(row, 6)
            status_text = str(status.text() if status else "").upper()
            urgency_text = str(urgency.text() if urgency else "").upper()
            normalized_status = status_text.replace("\u0130", "I").replace("\u00c7", "C")
            delivered = ServiceStatusPage._status_is_delivered(normalized_status)
            parts = "PARCA" in normalized_status
            matches_category = (
                category == "all"
                or (category == "delivered" and delivered)
                or (category == "parts" and parts)
                or (category == "active" and not delivered and not parts)
            )
            haystack = status_text + " " + urgency_text
            normalized_haystack = haystack.replace("\u0130", "I").replace("\u00c7", "C")
            matches_critical = not critical_only or any(
                token in normalized_haystack for token in ("PARCA", "BEKLIYOR", "ACIL")
            )
            matches_query = not query or any(query in (self.table.item(row, column).text().casefold() if self.table.item(row, column) else "") for column in range(self.table.columnCount()))
            if matches_category and matches_critical and matches_query:
                matching.append(row)
        sort = getattr(self, "status_sort", None)
        if sort is not None:
            matching.sort(key=lambda row: (self.table.item(row, 4).text(), self.table.item(row, 0).text()), reverse=sort.currentData() == "newest")
        size = getattr(self, "status_page_size", self.table.rowCount() or 1)
        pages = max(1, (len(matching) + size - 1) // size)
        self.status_page = max(0, min(getattr(self, "status_page", 0), pages - 1))
        start = self.status_page * size
        visible = set(matching[start:start + size])
        self._matching_status_rows = matching
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, row not in visible)
        if hasattr(self, "status_result_label"):
            self.status_result_label.setText("G\u00f6sterilen: {} / {} Kay\u0131t".format(len(visible), len(matching)))
            self.status_page_label.setText("{} / {}".format(self.status_page + 1, pages))
            self.status_previous.setEnabled(self.status_page > 0)
            self.status_next.setEnabled(self.status_page + 1 < pages)

    def _status_filter_changed(self, *_args):
        self.status_page = 0
        self._apply_status_filters()

    def _sort_status_rows(self):
        order = Qt.SortOrder.DescendingOrder if self.status_sort.currentData() == "newest" else Qt.SortOrder.AscendingOrder
        self.table.sortItems(0, order)
        self.table.sortItems(4, order)
        self._sync_status_badges()

    def _sync_status_badges(self):
        for row in range(self.table.rowCount()):
            for column in (3, 6):
                item = self.table.item(row, column)
                if item is None:
                    continue
                text = item.text()
                normalized = text.upper().replace("\u0130", "I").replace("\u00c7", "C")
                if any(word in normalized for word in ("PARCA", "ACIL", "IPTAL")):
                    color = "finance_tertiary"
                    badge_background = "finance_warning_bg"
                elif column == 3 and any(word in normalized for word in ("TESLIM", "TAMAM", "HAZIR")):
                    color = "finance_secondary"
                    badge_background = "finance_success_bg"
                elif column == 3:
                    color = "finance_primary"
                    badge_background = "finance_active_bg"
                else:
                    color = "finance_text_muted"
                    badge_background = "finance_surface_alt"
                cell = QWidget()
                cell.setObjectName("StatusBadgeCell")
                cell.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                background = "background" if row % 2 else "finance_surface"
                cell.setStyleSheet(theme_qss("QWidget#StatusBadgeCell{background:@" + background + ";border:none;padding:0;}"))
                box = QHBoxLayout(cell)
                box.setContentsMargins(4, 0, 4, 0)
                label = QLabel(text)
                label.setTextFormat(Qt.TextFormat.PlainText)
                label.setWordWrap(True)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setFixedHeight(36)
                badge_fill = tc(badge_background, default=tc("finance_surface_alt"))
                label.setStyleSheet(theme_qss("QLabel{background:" + badge_fill + ";color:@" + color + ";border:none;border-radius:4px;padding:0;min-height:36px;max-height:36px;font-size:10px;font-weight:700;}"))
                box.addWidget(label)
                self.table.setCellWidget(row, column, cell)

    def _change_status_page(self, delta):
        self.status_page += delta
        self._apply_status_filters()

    def toggle_critical_filter(self, enabled):
        """Show only waiting/urgent rows while preserving the selected category."""
        self.status_page = 0
        self._apply_status_filters()

    def export_status_snapshot(self):
        path, _ = QFileDialog.getSaveFileName(self, "Durum Panelini Disa Aktar", "ayec_status_snapshot.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow([self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())])
                for row in getattr(self, "_matching_status_rows", range(self.table.rowCount())):
                    writer.writerow([self.table.item(row, col).text() if self.table.item(row, col) else "" for col in range(self.table.columnCount())])
            logger.info("Service status snapshot exported: %s", path)
        except Exception as exc:
            logger.error("Service status snapshot export failed: %s", exc)

    # --- BROADCAST METHODS (Kept similar functionality) ---
    def toggle_broadcast(self):
        # Implementation of broadcast toggling
        if self.is_broadcasting:
            self.stop_server()
            self.btn_share.setText("📡 Ekranı Yayınla")
            self.btn_share.setStyleSheet(theme_qss("background-color: @accent; color: @selection_text; border-radius: 8px; font-weight: bold;"))
            self.is_broadcasting = False
            if hasattr(self.main_window, "toast"): self.main_window.toast.show_toast("Yayın durduruldu.", "info")
        else:
            try:
                ip = get_local_ip()
                port = 8080
                self.httpd = HTTPServer(('', port), BroadcastHandler)
                self.httpd.app_instance = self
                self.broadcast_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
                self.broadcast_thread.start()
                self.is_broadcasting = True
                self.btn_share.setText(f"📡 Yayında: {ip}:{port}")
                self.btn_share.setStyleSheet(theme_qss("background-color: @success; color: @selection_text; border-radius: 8px; font-weight: bold;"))
                
                from PyQt6.QtWidgets import QApplication
                QApplication.clipboard().setText(f"http://{ip}:{port}")
                if hasattr(self.main_window, "toast"): self.main_window.toast.show_toast(f"Yayın başladı: http://{ip}:{port}", "success")
            except Exception as e:
                logger.error("Service status broadcast server error: %s", e)

    def stop_server(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd = None

    def get_broadcast_data(self):
        # Allow broadcasting cached table data for performance
        try:
             services = self.db.cursor.execute("""
                SELECT customer_name, device_brand, device_model, status, entry_date 
                FROM devices WHERE is_archived = 0 ORDER BY id DESC LIMIT 20
            """).fetchall()
             res = []
             for s in services:
                 res.append({"customer": s[0], "device": f"{s[1]} {s[2]}", "status": s[3], "date": s[4]})
             return res
        except Exception as e:
             logger.error("Service status broadcast data error: %s", e)
             return []

    def get_broadcast_html(self):
         # Returns simple HTML for TV display
         return f"""
         <html><head><meta charset='utf-8'><title>Servis Ekranı</title>
         <style>body{{font-family:sans-serif;background:{tc("window")};color:{tc("text")};}} table{{width:100%;border-collapse:collapse;}} 
         th,td{{padding:15px;text-align:left;border-bottom:1px solid {tc("border")};}} th{{color:{tc("text_muted")};}} .st{{padding:5px 10px;border-radius:5px;}}
         </style></head><body>
         <h1 style='text-align:center'>🛠️ Servis Durum Ekranı</h1>
         <table><thead><tr><th>Müşteri</th><th>Cihaz</th><th>Durum</th><th>Tarih</th></tr></thead>
         <tbody id='tb'></tbody></table>
         <script>
         async function load(){{
            try{{
                let d = await (await fetch('/data')).json();
                let h=''; d.forEach(x=>h+=`<tr><td>${{x.customer}}</td><td>${{x.device}}</td><td>${{x.status}}</td><td>${{x.date}}</td></tr>`);
                document.getElementById('tb').innerHTML=h;
            }}catch(e){{}}
         }}
         setInterval(load, 5000); load();
         </script></body></html>
         """
    
    def show_manual(self):
        from src.ui.widgets.modern_confirm_dialog import ModernAlertDialog
        ModernAlertDialog(
            "Bilgi",
            "Bu ekranı mağazanızdaki bir TV'ye yansıtabilirsiniz.\n\n'Ekranı Yayınla' butonuna basın ve verilen adresi Smart TV tarayıcısına girin.",
            parent=self,
            ok_text="Tamam",
            variant="info",
        ).exec()

