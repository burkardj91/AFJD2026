import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from dataclasses import dataclass, field
import quest_core
from quest_store import SharedQuest

class ReloadTests(unittest.TestCase):
    def test_new_instances_resolve_current_model(self):
        @dataclass
        class UpdatedQuest(quest_core.Quest):
            reload_marker: int = field(default_factory=lambda:42)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'demo.db'
            SharedQuest(path)
            with patch.object(quest_core,'Quest',UpdatedQuest):
                state=SharedQuest(path)
                self.assertEqual(state.reload_marker,42)
                self.assertEqual(state.reset_epoch,0)

    def test_old_saved_state_gets_new_defaults_without_data_loss(self):
        with tempfile.TemporaryDirectory() as folder:
            state=SharedQuest(Path(folder)/'demo.db')
            p=state.activate('DEMO-264');state.simulate_completion(p)
            with state.connect() as db:
                body=json.loads(db.execute('SELECT body FROM event WHERE id=1').fetchone()[0])
                body.pop('reset_epoch');body.pop('raffle')
                db.execute('UPDATE event SET body=? WHERE id=1',(json.dumps(body),))
            reopened=SharedQuest(state.path)
            self.assertEqual(reopened.reset_epoch,0)
            self.assertEqual(reopened.raffle,{})
            self.assertEqual(len(reopened.completed(p)),4)
