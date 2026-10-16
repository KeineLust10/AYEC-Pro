import base64
import sqlite3
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def _insert_contract(path):
    conn = web_main._raw_connect(path)
    conn.execute(
        "INSERT INTO contracts(customer_id,title,contract_type,description,status) VALUES(NULL,?,?,?,?)",
        ("Maintenance Plan", "Annual", "Annual service plan", "Aktif"),
    )
    contract_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return contract_id


def test_contract_detail_upload_download_delete_is_authenticated_and_tenant_scoped(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    contract_id = _insert_contract(tenant_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        detail_url = f"{base_url}/api/desktop/contracts/{contract_id}/attachments"
        assert anonymous.get(detail_url).status_code == 401
        assert anonymous.post(
            f"{base_url}/api/desktop/table/contracts",
            json={"id": contract_id, "_action": "delete"},
        ).status_code == 401
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
        )
        assert login.status_code == 200
        original = b"%PDF-1.4 tenant contract fixture"
        uploaded = session.post(
            detail_url,
            json={"filename": "../service agreement.pdf", "data_base64": base64.b64encode(original).decode("ascii")},
        )
        assert uploaded.status_code == 201
        attachment_id = uploaded.json()["id"]
        details = session.get(detail_url).json()
        assert details["contract"]["title"] == "Maintenance Plan"
        assert details["attachments"] == [{
            "id": attachment_id,
            "filename": "service agreement.pdf",
            "created_at": details["attachments"][0]["created_at"],
            "available": True,
        }]
        stored = list((tmp_path / "Kullanicilar" / "contract_docs" / "tenant-1").iterdir())
        assert len(stored) == 1
        assert stored[0].read_bytes() == original
        download = session.get(
            f"{base_url}/api/desktop/contracts/attachments/{attachment_id}/download"
        )
        assert download.status_code == 200
        assert download.content == original
        assert "filename*=UTF-8''service%20agreement.pdf" in download.headers["Content-Disposition"]
        removed = session.post(
            f"{base_url}/api/desktop/contracts/attachments/delete",
            json={"attachment_id": attachment_id},
        )
        assert removed.status_code == 200
        assert session.get(detail_url).json()["attachments"] == []
        assert not stored[0].exists()
        assert session.get(
            f"{base_url}/api/desktop/contracts/attachments/{attachment_id}/download"
        ).status_code == 404
        contract_file = b"second attachment for contract deletion"
        second_upload = session.post(
            detail_url,
            json={"filename": "second.pdf", "data_base64": base64.b64encode(contract_file).decode("ascii")},
        )
        assert second_upload.status_code == 201
        second_stored = list((tmp_path / "Kullanicilar" / "contract_docs" / "tenant-1").iterdir())
        assert len(second_stored) == 1
        other_tenant_root = tmp_path / "Kullanicilar" / "contract_docs" / "tenant-2"
        other_tenant_root.mkdir(parents=True)
        other_tenant_file = other_tenant_root / "unrelated.pdf"
        other_tenant_file.write_bytes(b"other tenant attachment")
        contract_delete = session.post(
            f"{base_url}/api/desktop/table/contracts",
            json={"id": contract_id, "_action": "delete"},
        )
        assert contract_delete.status_code == 200
        assert contract_delete.json()["attachments_deleted"] == 1
        assert session.get(detail_url).status_code == 404
        assert not second_stored[0].exists()
        assert other_tenant_file.read_bytes() == b"other tenant attachment"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_contract_attachment_validation_rejects_invalid_size_or_path():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE contracts(id INTEGER PRIMARY KEY,title TEXT,customer_id INTEGER,contract_type TEXT,description TEXT,is_deleted INTEGER)"
    )
    conn.execute(
        "INSERT INTO contracts(id,title,description,is_deleted) VALUES(1,'Contract','Details',0)"
    )
    conn.commit()
    web_main.set_tenant_context({"id": "tenant-test"})
    try:
        for payload, expected in (
            ({"filename": "report.txt", "data_base64": "not base64!"}, "File data is invalid"),
            ({"filename": "large.bin", "data_base64": base64.b64encode(b"x" * (web_main.MAX_CONTRACT_ATTACHMENT_BYTES + 1)).decode("ascii")}, "exceeds the 25 MB limit"),
        ):
            try:
                web_main.desktop_upload_contract_attachment(conn, 1, payload)
            except ValueError as error:
                assert expected in str(error)
            else:
                raise AssertionError("Invalid contract attachment was accepted")
    finally:
        web_main.clear_tenant_context()
        conn.close()


def test_desktop_legacy_contract_attachment_is_migrated_into_tenant_storage(monkeypatch, tmp_path):
    legacy_root = tmp_path / "legacy" / "contract_docs"
    legacy_root.mkdir(parents=True)
    legacy_file = legacy_root / "legacy.pdf"
    legacy_file.write_bytes(b"legacy tenant contract")
    monkeypatch.setattr(web_main, "ROOT", tmp_path / "legacy" / "Web_Arayuzu")
    monkeypatch.setattr(web_main, "TENANT_ROOT", tmp_path / "tenant-data")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE contracts(id INTEGER PRIMARY KEY,title TEXT,customer_id INTEGER,contract_type TEXT,description TEXT,is_deleted INTEGER)")
    conn.execute("INSERT INTO contracts(id,title,is_deleted) VALUES(1,'Contract',0)")
    conn.execute("CREATE TABLE contract_attachments(id INTEGER PRIMARY KEY,contract_id INTEGER,file_path TEXT,filename TEXT,created_at TEXT)")
    conn.execute("INSERT INTO contract_attachments(id,contract_id,file_path,filename) VALUES(1,1,'contract_docs/legacy.pdf','legacy.pdf')")
    web_main.set_tenant_context({"id": "tenant-legacy", "db_filename": "tenant.db"})
    try:
        details = web_main.desktop_contract_detail(conn, 1)
        assert details["attachments"][0]["available"] is True
        migrated = Path(conn.execute("SELECT file_path FROM contract_attachments WHERE id=1").fetchone()[0])
        assert migrated.parent == tmp_path / "tenant-data" / "contract_docs" / "tenant-legacy"
        assert migrated.read_bytes() == legacy_file.read_bytes()
        assert legacy_file.exists()
    finally:
        web_main.clear_tenant_context()
        conn.close()
