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
