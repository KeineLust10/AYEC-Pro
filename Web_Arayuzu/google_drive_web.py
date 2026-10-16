"""Tenant-scoped Google Drive OAuth and backup upload helpers."""

from __future__ import annotations

import io
import json
from typing import Any


DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"


def validate_web_client_config(value: Any) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Select a Google OAuth client JSON file.")
    client = value.get("web")
    if not isinstance(client, dict):
        raise ValueError("Use a Google OAuth client configured as a Web application.")
    client_id = str(client.get("client_id") or "").strip()
    client_secret = str(client.get("client_secret") or "").strip()
    if not client_id.endswith(".apps.googleusercontent.com") or not client_secret:
        raise ValueError("The Google Web OAuth client ID or secret is missing.")
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def new_authorization(client_config: dict, redirect_uri: str, state: str) -> str:
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(client_config, scopes=[DRIVE_SCOPE], state=state)
    flow.redirect_uri = redirect_uri
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return authorization_url


def exchange_authorization(client_config: dict, redirect_uri: str, callback_url: str, state: str) -> str:
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(client_config, scopes=[DRIVE_SCOPE], state=state)
    flow.redirect_uri = redirect_uri
    flow.fetch_token(authorization_response=callback_url)
    if not flow.credentials or not flow.credentials.refresh_token:
        raise ValueError("Google did not return an offline refresh token. Reconnect and approve access.")
    return flow.credentials.to_json()


def upload_backup(token_json: str, filename: str, payload: bytes) -> tuple[str, str]:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload

    credentials_data = json.loads(token_json)
    credentials = Credentials.from_authorized_user_info(credentials_data, [DRIVE_SCOPE])
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials.valid:
        raise ValueError("Google Drive authorization has expired. Reconnect the account.")
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    media = MediaIoBaseUpload(io.BytesIO(payload), mimetype="application/x-sqlite3", resumable=True)
    result = service.files().create(
        body={"name": filename},
        media_body=media,
        fields="id,name,webViewLink",
    ).execute()
    file_id = str(result.get("id") or "")
    if not file_id:
        raise ValueError("Google Drive did not confirm the uploaded backup.")
    return file_id, credentials.to_json()
