"""Persistent, isolated inference worker for the local Turkish EMA model."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import traceback

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    import torch
    from ema_lightning import EMA

    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    _model = EMA()
    return _model


def _synthesize(request):
    output_path = Path(request["output_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = str(request.get("text") or "").strip()
    if not text:
        raise ValueError("Speech text must not be empty")
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        speech = _load_model().say(text, path=str(output_path), sample_rate=48000)
    return {
        "ok": True,
        "sample_rate": speech.sample_rate,
        "frames": len(speech.audio),
        "duration": speech.duration,
        "normalized_text": " ".join(word.text for word in speech.words),
    }


def main():
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            _load_model()
        ready = {"ready": True}
    except Exception:
        ready = {"ready": False, "error": traceback.format_exc()[-5000:]}
    sys.stdout.write(json.dumps(ready, ensure_ascii=True) + "\n")
    sys.stdout.flush()
    if not ready["ready"]:
        return

    for line in sys.stdin:
        try:
            request = json.loads(line)
            if request.get("command") == "shutdown":
                break
            response = _synthesize(request)
        except Exception:
            response = {"ok": False, "error": traceback.format_exc()[-5000:]}
        sys.stdout.write(json.dumps(response, ensure_ascii=True) + "\n")
        sys.stdout.flush()


if __name__ == "__main__" and "--worker" in sys.argv:
    main()
