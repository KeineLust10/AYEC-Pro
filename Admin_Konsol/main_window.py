"""
AYEC Pro Admin Konsol - Ana Pencere
Tum sayfalar sol sidebar + icerik alani yap\u0131s\u0131nda burada bir araya getirilir.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QSizePolicy,
    QSpacerItem, QMessageBox, QTableWidget, QAbstractItemView, QComboBox,
    QLineEdit, QProgressBar, QToolButton, QMenu
)
from PyQt6.QtCore import Qt, QSize, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QColor, QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPen, QPixmap

from pathlib import Path
import config
import api_client
import logging
from product_catalog import product_names, product_code

from pages.dashboard import DashboardPage
from pages.companies import CompaniesPage
from pages.customer_360 import Customer360Page
from pages.installation_map import InstallationMapPage
from pages.licenses import LicensesPage
from pages.license_requests import LicenseRequestsPage
from pages.invite_codes import InviteCodesPage
from pages.notifications import NotificationsPage
from pages.error_logs import ErrorLogsPage
from pages.live_status import LiveStatusPage
from pages.server_settings import ServerSettingsPage
from pages.database_manager import DatabaseManagerPage
from pages.limits import LimitsPage
from pages.backups import BackupsPage
from pages.updates import UpdatesPage
from pages.audit_logs import AuditLogsPage
from table_interaction import apply_professional_table


_NAV_ITEMS = [
    ("dashboard",        "\ud83d\udcca", "Dashboard"),
    ("companies",        "\ud83c\udfe2", "Firma Y\u00f6netimi"),
    ("customer_360",     "\ud83e\udde9", "M\u00fc\u015fteri 360"),
    ("installation_map", "\ud83d\udccd", "Kurulum Haritasi"),
    ("licenses",         "\ud83c\udf9f\ufe0f", "Lisans Y\u00f6netimi"),
    ("license_requests", "\ud83d\udcec", "Lisans Talepleri"),
    ("invite_codes",     "#", "Davet Kodu Uretme"),
    ("backups",          "\ud83d\udcbe", "Yedekleme ve Kurtarma"),
    ("updates",          "\ud83d\ude80", "G\u00fcncelleme Da\u011f\u0131t\u0131m\u0131"),
    ("limits",           "\ud83d\udcca", "Kota ve Limitler"),
    ("database_manager", "\ud83d\uddd4", "Salt Okunur SQL"),
    ("notifications",    "\ud83d\udd14", "Bildirim G\u00f6nder"),
    ("live_status",      "\ud83d\udccc", "Canl\u0131 Durum"),
    ("error_logs",       "\ud83d\udcdb", "Hata Kay\u0131tlar\u0131"),
    ("audit_logs",       "\ud83d\udee1", "Denetim Kay\u0131tlar\u0131"),
    ("server_settings",  "\u2699\ufe0f", "Sunucu Ayarlar\u0131"),
]

_PROGRAM_MENU_LABELS = {
    "AYEC Pro Elek": "Elek",
    "AYEC Pro Barkod Okuyucu": "Barkod Okuyucu",
    "AYEC Pro Ciro": "Ciro Takip",
    "AYEC Pro Teknik Servis": "AYEC Pro Teknik Servis Takip",
}


class _HeaderStatusWorker(QThread):
    done = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(api_client.server_status())
        except Exception as exc:
            self.failed.emit(str(exc))


_STYLESHEET = """
QMainWindow { background: #0b1220; }
QWidget { background: #0b1220; color: #e8eef8; font-family: 'Segoe UI'; }

/* Sidebar */
#sidebar { background: #0d192b; border-right: 1px solid #263a58; }
#logoLabel { color: #8bb8ff; font-size: 25px; font-weight: 900;
             padding: 0px 22px; letter-spacing: 3px; }
#versionLabel { color: #71829d; font-size: 11px; padding: 0 22px 16px; }
#navBtn { background: transparent; color: #a7b8cf; border: 1px solid transparent;
          text-align: left; padding: 11px 18px; font-size: 13px;
          border-radius: 10px; margin: 3px 12px; }
#navBtn:hover { background: #162a46; color: #f4f8ff; border: 1px solid #294766; }
#navBtn[active=true] { background: #1d4f91; color: #ffffff;
                        border: 1px solid #3f78bb; border-left: 4px solid #7db5ff;
                        font-weight: 800; }
#logoutBtn { background: transparent; color: #8ea0b9; border: none;
             text-align: left; padding: 11px 18px; font-size: 12px;
             border-radius: 11px; margin: 3px 12px; }
#logoutBtn:hover { background: #45202a; color: #ff9aa9; }
#sidebarDivider { background: #22304a; max-height: 1px; }

