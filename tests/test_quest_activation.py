import unittest
from quest_core import Quest, ACTIVATION_CODES

class ActivationTests(unittest.TestCase):
    def test_wrong_or_missing_code_cannot_claim_badge(self):
        q=Quest()
        for code in ['', 'DEMO-264', ACTIVATION_CODES['p-3nm9q4']]:
            with self.assertRaises(ValueError):
                q.demo_login('AFJD-0264',code)
        self.assertFalse(q.active)
        self.assertEqual(q.demo_login('AFJD-0264',ACTIVATION_CODES['p-8hd2v7']),('participant','p-8hd2v7'))
        self.assertEqual(q.active,{'p-8hd2v7'})
