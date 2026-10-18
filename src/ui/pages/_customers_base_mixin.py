# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QBoxLayout, QGridLayout, QLayout, QLabel, QPushButton,
    QTableWidget, QHeaderView, QAbstractItemView, QLineEdit, QFrame, QTabWidget, QComboBox, QButtonGroup,
    QMenu, QWidgetAction, QToolButton, QSizePolicy, QProgressBar, QGraphicsDropShadowEffect, QStyledItemDelegate, QStyle
)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QEvent, QSize
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QIcon, QShortcut, QKeySequence, QPalette, QRadialGradient, QPainterPath
from datetime import datetime

from src.ui.pages._customers_visual_theme import (
    customer_theme_color,
    customer_theme_qcolor,
    customer_theme_qss,
)
from src.utils.design_system import DesignTokens
from src.utils.system_config import SystemConfig
from src.ui.widgets.empty_state import EmptyState
from src.ui.widgets.navigation_glyph import navigation_icon


class _CustomerHeroFrame(QFrame):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect().adjusted(1, 1, -1, -1)), 12, 12)
        painter.setClipPath(clip)
        glows = (
            (QPointF(self.width() + 8, -18), 250, QColor(0, 242, 254, 13)),
            (QPointF(-24, self.height() + 16), 210, QColor(59, 130, 246, 20)),
        )
        for center, radius, color in glows:
            gradient = QRadialGradient(center, radius)
            gradient.setColorAt(0.0, color)
            gradient.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.fillRect(self.rect(), gradient)
        painter.end()


class _CustomerRowHoverDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hovered_row = -1

    def set_hovered_row(self, row):
        if self.hovered_row == row:
            return
        self.hovered_row = row
        if self.parent() is not None:
            self.parent().viewport().update()

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        is_hovered = index.row() == self.hovered_row
        if is_hovered:
            painter.save()
            painter.fillRect(option.rect, QColor(59, 130, 246, 10))
            if index.column() == 0:
                painter.fillRect(
                    QRectF(option.rect.left(), option.rect.top(), 2, option.rect.height()),
                    QColor(59, 130, 246),
                )
            painter.restore()
        check_state = index.data(Qt.ItemDataRole.CheckStateRole)
        if index.column() != 0 or check_state is None:
            return
        check_rect = QRectF(
            option.rect.left() + 11,
            option.rect.top() + 21,
            12,
            12,
        )
        painter.save()
        background_color = QColor("#0d121d")
        if option.state & QStyle.StateFlag.State_Selected:
            background_color = option.palette.color(QPalette.ColorRole.Highlight)
        painter.fillRect(
            QRectF(check_rect.left() - 3, check_rect.top() - 3, 18, 18),
            background_color,
        )
        if is_hovered:
            painter.fillRect(
                QRectF(check_rect.left() - 3, check_rect.top() - 3, 18, 18),
                QColor(59, 130, 246, 10),
            )
        checked = check_state in (Qt.CheckState.Checked, Qt.CheckState.Checked.value)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#32363e"), 1))
        painter.setBrush(QColor("#f8fafc") if not checked else QColor("#00f2fe"))
        painter.drawRoundedRect(check_rect, 2, 2)
        if checked:
            painter.setPen(QPen(QColor("#080b11"), 2))
            painter.drawLine(
                QPointF(check_rect.left() + 3, check_rect.top() + 6),
                QPointF(check_rect.left() + 5, check_rect.top() + 8),
            )
            painter.drawLine(
                QPointF(check_rect.left() + 5, check_rect.top() + 8),
                QPointF(check_rect.left() + 9, check_rect.top() + 4),
            )
        painter.restore()


class _CustomerTableHeaderView(QHeaderView):
    def paintSection(self, painter, rect, logical_index):
        super().paintSection(painter, rect, logical_index)
        if logical_index != 0:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.setBrush(QColor("#f8fafc"))
        check_rect = QRectF(rect.left() + 11, rect.top() + 9, 12, 12)
        painter.drawRoundedRect(check_rect, 2, 2)
        painter.restore()


class _CustomerTableWidget(QTableWidget):
    def viewportEvent(self, event):
        if event.type() == QEvent.Type.Leave:
            delegate = self.itemDelegate()
            if isinstance(delegate, _CustomerRowHoverDelegate):
                delegate.set_hovered_row(-1)
        return super().viewportEvent(event)


