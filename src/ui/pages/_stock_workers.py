# -*- coding: utf-8 -*-
# _stock_workers.py
# Worker sınıfları için modül

from PyQt6.QtCore import QThread, pyqtSignal
import os
from src.utils.performance_monitor import perf_span


class StockWorker(QThread):
    finished = pyqtSignal(list, int, dict)  # parts, total_count, stats
    error = pyqtSignal(str)

    def __init__(
        self, db, limit, offset, search_query, category_filters, critical_only,
        metric_filter="all",
    ):
        super().__init__()
        self.source_db = db
        self.db_name = getattr(db, "_db_name", "ayecpro.db")
        self.limit = limit
        self.offset = offset
        self.search_query = search_query
        self.category_filters = category_filters
        self.critical_only = critical_only
        self.metric_filter = metric_filter

    def run(self):
        db = None
        try:
            if (
                self.db_name == ":memory:"
                or os.environ.get("AYECPRO_SAFE_UI") == "1"
                or os.environ.get("QT_QPA_PLATFORM") == "offscreen"
            ):
                db = self.source_db
            else:
                from src.database import Database
                db = Database(self.db_name, init_mode="connection_only")
            # 1. Fetch Paginated Parts
            with perf_span(
                "sql.stock.page",
                extra=f"limit={self.limit} offset={self.offset}",
                threshold_ms=75,
            ):
                parts, total = db.get_parts_paginated(
                    limit=self.limit,
                    offset=self.offset,
                    search_query=self.search_query,
                    category=self.category_filters,
                    critical_only=self.critical_only,
                    metric_filter=self.metric_filter,
                )

            # 2. Fetch Stats (Global)
            with perf_span("sql.stock.stats", threshold_ms=75):
                stats = db.get_stock_stats()

            self.finished.emit(parts, total, stats)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if db is not None and db is not self.source_db:
                try:
                    db.close()
                except Exception:
                    pass


class HistoryWorker(QThread):
    """Stok geçmişini arka planda yükler — UI thread'unu bloklamaz."""
    finished = pyqtSignal(list, int)
    error = pyqtSignal(str)

    def __init__(self, db, limit=100, offset=0):
        super().__init__()
        self.source_db = db
        self.db_name = getattr(db, "_db_name", "ayecpro.db")
        self.limit = limit
        self.offset = offset

    def run(self):
        db = None
        try:
            if (
                self.db_name == ":memory:"
                or os.environ.get("AYECPRO_SAFE_UI") == "1"
                or os.environ.get("QT_QPA_PLATFORM") == "offscreen"
            ):
                db = self.source_db
            else:
                from src.database import Database
                db = Database(self.db_name, init_mode="connection_only")
            with perf_span(
                "sql.stock.history",
                extra=f"limit={self.limit} offset={self.offset}",
                threshold_ms=75,
            ):
                hists, total = db.get_stock_history(
                    limit=self.limit,
                    offset=self.offset,
                    with_total=True,
                )
            self.finished.emit(list(hists or []), int(total or 0))
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if db is not None and db is not self.source_db:
                try:
                    db.close()
                except Exception:
                    pass


class ParseWorker(QThread):
    """parse_file() işlemini arka planda çalıştırır — UI thread'unu bloklamaz."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        try:
            from src.utils.stock_import_parser import StockImportParser
            result = StockImportParser.parse_file(self.path)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
