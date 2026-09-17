import sqlite3
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import Web_Arayuzu.Main as web_main


def _configure_isolated_web(monkeypatch, tmp_path):
    registry_path = tmp_path / "registry.db"
    tenant_root = tmp_path / "Kullanicilar"
    backup_root = tmp_path / "support_backups"
    monkeypatch.setattr(web_main, "DB_PATH", registry_path)
    monkeypatch.setattr(web_main, "TENANT_ROOT", tenant_root)
    monkeypatch.setattr(web_main, "SUPPORT_BACKUP_ROOT", backup_root)
    monkeypatch.setattr(
        web_main,
        "send_registration_emails",
        lambda *_args, **_kwargs: (True, "ok"),
    )
    web_main._SCHEMA_READY_PATHS.clear()
    web_main.clear_tenant_context()
    return registry_path, tenant_root


def _registration_payload(**overrides):
    payload = {
        "company_name": "Sector Test Company",
        "full_name": "Test Administrator",
        "username": "sector.admin",
        "email": "sector@example.com",
        "phone": "05340000000",
        "password": "SectorPass42",
    }
    payload.update(overrides)
    return payload


def test_company_registration_requires_explicit_sector(monkeypatch, tmp_path):
    _configure_isolated_web(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="Sekt.r se.imi zorunludur"):
        web_main.setup_application(_registration_payload(), allow_existing=True)


def test_sector_is_saved_and_admin_change_updates_both_databases(
    monkeypatch,
    tmp_path,
):
    registry_path, tenant_root = _configure_isolated_web(monkeypatch, tmp_path)
    result = web_main.setup_application(
        _registration_payload(sector="otomotiv"),
        allow_existing=True,
    )
    tenant_id = result["tenant"]["id"]
    tenant_path = tenant_root / result["tenant"]["db_filename"]

    with sqlite3.connect(registry_path) as registry:
        saved_sector = registry.execute(
            "SELECT sector FROM tenants WHERE id=?",
            (tenant_id,),
        ).fetchone()[0]
    with sqlite3.connect(tenant_path) as tenant_db:
        local_sector = tenant_db.execute(
            "SELECT value FROM internal_settings WHERE key='current_sector'"
        ).fetchone()[0]
    assert saved_sector == "otomotiv"
    assert local_sector == "otomotiv"

    actor = {
        "id": result["user"]["id"],
        "role": "Admin",
        "_tenant_id": tenant_id,
    }
    update = web_main.update_current_company_sector(
        actor,
        {"sector": "teknik_servis"},
    )
    assert update["sector"] == "teknik_servis"

    with sqlite3.connect(registry_path) as registry:
        saved_sector = registry.execute(
            "SELECT sector FROM tenants WHERE id=?",
            (tenant_id,),
        ).fetchone()[0]
    with sqlite3.connect(tenant_path) as tenant_db:
        local_sector = tenant_db.execute(
            "SELECT value FROM internal_settings WHERE key='current_sector'"
        ).fetchone()[0]
    assert saved_sector == "teknik_servis"
    assert local_sector == "teknik_servis"


def test_regular_user_cannot_change_company_sector(monkeypatch, tmp_path):
    _configure_isolated_web(monkeypatch, tmp_path)
    result = web_main.setup_application(
        _registration_payload(sector="otomotiv"),
        allow_existing=True,
    )

    with pytest.raises(PermissionError):
        web_main.update_current_company_sector(
            {
                "id": result["user"]["id"],
                "role": "User",
                "_tenant_id": result["tenant"]["id"],
            },
            {"sector": "teknik_servis"},
        )


def test_vendor_admin_change_updates_registry_and_tenant_database(
    monkeypatch,
    tmp_path,
):
    registry_path, tenant_root = _configure_isolated_web(monkeypatch, tmp_path)
    result = web_main.setup_application(
        _registration_payload(sector="teknik_servis"),
        allow_existing=True,
    )
    tenant_id = result["tenant"]["id"]
    tenant_path = tenant_root / result["tenant"]["db_filename"]

    update = web_main.admin_update_company(tenant_id, {"sector": "otomotiv"})
    assert update["sector"] == "otomotiv"

    with sqlite3.connect(registry_path) as registry:
        assert registry.execute(
            "SELECT sector FROM tenants WHERE id=?",
            (tenant_id,),
        ).fetchone()[0] == "otomotiv"
    with sqlite3.connect(tenant_path) as tenant_db:
        assert tenant_db.execute(
            "SELECT value FROM internal_settings WHERE key='current_sector'"
        ).fetchone()[0] == "otomotiv"

    with pytest.raises(ValueError, match="Gecersiz sektor"):
        web_main.admin_update_company(tenant_id, {"sector": "invalid"})


