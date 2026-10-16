# -*- coding: utf-8 -*-

import logging
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class AssistantMonitoringWorker(QThread):
    result_ready = pyqtSignal(dict)

    def __init__(self, db_name, last_report_date, now, parent=None):
        super().__init__(parent)
        self.db_name = db_name or "ayecpro.db"
        self.last_report_date = last_report_date
        self.now = now

    def run(self):
        db = None
        result = {
            "urgent_report": None,
            "daily_report_sent": False,
            "evening_report_sent": False,
            "error": None,
        }
        try:
            from src.database import Database
            from src.utils.ai_service import AIService

            db = Database(self.db_name, init_mode="connection_only")
            ai_service = AIService(db)
            if not ai_service.is_configured:
                self.result_ready.emit(result)
                return

            report = ai_service.get_urgent_report()
            if report:
                ai_service.send_whatsapp(f"ACIL DURUM UYARISI: {report}")
                result["urgent_report"] = report

            today_str = self.now.strftime("%Y-%m-%d")
            if self.now.hour >= 9 and self.last_report_date != today_str:
                daily_report = ai_service.generate_specialized_report("morning")
                ai_service.send_whatsapp(daily_report)
                result["daily_report_sent"] = True

            if self.now.hour >= 18 and self.last_report_date != today_str + "_evening":
                evening_report = ai_service.generate_specialized_report("evening")
                ai_service.send_whatsapp(evening_report)
                result["evening_report_sent"] = True
        except Exception as e:
            logger.warning("Assistant monitoring worker failed: %s", e)
            result["error"] = str(e)
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass

        self.result_ready.emit(result)


class PaymentReminderWorker(QThread):
    result_ready = pyqtSignal(dict)

    def __init__(self, db_name, run_key, parent=None):
        super().__init__(parent)
        self.db_name = db_name or "ayecpro.db"
        self.run_key = run_key

    def run(self):
        db = None
        sent = 0
        manual = 0
        try:
            from src.database import Database
            from src.services.whatsapp_service import WhatsAppDeliveryError, WhatsAppService

            db = Database(self.db_name, init_mode="connection_only")
            if db.get_setting("whatsapp_payment_reminder_enabled", "0") != "1":
                return
            if db.get_internal_setting("whatsapp_payment_last_run", "") == self.run_key:
                return
            service = WhatsAppService(db)
            template_name = str(db.get_setting("whatsapp_cloud_template", "") or "").strip()
            template = db.get_setting(
                "whatsapp_payment_template",
                "Merhaba {musteri_adi}, {firma_adi} hesabinizda {borc_tutari} TRY borc bulunuyor.",
            )
            minimum = float(db.get_setting("whatsapp_payment_min_debt_try", "0") or 0)
            company = str(db.get_setting("company_name", "AYEC Pro") or "AYEC Pro")
            for customer in db.get_customers() or []:
                phone = customer[2] if len(customer) > 2 else ""
                if not phone:
                    continue
                balance = float(db.get_customer_balance(customer[0]) or 0)
                debt = max(0.0, -balance)
                if debt < minimum:
                    continue
                name = str(customer[1] or "Musteri")
                values = {
                    "musteri_adi": name,
                    "firma_adi": company,
                    "borc_tutari": f"{debt:,.2f}",
                    "referans_no": str(customer[0]),
                }
                message = service.render_template(template, values)
                ordered_values = [
                    value
                    for key, value in (
                        ("musteri_adi", name),
                        ("firma_adi", company),
                        ("borc_tutari", f"{debt:,.2f}"),
                        ("referans_no", str(customer[0])),
                    )
                    if "{" + key + "}" in template or "{{" + key + "}}" in template
                ]
                try:
                    result = service.send(phone, message, template_name, ordered_values)
                    sent += 1
                    if result.get("manual_required"):
                        manual += 1
                except WhatsAppDeliveryError as error:
                    logger.warning("Payment reminder skipped for customer %s: %s", customer[0], error)
                except Exception as error:
                    logger.warning("Payment reminder failed for customer %s: %s", customer[0], error)
            db.set_internal_setting("whatsapp_payment_last_run", self.run_key)
            self.result_ready.emit({"sent": sent, "manual": manual, "error": None})
        except Exception as error:
            logger.warning("Payment reminder worker failed: %s", error)
            self.result_ready.emit({"sent": sent, "manual": manual, "error": str(error)})
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass
