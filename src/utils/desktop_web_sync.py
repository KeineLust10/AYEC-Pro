"""Desktop web synchronization orchestration."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import date

from PyQt6.QtCore import QThread, pyqtSignal

from src.utils.path_helper import PathHelper
from src.utils.web_sync_client import (
    DEFAULT_WEB_SYNC_URL,
    WEB_SYNC_SESSION_FILE,
    WebSyncClient,
    WebSyncError,
)


def configured_sync_url() -> str:
    return str(os.environ.get("AYEC_WEB_SYNC_URL") or DEFAULT_WEB_SYNC_URL).strip().rstrip("/")


def configured_tenant_id(db=None) -> str:
    env_value = str(os.environ.get("AYEC_WEB_SYNC_TENANT_ID") or "").strip()
    if env_value:
        return env_value
    if db is not None:
        try:
            return str(db.get_setting("web_sync_tenant_id", "") or "").strip()
        except Exception:
            pass
    return ""


def sync_session_path() -> str:
    return os.path.join(PathHelper.get_app_data_dir(), WEB_SYNC_SESSION_FILE)


def local_provisioning_payload(
    db_name: str,
    username: str,
    password: str,
    provision_invite_code: str = "",
) -> dict:
    """Read the completed local setup data needed to create its remote tenant."""
    db_path = PathHelper.get_db_path(db_name)
    payload = {
        "username": str(username or "").strip(),
        "password": str(password or ""),
        "full_name": "",
        "email": "",
        "phone": "",
        "company_name": "",
        "company_email": "",
        "company_address": "",
        "installation_lat": None,
        "installation_lng": None,
        "installation_address": "",
        "sector": "teknik_servis",
    }
    with closing(sqlite3.connect(db_path, timeout=10)) as conn:
        conn.row_factory = sqlite3.Row
        tables = {
            str(row[0])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "company_info" in tables:
            company = conn.execute("SELECT * FROM company_info LIMIT 1").fetchone()
            if company:
                payload["company_name"] = str(company["company_name"] or "").strip()
                payload["full_name"] = str(company["authorized_person"] or "").strip()
                payload["phone"] = str(company["phone"] or "").strip()
                payload["company_email"] = str(company["email"] or "").strip()
                payload["company_address"] = str(company["address"] or "").strip()
        if "users" in tables:
            user = conn.execute(
                "SELECT * FROM users WHERE username=? COLLATE NOCASE LIMIT 1",
                (payload["username"],),
            ).fetchone()
            if user:
                user_columns = set(user.keys())
                payload["full_name"] = str(
                    (user["full_name"] if "full_name" in user_columns else "")
                    or (user["name"] if "name" in user_columns else "")
                    or payload["full_name"]
                    or payload["username"]
                ).strip()
                payload["email"] = str(
                    (user["email"] if "email" in user_columns else "")
                    or payload["company_email"]
                    or ""
                ).strip()
        if "settings" in tables:
            location_settings = {
                str(row[0]): row[1]
                for row in conn.execute(
                    "SELECT key,value FROM settings WHERE key IN "
                    "('installation_lat','installation_lng','installation_address',"
                    "'map_default_lat','map_default_lng','company_address')"
                )
            }
            lat_value = location_settings.get("installation_lat") or location_settings.get("map_default_lat")
            lng_value = location_settings.get("installation_lng") or location_settings.get("map_default_lng")
            try:
                if str(lat_value or "").strip() and str(lng_value or "").strip():
                    payload["installation_lat"] = float(lat_value)
                    payload["installation_lng"] = float(lng_value)
            except (TypeError, ValueError):
                payload["installation_lat"] = None
                payload["installation_lng"] = None
            payload["installation_address"] = str(
                location_settings.get("installation_address")
                or location_settings.get("company_address")
                or payload["company_address"]
                or ""
            ).strip()
            row = conn.execute(
                "SELECT value FROM settings WHERE key='current_sector' LIMIT 1"
            ).fetchone()
            if row and str(row[0] or "").strip():
                payload["sector"] = str(row[0]).strip()
        if "internal_settings" in tables:
            row = conn.execute(
                "SELECT value FROM internal_settings WHERE key='current_sector' LIMIT 1"
            ).fetchone()
            if row and str(row[0] or "").strip():
                payload["sector"] = str(row[0]).strip()
    if not payload["email"]:
        payload["email"] = payload["company_email"]
    if not payload["full_name"]:
        payload["full_name"] = payload["username"]
    if str(provision_invite_code or "").strip():
        payload["provision_invite_code"] = str(provision_invite_code).strip()
    return payload


class DesktopSectorSyncWorker(QThread):
    completed = pyqtSignal(bool, object)

    def __init__(self, sector: str, parent=None):
        super().__init__(parent)
        self.sector = str(sector or "").strip()

    def run(self):
        try:
            url = configured_sync_url()
            client = WebSyncClient(url, verify_tls=not url.lower().startswith("http://"))
            metadata = client.load_session(sync_session_path())
            if not client.cookies:
                self.completed.emit(True, {"ok": True, "skipped": True})
                return
            result = client.update_sector(self.sector)
            result["session"] = metadata
            self.completed.emit(True, result)
        except Exception as exc:
            self.completed.emit(False, {"ok": False, "error": str(exc)})


class DesktopWebSyncWorker(QThread):
    completed = pyqtSignal(bool, object)

    def __init__(
        self,
        db_name="ayecpro.db",
        username="",
        password="",
        tenant_id="",
        provision_invite_code="",
        allow_new_tenant=False,
        parent=None,
    ):
        super().__init__(parent)
        self.db_name = db_name or "ayecpro.db"
        self.username = str(username or "").strip()
        self.password = str(password or "")
        self.tenant_id = str(tenant_id or "").strip()
        self.provision_invite_code = str(provision_invite_code or "").strip()
        self.allow_new_tenant = bool(allow_new_tenant)

    def run(self):
        try:
            url = configured_sync_url()
            client = WebSyncClient(url, verify_tls=not url.lower().startswith("http://"))
            try:
                metadata = client.load_session(sync_session_path())
            except Exception:
                metadata = {}
                client.cookies = {}
            session_user = str(metadata.get("username") or "").strip()
            session_tenant = str(metadata.get("tenant_id") or "").strip()
            wrong_user = bool(
                self.username
                and session_user
                and self.username.casefold() != session_user.casefold()
            )
            wrong_tenant = bool(
                self.tenant_id
                and session_tenant
                and self.tenant_id != session_tenant
            )
            if wrong_user or wrong_tenant:
                client.cookies = {}
                metadata = {}
                WebSyncClient.clear_session(sync_session_path())
            if client.cookies and not (self.username and self.password):
                try:
                    status = client.auth_status()
                except WebSyncError as error:
                    if "oturum" not in str(error).casefold():
                        raise
                    status = {"authenticated": False}
                if not status.get("authenticated"):
                    client.cookies = {}
                    metadata = {}
                    WebSyncClient.clear_session(sync_session_path())
            if self.username and self.password:
                initial_pull_pending = bool(metadata.get("initial_pull_pending"))
                provision_requested = bool(
                    self.provision_invite_code and not (self.tenant_id or session_tenant)
                )
                if provision_requested:
                    login_result = client.provision_desktop_tenant(
                        local_provisioning_payload(
                            self.db_name,
                            self.username,
                            self.password,
                            self.provision_invite_code,
                        )
                    )
                    initial_pull_pending = False
                else:
                    try:
                        login_result = client.login(
                            self.username,
                            self.password,
                            remember=True,
                            tenant_id=self.tenant_id or None,
                        )
                    except WebSyncError:
                        can_create_first_tenant = bool(
                            self.allow_new_tenant
                            and not (self.tenant_id or session_tenant)
                        )
                        if not can_create_first_tenant:
                            raise
                        login_result = client.provision_desktop_tenant(
                            local_provisioning_payload(
                                self.db_name,
                                self.username,
                                self.password,
                            )
                        )
                        initial_pull_pending = False
                remote_user = dict(login_result.get("user") or {})
                metadata = {
                    "username": remote_user.get("username") or self.username,
                    "tenant_id": remote_user.get("tenant_id") or self.tenant_id,
                    "company_name": remote_user.get("company_name") or "",
                    "initial_pull_pending": initial_pull_pending,
                }
                client.save_session(sync_session_path(), metadata)
            elif not client.cookies:
                WebSyncClient.clear_session(sync_session_path())
                raise WebSyncError(
                    "Sunucu oturumu bulunamad\u0131. Kay\u0131tl\u0131 hesab\u0131n\u0131zla yeniden giri\u015f yap\u0131n."
                )

            initial_pull = bool(metadata.get("initial_pull_pending"))
            result = client.sync_sqlite(
                PathHelper.get_db_path(self.db_name),
                push_local=not initial_pull,
            )
            try:
                company_payload = local_provisioning_payload(
                    self.db_name, self.username, ""
                )
                if (
                    company_payload.get("installation_address")
                    or company_payload.get("company_address")
                    or (
                        company_payload.get("installation_lat") is not None
                        and company_payload.get("installation_lng") is not None
                    )
                ):
                    result["company_location"] = client.update_company_location({
                        "installation_lat": company_payload.get("installation_lat"),
                        "installation_lng": company_payload.get("installation_lng"),
                        "installation_address": company_payload.get("installation_address")
                        or company_payload.get("company_address")
                        or "",
                    })
            except WebSyncError as location_error:
                result["company_location_warning"] = str(location_error)
            if initial_pull and result.get("ok"):
                metadata["initial_pull_pending"] = False
            staged_restore = None
            update_requests = []
            for command in client.pending_commands():
                try:
                    if command.get("command_type") == "restore_backup":
                        staged_restore = client.stage_restore_command(
                            command,
                            PathHelper.get_db_path(self.db_name),
                        )
                        command_result = staged_restore
                    elif command.get("command_type") == "deploy_update":
                        command_result = dict(command.get("payload") or {})
                        update_requests.append(command_result)
                    else:
                        raise WebSyncError("Unsupported desktop command")
                    client.complete_command(
                        int(command.get("id") or 0), True, command_result
                    )
                except Exception as command_error:
                    client.complete_command(
                        int(command.get("id") or 0),
                        False,
                        {"error": str(command_error)},
                    )
            today_text = date.today().isoformat()
            backup_result = None
            if result.get("ok") and str(metadata.get("last_support_backup_date") or "") != today_text:
                backup_result = client.upload_backup(PathHelper.get_db_path(self.db_name))
                metadata["last_support_backup_date"] = today_text
            client.save_session(sync_session_path(), metadata)
            if staged_restore:
                result["restore_pending"] = staged_restore
            if update_requests:
                result["update_requests"] = update_requests
            if backup_result:
                result["support_backup"] = backup_result
            result["session"] = metadata
            self.completed.emit(bool(result.get("ok")), result)
        except Exception as exc:
            self.completed.emit(False, {"ok": False, "error": str(exc)})
