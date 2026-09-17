"""Authenticated WebSocket listener for small desktop sync notifications."""

from __future__ import annotations

import base64
import json
import secrets
import socket
import ssl
import threading
from pathlib import Path
from urllib.parse import urlsplit

from PyQt6.QtCore import QThread, pyqtSignal

from src.utils.desktop_web_sync import configured_sync_url, sync_session_path
from src.utils.path_helper import PathHelper
from src.utils.web_sync_client import WebSyncClient


class DesktopSyncEventWorker(QThread):
    """Keep a best-effort WebSocket notification channel open for one desktop."""

    sync_requested = pyqtSignal()
    event_received = pyqtSignal(dict)
    connection_changed = pyqtSignal(bool)

    def __init__(self, db_name: str = "ayecpro.db", parent=None):
        super().__init__(parent)
        self.db_name = str(db_name or "ayecpro.db")
        self._stopped = threading.Event()
        self._connection_lock = threading.Lock()
        self._connection: socket.socket | None = None
        self._receive_buffer = bytearray()

    def stop(self) -> None:
        self._stopped.set()
        with self._connection_lock:
            connection = self._connection
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                connection.close()
            except OSError:
                pass

    def _device_id(self) -> str:
        state_path = Path(f"{PathHelper.get_db_path(self.db_name)}.ayec-sync.json")
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            return str(dict(state or {}).get("machine_id") or "")[:128]
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return ""

    def _connect(self, cookies: dict[str, str], device_id: str) -> socket.socket:
        parsed = urlsplit(configured_sync_url())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise RuntimeError("Invalid web sync URL")
        secure = parsed.scheme == "https"
        port = parsed.port or (443 if secure else 80)
        connection = socket.create_connection((parsed.hostname, port), timeout=20)
        if secure:
            connection = ssl.create_default_context().wrap_socket(
                connection,
                server_hostname=parsed.hostname,
            )
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        host = parsed.hostname if parsed.port is None else f"{parsed.hostname}:{parsed.port}"
        path = (parsed.path.rstrip("/") + "/api/sync/events") if parsed.path else "/api/sync/events"
        headers = [
            f"GET {path} HTTP/1.1",
            f"Host: {host}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            "Sec-WebSocket-Version: 13",
            f"Sec-WebSocket-Key: {key}",
            "User-Agent: AYEC-Pro-Desktop-Sync/1.0",
        ]
        if cookies:
            headers.append("Cookie: " + "; ".join(f"{name}={value}" for name, value in cookies.items()))
        if device_id:
            headers.append(f"X-AYEC-Device-ID: {device_id}")
        connection.sendall(("\r\n".join(headers) + "\r\n\r\n").encode("ascii"))
        response = bytearray()
        while b"\r\n\r\n" not in response:
            chunk = connection.recv(4096)
            if not chunk:
                raise RuntimeError("WebSocket server closed the connection")
            response.extend(chunk)
            if len(response) > 16384:
                raise RuntimeError("WebSocket response headers are too large")
        head, _, remaining = bytes(response).partition(b"\r\n\r\n")
        status_line = head.split(b"\r\n", 1)[0]
        if b" 101 " not in status_line:
            raise RuntimeError(head.decode("iso-8859-1", errors="replace").split("\r\n", 1)[0])
        self._receive_buffer = bytearray(remaining)
        connection.settimeout(70)
        return connection

    def _read_exact(self, connection: socket.socket, size: int) -> bytes:
        result = bytearray()
        if self._receive_buffer:
            take = min(size, len(self._receive_buffer))
            result.extend(self._receive_buffer[:take])
            del self._receive_buffer[:take]
        while len(result) < size:
            chunk = connection.recv(size - len(result))
            if not chunk:
                raise ConnectionError("WebSocket connection closed")
            result.extend(chunk)
        return bytes(result)

    def _read_frame(self, connection: socket.socket) -> tuple[int, bytes]:
        first, second = self._read_exact(connection, 2)
        opcode = first & 0x0F
        length = second & 0x7F
        if length == 126:
            length = int.from_bytes(self._read_exact(connection, 2), "big")
        elif length == 127:
            length = int.from_bytes(self._read_exact(connection, 8), "big")
        if length > 65535:
            raise RuntimeError("WebSocket event is too large")
        return opcode, self._read_exact(connection, length)

    def _send_frame(self, connection: socket.socket, opcode: int, payload: bytes = b"") -> None:
        mask = secrets.token_bytes(4)
        size = len(payload)
        if size <= 125:
            header = bytes([0x80 | opcode, 0x80 | size])
        elif size <= 65535:
            header = bytes([0x80 | opcode, 0x80 | 126]) + size.to_bytes(2, "big")
        else:
            raise RuntimeError("WebSocket control frame is too large")
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        connection.sendall(header + mask + masked)

    def run(self) -> None:
        retry_delay = 1
        while not self._stopped.is_set():
            connection = None
            connected = False
            try:
                client = WebSyncClient(
                    configured_sync_url(),
                    verify_tls=not configured_sync_url().lower().startswith("http://"),
                )
                client.load_session(sync_session_path())
                if not client.cookies:
                    return
                connection = self._connect(client.cookies, self._device_id())
                with self._connection_lock:
                    self._connection = connection
                connected = True
                retry_delay = 1
                self.connection_changed.emit(True)
                while not self._stopped.is_set():
                    opcode, payload = self._read_frame(connection)
                    if opcode == 0x08:
                        break
                    if opcode == 0x09:
                        self._send_frame(connection, 0x0A, payload)
                        continue
                    if opcode != 0x01:
                        continue
                    event = json.loads(payload.decode("utf-8"))
                    if isinstance(event, dict):
                        self.event_received.emit(event)
                        if event.get("type") == "sync_delta":
                            self.sync_requested.emit()
            except (OSError, RuntimeError, UnicodeError, ValueError, json.JSONDecodeError):
                pass
            finally:
                with self._connection_lock:
                    self._connection = None
                if connection is not None:
                    try:
                        connection.close()
                    except OSError:
                        pass
                if connected:
                    self.connection_changed.emit(False)
            if not self._stopped.is_set():
                self._stopped.wait(retry_delay)
                retry_delay = min(retry_delay * 2, 30)
