import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from quest_store import SharedQuest
from quest_login import BrowserLogins, LOGIN_SECONDS


class BrowserLoginTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.q = SharedQuest(Path(self.folder.name) / 'event.db')
        self.logins = BrowserLogins(self.q)

    def test_restores_identity_in_new_session_without_storing_code(self):
        token = self.logins.issue('LEA-7K4M-26')
        other = BrowserLogins(SharedQuest(self.q.path))
        self.assertEqual(other.resolve(token), 'p-8hd2v7')
        with self.q.connect() as db:
            record = str(db.execute('SELECT * FROM browser_logins_4h').fetchall())
        self.assertNotIn(token, record)
        self.assertNotIn('LEA-7K4M-26', record)
        for invalid in [None, 'p-8hd2v7', 'LEA-7K4M-26', 'x'*43]:
            self.assertIsNone(other.resolve(invalid))

    def test_expiry_revocation_and_reset(self):
        self.assertEqual(LOGIN_SECONDS, 4 * 60 * 60)
        with patch('quest_login.time.time', return_value=1000):
            token = self.logins.issue('LEA-7K4M-26')
            self.assertEqual(self.logins.resolve(token), 'p-8hd2v7')
        with patch('quest_login.time.time', return_value=1000 + LOGIN_SECONDS):
            self.assertIsNone(self.logins.resolve(token))
        token = self.logins.issue('LEA-7K4M-26')
        self.logins.revoke(token)
        self.assertIsNone(self.logins.resolve(token))
        token = self.logins.issue('LEA-7K4M-26')
        self.q.reset_demo('ADMIN-01', 'RESET')
        self.q.demo_login('LEA-7K4M-26')
        self.assertIsNone(self.logins.resolve(token))

    def test_staff_and_invalid_credentials_cannot_get_browser_token(self):
        for code in ['STAFF-01', 'SCREEN-01', 'incorrect']:
            with self.assertRaises(ValueError):
                self.logins.issue(code)

    def test_live_login_rejects_demo_and_old_demo_cookie(self):
        from quest_login import guarded_login
        token=self.logins.issue('AFJD-LM-264')
        live=BrowserLogins(self.q,allow_demo=False)
        self.assertIsNone(live.resolve(token))
        with self.assertRaises(ValueError):live.issue('AFJD-LM-264')
        with self.assertRaises(ValueError):guarded_login(self.q,'AFJD-LM-264','live-test',allow_demo=False)
        for code,role in [('ADMIN-01','admin'),('STAFF-01','staff'),('STAFF-02','staff'),('SCREEN-01','screen')]:
            self.assertEqual(guarded_login(self.q,code,'live-team',allow_demo=False)[0],role)
        person=self.q.import_registrations('ADMIN-01',[{'name':'Real Test','email':'test@example.test'}])[0]
        code=self.q.registrations[person]['code']
        self.assertEqual(guarded_login(self.q,code,'live-person',allow_demo=False)[1],person)
        self.assertEqual(live.resolve(live.issue(code)),person)

    def test_parallel_invalid_logins_enforce_shared_five_attempt_limit(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from quest_login import guarded_login
        barrier = Barrier(20)
        def attempt(_):
            barrier.wait()
            try:
                guarded_login(SharedQuest(self.q.path), "INVALID", "same-event-wifi", allow_demo=False)
            except ValueError as error:
                return str(error)
            self.fail("Invalid credential accepted")
        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(attempt, range(20)))
        self.assertEqual(sum("Zu viele" in result for result in results), 15)
        with self.q.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM login_attempts").fetchone()[0], 5)
