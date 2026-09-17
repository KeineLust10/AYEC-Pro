# -*- coding: utf-8 -*-

import logging
import traceback
import re
import urllib.parse
import webbrowser
from datetime import datetime, timedelta
from PyQt6.QtCore import QObject, QTimer, QVariantAnimation, QEasingCurve, pyqtSignal, QThread
from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect
from PyQt6.QtGui import QIcon
from src.services.assistant_workers import AssistantMonitoringWorker
from src.ui.widgets.jarvis_toast import AssistantToast
from src.utils.system_config import SystemConfig
from src.services.whatsapp_service import WhatsAppService, WhatsAppDeliveryError

logger = logging.getLogger(__name__)

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
        self.voice_assistant_thread = None

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
                self.db.get_setting("assistant_tts_engine", "edge"),
            )
        except Exception:
            return "edge"

    def _assistant_edge_voice(self):
        try:
            return self.db.get_setting(
                "asistan_edge_voice",
                self.db.get_setting("assistant_edge_voice", "tr-TR-AhmetNeural"),
            )
        except Exception:
            return "tr-TR-AhmetNeural"

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
            return f"{user_alias}, " if hitap_aktif else ""
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
            return True

    def start_voice_assistant(self, notify=False):
        """Starts the continuous speech command listener when enabled."""
        if not self.is_voice_assistant_enabled():
            return False
        if self.voice_assistant_thread and self.voice_assistant_thread.isRunning():
            return True
        self.voice_assistant_thread = None

        try:
            from src.utils.asistan_motoru import BulutAsistan

            self.voice_assistant_thread = BulutAsistan()
            self.voice_assistant_thread.tetik_sinyali.connect(self.aksiyon_merkezi)
            self.voice_assistant_thread.hata_sinyali.connect(self._handle_voice_assistant_error)
            self.voice_assistant_thread.finished.connect(self._on_voice_assistant_finished)
            self.voice_assistant_thread.start()
            if notify:
                self.main_window.show_notification("Sesli asistan dinleme modu başlatıldı.", "success")
            logger.info("Voice assistant listener started")
            return True
        except Exception as exc:
            logger.error("Voice assistant start error: %s", exc, exc_info=True)
            if notify:
                self.main_window.show_notification(f"Sesli asistan başlatılamadı: {exc}", "error")
            return False

    def stop_voice_assistant(self, notify=False):
        thread = self.voice_assistant_thread
        if not thread:
            return
        try:
            if hasattr(thread, "stop"):
                thread.stop()
            elif thread.isRunning():
                thread.quit()
                thread.wait(1500)
            if self.voice_assistant_thread is thread:
                self.voice_assistant_thread = None
            if notify:
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

    def _on_voice_assistant_finished(self):
        logger.info("Voice assistant listener stopped")
        self.voice_assistant_thread = None

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
        major, minor = ("lira", "kuruş")
        if code == "USD": major, minor = ("dolar", "sent")
        elif code == "EUR": major, minor = ("euro", "sent")
        
        try:
            val = float(amount)
        except Exception:
            val = 0.0
            
        sign = "eksi " if val < 0 else ""
        val = round(abs(val), 2)
        whole = int(val)
        fraction = int(round((val - whole) * 100))
        
        if fraction == 100:
            whole += 1
            fraction = 0
            
        words = f"{self._number_to_tr_words(whole)} {major}"
        if fraction > 0:
            words = f"{words} {self._number_to_tr_words(fraction)} {minor}"
        return f"{sign}{words}"

    def _speak_async(self, text):
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
        """Send the configured weekly debt reminder once per scheduled minute."""
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
            service = WhatsAppService(self.db)
            template_name = str(self.db.get_setting("whatsapp_cloud_template", "") or "").strip()
            template = self.db.get_setting(
                "whatsapp_payment_template",
                "Merhaba {musteri_adi}, {firma_adi} hesabinizda {borc_tutari} TRY borc bulunuyor.",
            )
            minimum = float(self.db.get_setting("whatsapp_payment_min_debt_try", "0") or 0)
            company = str(self.db.get_setting("company_name", "AYEC Pro") or "AYEC Pro")
            sent = 0
            manual = 0
            for customer in self.db.get_customers() or []:
                phone = customer[2] if len(customer) > 2 else ""
                if not phone:
                    continue
                balance = float(self.db.get_customer_balance(customer[0]) or 0)
                debt = max(0.0, -balance)
                if debt < minimum:
                    continue
                name = str(customer[1] or "Musteri")
                values = {
                    "musteri_adi": name,
                    "borc_tutari": f"{debt:,.2f}",
                    "referans_no": str(customer[0]),
                }
                message = service.render_template(template, values)
                try:
                    ordered_values = []
                    for key, value in (("musteri_adi", name), ("firma_adi", company), ("borc_tutari", f"{debt:,.2f}"), ("referans_no", str(customer[0]))):
                        if "{" + key + "}" in template or "{{" + key + "}}" in template:
                            ordered_values.append(value)
                    result = service.send(phone, message, template_name, ordered_values)
                    sent += 1
                    if result.get("manual_required"):
                        manual += 1
                except WhatsAppDeliveryError as error:
                    logger.warning("Payment reminder skipped for customer %s: %s", customer[0], error)
            self.db.set_internal_setting("whatsapp_payment_last_run", run_key)
            if manual:
                self.show_assistant_alert("WhatsApp hatirlatmasi", f"{manual} mesaj kullanici onayi icin hazirlandi.")
            elif sent:
                self.show_assistant_alert("WhatsApp hatirlatmasi", f"{sent} borc odeme hatirlatmasi gonderildi.")
        except Exception as error:
            logger.warning("Payment reminder process error: %s", error)

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

        elif aksiyon == "servis_ac":
            msg = f"{prefix} servis ekranini aciyorum."
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)
            self.main_window.on_menu_click(140)

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
            pct = 10
            match = re.search(r"%(\d+)", str(parametre or ""))
            if match:
                pct = int(match.group(1))
            action = {"type": "apply_zam", "percentage": pct}
            self.pending_action = action
            self.main_window.pending_action = action
            msg = f"{prefix} stok satis fiyatlarina yuzde {pct} zam uygulayayim mi?"
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
            msg = (
                f"{prefix} servis, musteri, stok, finans, randevu ve personel "
                "ekranlarini acabilirim. Ozetleri okuyabilir, stok arayabilir, "
                "fiyat artisini onayla uygulayabilir ve senkronizasyon baslatabilirim."
            )
            self.main_window.show_notification(msg, "info")
            self._speak_async(msg)

        elif aksiyon == "check_appointments":
            msg = f"{prefix} Randevularınızı kontrol ediyorum."
            self._speak_async(msg)
            self.main_window.on_menu_click(30)

        elif aksiyon == "greeting_routine":
            self.arz_et_gunluk_plan()

        elif aksiyon == "confirm_yes":
            if hasattr(self.main_window, "pending_action") and self.main_window.pending_action:
                self._handle_confirmation(True)
        elif aksiyon == "confirm_no":
            self._handle_confirmation(False)

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
            ok = bool(self.db.apply_stock_price_increase(pct)) if hasattr(self.db, "apply_stock_price_increase") else False
            msg = f"{prefix} stok satis fiyatlarina yuzde {pct} zam uyguladim." if ok else f"{prefix} zam uygulanamadi."
            self.main_window.show_notification(msg, "success" if ok else "error")
            self._speak_async(msg)
            self.main_window.on_menu_click(999)

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
