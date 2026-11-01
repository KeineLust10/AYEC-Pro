import io
import base64
import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests
from openpyxl import load_workbook
from pypdf import PdfReader

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_stock_photo_upload_is_tenant_scoped_and_only_deletes_managed_paths(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)
    payload = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    )

    result = web_main.desktop_stock_photo_upload(
        base64.b64encode(payload).decode("ascii"), "product.png"
    )
    saved_path = web_main.Path(result["photo_path"]).resolve()
    managed_folder = (tenant_path.parent / "stock_photos").resolve()

    assert saved_path.is_file()
    assert saved_path.parent == managed_folder
    assert saved_path.name.startswith("stock_")
    assert result["filename"] == "product.png"
    assert web_main.desktop_stock_photo_delete_managed(str(tenant_path)) is False
    assert saved_path.is_file()
    assert web_main.desktop_stock_photo_delete_managed(result["photo_path"]) is True
    assert not saved_path.exists()


def test_stock_photo_upload_rejects_invalid_or_unsupported_image_data(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)

    for encoded in ("not-base64", base64.b64encode(b"not an image").decode("ascii")):
        try:
            web_main.desktop_stock_photo_upload(encoded, "payload.bin")
        except ValueError:
            pass
        else:
            raise AssertionError("Unsupported stock photo data was accepted")


def test_stock_photo_roundtrip_persists_to_the_tenant_stock_card(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)
    payload = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    )
    uploaded = web_main.desktop_stock_photo_upload(
        base64.b64encode(payload).decode("ascii"), "roundtrip.png"
    )

    saved = web_main.save_stock_card({
        "name": "Photo Stock",
        "code": "PHOTO-STOCK-1",
        "stock": 0,
        "unit": "Adet",
        "photo_path": uploaded["photo_path"],
    })
    served, content_type = web_main.desktop_stock_photo(saved["id"])

    assert saved["part"]["photo_path"] == uploaded["photo_path"]
    assert served == payload
    assert content_type == "image/png"
    web_main.desktop_stock_photo_delete_managed(uploaded["photo_path"])


def test_stock_card_catalog_metadata_roundtrips_in_the_active_tenant(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)

    saved = web_main.save_stock_card({
        "name": "Metadata Stock",
        "code": "META-STOCK-1",
        "brand": "Audit Brand",
        "stock": 0,
        "unit": "Adet",
        "oem_code": "OEM-01",
        "equivalent_code": "EQ-01",
        "shelf_number": "R-01",
        "compatible_models": "QA Model",
        "description": "Catalog metadata roundtrip",
    })

    assert {
        key: saved["part"][key]
        for key in ("brand", "oem_code", "equivalent_code", "shelf_number", "compatible_models", "description")
    } == {
        "brand": "Audit Brand",
        "oem_code": "OEM-01",
        "equivalent_code": "EQ-01",
        "shelf_number": "R-01",
        "compatible_models": "QA Model",
        "description": "Catalog metadata roundtrip",
    }


