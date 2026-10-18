import pytest

import Web_Arayuzu.Main as web_main


def test_archive_detail_returns_tenant_service_logs_parts_and_ignores_deleted_parts(tmp_path):
    conn = web_main._raw_connect(tmp_path / "archive-detail.db")
    conn.execute("CREATE TABLE devices(id INTEGER PRIMARY KEY,tracking_no TEXT,device_brand TEXT,device_model TEXT,serial_no TEXT,entry_date TEXT,delivered_at TEXT,status TEXT)")
    conn.execute("INSERT INTO devices VALUES(8,'SRV-ARCH-8','AYEC','Audit Device','SER-8','2026-01-02','2026-01-05','Teslim Edildi')")
    conn.execute("CREATE TABLE logs(id INTEGER PRIMARY KEY,tracking_no TEXT,log_type TEXT,message TEXT,user TEXT,created_at TEXT)")
    conn.execute("INSERT INTO logs VALUES(1,'SRV-ARCH-8','Customer','Ready','Owner','2026-01-04')")
    conn.execute("CREATE TABLE service_logs(id INTEGER PRIMARY KEY,device_tracking_no TEXT,log_type TEXT,message TEXT,created_at TEXT,user TEXT)")
    conn.execute("INSERT INTO service_logs VALUES(2,'SRV-ARCH-8','Technician','Repaired','2026-01-03','Tech')")
    conn.execute("CREATE TABLE used_parts(id INTEGER PRIMARY KEY,tracking_no TEXT,part_name TEXT,quantity REAL,price REAL,created_at TEXT,is_deleted INTEGER)")
    conn.execute("INSERT INTO used_parts VALUES(3,'SRV-ARCH-8','Screen',1,125,'2026-01-03',0)")
    conn.execute("INSERT INTO used_parts VALUES(4,'SRV-ARCH-8','Deleted part',1,50,'2026-01-03',1)")
    conn.execute("CREATE TABLE device_tests(id INTEGER PRIMARY KEY,tracking_no TEXT,test_name TEXT,result TEXT,note TEXT,technician TEXT,test_date TEXT)")
    conn.execute("INSERT INTO device_tests VALUES(5,'SRV-ARCH-8','Power','FAIL','Old result','Tech A','2026-01-02')")
    conn.execute("INSERT INTO device_tests VALUES(6,'SRV-ARCH-8','Power','PASS','Current result','Tech B','2026-01-04')")
    conn.execute("INSERT INTO device_tests VALUES(7,'SRV-OTHER','Power','FAIL','Other tenant record','Tech C','2026-01-05')")
    result = web_main.desktop_archive_detail(conn, "SRV-ARCH-8")
    assert result["device"]["serial_no"] == "SER-8"
    assert {row["message"] for row in result["logs"]} == {"Ready"}
    assert [row["part_name"] for row in result["used_parts"]] == ["Screen"]
    assert result["tests"] == [{"name": "Power", "result": "PASS", "note": "Current result", "technician": "Tech B", "test_date": "2026-01-04"}]
    conn.close()


def test_archive_detail_rejects_missing_service_and_api_is_authenticated(tmp_path):
    conn = web_main._raw_connect(tmp_path / "archive-detail-missing.db")
    conn.execute("CREATE TABLE devices(id INTEGER PRIMARY KEY,tracking_no TEXT)")
    with pytest.raises(LookupError, match="Service record not found"):
        web_main.desktop_archive_detail(conn, "SRV-404")
    conn.execute("INSERT INTO devices VALUES(1,'SRV-404')")
    assert web_main.desktop_archive_detail(conn, "SRV-404")["tests"] == []
    conn.close()
    source = open("Web_Arayuzu/Main.py", encoding="utf-8").read()
    start = source.index('if path == "/api/desktop/archive-detail"')
    end = source.index("if accounting_receipt_match", start)
    route = source[start:end]
    assert "if not self.current_user()" in route
    assert "desktop_archive_detail(conn, tracking_no)" in route
    assert "external_tracking_photos(tracking_no)" in source


def test_archive_detail_uses_legacy_archived_parts_flag_when_needed(tmp_path):
    conn = web_main._raw_connect(tmp_path / "archive-detail-legacy-parts.db")
    conn.execute("CREATE TABLE devices(id INTEGER PRIMARY KEY,tracking_no TEXT)")
    conn.execute("INSERT INTO devices VALUES(1,'SRV-ARCH-9')")
    conn.execute("CREATE TABLE used_parts(id INTEGER PRIMARY KEY,tracking_no TEXT,part_name TEXT,is_archived INTEGER)")
    conn.execute("INSERT INTO used_parts VALUES(1,'SRV-ARCH-9','Visible part',0)")
    conn.execute("INSERT INTO used_parts VALUES(2,'SRV-ARCH-9','Archived part',1)")

    result = web_main.desktop_archive_detail(conn, "SRV-ARCH-9")

    assert [row["part_name"] for row in result["used_parts"]] == ["Visible part"]
    conn.close()


def test_archive_detail_reads_legacy_test_rows_without_id_or_test_date(tmp_path):
    conn = web_main._raw_connect(tmp_path / "archive-detail-legacy-tests.db")
    conn.execute("CREATE TABLE devices(id INTEGER PRIMARY KEY,tracking_no TEXT)")
    conn.execute("INSERT INTO devices VALUES(1,'SRV-ARCH-10')")
    conn.execute("CREATE TABLE device_tests(tracking_no TEXT,test_name TEXT,result TEXT,note TEXT,technician TEXT,created_at TEXT)")
    conn.execute("INSERT INTO device_tests VALUES('SRV-ARCH-10','Display','FAIL','Old','Tech A','2026-01-02')")
    conn.execute("INSERT INTO device_tests VALUES('SRV-ARCH-10','Display','PASS','Latest','Tech B','2026-01-04')")

    result = web_main.desktop_archive_detail(conn, "SRV-ARCH-10")

    assert result["tests"] == [{"name": "Display", "result": "PASS", "note": "Latest", "technician": "Tech B", "test_date": "2026-01-04"}]
    conn.close()
