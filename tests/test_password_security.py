import hashlib

from src.database import Database
from src.utils.auth_manager import AuthManager
from src.utils.password_security import (
    hash_password,
    hash_session_token,
    validate_new_password,
    verify_password,
)


def test_password_hash_uses_bcrypt_and_verifies():
    password_hash = hash_password("StrongPass2026")

    assert password_hash.startswith("$2")
    assert verify_password("StrongPass2026", password_hash) == (True, None)
    assert verify_password("wrong", password_hash) == (False, None)


def test_legacy_sha256_is_upgraded_after_verification():
    password = "LegacyPass2026"
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()

    valid, upgraded = verify_password(password, legacy)

    assert valid is True
    assert upgraded
    assert upgraded.startswith("$2")


def test_new_database_does_not_create_fixed_admin_account():
    db = Database(":memory:", init_mode="full")
    try:
        row = db.cursor.execute(
            "SELECT id FROM users WHERE username='admin'"
        ).fetchone()
        assert row is None
    finally:
        db.close()


def test_database_login_upgrades_legacy_password():
    db = Database(":memory:", init_mode="full")
    try:
        password = "LegacyPass2026"
        legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
        db.cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("legacy-user", legacy, "Personel"),
        )
        db.conn.commit()

        assert db.authenticate_user("legacy-user", password)
        stored = db.cursor.execute(
            "SELECT password FROM users WHERE username=?",
            ("legacy-user",),
        ).fetchone()[0]
        assert stored.startswith("$2")
    finally:
        db.close()


def test_remember_token_is_stored_as_a_hash():
    db = Database(":memory:", init_mode="full")
    try:
        db.add_user(
            "remember-user",
            "RememberPass2026",
            "remember@example.invalid",
            "Personel",
        )
        manager = AuthManager(db)

        success, _message = manager.login(
            "remember-user",
            "RememberPass2026",
            remember=True,
        )

        assert success is True
        stored = db.cursor.execute(
            "SELECT remember_token FROM users WHERE username=?",
            ("remember-user",),
        ).fetchone()[0]
        assert stored == hash_session_token(manager.remember_token)
        assert stored != manager.remember_token
    finally:
        db.close()


def test_action_password_accepts_the_current_login_password():
    db = Database(":memory:", init_mode="full")
    try:
        db.add_user(
            "action-user",
            "ActionPass2026",
            "action@example.invalid",
            "Admin",
        )
        manager = AuthManager(db)
        success, _message = manager.login(
            "action-user",
            "ActionPass2026",
        )

        assert success is True
        assert manager.verify_action_password("ActionPass2026") is True
        assert manager.verify_action_password("wrong") is False
    finally:
        db.close()


def test_weak_password_is_rejected():
    assert validate_new_password("123456") is not None
    assert validate_new_password("onlylowercase1") is not None
    assert validate_new_password("StrongPass2026") is None
