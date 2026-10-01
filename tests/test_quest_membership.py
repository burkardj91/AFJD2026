import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from email import policy
from email.parser import BytesParser
from quest_core import Quest,payload,ACTIVATION_CODES
from quest_store import SharedQuest
from quest_login import BrowserLogins,guarded_login
from quest_registration import reserve_rows
from quest_mail_worker import dispatch_due

class MembershipFlowTests(unittest.TestCase):
    def test_mia_membership_two_messages_exact_fields_and_no_duplicate_send(self):
        with tempfile.TemporaryDirectory() as folder:
            q=SharedQuest(Path(folder)/'db');p=q.demo_login('AFJD-MB-310')[1]
            q.simulate_completion(p);q.assign(p,'r-7mn4b2',staff=True)
            valid=dict(qualification='HAFL',study_programme='Agrarwissenschaften',address='Teststrasse 1, 8000 Zürich',date_of_birth='2000-01-01')
            for key in valid:
                bad=dict(valid);bad.pop(key)
                with self.assertRaises(ValueError):q.submit(p,'r-7mn4b2',bad,True)
            with self.assertRaises(ValueError):q.submit(p,'r-7mn4b2',dict(valid,qualification='Invalid'),True)
            q.submit(p,'r-7mn4b2',dict(valid,linkedin='do not include'),True)
            self.assertEqual(set(q.applications['r-7mn4b2']['details']),set(valid))
            office=BytesParser(policy=policy.default).parsebytes(q.outbox['claim:r-7mn4b2']['draft'].encode())
            welcome=BytesParser(policy=policy.default).parsebytes(q.outbox['confirmation:r-7mn4b2']['draft'].encode())
            self.assertEqual(office['To'],'svial@svial.ch');self.assertEqual(welcome['To'],'j.burkard@svial.ch')
            html=welcome.get_body(preferencelist=('html',)).get_content()
            self.assertIn('Hallo Mia,',html);self.assertIn('nicht automatisch',html);self.assertIn('2027',html)
            self.assertNotIn(valid['address'],html)
            with patch('quest_mail_worker.send_once',return_value='Gesendet') as send:
                dispatch_due(q,{'enabled':True});dispatch_due(q,{'enabled':True})
                self.assertEqual(send.call_count,2)

    def test_reserve_tickets_short_codes_rename_and_cookie_revocation(self):
        with tempfile.TemporaryDirectory() as folder:
            q=SharedQuest(Path(folder)/'db');people=q.import_registrations('ADMIN-01',reserve_rows())
            self.assertEqual(len(people),20);self.assertEqual(q.import_registrations('ADMIN-01',reserve_rows()),people)
            self.assertEqual(len({r['code'] for r in q.registrations.values()}),20)
            for row in q.registrations.values():
                self.assertRegex(row['code'],r'^AFJD-JD-\d{3}$');self.assertTrue(row['blank_badge'])
            p=people[0];before=q.registrations[p];logins=BrowserLogins(q);token=logins.issue(before['code'])
            q.correct_registration('ADMIN-01',p,'Lea','Meier','j.burkard@svial.ch',renew_code=True)
            after=q.registrations[p]
            self.assertRegex(after['code'],r'^AFJD-LM-\d{3}$');self.assertEqual(after['id'],before['id'])
            self.assertIsNone(logins.resolve(token))
            with self.assertRaises(ValueError):q.demo_login(before['code'])
            self.assertEqual(q.demo_login(after['code']),('participant',p))
            q.import_registrations('ADMIN-01',reserve_rows());self.assertEqual(q.registrations[p]['code'],after['code'])
            self.assertEqual(q.registrations[p]['name'],'Lea Meier')

    def test_failed_guesses_are_limited_across_sessions(self):
        with tempfile.TemporaryDirectory() as folder:
            q=SharedQuest(Path(folder)/'db')
            for _ in range(5):
                with self.assertRaises(ValueError):guarded_login(q,'AFJD-XX-999','test-address')
            with self.assertRaisesRegex(ValueError,'fünf Minuten'):guarded_login(SharedQuest(q.path),'AFJD-XX-001','test-address')
            self.assertEqual(guarded_login(q,ACTIVATION_CODES['p-2bc7r8'],'test-address')[1],'p-2bc7r8')
