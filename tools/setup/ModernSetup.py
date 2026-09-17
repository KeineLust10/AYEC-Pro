# -*- coding: utf-8 -*-

import sys
import os
import shutil
import time
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QProgressBar, 
                             QStackedWidget, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor, QLinearGradient, QPainter, QBrush, QPalette

class InstallThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal()

    def run(self):
        try:
            # 1. Define Paths
            appdata = os.getenv('LOCALAPPDATA')
            install_dir = os.path.join(appdata, "AYECPro")
            if not os.path.exists(install_dir):
                os.makedirs(install_dir)

            self.status.emit("Dizinler yapısı optimize ediliyor...")
            time.sleep(1)

            # 2. Get Source Path (PyInstaller _MEIPASS)
            try:
                base_path = sys._MEIPASS
            except:
                base_path = os.path.abspath(".")

            # 3. Copy Application Executables
            self.status.emit("Ana modüller yükleniyor (Desktop App)...")
            src_exe = os.path.join(base_path, "AYECPro_App.exe")
            dst_exe = os.path.join(install_dir, "AYECPro.exe")
            
            if os.path.exists(src_exe):
                shutil.copy2(src_exe, dst_exe)
            self.progress.emit(25)

            # 3.1 Copy Server Motor
            self.status.emit("Sunucu motoru yapılandırılıyor (Web/Mobile Server)...")
            src_server = os.path.join(base_path, "AYECPro_Server.exe")
            dst_server = os.path.join(install_dir, "AYECPro_Server.exe")
            if os.path.exists(src_server):
                shutil.copy2(src_server, dst_server)
            self.progress.emit(45)
                
            # 4. Copy Assets and Web Interface
            self.status.emit("Görsel kaynaklar ve Web arayüzü kuruluyor...")
            src_assets = os.path.join(base_path, "assets")
            dst_assets = os.path.join(install_dir, "assets")
            if os.path.exists(src_assets):
                if os.path.exists(dst_assets):
                    shutil.rmtree(dst_assets)
                shutil.copytree(src_assets, dst_assets)
                
            # Copy Web Interface
            src_web = os.path.join(base_path, "web_interface")
            dst_web = os.path.join(install_dir, "web_interface")
            if os.path.exists(src_web):
                if os.path.exists(dst_web):
                    shutil.rmtree(dst_web)
                shutil.copytree(src_web, dst_web)
            self.progress.emit(75)

            # Copy Database (if not exists in target)
            self.status.emit("Veritabanı bütünlüğü kontrol ediliyor...")
            src_db = os.path.join(base_path, "ayecpro.db")
            dst_db = os.path.join(install_dir, "ayecpro.db")
            if os.path.exists(src_db) and not os.path.exists(dst_db):
                shutil.copy2(src_db, dst_db)
            
            # Copy Startup Batch Scripts
            src_batch = os.path.join(base_path, "Start_AYECPro.bat")
            dst_batch = os.path.join(install_dir, "Start_AYECPro.bat")
            if os.path.exists(src_batch):
                shutil.copy2(src_batch, dst_batch)
                
            src_setup_batch = os.path.join(base_path, "Bulut_Premium_Server.bat")
            dst_setup_batch = os.path.join(install_dir, "Bulut_Premium_Server.bat")
            if os.path.exists(src_setup_batch):
                shutil.copy2(src_setup_batch, dst_setup_batch)

            # 5. Create Desktop Shortcuts
            self.status.emit("Sistem entegrasyonu tamamlanıyor...")
            desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
            
            # App Shortcut
            shortcut_path = os.path.join(desktop, "AYEC Pro.lnk")
            icon_path = os.path.join(dst_assets, "app_icon.ico")
            batch_path = os.path.join(install_dir, "Start_AYECPro.bat")
            
            # Server Shortcut
            server_shortcut_path = os.path.join(desktop, "AYEC Pro Sunucu (Sadece Server).lnk")
            
            ps_script = f"""
            $WshShell = New-Object -ComObject WScript.Shell
            
            # Ana Kısayol (Batch üzerinden her şeyi başlatır)
            $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
            $Shortcut.TargetPath = 'cmd.exe'
            $Shortcut.Arguments = '/c "{batch_path}"'
            $Shortcut.WorkingDirectory = '{install_dir}'
            $Shortcut.IconLocation = '{icon_path}'
            $Shortcut.Description = 'AYEC Pro - Entegre Sistem'
            $Shortcut.Save()
            
            # Sunucu Kısayolu
            $SrvShortcut = $WshShell.CreateShortcut('{server_shortcut_path}')
            $SrvShortcut.TargetPath = '{dst_server}'
            $SrvShortcut.WorkingDirectory = '{install_dir}'
            $SrvShortcut.IconLocation = '{icon_path}'
            $SrvShortcut.Description = 'AYEC Pro Server'
            $SrvShortcut.Save()
            """
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
            
            self.progress.emit(100)
            self.status.emit("Kurulum başarıyla tamamlandı!")
            time.sleep(1)
            self.finished.emit()
            
        except Exception as e:
            self.status.emit(f"Hata oluştu: {str(e)}")
            time.sleep(3)
            self.finished.emit()

