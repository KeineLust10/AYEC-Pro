# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QStackedWidget, 
                             QDialog, QVBoxLayout, QLabel, 
                             QPushButton, QInputDialog)
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from PyQt6.QtGui import QKeySequence, QDesktopServices, QShortcut
from src.utils import message_helper

from PyQt6.QtCore import QTimer, QUrl, QPropertyAnimation, QEasingCurve
from datetime import datetime

from src.database import Database
from src.email_service import EmailService
from src.ui.pages.dashboard_page import DashboardPage
from src.ui.pages.summary_page import SummaryPage           # Yeni
from src.ui.pages.services_page import ServicesPage         # Yeni (Hizmet ve Fiyatlar)
from src.ui.pages.accounting_page import AccountingPage
from src.ui.pages.stock_page import StockPage               # Yeni
from src.ui.pages.personnel_page import PersonnelPage
from src.ui.pages.reports_page import ReportsPage
from src.ui.pages.appointments_page import AppointmentsPage
from src.ui.pages.customers_page import CustomersPage # Yeni Müşteri Sayfası
from src.ui.pages.knowledge_base_page import KnowledgeBasePage # Yeni
from src.ui.pages.ai_assistant_page import AIAssistantPage # Yeni (AI)
from src.ui.pages.backup_page import BackupPage # Yeni (Backup)

from src.ui.pages.support_page import SupportPage             # Yeni
from src.ui.pages.service_board_page import ServiceBoardPage # Yeni
from src.ui.pages.service_status_page import ServiceStatusPage # Yeni - Image 0
from src.ui.pages.settings_page import SettingsPage
from src.ui.widgets.toast_notification import NotificationContainer
from src.utils.logger import logger, NotificationHandler
from src.ui.widgets.jarvis_sidebar import JarvisSidebar
from src.ui.widgets.side_menu import SideMenu
from PyQt6.QtGui import QResizeEvent, QFont

