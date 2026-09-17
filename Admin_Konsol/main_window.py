"""
AYEC Pro Admin Konsol - Ana Pencere
Tum sayfalar sol sidebar + icerik alani yap\u0131s\u0131nda burada bir araya getirilir.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QSizePolicy,
    QSpacerItem, QMessageBox, QTableWidget, QAbstractItemView, QComboBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

import config
import api_client
from product_catalog import product_names

from pages.dashboard import DashboardPage
from pages.companies import CompaniesPage
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
#topBar { background: #0e1b2f; border-bottom: 1px solid #263a58; }
#pageHeaderTitle { color: #f4f8ff; font-size: 18px; font-weight: 800; }
#headerEyebrow { color: #6f8dad; font-size: 9px; font-weight: 800;
                 letter-spacing: 1px; }
#serverStatus { background: #112541; border: 1px solid #315477;
                border-radius: 12px; }
#serverDot { color: #35d399; font-size: 16px; }
#serverCaption { color: #7f9ab9; font-size: 9px; font-weight: 800; }
#serverUrl { color: #cfe3ff; font-size: 11px; font-weight: 700; }

/* Content area */
#contentArea { background: #091322; }

/* Page titles */
#pageTitle { color: #f7faff; font-size: 25px; font-weight: 800; margin-bottom: 4px; }
#pageSubtitle { color: #8da3c0; font-size: 12px; }
#sectionTitle { color: #9db0ca; font-size: 13px; font-weight: 700;
                text-transform: uppercase; letter-spacing: 1px; }
#panelTitle { color: #f4f8ff; font-size: 16px; font-weight: 800; }

/* Panels */
#leftPanel { background: #101b2f; border-right: 1px solid #22304a; }
#detailPanel { background: #0b1220; }
#detailTitle { color: #f4f8ff; font-size: 19px; font-weight: 800; }

/* Cards */
#metricCard { background: #10213a; border: 1px solid #294463;
              border-radius: 16px; min-height: 112px; }
#metricCard:hover { background: #122744; border: 1px solid #4e80c9; }
#metricCard[tone="blue"] { border-left: 3px solid #5b9df5; }
#metricCard[tone="green"] { border-left: 3px solid #35c99a; }
#metricCard[tone="amber"] { border-left: 3px solid #f2b84b; }
#metricCard[tone="violet"] { border-left: 3px solid #9a7cf5; }
#metricTitle { color: #9db0ca; font-size: 12px; }
#metricValue { color: #f4f8ff; font-size: 24px; font-weight: 800; }
#metricSub { color: #7890b1; font-size: 11px; }
#statusCard { background: #111f35; border: 1px solid #263b5b;
              border-radius: 14px; min-height: 86px; }
#statusCard:hover { border: 1px solid #4e80c9; }
#cardName { color: #f4f8ff; font-size: 14px; font-weight: 700; }
#cardStatus { font-size: 12px; font-weight: bold; }
#cardDetail { color: #7890b1; font-size: 11px; }
#formCard, #ctrlFrame { background: #10213a; border: 1px solid #294463;
            border-radius: 16px; }
#detailCard, #tableCard { background: #0f1d31; border: 1px solid #294463;
              border-radius: 14px; }
#card { background: #10213a; border: 1px solid #294463; border-radius: 14px; }
#tableToolbar { background: #10213a; border: none;
                border-bottom: 1px solid #294463; }
#selectionInfo { color: #cfe3ff; background: #132d4d;
                 border: 1px solid #31577d; border-radius: 9px;
                 padding: 8px 12px; font-size: 12px; }
#groupBox { color: #9db0ca; font-size: 11px; border: 1px solid #263b5b;
            border-radius: 10px; margin-top: 12px; padding-top: 12px; }
#groupBox::title { color: #8bb8ff; subcontrol-origin: margin;
                   subcontrol-position: top left; padding: 0 6px; left: 12px; }

/* Tables */
#dataTable, QTableWidget { background: #0f1c31; border: 1px solid #294463;
             border-radius: 14px; gridline-color: transparent;
             selection-background-color: transparent; selection-color: #ffffff;
             outline: none; }
#dataTable QHeaderView::section, QTableWidget QHeaderView::section {
    background: #182d4b; color: #c8d7ea; border: none;
    border-bottom: 1px solid #365779; padding: 11px 12px; font-size: 11px;
    font-weight: 800; }
#dataTable::item, QTableWidget::item { padding: 10px 12px; color: #edf4ff; }
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
#companyBtn { background: #111f35; color: #9db0ca; border: none;
              border-radius: 6px; padding: 10px 12px; text-align: left;
              font-size: 13px; }
#companyBtn:hover { background: #1b3558; color: #ffffff; }
#companyBtn:checked { background: #2455a5; color: #ffffff; font-weight: bold; }
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

    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_NAME)
        self.setMinimumSize(1240, 780)
        self.resize(1440, 900)
        self.setStyleSheet(_STYLESHEET)
        self._pages: dict[str, QWidget] = {}
        self._nav_btns: dict[str, QPushButton] = {}
        self._current_page = ""
        self._active_product = "AYEC Pro Teknik Servis"
        self._build_ui()
        self._navigate("dashboard")

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
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(78)
        top_bar_lay = QHBoxLayout(top_bar)
        top_bar_lay.setContentsMargins(28, 0, 28, 0)

        header_col = QVBoxLayout()
        header_col.setSpacing(2)
        header_eyebrow = QLabel("AYEC PRO  /  YONETIM MERKEZI")
        header_eyebrow.setObjectName("headerEyebrow")
        header_col.addWidget(header_eyebrow)
        self._header_title = QLabel("Dashboard")
        self._header_title.setObjectName("pageHeaderTitle")
        header_col.addWidget(self._header_title)
        top_bar_lay.addLayout(header_col)
        top_bar_lay.addStretch()

        self._product_selector = QComboBox()
        self._product_selector.setToolTip("Yonetilecek urunu secin")
        self._product_selector.addItems(product_names())
        self._product_selector.currentTextChanged.connect(self._product_changed)
        top_bar_lay.addWidget(self._product_selector)

        server_status = QFrame()
        server_status.setObjectName("serverStatus")
        server_lay = QHBoxLayout(server_status)
        server_lay.setContentsMargins(13, 7, 15, 7)
        server_lay.setSpacing(9)
        server_dot = QLabel("\u25cf")
        server_dot.setObjectName("serverDot")
        server_lay.addWidget(server_dot)
        server_text = QVBoxLayout()
        server_text.setSpacing(0)
        server_caption = QLabel("CANLI SUNUCU")
        server_caption.setObjectName("serverCaption")
        server_text.addWidget(server_caption)
        server_url = QLabel(config.server_url())
        server_url.setObjectName("serverUrl")
        server_text.addWidget(server_url)
        server_lay.addLayout(server_text)
        top_bar_lay.addWidget(server_status)
        right_lay.addWidget(top_bar)

        # Stacked pages
        self._stack = QStackedWidget()
        self._stack.setObjectName("contentArea")
        right_lay.addWidget(self._stack, 1)

        outer.addWidget(right, 1)

    def _product_changed(self, product_name: str):
        """Keep a single product context for the shared admin shell."""
        self._active_product = str(product_name or "AYEC Pro Teknik Servis")
        self._header_title.setToolTip("Urun: " + self._active_product)
        for page in self._pages.values():
            setter = getattr(page, 'set_product_filter', None)
            if setter:
                setter(self._active_product)

    def _get_page(self, page_id: str) -> QWidget:
        if page_id not in self._pages:
            constructors = {
                "dashboard":       DashboardPage,
                "companies":       CompaniesPage,
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
                page = cls()
                self._prepare_tables(page)
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
        self._stack.setCurrentWidget(page)

        # Nav buton stillerini guncelle
        for pid, btn in self._nav_btns.items():
            btn.setProperty("active", pid == page_id)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Header basligini guncelle
        labels = {pid: label for pid, _, label in _NAV_ITEMS}
        self._header_title.setText(labels.get(page_id, ""))

    def _logout(self):
        reply = QMessageBox.question(self, "Cikis", "Oturumu kapatmak istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            api_client.logout()
            self.close()
            self.logged_out.emit()
