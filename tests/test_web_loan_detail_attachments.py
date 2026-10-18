from pathlib import Path
import base64
import sqlite3

from Web_Arayuzu import Main as web_main


def _loan_db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE loans (id INTEGER PRIMARY KEY);
        CREATE TABLE loan_attachments (
            id INTEGER PRIMARY KEY,
            loan_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            notes TEXT,
            upload_date TEXT
        );
        INSERT INTO loans(id) VALUES (5);
        INSERT INTO loan_attachments(id, loan_id, file_name, file_path, file_type, notes, upload_date)
        VALUES (8, 5, 'agreement.pdf', 'C:/private/agreement.pdf', 'PDF', 'Signed', '2026-10-17');
        """
    )
    conn.commit()
    conn.close()


def test_loan_attachment_route_returns_metadata_without_local_path(tmp_path, monkeypatch):
    database = tmp_path / "tenant.db"
    _loan_db(database)

    def connect():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(web_main, "db_connect", connect)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/loans/5/attachments"
    handler.headers = {}
    handler.current_user = lambda: {"id": 2, "role": "User", "_tenant_id": "tenant-a"}
    replies = []
    handler.send_json = lambda payload, status=200: replies.append((payload, status))

    handler.do_GET()

    payload, status = replies[0]
    assert status == 200
    assert payload["count"] == 1
    assert payload["rows"] == [
        {
            "id": 8,
            "loan_id": 5,
            "file_name": "agreement.pdf",
            "file_type": "PDF",
            "notes": "Signed",
            "upload_date": "2026-10-17",
        }
    ]
    assert "file_path" not in payload["rows"][0]


def test_loan_attachment_route_rejects_invalid_loan_id(monkeypatch):
    monkeypatch.setattr(web_main, "db_connect", lambda: None)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/loans/../attachments"
    handler.headers = {}
    handler.current_user = lambda: {"id": 2, "role": "User", "_tenant_id": "tenant-a"}
    replies = []
    handler.send_json = lambda payload, status=200: replies.append((payload, status))

    handler.do_GET()

    assert replies == [({"error": "Invalid loan attachment route"}, 400)]


def test_loan_attachment_web_workflow_uses_safe_metadata_endpoint():
    source = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = source.index("function openLoanDetailManifestDialog()")
    end = source.index("function openManifestDialog(", start)
    workflow = source[start:end]
    assert 'apiFetch("/api/desktop/loans/"+encodeURIComponent(loan.id)+"/attachments")' in workflow


def test_loan_attachment_route_requires_authentication(tmp_path, monkeypatch):
    database = tmp_path / "tenant.db"
    _loan_db(database)

    def connect():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(web_main, "db_connect", connect)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/loans/5/attachments"
    handler.headers = {}
    handler.current_user = lambda: None
    replies = []
    handler.send_json = lambda payload, status=200: replies.append((payload, status))

    handler.do_GET()

    assert replies[0][1] == 401
    assert replies[0][0]["code"] == "AUTH_REQUIRED"


def test_loan_attachment_upload_stays_inside_active_tenant(tmp_path, monkeypatch):
    database = tmp_path / "tenant.db"
    _loan_db(database)
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-a")
    monkeypatch.setattr(web_main, "TENANT_ROOT", tmp_path / "tenants")

    saved = web_main.desktop_upload_loan_attachments(
        conn,
        5,
        [{
            "filename": r"..\private\agreement.pdf",
            "file_type": "Contract",
            "notes": "Tenant document",
            "data_base64": base64.b64encode(b"%PDF-fixture").decode("ascii"),
        }],
    )

    row = conn.execute("SELECT file_name,file_path FROM loan_attachments WHERE id=?", (saved[0]["id"],)).fetchone()
    stored = Path(row["file_path"]).resolve()
    tenant_root = (tmp_path / "tenants" / "loan_docs" / "tenant-a").resolve()
    assert stored.parent == tenant_root
    assert stored.read_bytes() == b"%PDF-fixture"
    assert row["file_name"] == "agreement.pdf"
    assert "file_path" not in saved[0]
    conn.close()


def test_loan_attachment_download_serves_only_active_tenant_files(tmp_path, monkeypatch):
    database = tmp_path / "tenant.db"
    _loan_db(database)
    tenant_root = tmp_path / "tenants" / "loan_docs" / "tenant-a"
    tenant_root.mkdir(parents=True)
    stored = tenant_root / "stored.pdf"
    stored.write_bytes(b"%PDF-fixture")
    conn = sqlite3.connect(database)
    conn.execute("UPDATE loan_attachments SET file_path=? WHERE id=8", (str(stored),))
    conn.commit()
    conn.close()

    def connect():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(web_main, "db_connect", connect)
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-a")
    monkeypatch.setattr(web_main, "TENANT_ROOT", tmp_path / "tenants")
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/loans/attachments/8/download"
    handler.headers = {}
    handler.current_user = lambda: {"id": 2, "role": "User", "_tenant_id": "tenant-a"}
    replies = []
    handler.send_json = lambda payload, status=200: replies.append(("json", payload, status))
    handler.send_bytes = lambda payload, content_type, disposition="": replies.append(("bytes", payload, content_type, disposition))

    handler.do_GET()

    assert replies == [("bytes", b"%PDF-fixture", "application/octet-stream", 'attachment; filename="agreement.pdf"')]


def test_loan_creation_api_requires_authentication():
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/loans/create"
    handler.headers = {"Content-Length": "0"}
    handler.current_user = lambda: None
    replies = []
    handler.send_json = lambda payload, status=200: replies.append((payload, status))

    handler.do_POST()

    assert replies[0][1] == 401
    assert replies[0][0]["code"] == "AUTH_REQUIRED"


def test_loan_creation_api_saves_taxed_installments_and_tenant_document(tmp_path, monkeypatch):
    import src.database as database_module

    captured = {"loans": [], "installments": []}

    class FakeDatabase:
        def __init__(self, *args, **kwargs):
            self.conn = sqlite3.connect(":memory:")
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self.conn.executescript(
                "CREATE TABLE loans(id INTEGER PRIMARY KEY, bank_name TEXT, amount REAL, interest_rate REAL, term_months INTEGER, start_date TEXT, total_payment REAL, description TEXT, loan_type TEXT, loan_title TEXT, kkdf_rate REAL, bsmv_rate REAL);"
                "CREATE TABLE loan_installments(id INTEGER PRIMARY KEY, loan_id INTEGER, installment_no INTEGER, due_date TEXT, total_amount REAL, principal_part REAL, interest_part REAL, status TEXT);"
                "CREATE TABLE loan_attachments(id INTEGER PRIMARY KEY AUTOINCREMENT, loan_id INTEGER NOT NULL, file_name TEXT NOT NULL, file_path TEXT NOT NULL, file_type TEXT, notes TEXT, upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
            )

        def add_loan(self, data):
            cursor = self.conn.execute(
                "INSERT INTO loans(bank_name,amount,interest_rate,term_months,start_date,total_payment,description,loan_type,loan_title,kkdf_rate,bsmv_rate) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (data["bank_name"], data["amount"], data["interest_rate"], data["term_months"], data["start_date"], data["total_payment"], data["description"], data["loan_type"], data["loan_title"], data["kkdf_rate"], data["bsmv_rate"]),
            )
            self.conn.commit()
            captured["loans"].append(self.conn.execute("SELECT * FROM loans WHERE id=?", (cursor.lastrowid,)).fetchone())
            return cursor.lastrowid

        def add_loan_installment(self, data):
            self.conn.execute(
                "INSERT INTO loan_installments(loan_id,installment_no,due_date,total_amount,principal_part,interest_part,status) VALUES(?,?,?,?,?,?,?)",
                (data["loan_id"], data["installment_no"], data["due_date"], data["amount"], data["amount"], 0, "Bekliyor"),
            )
            self.conn.commit()
            captured["installments"].append(data.copy())

        def close(self):
            self.conn.close()

    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-a")
    monkeypatch.setattr(web_main, "TENANT_ROOT", tmp_path / "tenants")
    payload = {
        "bank_name": "Audit Bank (AB)",
        "loan_type": "Taksitli Ticari Kredi",
        "loan_title": "Equipment loan",
        "amount": 1000,
        "interest_rate": 12,
        "term_months": 2,
        "start_date": "2026-01-31",
        "kkdf_rate": 1.5,
        "bsmv_rate": 10,
        "notes": "Fixture note",
        "attachments": [{"filename": "agreement.pdf", "file_type": "Contract", "data_base64": base64.b64encode(b"%PDF-fixture").decode("ascii")}],
    }
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/loans/create"
    handler.headers = {"Content-Length": "100"}
    handler.current_user = lambda: {"id": 2, "role": "Admin", "_tenant_id": "tenant-a"}
    handler.read_json = lambda: payload
    replies = []
    handler.send_json = lambda body, status=200: replies.append((body, status))

    handler.do_POST()

    response, status = replies[0]
    assert status == 201, response
    assert response["loan_id"] == 1
    assert response["attachments"][0]["file_name"] == "agreement.pdf"
    assert len(captured["installments"]) == 2
    assert captured["installments"][0]["due_date"] == "2026-02-28"
    assert captured["loans"][0]["loan_title"] == "Equipment loan"
    assert captured["loans"][0]["kkdf_rate"] == 1.5
    assert captured["loans"][0]["bsmv_rate"] == 10
    assert captured["loans"][0]["total_payment"] > 1000
    stored = next((tmp_path / "tenants" / "loan_docs" / "tenant-a").iterdir())
    assert stored.read_bytes() == b"%PDF-fixture"




def test_bank_catalog_api_returns_loan_upload_feature_flag(tmp_path, monkeypatch):
    import src.utils.bank_helper as bank_helper

    database = tmp_path / "tenant.db"
    conn = sqlite3.connect(database)
    conn.execute("CREATE TABLE internal_settings(key TEXT PRIMARY KEY,value TEXT)")
    conn.execute("INSERT INTO internal_settings(key,value) VALUES(?,?)", ("feature_wizard_upload_active", "0"))
    conn.execute("CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)")
    conn.execute("INSERT INTO settings(key,value) VALUES(?,?)", ("currency", "EUR"))
    conn.commit()
    conn.close()

    def connect():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    class Catalog:
        def get_all_banks(self):
            return [{"name": "Audit Bank", "shortName": "AB", "eftCode": "0012", "swift": "AUDITTR1", "type": "Commercial"}]

    monkeypatch.setattr(web_main, "db_connect", connect)
    monkeypatch.setattr(bank_helper, "get_bank_helper", lambda: Catalog())
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/banks/catalog"
    handler.headers = {}
    handler.current_user = lambda: {"id": 2, "role": "User", "_tenant_id": "tenant-a"}
    replies = []
    handler.send_json = lambda payload, status=200: replies.append((payload, status))

    handler.do_GET()

    assert replies[0][1] == 200
    assert replies[0][0]["document_upload_enabled"] is False
    assert replies[0][0]["banks"][0]["eftCode"] == "0012"
    assert replies[0][0]["currency"] == "EUR"
