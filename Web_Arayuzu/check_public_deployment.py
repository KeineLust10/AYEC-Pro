"""Read-only check for the public AYEC web frontend and authentication API."""

from __future__ import annotations

import argparse
import json
import os
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / "web" / "index.html"
DEFAULT_BASE_URL = os.environ.get("AYEC_PUBLIC_URL", "https://panel.ayecpro.com").rstrip("/")


class _ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        source = dict(attrs).get("src")
        if source:
            self.sources.append(source)


def expected_app_key(index_path: Path = INDEX_PATH) -> str | None:
    parser = _ScriptParser()
    parser.feed(index_path.read_text(encoding="utf-8"))
    for source in parser.sources:
        parsed = urlsplit(source)
        if Path(parsed.path).name.lower() == "app.js":
            return parse_qs(parsed.query).get("v", [None])[0]
    return None


def _fetch(
    url: str,
    timeout: float,
    accept: str,
    data: bytes | None = None,
    method: str | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, str, bytes, dict[str, str]]:
    request = Request(
        url,
        data=data,
        headers={
            "Accept": accept,
            "Cache-Control": "no-cache",
            **({"Content-Type": "application/json"} if data is not None else {}),
            **(headers or {}),
        },
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return (
                response.status,
                response.headers.get("Content-Type", ""),
                response.read(),
                {
                    "server": response.headers.get("Server", ""),
                    "date": response.headers.get("Date", ""),
                    "cache_control": response.headers.get("Cache-Control", ""),
                },
            )
    except HTTPError as error:
        return (
            error.code,
            error.headers.get("Content-Type", ""),
            error.read(),
            {
                "server": error.headers.get("Server", ""),
                "date": error.headers.get("Date", ""),
                "cache_control": error.headers.get("Cache-Control", ""),
            },
        )


def probe_public_deployment(
    base_url: str,
    expected_key: str | None,
    timeout: float = 15,
    check_login_post: bool = False,
    host_header: str | None = None,
) -> dict[str, object]:
    base_url = base_url.rstrip("/")
    parsed_base = urlsplit(base_url)
    request_headers = {"Host": host_header} if host_header else {}
    browser_origin = f"{parsed_base.scheme}://{host_header or parsed_base.netloc}"
    browser_post_headers = {
        **request_headers,
        "Origin": browser_origin,
        "Referer": browser_origin + "/#login",
    }
    result: dict[str, object] = {
        "host": host_header or parsed_base.netloc,
        "host_header": host_header or "",
        "expected_app_key": expected_key,
        "root_status": None,
        "root_server": "",
        "root_date": "",
        "root_cache_control": "",
        "served_app_key": None,
        "frontend_matches": False,
        "asset_status": None,
        "asset_content_type": "",
        "asset_is_javascript": False,
        "api_status": None,
        "api_content_type": "",
        "api_is_json": False,
        "api_build_id": "",
        "api_build_matches": False,
        "api_bootstrap_status": None,
        "api_bootstrap_content_type": "",
        "api_bootstrap_is_json": False,
        "api_bootstrap_rejects_anonymous": False,
        "api_post_status": None,
        "api_post_content_type": "",
        "api_post_is_json": False,
        "api_post_rejects_unauthenticated_profile": False,
        "api_post_missing_require_user": False,
        "api_login_post_checked": check_login_post,
        "api_login_status": None,
        "api_login_content_type": "",
        "api_login_is_json": False,
        "api_login_rejects_empty_credentials": False,
    }
    try:
        root_status, _root_type, root_body, root_headers = _fetch(
            base_url + "/", timeout, "text/html", headers=request_headers
        )
        result["root_status"] = root_status
        result["root_server"] = root_headers["server"]
        result["root_date"] = root_headers["date"]
        result["root_cache_control"] = root_headers["cache_control"]
        parser = _ScriptParser()
        parser.feed(root_body.decode("utf-8", errors="replace"))
        app_source = None
        for source in parser.sources:
            parsed = urlsplit(source)
            if Path(parsed.path).name.lower() == "app.js":
                app_source = source
                result["served_app_key"] = parse_qs(parsed.query).get("v", [None])[0]
                break
        result["frontend_matches"] = bool(
            expected_key and result["served_app_key"] == expected_key
        )
        if app_source:
            asset_url = urljoin(base_url + "/", app_source)
            asset_status, asset_type, asset_body, _asset_headers = _fetch(
                asset_url, timeout, "application/javascript", headers=request_headers
            )
            result["asset_status"] = asset_status
            result["asset_content_type"] = asset_type.split(";", 1)[0].strip().lower()
            result["asset_is_javascript"] = (
                "javascript" in result["asset_content_type"] and b"apiFetch" in asset_body
            )
    except (OSError, URLError, TimeoutError, ValueError):
        result["root_error"] = "request_failed"

    try:
        probe_id = str(time.time_ns())
        api_url = urljoin(base_url + "/", "api/auth/status") + "?deployment_probe=" + probe_id
        api_status, api_type, api_body, _api_headers = _fetch(
            api_url, timeout, "application/json", headers=request_headers
        )
        result["api_status"] = api_status
        result["api_content_type"] = api_type.split(";", 1)[0].strip().lower()
        try:
            parsed_body = json.loads(api_body.decode("utf-8"))
            result["api_is_json"] = isinstance(parsed_body, dict)
            result["api_build_id"] = str(parsed_body.get("app_build_id") or "")
            result["api_build_matches"] = bool(
                expected_key and result["api_build_id"] == expected_key
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            result["api_is_json"] = False
    except (OSError, URLError, TimeoutError, ValueError):
        result["api_error"] = "request_failed"

    try:
        bootstrap_url = urljoin(base_url + "/", "api/desktop/bootstrap")
        bootstrap_status, bootstrap_type, bootstrap_body, _bootstrap_headers = _fetch(
            bootstrap_url, timeout, "application/json", headers=request_headers
        )
        result["api_bootstrap_status"] = bootstrap_status
        result["api_bootstrap_content_type"] = bootstrap_type.split(";", 1)[0].strip().lower()
        try:
            bootstrap_payload = json.loads(bootstrap_body.decode("utf-8"))
            result["api_bootstrap_is_json"] = isinstance(bootstrap_payload, dict)
        except (UnicodeDecodeError, json.JSONDecodeError):
            bootstrap_payload = None
        result["api_bootstrap_rejects_anonymous"] = (
            bootstrap_status == 401
            and isinstance(bootstrap_payload, dict)
            and bool(bootstrap_payload.get("error"))
        )
    except (OSError, URLError, TimeoutError, ValueError):
        result["api_bootstrap_error"] = "request_failed"

    try:
        profile_url = urljoin(base_url + "/", "api/auth/profile")
        post_status, post_type, post_body, _post_headers = _fetch(
            profile_url,
            timeout,
            "application/json",
            data=b"{}",
            method="POST",
            headers=browser_post_headers,
        )
        result["api_post_status"] = post_status
        result["api_post_content_type"] = post_type.split(";", 1)[0].strip().lower()
        try:
            post_payload = json.loads(post_body.decode("utf-8"))
            result["api_post_is_json"] = isinstance(post_payload, dict)
        except (UnicodeDecodeError, json.JSONDecodeError):
            post_payload = None
        result["api_post_rejects_unauthenticated_profile"] = (
            post_status == 401
            and isinstance(post_payload, dict)
            and bool(post_payload.get("error"))
        )
        result["api_post_missing_require_user"] = (
            post_status == 400
            and isinstance(post_payload, dict)
            and "AYECRequestHandler" in str(post_payload.get("error") or "")
            and "require_user" in str(post_payload.get("error") or "")
        )
    except (OSError, URLError, TimeoutError, ValueError):
        result["api_post_error"] = "request_failed"

    if check_login_post:
        try:
            login_url = urljoin(base_url + "/", "api/auth/login")
            login_status, login_type, login_body, _login_headers = _fetch(
                login_url,
                timeout,
                "application/json",
                data=b"{}",
                method="POST",
                headers=browser_post_headers,
            )
            result["api_login_status"] = login_status
            result["api_login_content_type"] = login_type.split(";", 1)[0].strip().lower()
            try:
                login_payload = json.loads(login_body.decode("utf-8"))
                result["api_login_is_json"] = isinstance(login_payload, dict)
            except (UnicodeDecodeError, json.JSONDecodeError):
                login_payload = None
            result["api_login_rejects_empty_credentials"] = (
                login_status in {400, 401}
                and isinstance(login_payload, dict)
                and bool(login_payload.get("error"))
            )
        except (OSError, URLError, TimeoutError, ValueError):
            result["api_login_error"] = "request_failed"

    result["ok"] = (
        result["root_status"] == 200
        and result["frontend_matches"] is True
        and result["asset_status"] == 200
        and result["asset_is_javascript"] is True
        and result["api_status"] == 200
        and result["api_content_type"] == "application/json"
        and result["api_is_json"] is True
        and result["api_build_matches"] is True
        and result["api_bootstrap_content_type"] == "application/json"
        and result["api_bootstrap_rejects_anonymous"] is True
        and result["api_post_content_type"] == "application/json"
        and result["api_post_rejects_unauthenticated_profile"] is True
        and (
            not check_login_post
            or (
                result["api_login_content_type"] == "application/json"
                and result["api_login_rejects_empty_credentials"] is True
            )
        )
    )
    issues: list[str] = []
    upstream_statuses = {502, 503, 504}
    upstream_unavailable = (
        result["root_status"] in upstream_statuses
        or result["api_status"] in upstream_statuses
        or result["api_bootstrap_status"] in upstream_statuses
        or result["api_post_status"] in upstream_statuses
    )
    if upstream_unavailable:
        issues.append("backend_unavailable")
    if result["root_status"] == 200 and result["frontend_matches"] is False:
        issues.append("frontend_build_mismatch")
    if result["api_status"] == 200 and (
        result["api_content_type"] != "application/json" or result["api_is_json"] is False
    ):
        issues.append("api_status_route_returns_non_json")
    if result["api_post_missing_require_user"] is True:
        issues.append("legacy_backend_auth_handler")
    if result["api_status"] == 200 and not result["api_build_id"]:
        issues.append("backend_build_id_missing")
    if (
        result["api_bootstrap_status"] not in upstream_statuses
        and not result["api_bootstrap_rejects_anonymous"]
    ):
        issues.append("desktop_bootstrap_auth_contract_failed")
    if result["api_login_post_checked"] and (
        result["api_login_content_type"] != "application/json"
        or result["api_login_is_json"] is False
    ):
        issues.append("login_api_returns_non_json")
    result["deployment_issues"] = issues
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--expected-app-key", default=expected_app_key())
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--host-header", help="Send requests with this HTTP Host header, for local IIS site checks.")
    parser.add_argument(
        "--check-login-post",
        action="store_true",
        help="Send one empty login request; older servers may count it as a failed sign-in.",
    )
    args = parser.parse_args(argv)
    result = probe_public_deployment(
        args.base_url, args.expected_app_key, args.timeout, args.check_login_post, args.host_header
    )
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
