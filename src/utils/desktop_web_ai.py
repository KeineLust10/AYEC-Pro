"""Tenant-scoped web access to the desktop Jarvis assistant service."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def desktop_assistant_status(database_path: str | Path) -> dict:
    from src.database import Database

    db = Database(str(database_path), init_mode="connection_only")
    try:
        key_present = bool(db.get_setting("gemini_api_key", ""))
        try:
            sdk_available = importlib.util.find_spec("google.genai") is not None
        except ModuleNotFoundError:
            sdk_available = False
        return {
            "configured": bool(key_present and sdk_available),
            "key_present": key_present,
            "model": str(db.get_setting("gemini_model", "") or "gemini-3.6-flash"),
        }
    finally:
        db.close()


def query_desktop_assistant(database_path: str | Path, question: str) -> dict:
    question = str(question or "").strip()
    if not question:
        raise ValueError("Question is required.")
    if len(question) > 1200:
        raise ValueError("Question is too long.")

    from src.database import Database
    from src.utils.ai_service import AIService

    db = Database(str(database_path), init_mode="connection_only")
    try:
        db.conn.execute("PRAGMA query_only=ON")
        service = AIService(db)
        result = service.get_smart_response(question)
        if not isinstance(result, dict):
            raise RuntimeError("Assistant returned an invalid response.")
        answer = str(result.get("answer") or "")[:12000]
        error = str(result.get("error") or "")[:500]
        for api_key in service.api_keys:
            secret = str(api_key or "").strip()
            if len(secret) >= 8:
                answer = answer.replace(secret, "[MASKED]")
                error = error.replace(secret, "[MASKED]")
        return {
            "success": bool(result.get("success")),
            "answer": answer,
            "error": error,
            "model": str(db.get_setting("gemini_model", "") or "gemini-3.6-flash"),
        }
    finally:
        db.close()
