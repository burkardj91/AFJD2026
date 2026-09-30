import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from openpyxl import Workbook
from quest_registration import read_eventfrog, plan_import, print_documents
from quest_store import SharedQuest
from quest_core import payload

class RegistrationTests(unittest.TestCase):
    def test_eventfrog_header_and_allowlist(self):
        book=Workbook(); sheet=book.active
        sheet.append(['Event title']); sheet.append([]); sheet.append(['Notice'])
        sheet.append(['ID','Ticket-ID','Vorname','Nachname','E-Mail','Annotation','Preis','Strasse / Nr.'])
        sheet.append([1,'T42','Test','Person','person@example.test','Coop',99,'Do not import'])
        content=BytesIO(); book.save(content)
        rows=read_eventfrog(content.getvalue())
        self.assertEqual(rows[0]['name'],'Test Person')
        self.assertEqual(rows[0]['source_id'],'ticket:T42')
        self.assertEqual(rows[0]['annotation'],'Coop')
        self.assertNotIn('Preis',rows[0])
        self.assertNotIn('Do not import',str(rows))

    def test_import_reload_login_scan_update_and_reset(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'event.sqlite3'; q=SharedQuest(path)
            row={'name':'New Person','email':'new@example.test','source_id':'ticket:42'}
            person=q.import_registrations('ADMIN-01',[row])[0]
            r=q.roster()[person]
            q=SharedQuest(path)
            self.assertEqual(q.demo_login(r['code']),('participant',person))
            q.demo_login('LEA-7K4M-26')
            q.scan('p-8hd2v7','https://afjd2026.streamlit.app/?badge='+person)
            self.assertIn(person,q.people('p-8hd2v7'))
            q.update_profile(person,{'name':'Edited Person','email':'edit@example.test'})
            self.assertEqual(q.import_registrations('ADMIN-01',[dict(row,name='Updated Person')]),[person])
            self.assertEqual(q.roster()[person]['code'],r['code'])
            self.assertEqual(q.profile(person)['name'],'Edited Person')
            self.assertEqual(q.roster()[person]['id'],r['id'])
            front,slip=print_documents(q.registrations,[person],'https://afjd2026.streamlit.app')
            self.assertNotIn(r['code'],front); self.assertIn(r['code'],slip)
            q.reset_demo('ADMIN-01','RESET')
            self.assertIn(person,q.roster())
            self.assertFalse(q.connections)

    def test_atomic_review_and_distinct_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            q=SharedQuest(Path(folder)/'db')
            good={'name':'One Person','email':'one@example.test'}
            with self.assertRaises(ValueError):
                q.import_registrations('ADMIN-01',[good,dict(good,email='bad')])
            self.assertFalse(q.registrations)
            ids=q.import_registrations('ADMIN-01',[good,{'name':'Two Person','email':'two@example.test'}])
            self.assertEqual(len({q.roster()[p]['id'] for p in ids}),2)
            self.assertEqual(plan_import([good,good],{})[1]['action'],'Review')
            self.assertEqual(plan_import([dict(good,name='Different Person')],q.registrations)[0]['action'],'Review')
            with self.assertRaises(ValueError): q.import_registrations('SCREEN-01',[good])


    def test_annotations_batch_and_admin_permissions(self):
        from quest_registration import annotation_mapping, batch_archive
        from quest_core import Quest
        from zipfile import ZipFile
        q=Quest()
        rows=[{'name':'Company Person','email':'company@example.test','annotation':'Coop','affiliation':'Coop'},
              {'name':'Mentor Person','email':'mentor@example.test','annotation':'Mentor'},
              {'name':'Rosie Test','email':'rosie@example.test','annotation':'SVIAL-Mentoring'}]
        for staff in ['STAFF-01','STAFF-02','SCREEN-01']:
            with self.assertRaises(ValueError):q.import_registrations(staff,rows)
            with self.assertRaises(ValueError):q.reset_demo(staff,'RESET')
            with self.assertRaises(ValueError):q.configure_raffle(staff,'2099-10-08T19:30:00+02:00')
        ids=q.import_registrations('ADMIN-01',rows)
        self.assertEqual(q.affiliations[ids[0]],'in-3p9d')
        self.assertNotIn(ids[1],q.affiliations)
        self.assertEqual(annotation_mapping('Unknown sponsor')['company'],None)
        q.demo_login('LEA-7K4M-26');q.scan('p-8hd2v7',payload('person',ids[2]))
        self.assertIn('SVIAL-Mentoring',q.completed('p-8hd2v7'))
        with self.assertRaises(ValueError):
            q.import_registrations('ADMIN-01',[dict(rows[2],annotation='Coop')])
        archive=ZipFile(BytesIO(batch_archive(q.registrations,ids,'https://afjd2026.streamlit.app')))
        front=archive.read('01-public-badges.html').decode()
        slips=archive.read('02-PRIVATE-login-slips.html').decode()
        self.assertEqual(front.count('<section class="badge">'),3)
        self.assertNotIn('class="logo"',front)
        self.assertIn('Coop',front)
        for p in ids:
            self.assertIn(q.roster()[p]['name'],front)
            self.assertNotIn(q.roster()[p]['code'],front)
            self.assertIn(q.roster()[p]['code'],slips)

if __name__=='__main__': unittest.main()
