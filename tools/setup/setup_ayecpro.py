#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AYEC Pro - Modern Setup & Installation System
Version: 69.0.0
Author: AYEC Pro Development Team
Tarih: 2026-02-15
"""

import sys
import os
import json
import sqlite3
import shutil
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Logging Ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AYECPro_Setup')

# Qt Imports
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QProgressBar, QTextEdit, QStackedWidget,
        QMessageBox, QFileDialog, QCheckBox, QComboBox, QSpinBox,
        QFrame, QGraphicsDropShadowEffect
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QPoint
    from PyQt6.QtGui import QFont, QColor, QPixmap, QIcon, QLinearGradient, QPainter, QBrush, QPalette
    HAS_QT = True
except ImportError:
    HAS_QT = False
    logger.warning("PyQt6 yüklenemedi - GUI olmadan devam ediliyor")


class SetupConfiguration:
    """Setup Yapılandırması"""
    
    def __init__(self):
        self.appdata = os.getenv('LOCALAPPDATA')
        self.install_dir = os.path.join(self.appdata, "AYEC Pro")
        self.db_path = os.path.join(self.install_dir, "ayecpro.db")
        self.config_file = os.path.join(self.install_dir, "config.json")
        self.log_file = os.path.join(self.install_dir, "setup.log")
        
        # Version
        self.version = "69.0.0"
        self.app_name = "AYEC Pro"
        
        # Create directories
        os.makedirs(self.install_dir, exist_ok=True)
    
    def to_dict(self) -> Dict:
        return {
            'app_name': self.app_name,
            'version': self.version,
            'install_dir': self.install_dir,
            'db_path': self.db_path,
            'install_date': datetime.now().isoformat(),
        }
    
    def save_config(self):
        """Yapılandırma dosyasını kaydet"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=4)
            logger.info(f"Yapılandırma kaydedildi: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Yapılandırma kaydetme hatası: {e}")
            return False


