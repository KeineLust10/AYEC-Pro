# -*- coding: utf-8 -*-

import functools
import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

THRESHOLD_MS = 300
LOG_PATH = (
    Path(os.environ.get("LOCALAPPDATA") or Path.home())
    / "AYEC Pro"
    / "performance.log"
)
_dialog_patch_installed = False


def log_slow(label, elapsed_ms, extra="", threshold_ms=None):
    active_threshold = THRESHOLD_MS if threshold_ms is None else float(threshold_ms)
    if elapsed_ms < active_threshold:
        return
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {elapsed_ms:8.1f} ms | {label}"
    if extra:
        line += f" | {extra}"
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception as exc:
        logger.debug("Performance log write failed: %s", exc)


@contextmanager
def perf_span(label, extra="", threshold_ms=None):
    start = time.perf_counter()
    try:
        yield
    finally:
        log_slow(
            label,
            (time.perf_counter() - start) * 1000.0,
            extra=extra,
            threshold_ms=threshold_ms,
        )


def timed(label=None):
    def decorator(func):
        metric_label = label or f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with perf_span(metric_label):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def wrap_method_once(obj, method_name, label=None):
    method = getattr(obj, method_name, None)
    if not callable(method) or getattr(method, "_perf_wrapped", False):
        return
    metric_label = label or f"{obj.__class__.__module__}.{obj.__class__.__name__}.{method_name}"

    @functools.wraps(method)
    def wrapped(*args, **kwargs):
        with perf_span(metric_label):
            return method(*args, **kwargs)

    wrapped._perf_wrapped = True
    try:
        setattr(obj, method_name, wrapped)
    except Exception as exc:
        logger.debug("Performance method wrap failed for %s: %s", metric_label, exc)


def install_dialog_exec_monitor():
    # Modal exec() süresi kullanıcının dialogu açık bırakma süresini de içerir;
    # bu yüzden açılış performansı için yanıltıcıdır. Ağır dialoglar explicit
    # perf_span ile oluşturma/yükleme aşamasında ölçülür.
    return
