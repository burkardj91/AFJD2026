from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from quest_core import payload
from quest_store import SharedQuest

class SharedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "event.sqlite3"
        self.a, self.b = SharedQuest(self.path), SharedQuest(self.path)
        self.lea = self.a.activate("DEMO-264")
        self.alex = self.b.activate("DEMO-137")

    def tearDown(self):
        self.temp.cleanup()

    def test_cross_session_acceptance_and_repeat(self):
        self.a.scan(self.lea, payload("person", self.alex))
        self.assertIn((self.lea,self.alex), self.b.pending)
        self.b.confirm(self.alex,self.lea)
        self.assertEqual(self.a.people(self.lea), {self.alex})
        self.assertEqual(self.b.people(self.alex), {self.lea})
        self.b.confirm(self.alex,self.lea)
        self.assertEqual(len(self.a.connections),1)
        self.assertFalse(self.a.pending)

    def test_two_tablets_same_person(self):
        self.a.simulate_completion(self.lea)
        self.a.approve_draw(self.lea,"STAFF-01")
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda staff: SharedQuest(self.path).draw(self.lea,staff),["STAFF-01","STAFF-02"]))
        self.assertEqual(results[0],results[1])
        self.assertEqual(len(self.a.assignments),1)
        self.assertEqual(len(self.a.draw_log),1)
        self.assertIn(results[0],self.a.digital_cards)

    def test_two_tablets_different_people_and_restart(self):
        for p in [self.lea,self.alex]:
            self.a.simulate_completion(p)
            self.a.approve_draw(p,"STAFF-02")
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda args: SharedQuest(self.path).draw(*args),[(self.lea,"STAFF-01"),(self.alex,"STAFF-02")]))
        self.assertNotEqual(*results)
        self.assertEqual(len(SharedQuest(self.path).assignments),2)

    def test_draw_rules_and_rollback(self):
        with self.assertRaises(ValueError):
            self.a.draw(self.lea,"STAFF-01")
        self.assertFalse(self.a.assignments)
        self.a.simulate_completion(self.lea)
        with self.assertRaises(ValueError):
            self.a.draw(self.lea,"STAFF-01")
        self.a.approve_draw(self.lea,"STAFF-01")
        with self.assertRaises(ValueError):
            self.a.draw(self.lea,"participant")
        self.assertFalse(self.a.assignments)

if __name__ == "__main__":
    unittest.main()
