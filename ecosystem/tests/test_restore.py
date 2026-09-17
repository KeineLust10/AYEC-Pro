"""Restore regression tests use disposable SQLite databases only."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import hashlib

from ayec_core.restore import apply_pending_restore, stage_restore


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name) / "local.db"
        self.remote = Path(self.directory.name) / "remote.db"
        for path, value in ((self.target, 1), (self.remote, 2)):
            with closing(sqlite3.connect(path)) as conn:
                conn.execute("CREATE TABLE products(value INTEGER)")
                conn.execute("INSERT INTO products VALUES (?)", (value,))
                conn.commit()
        self.command = {"id": 7, "command_type": "restore_backup",
                        "payload": {"backup_id": 9, "product_code": "barkod_okuyucu"}}

    def stage(self):
        return stage_restore(self.command, self.target, lambda _: self.remote.read_bytes(),
                             product_code="barkod_okuyucu", required_tables=("products",))

    def test_restore_keeps_previous_data_and_is_idempotent(self):
        self.stage()
        self.stage()
        result = apply_pending_restore(self.target, product_code="barkod_okuyucu", required_tables=("products",))
        for path, expected in ((self.target, 2), (result["before_backup"], 1)):
            with closing(sqlite3.connect(path)) as conn:
                self.assertEqual(conn.execute("SELECT value FROM products").fetchone()[0], expected)
        self.assertFalse(apply_pending_restore(self.target)["applied"])

    def test_tampered_staging_never_changes_local_data(self):
        original = self.target.read_bytes()
        self.stage()
        self.target.with_suffix(".db.pending-restore").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "checksum"):
            apply_pending_restore(self.target)
        self.assertEqual(self.target.read_bytes(), original)

    def test_wrong_product_and_schema_are_rejected(self):
        self.command["payload"]["product_code"] = "elek"
        with self.assertRaisesRegex(ValueError, "another product"):
            self.stage()
        self.command["payload"]["product_code"] = "barkod_okuyucu"
        with self.assertRaisesRegex(ValueError, "schema"):
            stage_restore(self.command, self.target, lambda _: self.remote.read_bytes(),
                          product_code="barkod_okuyucu", required_tables=("sales",))

    def test_missing_marker_does_not_apply_orphaned_file(self):
        self.target.with_suffix(".db.pending-restore").write_bytes(self.remote.read_bytes())
        self.assertFalse(apply_pending_restore(self.target)["applied"])

    def test_failed_health_check_rolls_back_without_losing_old_records(self):
        self.stage()
        result = apply_pending_restore(self.target, required_tables=("products",),
                                       health_check=lambda path: False)
        self.assertEqual(result["state"], "ROLLED_BACK")
        with closing(sqlite3.connect(self.target)) as connection:
            self.assertEqual(connection.execute("SELECT value FROM products").fetchone()[0], 1)
        self.assertFalse(apply_pending_restore(self.target)["applied"])

    def test_process_loss_after_replacement_recovers_from_journal(self):
        self.stage()
        def terminated(path):
            raise SystemExit("simulated power loss")
        with self.assertRaises(SystemExit):
            apply_pending_restore(self.target, required_tables=("products",), health_check=terminated)
        result = apply_pending_restore(self.target, required_tables=("products",))
        self.assertEqual(result["state"], "ROLLED_BACK")
        with closing(sqlite3.connect(self.target)) as connection:
            self.assertEqual(connection.execute("SELECT value FROM products").fetchone()[0], 1)

    def test_remote_scope_checksum_size_and_confirmation_are_required(self):
        raw = self.remote.read_bytes()
        self.command["payload"].update(tenant_id="t1", hardware_id="pc1", installation_id="i1",
                                       sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        options = dict(product_code="barkod_okuyucu", tenant_id="t1", hardware_id="pc1",
                       installation_id="i1", require_confirmation=True)
        with self.assertRaises(PermissionError):
            stage_restore(self.command, self.target, lambda _: raw, **options)
        with self.assertRaises(ValueError):
            stage_restore(self.command, self.target, lambda _: raw, **dict(options, tenant_id="t2", confirmed=True))
        self.command["payload"]["size_bytes"] += 1
        with self.assertRaises(ValueError):
            stage_restore(self.command, self.target, lambda _: raw, **dict(options, confirmed=True))
        self.assertFalse(self.target.with_suffix(".db.pending-restore.json").exists())