def test_stock_photo_route_requires_login_and_reads_only_active_tenant(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    photo_path = tmp_path / "stock-photo.png"
    photo_path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        b"\x1f\x15\xc4\x89\x00\x00\x00\x0bIDATx\xda\x63\xf8\x0f"
        b"\x00\x01\x01\x01\x00\x18\xdd\x8d\xb1\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    with sqlite3.connect(tenant_path) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS parts (id INTEGER PRIMARY KEY, photo_path TEXT, is_deleted INTEGER DEFAULT 0)"
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(parts)")}
        for column, declaration in (
            ("photo_path", "TEXT"), ("is_deleted", "INTEGER DEFAULT 0"),
            ("stock", "REAL DEFAULT 0"), ("purchase_price", "REAL DEFAULT 0"),
            ("currency", "TEXT DEFAULT 'TRY'"), ("name", "TEXT"),
        ):
            if column not in columns:
                connection.execute(f"ALTER TABLE parts ADD COLUMN {column} {declaration}")
        connection.execute(
            "INSERT INTO parts(id,photo_path,is_deleted,stock,purchase_price,currency,name) VALUES(?,?,?,?,?,?,?)",
            (91001, str(photo_path), 0, 4, 3, "TRY", "Test Stock"),
        )
        connection.execute(
            "INSERT INTO parts(id,photo_path,is_deleted,stock,purchase_price,price,currency,name) "
            "VALUES(91002,'',0,2,10,15,'USD','Dollar Stock')"
        )
        connection.execute(
            "INSERT INTO exchange_rates(currency,buying_rate,selling_rate,effective_date,created_at) "
            "VALUES('USD',32,32.5,'2026-10-14','2026-10-14 12:00:00')"
        )

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = f"{base_url}/api/desktop/stock/photo/91001"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.get(endpoint).status_code == 401
        assert anonymous.get(f"{base_url}/api/desktop/stock/export/xlsx").status_code == 401
        assert anonymous.get(f"{base_url}/api/desktop/stock/export/pdf").status_code == 401
        assert anonymous.post(
            f"{base_url}/api/desktop/stock/delete", json={"id": 91001, "password": "operator-test-pass"}
        ).status_code == 401
        assert anonymous.post(
            f"{base_url}/api/desktop/stock/photo/upload", json={"filename": "stock.png", "data": ""}
        ).status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        response = session.get(endpoint)
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "image/png"
        assert response.content == photo_path.read_bytes()
        uploaded = session.post(
            f"{base_url}/api/desktop/stock/photo/upload",
            json={"filename": "tenant-stock.png", "data": base64.b64encode(photo_path.read_bytes()).decode("ascii")},
        )
        assert uploaded.status_code == 201
        photo_path_value = uploaded.json()["photo_path"]
        assert str(tenant_path.parent / "stock_photos") in photo_path_value
        created_stock = session.post(f"{base_url}/api/desktop/table/parts", json={
            "name": "Uploaded Photo Stock", "code": "PHOTO-UPLOAD-1", "currency": "TRY",
            "stock": 0, "photo_path": photo_path_value,
        })
        assert created_stock.status_code == 200
        stock_id = created_stock.json()["id"]
        served_photo = session.get(f"{base_url}/api/desktop/stock/photo/{stock_id}")
        assert served_photo.status_code == 200
        assert served_photo.content == photo_path.read_bytes()
        cleared_stock = session.post(f"{base_url}/api/desktop/table/parts", json={
            "id": stock_id, "_action": "update", "photo_path": "",
        })
        assert cleared_stock.status_code == 200
        removed_photo = session.post(
            f"{base_url}/api/desktop/stock/photo/delete", json={"photo_path": photo_path_value}
        )
        assert removed_photo.status_code == 200
        assert removed_photo.json() == {"ok": True, "deleted": True}
        assert session.get(f"{base_url}/api/desktop/stock/photo/{stock_id}").status_code == 404
        assert session.get(f"{base_url}/api/desktop/stock/photo/99999").status_code == 404
        workbook_response = session.get(f"{base_url}/api/desktop/stock/export/xlsx")
        assert workbook_response.status_code == 200
        assert "spreadsheetml.sheet" in workbook_response.headers["Content-Type"]
        workbook = load_workbook(io.BytesIO(workbook_response.content), read_only=True)
        sheet = workbook.active
        headers = [cell.value for cell in next(sheet.iter_rows(max_row=1))]
        assert sheet.title == "Stok"
        assert "photo_path" not in headers
        assert sheet.max_row >= 2
        assert "D\u00f6viz Kuru" in headers
        assert "Al\u0131\u015f Fiyat\u0131 (TRY)" in headers
        assert "Sat\u0131\u015f Fiyat\u0131 (TRY)" in headers
        assert "Stok De\u011feri (TRY)" in headers
        exported = [dict(zip(headers, row)) for row in sheet.iter_rows(min_row=2, values_only=True)]
        dollar_row = next(row for row in exported if row.get("\u00dcr\u00fcn Ad\u0131") == "Dollar Stock")
        assert dollar_row["D\u00f6viz Kuru"] == 32.5
        assert dollar_row["Al\u0131\u015f Fiyat\u0131 (TRY)"] == 325
        assert dollar_row["Sat\u0131\u015f Fiyat\u0131 (TRY)"] == 487.5
        assert dollar_row["Stok De\u011feri (TRY)"] == 650
        workbook.close()
        pdf_response = session.get(f"{base_url}/api/desktop/stock/export/pdf")
        assert pdf_response.status_code == 200
        assert pdf_response.headers["Content-Type"] == "application/pdf"
        assert pdf_response.content.startswith(b"%PDF-")
        pdf = PdfReader(io.BytesIO(pdf_response.content))
        pdf_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        assert "AYEC Pro - Stok Listesi" in pdf_text
        assert "Test Stock" in pdf_text
        assert "Dollar Stock" in pdf_text
        delete_url = f"{base_url}/api/desktop/stock/delete"
        rejected = session.post(delete_url, json={"id": 91001, "password": "wrong-pass"})
        assert rejected.status_code == 403
        with sqlite3.connect(tenant_path) as connection:
            assert connection.execute("SELECT is_deleted FROM parts WHERE id=91001").fetchone()[0] == 0
        deleted = session.post(delete_url, json={"id": 91001, "password": "operator-test-pass"})
        assert deleted.status_code == 200
        deletion = deleted.json()
        assert deletion["ok"] is True and deletion["id"] == 91001
        assert deletion["stock"] == 4 and deletion["refund"] == 12
        assert deletion["currency"] == "TRY"
        assert deletion["movement_id"] > 0 and deletion["finance_id"] > 0
        assert deletion["finance_amount"] == 12
        assert deletion["finance_original_amount"] == 12
        assert deletion["finance_try_equivalent"] == 12
        with sqlite3.connect(tenant_path) as connection:
            assert connection.execute("SELECT is_deleted FROM parts WHERE id=91001").fetchone()[0] == 1
            movement = connection.execute(
                "SELECT amount,new_stock FROM stock_movements WHERE part_id=91001 AND movement_type=?",
                ("\u00c7\u0131k\u0131\u015f (Silindi)",),
            ).fetchone()
            assert movement == (4, 0)
            assert connection.execute(
                "SELECT COUNT(*) FROM accounting WHERE category=? AND description LIKE ?",
                ("Stok \u0130ptali / Silinme", "%Test Stock%"),
            ).fetchone()[0] == 1
        deleted_dollar = session.post(delete_url, json={"id": 91002, "password": "operator-test-pass"})
        assert deleted_dollar.status_code == 200
        dollar_deletion = deleted_dollar.json()
        assert dollar_deletion["currency"] == "USD"
        assert dollar_deletion["refund"] == 20
        assert dollar_deletion["finance_original_amount"] == 20
        assert dollar_deletion["finance_amount"] == dollar_deletion["finance_try_equivalent"]
        assert dollar_deletion["finance_exchange_rate"] > 0
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_stock_purchase_expense_uses_a_valid_tenant_bank_account(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)
    with sqlite3.connect(tenant_path) as connection:
        cursor = connection.execute(
            "INSERT INTO bank_accounts(bank_name,is_active,is_deleted) VALUES(?,1,0)",
            ("Test Bank",),
        )
        bank_id = cursor.lastrowid

    saved = web_main.save_stock_card({
        "name": "Banked Stock", "code": "BANK-STOCK-1", "stock": 2,
        "purchase_price": 10, "bank_account_id": bank_id,
    })
    with sqlite3.connect(tenant_path) as connection:
        expense = connection.execute(
            "SELECT bank_account_id,payment_method FROM accounting WHERE id=?",
            (saved["finance_id"],),
        ).fetchone()
    assert expense == (bank_id, "Banka/Kasa")
    assert saved["finance_amount"] == 20
    assert saved["bank_account_id"] == bank_id
    with sqlite3.connect(tenant_path) as connection:
        balance = connection.execute("SELECT current_balance FROM bank_accounts WHERE id=?", (bank_id,)).fetchone()[0]
    assert balance == -20
    assert saved["bank_account_balance"] == -20


def test_stock_purchase_rejects_inactive_bank_account_before_saving(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)
    with sqlite3.connect(tenant_path) as connection:
        cursor = connection.execute(
            "INSERT INTO bank_accounts(bank_name,is_active,is_deleted) VALUES(?,0,0)",
            ("Inactive Bank",),
        )
        bank_id = cursor.lastrowid

    try:
        web_main.save_stock_card({
            "name": "Rejected Stock", "code": "BANK-STOCK-2", "stock": 1,
            "purchase_price": 5, "bank_account_id": bank_id,
        })
    except ValueError:
        pass
    else:
        raise AssertionError("An inactive bank account was accepted")
    with sqlite3.connect(tenant_path) as connection:
        part_count = connection.execute(
            "SELECT COUNT(*) FROM parts WHERE code='BANK-STOCK-2'"
        ).fetchone()[0]
    assert part_count == 0


def test_stock_quantity_edit_records_to_the_selected_purchase_account(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)
    with sqlite3.connect(tenant_path) as connection:
        first = connection.execute(
            "INSERT INTO bank_accounts(bank_name,is_active,is_deleted) VALUES(?,1,0)",
            ("First Bank",),
        ).lastrowid
        second = connection.execute(
            "INSERT INTO bank_accounts(bank_name,is_active,is_deleted) VALUES(?,1,0)",
            ("Second Bank",),
        ).lastrowid

    saved = web_main.save_stock_card({
        "name": "Editable Stock", "code": "BANK-STOCK-EDIT", "stock": 2,
        "purchase_price": 10, "bank_account_id": first,
    })
    updated = web_main.save_stock_card({
        "id": saved["id"], "name": "Editable Stock", "code": "BANK-STOCK-EDIT",
        "stock": 3, "purchase_price": 10, "bank_account_id": second,
    })
    assert updated["finance_id"] != saved["finance_id"]
    assert updated["bank_account_id"] == second
    with sqlite3.connect(tenant_path) as connection:
        expense = connection.execute(
            "SELECT bank_account_id,payment_method FROM accounting WHERE id=?",
            (updated["finance_id"],),
        ).fetchone()
    assert expense == (second, "Banka/Kasa")
    with sqlite3.connect(tenant_path) as connection:
        balances = dict(connection.execute("SELECT id,current_balance FROM bank_accounts"))
    assert balances[first] == -20
    assert balances[second] == -10


def test_stock_purchase_debits_bank_balance_in_try_equivalent(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)
    with sqlite3.connect(tenant_path) as connection:
        bank_id = connection.execute(
            "INSERT INTO bank_accounts(bank_name,is_active,is_deleted) VALUES(?,1,0)",
            ("FX Bank",),
        ).lastrowid

    saved = web_main.save_stock_card({
        "name": "FX Stock", "code": "BANK-STOCK-FX", "stock": 2,
        "purchase_price": 10, "currency": "USD", "exchange_rate": 35,
        "bank_account_id": bank_id,
    })
    with sqlite3.connect(tenant_path) as connection:
        expense = connection.execute(
            "SELECT amount,original_amount,try_equivalent FROM accounting WHERE id=?",
            (saved["finance_id"],),
        ).fetchone()
        balance = connection.execute(
            "SELECT current_balance FROM bank_accounts WHERE id=?", (bank_id,),
        ).fetchone()[0]
    assert expense == (700, 20, 700)
    assert balance == -700
    assert saved["finance_amount"] == 700
    assert saved["original_amount"] == 20
    assert saved["bank_account_balance"] == -700


def test_stock_price_only_edit_records_inventory_value_adjustment(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)
    with sqlite3.connect(tenant_path) as connection:
        bank_id = connection.execute(
            "INSERT INTO bank_accounts(bank_name,is_active,is_deleted) VALUES(?,1,0)",
            ("Value Bank",),
        ).lastrowid

    saved = web_main.save_stock_card({
        "name": "Value Stock", "code": "BANK-STOCK-VALUE", "stock": 2,
        "purchase_price": 10, "bank_account_id": bank_id,
    })
    updated = web_main.save_stock_card({
        "id": saved["id"], "name": "Value Stock", "code": "BANK-STOCK-VALUE",
        "stock": 2, "purchase_price": 12, "bank_account_id": bank_id,
    })
    with sqlite3.connect(tenant_path) as connection:
        expense = connection.execute(
            "SELECT category,amount,bank_account_id FROM accounting WHERE id=?",
            (updated["finance_id"],),
        ).fetchone()
        balance = connection.execute(
            "SELECT current_balance FROM bank_accounts WHERE id=?", (bank_id,),
        ).fetchone()[0]
    assert expense == ("Stok De\u011fer D\u00fczeltme - Art\u0131\u015f", 4, bank_id)
    assert balance == -24
    decreased = web_main.save_stock_card({
        "id": updated["id"], "name": "Value Stock", "code": "BANK-STOCK-VALUE",
        "stock": 2, "purchase_price": 9, "bank_account_id": bank_id,
    })
    with sqlite3.connect(tenant_path) as connection:
        adjustment = connection.execute(
            "SELECT category,amount FROM accounting WHERE id=?",
            (decreased["finance_id"],),
        ).fetchone()
        final_balance = connection.execute(
            "SELECT current_balance FROM bank_accounts WHERE id=?", (bank_id,),
        ).fetchone()[0]
    assert adjustment == ("Stok De\u011fer D\u00fczeltme - D\u00fc\u015f\u00fc\u015f", 6)
    assert final_balance == -30


def test_stock_decrease_records_desktop_writeoff_expense(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)
    with sqlite3.connect(tenant_path) as connection:
        bank_id = connection.execute(
            "INSERT INTO bank_accounts(bank_name,is_active,is_deleted) VALUES(?,1,0)",
            ("Writeoff Bank",),
        ).lastrowid

    web_main.save_stock_card({
        "name": "Writeoff Stock", "code": "BANK-STOCK-WRITEOFF", "stock": 3,
        "purchase_price": 10, "bank_account_id": bank_id,
    })
    with sqlite3.connect(tenant_path) as connection:
        part_id = connection.execute("SELECT id FROM parts WHERE code=?", ("BANK-STOCK-WRITEOFF",)).fetchone()[0]
    updated = web_main.save_stock_card({
        "id": part_id,
        "name": "Writeoff Stock", "code": "BANK-STOCK-WRITEOFF", "stock": 2,
        "purchase_price": 10, "bank_account_id": bank_id,
    })
    with sqlite3.connect(tenant_path) as connection:
        expense = connection.execute(
            "SELECT category,amount FROM accounting WHERE id=?", (updated["finance_id"],),
        ).fetchone()
        balance = connection.execute(
            "SELECT current_balance FROM bank_accounts WHERE id=?", (bank_id,),
        ).fetchone()[0]
    assert expense == ("Stok D\u00fc\u015f\u00fcm / Fire", 10)
    assert balance == -40
