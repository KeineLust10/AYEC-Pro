# -*- coding: utf-8 -*-

"""
Backup Settings Widget
Veri yedekleme ayarlari widget'
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QLineEdit,
    QHBoxLayout, QCheckBox, QTimeEdit, QFrame, QGridLayout, QSizePolicy, QGroupBox,
)
from PyQt6.QtGui import QFont, QIcon, QAction
from PyQt6.QtCore import Qt, QTime, QTimer, QThread, pyqtSignal
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_success, show_error, show_info
import shutil
import os
from datetime import datetime
from src.utils.path_helper import PathHelper
from src.utils.logger import logger

try:
    from src.utils.backup_scheduler import BackupScheduler
    from src.utils.cloud_backup import get_cloud_backup_manager
except ImportError:
    BackupScheduler = None
    get_cloud_backup_manager = None


class WipeDataWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db

    def run(self):
        try:
            success = bool(self.db.wipe_all_user_data())
            self.finished.emit(success, "" if success else "wipe_failed")
        except Exception as exc:
            self.finished.emit(False, str(exc))


class RemoteWipeDataWorker(QThread):
    finished = pyqtSignal(bool, object)

    def __init__(self, db, password, parent=None):
        super().__init__(parent)
        self.db = db
        self.password = str(password or "")

    def run(self):
        try:
            from src.utils.desktop_web_sync import configured_sync_url, sync_session_path
            from src.utils.web_sync_client import WebSyncClient

            url = configured_sync_url()
            client = WebSyncClient(
                url,
                verify_tls=not url.lower().startswith("http://"),
                timeout=120,
            )
            client.load_session(sync_session_path())
            if not client.cookies:
                raise RuntimeError(
                    "Sunucu oturumu bulunamadi. Once web senkronizasyonunda oturum acin."
                )
            result = client.wipe_tenant_data(self.password)
            local_success = bool(self.db.wipe_all_user_data())
            if not local_success:
                raise RuntimeError(
                    "Sunucu temizlendi ancak yerel veritabani temizlenemedi. "
                    "Sonraki senkronizasyon yerel verileri guvenli bicimde sifirlayacak."
                )
            self.finished.emit(True, result)
        except Exception as exc:
            self.finished.emit(False, {"error": str(exc)})


class BackupSettingsWidget(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    """Veri Yedekleme Ayarlari Widget"""
    
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self._wipe_worker = None
        self._remote_wipe_worker = None
        self.init_ui()
        
    def _init_ui_legacy(self):
        # Helper for Card Styling
        def create_settings_card(title, auto_chk):
            frame = QFrame()
            frame.setStyleSheet(theme_qss("QFrame { background: @surface; border: 1px solid @border; border-radius: 12px; }"))
            l = QVBoxLayout(frame)
            l.setSpacing(10)
            l.setContentsMargins(20, 20, 20, 20)
            lbl = QLabel(title)
            lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            lbl.setStyleSheet(theme_qss("color: @text; border: none;"))
            l.addWidget(lbl)
            l.addWidget(auto_chk)
            return frame

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header
        title = QLabel("Yedekleme ve Veri Merkezi")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(title)
        
        # --- Local Data Management (Export/Import) ---
        grp_local = QGroupBox("Yerel Veri Islemleri (Ice / Disa Aktar)")
        grp_local.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        grp_local.setStyleSheet(theme_qss("QGroupBox { background-color: @surface_alt; border: 1px solid @border; border-radius: 8px; margin-top: 15px; padding-top: 25px; font-weight: bold; }"))
        local_layout = QHBoxLayout(grp_local)
        local_layout.setSpacing(15)
        
        # Export Button (Veri Yedekle)
        from PyQt6.QtGui import QIcon
        btn_backup = QPushButton("Veri Yedekle (Disa Aktar)")
        btn_backup.setStyleSheet(theme_qss("""
            QPushButton { background-color: @success; color: @selection_text; border-radius: 8px; padding: 15px; font-size: 14px; font-weight: bold; text-align: left; padding-left: 20px;}
            QPushButton:hover { background-color: @success; }
        """))
        btn_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_backup.clicked.connect(self.backup)
        local_layout.addWidget(btn_backup)
        
        # Import Button (Veri Geri Yukle)
        btn_restore = QPushButton("Veri Geri Yukle (Ice Aktar)")
        btn_restore.setStyleSheet(theme_qss("""
            QPushButton { background-color: @accent_hover; color: @selection_text; border-radius: 8px; padding: 15px; font-size: 14px; font-weight: bold; text-align: left; padding-left: 20px;}
            QPushButton:hover { background-color: @accent_pressed; }
        """))
        btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restore.clicked.connect(self.restore)
        local_layout.addWidget(btn_restore)
        
        layout.addWidget(grp_local)
        
        # --- Remote Server & Upload ---
        grp_remote = QGroupBox("Sunucu ve AYEC Islemleri")
        grp_remote.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        grp_remote.setStyleSheet(theme_qss("QGroupBox { background-color: @surface; border: 1px solid @border; border-radius: 8px; margin-top: 15px; padding-top: 25px; font-weight: bold; }"))
        remote_layout = QVBoxLayout(grp_remote)
        remote_layout.setSpacing(15)
        
        # IP Configuration Row
        ip_layout = QHBoxLayout()
        lbl_ip = QLabel("Sunucu IP Adresi:")
        lbl_ip.setFont(QFont("Segoe UI", 10))
        self.inp_backup_ip = QLineEdit()
        self.inp_backup_ip.setPlaceholderText("Orn: 85.117.XXX.XXX")
        self.inp_backup_ip.setStyleSheet(theme_qss("padding: 10px; border: 1px solid @border; border-radius: 6px; font-size: 13px;"))
        
        self.btn_save_remote = QPushButton("Manuel Yapilandir / Kaydet")
        self.btn_save_remote.setStyleSheet(theme_qss("background-color: @accent; color: @selection_text; padding: 10px 20px; border-radius: 6px; font-weight: bold;"))
        self.btn_save_remote.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_remote.clicked.connect(self.save_remote_settings)
        
        ip_layout.addWidget(lbl_ip)
        ip_layout.addWidget(self.inp_backup_ip, 1) # Stretch settings
        ip_layout.addWidget(self.btn_save_remote)
        remote_layout.addLayout(ip_layout)
        
        # Upload Button
        self.btn_send_now = QPushButton("Sunucuya Aktar (Yukle)")
        self.btn_send_now.setStyleSheet(theme_qss("""
            QPushButton { background-color: @accent; color: @selection_text; border-radius: 6px; padding: 12px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: @accent_pressed; }
        """))
        self.btn_send_now.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send_now.clicked.connect(self.send_to_remote_now)
        remote_layout.addWidget(self.btn_send_now)
        
        layout.addWidget(grp_remote)
        
        # --- NEW: Google Drive Integration ---
        grp_gdrive = QGroupBox("Google Drive Yedekleme")
        grp_gdrive.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        grp_gdrive.setStyleSheet(theme_qss("QGroupBox { background-color: @surface_alt; border: 1px solid @border; border-radius: 8px; margin-top: 15px; padding-top: 25px; font-weight: bold; }"))
        gdrive_layout = QHBoxLayout(grp_gdrive)
        gdrive_layout.setSpacing(15)
        
        # 1. API Upload Button
        btn_gdrive_api = QPushButton("API Dosyasi Sec (credentials.json)")
        btn_gdrive_api.setStyleSheet(theme_qss("""
            QPushButton { background-color: @surface_alt; color: @text; border-radius: 8px; padding: 15px; font-size: 14px; font-weight: bold; text-align: left; padding-left: 20px;}
            QPushButton:hover { background-color: @window; }
        """))
        btn_gdrive_api.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_gdrive_api.clicked.connect(self.upload_gdrive_credentials)
        gdrive_layout.addWidget(btn_gdrive_api)
        
        # 2. Backup to Drive Button
        btn_gdrive_backup = QPushButton("Drive'a Yedekle")
        btn_gdrive_backup.setStyleSheet(theme_qss("""
            QPushButton { background-color: @danger; color: @selection_text; border-radius: 8px; padding: 15px; font-size: 14px; font-weight: bold; text-align: left; padding-left: 20px;}
            QPushButton:hover { background-color: @danger; }
        """))
        btn_gdrive_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_gdrive_backup.clicked.connect(self.send_to_gdrive_now)
        gdrive_layout.addWidget(btn_gdrive_backup)
        
        layout.addWidget(grp_gdrive)

        # --- Automatic Schedule (Collapsible-ish or just below) ---
        grp_auto = QGroupBox("Otomatik Yedekleme Zamanlayici")
        grp_auto.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        grp_auto.setStyleSheet(theme_qss("QGroupBox { background-color: @surface; border: 1px solid @border; border-radius: 8px; margin-top: 15px; padding-top: 25px; }"))
        auto_chk_layout = QHBoxLayout(grp_auto)
        
        # Custom Time Selector
        self.chk_daily = QCheckBox("Gunluk Otomatik Yedekleme")
        self.chk_daily.setStyleSheet(theme_qss("font-size: 13px; font-weight: 500;"))
        
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setFont(QFont("Segoe UI", 12))
        
        # Enable time edit only if checkbox is checked
        self.chk_daily.toggled.connect(self.time_edit.setEnabled)
        self.time_edit.setEnabled(False) # Initial state set in load_settings
        
        self.chk_on_exit = QCheckBox("Programdan Cikista")
        self.chk_on_exit.setStyleSheet(theme_qss("font-size: 13px; font-weight: 500;"))
        
        btn_save_auto = QPushButton("Zamanlayiciyi Guncelle")
        btn_save_auto.setStyleSheet(theme_qss("background-color: @disabled_text; color: @selection_text; padding: 8px 15px; border-radius: 4px; font-weight: bold;"))
        btn_save_auto.clicked.connect(self.save_auto_settings)
        
        auto_chk_layout.addWidget(self.chk_daily)
        auto_chk_layout.addWidget(self.time_edit)
        auto_chk_layout.addWidget(self.chk_on_exit)
        auto_chk_layout.addStretch()
        auto_chk_layout.addWidget(btn_save_auto)
        
        layout.addWidget(grp_auto)
        
        # --- DANGER ZONE ---
        layout.addSpacing(20)
        grp_danger = QGroupBox("TEHLIKELI BOLGE")
        grp_danger.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        grp_danger.setStyleSheet(theme_qss("""
            QGroupBox { 
                background-color: @surface_alt; 
                border: 2px solid @danger; 
                border-radius: 8px; 
                margin-top: 25px; 
                padding-top: 30px; 
                color: @danger;
            }
        """))
        danger_layout = QVBoxLayout(grp_danger)
        
        danger_desc = QLabel("Asagidaki islem geri alinamaz! Tum musteri, stok ve islem verileriniz kalici olarak silinecektir.")
        danger_desc.setStyleSheet(theme_qss("color: @danger; font-size: 13px; font-weight: 500; margin-bottom: 10px;"))
        danger_layout.addWidget(danger_desc)
        
        self.btn_wipe = QPushButton("TUM VERILERI TEMIZLE (Sifirla)")
        self.btn_wipe.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_wipe.setFixedHeight(50)
        self.btn_wipe.setStyleSheet(theme_qss("""
            QPushButton { 
                background-color: @danger; 
                color: @selection_text; 
                border-radius: 8px; 
                font-weight: bold; 
                font-size: 14px;
            }
            QPushButton:hover { background-color: @danger; }
        """))
        self.btn_wipe.clicked.connect(self.wipe_data)
        danger_layout.addWidget(self.btn_wipe)
        
        layout.addWidget(grp_danger)
        
        layout.addStretch()
        self.load_settings()

    def init_ui(self):
        self.setObjectName("BackupDataCenter")
        self.setStyleSheet(theme_qss("""
            #BackupDataCenter { background: @window; }
            QFrame#DataCard { background: @surface; border: 1px solid @border; border-radius: 12px; }
            QFrame#DataStatus { background: @surface_alt; border: 1px solid @border; border-radius: 10px; }
            QFrame#ResetCard { background: @surface; border: 1px solid @danger; border-radius: 12px; }
            QLabel#PageTitle { color: @text; font-size: 22px; font-weight: 800; }
            QLabel#PageSubtitle, QLabel#CardSubtitle, QLabel#HintText { color: @disabled_text; }
            QLabel#CardTitle { color: @text; font-size: 14px; font-weight: 800; }
            QLabel#StatusValue { color: @text; font-size: 12px; font-weight: 700; }
            QLabel#DangerTitle { color: @danger; font-size: 14px; font-weight: 800; }
            QLineEdit, QTimeEdit { min-height: 34px; padding: 0 10px; background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 8px; }
            QCheckBox { color: @text; spacing: 8px; }
            QPushButton { min-height: 36px; padding: 0 14px; border-radius: 8px; font-weight: 700; }
            QPushButton#PrimaryAction { background: @accent; color: @selection_text; border: 1px solid @accent; }
            QPushButton#PrimaryAction:hover { background: @accent_pressed; }
            QPushButton#SuccessAction { background: @success; color: @selection_text; border: 1px solid @success; }
            QPushButton#SecondaryAction { background: @surface_alt; color: @text; border: 1px solid @border; }
            QPushButton#SecondaryAction:hover { border-color: @accent; }
            QPushButton#DangerAction { background: @danger; color: @selection_text; border: 1px solid @danger; }
            QPushButton#DangerOutline { background: @surface; color: @danger; border: 1px solid @danger; }
        """))

        def title_label(text, object_name="CardTitle"):
            label = QLabel(text)
            label.setObjectName(object_name)
            return label

        def make_card(title, subtitle="", object_name="DataCard"):
            frame = QFrame()
            frame.setObjectName(object_name)
            frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            body = QVBoxLayout(frame)
            body.setContentsMargins(16, 13, 16, 14)
            body.setSpacing(9)
            body.addWidget(title_label(title))
            if subtitle:
                subtitle_label = QLabel(subtitle)
                subtitle_label.setObjectName("CardSubtitle")
                subtitle_label.setWordWrap(True)
                body.addWidget(subtitle_label)
            return frame, body

        def action_button(text, slot, object_name="SecondaryAction"):
            button = QPushButton(text)
            button.setObjectName(object_name)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(slot)
            return button

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(12)
        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        page_title = title_label("Yedekleme ve Veri Merkezi", "PageTitle")
        page_subtitle = title_label(
            "Yerel, sunucu ve zamanlanmis yedekleri tek merkezden yonetin.",
            "PageSubtitle",
        )
        header_text.addWidget(page_title)
        header_text.addWidget(page_subtitle)
        header.addLayout(header_text, 1)
        retention = QLabel("Sunucuda son 7 yedek korunur")
        retention.setObjectName("StatusValue")
        retention.setContentsMargins(12, 7, 12, 7)
        header.addWidget(retention, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(header)

        status_frame = QFrame()
        status_frame.setObjectName("DataStatus")
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(14, 8, 14, 8)
        status_layout.setSpacing(18)
        for heading, value in (
            ("YEREL KORUMA", "Silme oncesi otomatik yedek"),
            ("SUNUCU", "7 surum + 30 gun pre-wipe"),
            ("SENKRON", "Cihaz ve firma silme ayrimi"),
        ):
            block = QVBoxLayout()
            block.setSpacing(1)
            label = QLabel(heading)
            label.setObjectName("HintText")
            detail = QLabel(value)
            detail.setObjectName("StatusValue")
            block.addWidget(label)
            block.addWidget(detail)
            status_layout.addLayout(block, 1)
        root.addWidget(status_frame)

        actions_grid = QGridLayout()
        actions_grid.setHorizontalSpacing(10)
        actions_grid.setVerticalSpacing(10)

        local_card, local_body = make_card(
            "Yerel Yedek",
            "Bu bilgisayarda hizli yedek alin veya bir .db dosyasini geri yukleyin.",
        )
        local_buttons = QHBoxLayout()
        local_buttons.setSpacing(8)
        local_buttons.addWidget(action_button("Yedek Al", self.backup, "SuccessAction"))
        local_buttons.addWidget(action_button("Dosyadan Geri Yukle", self.restore))
        local_body.addLayout(local_buttons)
        actions_grid.addWidget(local_card, 0, 0)

        server_card, server_body = make_card(
            "AYEC Sunucu Yedegi",
            "Sifreli firma oturumuyla veritabanini sunucuya aktarir.",
        )
        server_row = QHBoxLayout()
        server_row.setSpacing(8)
        self.inp_backup_ip = QLineEdit()
        self.inp_backup_ip.setPlaceholderText("85.117.239.60:8000")
        self.btn_save_remote = action_button("Kaydet", self.save_remote_settings)
        server_row.addWidget(self.inp_backup_ip, 1)
        server_row.addWidget(self.btn_save_remote)
        server_body.addLayout(server_row)
        self.btn_send_now = action_button(
            "Simdi Sunucuya Yedekle", self.send_to_remote_now, "PrimaryAction"
        )
        server_body.addWidget(self.btn_send_now)
        actions_grid.addWidget(server_card, 0, 1)

        drive_card, drive_body = make_card(
            "Google Drive",
            "Istege bagli ikinci kopyayi Google Drive hesabinizda saklayin.",
        )
        drive_buttons = QHBoxLayout()
        drive_buttons.setSpacing(8)
        drive_buttons.addWidget(
            action_button("credentials.json Sec", self.upload_gdrive_credentials)
        )
        drive_buttons.addWidget(
            action_button("Drive'a Yedekle", self.send_to_gdrive_now, "PrimaryAction")
        )
        drive_body.addLayout(drive_buttons)
        actions_grid.addWidget(drive_card, 1, 0)

        schedule_card, schedule_body = make_card(
            "Otomatik Yedekleme",
            "Gunluk saati ve program kapanis yedegini birlikte yonetin.",
        )
        schedule_row = QHBoxLayout()
        schedule_row.setSpacing(10)
        self.chk_daily = QCheckBox("Gunluk")
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.chk_daily.toggled.connect(self.time_edit.setEnabled)
        self.chk_on_exit = QCheckBox("Cikista yedekle")
        save_schedule = action_button(
            "Plani Kaydet", self.save_auto_settings, "PrimaryAction"
        )
        schedule_row.addWidget(self.chk_daily)
        schedule_row.addWidget(self.time_edit)
        schedule_row.addWidget(self.chk_on_exit)
        schedule_row.addStretch(1)
        schedule_row.addWidget(save_schedule)
        schedule_body.addLayout(schedule_row)
        actions_grid.addWidget(schedule_card, 1, 1)
        actions_grid.setColumnStretch(0, 1)
        actions_grid.setColumnStretch(1, 1)
        root.addLayout(actions_grid)

        reset_card, reset_body = make_card(
            "Veri Sifirlama ve Kurtarma",
            "Islem turunu dikkatle secin. Firma sifirlama tum bagli cihazlari etkiler.",
            "ResetCard",
        )
        reset_card.findChild(QLabel, "CardTitle").setObjectName("DangerTitle")
        reset_grid = QGridLayout()
        reset_grid.setHorizontalSpacing(8)
        reset_grid.setVerticalSpacing(5)
        reset_grid.addWidget(title_label("Bu bilgisayari sifirla", "StatusValue"), 0, 0)
        reset_grid.addWidget(title_label("Firmayi her yerde sifirla", "StatusValue"), 0, 1)
        reset_grid.addWidget(title_label("Yanlislikla mi silindi?", "StatusValue"), 0, 2)
        local_hint = title_label(
            "Yerel veri silinir; sonraki senkronizasyonda sunucudan geri gelir.",
            "HintText",
        )
        remote_hint = title_label(
            "Sunucu ve tum cihazlar bosaltilir; eski veri tekrar yuklenemez.",
            "HintText",
        )
        restore_hint = title_label(
            "Yerel yedegi secin veya Yonetim Merkezinden sunucu yedegi gonderin.",
            "HintText",
        )
        for column, label in enumerate((local_hint, remote_hint, restore_hint)):
            label.setWordWrap(True)
            reset_grid.addWidget(label, 1, column)
        self.btn_wipe = action_button(
            "Yalniz Bu Cihazi Sifirla", self.wipe_data, "DangerOutline"
        )
        self.btn_wipe_everywhere = action_button(
            "Firma Verilerini Kalici Temizle", self.wipe_everywhere, "DangerAction"
        )
        restore_button = action_button("Yedekten Geri Don", self.restore)
        reset_grid.addWidget(self.btn_wipe, 2, 0)
        reset_grid.addWidget(self.btn_wipe_everywhere, 2, 1)
        reset_grid.addWidget(restore_button, 2, 2)
        reset_grid.setColumnStretch(0, 1)
        reset_grid.setColumnStretch(1, 1)
        reset_grid.setColumnStretch(2, 1)
        reset_body.addLayout(reset_grid)
        root.addWidget(reset_card)
        root.addStretch(1)
        self.load_settings()
        self._wire_ui_signals()

    def wipe_data(self):
        """Tum verileri silme islemi (onay + kullanici sifresi)."""
        from PyQt6.QtWidgets import QDialog
        from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
        from src.ui.dialogs.password_prompt_dialog import PasswordPromptDialog
        from src.utils.auth_manager import AuthManager

        dlg1 = ModernConfirmDialog(
            "Bu Bilgisayari Sifirla",
            "Yalnizca bu bilgisayardaki operasyon verileri temizlenecek.\n"
            "Sunucudaki veriler silinmez ve sonraki senkronizasyonda geri gelir.\n"
            "Devam etmek istiyor musunuz?",
            self,
            confirm_text="Bu Cihazi Sifirla",
            cancel_text="Hayir",
            destructive=True,
        )
        if dlg1.exec() != QDialog.DialogCode.Accepted:
            return

        current_user = getattr(self.main_window, "current_user", {}) or {}
        username = current_user.get("username", "Kullanici")
        full_name = current_user.get("name") or current_user.get("full_name") or username
        pwd_dialog = PasswordPromptDialog(username, full_name, self)
        if pwd_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        auth_manager = AuthManager(self.db)
        auth_manager.current_user = current_user
        if not auth_manager.verify_action_password(pwd_dialog.password_value):
            show_error(self, "Hatali kullanici sifresi! Islem iptal edildi.")
            return

        if self._wipe_worker and self._wipe_worker.isRunning():
            show_info(self, "Veri temizleme islemi zaten calisiyor.")
            return

        self.btn_wipe.setEnabled(False)
        self.btn_wipe.setText("Cihaz temizleniyor...")
        show_info(self, "Veri temizleme baslatildi. Lutfen bekleyin.")
        self._wipe_worker = WipeDataWorker(self.db, self)
        self._wipe_worker.finished.connect(self._on_wipe_finished)
        self._wipe_worker.finished.connect(self._wipe_worker.deleteLater)
        self._wipe_worker.start()

    def _on_wipe_finished(self, success, error_msg):
        self.btn_wipe.setEnabled(True)
        self.btn_wipe.setText("Yalniz Bu Cihazi Sifirla")
        self._wipe_worker = None

        if success:
            show_success(
                self,
                "Bu bilgisayardaki veriler temizlendi. Sunucu verileri korunuyor.",
            )
            if self.main_window:
                QTimer.singleShot(300, self.main_window.handle_wipe_completed)
                QTimer.singleShot(
                    1000,
                    lambda: show_info(
                        None,
                        "Degisikliklerin tam yansimasi icin programi yeniden baslatmaniz onerilir.",
                    ),
                )
            return

        detail = f" ({error_msg})" if error_msg else ""
        show_error(self, f"Veri temizleme sirasinda bir hata olustu.{detail}")

    def wipe_everywhere(self):
        """Clear operational data on the server and every linked desktop."""
        from PyQt6.QtWidgets import QDialog
        from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
        from src.ui.dialogs.password_prompt_dialog import PasswordPromptDialog
        from src.utils.auth_manager import AuthManager

        active_sync = getattr(self.main_window, "_web_sync_worker", None)
        if active_sync and active_sync.isRunning():
            show_info(self, "Senkronizasyon devam ediyor. Tamamlandiktan sonra tekrar deneyin.")
            return
        dialog = ModernConfirmDialog(
            "Firma Verilerini Her Yerde Sifirla",
            "Sunucu, bu bilgisayar ve diger bagli cihazlardaki operasyon verileri "
            "temizlenecek. Silme oncesi yedek 30 gun korunacak ve eski cihazlarin "
            "veriyi geri yuklemesi engellenecek. Devam etmek istiyor musunuz?",
            self,
            confirm_text="Firmayi Her Yerde Sifirla",
            cancel_text="Vazgec",
            destructive=True,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        current_user = getattr(self.main_window, "current_user", {}) or {}
        username = current_user.get("username", "Kullanici")
        full_name = current_user.get("name") or current_user.get("full_name") or username
        password_dialog = PasswordPromptDialog(username, full_name, self)
        if password_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        auth_manager = AuthManager(self.db)
        auth_manager.current_user = current_user
        if not auth_manager.verify_action_password(password_dialog.password_value):
            show_error(self, "Hatali kullanici sifresi! Islem iptal edildi.")
            return
        if self._remote_wipe_worker and self._remote_wipe_worker.isRunning():
            show_info(self, "Firma temizleme islemi zaten calisiyor.")
            return

        self.btn_wipe_everywhere.setEnabled(False)
        self.btn_wipe_everywhere.setText("Firma temizleniyor...")
        show_info(self, "Guvenli sunucu yedegi aliniyor ve firma verileri temizleniyor...")
        self._remote_wipe_worker = RemoteWipeDataWorker(
            self.db,
            password_dialog.password_value,
            self,
        )
        self._remote_wipe_worker.finished.connect(self._on_remote_wipe_finished)
        self._remote_wipe_worker.finished.connect(self._remote_wipe_worker.deleteLater)
        self._remote_wipe_worker.start()

    def _on_remote_wipe_finished(self, success, result):
        self.btn_wipe_everywhere.setEnabled(True)
        self.btn_wipe_everywhere.setText("Firma Verilerini Kalici Temizle")
        self._remote_wipe_worker = None
        if not success:
            show_error(
                self,
                "Firma verileri temizlenemedi: " + str((result or {}).get("error") or "Bilinmeyen hata"),
            )
            return
        backup_id = int((result or {}).get("backup_id") or 0)
        show_success(
            self,
            f"Firma verileri tum cihazlarda sifirlandi. Korunan yedek: #{backup_id}",
        )
        if self.main_window:
            QTimer.singleShot(250, self.main_window.handle_wipe_completed)
            if hasattr(self.main_window, "start_web_sync"):
                QTimer.singleShot(1200, lambda: self.main_window.start_web_sync(silent=True))

    def load_settings(self):
        """Ayarlari database'den yukle"""
        current_ip = self.db.get_setting("backup_server_ip", "85.117.239.60:8000")
        self.inp_backup_ip.setText(current_ip)
        
        # New Settings
        is_daily = self.db.get_setting("backup_daily_enabled", "0") == "1"
        self.chk_daily.setChecked(is_daily)
        
        time_str = self.db.get_setting("backup_daily_time", "12:00")
        try:
             # QTime requires HH:mm
             self.time_edit.setTime(QTime.fromString(time_str, "HH:mm"))
        except Exception:
            self.time_edit.setTime(QTime(12, 0))
             
        self.time_edit.setEnabled(is_daily)

        self.chk_on_exit.setChecked(self.db.get_setting("backup_on_exit", "1") == "1")
        
    def save_auto_settings(self):
        """Otomatik yedekleme ayarlarini kaydet"""
        self.db.set_setting("backup_daily_enabled", "1" if self.chk_daily.isChecked() else "0")
        self.db.set_setting("backup_daily_time", self.time_edit.time().toString("HH:mm"))
        self.db.set_setting("backup_on_exit", "1" if self.chk_on_exit.isChecked() else "0")
        
        # Clear old legacy settings to avoid confusion
        self.db.set_setting("backup_auto_morning", "0")
        self.db.set_setting("backup_auto_evening", "0")
        
        show_success(self, "Otomatik yedekleme ayarlari kaydedildi.")
        
    def save_remote_settings(self):
        """Uzak sunucu IP ayarini kaydet"""
        ip = self.inp_backup_ip.text().strip()
        if ip:
            self.db.set_setting("backup_server_ip", ip)
            show_success(self, "Sunucu IP adresi gncellendi. ")
        else:
            show_error(self, "Lutfen gecerli bir IP girin.")
            
    def send_to_remote_now(self):
        """Hemen buluta gonder"""
        if get_cloud_backup_manager:
            show_info(self, "Yedekleme dosyasi hazirlaniyor ve gonderiliyor...")
            try:
                # Get Company Name for filename
                company_name = self.db.get_setting("company_name", "")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backups_dir = os.path.join(PathHelper.get_app_data_dir(), "backups")
                if not os.path.exists(backups_dir): os.makedirs(backups_dir)
                
                # Dosya adi formati: [MusteriAdi]_Backup_[Tarih].db veya Backup_[Tarih].db
                if company_name:
                    # Gecersiz karakterleri temizle
                    safe_name = "".join([c for c in company_name if c.isalnum() or c in (' ', '_', '-')]).strip().replace(' ', '_')
                    filename = f"manual_{safe_name}_{timestamp}.db"
                else:
                    filename = f"manual_remote_{timestamp}.db"
                
                backup_path = self.db.backup_database(target_name=filename)
                if not backup_path:
                    raise RuntimeError("Tutarli yedek dosyasi olusturulamadi.")
                
                manager = get_cloud_backup_manager(PathHelper.get_db_path())
                # remote saglayicisina ozel gonderim yap
                # customer_name parametresini de geciriyoruz
                results = manager.upload_backup(backup_path, provider_name='remote', customer_name=company_name)
                
                # Sonuc results dictionary icinde remote anahtari altinda doner
                # rn: {'remote': {'success': True, ...}}
                remote_res = results.get('remote')
                
                if remote_res and remote_res.get('success'):
                    show_success(self, "Yedek basariyla uzak sunucuya gonderildi!")
                else:
                    error_msg = remote_res.get('error') if remote_res else "Sunucu yapilandirmasi bulunamadi."
                    show_error(self, f"Gonderim hatasi: {error_msg}")
                    
            except Exception as e:
                show_error(self, f"Beklenmedik bir hata olustu: {e}")
        else:
            show_error(self, "Yedekleme modl yklenemedi.")

    def backup(self):
        """Veritaban yedei al"""
        try:
            backups_dir = os.path.join(PathHelper.get_app_data_dir(), "backups")
            if not os.path.exists(backups_dir): os.makedirs(backups_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"yerel_yedek_{timestamp}.db"
            target = self.db.backup_database(target_name=filename)
            if not target:
                raise RuntimeError("Tutarli yedek dosyasi olusturulamadi.")

            show_success(self, f"Yerel yedek baaryla oluturuldu: {target}")
        except Exception as e:
            show_error(self, f"Yedek alnamad: {e}")
            
    def restore(self):
        """Yedekten geri ykle"""
        initial_dir = os.path.join(PathHelper.get_app_data_dir(), "backups")
        fname, _ = QFileDialog.getOpenFileName(
            self,
            "Geri Yklenecek Yedei Se",
            initial_dir,
            "Veritaban Dosyas (*.db)",
        )
        if fname:
            try:
                if not self.db.restore_database(fname):
                    raise RuntimeError("Yedek butunluk denetimini gecemedi veya geri yuklenemedi.")
                show_success(
                    self,
                    "Yedek ba\u015far\u0131yla geri y\u00fcklendi. "
                    "Sistemi yeniden ba\u015flatman\u0131z \u00f6nerilir.",
                )
            except Exception as e:
                show_error(self, f"Geri ykleme baarsz: {e}")

    def upload_gdrive_credentials(self):
        """Google Drive API dosyasn ykle"""
        fname, _ = QFileDialog.getOpenFileName(self, "Google Drive API Dosyas Se (credentials.json)", "", "JSON Dosyalar (*.json)")
        if fname:
            try:
                # Copy to app root directory
                # Note: cloud_backup generally looks at CWD or specific path
                target_path = os.path.join(os.getcwd(), "credentials.json")
                shutil.copy2(fname, target_path)
                
                # Clear old token
                if os.path.exists("token.pickle"):
                    try:
                        os.remove("token.pickle")
                    except Exception as e:
                        logger.warning(f"Backup settings old Google token cleanup failed: {e}")
                    
                show_success(self, "API dosyas baaryla yklendi! Ltfen 'Drive'a Yedekle' butonunu kullanarak ilk yetkilendirmeyi yapn. ")
                
            except Exception as e:
                show_error(self, f"Dosya ykleme hatas: {e}")
                
    def send_to_gdrive_now(self):
        """Google Drive'a hemen yedek gnder"""
        if get_cloud_backup_manager:
            show_info(self, "Google Drive yedeklemesi balatlyor (Tarayc alabilir)...")
            try:
                # Get Company Name for filename
                company_name = self.db.get_setting("company_name", "")
                
                manager = get_cloud_backup_manager(PathHelper.get_db_path())
                # Sadece 'gdrive' ilemini aryoruz, sync_all tmn dener ama gdrive parametresi ile o da mmkn
                # Ancak burada spesifik olarak sadece gdrive istendii iin sync_all'a provider_name veriyoruz
                
                res = manager.sync_all(customer_name=company_name, provider_name='gdrive')
                
                if res.get('success'):
                    show_success(self, "Google Drive yedeklemesi baaryla tamamland! ")
                else:
                    # Hata detayn bul
                    error_msg = res.get('error')
                    if 'results' in res and 'gdrive' in res['results']:
                         g_res = res['results']['gdrive']
                         if not g_res['success']:
                             error_msg = g_res.get('error', error_msg)
                             
                    show_error(self, f"Drive Hatas: {error_msg}")
                    
            except Exception as e:
                show_error(self, f"Beklenmedik bir hata olustu: {e}")
        else:
            show_error(self, "Yedekleme yneticisi bulunamad.")



    def _wire_ui_signals(self):
        self.chk_on_exit.stateChanged.connect(self._on_ui_widget_changed)
