import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from io import BytesIO
from zipfile import ZipFile
from lxml import etree as E
from quest_core import Quest
from quest_store import SharedQuest
from quest_registration import plan_import
from quest_badges import badge_docx, NS
from quest_mail_worker import dispatch_due

class EventOperationsTests(unittest.TestCase):
    def test_multiple_tickets_blank_front_and_correction_survives_import(self):
        q=Quest()
        rows=[dict(name='Lea Meier',email='buyer@example.test',source_id='ticket:'+str(i)) for i in (1,2)]
        ids=q.import_registrations('ADMIN-01',rows)
        a,b=(q.registrations[p] for p in ids)
        self.assertNotEqual(a['id'],b['id']);self.assertNotEqual(a['code'],b['code'])
        self.assertFalse(a['blank_badge']);self.assertTrue(b['identity_pending'])
        self.assertEqual(b['provisional_name'],'Lea Meier 2')
        self.assertEqual(q.import_registrations('ADMIN-01',rows),ids)
        self.assertEqual(q.registrations[ids[1]]['name'],'Lea Meier 2')
        xml=E.fromstring(ZipFile(BytesIO(badge_docx(q.registrations,ids,'https://afjd2026.streamlit.app'))).read('word/document.xml'))
        cells=xml.findall('.//w:tr',NS)[0].findall('w:tc',NS)
        self.assertNotIn('Lea',''.join(cells[2].xpath('.//w:t/text()',namespaces=NS)))
        self.assertIn('Lea Meier 2',''.join(xml.xpath('.//w:t/text()',namespaces=NS)))
        old=(b['id'],b['code'])
        q.correct_registration('ADMIN-01',ids[1],'Sara','Rossi','sara@example.test','Coop')
        self.assertEqual(q.import_registrations('ADMIN-01',rows),ids)
        b=q.registrations[ids[1]]
        self.assertEqual((b['id'],b['code']),old)
        self.assertEqual(b['name'],'Sara Rossi');self.assertFalse(b['identity_pending'])
        self.assertEqual(q.profile(ids[1])['email'],'sara@example.test')
        with self.assertRaises(ValueError):q.correct_registration('STAFF-01',ids[1],'A','B','a@b.ch')
        self.assertEqual(plan_import([rows[0],rows[0]],{})[1]['action'],'Review')

    def test_schedule_consent_pending_and_once_only(self):
        with tempfile.TemporaryDirectory() as directory:
            q=SharedQuest(Path(directory)/'db')
            self.assertEqual(q.recap_deadline,'2026-10-08T21:00:00+02:00')
            person=q.demo_login('LEA-7K4M-26')[1]
            q.set_preferences(person,True,True)
            config={'enabled':True,'auto_send':True}
            with patch('quest_mail_worker.send_once',return_value='Gesendet') as send:
                dispatch_due(q,config);send.assert_not_called()
                # Past schedule seeded directly to test due dispatch deterministically.
                seed=Quest();seed.recap_deadline=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
                p=seed.demo_login('LEA-7K4M-26')[1];seed.set_preferences(p,True,True)
                unresolved=seed.import_registrations('ADMIN-01',[dict(name='Placeholder Person',email='buyer@example.test',source_id='ticket:2',blank_badge=True)])[0]
                seed.demo_login(seed.registrations[unresolved]['code']);seed.set_preferences(unresolved,True,True)
                due=SharedQuest(Path(directory)/'due',seed=seed)
                dispatch_due(due,dict(config,auto_send=False));send.assert_not_called()
                dispatch_due(due,config);dispatch_due(due,config)
                send.assert_called_once();self.assertEqual(due.outbox['recap:'+p]['status'],'Gesendet')
                self.assertNotIn('recap:'+unresolved,due.outbox)
                self.assertIsNone(due.claim_recap_delivery('recap:'+p))

    def test_failed_dispatch_and_opt_out_are_not_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            seed=Quest();seed.recap_deadline='2020-10-08T21:00:00+02:00'
            p=seed.demo_login('LEA-7K4M-26')[1];seed.set_preferences(p,True,True)
            q=SharedQuest(Path(directory)/'db',seed=seed)
            with patch('quest_mail_worker.send_once',side_effect=ValueError('SMTP fehlgeschlagen')) as send:
                dispatch_due(q,{'enabled':True});dispatch_due(q,{'enabled':True})
                send.assert_called_once()
                self.assertTrue(q.outbox['recap:'+p]['attempted'])
            other=SharedQuest(Path(directory)/'other',seed=seed)
            other.queue_due_recaps();other.set_preferences(p,True,False)
            with patch('quest_mail_worker.send_once') as send:
                dispatch_due(other,{'enabled':True});send.assert_not_called()

    def test_existing_recaps_are_not_regenerated_on_every_mutation(self):
        seed=Quest();seed.recap_deadline='2020-10-08T21:00:00+02:00'
        p=seed.demo_login('LEA-7K4M-26')[1];seed.set_preferences(p,True,True)
        seed.queue_due_recaps()
        original=seed.outbox['recap:'+p]['draft']
        with patch('quest_core.recap_draft',side_effect=AssertionError('Queued draft regenerated')):
            seed.queue_due_recaps()
        self.assertEqual(seed.outbox['recap:'+p]['draft'], original)
        # Claiming still refreshes current consent/contact details at dispatch.
        with patch('quest_core.recap_draft',return_value=b'fresh-at-dispatch') as render:
            self.assertEqual(seed.claim_recap_delivery('recap:'+p),'fresh-at-dispatch')
            render.assert_called_once()
