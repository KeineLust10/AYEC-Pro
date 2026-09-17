# -*- coding: utf-8 -*-

from PyQt6.QtCore import QThread, pyqtSignal
from src.utils.audit_logger import get_audit_logger
from src.utils.logger import logger

class AssistantAnalysisWorker(QThread):
    finished = pyqtSignal(str)
    
    def __init__(self, ai_service, db, parent=None):
        super().__init__(parent)
        self.ai_service = ai_service
        self.db = db
        self.audit_logger = get_audit_logger(db)
        
    def run(self):
        try:
            if self.isInterruptionRequested():
                return
            # Ask a specific question about the dashboard content
            prompt = "Son işlemlere bakarak en acil müdahale gerektiren durumu (cihaz ve müşteri adı ile) 10 kelimede özetle. Eğer her şey yolundaysa 'Sistem stabil efendim' de."
            result = self.ai_service.ask_assistant(prompt)
            if self.isInterruptionRequested():
                return
            if result['success']:
                self.finished.emit(result['answer'])
            else:
                self.finished.emit("")
        except Exception as e:
            logger.error(f"AssistantAnalysisWorker run error: {e}")
            self.finished.emit("")


