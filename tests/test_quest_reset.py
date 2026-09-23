import tempfile
import unittest
from pathlib import Path
from quest_store import SharedQuest

class ResetTests(unittest.TestCase):
    def test_reset_shared_state_and_preserve_profiles(self):
        with tempfile.TemporaryDirectory() as folder:
            a=SharedQuest(Path(folder)/'event.db'); b=SharedQuest(a.path)
            p=a.activate('DEMO-264'); a.simulate_completion(p,all_six=True)
            a.update_profile(p,{'name':'Test Lea','email':'svial@svial.ch'})
            a.approve_draw(p,'STAFF-01'); card=a.draw(p,'STAFF-01')
            a.submit(p,card,{'address':'Test address'},True)
            for staff,confirm in [('participant','RESET'),('STAFF-01','')]:
                with self.assertRaises(ValueError): a.reset_demo(staff,confirm)
            self.assertTrue(b.visits)
            previous=a.revision()
            a.reset_demo('STAFF-01','RESET')
            for field in ['active','visits','connections','pending','unlocked','assignments','applications','draw_log','draw_approvals','recap','sharing','bonuses']:
                self.assertFalse(getattr(b,field),field)
            self.assertEqual(b.profile(p)['name'],'Test Lea')
            self.assertEqual(b.reset_epoch,1)
            self.assertGreater(b.revision(),previous)
            a.reset_demo('STAFF-02','RESET',False)
            self.assertEqual(b.profiles,{})
            self.assertEqual(b.reset_epoch,2)
