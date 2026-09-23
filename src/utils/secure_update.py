from __future__ import annotations

import hashlib
import json
import os
import secrets
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


DEFAULT_UPDATE_BASE_URL = os.environ.get(
    "AYECPRO_UPDATE_BASE_URL",
    "https://lisans.ayecpro.com/Update",
).rstrip("/")

# Legacy release host remains pinned for existing installations. New release
# manifests still default to HTTPS and every other HTTP host is rejected.
TRUSTED_HTTP_UPDATE_HOSTS = {"85.117.239.60"}


class UpdateSecurityError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpdateManifest:
    version: str
    url: str
    sha256: str
    notes: str = ""


def _allow_insecure_localhost() -> bool:
    return os.environ.get("AYECPRO_ALLOW_INSECURE_LOCAL_UPDATE", "").strip() == "1"


def validate_update_url(url: str, *, expected_host: str | None = None) -> str:
    value = str(url or "").strip()
    parsed = urllib.parse.urlparse(value)
    is_loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    is_trusted_http = (
        parsed.scheme == "http"
        and parsed.hostname in TRUSTED_HTTP_UPDATE_HOSTS
    )
    if (
        parsed.scheme != "https"
        and not is_trusted_http
        and not (is_loopback and _allow_insecure_localhost())
    ):
        raise UpdateSecurityError("Update URL must use HTTPS.")
    if not parsed.hostname:
        raise UpdateSecurityError("Update URL host is missing.")
    if expected_host and parsed.hostname.lower() != expected_host.lower():
        allowed = {
            item.strip().lower()
            for item in os.environ.get("AYECPRO_UPDATE_ALLOWED_HOSTS", "").split(",")
            if item.strip()
        }
        if parsed.hostname.lower() not in allowed:
            raise UpdateSecurityError("Update download host is not trusted.")
    return value


def parse_update_manifest(payload: str, *, manifest_url: str) -> UpdateManifest:
    try:
        data = json.loads(str(payload or "").strip())
    except (TypeError, ValueError) as exc:
        raise UpdateSecurityError("Update manifest must be valid JSON.") from exc

    if not isinstance(data, dict):
        raise UpdateSecurityError("Update manifest must be a JSON object.")

    version = str(data.get("version") or "").strip()
    url = str(data.get("url") or "").strip()
    digest = str(data.get("sha256") or "").strip().lower()
    notes = str(data.get("notes") or "").strip()
    if not version or not url:
        raise UpdateSecurityError("Update manifest version or URL is missing.")
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise UpdateSecurityError("Update manifest SHA-256 is invalid.")

    manifest_host = urllib.parse.urlparse(
        validate_update_url(manifest_url)
    ).hostname
    validate_update_url(url, expected_host=manifest_host)
    return UpdateManifest(version=version, url=url, sha256=digest, notes=notes)


def fetch_update_manifest(
    manifest_url: str,
    *,
    timeout: float = 5.0,
) -> UpdateManifest:
    trusted_url = validate_update_url(manifest_url)
    request = urllib.request.Request(
        trusted_url,
        headers={"User-Agent": "AYEC-Pro-Desktop-Updater/2"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        expected_host = urllib.parse.urlparse(trusted_url).hostname
        validate_update_url(final_url, expected_host=expected_host)
        payload = response.read().decode("utf-8")
    return parse_update_manifest(payload, manifest_url=trusted_url)


def download_verified_update(
    url: str,
    destination: str | os.PathLike[str],
    expected_sha256: str,
    *,
    progress_callback=None,
    timeout: float = 30.0,
) -> str:
    trusted_url = validate_update_url(url)
    expected = str(expected_sha256 or "").strip().lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise UpdateSecurityError("Expected update SHA-256 is invalid.")

    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    try:
        partial.unlink(missing_ok=True)
        request = urllib.request.Request(
            trusted_url,
            headers={"User-Agent": "AYEC-Pro-Desktop-Updater/2"},
        )
        digest = hashlib.sha256()
        downloaded = 0
        with urllib.request.urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            expected_host = urllib.parse.urlparse(trusted_url).hostname
            validate_update_url(final_url, expected_host=expected_host)
            total = int(response.headers.get("Content-Length") or 0)
            with partial.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    digest.update(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total > 0:
                        progress_callback(min(100, int(downloaded * 100 / total)))

        actual = digest.hexdigest()
        if not secrets.compare_digest(actual, expected):
            raise UpdateSecurityError("Downloaded update SHA-256 does not match.")
        os.replace(partial, target)
        if progress_callback:
            progress_callback(100)
        return str(target)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def verify_update_file(
    path: str | os.PathLike[str],
    expected_sha256: str,
) -> bool:
    expected = str(expected_sha256 or "").strip().lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        return False
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return secrets.compare_digest(digest.hexdigest(), expected)
