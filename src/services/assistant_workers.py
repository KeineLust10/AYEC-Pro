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
