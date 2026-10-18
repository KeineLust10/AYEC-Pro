"""Cross-product backup and restore contracts with disposable databases."""
from contextlib import closing
import json
import sqlite3
from pathlib import Path

import pytest

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web


def _payload(tmp_path, value=1):
    path = tmp_path / f"snapshot-{value}.db"
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("CREATE TABLE sample(value INTEGER)")
        conn.execute("INSERT INTO sample VALUES (?)", (value,))
        conn.commit()
    return path.read_bytes()


def test_identical_backup_bytes_are_isolated_by_product_device_and_tenant(monkeypatch, tmp_path):
    actor, _ = _setup_tenant(monkeypatch, tmp_path)
    raw = _payload(tmp_path)
    results = []
    for tenant, product, device in (("tenant-1", "barkod_okuyucu", "pc-1"),
                                    ("tenant-1", "elek", "pc-1"),
                                    ("tenant-1", "barkod_okuyucu", "pc-2"),
                                    ("tenant-2", "barkod_okuyucu", "pc-1")):
        result = web.support_store_backup({**actor, "_tenant_id": tenant}, raw,
                                          product_code=product, hardware_id=device)
        assert result["product_archive_ok"], result
        assert Path(result["product_backup_path"]).read_bytes() == raw
        results.append(result)
    assert len({r["backup_id"] for r in results}) == 4
    assert len({r["product_backup_path"] for r in results}) == 4
    duplicate = web.support_store_backup(actor, raw, product_code="barkod_okuyucu", hardware_id="pc-1")
    assert duplicate["backup_id"] == results[0]["backup_id"]


def test_control_center_snapshot_is_tenant_scoped_and_audited(monkeypatch, tmp_path):
    actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    result = web.control_create_backup(actor, {"tenant_id": "tenant-1"})

    assert result["ok"] is True
    assert result["tenant_id"] == "tenant-1"
    assert result["product_code"] == "teknik_servis"
    with closing(web.registry_connect()) as conn:
        backup = conn.execute(
            "SELECT * FROM support_backups WHERE id=? AND tenant_id=?",
            (result["backup_id"], "tenant-1"),
        ).fetchone()
        audit = conn.execute(
            "SELECT action,detail_json FROM support_audit "
            "WHERE target_tenant_id=? ORDER BY id DESC LIMIT 1",
            ("tenant-1",),
        ).fetchone()
        assert conn.execute(
            "SELECT COUNT(*) FROM support_backups WHERE tenant_id=?", ("tenant-2",)
        ).fetchone()[0] == 0
    assert backup["source"] == "control-center"
    assert backup["product_code"] == "teknik_servis"
    assert backup["hardware_id"] == "platform"
    assert Path(web.SUPPORT_BACKUP_ROOT / "tenant-1" / backup["filename"]).is_file()
    raw = web.admin_download_support_backup(actor, "tenant-1", result["backup_id"])[0]
    with closing(sqlite3.connect(":memory:")) as snapshot:
        snapshot.deserialize(raw)
        assert snapshot.execute("SELECT username FROM users ORDER BY id LIMIT 1").fetchone()[0] == "customer-admin"
    assert audit["action"] == "admin_tenant_backup_created"
    assert json.loads(audit["detail_json"])["backup_id"] == result["backup_id"]
    assert tenant_path.is_file()

    with pytest.raises(PermissionError):
        web.control_create_backup({"id": 1, "_tenant_id": "tenant-1", "role": "Admin"},
                                  {"tenant_id": "tenant-1"})
    with pytest.raises(LookupError):
        web.control_create_backup(actor, {"tenant_id": "missing-tenant"})