/* Header */
#topBar { background: #0f1523; border-bottom: 1px solid rgba(66, 71, 84, 51); font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; }
#topBar[referenceStyle="license"] { background: rgba(22, 27, 42, 242); border-bottom: 0; }
#topBar[referenceStyle="console"] { background: #090e1c; border-bottom: 1px solid rgba(66, 71, 84, 51); }
#pageHeaderTitle { color: #dee2f6; font-size: 13px; font-weight: 700; }
#headerEyebrow { color: #c2c6d6; font: 10px "Segoe UI", Arial; }
#topBar[referenceStyle="console"] #headerEyebrow { color: #dee2f6; font: 700 10px "JetBrains Mono", "Segoe UI", Arial; }
#globalSearch { background: #161b2a; border: 1px solid rgba(66, 71, 84, 77); border-radius: 4px;
                padding: 6px 9px; color: #dee2f6; min-width: 170px; }
#telemetryBar { background: #161b2a; border: 1px solid #424754; border-radius: 3px; }
#telemetryLabel { color: #8c909f; font-size: 9px; font-weight: 700; }
#telemetryValue { color: #4edea3; font-size: 9px; font-weight: 700; }
#headerMetrics { background: #161b2a; border: 1px solid #252a39; border-radius: 4px; }
#headerMetricLabel { color: #8c909f; font: 700 9px "Segoe UI", Arial; }
#headerMetricValue { color: #4edea3; font: 700 9px "Segoe UI", Arial; }
#headerMetricValue[tone="ram"] { color: #4cd7f6; }
#headerMetricValue[tone="disk"] { color: #adc6ff; }
QProgressBar#headerMetricBar { border: 0; border-radius: 2px; background: #303444; min-height: 4px; max-height: 4px; }
QProgressBar#headerMetricBar::chunk { border-radius: 2px; background: #4edea3; }
QProgressBar#headerMetricBar[tone="ram"]::chunk { background: #4cd7f6; }
QProgressBar#headerMetricBar[tone="disk"]::chunk { background: #adc6ff; }
#headerAction { background: #252a39; color: #dee2f6; border: none; border-radius: 3px;
                padding: 7px 10px; font-size: 11px; }
#headerPrimaryAction { background: #adc6ff; color: #002e6a; border: none; border-radius: 3px;
                       padding: 4px 8px; font-size: 10px; font-weight: 700; }
#companyMenuButton { background: #161b2a; color: #dee2f6; border: 1px solid #29394f;
                     border-radius: 4px; padding: 6px 10px; font: 600 10px "Segoe UI", Arial; }
#companyMenuButton:hover { background: #1a1f2e; border-color: #4d8eff; }
#companyMenuButton::menu-indicator { subcontrol-origin: padding; subcontrol-position: right center; }
#serverStatus { background: #161b2a; border: 1px solid #424754; border-radius: 3px; }
#serverDot { color: #4edea3; font-size: 14px; }
#serverCaption { color: #8c909f; font-size: 8px; font-weight: 700; }
#serverUrl { color: #c2c6d6; font-size: 9px; font-weight: 700; }

/* Content area */
#contentArea { background: #0e1321; }
#contentArea QWidget { background: #0e1321; color: #dee2f6; font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; }
QDialog, QMessageBox { font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; }
QDialog QWidget, QMessageBox QWidget { font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; }

/* Page titles */
#pageTitle { color: #dee2f6; font-size: 25px; font-weight: 800; margin-bottom: 4px; }
#pageSubtitle { color: #c2c6d6; font-size: 12px; }
#sectionTitle { color: #c2c6d6; font-size: 13px; font-weight: 700;
                text-transform: uppercase; letter-spacing: 1px; }
#panelTitle { color: #dee2f6; font-size: 16px; font-weight: 800; }

/* Panels */
#leftPanel { background: #161b2a; border-right: 1px solid #29394f; }
#detailPanel { background: #0e1321; }
#detailTitle { color: #dee2f6; font-size: 22px; font-weight: 800; }

/* Cards */
#metricCard { background: #161b2a; border: 1px solid #424754;
              border-radius: 6px; min-height: 112px; }
#metricCard:hover { background: #1a1f2e; border: 1px solid #4d8eff; }
#metricCard[tone="blue"] { border-left: 3px solid #adc6ff; }
#metricCard[tone="green"] { border-left: 3px solid #4edea3; }
#metricCard[tone="amber"] { border-left: 3px solid #f59e0b; }
#metricCard[tone="violet"] { border-left: 3px solid #8b5cf6; }
#metricTitle { color: #c2c6d6; font-size: 12px; }
#metricValue { color: #dee2f6; font-size: 24px; font-weight: 800; }
#metricSub { color: #8c909f; font-size: 11px; }
#statusCard { background: #161b2a; border: 1px solid #424754;
              border-radius: 6px; min-height: 86px; }
