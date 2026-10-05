import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from quest_store import SharedQuest
from quest_database import PostgresConnection


class InfrastructureTests(unittest.TestCase):
    def test_snapshots_detached_and_follow_other_clients(self):
        with tempfile.TemporaryDirectory() as folder:
            a = SharedQuest(Path(folder)/"db")
            b = SharedQuest(a.path)
            snapshot = a.snapshot()
            snapshot.active.add("not-a-real-person")
            self.assertNotIn("not-a-real-person", a.active)
            person = b.activate("DEMO-264")
            self.assertIn(person, a.active)
            with a.connect() as db:
                self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0], "wal")

    def test_unrelated_change_does_not_refresh_participant(self):
        with tempfile.TemporaryDirectory() as folder:
            q = SharedQuest(Path(folder)/"db")
            lea = q.activate("DEMO-264")
            before = q.viewer_revision(lea)
            alex = q.activate("DEMO-137")
            self.assertEqual(before, q.viewer_revision(lea))
            q.scan(alex, q.roster()[lea]["id"])
            self.assertNotEqual(before, q.viewer_revision(lea))

    def test_maintenance_before_deadline_is_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            from quest_core import Quest
            seed = Quest()
            seed.recap_deadline = "2999-01-01T00:00:00+00:00"
            q = SharedQuest(Path(folder)/"db", seed=seed)
            with patch.object(q, "resolve_raffle") as raffle, patch.object(q, "queue_due_recaps") as recap:
                q.maintenance()
            raffle.assert_not_called()
            recap.assert_not_called()

    def test_postgres_sql_adapter_keeps_parameters_bound(self):
        connection = Mock()
        db = PostgresConnection(connection)
        db.execute("INSERT OR IGNORE INTO event VALUES(1,?,0)", ("private",))
        connection.execute.assert_called_with("INSERT INTO event VALUES(1,%s,0) ON CONFLICT DO NOTHING", ("private",))
        db.execute("BEGIN IMMEDIATE")
        connection.execute.assert_called_with("SELECT pg_advisory_xact_lock(20261008)")
        db.execute("CREATE TABLE token (expires REAL)")
        connection.execute.assert_called_with("CREATE TABLE token (expires DOUBLE PRECISION)", ())
