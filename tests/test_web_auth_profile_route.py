import sqlite3

from Web_Arayuzu import Main as web_main
from Web_Arayuzu.check_public_deployment import expected_app_key
import pytest


def test_auth_status_returns_the_current_web_build_id(monkeypatch):
    monkeypatch.setattr(web_main, "tenant_records", lambda: [])
    monkeypatch.setattr(web_main, "registry_connect", lambda: sqlite3.connect(":memory:"))
    monkeypatch.setattr(web_main, "setting_value", lambda _conn, _key, default=None: default or "")

    status = web_main.auth_status()

    assert status["app_build_id"] == web_main.WEB_APP_BUILD_ID
    assert status["app_build_id"] == expected_app_key(web_main.WEB_ROOT / "index.html")


def test_auth_profile_route_returns_json_unauthorized_without_session():
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/auth/profile"
    handler.headers = {"Content-Length": "2"}
    handler.current_user = lambda: None
    responses = []
    handler.send_json = lambda payload, status=200, headers=None: responses.append(
        (payload, status, headers)
    )

    handler.do_POST()

    assert responses == [({"error": "Authentication required"}, 401, None)]


def test_auth_profile_route_updates_authenticated_profile(monkeypatch):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/auth/profile"
    handler.headers = {
        "Content-Length": "2",
        "Host": "panel.example.test",
        "Origin": "https://panel.example.test",
    }
    user = {"id": 23, "username": "profile-user"}
    payload = {"display_name": "Updated Name"}
    handler.current_user = lambda: user
    handler.read_json = lambda: payload
    responses = []
    handler.send_json = lambda body, status=200, headers=None: responses.append(
        (body, status, headers)
    )
    monkeypatch.setattr(
        web_main,
        "update_current_user_profile",
        lambda current, changes: {"ok": current is user and changes is payload},
    )

    handler.do_POST()

    assert responses == [({"ok": True}, 200, None)]


@pytest.mark.parametrize(
    "headers",
    [
        {"Content-Length": "2", "Host": "panel.example.test"},
        {
            "Content-Length": "2",
            "Host": "panel.example.test",
            "Origin": "https://attacker.example",
        },
    ],
)
def test_auth_profile_route_rejects_missing_or_cross_origin(headers):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/auth/profile"
    handler.headers = headers
    handler.current_user = lambda: {"id": 23, "username": "profile-user"}
    handler.read_json = lambda: (_ for _ in ()).throw(
        AssertionError("Rejected profile requests must not be parsed")
    )
    responses = []
    handler.send_json = lambda body, status=200, headers=None: responses.append(
        (body, status, headers)
    )

    handler.do_POST()

    assert responses == [({"error": "Invalid request origin"}, 403, None)]


@pytest.mark.parametrize(
    "payload",
    [{}, {"identifier": "profile-user"}, {"password": "secret"}, []],
)
def test_login_rejects_incomplete_payload_without_counting_auth_failure(payload):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/auth/login"
    handler.headers = {"Content-Length": "2"}
    handler.read_json = lambda: payload
    handler.client_ip = lambda: (_ for _ in ()).throw(
        AssertionError("Incomplete credentials must not reach rate limiting")
    )
    responses = []
    handler.send_json = lambda body, status=200, headers=None: responses.append(
        (body, status, headers)
    )

    handler.do_POST()

    expected = {"error": "Invalid login payload"} if not isinstance(payload, dict) else {
        "error": "Kullan\u0131c\u0131 ad\u0131 ve parola gereklidir."
    }
    assert responses == [(expected, 400, None)]


def test_successful_login_returns_json_payload_and_session_cookie(monkeypatch):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/auth/login"
    handler.headers = {"User-Agent": "test-agent"}
    payload = {"identifier": "profile-user", "password": "secret", "remember": True}
    user = {"id": 23, "username": "profile-user", "_tenant_id": "tenant-1"}
    handler.read_json = lambda: payload
    handler.client_ip = lambda: "127.0.0.1"
    handler.session_cookie_header = lambda token, max_age, remember: (
        f"session={token}; Max-Age={max_age}; remember={int(remember)}"
    )
    responses = []
    handler.send_json = lambda body, status=200, headers=None: responses.append(
        (body, status, headers)
    )
    monkeypatch.setattr(web_main, "auth_rate_limited", lambda _key: False)
    monkeypatch.setattr(
        web_main,
        "authenticate_account",
        lambda identifier, password, tenant_id: user
        if (identifier, password, tenant_id) == ("profile-user", "secret", None)
        else None,
    )
    monkeypatch.setattr(web_main, "tenant_by_id", lambda tenant_id: {"id": tenant_id})
    monkeypatch.setattr(web_main, "tenant_access_error", lambda _tenant: None)
    monkeypatch.setattr(web_main, "is_control_admin", lambda _user: False)
    monkeypatch.setattr(
        web_main,
        "create_session",
        lambda user_id, remember, user_agent, client_ip, tenant_id: (
            "session-token",
            86400,
        )
        if (user_id, remember, user_agent, client_ip, tenant_id)
        == (23, True, "test-agent", "127.0.0.1", "tenant-1")
        else (_ for _ in ()).throw(AssertionError("Unexpected session arguments")),
    )
    monkeypatch.setattr(web_main, "public_user", lambda _user: {"id": 23})

    handler.do_POST()

    assert responses == [
        (
            {"ok": True, "token": "session-token", "access_token": "session-token", "user": {"id": 23}},
            200,
            {"Set-Cookie": "session=session-token; Max-Age=86400; remember=1"},
        )
    ]
