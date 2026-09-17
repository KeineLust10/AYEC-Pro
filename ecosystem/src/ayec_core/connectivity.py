"""Stable error classes used by offline-capable AYEC clients."""

import socket
from urllib.error import HTTPError, URLError


RETRYABLE = {"offline", "dns", "tls", "timeout", "rate_limited", "server"}


def classify_error(error):
    status = error.code if isinstance(error, HTTPError) else getattr(error, 'status_code', None)
    if status is not None:
        if status == 401:
            return "authentication"
        if status == 403:
            return "authorization"
        if status == 409:
            return "conflict"
        if status == 429:
            return "rate_limited"
        if status >= 500:
            return "server"
        return "request"
    cause = getattr(error, '__cause__', None)
    if cause is not None and cause is not error:
        return classify_error(cause)
    reason = error.reason if isinstance(error, URLError) else error
    if isinstance(reason, socket.gaierror):
        return "dns"
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "timeout"
    name = type(reason).__name__.lower()
    message = str(reason).lower()
    if "ssl" in name or "certificate" in message or "tls" in message:
        return "tls"
    if isinstance(reason, OSError):
        return "offline"
    return "unknown"


def is_retryable(error):
    return classify_error(error) in RETRYABLE
