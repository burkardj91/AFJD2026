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

    def test_private_code_alone_opens_only_its_owner(self):
        q=Quest()
        self.assertEqual(q.demo_login('LEA-7K4M-26'),('participant','p-8hd2v7'))
        for public in ['AFJD-0264','p-8hd2v7','DEMO-264','']:
            with self.assertRaises(ValueError): q.demo_login(public)
        self.assertEqual(q.active,{'p-8hd2v7'})
