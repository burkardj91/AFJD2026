"""Rules from 2026_Networking Quest_AFJD.pdf, including upgrade behaviour."""
import tempfile
import unittest
from pathlib import Path
from quest_core import Quest, payload
from quest_store import SharedQuest


class PublishedRulesTests(unittest.TestCase):
    def test_retail_requires_person_and_three_distinct_people_exclude_reps(self):
        q = Quest()
        p = q.activate('DEMO-264')
        for station in ['sv-5w8j', 'in-3p9d', 're-lidl']:
            q.scan(p, payload('station', station))
        q.scan(p, payload('person', 'p-svial'))
        self.assertFalse(q.completed(p))
        q.scan(p, payload('person', 'p-3nm9q4'))
        self.assertEqual(q.completed(p), {'Detailhandel'})
        q.scan(p, payload('person', 'p-3nm9q4'))
        self.assertNotIn('Vernetzen', q.completed(p))
        q.scan(p, payload('person', 'p-6wx5t1'))
        self.assertEqual(q.completed(p), {'Detailhandel'})
        self.assertEqual(len(q.people(p)), 3)
        for target in ["p-2bc7r8", "p-4jf9n3", "p-9ls6d2"]:
            q.scan(p, payload("person", target))
        self.assertIn("Vernetzen", q.completed(p))

    def test_imported_mentor_counts_but_general_svial_does_not(self):
        q = Quest()
        p = q.activate('DEMO-264')
        mentor = q.import_registrations('ADMIN-01', [{
            'name':'Demo Mentorin', 'email':'mentor@example.test', 'annotation':'Mentor'}])[0]
        q.scan(p, payload('person', 'p-svial'))
        self.assertNotIn('SVIAL-Mentoring', q.completed(p))
        q.scan(p, payload('person', mentor))
        self.assertIn('SVIAL-Mentoring', q.completed(p))

    def test_catalog_upgrade_rechecks_quests_without_losing_reserved_prize(self):
        seed = Quest()
        p = seed.activate('DEMO-264')
        seed.catalog_version = 2
        seed.unlocked.add(p)
        seed.draw_approvals[p] = {'staff':'STAFF-01'}
        with tempfile.TemporaryDirectory() as folder:
            q = SharedQuest(Path(folder)/'event.db', seed=seed)
            self.assertNotIn(p, q.unlocked)
            self.assertNotIn(p, q.draw_approvals)
        seed.assignments['r-7mn4b2'] = p
        with tempfile.TemporaryDirectory() as folder:
            q = SharedQuest(Path(folder)/'event.db', seed=seed)
            self.assertIn(p, q.unlocked)
            self.assertEqual(q.assignments['r-7mn4b2'], p)

    def test_two_distinct_quests_unlock_and_allow_one_draw(self):
        q=Quest();p=q.activate("DEMO-264")
        q.scan(p,payload("station","fo-8b4q"))
        q.scan(p,payload("station","fo-8b4q"))
        self.assertNotIn(p,q.unlocked)
        with self.assertRaises(ValueError):q.approve_draw(p,"STAFF-01")
        q.scan(p,payload("station","future-apero"))
        self.assertEqual(len(q.completed(p)),2)
        self.assertIn(p,q.unlocked)
        q.approve_draw(p,"STAFF-01")
        card=q.draw(p,"STAFF-01")
        self.assertEqual(q.draw(p,"STAFF-02"),card)

    def test_existing_two_quest_progress_unlocks_without_changing_identity(self):
        seed=Quest()
        p=seed.import_registrations("ADMIN-01",[{"name":"Existing Person","email":"existing@example.test","source_id":"existing"}])[0]
        seed.demo_login(seed.registrations[p]["code"])
        for station in ["fo-8b4q","future-apero"]:seed.scan(p,payload("station",station))
        seed.unlocked.discard(p);seed.catalog_version=4
        original=dict(seed.registrations[p]);visits=set(seed.visits[p])
        with tempfile.TemporaryDirectory() as folder:
            q=SharedQuest(Path(folder)/"db",seed=seed)
            self.assertIn(p,q.unlocked)
            self.assertEqual(q.registrations[p],original)
            self.assertEqual(q.visits[p],visits)
            q.approve_draw(p,"STAFF-01")
            card=q.draw(p,"STAFF-01")
            self.assertEqual(SharedQuest(q.path).assignments[card],p)
