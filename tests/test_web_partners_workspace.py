import base64
import sqlite3
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


ROOT = Path(__file__).resolve().parents[1]


def test_partner_workspace_web_view_exposes_filters_and_shipment_tabs():
    web = (ROOT / "Web_Arayuzu/web/partners-reference.js").read_text(encoding="utf-8")
    desktop_ui = (ROOT / "src/ui/pages/_cpp_ui_mixin.py").read_text(encoding="utf-8")

    assert 'if (page !== "partners") return renderBeforePartnerWorkspace();' in web
    assert 'apiFetch(`/api/desktop/partners/workspace${query}`)' in web
    assert 'id="partnerWorkspaceSearch"' in web
    assert 'id="partnerWorkspaceService"' in web
    assert 'id="partnerWorkspaceCommission"' in web
    assert 'data-partner-workspace-tab="${tab.id}"' in web
    assert 'data-partner-id="${esc(partner.id)}"' in web
    assert r'.replace(/[\u0300-\u036f]/g, "").replaceAll("\u0131", "i")' in web
    assert 'row.serial_no || row.external_ref_no' in web
    assert 'id="partnerShipmentAdd"' in web
    assert 'data-partner-shipment="${esc(row.id)}"' in web
    for field in (
        "customer_name", "product_name", "serial_no", "issue_summary", "shipment_reason",
        "external_ref_no", "outbound_tracking_no", "return_tracking_no", "partner_cost",
        "customer_price", "quote_status", "quote_amount", "approval_status", "sent_at",
        "contract_type", "sla_level", "accessories", "cost_responsibility", "return_qc",
        "cosmetic_status", "missing_parts", "returned_at", "currency", "notes",
    ):
        assert f'"{field}"' in web
    assert 'apiFetch("/api/desktop/partners/shipments"' in web
    assert 'row.oncontextmenu = (event) => showPartnerShipmentMenu(event, shipment)' in web
    assert '["Ac / Duzenle", "edit"]' in web
    assert '["Belge Merkezi", "documents"]' in web
    assert '["Excel Disa Aktar", "export"]' in web
    assert 'window.openDesktopDocumentsCenter = showDocumentsCenter' in (
        ROOT / "Web_Arayuzu/web/external-tracking-reference.js"
    ).read_text(encoding="utf-8")
    assert '["Belgeler", "shipment-documents"]' in web
    assert '["Partner Finans", "finance"]' in web
    assert 'function openPartnerDocuments(shipment = null)' in web
    assert 'function openPartnerFinanceDialog()' in web
    assert 'id="partnerFinanceSave"' in web
    assert 'apiFetch("/api/desktop/partners/finance"' in web
    assert 'function openPartnerNotesDialog()' in web
    assert 'apiFetch("/api/desktop/partners/notes"' in web
    assert '{ id: "notes", label: "Notlar" }' in web
    assert 'function openPartnerProfileDialog(partner = null)' in web
    assert 'id="partnerAdd"' in web
    assert 'id="partnerProfileEdit"' in web
    assert 'apiFetch("/api/desktop/partners/profile"' in web
    assert 'self.btn_add_partner = QPushButton("+ Yeni Ortak")' in desktop_ui
    assert 'data-partner-document-delete="${esc(item.id)}"' in web
    assert 'action: "upload", partner_id: partner.id' in web
    assert 'anchor.href = selected.url' in web
    assert 'data-partner-document-delete="${esc(item.id)}"' in web
    assert 'self.partner_tabs.addTab(self.tab_active, "Aktif Gonderiler")' in desktop_ui
    assert 'self.partner_tabs.addTab(self.tab_history, "Gecmis")' in desktop_ui
    assert 'self.partner_tabs.addTab(self.tab_timeline, "Zaman Cizelgesi")' in desktop_ui
    assert 'self.partner_tabs.addTab(self.tab_trends, "Trendler")' in desktop_ui
    assert '{ id: "timeline", label: "Zaman Cizelgesi" }' in web
    assert '{ id: "trends", label: "Trendler" }' in web
    assert 'partnerAnalyticsTable("timeline")' in web
    assert 'partnerAnalyticsTable("trends")' in web


