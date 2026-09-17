"""Low-overhead startup timeline recorder."""

from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


class StartupProfiler:
    def __init__(self):
        self.enabled = os.environ.get("AYEC_STARTUP_PROFILE", "1") != "0"
        self.started_at = time.perf_counter()
        self.last_mark_at = self.started_at
        self.records = []
        self._finished = False
        self._lock = threading.Lock()

    def mark(self, label, detail=""):
        if not self.enabled or self._finished:
            return
        now = time.perf_counter()
        with self._lock:
            total_ms = (now - self.started_at) * 1000.0
            delta_ms = (now - self.last_mark_at) * 1000.0
            self.last_mark_at = now
            self.records.append((str(label), total_ms, delta_ms, str(detail or "")))

    @contextmanager
    def span(self, label, detail=""):
        started_at = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - started_at) * 1000.0
            suffix = f"duration_ms={elapsed_ms:.1f}"
            self.mark(label, detail=f"{detail} {suffix}".strip())

    def finish(self, label="startup.complete"):
        if not self.enabled or self._finished:
            return None
        self.mark(label)
        with self._lock:
            self._finished = True
            records = list(self.records)
        if not records:
            return None

        root = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        log_path = root / "AYEC Pro" / "startup_performance.log"
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            lines = [f"{stamp} | startup_timeline"]
            for item_label, total_ms, delta_ms, item_detail in records:
                line = (
                    f"  {total_ms:9.1f} ms | +{delta_ms:8.1f} ms | "
                    f"{item_label}"
                )
                if item_detail:
                    line += f" | {item_detail}"
                lines.append(line)
            lines.append("")
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write("\n".join(lines))
            logger.info(
                "Startup timeline recorded: %.1f ms (%s)",
                records[-1][1],
                log_path,
            )
            return log_path
        except Exception as exc:
            logger.debug("Startup timeline write failed: %s", exc)
            return None


_profiler = StartupProfiler()


def startup_mark(label, detail=""):
    _profiler.mark(label, detail)


def startup_span(label, detail=""):
    return _profiler.span(label, detail)


def startup_finish(label="startup.complete"):
    return _profiler.finish(label)
