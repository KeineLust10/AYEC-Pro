from __future__ import annotations

import hashlib
import re
import secrets

import bcrypt


_BCRYPT_ROUNDS = 12
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _password_material(password: str) -> bytes:
    return hashlib.sha256(str(password).encode("utf-8")).digest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        _password_material(password),
        bcrypt.gensalt(rounds=_BCRYPT_ROUNDS),
    ).decode("ascii")


def verify_password(password: str, stored_hash: str) -> tuple[bool, str | None]:
    stored = str(stored_hash or "").strip()
    if not stored:
        return False, None

    if stored.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            valid = bcrypt.checkpw(
                _password_material(password),
                stored.encode("ascii"),
            )
            if not valid:
                valid = bcrypt.checkpw(
                    str(password).encode("utf-8"),
                    stored.encode("ascii"),
                )
            return valid, None
        except (ValueError, TypeError):
            return False, None

    if _SHA256_RE.fullmatch(stored):
        legacy = hashlib.sha256(str(password).encode("utf-8")).hexdigest()
        valid = secrets.compare_digest(legacy.lower(), stored.lower())
        return valid, hash_password(password) if valid else None

    valid = secrets.compare_digest(stored, str(password))
    return valid, hash_password(password) if valid else None


def validate_new_password(password: str) -> str | None:
    value = str(password or "")
    if len(value) < 10:
        return "Password must contain at least 10 characters."
    if not any(ch.islower() for ch in value):
        return "Password must contain a lowercase letter."
    if not any(ch.isupper() for ch in value):
        return "Password must contain an uppercase letter."
    if not any(ch.isdigit() for ch in value):
        return "Password must contain a digit."
    if value.casefold() in {
        "admin123",
        "password123",
        "1234567890",
        "qwerty1234",
    }:
        return "Password is too common."
    return None


def hash_session_token(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()
