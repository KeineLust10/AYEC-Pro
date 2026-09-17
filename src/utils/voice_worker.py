# -*- coding: utf-8 -*-

from PyQt6.QtCore import QThread, pyqtSignal

class VoiceWorker(QThread):
    # Jarvis sesini metne çevirince bu sinyal tetiklenir
    text_received = pyqtSignal(str)
    # Hata olursa bu sinyal tetiklenir
    error_occurred = pyqtSignal(str)

    def __init__(self, ai_service, parent=None):
        super().__init__(parent)
        self.ai_service = ai_service

    def run(self):
        try:
            # Ses kayıt ve işleme işlemini arka planda yap
            result = self.ai_service.record_and_process_voice() 
            if result:
                self.text_received.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
