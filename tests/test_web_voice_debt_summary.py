import sqlite3

from Web_Arayuzu import Main as web_main


def test_customer_debt_summary_matches_desktop_ledger_sign_and_conversion(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, is_deleted INTEGER)")
    conn.execute(
        "CREATE TABLE currency_transactions "
        "(customer_id INTEGER, currency TEXT, transaction_type TEXT, amount REAL)"
    )
    conn.executemany(
        "INSERT INTO customers (id,is_deleted) VALUES (?,?)",
        [(1, 0), (2, 0), (3, 1)],
    )
    conn.executemany(
        "INSERT INTO currency_transactions VALUES (?,?,?,?)",
        [
            (1, "TRY", "DEBIT", 12000),
            (1, "TRY", "CREDIT", 2000),
            (1, "USD", "DEBIT", 10),
            (2, "TRY", "CREDIT", 500),
            (3, "TRY", "DEBIT", 9000),
        ],
    )
    conn.commit()
    monkeypatch.setattr(web_main, "db_connect", lambda: conn)
    monkeypatch.setattr(
        web_main,
        "exchange_rates",
        lambda refresh=False: {"TRY": {"selling": 1}, "USD": {"selling": 30}},
    )

    assert web_main.customer_debt_summary() == {"debtor_count": 1, "total_try": 10300.0}


def test_customer_debt_summary_route_requires_authentication(monkeypatch):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/customer/debt-summary"
    handler.headers = {}
    handler.current_user = lambda: None
    sent = []
    handler.send_json = lambda *args, **kwargs: sent.append((args, kwargs))
    monkeypatch.setattr(
        web_main,
        "customer_debt_summary",
        lambda: (_ for _ in ()).throw(AssertionError("anonymous request reached tenant data")),
    )

    handler.do_GET()

    assert sent[0][0][1] == 401

    authorized = object.__new__(web_main.AYECRequestHandler)
    authorized.path = handler.path
    authorized.headers = {}
    authorized.current_user = lambda: {"id": 7, "role": "User"}
    authorized_sent = []
    authorized.send_json = lambda *args, **kwargs: authorized_sent.append((args, kwargs))
    monkeypatch.setattr(
        web_main,
        "customer_debt_summary",
        lambda: {"debtor_count": 2, "total_try": 13000.0},
    )

    authorized.do_GET()

    assert authorized_sent[0][0][0] == {"debtor_count": 2, "total_try": 13000.0}