#statusCard:hover { border: 1px solid #4d8eff; }
#cardName { color: #dee2f6; font-size: 14px; font-weight: 700; }
#cardStatus { font-size: 12px; font-weight: bold; }
#cardDetail { color: #8c909f; font-size: 11px; }
#formCard, #ctrlFrame { background: #161b2a; border: 1px solid #424754;
            border-radius: 6px; }
#detailCard, #tableCard { background: #161b2a; border: 1px solid #424754;
              border-radius: 6px; }
#card { background: #161b2a; border: 1px solid #424754; border-radius: 6px; }
#tableToolbar { background: #161b2a; border: none;
                border-bottom: 1px solid #424754; }
#selectionInfo { color: #dee2f6; background: #252a39;
                 border: 1px solid #424754; border-radius: 4px;
                 padding: 8px 12px; font-size: 12px; }
#groupBox { color: #c2c6d6; font-size: 11px; border: 1px solid #424754;
            border-radius: 6px; margin-top: 12px; padding-top: 12px; }
#groupBox::title { color: #adc6ff; subcontrol-origin: margin;
                   subcontrol-position: top left; padding: 0 6px; left: 12px; }

/* Tables */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
QDateEdit, QDateTimeEdit, QTimeEdit {
    background: #090e1c; color: #dee2f6; border: 1px solid #424754;
    border-radius: 3px; padding: 7px 9px; selection-background-color: #4d8eff;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus,
QTimeEdit:focus { border: 1px solid #4d8eff; }
QPushButton { background: #252a39; color: #dee2f6; border: 1px solid #424754;
              border-radius: 3px; padding: 7px 10px; }
QPushButton:hover { background: #343948; }
QPushButton:disabled { color: #8c909f; background: #1a1f2e; }
#dataTable, QTableWidget { background: #090e1c; border: 1px solid #424754;
             border-radius: 6px; gridline-color: transparent;
             selection-background-color: transparent; selection-color: #ffffff;
             outline: none; }
#dataTable QHeaderView::section, QTableWidget QHeaderView::section {
    background: #252a39; color: #c2c6d6; border: none;
    border-bottom: 1px solid #424754; padding: 8px 10px; font-size: 11px;
    font-weight: 800; }
#dataTable::item, QTableWidget::item { padding: 8px 10px; color: #dee2f6; }
#dataTable::item:selected, QTableWidget::item:selected { background: transparent; color: #ffffff; }
#dataTable::item:hover, QTableWidget::item:hover { background: transparent; }
QTableWidget QLineEdit { background: #172943; color: #ffffff; border: 2px solid #78aefc;
                          border-radius: 8px; padding: 7px; }
QTableWidget::item:focus { border: none; outline: none; }
QTableCornerButton::section { background: #192b47; border: none; }
QListWidget { background: #111f35; border: 1px solid #263b5b; border-radius: 14px;
              outline: none; }
QListWidget::item { color: #edf4ff; padding: 12px 14px; border-radius: 9px; }
QListWidget::item:hover { background: #1b3558; }
QListWidget::item:selected { background: #2455a5; color: #ffffff; }
QCheckBox:focus, QPushButton:focus, QComboBox:focus, QLineEdit:focus,
QTextEdit:focus, QDateEdit:focus { outline: none; }

/* Inputs */
#fieldInput { background: #0d1b30; color: #edf4ff; border: 1px solid #365779;
              border-radius: 9px; padding: 9px 12px; font-size: 13px; }
#fieldInput:focus { border: 1px solid #68a7ff; background: #10233d; }
#searchInput { background: #0d1b30; color: #edf4ff; border: 1px solid #365779;
               border-radius: 9px; padding: 9px 12px; font-size: 13px; }
#searchInput:focus { border: 2px solid #78aefc; }
#textArea { background: #172943; color: #edf4ff; border: 1px solid #304b71;
            border-radius: 8px; padding: 8px; font-size: 13px; }
#codeBox { background: #102845; color: #8ee7c8; border: 1px solid #3a6b9f;
           border-radius: 12px; padding: 12px 16px; font-size: 16px; font-weight: 800; }
#combo { background: #0d1b30; color: #edf4ff; border: 1px solid #365779;
         border-radius: 9px; padding: 8px 11px; min-width: 140px; }
#dateEdit { background: #0d1b30; color: #edf4ff; border: 1px solid #365779;
            border-radius: 9px; padding: 8px 11px; }
