import json
import os
import shutil
import subprocess
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

import Web_Arayuzu.Main as web_main


ROOT = Path(__file__).resolve().parents[1]


def test_project_unit_note_editor_saves_and_closes_offscreen():
    edge = Path(os.environ.get("EDGE_EXECUTABLE", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"))
    if not edge.is_file() or not shutil.which("node"):
        pytest.skip("Headless Edge and Node are required for the offscreen project note check.")

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        env = os.environ.copy()
        env.update({
            "AYEC_AUDIT_URL": f"http://127.0.0.1:{server.server_address[1]}/",
            "AYEC_AUDIT_CDP_PORT": str(20000 + os.getpid() % 20000),
            "EDGE_EXECUTABLE": str(edge),
        })
        script = ROOT / "tools" / "quality" / "project_unit_note_offscreen.cjs"
        result = subprocess.run(
            ["node", str(script)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
        )
        assert result.returncode == 0, result.stderr[-4000:]
        evidence = json.loads(result.stdout.strip().splitlines()[-1])
        assert evidence["initial"] == {"open": True, "title": "Teknik Not", "note": "Original note"}
        assert evidence["state"]["closed"] is True
        assert evidence["state"]["open"] is False
        assert evidence["state"]["updatedNote"] == "Updated fixture note"
        assert evidence["browserExceptions"] == 0
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