class DatabaseInitializer:
    """Veritabanı İlkleştirici"""
    
    DATABASE_SCHEMA = {
        'users': """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                role TEXT,
                full_name TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT
            )
        """,
        'customers': """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                email VARCHAR(255),
                type VARCHAR(20),
                tax_id VARCHAR(50),
                address TEXT,
                city VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        'parts': """
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                code VARCHAR(50) UNIQUE,
                barcode VARCHAR(50) UNIQUE,
                stock INTEGER DEFAULT 0,
                min_stock INTEGER DEFAULT 0,
                price FLOAT,
                purchase_price FLOAT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        'devices': """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no VARCHAR(50) UNIQUE NOT NULL,
                customer_id INTEGER,
                brand VARCHAR(100),
                model VARCHAR(100),
                serial_no VARCHAR(100),
                fault_description TEXT,
                status VARCHAR(50),
                entry_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                exit_date DATETIME,
                price FLOAT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            )
        """,
        'accounting': """
            CREATE TABLE IF NOT EXISTS accounting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type VARCHAR(10),
                category VARCHAR(100),
                amount FLOAT NOT NULL,
                description TEXT,
                customer_id INTEGER,
                date DATE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            )
        """,
        'stock_movements': """
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_id INTEGER NOT NULL,
                type VARCHAR(20),
                amount INTEGER,
                current_stock INTEGER,
                description TEXT,
                date DATETIME DEFAULT CURRENT_TIMESTAMP,
                user VARCHAR(100),
                FOREIGN KEY(part_id) REFERENCES parts(id)
            )
        """,
        'audit_logs': """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(100),
                table_name VARCHAR(100),
                action VARCHAR(20),
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        'settings': """
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT
            )
        """
    }
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def initialize(self) -> bool:
        """Veritabanını başlat"""
        try:
            logger.info(f"Veritabanı oluşturuluyor: {self.db_path}")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tablolar oluştur
            for table_name, schema in self.DATABASE_SCHEMA.items():
                try:
                    cursor.execute(schema)
                    logger.info(f"[OK] Tablo oluşturuldu: {table_name}")
                except sqlite3.OperationalError as e:
                    if "already exists" in str(e):
                        logger.info(f"[OK] Tablo zaten mevcut: {table_name}")
                    else:
                        logger.error(f"[HATA] Tablo oluşturma hatası {table_name}: {e}")
            
            # Admin kullanıcısı ekle
            self._create_default_user(cursor)
            
            # Ayarları ekle
            self._create_default_settings(cursor)
            
            conn.commit()
            conn.close()
            
            logger.info("[OK] Veritabanı başarıyla oluşturuldu")
            return True
            
        except Exception as e:
            logger.error(f"Veritabanı oluşturma hatası: {e}")
            return False
    
    def _create_default_user(self, cursor):
        """Varsayılan admin kullanıcısını oluştur"""
        try:
            # Table users column 'active' follows schema at line 94
            cursor.execute(
                "INSERT OR IGNORE INTO users (username, password, role, active) VALUES (?, ?, ?, ?)",
                ('admin', 'admin123', 'admin', 1)
            )
            logger.info("[OK] Varsayılan admin kullanıcısı oluşturuldu")
        except Exception as e:
            logger.error(f"[HATA] Admin kullanıcı oluşturma hatası: {e}")
    
    def _create_default_settings(self, cursor):
        """Varsayılan ayarları oluştur"""
        settings = {
            'app_version': '69.0.0',
            'currency': 'TRY',
            'language': 'tr',
            'company_name': 'AYEC Pro',
        }
        
        try:
            for key, value in settings.items():
                cursor.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (key, value)
                )
            logger.info(f"[OK] {len(settings)} varsayılan ayar oluşturuldu")
        except Exception as e:
            logger.error(f"[HATA] Ayar oluşturma hatası: {e}")


class InstallationManager:
    """Kurulum Yöneticisi"""
    
    def __init__(self, config: SetupConfiguration):
        self.config = config
        self.status_message = ""
    
    def verify_prerequisites(self) -> bool:
        """Ön koşulları doğrula"""
        logger.info("Ön koşullar kontrol ediliyor...")
        
        self.status_message = "✓ Python 3.8+ tespit edildi"
        logger.info(self.status_message)
        
        # PyQt6 kontrolü
        try:
            import PyQt6
            _ = PyQt6
            self.status_message = "✓ PyQt6 bulundu"
            logger.info(self.status_message)
        except ImportError:
            logger.warning("PyQt6 bulunamadı - yüklenecek")
        
        return True
    
    def create_shortcuts(self) -> bool:
        """Masaüstü kısayolları oluştur"""
        try:
            logger.info("Masaüstü kısayolları oluşturuluyor...")
            
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            shortcut_path = os.path.join(desktop, "AYEC Pro.lnk")
            
            # PowerShell ile kısayol oluştur
            script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = '{self.config.install_dir}\\AYECPro.exe'
$Shortcut.WorkingDirectory = '{self.config.install_dir}'
$Shortcut.Description = 'AYEC Pro - Servis Yönetim Sistemi'
$Shortcut.Save()
"""
            result = subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Kısayol oluşturuldu: {shortcut_path}")
                return True
            else:
                logger.warning(f"Kısayol oluşturulamadı: {result.stderr}")
                return False
                
        except Exception as e:
            logger.warning(f"Kısayol oluşturma hatası: {e}")
            return False
    
    def backup_old_data(self) -> bool:
        """Eski verileri yedekle"""
        try:
            logger.info("Eski veriler yedekleniyor...")
            
            old_locations = [
                os.path.join(os.path.expanduser("~"), 'Desktop', 'AYEC Pro'),
                os.path.join(self.config.appdata, 'AYEC Pro'),
            ]
            
            for old_loc in old_locations:
                if os.path.exists(old_loc):
                    old_db = os.path.join(old_loc, "ayecpro.db")
                    if os.path.exists(old_db):
                        backup_path = os.path.join(
                            self.config.install_dir,
                            f"ayecpro_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                        )
                        shutil.copy2(old_db, backup_path)
                        logger.info(f"✓ Yedek oluşturuldu: {backup_path}")
                        return True
            
            logger.info("Eski veri bulunamadı")
            return True
            
        except Exception as e:
            logger.error(f"Yedekleme hatası: {e}")
            return False


class ModernInstallThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, config, manager):
        super().__init__()
        self.config = config
        self.manager = manager

    def run(self):
        try:
            # 1. Verify Prerequisites
            self.status.emit("Ön koşullar kontrol ediliyor...")
            time.sleep(1)
            self.manager.verify_prerequisites()
            self.progress.emit(20)

            # 2. Backup Old Data
            self.status.emit("Eski veriler yedekleniyor...")
            self.manager.backup_old_data()
            self.progress.emit(40)

            # 3. Initialize Database
            self.status.emit("Veritabanı yapılandırılıyor...")
            db_init = DatabaseInitializer(self.config.db_path)
            db_init.initialize()
            self.progress.emit(70)

            # 4. Save Config & Shortcuts
            self.status.emit("Sistem yapılandırması tamamlanıyor...")
            self.config.save_config()
            self.manager.create_shortcuts()
            self.progress.emit(100)
            
            self.status.emit("Kurulum başarıyla tamamlandı!")
            time.sleep(1)
            self.finished.emit()
            
        except Exception as e:
            self.status.emit(f"Hata oluştu: {str(e)}")
            logger.error(f"Kurulum hatası: {e}")
            time.sleep(2)
            self.finished.emit()

class SetupWizardGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = SetupConfiguration()
        self.manager = InstallationManager(self.config)
        
        self.setWindowTitle("AYEC Pro - Master Setup")
        self.setFixedSize(800, 600)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Main Base Frame
        self.base_frame = QFrame(self)
        self.base_frame.setGeometry(0, 0, 800, 600)
        self.base_frame.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border-radius: 15px;
                border: 1px solid #1e293b;
            }
        """)

        # Add Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.base_frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.base_frame)
        layout.setContentsMargins(0, 0, 0, 0)

        # Custom Title Bar
        self.title_bar = QFrame()
        self.title_bar.setFixedHeight(50)
        self.title_bar.setStyleSheet("background: #1e293b; border-top-left-radius: 15px; border-top-right-radius: 15px; border: none;")
        t_layout = QHBoxLayout(self.title_bar)
        t_layout.setContentsMargins(20, 0, 15, 0)
        
        self.app_title = QLabel("AYEC Pro Enterprise - Kurulum Sihirbazı")
        self.app_title.setStyleSheet("color: #94a3b8; font-size: 14px; font-weight: bold;")
        t_layout.addWidget(self.app_title)
        
        t_layout.addStretch()
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(35, 35)
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setStyleSheet("""
            QPushButton { color: #64748b; border: none; font-size: 18px; background: transparent; }
            QPushButton:hover { color: white; background: #ef4444; border-radius: 5px; }
        """)
        t_layout.addWidget(self.close_btn)
        layout.addWidget(self.title_bar)

        # Main Content Area
        self.stack = QStackedWidget()
        
        # --- PAGE 1: WELCOME & INFO ---
        self.page1 = QWidget()
        p1_layout = QVBoxLayout(self.page1)
        p1_layout.setContentsMargins(50, 30, 50, 30)
        p1_layout.setSpacing(20)
        
        # Logo Section
        logo_container = QLabel()
        logo_path = os.path.join(os.path.abspath("."), "assets/ayec_logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            logo_container.setPixmap(pix.scaled(300, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_container.setStyleSheet("border: none; background: transparent; margin-bottom: 20px;")
        p1_layout.addWidget(logo_container)
        
        welcome_title = QLabel(f"AYEC Pro® v{self.config.version}")
        welcome_title.setStyleSheet("color: #ffffff; font-size: 36px; font-weight: 800; border: none;")
        welcome_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p1_layout.addWidget(welcome_title)
        
        info_card = QFrame()
        info_card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-radius: 15px;
                padding: 25px;
                border: 1px solid #334155;
            }
        """)
        ic_layout = QVBoxLayout(info_card)
        ic_layout.setSpacing(15)
        
        features = [
            "  ✓  Tam Entegre Masaüstü, Web ve Mobil Sistem",
            "  ✓  Gelişmiş SQLite ve Bulut Veri Senkronizasyonu",
            "  ✓  Kapsamlı Teknik Servis, Stok ve Atölye Yönetimi",
            "  ✓  Profesyonel Muhasebe ve Cari Takip Modülü",
            "  ✓  Tek Tıkla Otomatik Veritabanı Yapılandırması"
        ]
        
        for f in features:
            f_lbl = QLabel(f)
            f_lbl.setStyleSheet("color: #e2e8f0; font-size: 16px; font-weight: 500; font-family: 'Segoe UI'; border: none;")
            ic_layout.addWidget(f_lbl)
            
        p1_layout.addWidget(info_card)
        p1_layout.addStretch()
        
        self.install_btn = QPushButton("KURULUMU ŞİMDİ BAŞLAT")
        self.install_btn.setFixedHeight(60)
        self.install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_btn.clicked.connect(self.start_installation)
        self.install_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb);
                color: white;
                border-radius: 12px;
                font-size: 18px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background: #1d4ed8; border: 2px solid #60a5fa; }
        """)
        p1_layout.addWidget(self.install_btn)
        
        self.stack.addWidget(self.page1)

        # --- PAGE 2: INSTALLATION PROGRESS ---
        self.page2 = QWidget()
        p2_layout = QVBoxLayout(self.page2)
        p2_layout.setContentsMargins(100, 150, 100, 150)
        p2_layout.setSpacing(30)
        
        self.status_title = QLabel("Sistem Yapılandırılıyor...")
        self.status_title.setStyleSheet("color: white; font-size: 22px; font-weight: 700; border: none;")
        self.status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p2_layout.addWidget(self.status_title)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border-radius: 10px;
                border: 1px solid #334155;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #60a5fa);
                border-radius: 9px;
            }
        """)
        p2_layout.addWidget(self.progress_bar)
        
        self.status_detail = QLabel("Lütfen bekleyin, kurulum devam ediyor...")
        self.status_detail.setStyleSheet("color: #94a3b8; font-size: 16px; border: none;")
        self.status_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p2_layout.addWidget(self.status_detail)
        
        self.stack.addWidget(self.page2)

        # --- PAGE 3: SUCCESS ---
        self.page3 = QWidget()
        p3_layout = QVBoxLayout(self.page3)
        p3_layout.setContentsMargins(60, 60, 60, 60)
        p3_layout.setSpacing(15)
        
        success_img = QLabel("🚀")
        success_img.setStyleSheet("font-size: 100px; border: none; background: transparent;")
        success_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p3_layout.addWidget(success_img)
        
        finish_title = QLabel("Kurulum Başarıyla Tamamlandı!")
        finish_title.setStyleSheet("color: #10b981; font-size: 32px; font-weight: bold; border: none;")
        finish_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p3_layout.addWidget(finish_title)
        
        finish_desc = QLabel("AYEC Pro kullanıma hazır.\nMasaüstündeki kısayolu kullanarak sistemi başlatabilirsiniz.")
        finish_desc.setStyleSheet("color: #cbd5e1; font-size: 16px; border: none; margin-top: 15px;")
        finish_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p3_layout.addWidget(finish_desc)
        
        p3_layout.addStretch()
        
        self.launch_btn = QPushButton("TAMAMLA")
        self.launch_btn.setFixedHeight(60)
        self.launch_btn.clicked.connect(self.close)
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border-radius: 12px;
                font-size: 18px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        p3_layout.addWidget(self.launch_btn)
        
        self.stack.addWidget(self.page3)
        layout.addWidget(self.stack)

        # Footer
        footer = QLabel("© 2026 AYEC Pro | Modern Servis Yönetim Sistemi")
        footer.setStyleSheet("color: #475569; font-size: 12px; border: none; margin-bottom: 20px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

        self.mouse_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.mouse_pos:
            diff = event.globalPos() - self.mouse_pos
            self.move(self.pos() + diff)
            self.mouse_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.mouse_pos = None

    def start_installation(self):
        self.stack.setCurrentIndex(1)
        self.thread = ModernInstallThread(self.config, self.manager)
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.status.connect(self.status_detail.setText)
        self.thread.finished.connect(lambda: self.stack.setCurrentIndex(2))
        self.thread.start()


def run_gui():
    """GUI modunu çalıştır"""
    app = QApplication(sys.argv)
    window = SetupWizardGUI()
    window.show()
    sys.exit(app.exec())


def run_console():
    """Konsol modunu çalıştır"""
    print("\n" + "="*60)
    print("    AYEC Pro - Kurulum Sihirbazı v69.0.0")
    print("="*60 + "\n")
    
    config = SetupConfiguration()
    manager = InstallationManager(config)
    
    print(f"[*] Kurulum Dizini: {config.install_dir}")
    print(f"[*] Veritabanı Dosyası: {config.db_path}\n")
    
    try:
        # Adım 1
        print("[1/4] Ön koşullar kontrol ediliyor...")
        if manager.verify_prerequisites():
            print("[OK] Ön koşullar OK\n")
        
        # Adım 2
        print("[2/4] Eski veriler yedekleniyor...")
        manager.backup_old_data()
        print("[OK] Yedekleme tamamlandı\n")
        
        # Adım 3
        print("[3/4] Veritabanı oluşturuluyor...")
        db_init = DatabaseInitializer(config.db_path)
        if db_init.initialize():
            print("[OK] Veritabanı başarıyla oluşturuldu\n")
        else:
            print("[HATA] Veritabanı oluşturulamadı\n")
            return False
        
        # Adım 4
        print("[4/4] Son ayarlar yapılıyor...")
        config.save_config()
        manager.create_shortcuts()
        print("[OK] Son ayarlar tamamlandı\n")
        
        print("="*60)
        print("    KURULUM BAŞARILI")
        print("="*60)
        print(f"\nAYEC Pro {config.version} kuruldu!")
        print(f"Kurulum Dizini: {config.install_dir}")
        print(f"Veritabanı: {config.db_path}")
        print(f"\nAuygulamayı başlatmak için AYECPro.exe'ye çift tıklayın.\n")
        
        return True
        
    except Exception as e:
        print(f"[HATA] KURULUM HATASI: {e}\n")
        logger.error(f"Setup hatası: {e}", exc_info=True)
        return False


def main():
    """Ana giriş noktası"""
    
    # Komut satırı argümanları
    if len(sys.argv) > 1:
        if sys.argv[1] == '--console' or sys.argv[1] == '-c':
            # Konsol modunu çalıştır
            success = run_console()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("""
AYEC Pro Setup v69.0.0

Kullanım:
  python setup_ayecpro.py              # GUI modunda çalıştır (PyQt6 gerekli)
  python setup_ayecpro.py --console    # Konsol modunda çalıştır
  python setup_ayecpro.py --help       # Bu yardımı göster
            """)
            sys.exit(0)
    
    # GUI modunu dene
    if HAS_QT:
        try:
            run_gui()
        except Exception as e:
            logger.error(f"GUI hatası: {e} - Konsol moduna geçiliyor...")
            print(f"\nGUI başlatılamadı: {e}")
            print("Konsol modunda devam ediliyor...\n")
            run_console()
    else:
        # PyQt6 yoksa konsol modunda çalıştır
        print("PyQt6 bulunamadı - Konsol modunda kurulum yapılacak...")
        run_console()


if __name__ == "__main__":
    main()
