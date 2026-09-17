# -*- coding: utf-8 -*-

"""
Alert Scheduler Service for AYEC Pro Voice Assistant
Zaman ayarlı sesli uyarı sistemi - DND mode, snooze, queue management
"""
import logging
from datetime import datetime, timedelta
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from src.utils.system_config import SystemConfig

logger = logging.getLogger("AlertScheduler")


def _row_get(row, key, default=None):
    """Safe access for dict/sqlite3.Row/plain mapping-like objects."""
    try:
        if row is None:
            return default
        if isinstance(row, dict):
            val = row.get(key, default)
            return default if val is None else val
        if hasattr(row, "keys") and key in row.keys():
            val = row[key]
            return default if val is None else val
        val = row[key]
        return default if val is None else val
    except Exception:
        return default


class AlertSchedulerService(QObject):
    """
    Sesli asistan için zamanlanmış uyarı servisi
    - Her dakika kontrol
    - Konuşma kuyruğu (çakışma önleme)
    - DND (Sessiz Saatler) desteği
    - Snooze mekanizması
    """
    
    alert_triggered = pyqtSignal(dict)  # Alert data
    
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        
        # Konuşma kuyruğu ve durum
        self.speech_queue = []
        self.is_speaking = False
        
        # Ertelenen uyarılar [(alert_data, resume_datetime)]
        self.snoozed_alerts = []
        
        # Timer: Her dakika kontrol
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_scheduled_alerts)
        self.timer.start(60000)  # 1 dakika = 60,000 ms
        
        logger.info("AlertSchedulerService başlatıldı (1 dakika interval)")
    
    def check_scheduled_alerts(self):
        """
        Her dakika çalışır
        1. Snoozed alerts kontrolü
        2. Scheduled alerts kontrolü
        """
        if not SystemConfig.is_feature_active(self.db, "scheduled_alerts"):
            return
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        current_date = now.strftime('%Y-%m-%d')
        
        # 1. Ertelenen uyarıları kontrol et
        self._check_snoozed_alerts(now)
        
        # 2. Zamanlanmış uyarıları kontrol et
        try:
            alerts = self.db.get_scheduled_alerts_by_time(current_time)
            
            for alert in alerts:
                alert_type = alert['alert_type']
                last_triggered = _row_get(alert, 'last_triggered')
                
                # Bugün zaten tetiklendi mi (Günde 1 kez)
                if last_triggered and last_triggered.startswith(current_date):
                    continue
                
                # Uyarıyı işle
                self._process_alert(alert, now)
                
                # Last triggered güncelle
                self.db.mark_alert_triggered(alert_type, now.isoformat())
        
        except Exception as e:
            logger.error(f"Scheduled alerts check error: {e}")
    
    def _process_alert(self, alert, now):
        """Uyarıyı işle - DND kontrolü + kuyruk"""
        alert_data = {
            'type': alert['alert_type'],
            'time': now.isoformat(),
            'is_critical': bool(_row_get(alert, 'is_critical', 0))
        }
        
        # DND kontrolü
        if self.is_within_quiet_hours() and not alert_data['is_critical']:
            # Sessiz saatlerde sadece toast göster
            self._show_silent_notification(alert_data)
            logger.info(f"DND aktif - Sadece toast: {alert_data['type']}")
            return
        
        # Kuyruğa ekle
        self.add_to_speech_queue(alert_data)
    
    def is_within_quiet_hours(self):
        """Sessiz saatler içinde miyiz?"""
        try:
            start_str = self.db.get_setting('quiet_hours_start', '19:00')
            end_str = self.db.get_setting('quiet_hours_end', '08:30')
            
            now = datetime.now().time()
            start = datetime.strptime(start_str, '%H:%M').time()
            end = datetime.strptime(end_str, '%H:%M').time()
            
            # Gece yarısını geçiyor mu (19:00 - 08:30 gibi)
            if start < end:
                return start <= now <= end
            else:
                return now >= start or now <= end
        
        except Exception as e:
            logger.error(f"DND check error: {e}")
            return False
    
    def add_to_speech_queue(self, alert_data):
        """Konuşma kuyruğuna ekle"""
        if not SystemConfig.is_feature_active(self.db, "voice_alerts"):
            self._show_silent_notification(alert_data)
            return
        self.speech_queue.append(alert_data)
        logger.info(f"Kuyruğa eklendi: {alert_data['type']} (Kuyruk boyutu: {len(self.speech_queue)})")
        self._process_speech_queue()
    
    def _process_speech_queue(self):
        """Kuyruğu işle - Çakışma önleyici"""
        if self.is_speaking or not self.speech_queue:
            return
        
        alert_data = self.speech_queue.pop(0)
        self.is_speaking = True
        
        logger.info(f"Seslendiriliyor: {alert_data['type']}")
        
        # Signal emit - Main window handle edecek
        self.alert_triggered.emit(alert_data)
        
        # 5 saniye sonra konuşma bitti kabul et
        QTimer.singleShot(5000, self._finish_speaking)
    
    def _finish_speaking(self):
        """Konuşma bitti, kuyruğa devam et"""
        self.is_speaking = False
        logger.info("Konuşma tamamlandı, kuyruğa devam ediliyor")
        self._process_speech_queue()
    
    def snooze_alert(self, alert_data, minutes=15):
        """Uyarıyı ertele"""
        resume_time = datetime.now() + timedelta(minutes=minutes)
        self.snoozed_alerts.append((alert_data, resume_time))
        logger.info(f"Ertelendi: {alert_data['type']} → {resume_time.strftime('%H:%M')}")
    
    def _check_snoozed_alerts(self, now):
        """Ertelenen uyarıları kontrol et"""
        for alert_data, resume_time in list(self.snoozed_alerts):
            if now >= resume_time:
                logger.info(f"Erteleme süresi doldu: {alert_data['type']}")
                self.add_to_speech_queue(alert_data)
                self.snoozed_alerts.remove((alert_data, resume_time))
    
    def _show_silent_notification(self, alert_data):
        """DND sırasında sessiz bildirim göster (AyecNotification ile)"""
        try:
            from src.ui.widgets.ayec_notification import NotificationManager
            
            if not hasattr(self.main_window, 'notification_manager'):
                self.main_window.notification_manager = NotificationManager(self.main_window)
            
            type_names = {
                'loan_reminder': '💳 Kredi Taksit Hatırlatması',
                'check_reminder': '📄 Çek/Senet Hatırlatması',
                'stock_critical': '📦 Kritik Stok Uyarısı'
            }
            
            title = type_names.get(alert_data['type'], 'Uyarı')
            message = f"{title}\n(Sessiz saatler - detaylar için finans sayfasına bakın)"
            
            self.main_window.notification_manager.show_notification(title, message, alert_data)
        
        except Exception as e:
            logger.error(f"Silent notification error: {e}")


# Test
if __name__ == "__main__":
    logger.info("=== Alert Scheduler Service ===")
    logger.info("Zaman ayarl? uyar? sistemi")
    logger.info("DND (Sessiz saatler) desteği")
    logger.info("Konuşma kuyruğu (çakışma önleme)")
    logger.info("Snooze mekanizmas?")
