"""Exercise session scope and atomic saves without real credentials."""
from email.message import Message
import json
from pathlib import Path
import tempfile
import unittest

from ayec_core.session import (load_session, protect_current_user, save_session,
                                unprotect_current_user, update_cookies)


class SessionTests(unittest.TestCase):
    def test_roundtrip_scope_and_legacy_compatibility(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session"
            # A reversible test codec; production clients supply their encryption.
            codec = lambda raw: raw[::-1]
            save_session(path, base_url="https://example.test", product_code="elek",
                         cookies={"ayec_session": "test-token"}, metadata={"tenant_id": "t1"}, protect=codec)
            cookies = {}
            self.assertEqual(load_session(path, base_url="https://example.test", product_code="elek",
                             cookies=cookies, unprotect=codec), {"tenant_id": "t1"})
            self.assertEqual(cookies, {"ayec_session": "test-token"})
            self.assertEqual(load_session(path, base_url="https://example.test", product_code="ciro",
                             cookies=cookies, unprotect=codec), {})
            self.assertEqual(cookies, {})
            path.write_bytes(codec(json.dumps({"base_url": "https://example.test", "cookies": {"ayec_session": "legacy"}}).encode()))
            load_session(path, base_url="https://example.test", product_code="elek", cookies=cookies, unprotect=codec)
            self.assertEqual(cookies["ayec_session"], "legacy")

    def test_failed_encryption_preserves_previous_session(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session"
            path.write_bytes(b"old")
            def failed(raw):
                raise OSError("encryption unavailable")
            with self.assertRaises(OSError):
                save_session(path, base_url="https://example.test", product_code="elek",
                             cookies={}, metadata={}, protect=failed)
            self.assertEqual(path.read_bytes(), b"old")

    def test_multiple_cookies_and_logout(self):
        headers = Message()
        headers.add_header("Set-Cookie", "ayec_session=one; HttpOnly; Path=/")
        headers.add_header("Set-Cookie", "csrf=two; Path=/")
        cookies = {}
        update_cookies(cookies, headers)
        self.assertEqual(cookies, {"ayec_session": "one", "csrf": "two"})
        update_cookies(cookies, {"Set-Cookie": "ayec_session=; Max-Age=0"})
        self.assertEqual(cookies, {"csrf": "two"})

    def test_current_user_codec_roundtrip(self):
        raw = b"central-session-fixture"
        self.assertEqual(unprotect_current_user(protect_current_user(raw)), raw)
