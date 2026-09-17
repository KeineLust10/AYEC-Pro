# -*- coding: utf-8 -*-

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from datetime import datetime
import os
from src.utils.logger import logger

class BackupScheduler(QObject):
    """
    Otomatik Yedekleme Zamanlayıcısı
    - Günlük 10:00 ve 17:00 yedekleri
    - Program kapanışında yedekleme
    """
    backup_completed = pyqtSignal(str, str) # type, path

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_schedule)
        
        # Check every 60 seconds
        self.timer.start(60000)
        
        # Initialize last run dates from settings or default to empty
        self.last_run_morning = self.db.get_setting("backup_last_run_morning", "")
        self.last_run_evening = self.db.get_setting("backup_last_run_evening", "")

    def check_schedule(self):
        """Dakikada bir çalışır ve zamanı kontrol eder"""
        now = datetime.now()
        current_time = now.time()
        today_str = now.strftime("%Y-%m-%d")
        
        # Custom Daily Backup
        # Check if daily backup is enabled
        if self.db.get_setting("backup_daily_enabled", "0") == "1":
            target_time_str = self.db.get_setting("backup_daily_time", "12:00")
            try:
                # Parse target time
                h, m = map(int, target_time_str.split(':'))
                
                # Check if current time matches target hour and today wasn't backed up yet
                # We check within the hour window to be safe if timer misses the exact minute
                # but we rely on last_run check to avoid duplicates
                if current_time.hour == h and self.last_run_morning != today_str:
                    logger.info(f"Scheduled backup triggering for time {target_time_str}")
                    self.perform_backup(f"auto_{h:02d}{m:02d}")
                    self.last_run_morning = today_str # Reuse this variable for daily tracker or rename it
                    self.db.set_setting("backup_last_run_morning", today_str)
            except ValueError:
                logger.error(f"Invalid backup time format: {target_time_str}")

        # Legacy support / clean up if needed:
        # We reused "backup_last_run_morning" as the tracker for the single daily backup to save space
        # Dropped "backup_auto_evening" logic as user requested single custom time choice

    def perform_backup(self, prefix="auto"):
        """Yedekleme işlemini gerçekleştirir"""
        try:
            # Şirket adını veritabanından al, bulunamazsa prefix'i kullan
            company_name = self.db.get_setting("company_name", prefix)
            if not company_name or len(company_name.strip()) == 0:
                company_name = prefix

            # Dosya adı için güvenli bir formata dönüştür
            safe_prefix = "".join(c for c in company_name if c.isalnum() or c in "-_ ").rstrip()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_prefix}_{timestamp}.db"
            
            # Kaynak veritabanı
            if hasattr(self.db, "backup_database"):
                created_path = self.db.backup_database(target_name=filename)
                if created_path and os.path.exists(created_path):
                    logger.info("Validated automatic backup created: %s", created_path)
                    self.backup_completed.emit("success", created_path)
                    return True

            logger.error("Validated automatic backup could not be created")
            self.backup_completed.emit(
                "error", "Validated automatic backup could not be created"
            )
            return False
                
        except Exception as e:
            logger.error(f"Otomatik yedek hatası ({prefix}): {e}")
            self.backup_completed.emit("error", str(e))
            return False

    def check_exit_backup(self):
        """Program kapanırken çalıştırılır"""
        if self.db.get_setting("backup_on_exit", "1") == "1":
            logger.info("Çıkış yedeği alınıyor...")
            return self.perform_backup("exit_backup")
        return False

# Global instance for easier access
_scheduler = None

def start_auto_backup(db, parent=None, **kwargs):
    """Sistemi başlatır"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackupScheduler(db, parent)
    return _scheduler

def get_backup_scheduler():
    """Mevcut zamanlayıcıyı döndürür"""
    return _scheduler
