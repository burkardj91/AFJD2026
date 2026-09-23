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
            record = str(db.execute('SELECT * FROM browser_logins').fetchall())
        self.assertNotIn(token, record)
        self.assertNotIn('LEA-7K4M-26', record)
        for invalid in [None, 'p-8hd2v7', 'LEA-7K4M-26', 'x'*43]:
            self.assertIsNone(other.resolve(invalid))

    def test_expiry_revocation_and_reset(self):
        with patch('quest_login.time.time', return_value=1000):
            token = self.logins.issue('LEA-7K4M-26')
            self.assertEqual(self.logins.resolve(token), 'p-8hd2v7')
        with patch('quest_login.time.time', return_value=1000 + LOGIN_SECONDS):
            self.assertIsNone(self.logins.resolve(token))
        token = self.logins.issue('LEA-7K4M-26')
        self.logins.revoke(token)
        self.assertIsNone(self.logins.resolve(token))
        token = self.logins.issue('LEA-7K4M-26')
        self.q.reset_demo('STAFF-01', 'RESET')
        self.q.demo_login('LEA-7K4M-26')
        self.assertIsNone(self.logins.resolve(token))

    def test_staff_and_invalid_credentials_cannot_get_browser_token(self):
        for code in ['STAFF-01', 'SCREEN-01', 'incorrect']:
            with self.assertRaises(ValueError):
                self.logins.issue(code)
