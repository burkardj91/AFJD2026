import unittest
from io import BytesIO
from openpyxl import Workbook
from quest_core import Quest, contact_rows, payload
from quest_registration import read_eventfrog
from quest_appointments import appointments_html


class AppointmentTests(unittest.TestCase):
    def test_both_slots_import_update_and_stay_private(self):
        book=Workbook(); sheet=book.active
        sheet.append(['Ticket-ID','Vorname','Nachname','E-Mail','CV-Check','CV-Foto'])
        sheet.append(['T1','Test','Person','test@example.test','18:00 - 18:15','19:20 - 19:30'])
        stream=BytesIO(); book.save(stream)
        rows=read_eventfrog(stream.getvalue()); q=Quest()
        p=q.import_registrations('ADMIN-01',rows)[0]
        markup=appointments_html(q.profile(p))
        self.assertIn('CV-Check',markup); self.assertIn('CV-Foto',markup)
        self.assertIn('18:00 - 18:15',markup); self.assertIn('19:20 - 19:30',markup)
        lea=q.activate('DEMO-264');q.scan(lea,payload('person',p))
        self.assertNotIn('18:00',str(contact_rows(q,lea)))
        q.import_registrations('ADMIN-01',[{k:v for k,v in rows[0].items() if k not in {'cv_check','cv_photo'}}])
        self.assertEqual(q.profile(p)['cv_photo'],'19:20 - 19:30')
        q.import_registrations('ADMIN-01',[dict(rows[0],cv_photo='')])
        self.assertNotIn('CV-Foto',appointments_html(q.profile(p)))

    def test_empty_hidden_and_text_escaped(self):
        self.assertEqual(appointments_html({}),'')
        self.assertNotIn('<script>',appointments_html({'cv_photo':'<script>alert(1)</script>'}))
        self.assertIn('18:00',appointments_html({'cv_check':'18:00:00'}))

    def test_excel_header_variants_and_preview(self):
        from quest_registration import plan_import, import_preview
        for check, photo in [('CV Check', 'CV Foto'), ('CV‑Check', 'CV–Foto'), (' CV - Check ', 'CV-\nFoto')]:
            book=Workbook(); sheet=book.active
            sheet.append(['Ticket-ID','Vorname','Nachname','E-Mail',check,photo])
            sheet.append(['T2','Test','Person','test@example.test','18:00 - 18:15','19:20 - 19:30'])
            stream=BytesIO();book.save(stream)
            rows=read_eventfrog(stream.getvalue())
            preview=import_preview(plan_import(rows,{}))[0]
            self.assertEqual(preview['CV-Check'],'18:00 - 18:15')
            self.assertEqual(preview['CV-Foto'],'19:20 - 19:30')
            q=Quest();person=q.import_registrations('ADMIN-01',rows)[0]
            admin=next(r for r in q.admin_people('ADMIN-01') if r['Person']==person)
            self.assertEqual(admin['CV-Foto'],preview['CV-Foto'])

    def test_old_profile_does_not_hide_registration_slots(self):
        q=Quest()
        person=q.import_registrations('ADMIN-01',[{'name':'Test Termine','email':'test@example.test','source_id':'CV-1','cv_check':'18:00 - 18:15','cv_photo':'19:00 - 19:15'}])[0]
        q.profiles[person]={'cv_check':'','cv_photo':'old value'}
        self.assertEqual(q.profile(person)['cv_check'],'18:00 - 18:15')
        self.assertEqual(q.profile(person)['cv_photo'],'19:00 - 19:15')

    def test_missing_slots_hidden_and_acknowledgement_persisted(self):
        from quest_appointments import appointment_slots
        from quest_store import SharedQuest
        import tempfile
        from pathlib import Path
        for value in ('', ' ', None, float('nan'), 'NaN', 'nan', 'NaT', '<NA>', 'null'):
            self.assertEqual(appointment_slots({'cv_check':value,'cv_photo':value}),[])
        self.assertEqual(appointment_slots({'cv_check':'NaN','cv_photo':'18:00 - 18:15'}), [('CV-Foto','18:00 - 18:15')])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'quest.sqlite3'
            q=SharedQuest(path)
            person=q.activate('DEMO-264')
            q.acknowledge_appointments(person)
            self.assertIn(person,SharedQuest(path).appointments_reviewed)
            q.reset_activities('ADMIN-01','AKTIVITÄTEN LÖSCHEN')
            self.assertIn(person,q.appointments_reviewed)
