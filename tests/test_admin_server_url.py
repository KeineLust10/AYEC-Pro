import importlib.util
from pathlib import Path


CONFIG = Path(__file__).resolve().parents[1] / "Admin_Konsol" / "config.py"


def _config(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    spec = importlib.util.spec_from_file_location("ayec_admin_config_test", CONFIG)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalize_server_url_removes_api_endpoint(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch)
    assert config.normalize_server_url("https://lisans.ayecpro.com/api/admin/login") == "https://lisans.ayecpro.com"
    assert config.normalize_server_url("https://lisans.ayecpro.com/api/") == "https://lisans.ayecpro.com"


def test_server_url_repairs_legacy_saved_endpoint(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch)
    config._current["server_url"] = "https://lisans.ayecpro.com/api/admin/login"
    assert config.server_url() == "https://lisans.ayecpro.com"
    assert config._current["server_url"] == "https://lisans.ayecpro.com"
