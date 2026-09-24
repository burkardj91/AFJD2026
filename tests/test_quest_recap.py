import unittest
from quest_core import Quest, payload, recap_draft, parse_payload
from quest_visuals import network_html

class RecapTests(unittest.TestCase):
    def test_badge_does_not_activate_and_recap_preserves_company(self):
        q=Quest()
        self.assertEqual(parse_payload('http://localhost:8503/?badge=p-8hd2v7'),('person','p-8hd2v7'))
        self.assertFalse(q.active)
        p=q.activate('DEMO-264'); other=q.activate('DEMO-137')
        q.scan(p,payload('station','in-3p9d'))
        q.scan(p,payload('person',other)); q.confirm(other,p)
        with self.assertRaises(ValueError): recap_draft(q,p)
        q.set_preferences(p,False,True)
        draft=recap_draft(q,p)
        from email import policy
        from email.parser import BytesParser
        mail=BytesParser(policy=policy.default).parsebytes(draft)
        self.assertEqual(mail['To'],'svial@svial.ch')
        body=mail.get_content()
        self.assertIn('Coop (4)',body)
        self.assertIn('Retail',body)
        self.assertNotIn('alex@example.test',body)
        graph=q.public_network()
        self.assertNotIn('Coop',network_html(graph,q.public_counts()))
        self.assertIn('Coop',network_html(graph,q.public_counts(),True))
        self.assertEqual(q.completed(p),set())
