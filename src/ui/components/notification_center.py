# -*- coding: utf-8 -*-


from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QScrollArea, 
                             QPushButton, QFrame, QTabWidget, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QIcon, QFont, QColor, QPainter, QPainterPath

from src.utils.theme_colors import theme_qss, tc
from src.utils.design_system import DesignTokens

class NotificationBell(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.count = 0
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Icon Label
        self.icon_label = QLabel("🔔")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet(theme_qss("font-size: 20px; color: @text_muted;"))
        layout.addWidget(self.icon_label)
        
        # Badge Label (Overlay)
        self.badge = QLabel("0", self)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setStyleSheet(theme_qss("""
            background-color: @danger; color: white;
            border-radius: 8px; font-weight: bold; font-size: 10px;
            padding: 2px;
        """))
        self.badge.setFixedSize(16, 16)
        self.badge.move(22, 2)
        self.badge.hide()

        # Shake Animation
        self.shake_timer = QTimer(self)
        self.shake_timer.setInterval(10000) # Every 10 seconds
        self.shake_timer.timeout.connect(self._do_shake)

    def _do_shake(self):
        if self.count <= 0:
            self.shake_timer.stop()
            return
            
        # Quick horizontal shake animation
        self.anim = QPropertyAnimation(self.icon_label, b"pos")
        self.anim.setDuration(500)
        self.anim.setLoopCount(2)
        
        base_pos = self.icon_label.pos()
        x, y = base_pos.x(), base_pos.y()
        
        self.anim.setKeyValueAt(0, base_pos)
        self.anim.setKeyValueAt(0.2, QPoint(x - 3, y))
        self.anim.setKeyValueAt(0.4, QPoint(x + 3, y))
        self.anim.setKeyValueAt(0.6, QPoint(x - 3, y))
        self.anim.setKeyValueAt(0.8, QPoint(x + 3, y))
        self.anim.setKeyValueAt(1, base_pos)
        
        self.anim.start()

    def set_count(self, count):
        self.count = count
        if count > 0:
            txt = "9+" if count > 9 else str(count)
            self.badge.setText(txt)
            self.badge.show()
            self.icon_label.setStyleSheet(theme_qss("font-size: 20px; color: @text;")) # Darker
            if not self.shake_timer.isActive():
                self.shake_timer.start()
        else:
            self.badge.hide()
            self.icon_label.setStyleSheet(theme_qss("font-size: 20px; color: @disabled_text;")) # Grayer
            self.shake_timer.stop()

    def mousePressEvent(self, event):
        self.clicked.emit()

class NotificationCard(QFrame):
    action_triggered = pyqtSignal(str) # link_id

    def __init__(self, n_id, category, title, content, link_id, status, parent=None):
        super().__init__(parent)
        self.link_id = link_id
        
        # Colors
        colors = {
            "Finance": tc("danger"),
            "Stock": tc("warning"),
            "Technical": tc("accent"),
            "System": tc("text_muted")
        }
        accent = colors.get(category, tc("text_muted"))
        
        # Style
        bg_color = tc("surface_alt") if status == 'read' else tc("surface")
        self.setStyleSheet(theme_qss(f"""
            NotificationCard {{
                background-color: {bg_color};
                border-left: 4px solid {accent};
                border-bottom: 1px solid @border;
            }}
            QLabel {{ border: none; background: transparent; }}
        """))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(5)
        
        # Header
        header = QHBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(theme_qss(f"font-weight: bold; color: @selection_text; font-size: 13px;"))
        
        lbl_cat = QLabel(category)
        lbl_cat.setStyleSheet(theme_qss(f"color: {accent}; font-size: 10px; font-weight: 600; text-transform: uppercase;"))
        
        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(lbl_cat)
        layout.addLayout(header)
        
        # Content
        lbl_content = QLabel(content)
        lbl_content.setWordWrap(True)
        lbl_content.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        layout.addWidget(lbl_content)
        
        # Action (if link_id)
        if link_id:
            btn_action = QPushButton("Hızlı Git ›")
            btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_action.setFixedHeight(24)
            btn_action.setStyleSheet(theme_qss(f"""
                QPushButton {{
                    text-align: left; color: {accent}; font-weight: 600; font-size: 11px;
                    background: transparent; border: none; padding: 0;
                }}
                QPushButton:hover {{ text-decoration: underline; }}
            """))
            btn_action.clicked.connect(lambda: self.action_triggered.emit(self.link_id))
            layout.addWidget(btn_action)

class NotificationPanel(QFrame):
    link_triggered = pyqtSignal(str) # Relay signal

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        # Keep the panel open until the bell or an outside area is clicked.
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(360, 500)
        
        self.setStyleSheet(theme_qss("""
            NotificationPanel {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 12px;
            }
        """))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet(theme_qss("border-bottom: 1px solid @border; background: @surface_alt; border-top-left-radius: 12px; border-top-right-radius: 12px;"))
        hl = QHBoxLayout(header)
        hl.setContentsMargins(15, 0, 15, 0)
        
        title = QLabel("Bildirimler")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        
        btn_read_all = QPushButton("Tümünü Okundu Say")
        btn_read_all.setStyleSheet(theme_qss("color: @accent; font-size: 11px; border: none; background: transparent; font-weight: 600;"))
        btn_read_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_read_all.clicked.connect(self.mark_all_read)
        
        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(btn_read_all)
        layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(theme_qss("""
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                min-width: 100px; padding: 8px; color: @text_muted; border-bottom: 2px solid transparent;
            }
            QTabBar::tab:selected {
                color: @accent; border-bottom: 2px solid @accent; font-weight: bold;
            }
        """))
        
        self.active_widget = QWidget()
        self.history_widget = QWidget()
        
        self.tabs.addTab(self.active_widget, "Aktif")
        self.tabs.addTab(self.history_widget, "Geçmiş")
        self.btn_toggle_notifications = QPushButton()
        self.btn_toggle_notifications.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_notifications.setStyleSheet(theme_qss(
            "QPushButton { color: @danger; border: none; background: transparent; "
            "font-size: 10px; font-weight: 600; padding: 6px; }"
            "QPushButton:hover { text-decoration: underline; }"
        ))
        self.btn_toggle_notifications.clicked.connect(self.toggle_notifications)
        self.tabs.setCornerWidget(
            self.btn_toggle_notifications,
            Qt.Corner.TopRightCorner,
        )
        self.update_notification_state()
        layout.addWidget(self.tabs)
        
        # Active Tab Layout
        self.active_layout = QVBoxLayout(self.active_widget)
        self.active_layout.setContentsMargins(0,0,0,0)
        self.active_scroll = QScrollArea()
        self.active_scroll.setWidgetResizable(True)
        self.active_scroll.setStyleSheet(theme_qss("border: none; background: @surface;"))
        self.active_content = QWidget()
        self.active_vbox = QVBoxLayout(self.active_content)
        self.active_vbox.setContentsMargins(0,0,0,0)
        self.active_vbox.setSpacing(0)
        self.active_vbox.addStretch()
        self.active_scroll.setWidget(self.active_content)
        self.active_layout.addWidget(self.active_scroll)
        
        # History Tab Layout (Search + List)
        self.hist_layout = QVBoxLayout(self.history_widget)
        self.hist_layout.setContentsMargins(10,10,10,0)
        
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Geçmişte ara...")
        self.inp_search.setStyleSheet(theme_qss("padding: 6px; border: 1px solid @border; border-radius: 6px;"))
        self.inp_search.textChanged.connect(self.load_history)
        self.hist_layout.addWidget(self.inp_search)
        
        self.hist_scroll = QScrollArea()
        self.hist_scroll.setWidgetResizable(True)
        self.hist_scroll.setStyleSheet(theme_qss("border: none; background: @surface;"))
        self.hist_content = QWidget()
        self.hist_vbox = QVBoxLayout(self.hist_content)
        self.hist_vbox.setContentsMargins(0,0,0,0)
        self.hist_vbox.setSpacing(0)
        self.hist_vbox.addStretch()
        self.hist_scroll.setWidget(self.hist_content)
        self.hist_layout.addWidget(self.hist_scroll)

    def show_at(self, pos):
        self.move(pos.x() - self.width() + 40, pos.y() + 45) # Align slightly left of bell
        self.update_notification_state()
        self.load_active()
        self.show()
        self.activateWindow()
    
    def load_active(self):
        # Clear
        while self.active_vbox.count() > 1: # Keep stretch
            item = self.active_vbox.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        notifications = self.db.get_notifications('unread')
        if not notifications:
            lbl = QLabel("Tüm bildirimler okundu 🎉")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(theme_qss("color: @disabled_text; padding: 20px;"))
            self.active_vbox.insertWidget(0, lbl)
        
        for n in notifications:
            card = NotificationCard(
                n['id'], 
                n['category'], 
                n['title'], 
                n['content'], 
                n['link_id'], 
                'unread'
            )
            card.action_triggered.connect(self._handle_link)
            # Mark as read immediately on display or hover 
            # No, user explicitly marks all ready or we mark individual on click?
            # Let's keep them unread until "Mark All" or Action.
            self.active_vbox.insertWidget(self.active_vbox.count()-1, card)

    def load_history(self):
        query = self.inp_search.text()
        while self.hist_vbox.count() > 1:
            item = self.hist_vbox.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        notifications = self.db.get_notification_history(query, limit=20)
        for n in notifications:
            card = NotificationCard(
                n['id'], 
                n['category'], 
                n['title'], 
                n['content'], 
                n['link_id'], 
                'read' # History is considered read/archived
            )
            card.action_triggered.connect(self._handle_link)
            self.hist_vbox.insertWidget(self.hist_vbox.count()-1, card)
            
    def mark_all_read(self):
        self.db.mark_all_read()
        self.load_active()

    def notifications_enabled(self):
        return str(self.db.get_setting("notifications_enabled", "1")) == "1"

    def update_notification_state(self):
        enabled = self.notifications_enabled()
        self.btn_toggle_notifications.setText(
            "Bildirimleri Kapat" if enabled else "Bildirimleri A\u00e7"
        )

    def toggle_notifications(self):
        enabled = not self.notifications_enabled()
        self.db.set_setting("notifications_enabled", "1" if enabled else "0")
        self.update_notification_state()
        parent = self.parent()
        main_window = getattr(parent, "main_window", None)
        if main_window is not None and hasattr(main_window, "refresh_notification_bell"):
            main_window.refresh_notification_bell()

    def _handle_link(self, link_id):
        self.link_triggered.emit(link_id)
        self.hide()
