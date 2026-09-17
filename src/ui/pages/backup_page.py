# -*- coding: utf-8 -*-


from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QGroupBox, QProgressBar, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFileDialog, QCheckBox, QFrame, QTimeEdit, QMessageBox, QAbstractItemView)
from src.utils.theme_colors import theme_qss, tc
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QTime, QSize
from PyQt6.QtGui import QFont, QIcon, QColor
import os
import datetime
from src.utils.path_helper import PathHelper

# Mevcut modülleri import etmeye çalışıyoruz, yoksa mock kullanacağız
try:
    from src.utils.backup_scheduler import BackupScheduler
    from src.utils.cloud_backup import CloudBackupManager, get_cloud_backup_manager
except ImportError:
    BackupScheduler = None
    CloudBackupManager = None
    get_cloud_backup_manager = None


class BackupWorker(QThread):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    finished = pyqtSignal(bool, str)

    def __init__(self, db, backup_type="local", customer_name=None):
        super().__init__()
        self.db_name = getattr(db, "_db_name", "ayecpro.db")
        self.backup_type = backup_type
        self.customer_name = customer_name

    def run(self):
        db = None
        try:
            if self.backup_type == "local":
                # DB'den yedekleme fonksiyonunu çağır (veya manuel)
                from src.database import Database
                db = Database(self.db_name, init_mode="auth")
                if hasattr(db, "backup_database"):
                    path = db.backup_database()
                    if path:
                        self.finished.emit(True, f"Yedek oluşturuldu: {path}")
                    else:
                        self.finished.emit(False, "Yedekleme oluşturulamadı. Logları kontrol edin.")
                else:
                    self.finished.emit(False, "Veritabanı yedekleme fonksiyonu bulunamadı.")

            elif self.backup_type == "cloud":
                # Cloud/Remote backup tetikle
                if get_cloud_backup_manager:
                    manager = get_cloud_backup_manager(PathHelper.get_db_path())
                    res = manager.sync_all(customer_name=self.customer_name)
                    if res.get('success'):
                        self.finished.emit(True, "Yedekler başarıyla bulut/uzak sunucuya gönderildi. ✅")
                    else:
                        self.finished.emit(False, f"Hata: {res.get('error')}")
                else:
                    self.finished.emit(False, "Cloud/Uzak sunucu modülü aktif değil.")

            elif self.backup_type == "gdrive":
                 # Google Drive Backup
                if get_cloud_backup_manager:
                    manager = get_cloud_backup_manager(PathHelper.get_db_path())

                    # 'gdrive' sağlayıcısını özellikle belirtiyoruz
                    res = manager.sync_all(customer_name=self.customer_name, provider_name='gdrive')

                    if res.get('success'):
                        self.finished.emit(True, "Google Drive yedeklemesi tamamlandı. ✅")
                    else:
                        # Detaylı hata mesajı bulmaya çalış
                        error_msg = res.get('error')
                        if 'results' in res and 'gdrive' in res['results']:
                            gdrive_res = res['results']['gdrive']
                            if not gdrive_res['success']:
                                error_msg = gdrive_res.get('error', error_msg)

                        self.finished.emit(False, f"Hata: {error_msg}")
                else:
                     self.finished.emit(False, "Yedekleme yöneticisi başlatılamadı.")

        except Exception as e:
            self.finished.emit(False, str(e))
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass

class BackupPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QLabel("Yedekleme ve Geri Yükleme Merkezi")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(header)

        # --- Cards Section ---
        cards_layout = QHBoxLayout()

        # Local Backup Card
        card_local = self.create_card(
            "Yerel Yedekleme",
            "💾",
            "Verilerinizi bilgisayarınıza güvenli bir şekilde kaydedin veya geri yükleyin.",
            "Veritabanını Yedekle",
            self.start_local_backup,
            btn_color=tc("success"),
            extra_btns=[("Sistemi Geri Yükle", self.restore_local_backup, tc("text_muted"))]
        )
        cards_layout.addWidget(card_local)

        # Cloud Backup Card (Remote Server)
        card_cloud = self.create_card(
            "Sunucu Yedekleme",
            "☁️",
            "Verilerinizi AYEC Pro sunucularında şifreli olarak saklayın.",
            "Sunucuya Yedekle",
            self.start_cloud_backup,
            btn_color=tc("accent"),
            extra_btns=[("Sunucudan Geri Yükle", self.restore_cloud_backup, tc("warning"))]
        )
        cards_layout.addWidget(card_cloud)

        # NEW: Google Drive Card
        card_gdrive = self.create_card(
            "Google Drive",
            "📂",
            "Kişisel Google Drive hesabınıza yedekleyin.",
            "Drive'a Yedekle",
            self.start_gdrive_backup,
            btn_color=tc("danger"),
            extra_btns=[("API Dosyası Seç (credentials.json)", self.upload_gdrive_credentials, tc("text_muted"))]
        )
        cards_layout.addWidget(card_gdrive)

        layout.addLayout(cards_layout)

        # --- Settings Section ---
        grp_settings = QGroupBox("Otomatik Yedekleme Zamanlayıcı")
        grp_settings.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        sett_layout = QVBoxLayout(grp_settings)

        # New options matching BackupSettingsWidget
        # Custom Time Selector
        self.chk_daily = QCheckBox("Günlük Otomatik Yedekleme")
        self.chk_daily.setStyleSheet(theme_qss("font-size: 13px; font-weight: 500;"))

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setFont(QFont("Segoe UI", 12))

        # Initial state setup
        is_daily = self.db.get_setting("backup_daily_enabled", "0") == "1"
        self.chk_daily.setChecked(is_daily)

        time_str = self.db.get_setting("backup_daily_time", "12:00")
        try:
             self.time_edit.setTime(QTime.fromString(time_str, "HH:mm"))
        except Exception:
            self.time_edit.setTime(QTime(12, 0))

        self.chk_daily.toggled.connect(self.time_edit.setEnabled)
        self.time_edit.setEnabled(is_daily)

        self.chk_on_exit = QCheckBox("Programdan Çıkışta")
        self.chk_on_exit.setStyleSheet(theme_qss("font-size: 13px; font-weight: 500;"))
        self.chk_on_exit.setChecked(self.db.get_setting("backup_on_exit", "1") == "1")

        btn_save_sett = QPushButton("Zamanlayıcı Ayarlarını Kaydet")
        btn_save_sett.clicked.connect(self.save_settings)
        btn_save_sett.setStyleSheet(theme_qss("background-color: @accent; color: white; padding: 6px;"))

        sett_layout.addWidget(self.chk_daily)
        sett_layout.addWidget(self.time_edit)
        sett_layout.addWidget(self.chk_on_exit)
        sett_layout.addWidget(btn_save_sett)

        layout.addWidget(grp_settings)

        # --- History Table ---
        layout.addWidget(QLabel("Son Yedekleme Geçmişi"))

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self.refresh_history()

    def start_cloud_backup(self):
        show_info(self, "Sunucuya yedekleniyor...")

        # Get Company Name for filename
        company_name = self.db.get_setting("company_name", "Müşteri")
        self.worker = BackupWorker(self.db, "cloud", customer_name=company_name)
        self.worker.finished.connect(self.on_backup_finished)
        self.worker.start()

    def start_gdrive_backup(self):
        show_info(self, "Google Drive yedeklemesi başlatılıyor...")

        # Get Company Name
        company_name = self.db.get_setting("company_name", "Müşteri")
        self.worker = BackupWorker(self.db, "gdrive", customer_name=company_name)
        self.worker.finished.connect(self.on_backup_finished)
        self.worker.start()

    def create_card(self, title, icon, desc, btn_text, slot, btn_color=tc("success"), extra_btns=None):
        frame = QFrame()
        frame.setStyleSheet(theme_qss("""
            QFrame {
                background-color: white;
                border: 1px solid @border;
                border-radius: 12px;
                margin: 5px;
            }
            QFrame:hover {
                border: 1px solid @accent;
                background-color: @surface_alt;
            }
        """))
        l = QVBoxLayout(frame)
        l.setSpacing(15)
        l.setContentsMargins(20, 20, 20, 20)

        # Icon Area
        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 48))
        icon_lbl.setStyleSheet(theme_qss("border: none; background: transparent;"))
        l.addWidget(icon_lbl)

        # Title
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_title.setStyleSheet(theme_qss("border: none; color: @text; background: transparent;"))
        l.addWidget(lbl_title)

        # Description
        lbl_desc = QLabel(desc)
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(theme_qss("border: none; color: @text_muted; font-size: 13px; background: transparent;"))
        l.addWidget(lbl_desc)

        l.addStretch()

        # Main Button
        btn = QPushButton(btn_text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(theme_qss(f"""
            QPushButton {{
                background-color: {btn_color};
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """))
        btn.clicked.connect(slot)
        l.addWidget(btn)

        # Extra Buttons (if any)
        if extra_btns:
            for b_text, b_slot, b_col in extra_btns:
                eb = QPushButton(b_text)
                eb.setCursor(Qt.CursorShape.PointingHandCursor)
                eb.setStyleSheet(theme_qss(f"""
                    QPushButton {{
                        background-color: {b_col};
                        color: white;
                        font-weight: bold;
                        padding: 12px;
                        border-radius: 6px;
                        font-size: 14px;
                        border: none;
                        margin-top: 5px;
                    }}
                    QPushButton:hover {{ opacity: 0.9; }}
                """))
                eb.clicked.connect(b_slot)
                l.addWidget(eb)

        return frame

    def start_local_backup(self):
        # Gerçek yedekleme işlemi
        self.worker = BackupWorker(self.db, "local")
        self.worker.finished.connect(self.on_backup_finished)
        self.worker.start()
        show_info(self, "Yedekleme arka planda başlatıldı...")

    def restore_local_backup(self):
        initial_dir = os.path.join(PathHelper.get_app_data_dir(), "backups")
        fname, _ = QFileDialog.getOpenFileName(self, "Geri Yüklenecek Yedeği Seç", initial_dir, "Veritabanı Dosyası (*.db)")
        if fname:
            try:
                if not hasattr(self.db, "restore_database"):
                    raise RuntimeError("Validated restore API is not available")
                if not self.db.restore_database(fname):
                    raise RuntimeError("Backup validation or restore failed")
                show_success(self, "Sistem başarıyla geri yüklendi! Lütfen programı yeniden başlatın. ✅")
            except Exception as e:
                show_error(self, f"Geri yükleme hatası: {e}")

    def restore_cloud_backup(self):
        """Sunucudan canlı veritabanını indir ve yerel sisteme uygula"""
        from src.ui.dialogs.simple_confirm import SimpleConfirmDialog

        # Onay al
        if not SimpleConfirmDialog(
            self,
            "Sunucudan Geri Yükle",
            "Sunucudaki güncel veritabanı indirilecek ve yerel sisteminizin üzerine yazılacak.\n\n"
            "Mevcut yerel verileriniz yedeklenecek ancak sunucudaki verilerle değiştirilecek.\n\n"
            "Devam etmek istediğinize emin misiniz"
        ).exec():
            return

        show_info(self, "Sunucudan veritabanı indiriliyor...")

        try:
            if not get_cloud_backup_manager:
                show_error(self, "Cloud backup modülü bulunamadı.")
                return

            manager = get_cloud_backup_manager(PathHelper.get_db_path())

            # Check if remote provider exists
            if 'remote' not in manager.providers:
                show_error(self, "Sunucu bağlantısı yapılandırılmamış. Lütfen ayarlardan sunucu IP'sini kontrol edin.")
                return

            # Download to temp location
            import tempfile
            temp_file = os.path.join(tempfile.gettempdir(), "server_sync_download.db")

            result = manager.providers['remote'].download("server_sync.db", temp_file)

            if result and os.path.exists(temp_file):
                # Backup current database
                current_db = PathHelper.get_db_path()
                backup_path = current_db + f".before_server_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

                try:
                    import shutil
                    shutil.copy2(current_db, backup_path)
                    show_info(self, f"Mevcut veritabanı yedeklendi: {os.path.basename(backup_path)}")
                except Exception as e:
                    show_warning(self, f"Yerel yedek alınamadı: {e}")

                # Replace with downloaded database
                try:
                    shutil.copy2(temp_file, current_db)
                    os.remove(temp_file)  # Clean up temp file

                    show_success(self, "Sunucudan geri yükleme başarılı! Programı yeniden başlatmanız önerilir. ✅")

                    # Ask to restart
                    if SimpleConfirmDialog(
                        self,
                        "Yeniden Başlat",
                        "Değişikliklerin tam olarak uygulanması için programı yeniden başlatmanız önerilir.\n\nŞimdi yeniden başlatmak ister misiniz"
                    ).exec():
                        import sys
                        from PyQt6.QtWidgets import QApplication
                        QApplication.quit()
                        os.execl(sys.executable, sys.executable, *sys.argv)

                except Exception as e:
                    show_error(self, f"Veritabanı güncellenirken hata: {e}")
            else:
                show_error(self, "Sunucudan indirme başarısız. Sunucu bağlantısını ve ayarlarını kontrol edin.")

        except Exception as e:
            show_error(f"Geri yükleme hatası: {e}")

    def upload_gdrive_credentials(self):
        """Allow user to select credentials.json file"""
        fname, _ = QFileDialog.getOpenFileName(self, "Google Drive API Dosyası Seç (credentials.json)", "", "JSON Dosyaları (*.json)")
        if fname:
            try:
                import shutil
                # Copy to current working directory or where cloud_backup expects it
                dest_path = os.path.join(os.getcwd(), "credentials.json")
                shutil.copy2(fname, dest_path)
                show_success(self, "API dosyası başarıyla yüklendi! Şimdi yedeklemeyi deneyebilirsiniz. ✅")

                # Optional: Clear old token if new credentials are loaded
                if os.path.exists("token.pickle"):
                    os.remove("token.pickle")

            except Exception as e:
                show_error(f"Dosya yükleme hatası: {e}")


    def on_backup_finished(self, success, msg):
        if success:
            show_success(self, msg)
            self.refresh_history()
        else:
            show_error(self, f"Yedekleme başarısız: {msg}")

    def save_settings(self):
        self.db.set_setting("backup_daily_enabled", "1" if self.chk_daily.isChecked() else "0")
        self.db.set_setting("backup_daily_time", self.time_edit.time().toString("HH:mm"))
        self.db.set_setting("backup_on_exit", "1" if self.chk_on_exit.isChecked() else "0")

        # Clear legacy
        self.db.set_setting("backup_auto_morning", "0")
        self.db.set_setting("backup_auto_evening", "0")

        show_success(self, "Otomatik yedekleme zamanlayıcıları güncellendi. ✅")

    def refresh_history(self):
        # AppData "backups" klasörünü tara
        self.table.setRowCount(0)
        backups_dir = os.path.join(PathHelper.get_app_data_dir(), "backups")
        if not os.path.exists(backups_dir):
            return

        files = sorted(os.listdir(backups_dir), reverse=True)
        for i, f in enumerate(files):
            if not f.endswith('.db'): continue

            path = os.path.join(backups_dir, f)
            size = os.path.getsize(path) / 1024 # KB
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")

            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(f))
            self.table.setItem(i, 1, QTableWidgetItem(f"{size:.1f} KB"))
            self.table.setItem(i, 2, QTableWidgetItem(mtime))
            self.table.setItem(i, 3, QTableWidgetItem("Yerel"))


    def _wire_ui_signals(self):
        self.chk_on_exit.stateChanged.connect(self._on_ui_widget_changed)
