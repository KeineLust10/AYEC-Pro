"""Shared session persistence and cookie handling for AYEC desktop clients."""

from http.cookies import SimpleCookie
import json
import os
from pathlib import Path
import secrets
import ctypes
from ctypes import wintypes


def update_cookies(cookies, headers):
    """Read every Set-Cookie header, including session deletion."""
    values = headers.get_all("Set-Cookie") if hasattr(headers, "get_all") else None
    for value in values or [headers.get("Set-Cookie", "")]:
        parsed = SimpleCookie()
        parsed.load(value)
        for name, morsel in parsed.items():
            if morsel["max-age"] == "0" or not morsel.value:
                cookies.pop(name, None)
            else:
                cookies[name] = morsel.value


def save_session(path, *, base_url, product_code, cookies, metadata, protect):
    """The product supplies its existing encryption to preserve old installs."""
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "base_url": base_url.rstrip('/'),
               "product_code": product_code, "cookies": dict(cookies),
               "metadata": dict(metadata or {})}
    protected = protect(json.dumps(payload, ensure_ascii=True).encode("utf-8"))
    temporary = target.with_name(target.name + "." + secrets.token_hex(8) + ".tmp")
    try:
        temporary.write_bytes(protected)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def load_session(path, *, base_url, product_code, cookies, unprotect):
    """Reject foreign sessions; accept this client's legacy unscoped format."""
    cookies.clear()
    source = Path(path).expanduser().resolve()
    if not source.exists():
        return {}
    raw = unprotect(source.read_bytes())
    if not raw:
        return {}
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Invalid session file")
    if str(payload.get("base_url") or "").rstrip('/') != base_url.rstrip('/'):
        return {}
    if payload.get("product_code", product_code) != product_code:
        return {}
    loaded = payload.get("cookies") or {}
    metadata = payload.get("metadata") or {}
    if not isinstance(loaded, dict) or not isinstance(metadata, dict):
        raise ValueError("Invalid session data")
    for name, value in loaded.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise ValueError("Invalid session cookie")
        if any(ord(char) < 33 or ord(char) > 126 or char in ';\r\n' for char in name + value):
            raise ValueError("Invalid session cookie")
    cookies.update(loaded)
    return dict(metadata)


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(data):
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


def protect_current_user(data):
    """Protect session bytes with Windows DPAPI; keep non-Windows tests portable."""
    if os.name != "nt":
        return bytes(data)
    source, _source_buffer = _blob(bytes(data))
    output = _DataBlob()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(source), "AYEC Central Session", None, None, None, 0,
        ctypes.byref(output)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


def unprotect_current_user(data):
    """Unprotect bytes written by protect_current_user."""
    if os.name != "nt":
        return bytes(data)
    source, _source_buffer = _blob(bytes(data))
    output = _DataBlob()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)