class MainWindow(QMainWindow):
    def __init__(self, db, user_data):
        super().__init__()
        self.db = db
        self.email_service = EmailService(self.db)
        self.user_data = user_data # (id, username, password, role, created_at)
        self.dark_mode = False
        self.setWindowTitle(f"BulutTech Teknik Servis Takip V2 - {user_data[1]} ({user_data[3]})")
        self.resize(1400, 900)
        
        container = QWidget()
        self.setCentralWidget(container)
        self.main_layout = QHBoxLayout(container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self._dialog_open = False # Debounce flag for dialogs
        self._switching = False   # Debounce flag for page switching
        
        self.stack = QStackedWidget()
        
        # Sayfaları oluştur
        self.page_dashboard = DashboardPage(self.db, self)        # Index 0
        self.page_summary = SummaryPage(self.db, self)            # Index 1
        self.page_accounting = AccountingPage(self.db)            # Index 2
        self.page_personnel = PersonnelPage(self.db)              # Index 3
        self.page_reports = ReportsPage(self.db)                  # Index 4
        self.page_appointments = AppointmentsPage(self.db)        # Index 5
        self.page_settings = SettingsPage(self.db)                # Index 6
        self.page_services = ServicesPage(self.db)                # Index 7
        self.page_stock = StockPage(self.db)                      # Index 8
        self.page_kb = KnowledgeBasePage(self.db)                 # Index 9

        self.page_support = SupportPage(self.db)                  # Index 11
        self.page_service_board = ServiceBoardPage(self.db, self) # Index 12
        self.page_customers = CustomersPage(self.db, self)        # Index 13
        self.page_status_screen = ServiceStatusPage(self.db, self)# Index 14 (New)
        self.page_ai = AIAssistantPage(self.db)                   # Index 15
        self.page_backup = BackupPage(self.db)                    # Index 16
        
        # Stack'e ekle
        self.stack.addWidget(self.page_dashboard)     # 0
        self.stack.addWidget(self.page_summary)       # 1
        self.stack.addWidget(self.page_accounting)    # 2
        self.stack.addWidget(self.page_personnel)     # 3
        self.stack.addWidget(self.page_reports)       # 4
        self.stack.addWidget(self.page_appointments)  # 5
        self.stack.addWidget(self.page_settings)      # 6
        self.stack.addWidget(self.page_services)      # 7
        self.stack.addWidget(self.page_stock)         # 8
        self.stack.addWidget(self.page_kb)            # 9

        self.stack.addWidget(self.page_support)       # 11
        self.stack.addWidget(self.page_service_board) # 12
        self.stack.addWidget(self.page_customers)     # 13
        self.stack.addWidget(self.page_status_screen) # 14
        self.stack.addWidget(self.page_ai)            # 15
        self.stack.addWidget(self.page_backup)        # 16
        
        self.side_menu = SideMenu(self.switch_page)
        # self.side_menu.page_selected.connect(self.switch_page) # Removed as SideMenu uses callback
        
        self.main_layout.addWidget(self.side_menu)
        self.main_layout.addWidget(self.stack)
        
        # Jarvis Sidebar (Initially Hidden)
        self.jarvis_sidebar = JarvisSidebar(self.db, self)
        self.jarvis_sidebar.setVisible(False)
        self.main_layout.addWidget(self.jarvis_sidebar)
        
        # Notifications Overlay
        self.toast = NotificationContainer(self)
        self.toast.resize(400, 900) # Initial size, will be updated in resizeEvent
        self.toast.raise_()
        
        # Log Watcher Integration
        if self.db.get_setting("jarvis_log_watcher_enabled", "0") == "1":
            self.log_handler = NotificationHandler(self.show_notification)
            logger.addHandler(self.log_handler)
        
        QTimer.singleShot(1000, self.check_notifications)
        self.setup_shortcuts()
        self.apply_theme()

    def reinit_log_watcher(self):
        """Update Log Watcher status based on current settings."""
        # Remove old handler if exists
        if hasattr(self, 'log_handler'):
            logger.removeHandler(self.log_handler)
            
        if self.db.get_setting("jarvis_log_watcher_enabled", "0") == "1":
            self.log_handler = NotificationHandler(self.show_notification)
            logger.addHandler(self.log_handler)
            logger.info("Log Watcher aktif edildi.")
        else:
            logger.info("Log Watcher devre dışı bırakıldı.")

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if hasattr(self, 'toast'):
            self.toast.setGeometry(0, 0, self.width(), self.height())

    def toggle_jarvis(self):
        """Jarvis panelini aç/kapat"""
        if not hasattr(self, 'jarvis_sidebar'): return
        
        is_visible = self.jarvis_sidebar.isVisible()
        
        if not is_visible:
            self.jarvis_sidebar.setVisible(True)
            self.jarvis_sidebar.setFixedWidth(0)
            self.jarvis_anim = QPropertyAnimation(self.jarvis_sidebar, b"minimumWidth")
            self.jarvis_anim.setDuration(300)
            self.jarvis_anim.setStartValue(0)
            self.jarvis_anim.setEndValue(350)
            self.jarvis_anim.setEasingCurve(QEasingCurve.Type.OutQuart)
            
            self.jarvis_anim_max = QPropertyAnimation(self.jarvis_sidebar, b"maximumWidth")
            self.jarvis_anim_max.setDuration(300)
            self.jarvis_anim_max.setStartValue(0)
            self.jarvis_anim_max.setEndValue(350)
            
            self.jarvis_anim.start()
            self.jarvis_anim_max.start()
        else:
            self.jarvis_anim = QPropertyAnimation(self.jarvis_sidebar, b"minimumWidth")
            self.jarvis_anim.setDuration(250)
            self.jarvis_anim.setStartValue(350)
            self.jarvis_anim.setEndValue(0)
            self.jarvis_anim.finished.connect(lambda: self.jarvis_sidebar.setVisible(False))
            
            self.jarvis_anim_max = QPropertyAnimation(self.jarvis_sidebar, b"maximumWidth")
            self.jarvis_anim_max.setDuration(250)
            self.jarvis_anim_max.setStartValue(350)
            self.jarvis_anim_max.setEndValue(0)
            
            self.jarvis_anim.start()
            self.jarvis_anim_max.start()
            
    def show_notification(self, message, toast_type="info", duration=4000, action=None):
        if hasattr(self, 'toast'):
            self.toast.add_notification(message, toast_type, duration, action)

    def setup_shortcuts(self):
        # Sayfa Geçişleri
        QShortcut(QKeySequence("F1"), self, activated=lambda: self.switch_page(0))
        QShortcut(QKeySequence("F2"), self, activated=lambda: self.switch_page(1))
        QShortcut(QKeySequence("F3"), self, activated=lambda: self.switch_page(2))
        QShortcut(QKeySequence("F4"), self, activated=lambda: self.switch_page(3))
        
        # Dashboard Aksiyonları
        QShortcut(QKeySequence("Ctrl+N"), self, activated=lambda: self.page_dashboard.open_add_dialog() if self.stack.currentIndex() == 0 else None)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self.page_dashboard.open_filter_dialog() if self.stack.currentIndex() == 0 else None)

    def switch_page(self, index):
        """
        SideMenu/ModernSidebar'dan gelen indekslere göre sayfa değiştirme.
        """
        if self._switching: return
        self._switching = True
        QTimer.singleShot(300, lambda: setattr(self, '_switching', False))

        # ÇIKI
        if index == -1:
            self.close()
            return

        # ANA İLEMLER
        if index == 40: # Ana Sayfa
            self.stack.setCurrentIndex(0)
        elif index == 45: # Yönetici Özeti
            self.stack.setCurrentIndex(1)
            self.page_summary.refresh_all()
        elif index == 150: # Yeni İşlem (Dialog açar)
            self.open_add_device_dialog()
        elif index == 41: # Servis Talepleri (Board)
            self.stack.setCurrentIndex(12)
        elif index == 42: # Servis Durum Ekranı (Image 0)
            self.stack.setCurrentIndex(14)
            self.page_status_screen.load_data()
        elif index == 60: # Teknisyen Paneli
            self.open_technician_panel()


        # YÖNETİM
        elif index == 10: # Personel Yönetimi
            self.stack.setCurrentIndex(3)
        elif index == 21: # Müşteri Listesi (FULL PAGE)
            self.stack.setCurrentIndex(13) # New Index for CustomersPage
        elif index == 22: # Yeni Müşteri Ekle
            self.open_add_customer_dialog()
        elif index == 30: # Randevu Yönetimi
            self.stack.setCurrentIndex(5)
        elif index == 50: # Stok Yönetimi
            self.stack.setCurrentIndex(8)
        elif index == 160: # Bilgi Bankası
            self.stack.setCurrentIndex(9)
        elif index == 170: # AI Asistan
            self.stack.setCurrentIndex(15)
        elif index == 180: # Yedekleme Merkezi
            self.stack.setCurrentIndex(16)

        # FİNANS
        elif index == 101: # Muhasebe - Genel Durum
            self.stack.setCurrentIndex(2)
            if hasattr(self.page_accounting, 'tabs'): self.page_accounting.tabs.setCurrentIndex(0)
        elif index == 102: # Muhasebe - Gelir/Gider
            self.stack.setCurrentIndex(2)
            if hasattr(self.page_accounting, 'tabs'): self.page_accounting.tabs.setCurrentIndex(0)
        elif index == 103: # Muhasebe - Cari Hesaplar
            self.stack.setCurrentIndex(2)
            if hasattr(self.page_accounting, 'tabs'): self.page_accounting.tabs.setCurrentIndex(1)
        elif index == 140: # Hizmet ve Fiyatlar
            self.stack.setCurrentIndex(7)

        # RAPORLAR
        elif index == 111 or index == 112 or index == 115: # Raporlar
            self.stack.setCurrentIndex(4)

        # İLETİİM / SİSTEM
        elif index == 70: # Teknik Destek
            self.show_support_dialog()
        elif index == 90: # Hatırlatıcılar
            self.check_notifications()
        elif index == 120: # Duyurular
            self.stack.setCurrentIndex(0)
        elif index == 130: # Ayarlar
            self.stack.setCurrentIndex(6)

    def open_add_device_dialog(self):
        if self._dialog_open: return
        self._dialog_open = True
        from src.ui.dialogs.add_device_dialog import AddDeviceDialog
        dialog = AddDeviceDialog(self.db, self)
        if dialog.exec():
            # Refresh if on Service Board
            if self.stack.currentWidget() == self.page_service_board:
                self.page_service_board.refresh_board()
            self.show_notification("Yeni servis kaydı oluşturuldu!", "success")
        self._dialog_open = False

    def open_add_customer_dialog(self):
        if self._dialog_open: return
        self._dialog_open = True
        from src.ui.dialogs.add_customer_dialog import AddCustomerDialog
        dialog = AddCustomerDialog(self.db, self)
        if dialog.exec():
            # Refresh if on Customer Page
            if self.stack.currentWidget() == self.page_customers:
                self.page_customers.load_data()
            self.show_notification("Müşteri başarıyla eklendi!", "success")
        self._dialog_open = False
        
    def open_technician_panel(self):
        if self._dialog_open: return
        self._dialog_open = True
        
        # Ask for Tracking No or ID
        device_id, ok = QInputDialog.getText(self, "Teknisyen Paneli", "İşlem yapılacak Takip No veya ID giriniz:")
        if ok and device_id:
            try:
                # Find device by tracking no or ID
                self.db.cursor.execute("SELECT * FROM devices WHERE tracking_no=? OR id=?", (device_id, device_id))
                row = self.db.cursor.fetchone()
                if row:
                    # TechnicianPanel expects a tuple, as it accesses indices like data[1], data[12] etc.
                    # So we must pass the raw 'row' tuple, not the 'dev_data' dict.
                    
                    from src.ui.dialogs.technician_panel import TechnicianPanel
                    dialog = TechnicianPanel(self.db, row, self)
                    dialog.exec()
                else:
                    self.show_notification("Cihaz bulunamadı!", "error")
            except Exception as e:
                self.show_notification(f"Hata: {e}", "error")
        
        self._dialog_open = False

    def show_support_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Teknik Destek & Yardım")
        dialog.setFixedSize(450, 480)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("Bize Ulaşın")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Phone
        btn_phone = QPushButton("0534 878 10 47 (Ara)")
        btn_phone.setFixedHeight(45)
        btn_phone.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        btn_phone.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("tel:05348781047")))
        layout.addWidget(btn_phone)
        
        # Email
        btn_mail = QPushButton("✉ gnnckrk@gmail.com (E-Posta)")
        btn_mail.setFixedHeight(45)
        btn_mail.setStyleSheet("background-color: #3498db; color: white; font-weight: bold;")
        btn_mail.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("mailto:gnnckrk@gmail.com")))
        layout.addWidget(btn_mail)
        
        # Portal Link
        btn_portal = QPushButton(" Web Destek Portalı")
        btn_portal.setFixedHeight(40)
        btn_portal.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://buluttech.com/destek")))
        layout.addWidget(btn_portal)
        
        # Remote Support
        hbox_remote = QHBoxLayout()
        btn_tv = QPushButton("TeamViewer")
        btn_tv.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.teamviewer.com")))
        btn_ad = QPushButton("AnyDesk")
        btn_ad.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://anydesk.com")))
        hbox_remote.addWidget(btn_tv)
        hbox_remote.addWidget(btn_ad)
        layout.addLayout(hbox_remote)
        
        # Live Support (Simulated)
        btn_live = QPushButton("💬 Canlı Destek Başlat")
        btn_live.setFixedHeight(50)
        btn_live.setStyleSheet("background-color: #f1c40f; color: #2c3e50; font-weight: bold;")
        btn_live.clicked.connect(lambda: message_helper.show_info(dialog, "Canlı Destek", "Müşteri temsilcisine bağlanılıyor..."))
        layout.addWidget(btn_live)
        
        layout.addStretch()
        dialog.exec()

    def send_feedback(self):
        msg, ok = QInputDialog.getMultiLineText(self, "Geri Bildirim", "Mesajınız:")
        if ok and msg:
            # Geliştiriciye mail at (örnek adres)
            developer_email = "destek@buluttech.com" # Burası örnek
            success, info = self.email_service.send_email(developer_email, "Geri Bildirim", msg)
            if success:
                message_helper.show_info(self, "Başarılı", "Geri bildiriminiz iletildi. Teşekkürler!")
            else:
                message_helper.show_warning(self, "Hata", info)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        if hasattr(self.page_dashboard, 'refresh_data'):
            self.page_dashboard.refresh_data()

    def apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #2c3e50; color: white; }
                QTableWidget { background-color: #34495e; color: white; gridline-color: #5d6d7e; }
                QLineEdit { background-color: #34495e; color: white; }
                QHeaderView::section { background-color: #2c3e50; color: white; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #f0f2f5; color: black; }
                QTableWidget { background-color: white; color: black; }
                QLineEdit { background-color: white; color: black; }
                QHeaderView::section { background-color: #34495e; color: white; }
            """)
        self.side_menu.setStyleSheet("background-color: #2c3e50; color: white;")

    def check_notifications(self):
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            self.db.cursor.execute("SELECT tracking_no, customer_name FROM devices WHERE estimated_date <= ? AND status != 'Tamamland'", (today,))
            overdue = self.db.cursor.fetchall()
            if overdue:
                msg = f"{len(overdue)} adet cihazn teslim tarihi geldi veya geti!\n"
                for trk, name in overdue[:3]:
                    msg += f"- {name} ({trk})\n"
                if len(overdue) > 3:
                    msg += "..."
                message_helper.show_warning(self, "Hatrlatma", msg)
        except Exception as e:
            logger.error(f"Bildirim hatas: {e}")

