import logging
import sys
import threading
from types import SimpleNamespace

from logging.handlers import RotatingFileHandler

from src.utils import logger as logger_module
from src.utils.logger import MultiInstanceRotatingFileHandler


def test_rollover_permission_conflict_reopens_active_log(tmp_path, monkeypatch):
    log_path = tmp_path / "active.log"
    handler = MultiInstanceRotatingFileHandler(
        str(log_path), maxBytes=1, backupCount=1, encoding="utf-8"
    )

    def locked_rollover(_handler):
        if _handler.stream is not None:
            _handler.stream.close()
            _handler.stream = None
        raise PermissionError("file is in use by another process")

    monkeypatch.setattr(RotatingFileHandler, "doRollover", locked_rollover)
    handler.doRollover()
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "after lock", (), None)
    handler.emit(record)
    handler.close()

    assert "after lock" in log_path.read_text(encoding="utf-8")


def test_telemetry_worker_is_joined_before_interpreter_shutdown(tmp_path, monkeypatch):
    sent = threading.Event()
    monkeypatch.setitem(
        sys.modules,
        "requests",
        SimpleNamespace(post=lambda *_args, **_kwargs: sent.set()),
    )
    from src.utils.path_helper import PathHelper

    monkeypatch.setattr(PathHelper, "get_db_path", lambda *_args: str(tmp_path / "missing.db"))
    was_stopping = logger_module._telemetry_stopping
    logger_module._telemetry_stopping = False
    logger_module.send_telemetry_to_server("fixture", "fixture trace")
    logger_module._join_telemetry_threads()
    assert sent.is_set()
    assert not logger_module._telemetry_threads
    logger_module._telemetry_stopping = was_stopping
