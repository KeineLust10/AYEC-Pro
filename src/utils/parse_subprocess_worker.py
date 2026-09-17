# -*- coding: utf-8 -*-
"""
parse_subprocess_worker.py
--------------------------
StockImportParser.parse_file() işlemini tamamen ayrı bir OS process'inde
çalıştırır.  QThread GIL'i tam serbest bırakmadığından PyTorch/EasyOCR model
yüklemesi sırasında Qt UI donuyordu.  Bu modül:

  • multiprocessing.Process ile bağımsız bir process başlatır
  • Sonucu multiprocessing.Queue üzerinden alır
  • QThread içinden Queue'yu poll ederek Qt sinyallerini güvenli tetikler
  • Windows'ta "spawn" start methodu otomatik seçilir (fork yok)
"""

import multiprocessing
import multiprocessing.queues
import queue
import traceback
from typing import Any, Optional

from PyQt6.QtCore import QThread, pyqtSignal, QTimer


# ─────────────────────────────────────────────────────────────────────────────
# Process entry-point  (top-level — pickle edilebilir olması için)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_worker_process(path: str, result_q: "multiprocessing.Queue") -> None:
    """Alt process giriş noktası: parse yapıp sonucu Queue'ya koyar."""
    try:
        import sys
        import os
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        venv_path = os.path.join(base_dir, ".venv_active", "Lib", "site-packages")
        if os.path.exists(venv_path) and venv_path not in sys.path:
            sys.path.insert(0, venv_path)
            
        from src.utils.stock_import_parser import StockImportParser
        result = StockImportParser.parse_file(path)
        result_q.put({"ok": True, "data": result})
    except Exception as exc:
        result_q.put({"ok": False, "error": str(exc), "tb": traceback.format_exc()})


def _service_parse_worker_process(
    path: str, is_auto: bool, result_q: "multiprocessing.Queue"
) -> None:
    """Hizmet (ServiceParseWorker) için ayrı process giriş noktası."""
    try:
        import sys
        import os
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        venv_path = os.path.join(base_dir, ".venv_active", "Lib", "site-packages")
        if os.path.exists(venv_path) and venv_path not in sys.path:
            sys.path.insert(0, venv_path)
            
        from src.utils.stock_import_parser import StockImportParser
        result = StockImportParser.parse_file(path)
        result_q.put({"ok": True, "data": result, "is_auto": is_auto})
    except Exception as exc:
        result_q.put({"ok": False, "error": str(exc), "tb": traceback.format_exc()})


# ─────────────────────────────────────────────────────────────────────────────
# Qt tarafı — QThread içinden Queue'yu izleyen wrapper
# ─────────────────────────────────────────────────────────────────────────────

class ParseProcessWorker(QThread):
    """
    StockImportParser.parse_file() işlemini gerçek bir alt-process'te çalıştırır.
    ParseWorker (QThread) ile aynı sinyalleri yayar; drop-in replacement.
    """
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)   # ileride kullanım için

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path
        self._proc: Optional[multiprocessing.Process] = None
        self._result_q: Optional[multiprocessing.Queue] = None

    def run(self):
        ctx = multiprocessing.get_context("spawn")
        self._result_q = ctx.Queue()
        self._proc = ctx.Process(
            target=_parse_worker_process,
            args=(self.path, self._result_q),
            daemon=True,
        )
        self._proc.start()

        # polling — join(0.2) ile döngü; UI thread bloklanmaz
        timeout_s = 300
        elapsed = 0
        while self._proc.is_alive():
            self._proc.join(timeout=0.2)
            elapsed += 0.2
            if elapsed >= timeout_s:
                self._proc.terminate()
                self._proc.join(timeout=3)
                self.error.emit("İşlem zaman aşımına uğradı (5 dk).")
                return

        try:
            msg = self._result_q.get_nowait()
        except queue.Empty:
            self.error.emit("İşlem sonucu alınamadı (process anormal sonlandı).")
            return

        if msg.get("ok"):
            self.finished.emit(msg["data"])
        else:
            self.error.emit(msg.get("error", "Bilinmeyen hata"))

    def stop(self):
        if self._proc and self._proc.is_alive():
            self._proc.terminate()
            self._proc.join(timeout=3)


class ServiceParseProcessWorker(QThread):
    """
    ServiceParseWorker'ın process-tabanlı versiyonu.
    Aynı sinyal imzası: finished(dict, bool), error(str)
    """
    finished = pyqtSignal(dict, bool)
    error = pyqtSignal(str)

    def __init__(self, path: str, is_auto: bool, parent=None):
        super().__init__(parent)
        self.path = path
        self.is_auto = is_auto
        self._proc: Optional[multiprocessing.Process] = None
        self._result_q: Optional[multiprocessing.Queue] = None

    def run(self):
        ctx = multiprocessing.get_context("spawn")
        self._result_q = ctx.Queue()
        self._proc = ctx.Process(
            target=_service_parse_worker_process,
            args=(self.path, self.is_auto, self._result_q),
            daemon=True,
        )
        self._proc.start()

        # join() yerine polling: her 200 ms'de bir kontrol et
        # → QThread içinde olsa da Windows spawn gecikmesi blocking görünüyor,
        #   polling ile timeout desteği de kazanıyoruz.
        timeout_s = 300  # 5 dakika max
        elapsed = 0
        while self._proc.is_alive():
            self._proc.join(timeout=0.2)
            elapsed += 0.2
            if elapsed >= timeout_s:
                self._proc.terminate()
                self._proc.join(timeout=3)
                self.error.emit("İşlem zaman aşımına uğradı (5 dk).")
                return

        try:
            msg = self._result_q.get_nowait()
        except queue.Empty:
            self.error.emit("İşlem sonucu alınamadı (process anormal sonlandı).")
            return

        if msg.get("ok"):
            self.finished.emit(msg["data"], msg.get("is_auto", self.is_auto))
        else:
            self.error.emit(msg.get("error", "Bilinmeyen hata"))

    def stop(self):
        if self._proc and self._proc.is_alive():
            self._proc.terminate()
            self._proc.join(timeout=3)
