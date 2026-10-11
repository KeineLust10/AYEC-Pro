"""Store a user-scoped encrypted secret with Windows DPAPI."""

import os
from pathlib import Path


def _secret_path(name):
    root = os.environ.get("LOCALAPPDATA") or str(Path.home())
    directory = Path(root) / "AYEC Pro" / "Secrets"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / (name + ".dpapi")


def save_secret(name, value):
    if os.name != "nt":
        raise RuntimeError("Secure local secret storage is available on Windows only.")
    import win32crypt

    encrypted = win32crypt.CryptProtectData(
        str(value).encode("utf-8"), "AYEC Pro local secret", None, None, None, 0
    )
    _secret_path(name).write_bytes(encrypted)


def load_secret(name):
    path = _secret_path(name)
    if not path.exists():
        return ""
    if os.name != "nt":
        return ""
    import win32crypt

    encrypted = path.read_bytes()
    return win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode("utf-8")


def delete_secret(name):
    path = _secret_path(name)
    if path.exists():
        path.unlink()