class CustomersBaseMixin:
    """Base UI and layout logic for CustomersPage."""
    def apply_theme_styles(self):
        self.setStyleSheet(customer_theme_qss(self, "background: @window; color: @text; font-family: 'Inter', 'Segoe UI', Arial;"))
        if hasattr(self, "tabs"):
            self.tabs.setStyleSheet(
                customer_theme_qss(self, """
                QTabWidget::pane { background: @window; border: none; }
                QTabBar::tab {
                    background: @surface_alt;
                    color: @text;
                    padding: 9px 16px;
                    border: 1px solid @border;
                    border-bottom: none;
                    border-top-left-radius: 10px;
                    border-top-right-radius: 10px;
                    margin-right: 4px;
                    font-weight: 700;
                }
                QTabBar::tab:selected { background: @accent; color: @selection_text; }
            """)
            )
        if hasattr(self, "tab_main"):
            self.tab_main.setStyleSheet(customer_theme_qss(self, "background: @window;"))
        if hasattr(self, "table"):
            self.table.setStyleSheet(
                customer_theme_qss(self, """
                QTableWidget { border-radius: 4px; border: 1px solid @border; background: @surface; gridline-color: transparent; }
                QHeaderView::section { background-color: rgba(8, 11, 17, 0.8); color: #93c5fd; padding: 8px 8px; font-size: 10px; font-weight: bold; border: none; }
                QTableWidget#CustomerListTable::item { padding: 4px 8px; color: @text; border-bottom: 1px solid @border; background-color: @surface; }
                QTableWidget#CustomerListTable::item:hover { background-color: @hover_bg; color: @text; }
                QTableWidget#CustomerListTable::item:selected:hover { background-color: @hover_bg; color: @text; }
                QTableWidget#CustomerListTable::item:selected { background-color: @selection_bg; color: @selection_text; font-weight: normal; border: none; outline: none; }
                QTableWidget::item:focus { outline: none; }
                QTableWidget::indicator:unchecked { width: 10px; height: 10px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 2px; }
                QTableWidget::indicator:checked { width: 12px; height: 12px; background: @accent; border: 1px solid @accent; border-radius: 2px; }
            """)
            )
        if hasattr(self, "inp_search"):
            self.inp_search.setStyleSheet(
                customer_theme_qss(self, "border: 1px solid @border; border-radius: 10px; padding-left: 0; background: @base; color: @text;")
            )
        for child in self.findChildren(QFrame):
            if child.objectName() == "CustomerFilterBar":
                child.setStyleSheet(customer_theme_qss(self, "QFrame#CustomerFilterBar { background: transparent; border: none; border-bottom: 1px solid @border; border-radius: 0; }"))
            elif child.objectName() == "CustomerToolbarCard":
                child.setStyleSheet(customer_theme_qss(self, "QFrame#CustomerToolbarCard { background: @surface; border: none; border-bottom: 1px solid @border; border-radius: 0; }"))

    def setup_ui(self):
        """Arayüz hiyerarşisini kurar"""
        self.setFont(QFont("Inter", 10))
        self.setStyleSheet(customer_theme_qss(self, "background: @window; font-family: 'Inter', 'Segoe UI', Arial;"))
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 2, 0, 6)
        self.main_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

        self.tabs = QTabWidget()
        self.tabs.tabBar().hide()
        self.tabs.setStyleSheet(
            customer_theme_qss(self, """
            QTabWidget::pane { background: @window; border: none; }
            QTabBar::tab {
                background: @surface_alt;
                color: @text;
                padding: 9px 16px;
                border: 1px solid @border;
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                margin-right: 4px;
                font-weight: 700;
            }
            QTabBar::tab:selected { background: @accent; color: @selection_text; }
        """)
        )
        self.tab_main = QWidget()
        self.tab_main.setStyleSheet(customer_theme_qss(self, "background: @window;"))
        self.tabs.addTab(self.tab_main, "👥 Müşteri Listesi")

        self.layout = QVBoxLayout(self.tab_main)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self._setup_header()
        self._setup_reference_metrics()
        # 1. Quick customer filters
        self._setup_banners()
        # 2. Araç Çubuğu (Dışa Aktarma & Arama)
        self._setup_toolbar()
        # 3. Veri Tablosu
        self._setup_table()
        # 4. Alt Bilgi (Footer)
        self._setup_footer()
        self.setMinimumSize(0, 0)

    def set_reference_shell_mode(self, enabled):
        self._reference_shell_mode = bool(enabled)
        self.main_layout.setContentsMargins(
            0, 2, 0, 21 if self._reference_shell_mode else 6
        )

    def _setup_reference_metrics(self):
        frame = QFrame()
        frame.setFixedHeight(141)
        frame.setStyleSheet(customer_theme_qss(self, "background: transparent; border: none;"))
        grid = QGridLayout(frame)
        grid.setContentsMargins(4, 22, 4, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        metrics = [
            ("Piyasa Alaca\u011f\u0131 (Bor\u00e7lular)", "\u20ba0.00 TRY", "danger", "4 Bor\u00e7lu M\u00fc\u015fteri Portf\u00f6y\u00fc", "USD: $0.00", "north_east", 38),
            ("Cari Avans & \u00d6n \u00d6demeler", "\u20ba0.00 TRY", "success", "Dengeli \u2022 A\u00e7\u0131k Avans Yok", "USD: $0.00", "wallet", 100),
            ("At\u00f6lye & Servisteki Cihazlar", "0 Adet Aktif", "#00f2fe", "3 At\u00f6lye Montaj \u2022 1 Testte", "Kapasite %40", "tool", 40),
            ("Kurumsal VIP Portf\u00f6y Oran\u0131", "%0", "#3b82f6", "Y\u0131ll\u0131k Bak\u0131m S\u00f6zle\u015fmeli", "+3.8% MoM", "verified", 28),
        ]
        self._customer_metric_values = []
        self._customer_metric_bars = []
        self._customer_metric_captions = []
        self._customer_metric_secondary = []
        self._customer_metric_title_labels = []
        for index, (title, value, accent, caption, secondary, icon_text, bar_value) in enumerate(metrics):
            card = QFrame(frame)
            card.setFixedHeight(117)
            card.setMinimumWidth(0)
            card.setProperty("skipThemeTransform", False)
            card.setStyleSheet(customer_theme_qss(self,
                "QFrame { background: @surface; border: 1px solid @border; border-radius: 12px; } "
                "QFrame:hover { background: @surface_alt; }"
            ))
            box = QGridLayout(card)
            box.setContentsMargins(12, 2, 12, 0)
            box.setVerticalSpacing(7)
            box.setHorizontalSpacing(8)
            box.setColumnStretch(0, 1)
            box.setRowStretch(2, 1)
            title_label = QLabel(title)
            title_label.setMinimumWidth(0)
            title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            title_font_size = 10
            title_label.setProperty("skipThemeTransform", False)
            title_label.setStyleSheet(customer_theme_qss(self, f"color: @text_muted; font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; font-size: {title_font_size}px; font-weight: 700; border: none; background: transparent;"))
            value_label = QLabel(value)
            value_label.setTextFormat(Qt.TextFormat.RichText)
            value_label.setFont(QFont("Plus Jakarta Sans", 32, QFont.Weight.Bold))
            value_label.setMinimumWidth(0)
            value_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            value_label.setProperty("skipThemeTransform", False)
            value_label.setStyleSheet(customer_theme_qss(self, f"color: {'@accent' if index == 2 else '@text'}; font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; font-size: 32px; font-weight: 700; border: none; background: transparent;"))
            box.addWidget(title_label, 0, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
            icon = QLabel()
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setFixedSize(24, 24)
            icon.setPixmap(navigation_icon(icon_text, 14, accent).pixmap(14, 14))
            icon.setProperty("skipThemeTransform", False)
            icon_color = "#00f2fe" if index == 2 else "#3b82f6" if index == 3 else "@" + accent
            icon.setStyleSheet(customer_theme_qss(self, f"color: {icon_color}; background: @surface_alt; border: 1px solid @border; border-radius: 6px; font-size: 16px; font-weight: 800;"))
            box.addWidget(icon, 0, 1, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if index == 3:
                sla_badge = QLabel("SLA Anla\u015fmal\u0131")
                sla_badge.setProperty("skipThemeTransform", False)
                sla_badge.setStyleSheet(customer_theme_qss(self,
                    "color: @accent; background: @surface_alt; border: none; border-radius: 3px; "
                    "padding: 2px 6px; font-size: 9px; font-weight: 700;"
                ))
                box.addWidget(value_label, 1, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
                box.addWidget(sla_badge, 1, 1, alignment=Qt.AlignmentFlag.AlignVCenter)
            else:
                box.addWidget(value_label, 1, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignVCenter)
            footer_row = QWidget(card)
            footer_row.setStyleSheet("background: transparent; border: none;")
            footer_layout = QHBoxLayout(footer_row)
            footer_layout.setContentsMargins(0, 0, 0, 0)
            footer_layout.setSpacing(4)
            caption_label = QLabel(caption)
            caption_label.setMinimumWidth(0)
            caption_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            caption_label.setProperty("skipThemeTransform", False)
            caption_label.setStyleSheet(customer_theme_qss(self, "color: @text_muted; font-family: 'JetBrains Mono', 'Segoe UI', Arial; font-size: 11px; border: none; background: transparent;"))
            secondary_label = QLabel(secondary)
            secondary_label.setMinimumWidth(0)
            secondary_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            secondary_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            secondary_label.setProperty("skipThemeTransform", False)
            secondary_label.setStyleSheet(customer_theme_qss(self, "color: @text_muted; font-family: 'JetBrains Mono', 'Segoe UI', Arial; font-size: 11px; font-weight: 600; border: none; background: transparent;"))
            footer_layout.addWidget(caption_label, 1)
            footer_layout.addWidget(secondary_label)
            box.addWidget(footer_row, 2, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignBottom)
            progress = QProgressBar(card)
            progress.setRange(0, 100)
            progress.setValue(bar_value)
            progress.setTextVisible(False)
            progress.setFixedHeight(4)
            progress.setProperty("skipThemeTransform", False)
            progress_color = ("@" + accent) if index < 2 else "#00f2fe" if index == 2 else "#3b82f6"
            if index == 0:
                progress_color = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 @warning, stop:1 @danger)"
            elif index == 2:
                progress_color = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f2fe, stop:1 #00f2fe)"
            progress.setStyleSheet(
                customer_theme_qss(self, "QProgressBar { background: @surface_alt; border: none; border-radius: 2px; } "
                "QProgressBar::chunk { background: " + progress_color + "; border-radius: 2px; }")
            )
            box.addWidget(progress, 3, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignBottom)
            grid.addWidget(card, 0, index)
            self._customer_metric_values.append(value_label)
            self._customer_metric_bars.append(progress)
            self._customer_metric_captions.append(caption_label)
            self._customer_metric_secondary.append(secondary_label)
            self._customer_metric_title_labels.append(title_label)
        self.layout.addWidget(frame)

    def _setup_header(self):
        # Note: This method was present in the plan but not called in setup_ui in the original file.
        # It's kept here for potential future use or if missed in original orkestration.
        hero = _CustomerHeroFrame()
        hero.setObjectName("CustomersHero")
        hero.setFixedHeight(112)
        hero.setProperty("skipThemeTransform", False)
        hero.setStyleSheet(
            customer_theme_qss(self, "QFrame#CustomersHero { background: @surface; border: 1px solid @border; border-radius: 12px; }")
        )
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(16, 18, 11, 8)
        hero_layout.setSpacing(4)
        header_row = QWidget(hero)
        header_row.setStyleSheet("background: transparent;")
        header_row_layout = QHBoxLayout(header_row)
        header_row_layout.setContentsMargins(0, 0, 0, 0)
        header_row_layout.setSpacing(8)
        title_region = QWidget(hero)
        title_region.setStyleSheet("background: transparent;")
        title_region_layout = QHBoxLayout(title_region)
        title_region_layout.setContentsMargins(0, 0, 0, 0)
        title_region_layout.setSpacing(8)

        icon_badge = QLabel()
        icon_badge.setFixedSize(48, 48)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_pixmap = QPixmap(48, 48)
        icon_pixmap.fill(Qt.GlobalColor.transparent)
        icon_painter = QPainter(icon_pixmap)
        icon_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        icon_painter.setPen(Qt.PenStyle.NoPen)
        icon_painter.setBrush(QColor(customer_theme_color(self, "accent")))
        icon_painter.drawEllipse(22, 14, 4, 4)
        icon_painter.drawEllipse(17, 17, 3, 3)
        icon_painter.drawEllipse(28, 17, 3, 3)
        icon_painter.drawRoundedRect(19, 19, 10, 8, 4, 4)
        icon_painter.drawRoundedRect(15, 21, 6, 6, 3, 3)
        icon_painter.drawRoundedRect(27, 21, 6, 6, 3, 3)
        icon_painter.end()
        icon_badge.setPixmap(icon_pixmap)
        icon_badge.setStyleSheet(
            customer_theme_qss(self, """
            QLabel {
                background: @surface_alt;
                color: @accent;
                border: none;
                border-radius: 12px;
            }
        """)
        )
        icon_shadow = QGraphicsDropShadowEffect(icon_badge)
        icon_shadow.setBlurRadius(24)
        icon_shadow.setColor(QColor(0, 242, 254, 76))
        icon_shadow.setOffset(0, 0)
        icon_badge.setGraphicsEffect(icon_shadow)
        title_region_layout.addWidget(icon_badge, alignment=Qt.AlignmentFlag.AlignTop)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title_box.setContentsMargins(0, 0, 0, 0)
        self.customer_header_title_box = title_box
        self.header_title = QLabel("M\u00fc\u015fteri Y\u00f6netimi & CRM")
        self.header_title.setObjectName("DashboardWelcomeTitle")
        self.header_title.setMinimumWidth(255)
        self.header_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.header_title.setStyleSheet(
            customer_theme_qss(self, """
            color: @text;
            font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial;
            font-size: 24px;
            font-weight: 600;
            border: none;
            background: transparent;
        """)
        )
        self.customer_header_title_style = self.header_title.styleSheet()
        self.header_badge = QLabel("Cari & Finans Entegre")
        self.header_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_badge.setFixedSize(116, 22)
        self.header_badge.setStyleSheet(customer_theme_qss(self, "QLabel { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 11px; font-size: 9px; font-weight: 600; padding: 0 6px; }"))
        title_row = QHBoxLayout()
        title_row.setSpacing(7)
        title_row.addWidget(self.header_title)
        title_row.addWidget(self.header_badge)
        self.header_live_badge = QLabel("\u25cf  Canl\u0131 Telemetri")
        self.header_live_badge.setFixedSize(94, 22)
        self.header_live_badge.setStyleSheet(customer_theme_qss(self, "color: @accent; background: @surface_alt; border: 1px solid @border; border-radius: 8px; padding: 2px 6px; font-size: 9px; font-weight: 700;"))
        title_row.addWidget(self.header_live_badge)
        title_row.addStretch(1)
        self.header_compact_badge = QLabel("Cari & Finans Entegre")
        self.header_compact_badge.setFixedSize(116, 18)
        self.header_compact_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_compact_badge.setStyleSheet(customer_theme_qss(self, "QLabel { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 9px; font-size: 8px; font-weight: 600; padding: 0 5px; }"))
        self.header_compact_live_badge = QLabel("\u25cf Canl\u0131 Telemetri")
        self.header_compact_live_badge.setFixedSize(94, 18)
        self.header_compact_live_badge.setStyleSheet(customer_theme_qss(self, "color: @accent; background: @surface_alt; border: 1px solid @border; border-radius: 8px; padding: 1px 5px; font-size: 8px; font-weight: 700;"))
        self.header_subtitle = QLabel(
            "M\u00fc\u015fteri portf\u00f6y\u00fcn\u00fc, cari hesap mutabakatlar\u0131n\u0131, at\u00f6lye teknik servis i\u015f emirlerini ve anl\u0131k tahsilat aksiyonlar\u0131n\u0131 tek merkezden y\u00f6netin."
        )
        self.header_subtitle.setWordWrap(True)
        self.header_subtitle.setMinimumWidth(0)
        self.header_subtitle.setMaximumWidth(535)
        self.header_subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.header_subtitle.setContentsMargins(0, 2, 0, 0)
        self.header_subtitle.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.header_subtitle.setStyleSheet(
            customer_theme_qss(self, """
            color: @text_muted;
            font-family: 'Inter', 'Segoe UI', Arial;
            font-size: 13px;
            border: none;
            background: transparent;
        """)
        )
        self.customer_header_subtitle_style = self.header_subtitle.styleSheet()
        title_box.addLayout(title_row)
        title_box.addWidget(
            self.header_subtitle,
            0,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        )
        self.header_compact_badge.hide()
        self.header_compact_live_badge.hide()
        title_region_layout.addLayout(title_box, 1)
        header_row_layout.addWidget(title_region, 1)
        action_panel = QWidget(hero)
        self.customer_header_action_panel = action_panel
        action_panel.setFixedWidth(604)
        action_panel.setStyleSheet("background: transparent;")
        action_stack = QVBoxLayout(action_panel)
        action_stack.setContentsMargins(0, 12, 0, 0)
        action_stack.setSpacing(8)
        action_bar = QFrame(action_panel)
        self.customer_header_action_bar = action_bar
        action_bar.setStyleSheet("QFrame { background: transparent; border: none; }")
        action_row = QHBoxLayout(action_bar)
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(6)
        self.customer_header_action_buttons = []
        self.customer_header_action_widths = []
        self.customer_header_action_styles = []
        action_specs = [
            ("Excel'e Aktar", 106, "document", "neon_cyan", self.export_excel),
            ("Toplu SMS/Bildirim", 138, "message", "secondary", self._open_selected_customer_sms),
            ("Cari Ekstre AI", 112, "calculator", "text_muted", self._open_selected_customer_history),
        ]
        for label, width, icon_name, icon_color, callback in action_specs:
            action = QPushButton(label)
            action.setFixedSize(width, 34)
            action.setIcon(navigation_icon(icon_name, 16, icon_color))
            action.setCursor(Qt.CursorShape.PointingHandCursor)
            action.setProperty("skipThemeTransform", False)
            action.setStyleSheet(
                customer_theme_qss(self, "QPushButton { background: @surface_alt; color: @text; border: 1px solid @border; "
                "border-radius: 8px; padding: 0 8px; font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; font-size: 11px; font-weight: 700; } "
                "QPushButton:hover { background: @hover_bg; color: @text; border-color: @accent; }")
            )
            action.clicked.connect(callback)
            action_row.addWidget(action)
            self.customer_header_action_buttons.append(action)
            self.customer_header_action_widths.append(width)
            self.customer_header_action_styles.append(action.styleSheet())
        help_action = QPushButton()
        help_action.setFixedSize(30, 34)
        help_action.setIcon(navigation_icon("help", 18, "text_muted"))
        help_action.setIconSize(QSize(18, 18))
        help_action.setToolTip("Nas\u0131l Kullan\u0131l\u0131r?")
        help_action.setAccessibleName("Nas\u0131l Kullan\u0131l\u0131r?")
        help_action.setProperty("skipThemeTransform", False)
        help_action.setStyleSheet(
            customer_theme_qss(self, "QPushButton { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 6px; padding: 0; font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; font-weight: 700; } "
            "QPushButton:hover { background: @hover_bg; }")
        )
        help_action.clicked.connect(lambda: self.notify("Customer search, filters, and actions are available on this screen."))
        action_row.addWidget(help_action)
        self.customer_header_action_buttons.append(help_action)
        self.customer_header_action_widths.append(30)
        self.customer_header_action_styles.append(help_action.styleSheet())
        add_customer = QPushButton("+ YEN\u0130 M\u00dc\u015eTER\u0130 EKLE")
        add_customer.setFixedSize(194, 32)
        add_customer.setIcon(navigation_icon("people", 16, "obsidian_base"))
        add_customer.setCursor(Qt.CursorShape.PointingHandCursor)
        add_customer.setStyleSheet(customer_theme_qss(self, "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f2fe, stop:1 #3b82f6); color: #080b11; border: 1px solid #00f2fe; border-radius: 8px; padding: 0 10px; font-size: 11px; font-weight: 800; } QPushButton:hover { border-color: #3b82f6; }"))
        add_customer_shadow = QGraphicsDropShadowEffect(add_customer)
        add_customer_shadow.setBlurRadius(20)
        add_customer_shadow.setColor(QColor(0, 242, 254, 100))
        add_customer_shadow.setOffset(0, 0)
        add_customer.setGraphicsEffect(add_customer_shadow)
        add_customer.clicked.connect(self.add_customer)
        self.btn_add_customer = add_customer
        action_row.addWidget(add_customer)
        self.customer_header_action_buttons.append(add_customer)
        self.customer_header_action_widths.append(194)
        self.customer_header_action_styles.append(add_customer.styleSheet())
        action_row.addStretch(1)
        action_stack.addWidget(action_bar)
        compact_row = QWidget(action_panel)
        compact_layout = QHBoxLayout(compact_row)
        compact_layout.setContentsMargins(0, 0, 0, 0)
        compact_layout.setSpacing(4)
        compact_add = QPushButton("+ YEN\u0130 M\u00dc\u015eTER\u0130")
        compact_add.setFixedSize(188, 32)
        compact_add.setIcon(navigation_icon("people", 16, "obsidian_base"))
        compact_add.setCursor(Qt.CursorShape.PointingHandCursor)
        compact_add.setStyleSheet(add_customer.styleSheet())
        compact_add_shadow = QGraphicsDropShadowEffect(compact_add)
        compact_add_shadow.setBlurRadius(20)
        compact_add_shadow.setColor(QColor(0, 242, 254, 100))
        compact_add_shadow.setOffset(0, 0)
        compact_add.setGraphicsEffect(compact_add_shadow)
        compact_add.clicked.connect(self.add_customer)
        compact_more = QToolButton()
        compact_more.setFixedSize(28, 32)
        compact_more.setIcon(navigation_icon("more_vertical", 16, "text_muted"))
        compact_more.setToolTip("D\u0131\u015fa aktar\u0131m ve m\u00fc\u015fteri ara\u00e7lar\u0131")
        compact_more.setAccessibleName("D\u0131\u015fa aktar\u0131m ve m\u00fc\u015fteri ara\u00e7lar\u0131")
        compact_more.setStyleSheet(customer_theme_qss(self,
            "QToolButton { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 8px; } "
            "QToolButton:hover { background: @surface_high; border-color: @accent; }"
        ))
        compact_menu = QMenu(compact_more)
        for label, callback in (
            ("Excel'e Aktar", self.export_excel),
            ("Toplu SMS/Bildirim", self._open_selected_customer_sms),
            ("Cari Ekstre AI", self._open_selected_customer_history),
            ("Nas\u0131l Kullan\u0131l\u0131r?", lambda: self.notify("Customer search, filters, and actions are available on this screen.")),
        ):
            compact_menu.addAction(label, callback)
        compact_more.setMenu(compact_menu)
        compact_more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        compact_layout.addWidget(compact_add)
        compact_layout.addWidget(compact_more)
        action_stack.addWidget(compact_row)
        compact_row.hide()
        self.customer_header_compact_row = compact_row
        self.customer_header_compact_add = compact_add
        header_row_layout.addWidget(action_panel)
        hero_layout.addWidget(header_row)
        details_row = QWidget(hero)
        details_row.setStyleSheet("background: transparent;")
        details_layout = QHBoxLayout(details_row)
        details_layout.setContentsMargins(56, 0, 0, 0)
        details_layout.setSpacing(6)
        details_layout.addStretch(1)
        details_layout.addWidget(self.header_compact_badge)
        details_layout.addWidget(self.header_compact_live_badge)
        self.customer_header_details_row = details_row
        hero_layout.addWidget(details_row)
        hero_container = QWidget()
        hero_container.setStyleSheet("background: transparent; border: none;")
        hero_container_layout = QHBoxLayout(hero_container)
        hero_container_layout.setContentsMargins(4, 10, 4, 0)
        hero_container_layout.setSpacing(0)
        hero_container_layout.addWidget(hero)
        self.customer_hero_container = hero_container
        self.layout.addWidget(hero_container)

    def _apply_customer_header_responsive_widths(self):
        panel = getattr(self, "customer_header_action_panel", None)
        action_bar = getattr(self, "customer_header_action_bar", None)
        compact_row = getattr(self, "customer_header_compact_row", None)
        if panel is None or action_bar is None or compact_row is None:
            return
        compact = self.width() < 1180
        hero = self.findChild(QFrame, "CustomersHero")
        panel.setFixedWidth(604 if not compact else 232)
        action_bar.setVisible(not compact)
        compact_row.setVisible(compact)
        self.header_badge.setVisible(not compact)
        self.header_live_badge.setVisible(not compact)
        self.header_compact_badge.setVisible(compact)
        self.header_compact_live_badge.setVisible(compact)
        detail_width = self.customer_header_details_row.width() or max(0, self.width() - 48)
        badge_width = 216 if compact else 0
        subtitle_width = max(0, min(535, detail_width - 56 - badge_width))
        self.header_subtitle.setMinimumWidth(subtitle_width)
        self.header_title.setStyleSheet(
            self.customer_header_title_style.replace(
                "font-size: 22px;", "font-size: 20px;"
            ) if compact else self.customer_header_title_style.replace(
                "font-size: 22px;", "font-size: 24px;"
            )
        )
        self.header_subtitle.setStyleSheet(
            self.customer_header_subtitle_style
        )
        for title_label in getattr(self, "_customer_metric_title_labels", ()):
            title = title_label.text()
            font_size = (8 if "VIP" in title else 9) if compact else 11
            title_label.setStyleSheet(
            customer_theme_qss(self, f"color: @text_muted; font-family: 'Inter', 'Segoe UI', Arial; font-size: {font_size}px; "
                "font-weight: 700; border: none; background: transparent;")
            )
        for button, wide_width, base_style in zip(
            self.customer_header_action_buttons,
            self.customer_header_action_widths,
            self.customer_header_action_styles,
        ):
            narrow_width = {106: 90, 138: 124, 112: 98, 30: 30, 194: 180}.get(wide_width, wide_width)
            button.setFixedWidth(narrow_width if compact else wide_width)
            button.setStyleSheet(
                base_style.replace("font-size: 11px;", "font-size: 9px;")
                if compact else base_style
            )
        if hero is not None:
            hero.setFixedHeight(112)

    def _setup_banners(self):
        filter_bar = QFrame()
        filter_bar.setObjectName("CustomerFilterBar")
        filter_bar.setStyleSheet(
            customer_theme_qss(self,
                "QFrame#CustomerFilterBar { background: transparent; border: none; "
                "border-bottom: 1px solid @border; border-radius: 0; }"
            )
        )
        grid = QGridLayout(filter_bar)
        grid.setContentsMargins(25, 8, 25, 8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        self.customer_filter_group = QButtonGroup(self)
        self.customer_filter_group.setExclusive(True)
        self.customer_filter_buttons = {}
        filter_specs = (
            ("T\u00dcM M\u00dc\u015eTER\u0130LER", "accent", None, 214),
            ("BOR\u00c7LULAR", "warning", "DEBTORS", 218),
            ("TAHS\u0130LAT BEKLEYENLER", "success", "OPEN_RECEIVABLES", 274),
            ("VIP M\u00dc\u015eTER\u0130LER", "accent", "VIP", 224),
            ("A\u00c7IK SERV\u0130SLER", "success", "OPEN_SERVICES", 266),
        )
        for index, (label, color, filter_key, width) in enumerate(filter_specs):
            button = self._create_banner_btn(label, color)
            button.setFixedWidth(width)
            button.setCheckable(True)
            button.clicked.connect(
                lambda _checked=False, key=filter_key: self.filter_by_type(key)
            )
            self.customer_filter_group.addButton(button)
            self.customer_filter_buttons[filter_key] = button
            row, column = divmod(index, 4)
            grid.addWidget(button, row, column)

        self.customer_filter_buttons[None].setChecked(True)
        grid.setColumnStretch(4, 1)
        filter_bar.hide()
        self.customer_quick_filter_bar = filter_bar

    def _create_banner_btn(self, text, color_key):
        btn = QPushButton(text)
        btn.setFixedHeight(46)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        btn.setStyleSheet(customer_theme_qss(self, f"""
            QPushButton {{ background: @surface_alt; color: @{color_key}; border-radius: 8px; border: 1px solid @border; padding: 0 8px; text-align: left; font-size: 11px; font-weight: 700; }}
            QPushButton:checked {{ background: @accent; color: @selection_text; border-color: @accent; }}
            QPushButton:hover {{ background: @hover_bg; border-color: @{color_key}; }}
        """))
        return btn

    def _setup_toolbar(self):
        toolbar_card = QFrame()
        self.customer_toolbar_card = toolbar_card
        toolbar_card.setObjectName("CustomerToolbarCard")
        toolbar_card.setProperty("skipThemeTransform", False)
        toolbar_card.setFixedHeight(70)
        toolbar_card.setStyleSheet(
            customer_theme_qss(self, "QFrame#CustomerToolbarCard { background: @surface; border: none; border-bottom: 1px solid @border; border-radius: 0; }")
        )
        rows = QBoxLayout(QBoxLayout.Direction.LeftToRight, toolbar_card)
        rows.setContentsMargins(12, 7, 12, 3)
        rows.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("\u0130sim, unvan, telefon, vergi no veya e-posta ile anl\u0131k filtrele...")
        self.inp_search.setMinimumWidth(220)
        self.inp_search.setFixedHeight(35)
        self.inp_search.setFont(QFont("Inter", 9))
        self.inp_search.setProperty("skipThemeTransform", False)
        self.inp_search.setStyleSheet(
            customer_theme_qss(self, "border: 1px solid @border; border-radius: 10px; padding-left: 0; background: @base; color: @text;")
        )
        self.inp_search.setTextMargins(0, 0, 82, 0)
        self.inp_search.addAction(
            navigation_icon("search", 16, "text_muted"),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.search_shortcut_button = QToolButton(self.inp_search)
        self.search_shortcut_button.setText("\u2318K / Ctrl+K")
        self.search_shortcut_button.setFixedSize(68, 20)
        self.search_shortcut_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_shortcut_button.setToolTip("Arama alan\u0131na git: Ctrl+K")
        self.search_shortcut_button.setAccessibleName("Arama k\u0131sayolu Ctrl+K")
        self.search_shortcut_button.setStyleSheet(
            customer_theme_qss(self, "QToolButton { background: @surface_alt; color: @text_muted; border: 1px solid @border; "
            "border-radius: 4px; padding: 0; font-family: 'JetBrains Mono'; font-size: 7px; } "
            "QToolButton:hover { color: @text; border-color: @accent; }")
        )
        self.search_shortcut_button.clicked.connect(self._focus_customer_search)
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        self.search_shortcut.activated.connect(self._focus_customer_search)
        self.inp_search.textChanged.connect(lambda: self.search_timer.start(500))
        filters = QHBoxLayout()
        filters.setSpacing(6)
        search_row.addWidget(self.inp_search, 1)
        self.customer_type_filter = QComboBox()
        self.customer_type_filter.addItem("T\u00fcm Tipler (Bireysel / VIP)", "all")
        self.customer_type_filter.addItem("Bireysel M\u00fc\u015fteriler", "individual")
        self.customer_type_filter.addItem("Kurumsal VIP", "vip")
        self.customer_type_filter.addItem("Ta\u015feron & Partner", "partner")
        self.customer_type_filter.addItem("Yetkili Bayi", "dealer")
        compact_toolbar = self.width() < 1180
        self.customer_type_filter.setFixedWidth(145 if compact_toolbar else 170)
        self.customer_type_filter.setFixedHeight(32)
        self.customer_type_filter.setFont(QFont("Inter", 7))
        filter_style = customer_theme_qss(self, "QComboBox { background: @base; color: @text; border: 1px solid @border; border-radius: 8px; padding: 0 9px; } QComboBox::drop-down { border: none; width: 22px; } QComboBox QAbstractItemView { background: @surface; color: @text; selection-background-color: @selection_bg; selection-color: @selection_text; }")
        self.customer_type_filter.setProperty("skipThemeTransform", False)
        self.customer_type_filter.setStyleSheet(filter_style)
        self.customer_type_filter.currentTextChanged.connect(self._apply_customer_toolbar_filters)

        self.customer_location_filter = QComboBox()
        self.customer_location_filter.addItems(["T\u00fcm Lokasyonlar (\u0130l / \u0130l\u00e7e)"])
        self.customer_location_filter.setFixedWidth(185 if compact_toolbar else 264)
        self.customer_location_filter.setFixedHeight(32)
        self.customer_location_filter.setFont(QFont("Inter", 8))
        self.customer_location_filter.setProperty("skipThemeTransform", False)
        self.customer_location_filter.setStyleSheet(filter_style)
        self.customer_location_filter.currentIndexChanged.connect(self._apply_customer_toolbar_filters)

        self.customer_balance_filter = QComboBox()
        self.customer_balance_filter.addItem("T\u00fcm Bakiyeler (Finans Durumu)", "all")
        self.customer_balance_filter.addItem("Sadece Alacakl\u0131lar (Bor\u00e7lular)", "receivable")
        self.customer_balance_filter.addItem("\u00d6n \u00d6deme / Avans Olanlar", "advance")
        self.customer_balance_filter.addItem("S\u0131f\u0131r Bakiyeli Dengeli Cari", "zero")
        self.customer_balance_filter.setFixedWidth(160 if compact_toolbar else 195)
        self.customer_balance_filter.setFixedHeight(32)
        self.customer_balance_filter.setProperty("skipThemeTransform", False)
        self.customer_balance_filter.setStyleSheet(filter_style)
        self.customer_balance_filter.setFont(QFont("Inter", 7))
        self.customer_balance_filter.currentTextChanged.connect(self._apply_customer_toolbar_filters)
        filter_menu = QMenu(self)
        filter_menu.setObjectName("CustomerFilterMenu")
        filter_menu.setStyleSheet(customer_theme_qss(self,
            "QMenu#CustomerFilterMenu { background: @surface; color: @text; border: 1px solid @border; }"
        ))
        filter_panel = QWidget()
        filter_panel.setFixedWidth(310)
        filter_panel_layout = QVBoxLayout(filter_panel)
        filter_panel_layout.setContentsMargins(10, 8, 10, 8)
        filter_panel_layout.setSpacing(6)
        filter_controls = (
            ("Tip", self.customer_type_filter),
            ("Lokasyon", self.customer_location_filter),
            ("Bakiye", self.customer_balance_filter),
        )
        for label_text, control in filter_controls:
            label = QLabel(label_text)
            label.setStyleSheet(customer_theme_qss(self, "color: @text_muted; font-size: 11px; font-weight: 700;"))
            control.setFixedWidth(286)
            filter_panel_layout.addWidget(label)
            filter_panel_layout.addWidget(control)
        filter_action = QWidgetAction(filter_menu)
        filter_action.setDefaultWidget(filter_panel)
        filter_menu.addAction(filter_action)
        for filter_key, filter_button in getattr(self, "customer_filter_buttons", {}).items():
            quick_action = filter_menu.addAction(filter_button.text())
            quick_action.triggered.connect(
                lambda _checked=False, key=filter_key: self.filter_by_type(key)
            )
        self.customer_filter_menu = filter_menu
        self.btn_customer_filter = QToolButton()
        self.btn_customer_filter.setText("Filtrele")
        self.btn_customer_filter.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_customer_filter.setMenu(filter_menu)
        self.btn_customer_filter.setFixedHeight(40)
        self.btn_customer_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_customer_filter.setStyleSheet(customer_theme_qss(self,
            "QToolButton { background: @surface; color: @text; border: 1px solid @border; "
            "border-radius: 8px; padding: 0; font-weight: 700; } "
            "QToolButton::menu-indicator { image: none; width: 0; } "
            "QToolButton:hover { background: @surface_high; border-color: @accent; }"
        ))
        self.btn_customer_filter.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        quick_filter_icon = QPixmap(18, 18)
        quick_filter_icon.fill(Qt.GlobalColor.transparent)
        quick_filter_painter = QPainter(quick_filter_icon)
        quick_filter_painter.setPen(QPen(QColor(customer_theme_color(self, "accent")), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for line_y, line_end in ((4, 15), (9, 12), (14, 15)):
            quick_filter_painter.drawLine(3, line_y, line_end, line_y)
        quick_filter_painter.end()
        self.btn_customer_filter.setIcon(QIcon(quick_filter_icon))
        self.btn_customer_filter.setToolTip("H\u0131zl\u0131 m\u00fc\u015fteri filtreleri")
        self.btn_customer_filter.setAccessibleName("H\u0131zl\u0131 m\u00fc\u015fteri filtreleri")
        self.btn_add_customer.setFixedHeight(32)
        filters.addWidget(self.customer_type_filter)
        filters.addWidget(self.customer_location_filter)
        filters.addWidget(self.customer_balance_filter)

        self.customer_toolbar_actions = {}
        action_specs = (
            ("copy", "", "Listeyi Kopyala", self.copy_list),
            ("print", "", "Yazd\u0131r", self.print_list),
            ("excel", "XLS", "Excel'e Aktar", self.export_excel),
            ("pdf", "PDF", "PDF'e Aktar", self.export_pdf),
            ("documents", "", "Belge Merkezi", self.open_documents_center),
            ("import", "", "M\u00fc\u015fteri \u0130\u00e7e Aktar", self.import_customers),
            ("fit_columns", "", "\u00d6l\u00e7\u00fctleri S\u0131\u011fd\u0131r", self.fit_customer_columns),
            ("multi_select", "", "\u00c7oklu Se\u00e7im", self.toggle_multiselect),
        )
        button_size = 28 if compact_toolbar else 30
        overflow_menu = QMenu(self)
        overflow_menu.setStyleSheet(customer_theme_qss(self,
            "QMenu { background: @surface; color: @text; border: 1px solid @border; } "
            "QMenu::item { padding: 8px 16px; } QMenu::item:selected { background: @selection_bg; }"
        ))
        print_action = None
        for key, icon, tooltip, callback in action_specs:
            action = QPushButton(icon)
            action.setObjectName("CustomerToolbar_" + key)
            action.setFixedSize(button_size, button_size)
            action.setToolTip(tooltip)
            action.setAccessibleName(tooltip)
            action.setStyleSheet(customer_theme_qss(self, DesignTokens.get_icon_btn_qss()))
            action.clicked.connect(callback)
            self.customer_toolbar_actions[key] = action
            if key == "print":
                action.setText("")
                action.setIcon(navigation_icon("printer", 18))
                print_action = action
            else:
                menu_action = overflow_menu.addAction(tooltip)
                menu_action.triggered.connect(callback)
                action.hide()
        filters.addWidget(self.btn_customer_filter)
        if print_action is not None:
            filters.addWidget(print_action)
        self.customer_more_actions = QToolButton()
        self.customer_more_actions.setObjectName("CustomerToolbar_more_actions")
        self.customer_more_actions.setFixedSize(button_size, button_size)
        self.customer_more_actions.setIcon(navigation_icon("settings", 18))
        self.customer_more_actions.setToolTip("Di\u011fer m\u00fc\u015fteri i\u015flemleri")
        self.customer_more_actions.setAccessibleName("Di\u011fer m\u00fc\u015fteri i\u015flemleri")
        self.customer_more_actions.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.customer_more_actions.setMenu(overflow_menu)
        self.customer_more_actions.setStyleSheet(customer_theme_qss(self, DesignTokens.get_icon_btn_qss()))
        filters.addWidget(self.customer_more_actions)
        self.btn_multi = self.customer_toolbar_actions["multi_select"]
        self.btn_multi.setCheckable(True)
        rows.addLayout(search_row, 1)
        rows.addLayout(filters)
        self.layout.addSpacing(23)
        self.layout.addWidget(toolbar_card)
        self._apply_customer_toolbar_responsive_widths()

    def _apply_customer_toolbar_responsive_widths(self):
        toolbar = getattr(self, "customer_toolbar_card", None)
        if toolbar is None:
            return
        compact = toolbar.width() < 1180
        rows = toolbar.layout()
        rows.setDirection(
            QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight
        )
        toolbar.setFixedHeight(78 if compact else 42)
        if toolbar.width() < 1050:
            widths = (170, 215, 195)
        else:
            widths = (145, 185, 160) if compact else (170, 264, 195)
        for widget, width in zip(
            (self.customer_type_filter, self.customer_location_filter, self.customer_balance_filter),
            widths,
        ):
            widget.setFixedWidth(width)
        button_size = 28 if compact else 30
        self.btn_customer_filter.setFixedSize(button_size, button_size)
        for button in getattr(self, "customer_toolbar_actions", {}).values():
            button.setFixedSize(button_size, button_size)
        self._position_customer_search_badge()

    def _position_customer_search_badge(self):
        button = getattr(self, "search_shortcut_button", None)
        search = getattr(self, "inp_search", None)
        if button is None or search is None:
            return
        button.move(max(0, search.width() - button.width() - 14), (search.height() - button.height()) // 2)

    def _focus_customer_search(self):
        search = getattr(self, "inp_search", None)
        if search is not None:
            search.setFocus(Qt.FocusReason.ShortcutFocusReason)
            search.selectAll()

    def fit_customer_columns(self):
        table = getattr(self, "table", None)
        if table is None or table.columnCount() <= 0:
            return
        table.resizeColumnsToContents()
        available = table.viewport().width()
        widths = [table.columnWidth(column) for column in range(table.columnCount())]
        minimums = (48, 84, 170, 84, 150, 92, 116, 84, 116)
        widths = [max(width, minimums[index]) for index, width in enumerate(widths)]
        total = sum(widths)
        if available > total:
            extra = available - total
            for column in (2, 4, 6):
                share = extra // 3
                widths[column] += share
            widths[2] += extra % 3
        table.horizontalHeader().setStretchLastSection(False)
        for column, width in enumerate(widths):
            table.setColumnWidth(column, width)

    def _apply_customer_toolbar_filters(self):
        type_filter = self.customer_type_filter.currentText() if hasattr(self, "customer_type_filter") else "Tum Tipler"
        type_filter_key = self.customer_type_filter.currentData() if hasattr(self, "customer_type_filter") else None
        balance_filter = self.customer_balance_filter.currentText() if hasattr(self, "customer_balance_filter") else "Tum Bakiyeler"
        balance_filter_key = self.customer_balance_filter.currentData() if hasattr(self, "customer_balance_filter") else None
        location_filter = self.customer_location_filter.currentData() if hasattr(self, "customer_location_filter") else ""
        visible_count = 0
        for row in range(self.table.rowCount()):
            row_data = self.table.item(row, 1)
            customer = row_data.data(Qt.ItemDataRole.UserRole) if row_data else None
            customer_type = str(customer["type"] if customer and "type" in customer.keys() else "")
            customer_location = str((customer.get("city") or customer.get("location") or "").strip() if customer else "")
            balances = [
                float(customer[key] or 0.0)
                for key in ("balance_try", "balance_usd", "balance_eur")
                if customer and key in customer.keys()
            ]
            has_debt = any(value < -0.0001 for value in balances)
            has_credit = any(value > 0.0001 for value in balances)
            contract_type = str(customer.get("contract_type") or "").casefold() if customer else ""
            is_partner = bool(int(customer.get("is_partner", 0) or 0)) if customer else False
            if type_filter_key == "individual":
                type_visible = "bireysel" in customer_type.casefold() or "individual" in customer_type.casefold()
            elif type_filter_key == "vip":
                type_visible = "vip" in customer_type.casefold() or "vip" in contract_type
            elif type_filter_key == "partner":
                type_visible = is_partner or "ta\u015feron" in customer_type.casefold() or "partner" in customer_type.casefold()
            elif type_filter_key == "dealer":
                type_visible = is_partner or "bayi" in customer_type.casefold()
            elif type_filter_key == "all" or type_filter.startswith("T\u00fcm Tipler"):
                type_visible = True
            else:
                type_visible = type_filter.lower() in customer_type.lower()
            visible = type_visible
            if location_filter:
                visible = visible and customer_location.casefold() == str(location_filter).casefold()
            if balance_filter_key == "receivable":
                visible = visible and (has_credit or has_debt)
            elif balance_filter_key == "advance":
                visible = visible and has_debt
            elif balance_filter_key == "zero":
                visible = visible and not has_debt and not has_credit
            elif balance_filter.casefold().startswith("bor"):
                visible = visible and has_debt
            elif balance_filter == "Alacak":
                visible = visible and has_credit
            elif balance_filter == "Dengede":
                visible = visible and not has_debt and not has_credit
            self.table.setRowHidden(row, not visible)
            visible_count += int(visible)
        if hasattr(self, "lbl_total"):
            total = getattr(self, "total_count", self.table.rowCount())
            self.lbl_total.setText(
                "<span style='color:#f8fafc;font-weight:600'>Toplam Kay\u0131t:</span> "
                "<span style='color:#00f2fe;font-weight:700'>{}</span> &nbsp; "
                "<span style='color:#94a3b8'>\u2022</span> &nbsp; Filtrelenen: "
                "<span style='color:#f8fafc;font-weight:600'>{}</span> M\u00fc\u015fteri".format(
                    total, visible_count
                )
            )

    def _setup_table(self):
        self.table = _CustomerTableWidget()
        self.table.setObjectName("CustomerListTable")
        self.customer_row_hover_delegate = _CustomerRowHoverDelegate(self.table)
        self.table.setItemDelegate(self.customer_row_hover_delegate)
        self.table.setProperty("skipThemeTransform", False)
        self.table.setMinimumHeight(0)
        self.table.setColumnCount(9)
        self.table.setHorizontalHeader(_CustomerTableHeaderView(Qt.Orientation.Horizontal, self.table))
        self.table.setHorizontalHeaderLabels(
            ["", "M\u00dc\u015eTER\u0130 NO", "M\u00dc\u015eTER\u0130 & \u00dcNVAN", "SEGMENT", "\u0130LET\u0130\u015e\u0130M & ER\u0130\u015e\u0130M", "C\u0130HAZ & SERV\u0130S DURUMU", "CAR\u0130 BAK\u0130YE", "S\u0130STEM DURUMU", "\u0130\u015eLEMLER"]
        )

        header = self.table.horizontalHeader()
        header.setFixedHeight(37)
        header.setSortIndicatorShown(True)
        header.setSortIndicator(2, Qt.SortOrder.AscendingOrder)
        header.sectionClicked.connect(self._toggle_customer_select_all)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._customer_column_widths = (39, 157, 342, 204, 211, 442, 139, 287, 67)
        for column, width in enumerate(self._customer_column_widths):
            self.table.setColumnWidth(column, width)
        self.table.horizontalHeaderItem(6).setTextAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.setCornerButtonEnabled(False)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setMouseTracking(True)
        self.table.itemChanged.connect(self._on_customer_checkbox_changed)
        self.table.cellEntered.connect(self._on_table_cell_entered)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.cellDoubleClicked.connect(self.on_table_double_click)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setStyleSheet(
            customer_theme_qss(self, """
            QTableWidget { border-radius: 4px; border: 1px solid @border; background: @surface; gridline-color: transparent; }
            QHeaderView::section { background-color: rgba(8, 11, 17, 0.8); color: #93c5fd; padding: 8px 8px; font-size: 10px; font-weight: bold; border: none; }
            QTableWidget#CustomerListTable::item { padding: 4px 8px; color: @text; border-bottom: 1px solid @border; background-color: @surface; }
            QTableWidget#CustomerListTable::item:hover { background-color: @hover_bg; color: @text; }
            QTableWidget#CustomerListTable::item:selected:hover { background-color: @hover_bg; color: @text; }
            QTableWidget#CustomerListTable::item:selected { background-color: @selection_bg; color: @selection_text; font-weight: normal; border: none; outline: none; }
            QTableWidget::item:focus { outline: none; }
            QTableWidget::indicator:unchecked { width: 10px; height: 10px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 2px; }
            QTableWidget::indicator:checked { width: 12px; height: 12px; background: @accent; border: 1px solid @accent; border-radius: 2px; }
        """)
        )
        table_palette = self.table.palette()
        table_palette.setColor(QPalette.ColorRole.Base, QColor(customer_theme_color(self, "surface")))
        table_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(customer_theme_color(self, "surface")))
        self.table.setPalette(table_palette)
        self.table.viewport().setPalette(table_palette)
        self.table.viewport().setAutoFillBackground(True)
        self.table.viewport().setProperty("skipThemeTransform", False)
        self.table.viewport().setStyleSheet(customer_theme_qss(self, "background-color: @surface;"))
        self.customer_table_container = QWidget(self.tab_main)
        table_container_layout = QVBoxLayout(self.customer_table_container)
        table_container_layout.setContentsMargins(4, 23, 4, 0)
        table_container_layout.setSpacing(0)
        table_container_layout.addWidget(self.table)
        self.empty_state = EmptyState(
            "Henüz müşteri yok",
            "Bu görünümde gösterilecek müşteri kaydı bulunamadı.",
            parent=self,
        )
        self.empty_state.setMinimumHeight(280)
        self.empty_state.hide()
        table_container_layout.addWidget(self.empty_state)
        self.layout.addWidget(self.customer_table_container, 1)

    def _fit_customer_table_columns(self):
        table = getattr(self, "table", None)
        widths = getattr(self, "_customer_column_widths", ())
        if table is None or len(widths) != table.columnCount():
            return
        available = table.viewport().width()
        if available <= 0:
            return
        if available < 1100:
            widths = (34, 68, 175, 78, 128, 108, 110, 76, 145)
        total = sum(widths)
        scale = available / total
        fitted = [max(28, round(width * scale)) for width in widths]
        fitted[-1] = max(28, available - sum(fitted[:-1]))
        for column, width in enumerate(fitted):
            table.setColumnWidth(column, width)

    def _setup_footer(self):
        self.footer = QFrame()
        self.footer.setObjectName("CustomerFooterCard")
        self.footer.setFixedHeight(40)
        self.footer.setAutoFillBackground(True)
        footer_palette = self.footer.palette()
        footer_palette.setColor(
            QPalette.ColorRole.Window,
            QColor(customer_theme_color(self, "base")),
        )
        self.footer.setPalette(footer_palette)
        self.footer.setProperty("skipThemeTransform", False)
        self.footer.setStyleSheet(
            customer_theme_qss(self, "background: @base; border: none; border-radius: 0;")
        )
        f_layout = QHBoxLayout(self.footer)
        f_layout.setContentsMargins(12, 3, 12, 3)
        f_layout.setSpacing(10)
        self.lbl_total = QLabel("Toplam Kay\u0131t: 0")
        self.lbl_total.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_total.setStyleSheet(
            customer_theme_qss(
                self,
                "color: @text; border: none; background: transparent; "
                "font: 10px 'JetBrains Mono', 'Segoe UI', Arial;",
            )
        )
        self.lbl_time = QLabel(
            "Son G\u00fcncelleme: {}".format(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        )
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_time.setStyleSheet(customer_theme_qss(self, "color: @text_muted; border: none; background: transparent;"))
        self.lbl_sync = QLabel("\u25cf AYEC Cloud Sync: Canl\u0131 (1.8ms)")
        self.lbl_sync.setStyleSheet(
            customer_theme_qss(self, "color: @success; border: none; background: transparent; "
            "font: 10px 'JetBrains Mono', 'Segoe UI', Arial;")
        )

        left_box = QWidget()
        left_box.setStyleSheet("background: transparent;")
        left_layout = QHBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.lbl_total)
        left_layout.addStretch()
        page_size_label = QLabel("Sayfa ba\u015f\u0131na:")
        page_size_label.setStyleSheet(
            customer_theme_qss(
                self,
                "color: @text_muted; border: none; background: transparent; "
                "font: 10px 'JetBrains Mono', 'Segoe UI', Arial;",
            )
        )
        left_layout.addWidget(page_size_label)
        self.page_size_filter = QComboBox()
        self.page_size_filter.addItems(["10", "25", "50", "100"])
        self.page_size_filter.setCurrentText(str(self.limit))
        self.page_size_filter.setFixedWidth(64)
        self.page_size_filter.setFixedHeight(24)
        self.page_size_filter.setStyleSheet(
            customer_theme_qss(
                self,
                "QComboBox { background: @surface; color: @text; border: none; "
                "border-radius: 4px; padding: 0 7px; font: 10px 'JetBrains Mono', 'Segoe UI', Arial; } "
                "QComboBox::drop-down { border: none; width: 14px; }",
            )
        )
        self.page_size_filter.currentTextChanged.connect(self._on_customer_page_size_changed)
        left_layout.addWidget(self.page_size_filter)

        center_box = QWidget()
        center_box.setStyleSheet("background: transparent;")
        center_layout = QHBoxLayout(center_box)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)
        center_layout.addStretch()

        right_box = QWidget()
        right_box.setStyleSheet("background: transparent;")
        right_layout = QHBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addStretch()
        right_layout.addWidget(self.lbl_sync)
        right_layout.addWidget(QLabel("|"))
        right_layout.addWidget(self.lbl_time)

        self.btn_prev = QPushButton("◀")
        self.btn_prev.setFixedSize(28, 24)
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_prev.setStyleSheet(
            customer_theme_qss(self,
                "background: @surface; color: @text; border: 1px solid @border; border-radius: 8px;"
            )
        )

        self.lbl_page = QLabel("1 / 1")
        self.lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_page.setMinimumWidth(52)
        self.lbl_page.setStyleSheet(
            customer_theme_qss(self, "font-weight: 800; color: @text; border: none; background: transparent;")
        )
        self.lbl_page.hide()
        self.page_number_buttons = []
        self.page_number_group = QButtonGroup(self)
        self.page_number_group.setExclusive(True)
        for page_index in range(3):
            page_button = QPushButton(str(page_index + 1))
            page_button.setCheckable(True)
            page_button.setFixedSize(28, 24)
            page_button.setStyleSheet(
                customer_theme_qss(self, "QPushButton { background: @surface; color: @text_muted; border: 1px solid @border; border-radius: 6px; font-family: 'JetBrains Mono', 'Segoe UI', Arial; font-size: 10px; font-weight: 600; } "
                "QPushButton:checked { background: @accent; color: @selection_text; border-color: @accent; font-weight: 800; }")
            )
            page_button.clicked.connect(
                lambda _checked=False, index=page_index: self._go_to_customer_page(index)
            )
            self.page_number_group.addButton(page_button, page_index)
            self.page_number_buttons.append(page_button)

        self.btn_next = QPushButton("▶")
        self.btn_next.setFixedSize(28, 24)
        self.btn_next.clicked.connect(self.next_page)
        self.btn_next.setStyleSheet(
            customer_theme_qss(self,
                "background: @surface; color: @text; border: 1px solid @border; border-radius: 8px;"
            )
        )

        center_layout.addWidget(self.btn_prev)
        center_layout.addWidget(self.lbl_page)
        for page_button in self.page_number_buttons:
            center_layout.addWidget(page_button)
        center_layout.addWidget(self.btn_next)
        center_layout.addStretch()

        f_layout.addWidget(left_box, 1)
        f_layout.addWidget(center_box, 1)
        f_layout.addWidget(right_box, 1)

        self.customer_table_container.layout().addWidget(self.footer)

        if SystemConfig.is_feature_active(self.db, "usage_guides"):
            self.tab_guide = QWidget()
            self.setup_usage_guide_tab()
            self.tabs.addTab(self.tab_guide, "❓ Nasıl Kullanılır?")

        self.main_layout.addWidget(self.tabs, 1)

    def _update_pagination_ui(self):
        total_pages = (self.total_count + self.limit - 1) // self.limit
        if total_pages == 0:
            total_pages = 1

        self.lbl_page.setText(f"{self.current_page + 1} / {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < total_pages - 1)
        first_page = max(0, min(self.current_page - 1, total_pages - 3))
        for offset, button in enumerate(getattr(self, "page_number_buttons", [])):
            page_index = first_page + offset
            button.setVisible(page_index < total_pages)
            if page_index < total_pages:
                button.setText(str(page_index + 1))
                button.setChecked(page_index == self.current_page)
                button.setAccessibleName("Sayfa {}".format(page_index + 1))

    def _go_to_customer_page(self, page_index):
        total_pages = max(1, (self.total_count + self.limit - 1) // self.limit)
        page_index = int(page_index)
        if 0 <= page_index < total_pages and page_index != self.current_page:
            self.current_page = page_index
            self.request_reload()

    def _on_customer_page_size_changed(self, value):
        try:
            new_limit = max(1, int(value))
        except (TypeError, ValueError):
            return
        if new_limit != self.limit:
            self.limit = new_limit
            self.current_page = 0
            self.request_reload()

    def _prepare_initial_view(self):
        """Yükleniyor durumunu göster. Worker çalışıyorsa tabloyu sıfırlama."""
        self.lbl_total.setText("⏳ Yükleniyor...")
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.request_reload()

    def next_page(self):
        total_pages = (self.total_count + self.limit - 1) // self.limit
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.request_reload()

    def filter_by_type(self, type_name):
        self.current_filter_type = type_name
        filter_buttons = getattr(self, "customer_filter_buttons", {})
        active_filter_button = filter_buttons.get(type_name)
        if active_filter_button is not None:
            active_filter_button.setChecked(True)
        title_map = {
            None: "Müşteri Yönetimi",
            "DEBTORS": "Net Borçlular",
            "OPEN_RECEIVABLES": "Tahsilat Bekleyenler",
            "VIP": "VIP M\u00fc\u015fteriler",
            "OPEN_SERVICES": "A\u00e7\u0131k Servisi Olanlar",
        }
        subtitle_map = {
            None: "Müşterileri, cari durumlarını ve tahsilat aksiyonlarını tek ekranda yönetin.",
            "DEBTORS": "Borç bakiyesi taşıyan kayıtları odak görünümünde inceleyin.",
            "OPEN_RECEIVABLES": "Tahsilat bekleyen işlemleri hızlıca filtreleyip aksiyon alın.",
            "VIP": "Kurumsal VIP segmentindeki m\u00fc\u015fterileri listeleyin.",
            "OPEN_SERVICES": "A\u00e7\u0131k servis talebi olan m\u00fc\u015fterileri listeleyin.",
        }
        badge_map = {
            None: "MÜŞTERİ HUB",
            "DEBTORS": "BORÇ ODAĞI",
            "OPEN_RECEIVABLES": "TAHSİLAT",
            "VIP": "VIP M\u00dc\u015eTER\u0130LER",
            "OPEN_SERVICES": "A\u00c7IK SERV\u0130SLER",
        }
        if hasattr(self, "header_title"):
            self.header_title.setText(
                title_map.get(type_name, "Müşteri Yönetimi")
            )
        if hasattr(self, "header_subtitle"):
            self.header_subtitle.setText(
                subtitle_map.get(type_name, subtitle_map[None])
            )
        if hasattr(self, "header_badge"):
            self.header_badge.setText(badge_map.get(type_name, badge_map[None]))
        self.current_page = 0
        self.request_reload()
