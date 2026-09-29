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
        sheet.append(['ID','Ticket-ID','Vorname','Nachname','E-Mail','Preis','Strasse / Nr.'])
        sheet.append([1,'T42','Test','Person','person@example.test',99,'Do not import'])
        content=BytesIO(); book.save(content)
        rows=read_eventfrog(content.getvalue())
        self.assertEqual(rows[0]['name'],'Test Person')
        self.assertEqual(rows[0]['source_id'],'ticket:T42')
        self.assertNotIn('Preis',rows[0])
        self.assertNotIn('Do not import',str(rows))

    def test_import_reload_login_scan_update_and_reset(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'event.sqlite3'; q=SharedQuest(path)
            row={'name':'New Person','email':'new@example.test','source_id':'ticket:42'}
            person=q.import_registrations('STAFF-01',[row])[0]
            r=q.roster()[person]
            q=SharedQuest(path)
            self.assertEqual(q.demo_login(r['code']),('participant',person))
            q.demo_login('LEA-7K4M-26')
            q.scan('p-8hd2v7','https://afjd2026.streamlit.app/?badge='+person)
            self.assertIn(person,q.people('p-8hd2v7'))
            q.update_profile(person,{'name':'Edited Person','email':'edit@example.test'})
            self.assertEqual(q.import_registrations('STAFF-02',[dict(row,name='Updated Person')]),[person])
            self.assertEqual(q.roster()[person]['code'],r['code'])
            self.assertEqual(q.profile(person)['name'],'Edited Person')
            self.assertEqual(q.roster()[person]['id'],r['id'])
            front,slip=print_documents(q.registrations,[person],'https://afjd2026.streamlit.app')
            self.assertNotIn(r['code'],front); self.assertIn(r['code'],slip)
            q.reset_demo('STAFF-01','RESET')
            self.assertIn(person,q.roster())
            self.assertFalse(q.connections)

    def test_atomic_review_and_distinct_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            q=SharedQuest(Path(folder)/'db')
            good={'name':'One Person','email':'one@example.test'}
            with self.assertRaises(ValueError):
                q.import_registrations('STAFF-01',[good,dict(good,email='bad')])
            self.assertFalse(q.registrations)
            ids=q.import_registrations('STAFF-01',[good,{'name':'Two Person','email':'two@example.test'}])
            self.assertEqual(len({q.roster()[p]['id'] for p in ids}),2)
            self.assertEqual(plan_import([good,good],{})[1]['action'],'Review')
            self.assertEqual(plan_import([dict(good,name='Different Person')],q.registrations)[0]['action'],'Review')
            with self.assertRaises(ValueError): q.import_registrations('SCREEN-01',[good])

if __name__=='__main__': unittest.main()
