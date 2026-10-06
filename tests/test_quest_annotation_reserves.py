from io import BytesIO
import unittest
from datetime import datetime, timezone, timedelta
from openpyxl import Workbook
from quest_registration import read_eventfrog, print_documents
from quest_core import Quest


class AnnotationReserveTests(unittest.TestCase):
    def rows(self):
        book=Workbook(); sheet=book.active
        sheet.append(['Annotation'])
        sheet.append(['SVIAL']); sheet.append(['SVIAL']); sheet.append(['Coop'])
        data=BytesIO(); book.save(data)
        return read_eventfrog(data.getvalue())

    def test_blank_badges_unique_and_idempotent_after_assignment(self):
        q=Quest(); rows=self.rows()
        people=q.import_registrations('ADMIN-01',rows)
        self.assertEqual(len(set(people)),3)
        self.assertEqual(len({q.roster()[p]['id'] for p in people}),3)
        self.assertEqual(len({q.roster()[p]['code'] for p in people}),3)
        for p in people:
            row=q.registrations[p]
            self.assertTrue(row['identity_pending']); self.assertTrue(row['blank_badge'])
            self.assertEqual(row['email'],'')
        self.assertEqual(q.affiliations[people[2]],'in-3p9d')
        front,back=print_documents(q.roster(),people,'https://afjd2026.streamlit.app')
        self.assertNotIn('Offen',front); self.assertIn('SVIAL',front); self.assertIn('Offen',back)
        p=people[0]; before=dict(q.registrations[p])
        q.correct_registration('ADMIN-01',p,'New','Person','new@example.test','SVIAL',annotation='SVIAL')
        self.assertEqual(q.import_registrations('ADMIN-01',rows),people)
        self.assertEqual(q.profile(p)['name'],'New Person')
        self.assertEqual(q.profile(p)['email'],'new@example.test')
        self.assertFalse(q.registrations[p]['identity_pending'])
        self.assertEqual(q.registrations[p]['code'],before['code'])
        self.assertEqual(q.registrations[p]['id'],before['id'])

    def test_unassigned_reserve_excluded_from_mail_and_prizes(self):
        q=Quest(); p=q.import_registrations('ADMIN-01',self.rows())[0]
        q.demo_login(q.roster()[p]['code']); q.set_preferences(p,True,True)
        q.simulate_completion(p,all_six=True)
        with self.assertRaises(ValueError): q.approve_draw(p,'STAFF-01')
        with self.assertRaises(ValueError): q.assign(p,'r-7mn4b2',staff=True)
        q.recap_deadline='2000-01-01T00:00:00+00:00'; q.queue_due_recaps()
        self.assertNotIn('recap:'+p,q.outbox)
        future=datetime.now(timezone.utc)+timedelta(hours=1)
        q.configure_raffle('ADMIN-01',future.isoformat(),3,1)
        q.resolve_raffle(future+timedelta(seconds=1))
        self.assertNotIn(p,q.raffle['eligible'])

    def test_incomplete_named_person_still_requires_review(self):
        q=Quest()
        with self.assertRaises(ValueError):
            q.import_registrations('ADMIN-01',[dict(name='Some Person',email='',annotation='SVIAL')])
