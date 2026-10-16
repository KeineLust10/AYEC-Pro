import json
import os
import shutil
import subprocess
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import requests

import Web_Arayuzu.Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def test_authenticated_customer_map_click_updates_coordinates(monkeypatch, tmp_path):
    from src.utils.local_secret_store import load_secret

    if not load_secret("tomtom_traffic_api_key"):
        pytest.skip("The local TomTom map credential is not configured.")
    edge = Path(os.environ.get("EDGE_EXECUTABLE", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"))
    if not edge.is_file() or not shutil.which("node"):
        pytest.skip("Headless Edge and Node are required for the offscreen map check.")

    _actor, _tenant_path = _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    session = requests.Session()
    session.headers["Origin"] = base_url
    try:
        login = session.post(
            base_url + "/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
        )
        assert login.status_code == 200
        cookies = [
            {"name": cookie.name, "value": cookie.value, "path": cookie.path, "secure": cookie.secure}
            for cookie in session.cookies
        ]
        output_path = Path(__file__).resolve().parents[1] / "output" / "playwright" / "customer-location-map-authenticated-headless.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({
            "AYEC_MAP_AUDIT_URL": base_url + "/",
            "AYEC_MAP_AUDIT_COOKIES": json.dumps(cookies),
            "AYEC_MAP_AUDIT_SCREENSHOT": str(output_path),
            "EDGE_EXECUTABLE": str(edge),
        })
        script = Path(__file__).resolve().parents[1] / "tools" / "quality" / "customer_location_map_offscreen_capture.cjs"
        result = subprocess.run(
            ["node", str(script)],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr[-4000:]
        evidence = json.loads(result.stdout.strip().splitlines()[-1])
        assert evidence["changed"] is True
        assert evidence["selected"]["status"].startswith("Haritadan")
        assert evidence["browserExceptions"] == 0
        assert output_path.is_file() and output_path.stat().st_size > 0
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
        session.close()