def test_web_and_desktop_sector_contracts_are_present():
    app_source = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    server_source = (ROOT / "Web_Arayuzu" / "Main.py").read_text(
        encoding="utf-8"
    )
    client_source = (ROOT / "src" / "utils" / "web_sync_client.py").read_text(
        encoding="utf-8"
    )

    assert 'sectorSelect.name="sector"' in app_source
    assert 'data-action="save-company-sector"' in app_source
    assert 'path == "/api/company/sector"' in server_source
    assert '"/api/company/sector"' in client_source


def test_web_navigation_is_scoped_and_hierarchical_for_both_sectors():
    app_source = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    style_source = (ROOT / "Web_Arayuzu" / "web" / "styles.css").read_text(
        encoding="utf-8"
    )

    assert "const ayecSectorMenuModels={" in app_source
    assert 'id:"stock-parent"' in app_source
    assert 'id:"automotive-stock-parent"' in app_source
    assert 'id:"automotive-stock"' in app_source
    assert 'id:"vehicle-maintenance"' in app_source
    assert 'data-editor-panel="${sector}"' in app_source
    assert 'data-editor-sector="teknik_servis"' in app_source
    assert 'data-editor-sector="otomotiv"' in app_source
    assert 'target==="stock")target="automotive-stock"' in app_source
    assert 'target==="automotive-stock")target="stock"' in app_source
    assert ".sector-menu-columns" in style_source
    assert ".sector-menu-group" in style_source
    assert ".sector-menu-children" in style_source
    assert ".sector-menu-panel.mobile-active" in style_source
    assert "dialog.sector-menu-editor-dialog footer{display:grid" in style_source
    assert "white-space:nowrap" in style_source


def test_web_system_identity_has_sector_and_module_controls():
    app_source = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(
        encoding="utf-8"
    )

    assert 'class="identity-settings"' in app_source
    assert 'id="companySectorSelect"' in app_source
    assert 'data-action="save-company-sector"' in app_source
    assert '["module_operations_active"' in app_source
    assert '["module_stock_active"' in app_source
    assert '["feature_right_click_active"' in app_source


def test_vendor_admin_console_has_sector_control():
    console_source = (ROOT / "Admin_Konsol" / "pages" / "companies.py").read_text(
        encoding="utf-8"
    )

    assert "class _UpdateSectorThread" in console_source
    assert "api_client.update_company_sector(self._tid, self._sector)" in console_source
    assert "self._sector_btn.clicked.connect(self._change_sector)" in console_source
    assert "Sekt\\u00f6r zaten secili." not in console_source


def test_vendor_admin_sector_client_falls_back_to_control_api(monkeypatch):
    admin_root = str(ROOT / "Admin_Konsol")
    if admin_root not in sys.path:
        sys.path.insert(0, admin_root)
    import api_client as admin_api

    calls = []

    class FakeResponse:
        def __init__(self, ok, status_code, payload):
            self.ok = ok
            self.status_code = status_code
            self._payload = payload
            self.text = str(payload)

        def json(self):
            return self._payload

    def fake_post(url, **kwargs):
        calls.append((url, kwargs.get("json")))
        if url.endswith("/api/control/tenant"):
            return FakeResponse(True, 200, {"ok": True, "sector": "otomotiv"})
        return FakeResponse(False, 400, {"error": "Guncellenecek alan bulunamadi"})

    monkeypatch.setattr(admin_api.config, "server_url", lambda: "http://test")
    monkeypatch.setattr(admin_api.config, "timeout", lambda: 1)
    monkeypatch.setattr(admin_api.requests, "post", fake_post)

    result = admin_api.update_company_sector("tenant-1", "otomotiv")

    assert result["sector"] == "otomotiv"
    assert calls == [
        ("http://test/api/admin/companies/tenant-1", {"sector": "otomotiv"}),
        (
            "http://test/api/control/tenant",
            {"tenant_id": "tenant-1", "sector": "otomotiv"},
        ),
    ]


def test_vendor_admin_login_enter_contract():
    source = (ROOT / "Admin_Konsol" / "login_window.py").read_text(
        encoding="utf-8"
    )

    assert "self._password.returnPressed.connect(self._do_login)" in source
    assert "self._email.returnPressed.connect(self._focus_password)" in source
    assert "self._close_btn.setAutoDefault(False)" in source
    assert "self._login_btn.setAutoDefault(False)" in source
    assert "if self._login_in_progress:" in source
