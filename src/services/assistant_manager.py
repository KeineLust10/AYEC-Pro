# -*- coding: utf-8 -*-

import logging
import traceback
import re
import time
import unicodedata
import urllib.parse
import webbrowser
from types import SimpleNamespace
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from PyQt6.QtCore import QObject, QTimer, QVariantAnimation, QEasingCurve, pyqtSignal, QThread
from PyQt6.QtWidgets import QApplication, QLabel, QGraphicsOpacityEffect
from PyQt6.QtGui import QIcon
from src.services.assistant_workers import AssistantMonitoringWorker, PaymentReminderWorker
from src.ui.widgets.jarvis_toast import AssistantToast
from src.utils.system_config import SystemConfig
from src.services.whatsapp_service import WhatsAppService, WhatsAppDeliveryError

logger = logging.getLogger(__name__)


def _assistant_voice_feature_enabled(manager, key):
    feature_reader = getattr(manager, "_voice_feature_enabled", None)
    if callable(feature_reader):
        return feature_reader(key)
    db = getattr(manager, "db", None)
    if db is None:
        return True
    from src.services.voice_feature_settings import voice_feature_enabled

    return voice_feature_enabled(db, key, True)

class AssistantManager(QObject):
    """
    AI Asistan mantığını yöneten servis. 
    Main Window üzerindeki UI elemanlarına ve veritabanına erişim sağlar.
    """
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.db = main_window.db
        self.pending_action = None
        self.last_report_date = getattr(main_window, "last_report_date", None)
        self.assistant_monitor_worker = None
        self.payment_reminder_worker = None
        self.voice_assistant_thread = None
        self._voice_assistant_restart_pending = False
        self._voice_assistant_restart_notify = False
        self._conversation_workers = []
        self._conversation_history = []
        self._pending_voice_control = None
        self._pending_form_intake = None
        self._last_voice_change = None
        self._last_spoken_response = ""
        self._dictation_mode = False
        self._assistant_help_state = None
        self._payment_reminder_timer = QTimer(self)
        self._payment_reminder_timer.setInterval(30000)
        self._payment_reminder_timer.timeout.connect(self._check_payment_reminders)
        self._payment_reminder_timer.start()
        QTimer.singleShot(0, self._check_payment_reminders)
        QTimer.singleShot(0, self._preload_turkish_speech)

    def _voice_feature_enabled(self, key):
        from src.services.voice_feature_settings import voice_feature_enabled

        return voice_feature_enabled(self.db, key, True)

    def _preload_turkish_speech(self):
        if not self._assistant_voice_enabled():
            return
        try:
            from src.utils.local_turkish_tts import preload_async

            preload_async()
        except Exception:
            logger.debug("Local EMA speech preload was skipped", exc_info=True)

    def _log_soft_failure(self, context, exc):
        logger.debug("Assistant fallback triggered in %s: %s", context, exc, exc_info=True)
        
    def _assistant_voice_enabled(self):
        try:
            return self.db.get_setting(
                "asistan_voice_enabled",
                self.db.get_setting("assistant_voice_enabled", "1"),
            ) == "1"
        except Exception:
            return True

    def _assistant_tts_engine(self):
        try:
            return self.db.get_setting(
                "asistan_tts_engine",
                self.db.get_setting("assistant_tts_engine", "ema-lightning"),
            )
        except Exception:
            return "ema-lightning"

    def _assistant_edge_voice(self):
        try:
            return self.db.get_setting(
                "asistan_edge_voice",
                self.db.get_setting("assistant_edge_voice", "ema_default"),
            )
        except Exception:
            return "ema_default"

    def _assistant_edge_rate(self):
        try:
            return self.db.get_setting(
                "asistan_edge_rate",
                self.db.get_setting("assistant_edge_rate", "+0%"),
            )
        except Exception:
            return "+0%"

    def _assistant_edge_pitch(self):
        try:
            return self.db.get_setting(
                "asistan_edge_pitch",
                self.db.get_setting("assistant_edge_pitch", "+0Hz"),
            )
        except Exception:
            return "+0Hz"

    def _assistant_prefix(self):
        try:
            user_alias = self.db.get_setting("asistan_user_name", "Efendim")
            hitap_aktif = self.db.get_setting("asistan_hitap_aktif", "0") == "1"
            style = self.db.get_setting("asistan_greeting_style", "formal")
            separator = " " if style == "compact" else ", "
            return f"{user_alias}{separator}" if hitap_aktif else ""
        except Exception:
            return ""

    def get_asistan_name(self):
        try:
            return self.db.get_setting(
                "asistan_ozel_adi",
                self.db.get_setting("asistan_ozel_isim", "Asistan"),
            )
        except Exception:
            return "Asistan"

    def is_voice_assistant_enabled(self):
        try:
            return self.db.get_setting("voice_assistant_active", "1") == "1"
        except Exception:
            return False

    def start_voice_assistant(self, notify=False):
        """Starts the continuous speech command listener when enabled."""
        if not self.is_voice_assistant_enabled():
            self._voice_assistant_restart_pending = False
            return False
        if self.voice_assistant_thread and self.voice_assistant_thread.isRunning():
            if not getattr(self.voice_assistant_thread, "is_running", True):
                self._voice_assistant_restart_pending = True
                self._voice_assistant_restart_notify = bool(
                    self._voice_assistant_restart_notify or notify
                )
            return True
        self.voice_assistant_thread = None

        try:
            from src.utils.asistan_motoru import BulutAsistan

            raw_device = str(self.db.get_setting("voice_input_device", "default") or "default")
            self._voice_assistant_notify_when_ready = bool(notify)
            self.voice_assistant_thread = BulutAsistan(input_device_key=raw_device)
            self.voice_assistant_thread.tetik_sinyali.connect(self.aksiyon_merkezi)
            self.voice_assistant_thread.hata_sinyali.connect(self._handle_voice_assistant_error)
            self.voice_assistant_thread.hazir_sinyali.connect(self._handle_voice_assistant_ready)
            self.voice_assistant_thread.finished.connect(self._on_voice_assistant_finished)
            self.voice_assistant_thread.start()
            logger.info("Voice assistant listener initialization started")
            return True
        except Exception as exc:
            logger.error("Voice assistant start error: %s", exc, exc_info=True)
            if notify:
                self.main_window.show_notification(f"Sesli asistan başlatılamadı: {exc}", "error")
            return False

    def stop_voice_assistant(self, notify=False):
        self._voice_assistant_restart_pending = False
        self._voice_assistant_restart_notify = False
        thread = self.voice_assistant_thread
        if not thread:
            return
        try:
            if hasattr(thread, "stop"):
                thread.stop()
            elif thread.isRunning():
                thread.quit()
                thread.wait(1500)
            if self.voice_assistant_thread is thread and not thread.isRunning():
                self.voice_assistant_thread = None
            elif thread.isRunning():
                logger.info("Voice assistant listener is stopping; restart is deferred until shutdown completes.")
            if notify and not thread.isRunning():
                self.main_window.show_notification("Sesli asistan durduruldu.", "info")
        except Exception as exc:
            if self.voice_assistant_thread is thread and not thread.isRunning():
                self.voice_assistant_thread = None
            logger.warning("Voice assistant stop warning: %s", exc)

    def toggle_voice_assistant(self):
        if self.voice_assistant_thread and self.voice_assistant_thread.isRunning():
            self.db.set_setting("voice_assistant_active", "0")
            self.stop_voice_assistant(notify=True)
            return False
        self.db.set_setting("voice_assistant_active", "1")
        return self.start_voice_assistant(notify=True)

    def _handle_voice_assistant_error(self, message):
        logger.warning("Voice assistant error: %s", message)
        try:
            self.main_window.show_notification(str(message), "warning")
        except Exception:
            pass

    def _handle_voice_assistant_ready(self):
        if not getattr(self, "_voice_assistant_notify_when_ready", False):
            return
        try:
            self.main_window.show_notification("Sesli asistan dinleme modu ba\u015flat\u0131ld\u0131.", "success")
        except Exception:
            logger.debug("Voice assistant ready notification could not be shown", exc_info=True)

    def _on_voice_assistant_finished(self):
        logger.info("Voice assistant listener stopped")
        finished_thread = self.sender() or self.voice_assistant_thread
        if self.voice_assistant_thread is finished_thread:
            self.voice_assistant_thread = None
        if self._voice_assistant_restart_pending:
            notify = bool(self._voice_assistant_restart_notify)
            self._voice_assistant_restart_pending = False
            self._voice_assistant_restart_notify = False
            if self.is_voice_assistant_enabled():
                QTimer.singleShot(
                    0,
                    lambda requested_notify=notify: self.start_voice_assistant(
                        notify=requested_notify
                    ),
                )

    def _number_to_tr_words(self, n):
        """Sayıyı Türkçe metne çevirir"""
        if n == 0: return "sıfır"
        
        birler = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
        onlar = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
        
        def chunk_to_words(num):
            s = ""
            h = num // 100
            if h > 0:
                s += (birler[h] if h > 1 else "") + "yüz "
            o = (num % 100) // 10
            if o > 0:
                s += onlar[o] + " "
            b = num % 10
            if b > 0:
                s += birler[b] + " "
            return s.strip()

        words = []
        scales = [(1000000000, "milyar"), (1000000, "milyon"), (1000, "bin")]
        
        for scale_val, scale_name in scales:
            if n >= scale_val:
                count = n // scale_val
                if scale_name == "bin" and count == 1:
                    words.append("bin")
                else:
                    words.append(chunk_to_words(count))
                    words.append(scale_name)
                n = n % scale_val
        if n > 0:
            words.append(chunk_to_words(n))
        return " ".join([w for w in words if w]).strip()

    def _assistant_currency_code(self):
        try:
            curr = str(self.db.get_setting("currency", "") or "").upper()
        except Exception:
            curr = ""
        if "USD" in curr or "$" in curr: return "USD"
        if "EUR" in curr or "€" in curr: return "EUR"
        return "TRY"

    def _amount_in_words(self, amount, currency=None):
        code = currency or self._assistant_currency_code()
        major, minor = ("T\u00fcrk liras\u0131", "kuru\u015f")
        if code == "USD": major, minor = ("dolar", "sent")
        elif code == "EUR": major, minor = ("euro", "sent")
        
        try:
            val = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError):
            val = Decimal("0.00")
            
        sign = "eksi " if val < 0 else ""
        val = abs(val)
        whole = int(val)
        fraction = int((val - whole) * 100)
        
        if fraction == 100:
            whole += 1
            fraction = 0
            
        words = f"{self._number_to_tr_words(whole)} {major}"
        if fraction > 0:
            words = f"{words} {self._number_to_tr_words(fraction)} {minor}"
        return f"{sign}{words}"

    def _speak_async(self, text):
        if text:
            self._last_spoken_response = str(text)[:1200]
        if not text or not self._assistant_voice_enabled():
            return
        try:
            engine = self._assistant_tts_engine()
            voice = self._assistant_edge_voice()
            rate = self._assistant_edge_rate()
            pitch = self._assistant_edge_pitch()
            efekt = self.db.get_setting("telsiz_efekti_aktif", "0") == "1"
            
            from src.utils.asistan_motoru import sesli_cevap_ver_async
            sesli_cevap_ver_async(text, engine, voice=voice, rate=rate, pitch=pitch, efekt_aktif=efekt)
        except Exception as e:
            logger.error(f"TTS speak async error: {e}")

    def run_assistant_monitoring(self):
        """Assistant arka planda sistemi denetler ve önemli bir durum varsa uyarır"""
        try:
            if self.assistant_monitor_worker and self.assistant_monitor_worker.isRunning():
                return
                
            now = datetime.now()
            self.assistant_monitor_worker = AssistantMonitoringWorker(
                getattr(self.db, "_db_name", "ayecpro.db"),
                self.last_report_date,
                now,
                self
            )
            # Düzgün referanslar için MainWindow'daki metodlara bağla
            self.assistant_monitor_worker.result_ready.connect(self._on_monitoring_result)
            self.assistant_monitor_worker.finished.connect(self.assistant_monitor_worker.deleteLater)
            self.assistant_monitor_worker.start()
        except Exception as e:
            logger.warning(f"Assistant monitoring error: {e}")

    def _on_monitoring_result(self, result):
        try:
            if result.get("urgent_report"):
                self.show_assistant_alert("ACİL DURUM", result["urgent_report"])

            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            if result.get("daily_report_sent"):
                self.show_assistant_alert("GÜNLÜK RAPOR", "Günlük durum raporunuz WhatsApp ile iletildi.")
                self.last_report_date = today_str
            if result.get("evening_report_sent"):
                self.show_assistant_alert("BAŞARI RAPORU", "Günün özeti hazırlandı efendim.")
                self.last_report_date = today_str + "_evening"
            
            self._process_vehicle_maintenance_alerts(now)
            self._process_payment_reminders(now)

            # Update main window's date
            self.main_window.last_report_date = self.last_report_date
        except Exception as e:
            logger.warning(f"Assistant monitoring result error: {e}")

    def _process_vehicle_maintenance_alerts(self, now):
        try:
            if not SystemConfig.is_feature_active(self.db, "voice_alerts"):
                return
            sector_id = "teknik_servis"
            try:
                sector_manager = getattr(self.main_window, "sector_manager", None)
                if sector_manager and sector_manager.get_current_plugin():
                    sector_id = sector_manager.get_current_plugin().sector_id
                else:
                    sector_id = self.db.get_internal_setting("current_sector", "teknik_servis")
            except Exception:
                pass
            if sector_id != "otomotiv":
                return
            today_str = now.strftime("%Y-%m-%d")
            due_rows = self.db.ensure_due_vehicle_maintenance_notifications(today_str)
            km_rows = self.db.ensure_upcoming_vehicle_maintenance_km_notifications(500, today_str)
            inspection_rows = self.db.ensure_due_vehicle_inspection_notifications(today_str)
            self._send_vehicle_maintenance_whatsapp_reminders(today_str)
            self._send_vehicle_maintenance_km_whatsapp_reminders(today_str)
            self._send_vehicle_inspection_whatsapp_reminders(today_str)
            if hasattr(self.main_window, "refresh_notification_bell"):
                self.main_window.refresh_notification_bell()
            if (not due_rows and not km_rows and not inspection_rows) or now.hour < 8:
                return

            last_voice_date = self.db.get_internal_setting("vehicle_maintenance_voice_alert_date", "")
            if last_voice_date == today_str:
                return

            summary = []
            for row in due_rows[:3]:
                summary.append(f"{row['customer_name']} - {row['vehicle_plate'] or row['vehicle_brand'] or 'Arac'}")
            if not summary:
                for row in km_rows[:3]:
                    summary.append(f"{row['customer_name']} - {row['vehicle_plate'] or row['item_label'] or 'Arac'}")
            if not summary:
                for row in inspection_rows[:3]:
                    summary.append(f"{row['customer_name']} - {row['vehicle_plate'] or row['vehicle_brand'] or 'Arac'}")
            total_count = len(due_rows) + len(km_rows) + len(inspection_rows)
            suffix = "" if total_count <= 3 else f" ve {max(0, total_count - 3)} kayit daha"
            self.show_assistant_alert(
                "Bakim Hatirlatmasi",
                f"Bakim takibinde {total_count} kayit var: {', '.join(summary)}{suffix}.",
            )
            self.db.set_internal_setting("vehicle_maintenance_voice_alert_date", today_str)
        except Exception as e:
            logger.warning(f"Vehicle maintenance alert process error: {e}")

    def _process_payment_reminders(self, now):
        """Queue the configured reminder when its weekly schedule is due."""
        try:
            if self.db.get_setting("whatsapp_payment_reminder_enabled", "0") != "1":
                return
            target_day = int(self.db.get_setting("whatsapp_payment_reminder_day", "4") or 4)
            target_time = str(self.db.get_setting("whatsapp_payment_reminder_time", "10:00") or "10:00")
            if now.weekday() != target_day or now.strftime("%H:%M") != target_time:
                return
            run_key = now.strftime("%Y-%m-%d-%H:%M")
            if self.db.get_internal_setting("whatsapp_payment_last_run", "") == run_key:
                return
            worker = self.payment_reminder_worker
            if worker is not None and worker.isRunning():
                return
            worker = PaymentReminderWorker(
                getattr(self.db, "_db_name", "ayecpro.db"), run_key, self
            )
            self.payment_reminder_worker = worker
            worker.result_ready.connect(self._on_payment_reminder_result)
            worker.finished.connect(lambda current=worker: self._clear_payment_reminder_worker(current))
            worker.finished.connect(worker.deleteLater)
            worker.start()
        except Exception as error:
            logger.warning("Payment reminder scheduling error: %s", error)

    def _check_payment_reminders(self):
        self._process_payment_reminders(datetime.now())

    def _clear_payment_reminder_worker(self, worker):
        if self.payment_reminder_worker is worker:
            self.payment_reminder_worker = None

    def _on_payment_reminder_result(self, result):
        manual = int(result.get("manual", 0) or 0)
        sent = int(result.get("sent", 0) or 0)
        if manual:
            self.show_assistant_alert(
                "WhatsApp hatirlatmasi",
                f"{manual} mesaj kullanici onayi icin hazirlandi.",
            )
        elif sent:
            self.show_assistant_alert(
                "WhatsApp hatirlatmasi",
                f"{sent} borc odeme hatirlatmasi gonderildi.",
            )

    def _send_vehicle_maintenance_whatsapp_reminders(self, target_date):
        try:
            due_rows = self.db.get_due_vehicle_maintenance_whatsapp_rows(target_date)
            for row in due_rows:
                phone = re.sub(r"\D", "", str(row["customer_phone"] or ""))
                if not phone:
                    continue
                if phone.startswith("0") and len(phone) == 11:
                    phone = "90" + phone[1:]
                elif len(phone) == 10:
                    phone = "90" + phone

                message = (
                    f"Sayin {row['customer_name']}, {row['vehicle_plate'] or row['vehicle_brand'] or 'araciniz'} "
                    f"icin planli bakim tarihiniz {row['next_maintenance_date']} olarak yaklasmistir. "
                    f"Randevu taslagi olusturuldu. Uygun saat icin bizimle iletisime gecebilirsiniz. AYEC Pro Otomotiv"
                )
                webbrowser.open(f"https://wa.me/{phone}?text={urllib.parse.quote(message)}")
                self.db.mark_vehicle_maintenance_whatsapp_sent(row["id"])
        except Exception as e:
            logger.warning(f"Vehicle maintenance WhatsApp reminder error: {e}")

    def _send_vehicle_maintenance_km_whatsapp_reminders(self, target_date):
        try:
            due_rows = self.db.get_upcoming_vehicle_maintenance_km_whatsapp_rows(500, target_date)
            for row in due_rows:
                phone = re.sub(r"\D", "", str(row["customer_phone"] or ""))
                if not phone:
                    continue
                if phone.startswith("0") and len(phone) == 11:
                    phone = "90" + phone[1:]
                elif len(phone) == 10:
                    phone = "90" + phone

                remaining = max(0, int(row["next_due_odometer"] or 0) - int(row["current_odometer"] or 0))
                message = (
                    f"Sayin {row['customer_name']}, {row['vehicle_plate'] or row['vehicle_brand'] or 'araciniz'} "
                    f"icin {row['item_label']} bakimi yaklasiyor. Yaklasik {remaining} KM kaldi. "
                    "Kontrol ve randevu icin bizimle iletisime gecebilirsiniz. AYEC Pro Otomotiv"
                )
                webbrowser.open(f"https://wa.me/{phone}?text={urllib.parse.quote(message)}")
                self.db.mark_vehicle_maintenance_item_km_whatsapp_sent(row["item_id"])
        except Exception as e:
            logger.warning(f"Vehicle maintenance KM WhatsApp reminder error: {e}")

    def _send_vehicle_inspection_whatsapp_reminders(self, target_date):
        try:
            due_rows = self.db.get_due_vehicle_inspection_whatsapp_rows(target_date)
            for row in due_rows:
                phone = re.sub(r"\D", "", str(row["customer_phone"] or ""))
                if not phone:
                    continue
                if phone.startswith("0") and len(phone) == 11:
                    phone = "90" + phone[1:]
                elif len(phone) == 10:
                    phone = "90" + phone

                message = (
                    f"Sayin {row['customer_name']}, {row['vehicle_plate'] or row['vehicle_brand'] or 'araciniz'} "
                    f"icin muayene tarihiniz {row['inspection_due_date'] or '-'} olarak yaklasmistir. "
                    "Planlama ve randevu icin bizimle iletisime gecebilirsiniz. AYEC Pro Otomotiv"
                )
                webbrowser.open(f"https://wa.me/{phone}?text={urllib.parse.quote(message)}")
                self.db.mark_vehicle_inspection_notification_sent(row["id"])
        except Exception as e:
            logger.warning(f"Vehicle inspection WhatsApp reminder error: {e}")

    def show_assistant_alert(self, title, message):
        """Asistan tarzı özel bir toast uyarısı çıkartır"""
        toast = AssistantToast(self.main_window, title, message)
        toast.clicked.connect(self.main_window.toggle_assistant)
        toast.show_toast()
        
        if self._assistant_voice_enabled():
            speech_text = message
            if len(speech_text) > 150:
                speech_text = speech_text[:147] + "..."
            self._speak_async(speech_text)

    def start_assistant_visual_feedback(self, duration_ms=3500):
        if not hasattr(self.main_window, "assistant_fab") or not self.main_window.assistant_fab:
            return

        # Pulse animasyonu (Genişleme efekti)
        if hasattr(self, "_assistant_pulse_anim") and self._assistant_pulse_anim:
            try:
                self._assistant_pulse_anim.stop()
            except Exception as exc:
                self._log_soft_failure("start_assistant_visual_feedback.stop_existing_anim", exc)

        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(520)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.setLoopCount(-1)

        def on_val(v):
            try:
                base = getattr(self.main_window, "_assistant_fab_base_rect", self.main_window.assistant_fab.geometry())
                grow = int(6 * (0.3 + 0.7 * abs((float(v) * 2) - 1)))
                self.main_window.assistant_fab.setGeometry(base.adjusted(-grow, -grow, grow, grow))
            except Exception as exc:
                self._log_soft_failure("start_assistant_visual_feedback.on_val", exc)

        anim.valueChanged.connect(on_val)
        self._assistant_pulse_anim = anim
        anim.start()

        def stop():
            try:
                if hasattr(self, "_assistant_pulse_anim"):
                    self._assistant_pulse_anim.stop()
                base = getattr(self.main_window, "_assistant_fab_base_rect", None)
                if base:
                    self.main_window.assistant_fab.setGeometry(base)
            except Exception as exc:
                self._log_soft_failure("start_assistant_visual_feedback.stop", exc)

        QTimer.singleShot(int(duration_ms), stop)

    def aksiyon_merkezi(self, aksiyon, parametre):
        """Sesli Asistan'dan gelen komutları işler"""
        logger.info(f"Asistan tetiklendi: {aksiyon} - Parametre: {parametre}")
        prefix = self._assistant_prefix()

        if aksiyon == "assistant_chat" and self._pending_voice_control:
            answer = "".join(
                char for char in unicodedata.normalize("NFKD", str(parametre or "").casefold())
                if not unicodedata.combining(char)
            ).replace("\u0131", "i")
            words = set(re.findall(r"\w+", answer))
            if words.intersection({"evet", "tamam", "onayliyorum", "devam", "baslayalim", "dolduralim", "olur"}):
                self._confirm_voice_control(True)
                return
            if words.intersection({"hayir", "iptal", "vazgectim", "sonra", "istemiyorum"}):
                self._confirm_voice_control(False)
                return

        form_intake = getattr(self, "_pending_form_intake", None)
        if aksiyon == "assistant_chat" and form_intake and form_intake.get("status") == "awaiting_consent":
            answer = "".join(
                char for char in unicodedata.normalize("NFKD", str(parametre or "").casefold())
                if not unicodedata.combining(char)
            ).replace("\u0131", "i")
            words = set(re.findall(r"\w+", answer))
            if words.intersection({"evet", "tamam", "olur", "baslayalim", "dolduralim", "hadi"}):
                self._resolve_form_assistance_confirmation(True)
                return
            if words.intersection({"hayir", "istemiyorum", "vazgectim", "sonra"}):
                self._resolve_form_assistance_confirmation(False)
                return

        if aksiyon not in {"confirm_yes", "confirm_no", "voice_cancel_pending", "voice_repeat_last", "voice_stop_speech", "voice_help_next", "assistant_help", "assistant_unclear", "assistant_conversation_result"} and self._pending_voice_control:
            self._pending_voice_control = None

        if aksiyon == "assistant_unclear":
            message = "Komutu net anlayamadim. Lutfen tekrar edin; hicbir islem yapmadim."
            self.main_window.show_notification(message, "warning")
            self._speak_async(message)
            return

        if aksiyon == "assistant_chat" and self._dictation_mode:
            from src.services.assistant_ui_actions import append_dictation

            root = self._assistant_action_root(getattr(self.main_window, "_current_page_index", None))
            ok, message = append_dictation(root, parametre)
            self.main_window.show_notification(message, "success" if ok else "warning")
            self._speak_async(message)
            return

        if aksiyon == "assistant_named_target":
            form_intake = getattr(self, "_pending_form_intake", None)
            if form_intake:
                if form_intake.get("status") == "active":
                    page_id = getattr(self.main_window, "_current_page_index", None)
                    current_root = self._assistant_action_root(page_id)
                    if (
                        time.monotonic() <= form_intake.get("expires_at", 0)
                        and form_intake.get("page_id") == page_id
                        and form_intake.get("root") is current_root
                    ):
                        self._start_local_conversation(parametre)
                        return
                    self._pending_form_intake = None
                    self._set_form_voice_followup(False)
                if form_intake.get("status") == "awaiting_consent":
                    answer = "".join(
                        char for char in unicodedata.normalize(
                            "NFKD", str(parametre or "").casefold()
                        )
                        if not unicodedata.combining(char)
                    ).replace("\u0131", "i")
                    words = set(re.findall(r"\w+", answer))
                    affirmative = words.intersection({
                        "evet", "tamam", "olur", "baslayalim", "dolduralim",
                        "dolduruyoruz", "soyluyorum", "hadi",
                    })
                    negative = words.intersection({
                        "hayir", "istemiyorum", "vazgectim", "sonra",
                    })
                    if affirmative:
                        self._resolve_form_assistance_confirmation(True)
                        return
                    if negative:
                        self._resolve_form_assistance_confirmation(False)
                        return
            elif self._is_form_assistance_phrase(parametre):
                page_id = getattr(self.main_window, "_current_page_index", None)
                if self._offer_form_assistance(page_id, force=True):
                    self._resolve_form_assistance_confirmation(True)
                    return
            self._resolve_named_ui_target(parametre)
            return

        if isinstance(aksiyon, str) and aksiyon.startswith("voice_"):
            self._handle_voice_accessibility_command(aksiyon, parametre)
            return

        if aksiyon == "assistant_chat":
            self._start_local_conversation(parametre)
            return

        if aksiyon == "new_service_dialog":
            self._open_new_service_dialog()
            return

        if aksiyon == "assistant_conversation_result":
            self._apply_conversation_result(parametre)
            return

        if aksiyon == "wake_ack":
            msg = f"{prefix}dinliyorum."
            self.start_assistant_visual_feedback(1800)
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
            return

        # Sayfa Açma Komutları
        if isinstance(aksiyon, str) and (
            aksiyon.startswith("page:")
            or aksiyon in {"open_page", "open_page_search"}
        ):
            try:
                idx = int(aksiyon.split(":", 1)[1].strip()) if ":" in aksiyon else int(str(parametre).split("|")[0].strip())
                search_text = ""
                if aksiyon == "open_page_search" and "|" in str(parametre):
                    search_text = str(parametre).split("|", 1)[1].strip()
                page_name = self.main_window.get_page_name_by_index(idx)
                msg = f"{prefix}{page_name} sayfasını açıyorum."
                self.start_assistant_visual_feedback()
                self.main_window.show_notification(msg, "info")
                self._speak_async(msg)
                self.main_window.on_menu_click(idx)
                if search_text:
                    QTimer.singleShot(
                        700,
                        lambda text=search_text: self.main_window.perform_search_on_page(text),
                    )
                return
            except Exception as exc:
                self._log_soft_failure("aksiyon_merkezi.open_page", exc)

        # Özel Aksiyonlar
        if aksiyon == "stok_sorgu":
            msg = f"{prefix}stok ekranını açıyorum."
            self.start_assistant_visual_feedback()
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
            self.main_window.on_menu_click(999)
            if parametre:
                QTimer.singleShot(700, lambda: self.main_window.perform_search_on_page(parametre))

        elif aksiyon == "list_critical_stock":
            try:
                items = self.db.get_critical_stock_items() or []
                count = len(items)
                msg = (
                    f"{prefix} kritik seviyede {count} stok kalemi var. "
                    "Kritik stok ekranini aciyorum."
                    if count
                    else f"{prefix} kritik seviyede stok bulunmuyor."
                )
            except Exception as exc:
                self._log_soft_failure("aksiyon_merkezi.list_critical_stock", exc)
                msg = f"{prefix} kritik stok ekranini aciyorum."
            self.start_assistant_visual_feedback()
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
            self.main_window.on_menu_click(50)

        elif aksiyon == "stock_summary":
            try:
                stats = self.db.get_stock_stats() or {}
                item_count = int(stats.get("total_items", 0) or 0)
                total_stock = int(float(stats.get("total_stock", 0) or 0))
                critical_count = int(stats.get("critical_items", 0) or 0)
                msg = (
                    f"{prefix} {item_count} stok kartinda toplam {total_stock} urun var. "
                    f"Kritik seviyedeki kart sayisi {critical_count}."
                )
            except Exception as exc:
                self._log_soft_failure("aksiyon_merkezi.stock_summary", exc)
                msg = f"{prefix} stok ozetini aciyorum."
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
            self.main_window.on_menu_click(50)

        elif aksiyon == "panel_ac":
            msg = f"{prefix} teknisyen panelini aciyorum."
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
            self.main_window.on_menu_click(62)

        elif aksiyon == "select_service_device":
            dialog = getattr(self.main_window, "_active_device_selection_dialog", None)
            if dialog is None or not dialog.isVisible():
                self._start_local_conversation(f"{parametre} sec", continuation=True)
                return
            selected, msg = dialog.select_by_voice(parametre)
            self.main_window.show_notification(msg, "info" if selected else "warning")
            self._speak_async(msg)

        elif aksiyon == "servis_ac":
            self._open_new_service_dialog()

        elif aksiyon == "check_appointments":
            msg = f"{prefix} randevularinizi kontrol ediyorum."
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
            self.main_window.on_menu_click(30)

        elif aksiyon == "financial_summary":
            self.aksiyon_merkezi("accounting_summary", parametre)

        elif aksiyon == "customer_360":
            target = str(parametre or "").strip()
            customer_id = self.db.get_customer_id_by_name(target) if target else None
            if customer_id and hasattr(self.main_window, "open_customer_360_by_id"):
                msg = f"{prefix}{target} musterisi icin 360 derece gorunumu aciyorum."
                self.main_window.show_notification(msg, "info")
                self._speak_async(msg)
                self.main_window.open_customer_360_by_id(customer_id)
            else:
                msg = f"{prefix} musteriyi bulamadim. Musteri listesini aciyorum."
                self.main_window.show_notification(msg, "warning")
                self._speak_async(msg)
                self.main_window.on_menu_click(21)

        elif aksiyon == "device_status_query":
            msg = f"{prefix} cihaz ve servis durumunu aciyorum."
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
            self.main_window.on_menu_click(201)

        elif aksiyon == "discount_advice":
            msg = f"{prefix} indirim tavsiyesi icin musteri ekranini aciyorum."
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
            self.main_window.on_menu_click(21)

        elif aksiyon == "loan_summary":
            msg = f"{prefix} borc ozetini aciyorum."
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
            self.main_window.on_menu_click(101)

        elif aksiyon == "check_summary":
            msg = f"{prefix} cek ve senet ekranini aciyorum."
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
            self.main_window.on_menu_click(106)

        elif aksiyon == "stock_comparison":
            msg = f"{prefix} stok karsilastirma ekranini aciyorum."
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
            self.main_window.on_menu_click(50)

        elif aksiyon in {"add_quick_note_voice", "add_reminder_voice"}:
            msg = f"{prefix} ilgili kayit ekranini aciyorum."
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
            self.main_window.on_menu_click(90)

        elif aksiyon == "closing_routine":
            self.arz_et_gunluk_plan()

        elif aksiyon == "apply_zam":
            scope, category, affected, scope_error = self._resolve_voice_stock_scope(parametre)
            if scope_error:
                self.pending_action = None
                self.main_window.pending_action = None
                self.main_window.show_notification(scope_error, "warning")
                self._speak_async(scope_error)
                return
            match = re.search(r"%(\d+)", str(parametre or ""))
            if not match:
                self.pending_action = None
                self.main_window.pending_action = None
                msg = f"{prefix} tum aktif stok satis fiyatlari icin yuzde kac zam uygulayayim?"
                self.main_window.show_notification(msg, "warning")
                self._speak_async(msg)
                return
            pct = int(match.group(1))
            if pct < 1 or pct > 100:
                self.pending_action = None
                self.main_window.pending_action = None
                msg = f"{prefix} yuzde 1 ile 100 arasinda bir oran soyleyin."
                self.main_window.show_notification(msg, "warning")
                self._speak_async(msg)
                return
            action = {
                "type": "apply_zam", "percentage": pct,
                "scope": scope, "category": category, "affected_count": affected,
            }
            self.pending_action = action
            self.main_window.pending_action = action
            if affected is None:
                target_label = (
                    f"{category} kategorisindeki stok kartlarinin"
                    if category else "tum aktif stok kartlarinin"
                )
            elif category:
                target_label = f"{category} kategorisindeki {affected} kartin"
            else:
                target_label = f"{affected} aktif stok kartinin"
            msg = (
                f"{prefix} yuzde {pct} zam, {target_label} satis fiyatini etkiler. "
                "Bu toplu islem sesle geri alinamaz. Uygulamami onayliyor musunuz?"
            )
            self.main_window.show_notification(msg, "warning")
            self._speak_async(msg)
            
        elif aksiyon == "accounting_summary":
            try:
                from src.utils.finance_manager import FinanceManager
                fm = FinanceManager(self.db)
                data = fm.get_financial_summary("month") or {}
                gelir = float(data.get("gross_revenue", 0.0) or 0.0)
                gider = float(data.get("expenses", 0.0) or 0.0)
                net = gelir - gider
                msg = f"{prefix} Bu ay toplam {self._amount_in_words(gelir)} gelir ve {self._amount_in_words(gider)} gideriniz var. Net durumunuz {self._amount_in_words(net)}."
                self.start_assistant_visual_feedback()
                self.main_window.show_notification("Finansal Özet Hazırlandı", "success")
                self._speak_async(msg)
                self.main_window.on_menu_click(101)
            except Exception as exc:
                self._log_soft_failure("aksiyon_merkezi.accounting_summary", exc)

        elif aksiyon == "managerial_summary":
            # (ModernDesktopApp içindeki 4043-4085 arası logic buraya gelecek şekilde özetlenmiştir)
            msg = f"{prefix} Yönetici özetini hazırlıyorum."
            self._speak_async(msg)
            self.main_window.on_menu_click(40)

        elif aksiyon == "customer_debt_summary":
            try:
                balances = self.db.get_customer_balances() or []
                debtors = [row for row in balances if float(row[2] or 0) < 0]
                total = sum(abs(float(row[2] or 0)) for row in debtors)
                if debtors:
                    msg = (
                        f"{prefix} borcu bulunan {len(debtors)} musteri var. "
                        f"Toplam alacak {self._amount_in_words(total)}."
                    )
                else:
                    msg = f"{prefix} borcu bulunan musteri yok."
                self.main_window.show_notification(msg, "info")
                self._speak_async(msg)
                self.main_window.on_menu_click(21)
            except Exception as exc:
                self._log_soft_failure("aksiyon_merkezi.customer_debt_summary", exc)
                msg = f"{prefix} musteri borc ozeti hazirlanamadi."
                self.main_window.show_notification(msg, "error")
                self._speak_async(msg)

        elif aksiyon == "service_workload_summary":
            try:
                self.db.cursor.execute(
                    "SELECT COALESCE(status, 'Belirsiz'), COUNT(*) FROM devices "
                    "WHERE COALESCE(is_deleted, 0)=0 GROUP BY COALESCE(status, 'Belirsiz') "
                    "ORDER BY COUNT(*) DESC"
                )
                rows = self.db.cursor.fetchall() or []
                total = sum(int(row[1] or 0) for row in rows)
                details = ", ".join(
                    f"{row[0]} {int(row[1] or 0)}" for row in rows[:3]
                )
                msg = (
                    f"{prefix} serviste toplam {total} cihaz var. {details}."
                    if details
                    else f"{prefix} serviste aktif cihaz kaydi bulunmuyor."
                )
                self.main_window.show_notification(msg, "info")
                self._speak_async(msg)
                self.main_window.on_menu_click(201)
            except Exception as exc:
                self._log_soft_failure("aksiyon_merkezi.service_workload_summary", exc)
                msg = f"{prefix} servis is yuku hazirlanamadi."
                self.main_window.show_notification(msg, "error")
                self._speak_async(msg)

        elif aksiyon == "sync_now":
            started = bool(
                hasattr(self.main_window, "start_web_sync")
                and self.main_window.start_web_sync(silent=False)
            )
            msg = (
                f"{prefix} web ve masaustu senkronizasyonunu baslattim."
                if started
                else f"{prefix} senkronizasyon baslatilamadi veya zaten devam ediyor."
            )
            self.main_window.show_notification(msg, "success" if started else "warning")
            self._speak_async(msg)

        elif aksiyon == "assistant_help":
            self._announce_assistant_capabilities()

        elif aksiyon == "check_appointments":
            msg = f"{prefix} Randevularınızı kontrol ediyorum."
            self._speak_async(msg)
            self.main_window.on_menu_click(30)

        elif aksiyon == "greeting_routine":
            self.arz_et_gunluk_plan()

        elif aksiyon == "confirm_yes":
            if self._pending_form_intake and self._pending_form_intake.get("status") == "awaiting_consent":
                self._resolve_form_assistance_confirmation(True)
            elif self._pending_voice_control:
                self._confirm_voice_control(True)
            elif hasattr(self.main_window, "pending_action") and self.main_window.pending_action:
                self._handle_confirmation(True)
        elif aksiyon == "confirm_no":
            if self._pending_voice_control:
                self._confirm_voice_control(False)
            elif self._pending_form_intake:
                self._resolve_form_assistance_confirmation(False)
            else:
                self._handle_confirmation(False)

    def _visible_assistant_menu(self):
        sidebar = getattr(self.main_window, "app_sidebar", None)
        side_menu = getattr(sidebar, "side_menu", None)
        buttons = getattr(side_menu, "_btn_map", {}) if side_menu else {}
        labels = getattr(side_menu, "_badge_names", {}) if side_menu else {}
        catalog = []
        for page_id, button in buttons.items():
            try:
                page_id = int(page_id)
                if page_id < 0 or not self.main_window._is_page_allowed_for_active_sector(page_id):
                    continue
                label = str(labels.get(page_id) or self.main_window.get_page_name_by_index(page_id))
                if label.strip():
                    catalog.append((page_id, label.strip()))
            except Exception:
                continue
        return sorted(set(catalog), key=lambda item: (item[1].casefold(), item[0]))

    def _assistant_capability_entries(self, root):
        from src.services.assistant_ui_actions import describe_controls

        control_types = {
            "button": "d\u00fc\u011fme", "action": "i\u015flem",
            "check": "onay kutusu", "radio": "se\u00e7enek",
            "table": "tablo", "combo": "se\u00e7im listesi",
            "text": "metin alan\u0131", "multiline": "metin alan\u0131",
            "number": "say\u0131sal alan", "date": "tarih alan\u0131",
            "time": "saat alan\u0131", "datetime": "tarih ve saat alan\u0131",
            "tabs": "sekme",
        }
        controls, _bindings = describe_controls(root, limit=1000)
        entries = []
        for item in controls:
            label = str(item.get("label") or "").strip()
            if label:
                kind = control_types.get(str(item.get("type") or ""), "kontrol")
                entries.append(kind + ": " + label)
        entries.extend("Men\u00fc: " + label for _page, label in self._visible_assistant_menu())
        return entries

    def _announce_assistant_capabilities(self, continue_listing=False):
        page_id = getattr(self.main_window, "_current_page_index", None)
        root = self._assistant_action_root(page_id)
        state = self._assistant_help_state
        if continue_listing and (not state or state.get("page_id") != page_id or state.get("root") is not root):
            message = "Devam edilecek g\u00fcncel bir yetenek listesi yok. Neler yapabilirim diye sorun."
        else:
            if not continue_listing:
                entries = self._assistant_capability_entries(root)
                self._assistant_help_state = {
                    "page_id": page_id, "root": root, "entries": entries, "offset": 0,
                }
                state = self._assistant_help_state
            else:
                entries = self._assistant_capability_entries(root)
                if entries != state.get("entries", []):
                    state["entries"] = entries
                    state["offset"] = 0
            try:
                page_label = self.main_window.get_page_name_by_index(page_id)
            except Exception:
                page_label = "aktif ekran"
            start = int(state.get("offset", 0))
            batch = state.get("entries", [])[start:start + 8]
            state["offset"] = start + len(batch)
            more = state["offset"] < len(state.get("entries", []))
            details = "; ".join(batch) if batch else "Eri\u015filebilir ek kontrol veya men\u00fc bulamad\u0131m"
            message = page_label + " ekran\u0131ndas\u0131n\u0131z. "
            if not continue_listing:
                message += (
                    "Ekran\u0131 oku, sonraki alana ge\u00e7, dikte modunu a\u00e7, bu ekranda ara, "
                    "se\u00e7ili kayd\u0131 a\u00e7 veya son de\u011fi\u015fikli\u011fi geri al diyebilirsiniz. "
                    "Kritik kaydetme, silme ve \u00f6deme ad\u0131mlar\u0131nda onay\u0131n\u0131z\u0131 isterim. "
                )
            message += "Kullanilabilir oge listesi: " + details + "."
            if not continue_listing and not state.get("entries"):
                message += " Ekrani oku, sonraki alana gec, dikte modunu ac veya bu ekranda ara diyebilirsiniz."
            if more:
                message += " Devam\u0131 i\u00e7in sonraki komutlar deyin."
            else:
                self._assistant_help_state = None
        self.main_window.show_notification(message, "info")
        self._speak_async(message)

    def _start_local_conversation(self, utterance, continuation=False):
        try:
            from src.services.assistant_conversation import LocalAssistantConversation
            from src.services.assistant_ui_actions import describe_controls

            pending_form = getattr(self, "_pending_form_intake", None)
            if pending_form and pending_form.get("status") == "active":
                pending_form["expires_at"] = time.monotonic() + 300.0
                self._set_form_voice_followup(True)

            page_id = getattr(self.main_window, "_current_page_index", None)
            root = self._assistant_action_root(page_id)
            controls, bindings = describe_controls(root, utterance=utterance)
            worker = LocalAssistantConversation(
                utterance,
                self._visible_assistant_menu(),
                page_id,
                self._conversation_history,
                controls,
                self,
                continuation=continuation,
            )
            worker.control_bindings = bindings
            worker.action_root = root
            worker.page_id = page_id
            worker.continuation = bool(continuation)
            worker.resolved.connect(self._on_conversation_resolved)
            worker.finished.connect(self._on_conversation_finished)
            self._conversation_workers.append(worker)
            worker.start()
        except Exception as exc:
            self._log_soft_failure("assistant.local_conversation", exc)
            self._speak_async("Su anda sohbet isteginizi isleyemiyorum.")

    def _release_conversation_worker(self, worker):
        if worker in self._conversation_workers:
            self._conversation_workers.remove(worker)
        worker.deleteLater()

    def _on_conversation_resolved(self, result):
        self._apply_conversation_result(result, self.sender())

    def _on_conversation_finished(self):
        worker = self.sender()
        if worker is not None:
            self._release_conversation_worker(worker)

    def _assistant_action_root(self, page_id):
        modal = QApplication.activeModalWidget()
        if modal is not None:
            return modal
        try:
            page = self.main_window.get_page(page_id) if page_id is not None else None
            if page is not None:
                return page
        except Exception:
            pass
        return self.main_window

    def _resolve_named_ui_target(self, utterance):
        """Route an exact spoken menu, button, or tab name without an LLM call."""
        from PyQt6.QtWidgets import QAbstractButton, QTabWidget
        from PyQt6.QtGui import QAction
        from src.services.assistant_ui_actions import describe_controls
        from src.services.assistant_conversation import LocalAssistantConversation

        normalize = LocalAssistantConversation._normalize_text
        canonical_name = LocalAssistantConversation._canonical_spoken_name
        command_words = {"lutfen", "bana", "ac", "acalim", "git", "goster", "goruntule", "sayfasini", "ekranini", "ekranina", "sayfasina"}
        tokens = normalize(utterance).split()
        while tokens and tokens[0] in {"hey", "merhaba", "selam", "asistan", "lutfen", "bana"}:
            tokens.pop(0)
        while tokens and tokens[-1] in command_words:
            tokens.pop()
        spoken_name = canonical_name(" ".join(tokens))
        if not spoken_name:
            return False

        page_matches = [
            (page_id, label) for page_id, label in self._visible_assistant_menu()
            if canonical_name(label) == spoken_name
        ]
        current_page = getattr(self.main_window, "_current_page_index", None)
        if len(page_matches) == 1 and page_matches[0][0] != current_page:
            if not _assistant_voice_feature_enabled(self, "voice_feature_navigation"):
                message = "Sesle menu gezinme ayarlardan kapali."
                self.main_window.show_notification(message, "warning")
                self._speak_async(message)
                return True
            self.main_window.on_menu_click(page_matches[0][0])
            message = page_matches[0][1] + " ekranina geciyorum."
            self.main_window.show_notification(message, "info")
            self._speak_async(message)
            return True
        if len(page_matches) > 1:
            message = "Birden fazla menu eslesti. Lutfen tam menu adini soyleyin."
            self.main_window.show_notification(message, "warning")
            self._speak_async(message)
            return True

        root = self._assistant_action_root(current_page)
        descriptions, bindings = describe_controls(root, limit=1000)
        matches = []
        for item in descriptions:
            control = bindings.get(str(item.get("id") or ""))
            if control is None:
                continue
            control_type = str(item.get("type") or "")
            label = normalize(item.get("label"))
            aliases = [canonical_name(part) for part in re.split(r"[/|\n]", label) if len(canonical_name(part)) > 2]
            if label:
                aliases.append(canonical_name(label))
            if isinstance(control, QTabWidget) or control_type in {"combo", "tabs"}:
                options = [str(option) for option in item.get("options", [])]
                matches.extend(
                    (item, control, option, "select_option")
                    for option in options if canonical_name(option) == spoken_name
                )
            elif isinstance(control, (QAbstractButton, QAction)) and spoken_name in set(aliases):
                matches.append((item, control, None, "click_control"))

        if len(matches) != 1:
            if len(matches) > 1:
                message = "Bu isimde birden fazla kontrol var. Ekrandaki bolumunu da soyleyin."
                self.main_window.show_notification(message, "warning")
                self._speak_async(message)
                return True
            return False

        item, control, value, intent = matches[0]
        worker = SimpleNamespace(
            control_bindings={str(item.get("id") or ""): control},
            page_id=current_page,
            action_root=root,
            continuation=False,
        )
        self._apply_conversation_result({
            "intent": intent,
            "control_id": str(item.get("id") or ""),
            "value": value,
            "utterance": utterance,
            "reply": "",
        }, worker)
        return True

    def _handle_voice_accessibility_command(self, intent, parameter=""):
        from src.services.assistant_ui_actions import (
            move_focus,
            move_item_selection,
            read_active_field,
            read_form_feedback,
            read_screen,
            search_screen,
            scroll_screen,
            activate_selected_item,
            apply_control,
            focused_text_control,
        )

        accessibility_commands = {
            "voice_dictation_on", "voice_dictation_off", "voice_read_screen",
            "voice_read_field", "voice_read_form_feedback", "voice_focus_next",
            "voice_focus_previous", "voice_scroll_up", "voice_scroll_down",
            "voice_move_focus", "voice_select_next", "voice_select_previous",
            "voice_clear_field", "voice_delete_word", "voice_cursor_start",
            "voice_cursor_end", "voice_insert_comma", "voice_insert_period",
            "voice_insert_newline", "voice_search_screen",
        }
        navigation_commands = {
            "voice_next_record", "voice_previous_record", "voice_open_record",
            "voice_navigate_back",
        }
        if intent in navigation_commands and not _assistant_voice_feature_enabled(
            self, "voice_feature_navigation"
        ):
            message = "Sesle menu ve kayit gezinmesi ayarlardan kapali."
            self.main_window.show_notification(message, "warning")
            self._speak_async(message)
            return
        if intent in accessibility_commands and not _assistant_voice_feature_enabled(
            self, "voice_feature_screen_accessibility"
        ):
            message = "Ekran okuma ve erisilebilirlik komutlari ayarlardan kapali."
            self.main_window.show_notification(message, "warning")
            self._speak_async(message)
            return

        root = self._assistant_action_root(getattr(self.main_window, "_current_page_index", None))
        if intent == "voice_dictation_on":
            self._dictation_mode = True
            message = "Dikte modu a\u00e7\u0131k. Konu\u015ftuklar\u0131n\u0131z odaklanan metin alan\u0131na eklenecek. Bitirmek i\u00e7in dikteyi bitir deyin."
            ok = True
        elif intent == "voice_dictation_off":
            self._dictation_mode = False
            message = "Dikte modunu kapatt\u0131m."
            ok = True
        elif intent == "voice_cancel_pending":
            had_pending = bool(self._pending_voice_control)
            self._pending_voice_control = None
            ok = True
            message = "Bekleyen sesli islemi iptal ettim." if had_pending else "Iptal edilecek bekleyen bir islem yok."
        elif intent == "voice_undo":
            if _assistant_voice_feature_enabled(self, "voice_feature_voice_undo"):
                ok, message = self._undo_last_voice_change()
            else:
                ok, message = False, "Sesli degisikligi geri alma ayarlardan kapali."
        elif intent == "voice_form_status":
            if _assistant_voice_feature_enabled(self, "voice_feature_form_filling"):
                message = self._form_status_text(root)
            else:
                message = "Sesle form doldurma ayarlardan kapali."
            ok = True
        elif intent == "voice_form_reset":
            if _assistant_voice_feature_enabled(self, "voice_feature_field_correction"):
                ok, message = self._stage_form_reset(root)
            else:
                ok, message = False, "Form duzeltme ve temizleme ayarlardan kapali."
        elif intent == "voice_clear_named_field":
            if _assistant_voice_feature_enabled(self, "voice_feature_field_correction"):
                ok, message = self._stage_named_field_clear(root, parameter)
            else:
                ok, message = False, "Form duzeltme ve temizleme ayarlardan kapali."
        elif intent == "voice_repeat_last":
            message = self._last_spoken_response or "Tekrar edebilecegim bir onceki yanitim yok."
            ok = True
        elif intent == "voice_stop_speech":
            try:
                from src.utils.asistan_motoru import stop_tts_playback

                stop_tts_playback()
            except Exception as exc:
                self._log_soft_failure("assistant.stop_speech", exc)
            self.main_window.show_notification("Sesli yaniti durdurdum.", "info")
            return
        elif intent == "voice_help_next":
            self._announce_assistant_capabilities(continue_listing=True)
            return
        elif intent == "voice_open_stock_ocr":
            ok, message = self._open_stock_ocr_import()
        elif intent == "voice_read_screen":
            message = read_screen(root)
            ok = True
        elif intent == "voice_read_field":
            message = read_active_field(root)
            ok = True
        elif intent == "voice_read_form_feedback":
            message = read_form_feedback(root)
            ok = True
        elif intent == "voice_clear_field":
            control = focused_text_control(root)
            if control is None:
                ok, message = False, "Once temizlenecek metin alanina odaklanin."
            else:
                value = control.text() if hasattr(control, "text") else control.toPlainText()
                if not value.strip():
                    ok, message = True, "Alan zaten bos."
                else:
                    page_id = getattr(self.main_window, "_current_page_index", None)
                    message = self._stage_voice_confirmation(
                        control, "clear", None, False, root, page_id
                    )
                    ok = True
        elif intent in {
            "voice_delete_word", "voice_cursor_start", "voice_cursor_end",
            "voice_insert_comma", "voice_insert_period", "voice_insert_newline",
        }:
            control = focused_text_control(root)
            operation, value = {
                "voice_delete_word": ("delete_word", None),
                "voice_cursor_start": ("cursor_start", None),
                "voice_cursor_end": ("cursor_end", None),
                "voice_insert_comma": ("insert", ", "),
                "voice_insert_period": ("insert", ". "),
                "voice_insert_newline": ("insert", "\\n"),
            }[intent]
            if control is None:
                ok, message = False, "Once metin alanina odaklanin."
            else:
                ok, message = apply_control(control, operation, value)
        elif intent == "voice_search_screen":
            ok, message = search_screen(root, parameter)
        elif intent in {"voice_focus_next", "voice_focus_previous"}:
            ok, message = move_focus(root, forward=intent == "voice_focus_next")
        elif intent in {"voice_scroll_down", "voice_scroll_up"}:
            ok, message = scroll_screen(root, forward=intent == "voice_scroll_down")
        elif intent in {"voice_next_record", "voice_previous_record"}:
            ok, message = move_item_selection(root, forward=intent == "voice_next_record")
        elif intent == "voice_open_record":
            ok, message = activate_selected_item(root)
        elif intent == "voice_navigate_back":
            history = getattr(self.main_window, "_navigation_history", [])
            if history and hasattr(self.main_window, "navigate_back"):
                current_page = getattr(self.main_window, "_current_page_index", None)
                self.main_window.navigate_back()
                ok = getattr(self.main_window, "_current_page_index", None) != current_page
                message = "Onceki ekrana dondum." if ok else "Onceki ekrana gecemedim."
            else:
                ok, message = False, "Geri donulecek bir ekran gecmisi yok."
        else:
            return
        self.main_window.show_notification(message, "info" if ok else "warning")
        self._speak_async(message)

    def _form_missing_required(self, root):
        from src.services.assistant_ui_actions import describe_controls

        controls, _bindings = describe_controls(root, limit=1000)
        return [
            item for item in controls
            if item.get("required") and not item.get("filled")
            and item.get("type") in {"text", "multiline", "combo"}
        ]

    def _form_status_text(self, root):
        if not _assistant_voice_feature_enabled(self, "voice_feature_form_filling"):
            return "Sesle form doldurma ayarlardan kapali."
        if self._pending_form_intake and time.monotonic() > self._pending_form_intake.get("expires_at", 0):
            self._pending_form_intake = None
            self._set_form_voice_followup(False)
        if (
            not self._pending_form_intake
            or self._pending_form_intake.get("root") is not root
        ):
            return "Aktif bir sesli form doldurma oturumu yok. Bir form a\u00e7\u0131p doldurma yard\u0131m\u0131 isteyin."
        missing = self._form_missing_required(root)
        if not missing:
            return "Zorunlu alan kalmad\u0131. Doldurmak istedi\u011finiz ba\u015fka bilgi varsa s\u00f6yleyin."
        labels = [str(item.get("label") or "zorunlu alan").split(" / ", 1)[0].strip(" *") for item in missing[:8]]
        return "Tamamlanmas\u0131 gereken alanlar: " + ", ".join(labels) + ". \u0130lk alandan devam edelim."

    def _stage_named_field_clear(self, root, spoken_label):
        if not _assistant_voice_feature_enabled(self, "voice_feature_field_correction"):
            return False, "Form duzeltme ve temizleme ayarlardan kapali."
        if not _assistant_voice_feature_enabled(self, "voice_feature_critical_confirmation"):
            return False, "Kritik islemlerde sesli onay kapali; guvenlik icin islemi uygulamadim."
        from PyQt6.QtWidgets import QLineEdit, QPlainTextEdit, QTextEdit
        from src.services.assistant_ui_actions import describe_controls, label_for_control

        controls, bindings = describe_controls(root, limit=1000)
        normalize = lambda value: "".join(
            char for char in unicodedata.normalize("NFKD", str(value or "").casefold())
            if not unicodedata.combining(char)
        ).replace("\u0131", "i")
        target = normalize(spoken_label).strip()
        matches = []
        for item in controls:
            control = bindings.get(item.get("id"))
            if not isinstance(control, (QLineEdit, QTextEdit, QPlainTextEdit)):
                continue
            label = label_for_control(root, control)
            aliases = [normalize(part).strip() for part in re.split(r"[/|\n]", label)]
            if target and any(target == alias or target in alias for alias in aliases if alias):
                matches.append(control)
        if len(matches) != 1:
            return False, "Bu alan ad\u0131 tek bir kontrolle e\u015fle\u015fmedi. Ekran\u0131 oku deyip alan ad\u0131n\u0131 s\u00f6yleyin."
        control = matches[0]
        value = control.text() if isinstance(control, QLineEdit) else control.toPlainText()
        if not value.strip():
            return True, "Alan zaten bo\u015f."
        page_id = getattr(self.main_window, "_current_page_index", None)
        return True, self._stage_voice_confirmation(control, "clear", None, False, root, page_id)

    def _stage_form_reset(self, root):
        if not _assistant_voice_feature_enabled(self, "voice_feature_field_correction"):
            return False, "Form duzeltme ve temizleme ayarlardan kapali."
        if not _assistant_voice_feature_enabled(self, "voice_feature_critical_confirmation"):
            return False, "Kritik islemlerde sesli onay kapali; guvenlik icin islemi uygulamadim."
        from PyQt6.QtWidgets import QComboBox, QLineEdit, QPlainTextEdit, QTextEdit
        from src.services.assistant_ui_actions import describe_controls, label_for_control, snapshot_control

        controls, bindings = describe_controls(root, limit=1000)
        batch = []
        for item in controls:
            control = bindings.get(item.get("id"))
            if not isinstance(control, (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox)):
                continue
            if isinstance(control, QComboBox):
                value = control.currentText()
                needs_reset = bool(value.strip()) and (control.isEditable() or control.currentIndex() > 0)
            else:
                value = control.text() if isinstance(control, QLineEdit) else control.toPlainText()
                needs_reset = bool(value.strip())
            if needs_reset:
                batch.append({
                    "control": control,
                    "value": None,
                    "overwrite": True,
                    "operation": "clear",
                    "before": snapshot_control(control),
                })
        if not batch:
            return True, "Temizlenecek dolu metin alan\u0131 yok."
        page_id = getattr(self.main_window, "_current_page_index", None)
        self._pending_voice_control = {
            "batch": batch,
            "root": root,
            "page_id": page_id,
            "expires_at": time.monotonic() + 25.0,
        }
        labels = [label_for_control(root, item["control"]).split(" / ", 1)[0] for item in batch[:8]]
        return True, (
            "Formdaki " + str(len(batch)) + " dolu metin alan\u0131 temizlenecek: "
            + ", ".join(labels) + ". Onaylamak i\u00e7in evet, iptal etmek i\u00e7in hay\u0131r deyin."
        )

    def _open_stock_ocr_import(self):
        menu = self._visible_assistant_menu()
        stock_pages = [
            (page_id, label) for page_id, label in menu
            if "stok" in label.casefold() or "stock" in label.casefold()
        ]
        if not stock_pages:
            return False, "Stok ekrani mevcut menunuzde bulunmuyor."
        page_id, _label = next(
            ((page, label) for page, label in stock_pages
             if label.casefold().strip() in {"stoklar", "stok", "teknik stok"}),
            stock_pages[0],
        )
        if getattr(self.main_window, "_current_page_index", None) != page_id:
            self.main_window.on_menu_click(page_id)
        QTimer.singleShot(650, lambda selected_page=page_id: self._launch_stock_ocr_import(selected_page))
        return True, "Stok OCR ice aktarma penceresini aciyorum. Resim dosyasini secin; sonuc once onizlemeye gelecek."

    def _launch_stock_ocr_import(self, page_id):
        if getattr(self.main_window, "_current_page_index", None) != page_id:
            return False
        try:
            page = self.main_window.get_page(page_id)
            opener = getattr(page, "open_smart_stock_import", None)
            if not callable(opener):
                raise AttributeError("Stock import is unavailable on the selected page")
            opener(initial_mode="image")
            return True
        except Exception as exc:
            self._log_soft_failure("assistant.stock_ocr_import", exc)
            self._speak_async("Stok OCR ice aktarma penceresini acamadim.")
            return False

    def _apply_conversation_result(self, result, worker=None):
        try:
            if not isinstance(result, dict):
                return
            intent = result.get("intent")
            reply = str(result.get("reply") or "")[:500]
            if not reply:
                reply = "Size nasil yardimci olabilirim?"

            if intent == "navigate":
                if not _assistant_voice_feature_enabled(self, "voice_feature_navigation"):
                    reply = "Sesle menu gezinme ayarlardan kapali."
                    page_id = None
                else:
                    page_id = int(result.get("page_id"))
                available = {item[0] for item in self._visible_assistant_menu()}
                if page_id is None:
                    pass
                elif page_id not in available:
                    reply = "Bu ekran mevcut menunuzde kullanilamiyor."
                else:
                    if result.get("continue_action") and worker is not None and not getattr(worker, "continuation", False):
                        QTimer.singleShot(
                            700,
                            lambda target_page=page_id, request=str(result.get("utterance") or ""):
                            self._continue_voice_request(target_page, request),
                        )
                    self.main_window.on_menu_click(page_id)
            elif intent == "navigate_search":
                if not _assistant_voice_feature_enabled(self, "voice_feature_navigation"):
                    reply = "Sesle menu gezinme ayarlardan kapali."
                else:
                    page_id = int(result.get("page_id"))
                    available = {item[0] for item in self._visible_assistant_menu()}
                    query = str(result.get("query") or "").strip()[:160]
                    if page_id not in available:
                        reply = "Bu ekran mevcut menunuzde kullanilamiyor."
                    elif not query:
                        reply = "Arama icin bir deger alamadim."
                    else:
                        self.main_window.on_menu_click(page_id)
                        QTimer.singleShot(
                            700,
                            lambda page=page_id, value=query: self._search_after_navigation(page, value),
                        )
            elif intent == "new_service":
                dashboard = self.main_window.get_page(40)
                if dashboard and hasattr(dashboard, "open_new_service_dialog"):
                    QTimer.singleShot(
                        350,
                        lambda page=getattr(self.main_window, "_current_page_index", None):
                        self._offer_form_assistance(page, force=True),
                    )
                    dashboard.open_new_service_dialog()
                else:
                    reply = "Yeni servis formunu bu ekrandan acamiyorum."
            elif intent == "set_fields":
                if _assistant_voice_feature_enabled(self, "voice_feature_form_filling"):
                    reply = self._run_voice_control_batch(result, worker)
                else:
                    reply = "Sesle form doldurma ayarlardan kapali."
            elif intent in {"click_control", "set_field", "select_option", "set_toggle"}:
                table_selection = False
                tab_selection = False
                if intent == "select_option" and worker is not None:
                    from PyQt6.QtWidgets import QAbstractItemView, QTabWidget

                    selected_control = getattr(worker, "control_bindings", {}).get(
                        str(result.get("control_id") or "")
                    )
                    table_selection = isinstance(selected_control, QAbstractItemView)
                    tab_selection = isinstance(selected_control, QTabWidget)
                if (intent in {"click_control", "set_toggle"} or table_selection or tab_selection) and not _assistant_voice_feature_enabled(self, "voice_feature_ui_controls"):
                    reply = "Dugme ve anahtarlari sesle kullanma ayarlardan kapali."
                elif intent in {"set_field", "select_option"} and not table_selection and not tab_selection and not _assistant_voice_feature_enabled(self, "voice_feature_form_filling"):
                    reply = "Sesle form doldurma ayarlardan kapali."
                elif intent == "set_field" and result.get("overwrite") and not _assistant_voice_feature_enabled(self, "voice_feature_field_correction"):
                    reply = "Alan duzeltme ayarlardan kapali; mevcut degeri korudum."
                else:
                    reply = self._run_voice_control(intent, result, worker)

            if not (worker is not None and getattr(worker, "continuation", False)):
                self._conversation_history.append(("user", str(result.get("utterance") or "")))
            self._conversation_history.append(("assistant", reply))
            self._conversation_history = self._conversation_history[-12:]
            self.main_window.show_notification(reply, "info")
            self._speak_async(reply)
        except Exception as exc:
            self._log_soft_failure("assistant.conversation_result", exc)

    def _continue_voice_request(self, page_id, utterance):
        target_is_dialog = False
        if page_id in {60, 62}:
            modal = QApplication.activeModalWidget()
            target_is_dialog = type(modal).__name__ == "DeviceSelectionDialog"
        if (
            getattr(self.main_window, "_current_page_index", None) != page_id
            and not target_is_dialog
        ):
            message = "Hedef ekrana gecemedim; isteginizi uygulamadim."
            self.main_window.show_notification(message, "warning")
            self._speak_async(message)
            return
        self._start_local_conversation(utterance, continuation=True)

    def _search_after_navigation(self, page_id, query):
        if getattr(self.main_window, "_current_page_index", None) != page_id:
            return False
        from src.services.assistant_ui_actions import search_screen

        root = self._assistant_action_root(page_id)
        ok, message = search_screen(root, query)
        self.main_window.show_notification(message, "info" if ok else "warning")
        self._speak_async(message)
        return ok

    def _stage_voice_confirmation(self, control, operation, value, overwrite, root, page_id):
        from PyQt6.QtGui import QAction
        from PyQt6.QtWidgets import QAbstractButton
        from src.services.assistant_ui_actions import confirmation_summary, label_for_control

        if not _assistant_voice_feature_enabled(self, "voice_feature_critical_confirmation"):
            return "Kritik islemlerde sesli onay kapali; guvenlik icin islemi uygulamadim."

        if self._dictation_mode:
            self._dictation_mode = False
            if self.voice_assistant_thread is not None:
                self.voice_assistant_thread.dictation_mode = False
        label = label_for_control(root, control)
        if isinstance(control, (QAbstractButton, QAction)):
            label = control.text().replace("&", "").strip()
        label = label or "alan"
        try:
            page_label = self.main_window.get_page_name_by_index(page_id)
        except Exception:
            page_label = "aktif ekran"
        details = confirmation_summary(root, control, operation, value)
        self._pending_voice_control = {
            "control": control,
            "operation": operation,
            "value": value,
            "overwrite": overwrite,
            "root": root,
            "page_id": page_id,
            "expires_at": time.monotonic() + 25.0,
        }
        confirmation = f"{page_label} ekranindaki {label} islemini gerceklestirmek uzeresiniz. "
        if operation == "click":
            confirmation += (
                "Bu eylem kaydedilmis veriyi degistirirse asistan bunu otomatik geri alamayabilir. "
            )
        if details:
            confirmation += "Duydugum islem ozeti: " + details + ". "
        confirmation += "Devam etmek icin evet, vazgecmek icin hayir deyin."
        if self.voice_assistant_thread is not None:
            confirmation = "Dikte modu kapatildi. " + confirmation
        return confirmation

    def _run_voice_control(self, intent, result, worker):
        from PyQt6.QtWidgets import QAbstractItemView
        from src.services.assistant_ui_actions import (
            action_needs_confirmation,
            activate_table_row,
            apply_control,
            snapshot_control,
            table_row_open_handler_available,
        )

        control_id = str(result.get("control_id") or "")
        control = getattr(worker, "control_bindings", {}).get(control_id) if worker else None
        if control is None:
            return "Bu kontrol artik ekranda bulunmuyor. Komutunuzu tekrarlar misiniz?"
        page_id = getattr(worker, "page_id", None)
        if page_id != getattr(self.main_window, "_current_page_index", None):
            return "Ekran komut sirasinda degisti; guvenlik icin islemi uygulamadim."
        root = self._assistant_action_root(page_id)
        if getattr(worker, "action_root", None) is not root:
            return "Acik form degisti; guvenlik icin islemi uygulamadim."
        operation = {
            "click_control": "click",
            "set_field": "set",
            "select_option": "select",
            "set_toggle": "toggle",
        }[intent]
        value = result.get("value")
        overwrite = bool(result.get("overwrite"))
        if action_needs_confirmation(control, root) or (intent == "set_field" and overwrite):
            return self._stage_voice_confirmation(
                control, operation, value, overwrite, root, page_id
            )

        before = snapshot_control(control) if operation in {"set", "select", "toggle"} else None
        if operation == "click":
            QTimer.singleShot(
                350,
                lambda expected_page=page_id: self._offer_form_assistance(expected_page),
            )
        ok, message = apply_control(control, operation, value, overwrite=overwrite)
        if ok and intent == "select_option" and isinstance(control, QAbstractItemView):
            if type(root).__name__ == "DeviceSelectionDialog":
                continue_button = getattr(root, "btn_select", None)
                if continue_button is None or not continue_button.isEnabled():
                    return "Kaydi sectim ancak devam dugmesi kullanilamiyor."
                continue_button.click()
                return "Kaydi sectim ve teknisyen panelini aciyorum."
            if AssistantManager._voice_request_opens_selected_record(result.get("utterance")):
                if not table_row_open_handler_available(control):
                    return "Kaydi sectim ancak bu listede kaydi acan bir islem bagli degil."
                QTimer.singleShot(120, lambda view=control: activate_table_row(view))
                return "Kaydi sectim ve detayini aciyorum."
            return message
        if ok and before is not None:
            after = snapshot_control(control)
            if after is not None and after != before:
                self._remember_voice_change(control, before, after, root, page_id)
        if ok and operation in {"set", "select"}:
            message = self._voice_form_change_reply(control, value, root)
        return message if ok else message

    @staticmethod
    def _voice_request_opens_selected_record(utterance):
        from src.services.assistant_conversation import LocalAssistantConversation

        words = set(LocalAssistantConversation._normalize_text(utterance).split())
        return bool(
            words.intersection({"ac", "goster", "goruntule", "detay", "incele"})
            or any(word.startswith(("acil", "acalim", "acabilir", "aciyor", "acmak")) for word in words)
        )

    def _voice_form_change_reply(self, control, value, root):
        from PyQt6.QtWidgets import QLineEdit
        from src.services.assistant_ui_actions import label_for_control

        if not _assistant_voice_feature_enabled(self, "voice_feature_spoken_recap"):
            return "Alan guncellendi." + self._form_required_followup(root)

        label = (label_for_control(root, control) or "Alan").split(" / ", 1)[0].strip(" *")
        sensitive = isinstance(control, QLineEdit) and control.echoMode() != QLineEdit.EchoMode.Normal
        normalized_label = "".join(
            char for char in unicodedata.normalize("NFKD", label.casefold())
            if not unicodedata.combining(char)
        )
        sensitive = sensitive or any(term in normalized_label for term in ("parola", "sifre", "password", "pin", "kimlik", "tckn", "vergi", "iban", "hesap"))
        detail = "de\u011feri kaydettim" if sensitive else str(value or "")
        recap = label + ": " + detail + ". "
        return recap + self._form_required_followup(root)

    def _form_required_followup(self, root):
        if not _assistant_voice_feature_enabled(self, "voice_feature_required_guidance"):
            return ""
        if not self._pending_form_intake or self._pending_form_intake.get("status") != "active":
            return ""
        if time.monotonic() > self._pending_form_intake.get("expires_at", 0):
            self._pending_form_intake = None
            return "Form doldurma oturumunun s\u00fcresi doldu. Yeniden devam et diyebilirsiniz."
        if self._pending_form_intake.get("root") is not root:
            self._pending_form_intake = None
            return ""
        self._pending_form_intake["expires_at"] = time.monotonic() + 300.0
        missing = self._form_missing_required(root)
        if missing:
            label = str(missing[0].get("label") or "zorunlu alan").split(" / ", 1)[0].strip(" *")
            return "S\u0131radaki zorunlu alan: " + label + ". Bu alan\u0131n bilgisini s\u00f6yleyin."
        return (
            "Ba\u015fka alan eklemek ister misiniz? Kaydetmemi istedi\u011finizde "
            "ayr\u0131ca onay\u0131n\u0131z\u0131 alaca\u011f\u0131m."
        )

    def _offer_form_assistance(self, page_id, force=False):
        if not _assistant_voice_feature_enabled(self, "voice_feature_form_filling"):
            return False
        if page_id != getattr(self.main_window, "_current_page_index", None):
            return False
        root = QApplication.activeModalWidget()
        if root is None or not root.isVisible():
            return False
        existing = getattr(self, "_pending_form_intake", None)
        if existing and existing.get("root") is root and time.monotonic() <= existing.get("expires_at", 0):
            return False
        try:
            from src.services.assistant_ui_actions import describe_controls

            controls, _bindings = describe_controls(root, limit=1000)
            form_controls = [
                item for item in controls
                if item.get("type") in {"text", "multiline", "combo", "number", "date", "time", "datetime"}
            ]
            if not force and len(form_controls) < 2:
                return False
        except Exception as exc:
            self._log_soft_failure("assistant.form_assistance_probe", exc)
            return False
        self._pending_form_intake = {
            "root": root,
            "page_id": page_id,
            "expires_at": time.monotonic() + 90.0,
            "status": "awaiting_consent",
        }
        message = (
            "Form a\u00e7\u0131ld\u0131. Alanlar\u0131 birlikte doldural\u0131m m\u0131? "
            "Evet derseniz bilgileri s\u00f6yleyin. Kaydetme i\u015flemini ayr\u0131ca "
            "onay\u0131n\u0131z olmadan yapmayaca\u011f\u0131m."
        )
        self._conversation_history.append(("assistant", message))
        self._conversation_history = self._conversation_history[-12:]
        self.main_window.show_notification(message, "info")
        self._speak_async(message)
        return True

    @staticmethod
    def _is_form_assistance_phrase(utterance):
        normalized = "".join(
            char for char in unicodedata.normalize(
                "NFKD", str(utterance or "").casefold()
            )
            if not unicodedata.combining(char)
        ).replace("\u0131", "i")
        phrases = (
            "formu beraber doldur", "formu birlikte doldur",
            "beraber form doldur", "birlikte form doldur",
            "form doldurmama yardim", "formu doldurmama yardim",
            "musteri adini soyl", "musteri adini doldur",
        )
        return any(phrase in normalized for phrase in phrases)

    def _resolve_form_assistance_confirmation(self, confirmed):
        pending = self._pending_form_intake
        self._pending_form_intake = None
        if not pending:
            return False
        if not _assistant_voice_feature_enabled(self, "voice_feature_form_filling"):
            message = "Sesle form doldurma ayarlardan kapali; oturumu baslatmadim."
            self.main_window.show_notification(message, "warning")
            self._speak_async(message)
            return False
        if time.monotonic() > pending.get("expires_at", 0):
            self._set_form_voice_followup(False)
            message = "Form doldurma iste\u011fi zaman a\u015f\u0131m\u0131na u\u011frad\u0131. Yeniden yard\u0131m isteyebilirsiniz."
        elif pending.get("page_id") != getattr(self.main_window, "_current_page_index", None):
            self._set_form_voice_followup(False)
            message = "Form ekran\u0131 de\u011fi\u015fti; doldurma oturumunu kapatt\u0131m."
        elif pending.get("root") is not QApplication.activeModalWidget():
            self._set_form_voice_followup(False)
            message = "Form kapand\u0131 veya de\u011fi\u015fti; doldurma oturumunu kapatt\u0131m."
        elif confirmed:
            pending["status"] = "active"
            pending["expires_at"] = time.monotonic() + 300.0
            self._pending_form_intake = pending
            self._set_form_voice_followup(True)
            message = (
                "Tamam, formu birlikte doldural\u0131m. Bilgileri alan adlar\u0131yla "
                "s\u00f6yleyin; \u00f6rnek: m\u00fc\u015fteri ad\u0131 Burak \u015eahin, "
                "telefon 555... Birden \u00e7ok alan\u0131 tek seferde s\u00f6yleyebilirsiniz. "
                "Kaydetme ayr\u0131ca onay ister. "
                + self._form_required_followup(pending["root"])
            )
            self._conversation_history.append(("user", "Evet, formu dolduralim."))
        else:
            self._set_form_voice_followup(False)
            message = "Peki, formu a\u00e7\u0131k b\u0131rakt\u0131m. \u0130stedi\u011finiz zaman doldurmam\u0131 s\u00f6yleyin."
        self._conversation_history.append(("assistant", message))
        self._conversation_history = self._conversation_history[-12:]
        self.main_window.show_notification(message, "info")
        self._speak_async(message)
        return bool(confirmed)

    def _set_form_voice_followup(self, enabled):
        thread = getattr(self, "voice_assistant_thread", None)
        if thread is None:
            return
        thread.followup_mode = bool(enabled)
        thread.followup_expires_at = time.time() + 300.0 if enabled else 0.0

    def _remember_voice_change(self, control, before, after, root, page_id):
        self._last_voice_change = {
            "control": control, "before": before, "after": after,
            "root": root, "page_id": page_id,
            "expires_at": time.monotonic() + 60.0,
        }

    def _undo_last_voice_change(self):
        from src.services.assistant_ui_actions import restore_control, snapshot_control

        change = self._last_voice_change
        self._last_voice_change = None
        if not change:
            return False, "Geri alinabilecek son bir sesli alan degisikligi yok."
        if time.monotonic() > change.get("expires_at", 0):
            return False, "Geri alma suresi dolmus."
        page_id = change.get("page_id")
        if page_id != getattr(self.main_window, "_current_page_index", None):
            return False, "Ekran degistigi icin degisikligi geri alamadim."
        root = self._assistant_action_root(page_id)
        if root is not change.get("root"):
            return False, "Form degistigi icin degisikligi geri alamadim."
        if change.get("batch"):
            batch = change["batch"]
            if any(snapshot_control(item["control"]) != item["after"] for item in batch):
                return False, "Alanlardan biri sonradan degistigi icin mevcut degerleri korudum."
            for item in reversed(batch):
                ok, message = restore_control(item["control"], item["before"])
                if not ok:
                    return False, message
            return True, "Son sesli form guncellemesini geri aldim."
        control = change.get("control")
        if snapshot_control(control) != change.get("after"):
            return False, "Alan sonradan degistigi icin mevcut degeri korudum."
        return restore_control(control, change.get("before"))

    def _run_voice_control_batch(self, result, worker):
        from PyQt6.QtGui import QValidator
        from PyQt6.QtWidgets import QComboBox, QLineEdit, QPlainTextEdit, QTextEdit
        from src.services.assistant_ui_actions import (
            action_needs_confirmation,
            apply_control,
            label_for_control,
            snapshot_control,
        )
        normalize_option = lambda value: "".join(
            char for char in unicodedata.normalize("NFKD", str(value or "").casefold())
            if not unicodedata.combining(char)
        ).replace("\u0131", "i")

        page_id = getattr(worker, "page_id", None) if worker else None
        root = getattr(worker, "action_root", None) if worker else None
        if page_id != getattr(self.main_window, "_current_page_index", None):
            return "Ekran komut sirasinda degisti; alanlari doldurmadim."
        if root is not self._assistant_action_root(page_id):
            return "Acik form degisti; alanlari doldurmadim."
        bindings = getattr(worker, "control_bindings", {})
        updates = result.get("fields")
        if not isinstance(updates, list) or not 2 <= len(updates) <= 10:
            return "Iki ile on arasi alan icin deger algilayamadim."

        batch = []
        for item in updates:
            control = bindings.get(str(item.get("control_id") or ""))
            if not isinstance(control, (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox)):
                return "Form alanlarindan biri artik kullanilabilir degil."
            if isinstance(control, QComboBox) and not control.isEditable():
                return "Secim listesi serbest metin kabul etmiyor."
            if not control.isVisible() or not control.isEnabled():
                return "Form degisti; alanlarin hicbirini doldurmadim."
            value = str(item.get("value") or "")
            if not value.strip():
                return "Bos bir deger icin alanlari degistirmedim."
            overwrite = bool(item.get("overwrite"))
            if overwrite and not _assistant_voice_feature_enabled(self, "voice_feature_field_correction"):
                return "Alan duzeltme ayarlardan kapali; mevcut degerleri korudum."
            current = control.currentText() if isinstance(control, QComboBox) else (
                control.text() if isinstance(control, QLineEdit) else control.toPlainText()
            )
            if current.strip() and not overwrite and not isinstance(control, QComboBox):
                return "Dolu alan var. Degistirmemi istiyorsaniz acikca soyleyin."
            operation = str(item.get("operation") or "set_field")
            if isinstance(control, QComboBox):
                if operation != "select_option" or not any(
                    normalize_option(control.itemText(index).strip()) == normalize_option(value.strip())
                    for index in range(control.count())
                ):
                    return "Secim listesinde istenen kayit bulunamadi; hicbir alani degistirmedim."
            elif operation != "set_field":
                return "Form alanlarindan biri icin islem turu gecersiz."
            elif isinstance(control, QLineEdit):
                if len(value) > control.maxLength():
                    return "Bir alanin karakter siniri asiliyor; hicbir alani degistirmedim."
                validator = control.validator()
                if validator is not None:
                    state, _candidate, _position = validator.validate(value, len(value))
                    if state != QValidator.State.Acceptable:
                        return "Bir alanin giris dogrulamasi uyusmuyor; hicbir alani degistirmedim."
            batch.append({
                "control": control,
                "value": value,
                "overwrite": overwrite,
                "operation": operation,
                "before": snapshot_control(control),
            })

        requires_confirmation = any(
            item["overwrite"] or action_needs_confirmation(item["control"], root)
            for item in batch
        )
        if requires_confirmation:
            if not _assistant_voice_feature_enabled(
                self, "voice_feature_critical_confirmation"
            ):
                return "Kritik islemlerde sesli onay kapali; guvenlik icin hicbir alani degistirmedim."
            if self._dictation_mode:
                self._dictation_mode = False
                if self.voice_assistant_thread is not None:
                    self.voice_assistant_thread.dictation_mode = False
            self._pending_voice_control = {
                "batch": batch,
                "root": root,
                "page_id": page_id,
                "expires_at": time.monotonic() + 25.0,
            }
            summaries = []
            for item in batch:
                control = item["control"]
                label = label_for_control(root, control) or "metin alani"
                if isinstance(control, QLineEdit) and control.echoMode() != QLineEdit.EchoMode.Normal:
                    summaries.append(label + ": parola alani guncellenecek")
                else:
                    summaries.append(label + ": " + item["value"][:80])
            try:
                page_label = self.main_window.get_page_name_by_index(page_id)
            except Exception:
                page_label = "aktif ekran"
            return (
                page_label + " ekranindaki dolu veya hassas alanlar degisecek: " + ". ".join(summaries)
                + ". Devam etmek icin evet, vazgecmek icin hayir deyin."
            )

        applied = []
        for item in batch:
            ok, _message = apply_control(item["control"], "select" if item["operation"] == "select_option" else "set", item["value"])
            if not ok:
                from src.services.assistant_ui_actions import restore_control

                for applied_item in reversed(applied):
                    if applied_item.get("before") is not None:
                        restore_control(applied_item["control"], applied_item["before"])
                return "Alanlardan biri doldurulamad\u0131. Formu kontrol et deyin."
            applied.append(item)
        self._remember_voice_batch_change(batch, root, page_id)
        recap = self._voice_form_batch_recap(batch, root)
        return str(len(batch)) + " alan doldurdum. " + recap + self._form_required_followup(root)

    def _remember_voice_batch_change(self, batch, root, page_id):
        from src.services.assistant_ui_actions import snapshot_control

        changes = []
        for item in batch:
            before = item.get("before")
            after = snapshot_control(item["control"])
            if before is not None and after is not None and before != after:
                changes.append({"control": item["control"], "before": before, "after": after})
        if changes:
            self._last_voice_change = {
                "batch": changes,
                "root": root,
                "page_id": page_id,
                "expires_at": time.monotonic() + 60.0,
            }

    def _voice_form_batch_recap(self, batch, root):
        from PyQt6.QtWidgets import QComboBox, QLineEdit
        from src.services.assistant_ui_actions import label_for_control

        if not _assistant_voice_feature_enabled(self, "voice_feature_spoken_recap"):
            return ""

        summaries = []
        for item in batch:
            control = item["control"]
            label = (label_for_control(root, control) or "Alan").split(" / ", 1)[0].strip(" *")
            sensitive = isinstance(control, QLineEdit) and control.echoMode() != QLineEdit.EchoMode.Normal
            normalized = "".join(
                char for char in unicodedata.normalize("NFKD", label.casefold())
                if not unicodedata.combining(char)
            )
            sensitive = sensitive or any(term in normalized for term in ("parola", "sifre", "password", "pin", "kimlik", "tckn", "vergi", "iban", "hesap"))
            value = "de\u011feri kaydettim" if sensitive else (
                "se\u00e7imi s\u0131f\u0131rlad\u0131m" if item.get("operation") == "clear" and isinstance(control, QComboBox)
                else str(item.get("value") or "")
            )
            summaries.append(label + ": " + value)
        return "Duydu\u011fum bilgiler: " + "; ".join(summaries) + ". "

    def _confirm_voice_control(self, confirmed):
        from src.services.assistant_ui_actions import apply_control, snapshot_control

        pending = self._pending_voice_control
        self._pending_voice_control = None
        if not pending:
            self._speak_async("Onay bekleyen bir sesli ekran i\u015flemi bulunmuyor.")
            return
        if not _assistant_voice_feature_enabled(self, "voice_feature_critical_confirmation"):
            self._speak_async("Kritik islemlerde sesli onay kapali; guvenlik icin islemi uygulamadim.")
            return
        if time.monotonic() > pending.get("expires_at", 0):
            self._speak_async("Onay s\u00fcresi doldu. G\u00fcvenlik i\u00e7in i\u015flemi uygulamad\u0131m.")
            return
        if not confirmed:
            self._speak_async("\u0130\u015flemi iptal ettim.")
            return
        if pending.get("page_id") != getattr(self.main_window, "_current_page_index", None):
            self._speak_async("Ekran de\u011fi\u015fti; g\u00fcvenlik i\u00e7in i\u015flemi uygulamad\u0131m.")
            return
        pending_root = pending.get("root")
        current_root = self._assistant_action_root(pending.get("page_id"))
        if pending_root is not None and pending_root is not current_root:
            self._speak_async("Form de\u011fi\u015fti; g\u00fcvenlik i\u00e7in i\u015flemi uygulamad\u0131m.")
            return
        if pending.get("batch"):
            batch = pending["batch"]
            if any(not item["control"].isVisible() or not item["control"].isEnabled() for item in batch):
                self._speak_async("Form degisti; guvenlik icin alanlari guncellemedim.")
                return
            for item in batch:
                operation = {
                    "select_option": "select",
                    "clear": "clear",
                }.get(item.get("operation"), "set")
                ok, _message = apply_control(
                    item["control"], operation, item["value"], overwrite=True
                )
                if not ok:
                    self._speak_async("Alanlardan biri guncellenemedi. Formu kontrol edin.")
                    return
            self._remember_voice_batch_change(
                batch, pending_root, pending.get("page_id")
            )
            if all(item.get("operation") == "clear" for item in batch):
                message = "Formdaki alanlar\u0131 ba\u015flang\u0131\u00e7 de\u011ferlerine d\u00f6nd\u00fcrd\u00fcm. "
            else:
                message = (
                    str(len(batch)) + " alan\u0131 g\u00fcncelledim. "
                    + self._voice_form_batch_recap(batch, pending_root)
                )
            message += self._form_required_followup(pending_root)
            self.main_window.show_notification(message, "success")
            self._speak_async(message)
            return
        control = pending.get("control")
        if pending.get("operation") == "click":
            QTimer.singleShot(
                350,
                lambda expected_page=pending.get("page_id"):
                self._offer_form_assistance(expected_page),
            )
        before = snapshot_control(control)
        ok, message = apply_control(
            control,
            pending.get("operation"),
            pending.get("value"),
            overwrite=pending.get("overwrite", False),
        )
        after = snapshot_control(control) if ok else None
        if before is not None and after is not None and before != after:
            self._remember_voice_change(
                control, before, after, pending_root, pending.get("page_id")
            )
        if ok and pending.get("operation") in {"set", "select"}:
            message = self._voice_form_change_reply(
                control, pending.get("value"), pending_root
            )
        notification_kind = "info" if ok and pending.get("operation") == "click" else (
            "success" if ok else "warning"
        )
        self.main_window.show_notification(message, notification_kind)
        self._speak_async(message)

    def _open_new_service_dialog(self):
        try:
            dashboard = self.main_window.get_page(40)
            if dashboard and hasattr(dashboard, "open_new_service_dialog"):
                QTimer.singleShot(
                    350,
                    lambda page=getattr(self.main_window, "_current_page_index", None):
                    self._offer_form_assistance(page, force=True),
                )
                dashboard.open_new_service_dialog()
                msg = "Yeni servis formunu aciyorum."
            else:
                msg = "Yeni servis formu bu ekranda kullanilamiyor."
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
        except Exception as exc:
            self._log_soft_failure("assistant.new_service_dialog", exc)

    def _handle_confirmation(self, confirmed):
        action = getattr(self.main_window, "pending_action", None) or self.pending_action
        self.main_window.pending_action = None
        self.pending_action = None
        prefix = self._assistant_prefix()

        if not action:
            msg = f"{prefix}onay bekleyen bir islem bulunmuyor."
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
            return
        
        if not confirmed:
            msg = f"{prefix} İşlemi iptal ettim."
            self._speak_async(msg)
            return

        if action and action.get("type") == "apply_zam":
            pct = action.get("percentage", 10)
            category = action.get("category")
            if hasattr(self.db, "apply_stock_price_increase"):
                if category:
                    ok = bool(self.db.apply_stock_price_increase(pct, category=category))
                else:
                    ok = bool(self.db.apply_stock_price_increase(pct))
            else:
                ok = False
            scope = f"{category} kategorisindeki" if category else "tum aktif"
            msg = f"{prefix}{scope} stok satis fiyatlarina yuzde {pct} zam uyguladim." if ok else f"{prefix} zam uygulanamadi."
            self.main_window.show_notification(msg, "success" if ok else "error")
            self._speak_async(msg)
            self.main_window.on_menu_click(999)

    def _resolve_voice_stock_scope(self, utterance):
        normalize = lambda value: "".join(
            char for char in unicodedata.normalize("NFKD", str(value or "").casefold())
            if not unicodedata.combining(char)
        ).replace("\u0131", "i")
        text = normalize(utterance)
        category_requested = any(
            term in text for term in ("kategori", "grup", "marka", "yalniz", "sadece", "secili")
        )
        cursor = getattr(self.db, "cursor", None)
        if cursor is None:
            if category_requested:
                return None, None, None, "Kategori kapsamini dogrulayamiyorum; stok fiyatlarini degistirmedim."
            return "all_active_stock", None, None, ""
        try:
            cursor.execute(
                "SELECT DISTINCT category FROM parts "
                "WHERE COALESCE(is_deleted, 0)=0 AND category IS NOT NULL "
                "AND TRIM(category)<>''"
            )
            categories = [str(row[0]).strip() for row in (cursor.fetchall() or []) if row and row[0]]
            matches = [
                name for name in categories
                if len(normalize(name)) >= 3 and normalize(name) in text
            ]
            if matches:
                category = max(matches, key=len)
                cursor.execute(
                    "SELECT COUNT(*) FROM parts WHERE COALESCE(is_deleted, 0)=0 AND category=?",
                    (category,),
                )
                row = cursor.fetchone()
                return "category", category, int(row[0] or 0) if row else 0, ""
            if category_requested:
                return None, None, None, "Istenen kategori adini stoklarda bulamadim; tum stoklara zam uygulamadim."
            cursor.execute("SELECT COUNT(*) FROM parts WHERE COALESCE(is_deleted, 0)=0")
            row = cursor.fetchone()
            return "all_active_stock", None, int(row[0] or 0) if row else 0, ""
        except Exception as exc:
            self._log_soft_failure("assistant.stock_price_scope", exc)
            if category_requested:
                return None, None, None, "Kategori kapsamini dogrulayamiyorum; stok fiyatlarini degistirmedim."
            return "all_active_stock", None, None, ""

    def arz_et_gunluk_plan(self):
        prefix = self._assistant_prefix()
        try:
            ad = self.get_asistan_name()
            now = datetime.now()
            saat = now.hour

            # Güne göre selamlama
            if saat < 12:
                selamlama = "Günaydın"
            elif saat < 18:
                selamlama = "İyi günler"
            else:
                selamlama = "İyi akşamlar"

            parts = []

            # Randevu bilgisi — sayı + detay
            try:
                appointments = self.db.get_daily_appointments()
                randevu_count = len(appointments) if appointments else 0
            except Exception:
                appointments = []
                randevu_count = 0

            if randevu_count == 0:
                parts.append("Bugün için kayıtlı randevunuz bulunmuyor")
            elif randevu_count == 1:
                parts.append("Bugün için bir randevunuz var")
            else:
                parts.append(f"Bugün için toplam {self._number_to_tr_words(randevu_count)} randevunuz var")

            # Randevu detayları — ilk 3 randevuyu seslendir
            appt_details = []
            for appt in (appointments or [])[:3]:
                try:
                    appt_dict = dict(appt) if hasattr(appt, "keys") else {}
                    # Saat/zaman
                    appt_time = (
                        appt_dict.get("appointment_time")
                        or appt_dict.get("time")
                        or appt_dict.get("start_time")
                        or ""
                    )
                    if appt_time and len(str(appt_time)) >= 5:
                        appt_time = str(appt_time)[:5]  # HH:MM
                    # Müşteri
                    customer = (
                        appt_dict.get("customer_name")
                        or appt_dict.get("title")
                        or appt_dict.get("name")
                        or "Müşteri"
                    )
                    # Açıklama
                    description = (
                        appt_dict.get("description")
                        or appt_dict.get("notes")
                        or appt_dict.get("service_type")
                        or ""
                    )
                    detail = f"{appt_time + ' saatinde ' if appt_time else ''}{customer}"
                    if description:
                        detail += f" için {description[:40]}"
                    appt_details.append(detail)
                except Exception:
                    pass

            if appt_details:
                parts.append("Detaylar: " + "; ".join(appt_details))

            # Kritik stok bilgisi
            try:
                critical = self.db.get_critical_stock_items() if hasattr(self.db, "get_critical_stock_items") else []
                if not critical:
                    # Alternatif DB metodu dene
                    try:
                        critical = [r for r in (self.db.get_all_parts() or [])
                                    if int(r.get("stock", 0) or 0) <= int(r.get("min_stock", 5) or 5)]
                    except Exception:
                        critical = []
                if critical:
                    parts.append(f"{self._number_to_tr_words(len(critical))} ürün kritik stok seviyesinde")
            except Exception:
                pass

            birlesik = " ve ".join(parts) if parts else ""
            prefix_str = f"{prefix} " if prefix else ""
            cevap = f"Hoş geldiniz! {selamlama} {prefix_str}Ben {ad}. {birlesik}."

            # show_assistant_alert hem toast gösterir hem de sesi çalar — _speak_async ayrıca çağırma
            self.show_assistant_alert(f"{selamlama}!", cevap)
        except Exception as exc:
            self._log_soft_failure("arz_et_gunluk_plan", exc)

    def startup_greeting(self):
        """Program açılışında otomatik olarak çalışan karşılama rutini."""
        try:
            if not self._assistant_voice_enabled():
                return
            # 5 dakika içinde tekrar açıldıysa selamlama tekrarlanmaz
            if getattr(self, "_startup_greeting_done", False):
                return
            self.arz_et_gunluk_plan()
            self._startup_greeting_done = True
        except Exception as exc:
            self._startup_greeting_done = False
            self._log_soft_failure("startup_greeting", exc)
