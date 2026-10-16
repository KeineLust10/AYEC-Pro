import os
from pathlib import Path
from types import SimpleNamespace

from PyQt6.QtWidgets import QApplication

from src.ui.pages.settings_widgets import voice_healthcheck_worker as worker_module
from src.ui.pages.settings_widgets.voice_training_reference import VoiceTrainingWidget
from src.utils.path_helper import PathHelper
from src.ui.pages.settings_widgets.voice_healthcheck_worker import VoiceHealthcheckWorker


def test_healthcheck_worker_uses_temporary_data_and_decodes_utf8(monkeypatch):
    calls = []
    completed = []
    failed = []
    previous_local_app_data = os.environ.get("LOCALAPPDATA")

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout='INFO: check complete\n{"overall_ok": true, "label": "T\u00fcrk\u00e7e"}',
            stderr="",
        )

    monkeypatch.setattr(worker_module.subprocess, "run", run)
    worker = VoiceHealthcheckWorker("healthcheck.py", "project")
    worker.completed.connect(completed.append)
    worker.failed.connect(failed.append)

    worker.run()

    command, options = calls[0]
    temporary_data = options["env"]["LOCALAPPDATA"]
    assert command[-1] == "healthcheck.py"
    assert options["cwd"] == "project"
    assert options["encoding"] == "utf-8"
    assert options["env"]["PYTHONIOENCODING"] == "utf-8"
    assert temporary_data != previous_local_app_data
    assert not Path(temporary_data).exists()
    assert completed == [{"overall_ok": True, "label": "T\u00fcrk\u00e7e"}]
    assert failed == []


def test_healthcheck_worker_reports_nonzero_exit_without_json(monkeypatch):
    completed = []
    failed = []
    monkeypatch.setattr(
        worker_module.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=2,
            stdout="partial",
            stderr="healthcheck failed",
        ),
    )
    worker = VoiceHealthcheckWorker("healthcheck.py", "project")
    worker.completed.connect(completed.append)
    worker.failed.connect(failed.append)

    worker.run()

    assert completed == []
    assert failed and "healthcheck failed" in failed[0]


def test_voice_settings_starts_healthcheck_asynchronously(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(PathHelper, "get_app_data_dir", lambda: str(tmp_path))

    class Db:
        def get_setting(self, _key, default=""):
            return default

        def set_setting(self, _key, _value):
            return None

        def get_all_scheduled_alerts(self):
            return []

        def update_scheduled_alert(self, *_args, **_kwargs):
            return None

    class Signal:
        def connect(self, callback):
            self.callback = callback

    class Worker:
        def __init__(self, script_path, project_root, parent):
            self.args = (script_path, project_root, parent)
            self.completed = Signal()
            self.failed = Signal()
            self.finished = Signal()
            self.started = False

        def isRunning(self):
            return self.started

        def start(self):
            self.started = True

    monkeypatch.setattr(worker_module, "VoiceHealthcheckWorker", Worker)
    widget = VoiceTrainingWidget(Db())

    widget.run_healthcheck()

    assert widget._healthcheck_worker.started
    assert not widget.btn_healthcheck.isEnabled()
    assert widget.lbl_test_result.text() == "Sesli asistan sa\u011fl\u0131k testi \u00e7al\u0131\u015f\u0131yor..."
    widget.close()
    app.processEvents()
