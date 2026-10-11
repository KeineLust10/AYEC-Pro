from pathlib import Path
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1] / "Web_Arayuzu"


def test_server_deployment_bundle_has_required_files_and_persistent_mounts():
    for filename in ("Dockerfile", "docker-compose.yml", ".env.example", "DEPLOYMENT.md"):
        assert (ROOT / filename).is_file()
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    deployment = (ROOT / "DEPLOYMENT.md").read_text(encoding="utf-8")
    assert '"${AYEC_PORT:-8501}:8501"' in compose
    assert "./data:/data" in compose
    assert "./Kullan" in compose
    assert "./web/uploads:/app/web/uploads" in compose
    assert ".env" in ignore and "data" in ignore and "web/uploads" in ignore
    assert "backups" in ignore and "support_backups" in ignore and "Kullan*" in ignore
    assert "docker compose config --quiet" in deployment
    assert "docker compose build ayec-web" in deployment
    assert "docker compose up -d ayec-web" in deployment


def test_clean_server_bundle_contains_runtime_and_excludes_local_state(tmp_path):
    output = tmp_path / "AYEC_Pro_Web_Server.zip"
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_deployment_bundle.py"), "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()

    assert "Web_Arayuzu/Dockerfile" in names
    assert "Web_Arayuzu/.env.example" in names
    assert "Web_Arayuzu/web/index.html" in names
    assert not any("/data/" in name or "/backups/" in name for name in names)
    assert not any("/Kullan" in name or "/.venv" in name for name in names)
    assert not any(name.endswith((".db", ".sqlite", ".sqlite3")) for name in names)
