import tempfile
import unittest
from pathlib import Path
from quest_core import Quest, ORGANISATIONS, payload
from quest_store import SharedQuest
from quest_visuals import network_html
from quest_registration import annotation_mapping

class AdminManagementTests(unittest.TestCase):
    def test_import_reset_clears_people_activity_and_settings_not_team_access(self):
        with tempfile.TemporaryDirectory() as directory:
            q = SharedQuest(Path(directory)/'test.sqlite3')
            person = q.import_registrations('ADMIN-01', [{'name':'Test Person','email':'test@example.test','source_id':'ticket:42'}])[0]
            code = q.activation_codes()[person]
            q.demo_login(code)
            q.scan(person,payload('station','yumame'))
            q.schedule_recaps('ADMIN-01','2099-10-08T21:00:00+02:00')
            with self.assertRaises(ValueError): q.reset_imports('STAFF-01','IMPORTE LÖSCHEN')
            with self.assertRaises(ValueError): q.reset_imports('ADMIN-01','RESET')
            self.assertIn(person,q.registrations)
            q.reset_imports('ADMIN-01','IMPORTE LÖSCHEN')
            fresh=SharedQuest(q.path)
            self.assertFalse(fresh.registrations)
            self.assertFalse(fresh.active)
            self.assertFalse(fresh.visits)
            self.assertFalse(fresh.outbox)
            self.assertEqual(fresh.reset_epoch,1)
            self.assertEqual(fresh.recap_deadline,Quest().recap_deadline)
            self.assertEqual(fresh.demo_login('ADMIN-01')[0],'admin')
            self.assertEqual(fresh.demo_login('STAFF-01')[0],'staff')
            with self.assertRaises(ValueError): fresh.demo_login(code)

    def test_annotation_keeps_credentials_and_apero_counts(self):
        q=Quest()
        p=q.import_registrations('ADMIN-01',[{'name':'Test Person','email':'test@example.test','source_id':'ticket:1'}])[0]
        before=dict(q.registrations[p])
        q.set_annotation('ADMIN-01',p,'Yumame')
        self.assertEqual(q.registrations[p]['code'],before['code'])
        self.assertEqual(q.registrations[p]['id'],before['id'])
        q.demo_login('AFJD-LM-264')
        q.scan('p-8hd2v7',payload('person',p))
        self.assertIn('Future Food Apéro',q.completed('p-8hd2v7'))
        self.assertNotIn('Vernetzen',q.completed('p-8hd2v7'))
        with self.assertRaises(ValueError): q.set_annotation('ADMIN-01',p,'Coop')
        rows=q.admin_people('ADMIN-01')
        self.assertTrue(next(r for r in rows if r['Person']=='p-8hd2v7')['Pass aktiviert'])
        with self.assertRaises(ValueError): q.admin_people('STAFF-01')
        for name in ['Yumame','Catchfree','Luya']:
            self.assertEqual(ORGANISATIONS[annotation_mapping(name)['company']][2],'Future Food Apéro')
        for individual in [False,True]:
            self.assertIn('Future Food Apéro',network_html(q.public_network(),q.public_counts(),individual))

    def test_mentor_assignment_and_reset_keep_mapping(self):
        q=Quest()
        p=q.import_registrations('ADMIN-01',[{'name':'Test Mentor','email':'test@example.test','source_id':'ticket:2'}])[0]
        q.set_annotation('ADMIN-01',p,'Mentoring')
        q.reset_demo('ADMIN-01','RESET')
        q.demo_login('AFJD-LM-264')
        q.scan('p-8hd2v7',payload('person',p))
        self.assertIn('SVIAL-Mentoring',q.completed('p-8hd2v7'))
        self.assertEqual(q.public_raffle()['winner_badges'],[])
