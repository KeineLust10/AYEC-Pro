"""Isolated local EMA Turkish speech adapter."""

import atexit
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import threading

logger = logging.getLogger("AYEC_TTS")
_worker = None
_worker_lock = threading.Lock()


def _project_root():
    return Path(__file__).resolve().parents[2]


def _runtime_python():
    root = _project_root()
    local_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    candidates = (
        local_data / "AYEC Pro" / "TTSRuntime" / "Scripts" / "python.exe",
        root / ".venv_tts" / "Scripts" / "python.exe",
        root / ".venv_active" / "Scripts" / "python.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def synthesize_to_file(text, output_path, voice=None):
    """Create normalized Turkish speech with the local EMA voice."""
    del voice
    text = str(text or "").strip()
    if not text:
        raise ValueError("Speech text must not be empty")
    runtime = _runtime_python()
    if runtime is None:
        raise RuntimeError(
            "The isolated local Turkish TTS runtime is not installed. "
            "Run tools/setup/install_local_tts_runtime.ps1."
        )
    _request_worker(text, Path(output_path), runtime)
    return output_path


def _worker_script_path():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "src" / "utils" / "local_turkish_tts_worker.py"
    return Path(__file__).resolve().with_name("local_turkish_tts_worker.py")


def _start_worker(runtime):
    global _worker
    worker_script = _worker_script_path()
    if not worker_script.is_file():
        raise FileNotFoundError("The local Turkish TTS worker script is missing: " + str(worker_script))
    env = os.environ.copy()
    env["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    kwargs = {
        "cwd": str(worker_script.parent),
        "env": env,
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.DEVNULL,
        "text": True,
        "encoding": "utf-8",
        "bufsize": 1,
    }
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        kwargs["startupinfo"] = startupinfo
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    _worker = subprocess.Popen(
        [str(runtime), "-u", str(worker_script), "--worker"],
        **kwargs,
    )
    ready_line = _worker.stdout.readline()
    if not ready_line:
        code = _worker.poll()
        _stop_worker()
        raise RuntimeError(f"The local Turkish TTS worker failed to initialize ({code})")
    ready = json.loads(ready_line)
    if not ready.get("ready"):
        message = ready.get("error") or "The local Turkish TTS model failed to initialize"
        _stop_worker()
        raise RuntimeError(message)


def _ensure_worker(runtime):
    if _worker is None or _worker.poll() is not None:
        _start_worker(runtime)


def _preload_worker(runtime):
    try:
        with _worker_lock:
            _ensure_worker(runtime)
        logger.info("Local EMA Turkish speech model is ready")
    except Exception:
        logger.exception("Local EMA Turkish speech model could not be preloaded")


def preload_async():
    """Warm the local model in the background without blocking the UI."""
    runtime = _runtime_python()
    if runtime is None:
        logger.warning("Local Turkish TTS runtime is not installed; model preload skipped")
        return None
    thread = threading.Thread(target=_preload_worker, args=(runtime,), daemon=True)
    thread.start()
    return thread


def _request_worker(text, output_path, runtime):
    with _worker_lock:
        _ensure_worker(runtime)
        request = {
            "text": text,
            "output_path": str(output_path.resolve()),
        }
        try:
            _worker.stdin.write(json.dumps(request, ensure_ascii=True) + "\n")
            _worker.stdin.flush()
            response_line = _worker.stdout.readline()
        except (BrokenPipeError, OSError) as error:
            _stop_worker()
            raise RuntimeError("The local Turkish TTS worker stopped unexpectedly") from error
        if not response_line:
            code = _worker.poll()
            _stop_worker()
            raise RuntimeError(f"The local Turkish TTS worker exited without a result ({code})")
        response = json.loads(response_line)
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "Turkish speech synthesis failed")


def _stop_worker():
    global _worker
    worker = _worker
    _worker = None
    if worker is None or worker.poll() is not None:
        return
    try:
        worker.stdin.write('{"command":"shutdown"}\n')
        worker.stdin.flush()
        worker.stdin.close()
        worker.wait(timeout=8)
    except Exception:
        worker.terminate()


def reset_model_for_tests():
    """Stop the isolated worker between tests."""
    _stop_worker()


atexit.register(_stop_worker)
