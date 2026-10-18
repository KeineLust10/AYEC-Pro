import inspect
import threading
from http.server import ThreadingHTTPServer

import pytest
import requests

from Web_Arayuzu import Main as web_main
import src.database
import src.services.offer_acceptance_service
from tests.test_vendor_management_center import _setup_tenant


class FakeOfferDatabase:
    def __init__(self, **kwargs):
        self.options = kwargs
        self.closed = False

    def close(self):
        self.closed = True


class FakeOfferService:
    def __init__(self, database):
        self.database = database
        self.arguments = None

    def accept(self, offer_id, **kwargs):
        self.arguments = (offer_id, kwargs)
        return {"offer_id": offer_id, "payment": kwargs["payment_amount"]}

    def reverse_for_revision(self, offer_id, reason, reversed_by=""):
        self.reversal_arguments = (offer_id, reason, reversed_by)
        return {"offer_id": offer_id, "reversal_tracking_no": "SRV-REV-1"}


def test_offer_acceptance_uses_the_active_tenant_database_and_actor(monkeypatch, tmp_path):
    database = FakeOfferDatabase()
    service = FakeOfferService(database)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant-a.db")
    def database_factory(**kwargs):
        database.options = kwargs
        return database

    monkeypatch.setattr(src.database, "Database", database_factory)
    monkeypatch.setattr(
        src.services.offer_acceptance_service,
        "OfferAcceptanceService",
        lambda selected: service,
    )

    result = web_main.desktop_accept_offer(
        81,
        {"payment_amount": "25.5", "payment_method": "Nakit"},
        "agent-a",
    )

    assert result == {"offer_id": 81, "payment": 25.5}
    assert database.options == {
        "db_name": str(tmp_path / "tenant-a.db"),
        "init_mode": "connection_only",
    }
    assert service.arguments == (
        81,
        {"payment_amount": 25.5, "payment_method": "Nakit", "accepted_by": "agent-a"},
    )
    assert database.closed is True


@pytest.mark.parametrize(
    "offer_id,payload",
    [
        (0, {"payment_amount": 0}),
        (81, {"payment_amount": "nan"}),
        (81, {"payment_amount": -1}),
        (81, {"payment_amount": 0, "payment_method": "Unapproved"}),
    ],
)
def test_offer_acceptance_rejects_invalid_requests_before_opening_database(
    monkeypatch, offer_id, payload
):
    monkeypatch.setattr(
        src.database,
        "Database",
        lambda **_kwargs: pytest.fail("invalid payment must not open the database"),
    )

    with pytest.raises(ValueError):
        web_main.desktop_accept_offer(offer_id, payload)


def test_offer_reversal_uses_the_active_tenant_database_and_actor(monkeypatch, tmp_path):
    database = FakeOfferDatabase()
    service = FakeOfferService(database)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant-a.db")
    monkeypatch.setattr(src.database, "Database", lambda **kwargs: database)
    monkeypatch.setattr(
        src.services.offer_acceptance_service,
        "OfferAcceptanceService",
        lambda selected: service,
    )

    result = web_main.desktop_reverse_offer(
        81, {"reason": "Customer changed product quantity"}, "agent-a"
    )

    assert result == {"offer_id": 81, "reversal_tracking_no": "SRV-REV-1"}
    assert service.reversal_arguments == (
        81,
        "Customer changed product quantity",
        "agent-a",
    )
    assert database.closed is True


@pytest.mark.parametrize(
    "offer_id,payload",
    [(0, {"reason": "Valid revision reason"}), (81, {"reason": "no"})],
)
def test_offer_reversal_rejects_invalid_requests_before_opening_database(
    monkeypatch, offer_id, payload
):
    monkeypatch.setattr(
        src.database,
        "Database",
        lambda **_kwargs: pytest.fail("invalid reversal must not open the database"),
    )

    with pytest.raises(ValueError):
        web_main.desktop_reverse_offer(offer_id, payload)


def test_offer_acceptance_endpoint_requires_a_user_and_calls_the_service():
    source = inspect.getsource(web_main.AYECRequestHandler.do_POST)
    start = source.index('if path.startswith("/api/desktop/offers/")')
    end = source.index('if path == "/api/desktop/projects/lifecycle"', start)
    route = source[start:end]

    assert "user = self.current_user()" in route
    assert "if not user:" in route
    assert "desktop_accept_offer(offer_id, payload, accepted_by)" in route
    assert "return self.send_json({\"error\": str(error)}, 409)" in route


def test_offer_reversal_endpoint_requires_a_user_and_calls_the_service():
    source = inspect.getsource(web_main.AYECRequestHandler.do_POST)
    start = source.index('if path.startswith("/api/desktop/offers/") and path.endswith("/reverse")')
    end = source.index('if path == "/api/desktop/projects/lifecycle"', start)
    route = source[start:end]

    assert "user = self.current_user()" in route
    assert "if not user:" in route
    assert "desktop_reverse_offer(offer_id, payload, reversed_by)" in route
    assert "return self.send_json({\"error\": str(error)}, 409)" in route


def test_offer_acceptance_http_route_requires_auth_and_uses_the_session_actor(
    monkeypatch, tmp_path
):
    _actor, _tenant_path = _setup_tenant(monkeypatch, tmp_path)
    accepted = []
    monkeypatch.setattr(
        web_main,
        "desktop_accept_offer",
        lambda offer_id, payload, accepted_by: accepted.append(
            (offer_id, payload, accepted_by)
        ) or {"offer_id": offer_id, "payment": float(payload["payment_amount"])},
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = f"{base_url}/api/desktop/offers/81/accept"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.post(endpoint, json={"payment_amount": 10}).status_code == 401

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
        assert login.status_code == 200, login.text
        accepted_response = session.post(
            endpoint,
            json={"payment_amount": 10, "payment_method": "Nakit"},
        )
        assert accepted_response.status_code == 200, accepted_response.text
        assert accepted_response.json() == {"offer_id": 81, "payment": 10.0}
        assert accepted == [(81, {"payment_amount": 10, "payment_method": "Nakit"}, "vendor-operator")]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_offer_reversal_http_route_requires_auth_and_uses_the_session_actor(
    monkeypatch, tmp_path
):
    _actor, _tenant_path = _setup_tenant(monkeypatch, tmp_path)
    reversed_offers = []
    monkeypatch.setattr(
        web_main,
        "desktop_reverse_offer",
        lambda offer_id, payload, reversed_by: reversed_offers.append(
            (offer_id, payload, reversed_by)
        ) or {"offer_id": offer_id, "reversal_tracking_no": "SRV-REV-1"},
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = f"{base_url}/api/desktop/offers/81/reverse"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.post(endpoint, json={"reason": "Valid reversal reason"}).status_code == 401

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
        assert login.status_code == 200, login.text
        response = session.post(endpoint, json={"reason": "Customer changed product quantity"})
        assert response.status_code == 200, response.text
        assert response.json() == {"offer_id": 81, "reversal_tracking_no": "SRV-REV-1"}
        assert reversed_offers == [
            (81, {"reason": "Customer changed product quantity"}, "vendor-operator")
        ]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
