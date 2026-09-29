# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QFrame, QHBoxLayout, QPushButton, QGridLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer, QSize, QPoint, QByteArray
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QGradient
import socket
import threading
import json
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from src.utils.theme_colors import theme_qss, tc, qc
from src.utils.audit_logger import get_audit_logger

logger = logging.getLogger("AYECProLogger")

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
        self.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
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
        self.setup_ui()

    def setup_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)
        self.setStyleSheet(theme_qss("background-color: @surface_alt;"))

        # --- HEADER ---
        page_header = QFrame()
        page_header.setFixedHeight(70)
        page_header.setStyleSheet(theme_qss("background-color: @surface; border-bottom: 1px solid @border;"))
        phl = QHBoxLayout(page_header)
        phl.setContentsMargins(30, 0, 30, 0)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_head = QLabel("Durum Paneli")
        lbl_head.setStyleSheet(theme_qss("font-size: 20px; font-weight: 800; color: @text;"))
        lbl_sub = QLabel("Anlık iş akışı ve istatistikler")
        lbl_sub.setStyleSheet(theme_qss("font-size: 13px; color: @text_muted;"))
        title_box.addWidget(lbl_head)
        title_box.addWidget(lbl_sub)
        phl.addLayout(title_box)
        phl.addStretch()

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
        phl.addWidget(self.btn_share)

        self.btn_manual = QPushButton("❓ Yardım")
        self.btn_manual.setFixedSize(100, 40)
        self.btn_manual.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface; color: @text_muted; border: 1px solid @border; border-radius: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: @surface_alt; }
        """))
        self.btn_manual.clicked.connect(self.show_manual)
        phl.addWidget(self.btn_manual)

        self.lbl_timer = QLabel("30s")
        self.lbl_timer.setFixedSize(60, 40)
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_timer.setStyleSheet(theme_qss("background: @selection_bg; color: @accent; border-radius: 8px; font-weight: bold;"))
        phl.addWidget(self.lbl_timer)

        self.root_layout.addWidget(page_header)

        # --- SCROLLABLE CONTENT ---
        # Only use scroll if height is an issue, generally TV screens are fixed. 
        # But let's use a widget container for layout flexibility.
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(20)

        # --- TABLE ---
        table_frame = QFrame()
        table_frame.setStyleSheet(theme_qss("background: @surface; border-radius: 15px; border: 1px solid @border;"))
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
        
        # Table Header custom
        lbl_tbl = QLabel("📋 Son Servis Hareketleri")
        lbl_tbl.setStyleSheet(theme_qss("font-size: 16px; font-weight: bold; color: @text; padding: 15px; border-bottom: 1px solid @surface_alt;"))
        tl.addWidget(lbl_tbl)

        self.table = QTableWidget()
        cols = ["MÜŞTERİ", "CİHAZ", "DURUM", "GİRİŞ", "TESLİM", "ÖNCELİK"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme_qss("""
            QTableWidget { border: none; background: transparent; alternate-background-color: @surface_alt; font-size: 13px; }
            QTableWidget::item { padding: 12px 15px; border-bottom: 1px solid @surface_alt; color: @text_muted; }
            QHeaderView::section { background: @surface; color: @text_muted; font-weight: bold; border: none; border-bottom: 2px solid @border; padding: 10px 15px; text-transform: uppercase; font-size: 11px; }
        """))
        tl.addWidget(self.table)
        content_layout.addWidget(table_frame)

        self.root_layout.addWidget(content)

        # --- FOOTER (Marquee) ---
        footer_frame = QFrame()
        footer_frame.setFixedHeight(50)
        footer_frame.setStyleSheet(theme_qss("background-color: @surface_alt; border-top: 1px solid @border;"))
        flLayout = QVBoxLayout(footer_frame)
        flLayout.setContentsMargins(0, 0, 0, 0)
        
        initial_text = self.db.get_setting("marquee_text", "📢 AYEC Pro Servis Yönetim Sistemi - Hoşgeldiniz...")
        self.marquee = MarqueeLabel(initial_text, self)
        self.marquee.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
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
        # Update Table
        self.table.setRowCount(0)
        try:
            services = self.db.cursor.execute("""
                SELECT customer_name, device_brand, device_model, status, entry_date, estimated_date, urgency 
                FROM devices 
                WHERE is_archived = 0
                ORDER BY id DESC LIMIT 15
            """).fetchall()

            for row_idx, data in enumerate(services):
                self.table.insertRow(row_idx)
                # data: name, brand, model, status, entry, est, urgency
                c_name = data[0] or "-"
                
                device = f"{data[1] or ''} {data[2] or ''}".strip()
                status = (data[3] or "Bekliyor").upper()
                entry = data[4]
                est = data[5] or "-"
                urgency = (data[6] or "Normal").upper()
                
                # Items
                self.table.setItem(row_idx, 0, QTableWidgetItem(c_name))
                self.table.setItem(row_idx, 1, QTableWidgetItem(device))
                
                # Status with Color
                item_status = QTableWidgetItem(status)
                item_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                
                color = tc("text_muted")
                if "TAMİR" in status or "SERVİS" in status: color = tc("accent")
                elif "HAZIR" in status or "TAMAM" in status: color = tc("success")
                elif "BEKLİYOR" in status: color = tc("warning")
                elif "PARÇA" in status: color = tc("warning")
                elif "İPTAL" in status: color = tc("danger")
                
                item_status.setForeground(QColor(color))
                self.table.setItem(row_idx, 2, item_status)
                
                self.table.setItem(row_idx, 3, QTableWidgetItem(str(entry)))
                self.table.setItem(row_idx, 4, QTableWidgetItem(str(est)))
                
                item_urgency = QTableWidgetItem(urgency)
                if "ACİL" in urgency: item_urgency.setForeground(qc("danger"))
                self.table.setItem(row_idx, 5, item_urgency)
                
        except Exception as e:
            logger.error("Service status table refresh error: %s", e)

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