class ModernSetup(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AYEC Pro - Master Setup")
        self.setFixedSize(850, 650) # Increased size for better readability
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Main Base Frame
        self.base_frame = QFrame(self)
        self.base_frame.setGeometry(0, 0, 850, 650)
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
        if os.path.exists("assets/logo.png"):
            pix = QPixmap("assets/logo.png")
            logo_container.setPixmap(pix.scaled(300, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        elif os.path.exists("assets/app_icon.png"):
            pix = QPixmap("assets/app_icon.png")
            logo_container.setPixmap(pix.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_container.setStyleSheet("border: none; background: transparent; margin-bottom: 20px;")
        p1_layout.addWidget(logo_container)
        
        welcome_title = QLabel("AYEC Pro® v68.1.0")
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
            "  ✓  Tek Tıkla Otomatik Sunucu Yapılandırması"
        ]
        
        for f in features:
            f_lbl = QLabel(f)
            # Use a standard font to prevent rendering issues, increase line height/size
            f_lbl.setStyleSheet("""
                color: #e2e8f0; 
                font-size: 18px; 
                font-weight: 500;
                font-family: 'Segoe UI', Arial, sans-serif;
                border: none;
                margin: 2px;
            """)
            f_lbl.setWordWrap(True)
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
                font-size: 20px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { 
                background: #1d4ed8; 
                border: 2px solid #60a5fa;
            }
        """)
        p1_layout.addWidget(self.install_btn)
        
        self.stack.addWidget(self.page1)

        # --- PAGE 2: INSTALLATION PROGRESS ---
        self.page2 = QWidget()
        p2_layout = QVBoxLayout(self.page2)
        p2_layout.setContentsMargins(100, 150, 100, 150)
        p2_layout.setSpacing(30)
        
        self.status_title = QLabel("Sistem Dosyaları Yapılandırılıyor...")
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
        finish_title.setStyleSheet("color: #10b981; font-size: 36px; font-weight: bold; border: none;")
        finish_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p3_layout.addWidget(finish_title)
        
        finish_desc = QLabel("AYEC Pro kullanıma hazır.\nMasaüstündeki kısayolu kullanarak tüm sistemi başlatabilirsiniz.")
        finish_desc.setStyleSheet("color: #cbd5e1; font-size: 18px; border: none; margin-top: 15px; line-height: 1.5;")
        finish_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p3_layout.addWidget(finish_desc)
        
        p3_layout.addStretch()
        
        self.launch_btn = QPushButton("SİSTEMİ BAŞLAT")
        self.launch_btn.setFixedHeight(60)
        self.launch_btn.clicked.connect(self.finish_and_launch)
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border-radius: 12px;
                font-size: 20px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        p3_layout.addWidget(self.launch_btn)
        
        self.stack.addWidget(self.page3)

        layout.addWidget(self.stack)

        # Footer
        footer = QLabel("© 2026 AYEC Pro | www.premiumonmuhasebe.com")
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
        self.thread = InstallThread()
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.status.connect(self.status_detail.setText)
        self.thread.finished.connect(lambda: self.stack.setCurrentIndex(2))
        self.thread.start()

    def finish_and_launch(self):
        appdata = os.getenv('LOCALAPPDATA')
        batch_path = os.path.join(appdata, "AYECPro", "Start_AYECPro.bat")
        if os.path.exists(batch_path):
            subprocess.Popen(['cmd.exe', '/c', f'"{batch_path}"'], shell=True)
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernSetup()
    window.show()
    sys.exit(app.exec())