#combo:focus, #dateEdit:focus { border: 1px solid #68a7ff; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit, QDateTimeEdit, QSpinBox {
    background: #0d1b30; color: #edf4ff; border: 1px solid #365779;
    border-radius: 9px; padding: 8px 11px; selection-background-color: #2455a5;
    selection-color: #ffffff; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QDateEdit:focus, QDateTimeEdit:focus, QSpinBox:focus {
    border: 1px solid #68a7ff; background: #10233d; }
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled,
QDateEdit:disabled, QDateTimeEdit:disabled { color: #627895; background: #0b1728; }

/* Buttons */
#primaryBtn { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                  stop:0 #2563eb, stop:1 #1d4ed8);
              color: white; border: 1px solid #3b75c2; border-radius: 9px;
              padding: 9px 18px; font-size: 13px; font-weight: bold; }
#primaryBtn:hover { background: #3b82f6; }
#primaryBtn:disabled { background: #263b5b; color: #71829d; }
#secondaryBtn { background: #132742; color: #c8d7ea; border: 1px solid #365779;
                border-radius: 9px; padding: 8px 16px; font-size: 12px; }
#secondaryBtn:hover { background: #1f3b61; color: #ffffff; }
#dangerBtn { background: #45202a; color: #ff9aa9; border: 1px solid #703344;
             border-radius: 8px; padding: 7px 16px; font-size: 12px; }
#dangerBtn:hover { background: #63303e; }
#dangerBtn:disabled { background: #231b27; color: #725764; border: 1px solid #3c2932; }
#tableDangerBtn { background: #4a1f2b; color: #ffadb9; border: 1px solid #743446;
                  border-radius: 7px; padding: 5px 10px; font-size: 11px;
                  font-weight: 700; margin: 5px 8px; }
#tableDangerBtn:hover { background: #67293a; color: #ffffff; }
#tableDangerBtn:disabled { background: #182235; color: #65758c;
                           border: 1px solid #29394f; }
#successBtn { background: #123b36; color: #5eead4; border: 1px solid #1f665d;
              border-radius: 8px; padding: 7px 16px; font-size: 12px; }
#successBtn:hover { background: #1e3d29; }
QPushButton { min-height: 20px; }
#companyBtn { background: #161b2a; color: #c2c6d6; border: 1px solid #29394f;
              border-radius: 8px; padding: 12px; text-align: left;
              font-size: 12px; }
#companyBtn:hover { background: #1a1f2e; color: #ffffff; border-color: #4d8eff; }
#companyBtn:checked { background: #1b3558; color: #ffffff; font-weight: bold;
                      border: 1px solid #4d8eff; }
#companyBtn:focus { outline: none; border: 1px solid #4e80c9; }

/* Lists & scrolls */
#companyList { border: none; background: transparent; }
#logScroll { border: none; background: transparent; }
#statusScroll { border: none; background: transparent; }
#logFrame { background: transparent; }
#logRow { background: #13151c; border-radius: 6px; }
#logRow:hover { background: #1e2130; }
#logTime { color: #6b7280; font-size: 11px; }
#logAction { color: #e5e7eb; font-size: 12px; }
#logFirm { color: #7c6af7; font-size: 12px; }

/* Forms */
#infoKey { color: #6b7280; font-size: 12px; }
#infoVal { color: #e5e7eb; font-size: 13px; }
#counterLabel { color: #60a5fa; font-size: 13px; }

/* Labels */
#statusLabel { color: #8da3c0; font-size: 12px; min-height: 20px; }
#emptyLabel { color: #4b5563; font-size: 13px; padding: 40px; }
#rememberCheck { color: #9ca3af; font-size: 12px; }
#rememberCheck::indicator { width: 16px; height: 16px;
    border: 1px solid #2d3147; border-radius: 4px; background: #1a1d27; }
#rememberCheck::indicator:checked { background: #7c6af7; border: 1px solid #7c6af7; }

/* Progress bars */
#metricBar { background: #1a1d27; border-radius: 6px; border: none; height: 18px; }
#metricBar::chunk { border-radius: 6px; }

