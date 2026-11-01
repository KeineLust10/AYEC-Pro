from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
CONFIG_TOOL = ROOT / "Web_Arayuzu" / "tools" / "configure_google_oauth.py"
SPEC = importlib.util.spec_from_file_location("configure_google_oauth", CONFIG_TOOL)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_google_oauth_config_update_preserves_smtp_and_restricts_temp_file(tmp_path, monkeypatch):
    (tmp_path / "Main.py").write_text("", encoding="utf-8")
    target = tmp_path / "official-services.json"
    target.write_text(json.dumps({"smtp_host": "smtp.example", "smtp_password": "keep-me"}), encoding="utf-8")
    calls = []
    monkeypatch.setattr(
        MODULE.subprocess,
        "run",
        lambda command, **kwargs: calls.append((command, kwargs)) or SimpleNamespace(returncode=0),
    )

    saved = MODULE.save_client_id(tmp_path, "sample.apps.googleusercontent.com")

    config = json.loads(saved.read_text(encoding="utf-8"))
    assert saved == target
    assert config == {
        "smtp_host": "smtp.example",
        "smtp_password": "keep-me",
        "google_client_id": "sample.apps.googleusercontent.com",
    }
    if MODULE.os.name == "nt":
        assert calls and calls[0][0][0].lower() == "icacls"
    assert not list(tmp_path.glob(".official-services-*"))


def test_google_oauth_config_rejects_non_web_client_ids_without_writing(tmp_path):
    (tmp_path / "Main.py").write_text("", encoding="utf-8")

    try:
        MODULE.save_client_id(tmp_path, "not-a-google-client-id")
        raise AssertionError("A non-Web client ID was accepted")
    except ValueError as error:
        assert "Google Web OAuth Client ID" in str(error)

    assert not (tmp_path / "official-services.json").exists()


def test_google_oauth_disable_preserves_other_official_services(tmp_path, monkeypatch):
    (tmp_path / "Main.py").write_text("", encoding="utf-8")
    target = tmp_path / "official-services.json"
    target.write_text(
        json.dumps({"smtp_host": "smtp.example", "google_client_id": "old.apps.googleusercontent.com"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        MODULE.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )

    MODULE.save_client_id(tmp_path, "")

    assert json.loads(target.read_text(encoding="utf-8")) == {"smtp_host": "smtp.example"}
