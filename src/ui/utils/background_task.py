"""Reusable cancellable background jobs for desktop UI tasks."""

from __future__ import annotations

import os
import threading
from typing import Any, Callable, Optional

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import QProgressDialog


class CancellableTaskWorker(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(
        self,
        target: Callable[[Callable[[], bool]], Any],
        output_path: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._target = target
        self._output_path = str(output_path or "")
        self._cancel_event = threading.Event()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set() or self.isInterruptionRequested()

    def cancel(self):
        self._cancel_event.set()
        self.requestInterruption()

    def _remove_partial_output(self):
        if not self._output_path:
            return
        try:
            if os.path.isfile(self._output_path):
                os.remove(self._output_path)
        except OSError:
            pass

    def run(self):
        try:
            if self.is_cancelled():
                self.cancelled.emit()
                return
            result = self._target(self.is_cancelled)
            if self.is_cancelled():
                self._remove_partial_output()
                self.cancelled.emit()
                return
            self.succeeded.emit(result)
        except Exception as exc:
            self._remove_partial_output()
            self.failed.emit(str(exc))


def run_cancellable_task(
    owner,
    title: str,
    target: Callable[[Callable[[], bool]], Any],
    on_success: Callable[[Any], None],
    on_error: Optional[Callable[[str], None]] = None,
    on_done: Optional[Callable[[], None]] = None,
    output_path: str = "",
):
    """Start a modal background task and retain it until completion."""
    progress = QProgressDialog(
        str(title or ""),
        "\u0130ptal",
        0,
        0,
        owner,
    )
    progress.setWindowTitle(str(title or ""))
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setMinimumDuration(0)
    progress.setAutoClose(False)
    progress.setAutoReset(False)

    worker = CancellableTaskWorker(
        target=target,
        output_path=output_path,
        parent=owner,
    )
    jobs = getattr(owner, "_background_jobs", None)
    if jobs is None:
        jobs = []
        owner._background_jobs = jobs
    handle = {"worker": worker, "progress": progress}
    jobs.append(handle)

    def cleanup():
        progress.close()
        if handle in jobs:
            jobs.remove(handle)
        worker.deleteLater()
        progress.deleteLater()
        if on_done:
            on_done()

    def success(result):
        try:
            on_success(result)
        finally:
            cleanup()

    def failure(message):
        try:
            if on_error:
                on_error(str(message or ""))
        finally:
            cleanup()

    def cancelled():
        cleanup()

    progress.canceled.connect(worker.cancel)
    worker.succeeded.connect(success)
    worker.failed.connect(failure)
    worker.cancelled.connect(cancelled)
    progress.show()
    worker.start()
    return worker