def test_restore_only_reaches_matching_product_and_device(monkeypatch, tmp_path):
    actor, _ = _setup_tenant(monkeypatch, tmp_path)
    raw = _payload(tmp_path)
    backup = web.support_store_backup(actor, raw, product_code="barkod_okuyucu", hardware_id="pc-1")
    command = web.control_queue_restore(actor, {"tenant_id": "tenant-1", "backup_id": backup["backup_id"]})
    assert web.desktop_pending_commands(actor)["commands"] == []
    assert web.desktop_pending_commands(actor, "barkod_okuyucu", "pc-2")["commands"] == []
    pending = web.desktop_pending_commands(actor, "barkod_okuyucu", "pc-1")["commands"]
    assert [item["id"] for item in pending] == [command["command_id"]]
    assert pending[0]["payload"]["sha256"] == backup["sha256"]
    with pytest.raises(LookupError):
        web.support_backup_file(actor, backup["backup_id"], "elek", "pc-1")
    with pytest.raises(LookupError):
        web.desktop_complete_command(actor, {"command_id": command["command_id"], "success": True})
    assert web.support_backup_file(actor, backup["backup_id"], "barkod_okuyucu", "pc-1")[0] == raw
    assert web.desktop_complete_command(actor, {"command_id": command["command_id"], "success": True},
                                        "barkod_okuyucu", "pc-1")["ok"]
    duplicate = web.desktop_complete_command(
        actor, {"command_id": command["command_id"], "success": True,
                "result": {"restart_required": True}},
        "barkod_okuyucu", "pc-1",
    )
    assert duplicate["duplicate"] is True
    assert duplicate["status"] == "completed"


def test_retention_does_not_delete_other_products(monkeypatch, tmp_path):
    actor, _ = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web, "SUPPORT_BACKUP_KEEP", 3)
    first = web.support_store_backup(actor, _payload(tmp_path, 1), product_code="elek")
    for value in range(2, 7):
        web.support_store_backup(actor, _payload(tmp_path, value), product_code="barkod_okuyucu")
    assert web.support_backup_file(actor, first["backup_id"], "elek")[0]
    with closing(web.registry_connect()) as conn:
        counts = dict(conn.execute("SELECT product_code,COUNT(*) FROM support_backups GROUP BY product_code"))
    assert counts == {"elek": 1, "barkod_okuyucu": 3}
    assert len(list((tmp_path / "programs").glob("**/versions/*.db"))) == 4


def test_operator_download_uses_selected_tenant_not_operator_tenant(monkeypatch, tmp_path):
    actor, _ = _setup_tenant(monkeypatch, tmp_path)
    customer = {"id": 1, "_tenant_id": "tenant-2"}
    raw = _payload(tmp_path)
    backup = web.support_store_backup(customer, raw, product_code="barkod_okuyucu", hardware_id="pc")
    assert web.admin_download_support_backup(actor, "tenant-2", backup["backup_id"])[0] == raw
    with pytest.raises(LookupError):
        web.admin_download_support_backup(actor, "tenant-1", backup["backup_id"])
    with pytest.raises(PermissionError):
        web.admin_download_support_backup(customer, "tenant-2", backup["backup_id"])


def test_same_hardware_two_installations_are_isolated(monkeypatch, tmp_path):
    actor, _ = _setup_tenant(monkeypatch, tmp_path)
    first_raw = _payload(tmp_path, 11)
    second_raw = _payload(tmp_path, 12)
    first = web.support_store_backup(
        actor, first_raw, product_code="barkod_okuyucu",
        hardware_id="same-pc", installation_id="install-a",
    )
    second = web.support_store_backup(
        actor, second_raw, product_code="barkod_okuyucu",
        hardware_id="same-pc", installation_id="install-b",
    )
    assert first["backup_id"] != second["backup_id"]
    assert first["product_backup_path"] != second["product_backup_path"]
    assert web.support_backup_file(
        actor, first["backup_id"], "barkod_okuyucu", "same-pc", "install-a"
    )[0] == first_raw
    with pytest.raises(LookupError):
        web.support_backup_file(
            actor, first["backup_id"], "barkod_okuyucu", "same-pc", "install-b"
        )

    command = web.control_queue_restore(actor, {
        "tenant_id": "tenant-1", "backup_id": first["backup_id"]
    })
    assert len(web.desktop_pending_commands(
        actor, "barkod_okuyucu", "same-pc", "install-a"
    )["commands"]) == 1
    assert web.desktop_pending_commands(
        actor, "barkod_okuyucu", "same-pc", "install-b"
    )["commands"] == []
    with pytest.raises(LookupError):
        web.desktop_complete_command(
            actor, {"command_id": command["command_id"], "success": True},
            "barkod_okuyucu", "same-pc", "install-b"
        )
    assert web.desktop_complete_command(
        actor, {"command_id": command["command_id"], "success": True},
        "barkod_okuyucu", "same-pc", "install-a"
    )["ok"]
