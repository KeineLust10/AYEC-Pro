import sqlite3
import tempfile
import unittest
from pathlib import Path

from ayec_core.backup import snapshot_upload


class SnapshotTests(unittest.TestCase):
    def upload(self, path, **overrides):
        options = dict(product_code="barkod_okuyucu", program_name="AYEC Pro Barkod Okuyucu",
                       database_name="Barkod-AYEC.db")
        options.update(overrides)
        return snapshot_upload(path, **options)

    def test_snapshot_includes_committed_wal_and_excludes_pending_transaction(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "live.db"
            connection = sqlite3.connect(source)
            try:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("CREATE TABLE items (name TEXT)")
                connection.execute("INSERT INTO items VALUES ('committed')")
                connection.commit()
                connection.execute("INSERT INTO items VALUES ('pending')")
                payload, headers = self.upload(source)
                restored = sqlite3.connect(":memory:")
                try:
                    restored.deserialize(payload)
                    self.assertEqual(restored.execute("SELECT name FROM items").fetchall(), [("committed",)])
                finally:
                    restored.close()
                self.assertEqual(headers["X-AYEC-Product-Code"], "barkod_okuyucu")
                self.assertEqual(headers["X-AYEC-Backup-Name"], "Barkod-AYEC.db")
            finally:
                connection.close()

    def test_missing_file_is_not_created_and_corrupt_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "missing.db"
            with self.assertRaises(FileNotFoundError):
                self.upload(source)
            self.assertFalse(source.exists())
            source.write_bytes(b"invalid SQLite data")
            with self.assertRaises(sqlite3.DatabaseError):
                self.upload(source)

    def test_header_injection_is_rejected_before_reading_file(self):
        with self.assertRaises(ValueError):
            self.upload("missing.db", program_name="Program\r\nInjected: yes")
