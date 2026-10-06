import tempfile
import unittest
from pathlib import Path
from quest_store import SharedQuest

class ResetTests(unittest.TestCase):
    def test_activities_only_preserves_imports_codes_profiles_and_preferences(self):
        from quest_login import BrowserLogins
        with tempfile.TemporaryDirectory() as folder:
            q=SharedQuest(Path(folder)/'event.db')
            p=q.import_registrations('ADMIN-01',[dict(name='Test Person',email='test@example.test',annotation='Coop',address='Privatweg 1')])[0]
            registration=q.registrations[p]
            cookie=BrowserLogins(q).issue(registration['code'])
            q.set_preferences(p,True,True)
            q.simulate_completion(p)
            q.assign(p,'r-7mn4b2',staff=True)
            q.submit(p,'r-7mn4b2',dict(address='Privatweg 2',qualification='HAFL',study_programme='Agrarwissenschaften',date_of_birth='2000-01-01'),True)
            profile=q.profile(p); deadline=q.recap_deadline
            for staff, confirmation in [('STAFF-01','AKTIVITÄTEN LÖSCHEN'),('ADMIN-01','RESET')]:
                with self.assertRaises(ValueError): q.reset_activities(staff,confirmation)
            q.reset_activities('ADMIN-01','AKTIVITÄTEN LÖSCHEN')
            restored=SharedQuest(q.path)
            self.assertEqual(restored.registrations[p],registration)
            self.assertEqual(restored.profile(p),profile)
            self.assertEqual(restored.recap_deadline,deadline)
            self.assertIn(p,restored.sharing); self.assertIn(p,restored.recap)
            self.assertEqual(restored.affiliations[p],'in-3p9d')
            for field in ['active','visits','connections','pending','unlocked','assignments','applications','draw_log','draw_approvals','outbox','raffle','collected']:
                self.assertFalse(getattr(restored,field),field)
            self.assertIsNone(BrowserLogins(restored).resolve(cookie))
            self.assertEqual(restored.demo_login(registration['code']),('participant',p))

    def test_reset_shared_state_and_preserve_profiles(self):
        with tempfile.TemporaryDirectory() as folder:
            a=SharedQuest(Path(folder)/'event.db'); b=SharedQuest(a.path)
            p=a.activate('DEMO-264'); a.simulate_completion(p,all_six=True)
            a.update_profile(p,{'name':'Test Lea','email':'svial@svial.ch'})
            a.approve_draw(p,'STAFF-01'); card='r-7mn4b2'; a.assign(p,card,staff=True)
            a.submit(p,card,{'address':'Test address','qualification':'HAFL','study_programme':'Agrarwissenschaften','date_of_birth':'2000-01-01'},True)
            for staff,confirm in [('participant','RESET'),('ADMIN-01','')]:
                with self.assertRaises(ValueError): a.reset_demo(staff,confirm)
            self.assertTrue(b.visits)
            previous=a.revision()
            a.reset_demo('ADMIN-01','RESET')
            for field in ['active','visits','connections','pending','unlocked','assignments','applications','draw_log','draw_approvals','recap','sharing','bonuses']:
                self.assertFalse(getattr(b,field),field)
            self.assertEqual(b.profile(p)['name'],'Test Lea')
            self.assertEqual(b.reset_epoch,1)
            self.assertGreater(b.revision(),previous)
            a.reset_demo('ADMIN-01','RESET',False)
            self.assertEqual(b.profiles,{})
            self.assertEqual(b.reset_epoch,2)
