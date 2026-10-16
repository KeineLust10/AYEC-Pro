from datetime import datetime
from types import SimpleNamespace

from src.services import assistant_manager as assistant_manager_module
from src.services.assistant_manager import AssistantManager


class FakeSignal:
    def __init__(self):
        self.handlers = []

    def connect(self, handler):
        self.handlers.append(handler)


class FakeReminderWorker:
    def __init__(self, db_name, run_key, parent):
        self.db_name = db_name
        self.run_key = run_key
        self.parent = parent
        self.result_ready = FakeSignal()
        self.finished = FakeSignal()
        self.started = False

    def isRunning(self):
        return self.started

    def start(self):
        self.started = True

    def deleteLater(self):
        pass


class FakeDatabase:
    _db_name = "test.db"

    def __init__(self, enabled="1", day="4", time="10:00", last_run=""):
        self.values = {
            "whatsapp_payment_reminder_enabled": enabled,
            "whatsapp_payment_reminder_day": day,
            "whatsapp_payment_reminder_time": time,
        }
        self.last_run = last_run

    def get_setting(self, key, default=""):
        return self.values.get(key, default)

    def get_internal_setting(self, key, default=""):
        return self.last_run if key == "whatsapp_payment_last_run" else default


def make_manager(db):
    return SimpleNamespace(
        db=db,
        payment_reminder_worker=None,
        _on_payment_reminder_result=lambda _result: None,
        _clear_payment_reminder_worker=lambda _worker: None,
    )


def test_weekly_reminder_starts_worker_when_schedule_is_due(monkeypatch):
    workers = []

    def worker_factory(db_name, run_key, parent):
        worker = FakeReminderWorker(db_name, run_key, parent)
        workers.append(worker)
        return worker

    monkeypatch.setattr(assistant_manager_module, "PaymentReminderWorker", worker_factory)
    manager = make_manager(FakeDatabase())

    AssistantManager._process_payment_reminders(manager, datetime(2026, 10, 16, 10, 0, 15))

    assert len(workers) == 1
    assert workers[0].db_name == "test.db"
    assert workers[0].run_key == "2026-10-16-10:00"
    assert workers[0].started


def test_weekly_reminder_does_not_start_outside_schedule(monkeypatch):
    monkeypatch.setattr(
        assistant_manager_module,
        "PaymentReminderWorker",
        lambda *_args: (_ for _ in ()).throw(AssertionError("worker should not start")),
    )
    manager = make_manager(FakeDatabase())

    AssistantManager._process_payment_reminders(manager, datetime(2026, 10, 16, 10, 1))

    assert manager.payment_reminder_worker is None