def test_partner_workspace_api_filters_partners_and_scopes_shipments(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        customer_columns = {row[1] for row in conn.execute("PRAGMA table_info(customers)")}
        if "is_partner" not in customer_columns:
            conn.execute("ALTER TABLE customers ADD COLUMN is_partner INTEGER DEFAULT 0")
        conn.executemany(
            "INSERT INTO customers(name, type, is_partner) VALUES(?,?,?)",
            [
                ("Marked partner", "Kurumsal", 1),
                ("Dealer partner", "bayi", 0),
                ("Supplier partner", "tedarik\u00e7i", 0),
                ("Ordinary customer", "Bireysel", 0),
            ],
        )
        partner_id = conn.execute(
            "SELECT id FROM customers WHERE name='Marked partner'"
        ).fetchone()[0]
        conn.execute(
            "CREATE TABLE partner_shipments (id INTEGER PRIMARY KEY, partner_id INTEGER, "
            "partner_name TEXT, customer_name TEXT, product_name TEXT, status TEXT, "
            "sent_at TEXT, created_at TEXT, updated_at TEXT)"
        )
        conn.execute(
            "INSERT INTO partner_shipments VALUES(?,?,?,?,?,?,?,?,?)",
            (71, partner_id, "Marked partner", "Customer", "Device", "Serviste", "2026-10-14", "2026-10-14", "2026-10-14"),
        )
        conn.execute("ALTER TABLE partner_shipments ADD COLUMN partner_cost REAL DEFAULT 0")
        conn.execute("ALTER TABLE partner_shipments ADD COLUMN customer_price REAL DEFAULT 0")
        conn.execute("ALTER TABLE partner_shipments ADD COLUMN currency TEXT DEFAULT 'TRY'")
        conn.execute("ALTER TABLE partner_shipments ADD COLUMN serial_no TEXT")
        conn.execute("UPDATE partner_shipments SET partner_cost=500, customer_price=750, serial_no='SN-71' WHERE id=71")
        conn.execute(
            "CREATE TABLE partner_timeline (id INTEGER PRIMARY KEY, partner_id INTEGER, shipment_id INTEGER, "
            "event_type TEXT, detail TEXT, event_date TEXT, created_at TEXT)"
        )
        conn.execute(
            "INSERT INTO partner_timeline VALUES(1,?,?,?,?,?,?)",
            (partner_id, 71, "shipment_saved", "Device | status=Serviste", "2026-10-14", "2026-10-14"),
        )

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anonymous = requests.get(f"{base_url}/api/desktop/partners/workspace", timeout=5)
        assert anonymous.status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
            timeout=5,
        )
        assert login.status_code == 200
        listing = session.get(f"{base_url}/api/desktop/partners/workspace", timeout=5)
        assert listing.status_code == 200
        listed_names = {item["name"] for item in listing.json()["partners"]}
        assert listed_names == {"Marked partner", "Dealer partner", "Supplier partner"}
        assert listing.json()["shipments"] == []

        selected = session.get(
            f"{base_url}/api/desktop/partners/workspace?partner_id={partner_id}",
            timeout=5,
        )
        assert selected.status_code == 200
        body = selected.json()
        assert body["selected_partner"]["id"] == partner_id
        assert [item["id"] for item in body["shipments"]] == [71]
        assert body["timeline"] == [{
            "event_date": "2026-10-14", "event_type": "shipment_saved",
            "detail": "Device | status=Serviste", "shipment_id": 71,
        }]
        assert body["trends"] == [{
            "period": "2026-10", "shipment_count": 1, "completed_count": 0,
            "partner_cost": 500.0, "customer_price": 750.0, "quote_amount": 0.0,
        }]
        finance_initial = session.get(f"{base_url}/api/desktop/partners/finance?partner_id={partner_id}", timeout=5)
        assert finance_initial.status_code == 200, finance_initial.text
        assert finance_initial.json()["summary"] == {
            "total_cost": 500.0, "total_paid": 0.0, "balance": 500.0, "customer_total": 750.0,
        }
        payment = session.post(
            f"{base_url}/api/desktop/partners/finance",
            json={
                "partner_id": partner_id, "shipment_id": 71, "amount": 100,
                "payment_method": "Havale / EFT", "description": "First payment",
                "invoice_no": "INV-71", "entry_date": "2026-10-14", "invoice_date": "2026-10-14",
            },
            timeout=5,
        )
        assert payment.status_code == 201
        finance = session.get(
            f"{base_url}/api/desktop/partners/finance?partner_id={partner_id}", timeout=5
        ).json()
        assert finance["summary"] == {
            "total_cost": 500.0, "total_paid": 100.0, "balance": 400.0, "customer_total": 750.0,
        }
        assert finance["entries"][0]["invoice_no"] == "INV-71"
        assert finance["reconciliation"][0]["paid"] == 100.0
        invalid_payment = session.post(
            f"{base_url}/api/desktop/partners/finance",
            json={"partner_id": partner_id, "amount": 0}, timeout=5,
        )
        assert invalid_payment.status_code == 400
        wrong_partner_payment = session.post(
            f"{base_url}/api/desktop/partners/finance",
            json={"partner_id": listing.json()["partners"][1]["id"], "shipment_id": 71, "amount": 10},
            timeout=5,
        )
        assert wrong_partner_payment.status_code == 404

        notes_url = f"{base_url}/api/desktop/partners/notes"
        assert requests.get(notes_url, params={"partner_id": partner_id}, timeout=5).status_code == 401
        assert session.get(notes_url, params={"partner_id": partner_id}, timeout=5).json()["notes"] == []

        profile_url = f"{base_url}/api/desktop/partners/profile"
        assert requests.post(profile_url, json={"name": "Anonymous"}, timeout=5).status_code == 401
        profile = session.post(
            profile_url,
            json={
                "name": "Web Created Partner", "type": "Tedarikci", "phone": "555-0110",
                "email": "created@example.com", "city": "Ankara", "service_type": "Camera Repair",
                "commission_rate": 12.5, "contract_type": "Premium SLA", "sla_level": "Ayni Gun",
            },
            timeout=5,
        )
        assert profile.status_code == 201, profile.text
        new_partner_id = profile.json()["id"]
        profile_update = session.post(
            profile_url,
            json={"id": new_partner_id, "name": "Web Partner Updated", "type": "Bayi", "commission_rate": 15.25},
            timeout=5,
        )
        assert profile_update.status_code == 200, profile_update.text
        with sqlite3.connect(tenant_path) as conn:
            updated_partner = conn.execute(
                "SELECT name,type,is_partner,commission_rate FROM customers WHERE id=?", (new_partner_id,)
            ).fetchone()
            ordinary_id = conn.execute(
                "SELECT id FROM customers WHERE name='Ordinary customer'"
            ).fetchone()[0]
        assert updated_partner == ("Web Partner Updated", "Bayi", 1, 15.25)
        assert session.post(
            profile_url,
            json={"id": ordinary_id, "name": "Ordinary customer"},
            timeout=5,
        ).status_code == 404
        assert session.post(
            profile_url,
            json={"id": new_partner_id, "name": "Invalid commission", "commission_rate": 100.1},
            timeout=5,
        ).status_code == 400
        created_note = session.post(
            notes_url,
            json={"partner_id": partner_id, "note_type": "Genel Not", "title": "Service follow-up", "content": "Initial note"},
            timeout=5,
        )
        assert created_note.status_code == 201, created_note.text
        note_id = created_note.json()["id"]
        saved_notes = session.get(notes_url, params={"partner_id": partner_id}, timeout=5).json()["notes"]
        assert len(saved_notes) == 1
        assert {key: saved_notes[0][key] for key in ("id", "note_type", "title", "content")} == {
            "id": note_id, "note_type": "Genel Not", "title": "Service follow-up", "content": "Initial note",
        }
        updated_note = session.post(
            notes_url,
            json={"partner_id": partner_id, "id": note_id, "note_type": "SMS", "title": "Updated follow-up", "content": "Revised note"},
            timeout=5,
        )
        assert updated_note.status_code == 200
        other_partner_id = next(
            item["id"] for item in listing.json()["partners"] if item["name"] == "Dealer partner"
        )
        cross_partner_note = session.post(
            notes_url,
            json={"action": "delete", "partner_id": other_partner_id, "note_id": note_id},
            timeout=5,
        )
        assert cross_partner_note.status_code == 404
        deleted_note = session.post(
            notes_url, json={"action": "delete", "partner_id": partner_id, "note_id": note_id}, timeout=5
        )
        assert deleted_note.status_code == 200
        assert session.get(notes_url, params={"partner_id": partner_id}, timeout=5).json()["notes"] == []

        unauthenticated_save = requests.post(
            f"{base_url}/api/desktop/partners/shipments",
            json={"partner_id": partner_id, "customer_name": "C", "product_name": "P"},
            timeout=5,
        )
        assert unauthenticated_save.status_code == 401
        assert requests.get(
            f"{base_url}/api/desktop/partners/documents?partner_id={partner_id}", timeout=5
        ).status_code == 401
        shipment_payload = {
            "partner_id": partner_id,
            "customer_name": "New customer",
            "product_name": "New device",
            "serial_no": "SN-22",
            "status": "Serviste",
            "partner_cost": 120.5,
            "customer_price": 180,
            "quote_amount": 100,
            "sent_at": "2026-10-14",
            "returned_at": "2026-10-14",
        }
        created = session.post(
            f"{base_url}/api/desktop/partners/shipments", json=shipment_payload, timeout=5
        )
        assert created.status_code == 201
        created_id = created.json()["id"]
        shipment_payload.update({"id": created_id, "status": "Geri geldi"})
        updated = session.post(
            f"{base_url}/api/desktop/partners/shipments", json=shipment_payload, timeout=5
        )
        assert updated.status_code == 200
        with sqlite3.connect(tenant_path) as conn:
            saved = conn.execute(
                "SELECT customer_name, product_name, status, partner_cost FROM partner_shipments WHERE id=?",
                (created_id,),
            ).fetchone()
            timeline = conn.execute(
                "SELECT COUNT(*) FROM partner_timeline WHERE shipment_id=? AND event_type='shipment_saved'",
                (created_id,),
            ).fetchone()[0]
        assert saved == ("New customer", "New device", "Geri geldi", 120.5)
        assert timeline == 2
        wrong_partner_update = session.post(
            f"{base_url}/api/desktop/partners/shipments",
            json={**shipment_payload, "partner_id": listing.json()["partners"][1]["id"]},
            timeout=5,
        )
        assert wrong_partner_update.status_code == 404
        invalid = session.post(
            f"{base_url}/api/desktop/partners/shipments",
            json={**shipment_payload, "id": None, "customer_name": "", "partner_cost": -1},
            timeout=5,
        )
        assert invalid.status_code == 400

        shipment_document_query = f"?partner_id={partner_id}&shipment_id=71"
        empty_documents = session.get(
            f"{base_url}/api/desktop/partners/documents{shipment_document_query}", timeout=5
        )
        assert empty_documents.status_code == 200
        assert empty_documents.json()["documents"] == []
        file_bytes = b"partner shipment document"
        upload = session.post(
            f"{base_url}/api/desktop/partners/documents",
            json={
                "action": "upload", "partner_id": partner_id, "shipment_id": 71,
                "filename": "shipment-proof.pdf", "data_base64": base64.b64encode(file_bytes).decode("ascii"),
            },
            timeout=5,
        )
        assert upload.status_code == 201
        document_id = upload.json()["id"]
        listed_documents = session.get(
            f"{base_url}/api/desktop/partners/documents{shipment_document_query}", timeout=5
        )
        document = listed_documents.json()["documents"][0]
        assert document["id"] == document_id
        assert document["available"] is True
        assert document["category"] == "Sevk Belgesi"
        downloaded = session.get(f"{base_url}{document['url']}", timeout=5)
        assert downloaded.status_code == 200
        assert downloaded.content == file_bytes
        document_center = session.get(f"{base_url}/api/desktop/documents/center", timeout=5)
        partner_document = next(
            item for item in document_center.json()["rows"]
            if item["key"] == f"partner-document:{document_id}"
        )
        assert partner_document["available"] is True
        assert partner_document["url"] == document["url"]
        with sqlite3.connect(tenant_path) as conn:
            stored_file = Path(conn.execute(
                "SELECT file_path FROM partner_documents WHERE id=?", (document_id,)
            ).fetchone()[0])
        wrong_shipment = session.get(
            f"{base_url}/api/desktop/partners/documents?partner_id={partner_id}&shipment_id=9999", timeout=5
        )
        assert wrong_shipment.status_code == 404
        cross_partner_upload = session.post(
            f"{base_url}/api/desktop/partners/documents",
            json={
                "action": "upload", "partner_id": listing.json()["partners"][1]["id"],
                "shipment_id": 71, "filename": "blocked.txt",
                "data_base64": base64.b64encode(b"x").decode("ascii"),
            },
            timeout=5,
        )
        assert cross_partner_upload.status_code == 404
        removed = session.post(
            f"{base_url}/api/desktop/partners/documents",
            json={"action": "delete", "partner_id": partner_id, "id": document_id},
            timeout=5,
        )
        assert removed.status_code == 200
        assert not stored_file.exists()
        missing_download = session.get(f"{base_url}{document['url']}", timeout=5)
        assert missing_download.status_code == 404
        with sqlite3.connect(tenant_path) as conn:
            conn.execute(
                "INSERT INTO partner_documents(partner_id,shipment_id,title,category,file_path,added_at) "
                "VALUES(?,?,?,?,?,?)",
                (partner_id, 71, "legacy.pdf", "Sevk Belgesi", "C:/legacy/partner.pdf", "2026-10-14"),
            )
        legacy = session.get(
            f"{base_url}/api/desktop/partners/documents{shipment_document_query}", timeout=5
        ).json()["documents"][0]
        assert legacy["available"] is False
        assert legacy["url"] == ""
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
