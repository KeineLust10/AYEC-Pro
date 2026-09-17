from src.utils.desktop_service_policy import (
    auto_web_sync_enabled,
    local_api_enabled,
    local_api_host,
)


class _Settings:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get_setting(self, key, default=None):
        return self.values.get(key, default)


def test_startup_sync_is_enabled_and_local_api_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AYECPRO_ENABLE_WEB_SYNC", raising=False)
    monkeypatch.delenv("AYECPRO_ENABLE_LOCAL_API", raising=False)

    assert auto_web_sync_enabled(_Settings()) is True
    assert local_api_enabled(_Settings()) is False


def test_database_settings_can_enable_desktop_services(monkeypatch):
    monkeypatch.delenv("AYECPRO_ENABLE_WEB_SYNC", raising=False)
    monkeypatch.delenv("AYECPRO_ENABLE_LOCAL_API", raising=False)
    settings = _Settings(
        {
            "desktop_auto_web_sync": "1",
            "desktop_local_api": "true",
        }
    )

    assert auto_web_sync_enabled(settings) is True
    assert local_api_enabled(settings) is True


def test_environment_override_has_priority(monkeypatch):
    settings = _Settings(
        {
            "desktop_auto_web_sync": "1",
            "desktop_local_api": "1",
        }
    )
    monkeypatch.setenv("AYECPRO_ENABLE_WEB_SYNC", "0")
    monkeypatch.setenv("AYECPRO_ENABLE_LOCAL_API", "false")

    assert auto_web_sync_enabled(settings) is False
    assert local_api_enabled(settings) is False


def test_local_api_is_loopback_only():
    assert local_api_host() == "127.0.0.1"
