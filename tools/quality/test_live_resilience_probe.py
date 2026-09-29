"""Safety tests for the controlled live resilience probe."""

import os
import unittest
from unittest.mock import Mock, patch

import live_resilience_probe as probe


class LiveProbeSafetyTests(unittest.TestCase):
    def test_missing_mutation_variables_are_reported(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(set(probe._mutation_preflight()), set(probe.REQUIRED_MUTATION_VARS))

    def test_missing_variables_stop_before_any_post(self):
        fake_session = Mock()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Missing live mutation variables"):
                probe._execute_mutation_flow(fake_session)
        fake_session.request.assert_not_called()

    def test_fixture_snapshot_is_sqlite_and_disposed(self):
        holder, path = probe._make_fixture_database()
        try:
            self.assertTrue(path.is_file())
            connection = probe.sqlite3.connect(path)
            try:
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone(), ("ok",))
                self.assertEqual(connection.execute("SELECT value FROM verification").fetchone()[0],
                                 "AYEC live verification")
            finally:
                connection.close()
        finally:
            holder.cleanup()
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
