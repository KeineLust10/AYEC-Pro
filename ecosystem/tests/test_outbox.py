import tempfile
import unittest
from pathlib import Path

from ayec_core.outbox import DurableOutbox


class OutboxTests(unittest.TestCase):
    def create(self, path, product="elek"):
        return DurableOutbox(path, product_code=product, tenant_id="tenant-1",
                             installation_id="install-1")

    def test_queue_survives_restart_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "outbox.db"
            first = self.create(path)
            item = first.enqueue("backup_upload", {"path": "fixture.db"},
                                 idempotency_key="backup-1", now=10)
            self.assertEqual(item, first.enqueue("backup_upload", {},
                                                 idempotency_key="backup-1", now=11))
            reopened = self.create(path)
            self.assertEqual(reopened.due(now=10)[0]["payload"]["path"], "fixture.db")

    def test_retry_is_delayed_and_scope_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "outbox.db"
            outbox = self.create(path)
            item = outbox.enqueue("backup_upload", {}, now=100)
            outbox.mark_retry(item, "offline", now=100, jitter=False)
            self.assertEqual(outbox.due(now=159), [])
            self.assertEqual(outbox.due(now=160)[0]["attempts"], 1)
            self.assertEqual(self.create(path, product="ciro").due(now=1000), [])
            outbox.mark_done(item)
            self.assertEqual(outbox.due(now=1000), [])

    def test_invalid_scope_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                DurableOutbox(Path(directory) / "outbox.db", product_code="elek",
                              tenant_id="", installation_id="install-1")

    def test_command_journal_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            outbox = self.create(Path(directory) / "outbox.db")
            first = outbox.record_command_result(17, {"success": True, "value": 1})
            second = outbox.record_command_result(17, {"success": False})
            self.assertEqual(first["value"], 1)
            self.assertEqual(second["success"], True)
            self.assertEqual(outbox.command_result(17)["value"], 1)

    def test_command_completion_can_wait_for_network(self):
        with tempfile.TemporaryDirectory() as directory:
            outbox = self.create(Path(directory) / "outbox.db")
            payload = {"command_id": 17, "success": True, "result": {"queued": True}}
            outbox.record_command_result(17, payload)
            outbox.enqueue("command_complete", payload,
                           idempotency_key="command-complete:17", now=0)
            self.assertEqual(outbox.due(now=0)[0]["operation"], "command_complete")

    def test_same_key_and_command_are_independent_across_scopes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "outbox.db"
            first = self.create(path)
            other = self.create(path, product="ciro")
            one = first.enqueue("backup_upload", {"path": "elek.db"}, idempotency_key="same", now=0)
            two = other.enqueue("backup_upload", {"path": "ciro.db"}, idempotency_key="same", now=0)
            self.assertNotEqual(one, two)
            first.record_command_result(17, {"product": "elek"})
            self.assertIsNone(other.command_result(17))
            other.record_command_result(17, {"product": "ciro"})
            self.assertEqual(first.command_result(17)["product"], "elek")
            self.assertEqual(other.command_result(17)["product"], "ciro")
