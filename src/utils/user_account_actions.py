"""Shared existing local account-state action; no credential or session changes."""

import json
from src.utils.role_utils import is_admin_role
from src.utils.password_security import hash_password, validate_new_password


def current_account_administrator(widget, db):
    ancestor = widget.parentWidget()
    while ancestor is not None:
        context = getattr(ancestor, "current_user", None)
        if getattr(ancestor, "db", None) is db and isinstance(context, dict):
            return context if is_admin_role(context.get("role")) and context.get("id") is not None else None
        ancestor = ancestor.parentWidget()
    return None


def save_user_page_permissions(db, user_id, page_ids):
    row = db.conn.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
    if row is None or is_admin_role(row[0]):
        raise ValueError("Account missing or administrator permissions are role-owned")
    payload = json.dumps({"pages": sorted({int(page_id) for page_id in page_ids})})
    db.conn.execute("UPDATE users SET permissions=? WHERE id=?", (payload, user_id))
    db.conn.commit()


def set_user_account_active(db, user_id, enabled):
    result = db.conn.execute("UPDATE users SET active=? WHERE id=?", (1 if enabled else 0, user_id))
    if result.rowcount != 1:
        raise ValueError("Account not found")
    db.conn.commit()


def resolve_audit_account(db, actor):
    key = str(actor if actor is not None else "").strip()
    if not key:
        return None
    account = db.conn.execute("SELECT id, username, COALESCE(active, 1) FROM users WHERE CAST(id AS TEXT)=?", (key,)).fetchone()
    if account is None:
        account = db.conn.execute("SELECT id, username, COALESCE(active, 1) FROM users WHERE username=?", (key,)).fetchone()
    return tuple(account) if account is not None else None


def change_account_passwords(db, actor_id, changes):
    """Apply explicit per-account passwords through the existing password codec."""
    entries = [(int(user_id), str(password)) for user_id, password in changes]
    if not entries or len({user_id for user_id, _password in entries}) != len(entries):
        raise ValueError("Select distinct accounts")
    if len({password for _user_id, password in entries}) != len(entries):
        raise ValueError("Each account requires a different password")
    for user_id, password in entries:
        error = validate_new_password(password)
        if error:
            raise ValueError(f"Account {user_id}: {error}")

    def check_accounts():
        actor = db.conn.execute("SELECT role FROM users WHERE id=?", (actor_id,)).fetchone()
        if not actor or not is_admin_role(actor[0]):
            raise PermissionError("Administrator access required")
        for user_id, _password in entries:
            target = db.conn.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
            if not target or str(user_id) == str(actor_id) or is_admin_role(target[0]):
                raise PermissionError("Missing, current, or privileged account cannot be changed in bulk")

    if db.conn.in_transaction:
        raise RuntimeError("Finish the existing transaction before changing passwords")
    check_accounts()
    hashes = [(hash_password(password), user_id) for user_id, password in entries]
    with db.conn:
        check_accounts()
        for password_hash, user_id in hashes:
            db.conn.execute(
                "UPDATE users SET password=?, password_updated_at=datetime('now'), must_change_password=0, "
                "remember_token=NULL, auto_login=0 WHERE id=?", (password_hash, user_id),
            )
    return len(entries)
