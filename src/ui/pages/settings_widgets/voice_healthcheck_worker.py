import json
import os
import subprocess
import sys
import tempfile

from PyQt6.QtCore import QThread, pyqtSignal


class VoiceHealthcheckWorker(QThread):
    completed = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, script_path, project_root, parent=None):
        super().__init__(parent)
        self.script_path = str(script_path)
        self.project_root = str(project_root)

    def run(self):
        try:
            with tempfile.TemporaryDirectory(prefix="ayec_voice_healthcheck_") as data_dir:
                env = os.environ.copy()
                env["LOCALAPPDATA"] = data_dir
                env["PYTHONIOENCODING"] = "utf-8"
                result = subprocess.run(
                    [sys.executable, self.script_path],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=25,
                    env=env,
                )
                stdout = (result.stdout or "").strip()
                stderr = (result.stderr or "").strip()
                if result.returncode != 0:
                    raise RuntimeError(
                        f"Healthcheck exited with code {result.returncode}: {stderr or stdout or '-'}"
                    )

                json_start = stdout.find("{")
                if json_start < 0:
                    raise ValueError("Healthcheck returned no JSON result.")
                self.completed.emit(json.loads(stdout[json_start:]))
        except subprocess.TimeoutExpired:
            self.failed.emit("Healthcheck exceeded the 25 second limit.")
        except Exception as exc:
            self.failed.emit(str(exc))
