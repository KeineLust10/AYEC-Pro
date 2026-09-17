# -*- coding: utf-8 -*-

from PyQt6.QtCore import QThread, pyqtSignal

class AIWorker(QThread):
    finished = pyqtSignal(str) # İşlem bitince metni gönderir
    error = pyqtSignal(str)    # Hata olursa hatayı gönderir

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func   # Çalıştırılacak fonksiyon (Ses kaydı veya AI)
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            # Result None ise boş string gönder
            if result is None:
                result = ""
            self.finished.emit(str(result))
        except Exception as e:
            self.error.emit(str(e))
