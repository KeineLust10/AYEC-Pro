import hashlib
import io
import json

import pytest

from src.utils import secure_update


class _Response:
    def __init__(self, payload, url):
        self._payload = payload
        self._url = url
        self.headers = {"Content-Length": str(payload.getbuffer().nbytes)}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self):
        return self._url

    def read(self, size=-1):
        return self._payload.read(size)


def test_manifest_rejects_http_and_missing_hash():
    with pytest.raises(secure_update.UpdateSecurityError):
        secure_update.parse_update_manifest(
            json.dumps(
                {
                    "version": "2.0.0",
                    "url": "http://updates.example.com/setup.exe",
                }
            ),
            manifest_url="https://updates.example.com/version.json",
        )


def test_manifest_rejects_untrusted_download_host():
    with pytest.raises(secure_update.UpdateSecurityError):
        secure_update.parse_update_manifest(
            json.dumps(
                {
                    "version": "2.0.0",
                    "url": "https://other.example.com/setup.exe",
                    "sha256": "a" * 64,
                }
            ),
            manifest_url="https://updates.example.com/version.json",
        )


def test_manifest_accepts_pinned_http_update_host():
    manifest = secure_update.parse_update_manifest(
        json.dumps(
            {
                "version": "2.0.4",
                "url": "http://85.117.239.60/Update/setup.exe",
                "sha256": "a" * 64,
            }
        ),
        manifest_url="http://85.117.239.60/Update/version.json",
    )
    assert manifest.version == "2.0.4"


def test_manifest_rejects_other_http_update_host():
    with pytest.raises(secure_update.UpdateSecurityError):
        secure_update.parse_update_manifest(
            json.dumps(
                {
                    "version": "2.0.4",
                    "url": "http://updates.example.com/setup.exe",
                    "sha256": "a" * 64,
                }
            ),
            manifest_url="http://updates.example.com/version.json",
        )


def test_verified_download_is_atomic(monkeypatch, tmp_path):
    payload = b"verified-update"
    expected = hashlib.sha256(payload).hexdigest()
    response = _Response(
        io.BytesIO(payload),
        "https://updates.example.com/setup.exe",
    )
    monkeypatch.setattr(
        secure_update.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: response,
    )
    target = tmp_path / "setup.exe"
    result = secure_update.download_verified_update(
        "https://updates.example.com/setup.exe",
        target,
        expected,
    )
    assert result == str(target)
    assert target.read_bytes() == payload
    assert not (tmp_path / "setup.exe.part").exists()


def test_failed_hash_never_replaces_existing_file(monkeypatch, tmp_path):
    payload = b"tampered-update"
    response = _Response(
        io.BytesIO(payload),
        "https://updates.example.com/setup.exe",
    )
    monkeypatch.setattr(
        secure_update.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: response,
    )
    target = tmp_path / "setup.exe"
    target.write_bytes(b"known-good")
    with pytest.raises(secure_update.UpdateSecurityError):
        secure_update.download_verified_update(
            "https://updates.example.com/setup.exe",
            target,
            "0" * 64,
        )
    assert target.read_bytes() == b"known-good"
    assert not (tmp_path / "setup.exe.part").exists()