/* Scrollbars */
QScrollBar:vertical { background: #0f1117; width: 8px; }
QScrollBar::handle:vertical { background: #2d3147; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #0b1220; height: 9px; }
QScrollBar::handle:horizontal { background: #304b71; border-radius: 4px; min-width: 28px; }
QToolTip { background: #172943; color: #f4f8ff; border: 1px solid #4e80c9;
          padding: 6px; border-radius: 6px; }
QComboBox QAbstractItemView { background: #172943; color: #edf4ff;
                              border: 1px solid #365779;
                              selection-background-color: #2455a5; }
QComboBox::drop-down { border: none; width: 28px; }
QGroupBox { background: #10213a; border: 1px solid #294463;
            border-radius: 14px; margin-top: 14px; padding: 16px; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 8px;
                   color: #b9cce3; font-weight: 700; }
"""


class MainWindow(QMainWindow):
    logged_out = pyqtSignal()

    @staticmethod
    def _notification_icon() -> QIcon:
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#adc6ff"), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        bell = QPainterPath()
        bell.moveTo(5, 14)
        bell.cubicTo(7, 12, 6, 8, 7, 6)
        bell.cubicTo(9, 2, 15, 4, 15, 8)
        bell.cubicTo(15, 11, 15, 13, 17, 14)
        painter.drawPath(bell)
        painter.drawLine(5, 14, 17, 14)
        painter.drawArc(8, 15, 6, 4, 180 * 16, 180 * 16)
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def _search_icon() -> QIcon:
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#8c909f"), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawEllipse(3, 3, 8, 8)
        painter.drawLine(10, 10, 15, 15)
        painter.end()
        return QIcon(pixmap)

    def __init__(self):
        super().__init__()
        font_root = Path(__file__).resolve().parent / "assets" / "fonts"
        for weight in (400, 500, 600, 700):
            font_path = font_root / f"PlusJakartaSans-{weight}.ttf"
            if font_path.is_file():
                QFontDatabase.addApplicationFont(str(font_path))
        mono_font_path = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "JetBrainsMono-Regular.ttf"
        if mono_font_path.is_file():
            QFontDatabase.addApplicationFont(str(mono_font_path))
        self.setWindowTitle(config.APP_NAME)
        self.setMinimumSize(1240, 780)
        self.resize(1440, 900)
        self.setStyleSheet(_STYLESHEET)
        self._pages: dict[str, QWidget] = {}
        self._nav_btns: dict[str, QPushButton] = {}
        self._current_page = ""
        self._active_product = "AYEC Pro Teknik Servis"
        self._header_status_thread = None
        api_client.set_product_context(product_code(self._active_product))
        self._build_ui()
        self._navigate("dashboard")
        self._header_status_timer = QTimer(self)
        self._header_status_timer.setInterval(30_000)
        self._header_status_timer.timeout.connect(self._refresh_header_status)
        self._header_status_timer.start()
        self._refresh_header_status()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- Sidebar ----
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(264)
        sidebar_lay = QVBoxLayout(sidebar)
        sidebar_lay.setContentsMargins(0, 16, 0, 12)
        sidebar_lay.setSpacing(2)

        # Logo
        logo_lbl = QLabel("AYEC")
        logo_lbl.setObjectName("logoLabel")
        logo_lbl.setContentsMargins(0, 12, 0, 4)
        sidebar_lay.addWidget(logo_lbl)
        ver_lbl = QLabel(f"Admin Konsol v{config.APP_VERSION}")
        ver_lbl.setObjectName("versionLabel")
        sidebar_lay.addWidget(ver_lbl)

        divider = QFrame()
        divider.setObjectName("sidebarDivider")
        divider.setFixedHeight(1)
        sidebar_lay.addWidget(divider)
        sidebar_lay.addSpacing(10)

        # Nav butonlari
        for page_id, icon, label in _NAV_ITEMS:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("navBtn")
            btn.setProperty("active", False)
            btn.setFixedHeight(43)
            btn.clicked.connect(lambda _, pid=page_id: self._navigate(pid))
            sidebar_lay.addWidget(btn)
            self._nav_btns[page_id] = btn

        sidebar_lay.addStretch()

        divider2 = QFrame()
        divider2.setObjectName("sidebarDivider")
        divider2.setFixedHeight(1)
        sidebar_lay.addWidget(divider2)

        logout_btn = QPushButton("  \ud83d\udeaa  Cikis Yap")
        logout_btn.setObjectName("logoutBtn")
        logout_btn.setFixedHeight(44)
        logout_btn.clicked.connect(self._logout)
        sidebar_lay.addWidget(logout_btn)

        outer.addWidget(sidebar)

        # ---- Sag taraf ----
        right = QFrame()
        right.setObjectName("contentArea")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        # Top bar
        top_bar = QFrame()
        self._top_bar = top_bar
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(56)
        top_bar_lay = QHBoxLayout(top_bar)
        top_bar_lay.setContentsMargins(40, 0, 16, 0)
        top_bar_lay.setSpacing(8)
        self._top_bar_layout = top_bar_lay
        self._header_flex_active = False
        self._license_gap_active = False
        self._header_col_removed = False

        header_col = QVBoxLayout()
        self._header_col = header_col
        header_col.setSpacing(0)
        header_col.addStrut(259)
        header_eyebrow = QLabel("Sistem  /  Yonetim Konsolu  /  Dashboard")
        header_eyebrow.setObjectName("headerEyebrow")
        header_col.addWidget(header_eyebrow)
        self._header_title = QLabel("Dashboard")
        self._header_title.setObjectName("pageHeaderTitle")
        header_col.addWidget(self._header_title)
        self._header_title.hide()
        self._header_eyebrow = header_eyebrow
        top_bar_lay.addLayout(header_col)
        self._global_search = QLineEdit()
        self._global_search.setObjectName("globalSearch")
        self._global_search.setPlaceholderText("Firma, lisans veya hata ara...")
        self._global_search.setClearButtonEnabled(True)
        self._global_search.setFixedWidth(320)
        self._global_search.addAction(self._search_icon(), QLineEdit.ActionPosition.LeadingPosition)
        self._global_search.returnPressed.connect(self._submit_global_search)
        top_bar_lay.addWidget(self._global_search)

        self._product_selector = QComboBox(self)
        self._product_selector.setToolTip("Yonetilecek urunu secin")
        self._product_selector.addItems(product_names())
        self._product_selector.currentTextChanged.connect(self._product_changed)
        self._product_selector.hide()

        telemetry = QFrame()
        telemetry.setObjectName("headerMetrics")
        telemetry.setToolTip("Sistem kaynak telemetrisi")
        telemetry_layout = QHBoxLayout(telemetry)
        telemetry_layout.setContentsMargins(8, 4, 8, 4)
        telemetry_layout.setSpacing(8)
        self._header_metric_widgets = {}
        for key, label, tone in (("cpu_percent", "CPU", "cpu"), ("ram_percent", "RAM", "ram"), ("disk_percent", "DISK", "disk")):
            metric = QWidget(telemetry)
            metric_layout = QHBoxLayout(metric)
            metric_layout.setContentsMargins(0, 0, 0, 0)
            metric_layout.setSpacing(4)
            metric_label = QLabel(label)
            metric_label.setObjectName("headerMetricLabel")
            metric_value = QLabel("--")
            metric_value.setObjectName("headerMetricValue")
            metric_value.setProperty("tone", tone)
            metric_bar = QProgressBar()
            metric_bar.setObjectName("headerMetricBar")
            metric_bar.setProperty("tone", tone)
            metric_bar.setRange(0, 100)
            metric_bar.setValue(0)
            metric_bar.setTextVisible(False)
            metric_bar.setFixedWidth(48)
            metric_bar.setAccessibleName(label + " utilization")
            metric_value.setAccessibleName(label + " usage percentage")
            metric_layout.addWidget(metric_label)
            metric_layout.addWidget(metric_bar)
            metric_layout.addWidget(metric_value)
            telemetry_layout.addWidget(metric)
            self._header_metric_widgets[key] = (metric_bar, metric_value)
        telemetry.setFixedWidth(361)
        top_bar_lay.addWidget(telemetry)
        refresh_header = QPushButton("\u21bb")
        refresh_header.setObjectName("headerAction")
        refresh_header.setFixedSize(32, 32)
        refresh_header.setToolTip("Telemetriyi yenile")
        refresh_header.clicked.connect(self._refresh_shell_status)
        self._refresh_header_button = refresh_header
        top_bar_lay.addWidget(refresh_header)
        quick_header = QPushButton("\u26a1  Hizli Islem")
        quick_header.setObjectName("headerPrimaryAction")
        quick_header.setFixedSize(88, 32)
        quick_header.clicked.connect(lambda: self._navigate("license_requests"))
        self._quick_header_button = quick_header
        top_bar_lay.addWidget(quick_header)
        self._header_notifications = QPushButton()
        self._header_notifications.setObjectName("headerAction")
        self._header_notifications.setFixedSize(34, 34)
        self._header_notifications.setIcon(self._notification_icon())
        self._header_notifications.setIconSize(QSize(16, 16))
        self._header_notifications.setAccessibleName("Bildirimlere git")
        self._header_notifications.setToolTip("Bildirimleri ac")
        self._header_notifications.clicked.connect(lambda: self._navigate("notifications"))
        self._header_notifications.hide()
        account = QLabel("PA")
        account.setAlignment(Qt.AlignmentFlag.AlignCenter)
        account.setFixedSize(32, 32)
        account.setStyleSheet("background: #adc6ff; color: #002e6a; border-radius: 16px; font-weight: 700;")
        account.setToolTip("Platform Admin")
        top_bar_lay.addWidget(account)
        self._firm_menu = QMenu(self)
        manage_companies = self._firm_menu.addAction("Firma Y\u00f6netimi")
        manage_companies.triggered.connect(lambda: self._navigate("companies"))
        self._firm_menu.addSeparator()
        self._firm_menu.addSection("Programlar\u0131m")
        self._program_action_group = QActionGroup(self)
        self._program_action_group.setExclusive(True)
        self._program_actions = {}
        for name in product_names():
            action = QAction(_PROGRAM_MENU_LABELS.get(name, name), self._firm_menu)
            action.setCheckable(True)
            action.setData(name)
            action.setChecked(name == self._active_product)
            self._program_action_group.addAction(action)
            self._firm_menu.addAction(action)
            self._program_actions[name] = action
        self._program_action_group.triggered.connect(
            lambda action: self._select_program(str(action.data() or ""))
        )
        self._firm_button = QToolButton()
        self._firm_button.setObjectName("companyMenuButton")
        self._firm_button.setText("Programlarim \u25be")
        self._firm_button.setMenu(self._firm_menu)
        self._firm_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._firm_button.setToolTip("Firma ve program kapsam\u0131n\u0131 se\u00e7in")
        self._firm_button.setAccessibleName("Firmalar ve Programlar\u0131m men\u00fcs\u00fc")
        self._firm_button.setMinimumWidth(112)
        top_bar_lay.insertWidget(top_bar_lay.count() - 1, self._firm_button)
        right_lay.addWidget(top_bar)

        # Stacked pages
        self._stack = QStackedWidget()
        self._stack.setObjectName("contentArea")
        right_lay.addWidget(self._stack, 1)

        outer.addWidget(right, 1)

    def _product_changed(self, product_name: str):
        """Keep a single product context for the shared admin shell."""
        self._active_product = str(product_name or "AYEC Pro Teknik Servis")
        api_client.set_product_context(product_code(self._active_product))
        self._header_title.setToolTip("Urun: " + self._active_product)
        program_action = getattr(self, "_program_actions", {}).get(self._active_product)
        if program_action and not program_action.isChecked():
            program_action.setChecked(True)
        page = self._pages.get(self._current_page)
        product_filter = getattr(page, "set_product_filter", None)
        if callable(product_filter):
            product_filter(self._active_product)

    def _select_program(self, product_name: str):
        if product_name not in product_names():
            return
        self._product_selector.setCurrentText(product_name)
        self._navigate("companies")

    def _refresh_shell_status(self):
        self._refresh_current_page()
        self._refresh_header_status()

    def _refresh_header_status(self):
        worker = self._header_status_thread
        if worker and worker.isRunning():
            return
        worker = _HeaderStatusWorker(self)
        worker.done.connect(self._update_header_metrics)
        worker.failed.connect(self._clear_header_metrics)
        self._header_status_thread = worker
        worker.start()

    def _update_header_metrics(self, data: dict):
        for key, (bar, value_label) in self._header_metric_widgets.items():
            raw_value = data.get(key)
            if raw_value is None:
                bar.setValue(0)
                value_label.setText("--")
                continue
            try:
                value = max(0, min(100, int(float(raw_value))))
            except (TypeError, ValueError):
                bar.setValue(0)
                value_label.setText("--")
                continue
            bar.setValue(value)
            value_label.setText(f"{value}%")

    def _clear_header_metrics(self, _error: str):
        self._update_header_metrics({})

    def _submit_global_search(self):
        page = self._pages.get(self._current_page)
        query = self._global_search.text().strip()
        if not page or not query:
            return
        fields = page.findChildren(QLineEdit)
        if fields:
            fields[0].setText(query)

    def _refresh_current_page(self):
        page = self._pages.get(self._current_page)
        refresh = getattr(page, "_refresh", None)
        if callable(refresh):
            refresh()

    def _get_page(self, page_id: str) -> QWidget:
        if page_id not in self._pages:
            constructors = {
                "dashboard":       DashboardPage,
                "companies":       CompaniesPage,
                "customer_360":    Customer360Page,
                "installation_map": InstallationMapPage,
                "licenses":        LicensesPage,
                "license_requests": LicenseRequestsPage,
                "invite_codes":     InviteCodesPage,
                "backups":         BackupsPage,
                "updates":         UpdatesPage,
                "limits":          LimitsPage,
                "database_manager": DatabaseManagerPage,
                "notifications":   NotificationsPage,
                "live_status":     LiveStatusPage,
                "error_logs":      ErrorLogsPage,
                "audit_logs":      AuditLogsPage,
                "server_settings": ServerSettingsPage,
            }
            cls = constructors.get(page_id)
            if cls:
                try:
                    page = cls()
                except Exception as exc:
                    logging.getLogger("ayec_admin").exception("Page initialization failed: %s", page_id)
                    page = QLabel(f"Sayfa yuklenemedi: {page_id}\\n{type(exc).__name__}: {exc}")
                    page.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._prepare_tables(page)
                if hasattr(page, "navigate_requested"):
                    page.navigate_requested.connect(self._navigate)
                self._pages[page_id] = page
                self._stack.addWidget(page)
            else:
                placeholder = QLabel(f"Sayfa bulunamadi: {page_id}")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._pages[page_id] = placeholder
                self._stack.addWidget(placeholder)
        return self._pages[page_id]

    @staticmethod
    def _prepare_tables(page: QWidget):
        """Apply one predictable, read-only interaction across data views."""
        tones = ("blue", "green", "amber", "violet")
        for index, card in enumerate(page.findChildren(QFrame, "metricCard")):
            card.setProperty("tone", tones[index % len(tones)])
            card.style().unpolish(card)
            card.style().polish(card)
        for view in page.findChildren(QAbstractItemView):
            view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            view.setTextElideMode(Qt.TextElideMode.ElideRight)
        for table in page.findChildren(QTableWidget):
            apply_professional_table(table)

    def _navigate(self, page_id: str):
        if self._current_page == page_id:
            return
        self._current_page = page_id
        page = self._get_page(page_id)
        product_filter = getattr(page, "set_product_filter", None)
        if callable(product_filter):
            product_filter(self._active_product)
        self._stack.setCurrentWidget(page)

        # Nav buton stillerini guncelle
        for pid, btn in self._nav_btns.items():
            btn.setProperty("active", pid == page_id)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Header basligini guncelle
        labels = {pid: label for pid, _, label in _NAV_ITEMS}
        self._header_title.setText(labels.get(page_id, ""))
        self._apply_reference_header_layout(page_id)

    def _apply_reference_header_layout(self, page_id: str):
        is_license = page_id == "license_requests"
        is_console = page_id in {"backups", "updates", "limits", "server_settings"}
        self._top_bar.setFixedHeight(48 if is_license else 56)
        self._global_search.setFixedWidth(256 if is_license else 288 if is_console else 320)
        self._top_bar.setProperty("referenceStyle", "license" if is_license else "console" if is_console else "standard")
        if hasattr(self, "_header_col"):
            self._header_col.takeAt(0)
            header_width = 0 if is_license else 138 if is_console else 259
            self._header_col.insertItem(0, QSpacerItem(
                header_width, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum
            ))
        if hasattr(self, "_top_bar_layout"):
            if is_license and not self._header_col_removed:
                self._top_bar_layout.takeAt(0)
                self._header_col_removed = True
            elif not is_license and self._header_col_removed:
                self._top_bar_layout.insertLayout(0, self._header_col)
                self._header_col_removed = False
            self._top_bar_layout.setContentsMargins(4 if is_license else 44 if is_console else 40, 0, 16, 0)
            self._top_bar_layout.setSpacing(0 if is_license else 8)
            self._top_bar_layout.setAlignment(Qt.AlignmentFlag.AlignLeft if is_license else Qt.AlignmentFlag(0))
            after_search = 1 if self._header_col_removed else 2
            if is_license and not self._license_gap_active:
                self._top_bar_layout.insertSpacing(after_search, 12)
                self._license_gap_active = True
            elif not is_license and self._license_gap_active:
                self._top_bar_layout.takeAt(after_search)
                self._license_gap_active = False
            if is_license and self._header_flex_active:
                self._top_bar_layout.takeAt(after_search + (1 if self._license_gap_active else 0))
                self._header_flex_active = False
            if is_console and not self._header_flex_active:
                self._top_bar_layout.insertStretch(after_search, 1)
                self._header_flex_active = True
            elif not is_console and self._header_flex_active:
                self._top_bar_layout.takeAt(after_search + (1 if self._license_gap_active else 0))
                self._header_flex_active = False
            self._top_bar_layout.invalidate()
            self._top_bar_layout.activate()
        if hasattr(self, "_header_eyebrow"):
            self._header_eyebrow.setVisible(not is_license)
            if is_license:
                self._header_eyebrow.setFixedWidth(0)
                self._header_title.setFixedWidth(0)
            else:
                self._header_eyebrow.setMinimumWidth(0)
                self._header_eyebrow.setMaximumWidth(16777215)
                self._header_title.setMinimumWidth(0)
                self._header_title.setMaximumWidth(16777215)
            self._header_eyebrow.setText(
                "KONSOL  /  Y\u00d6NET\u0130M"
                if is_console else "Sistem  /  Yonetim Konsolu  /  Canl\u0131 Izleme"
            )
        self._top_bar.style().unpolish(self._top_bar)
        self._top_bar.style().polish(self._top_bar)

    def closeEvent(self, event):
        timer = getattr(self, "_header_status_timer", None)
        if timer:
            timer.stop()
        worker = getattr(self, "_header_status_thread", None)
        if worker and worker.isRunning():
            worker.wait(5000)
        super().closeEvent(event)

    def _logout(self):
        reply = QMessageBox.question(self, "Cikis", "Oturumu kapatmak istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            api_client.logout()
            self.close()
            self.logged_out.emit()
