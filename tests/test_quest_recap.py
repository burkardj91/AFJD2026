import unittest
from quest_core import Quest, payload, recap_draft, parse_payload, contact_rows
from quest_visuals import network_html

class RecapTests(unittest.TestCase):
    def test_shared_contact_table_has_no_duplicate_company_or_private_claim_fields(self):
        from email import policy
        from email.parser import BytesParser
        q = Quest()
        p = q.activate('DEMO-264')
        other = q.import_registrations('ADMIN-01', [{
            'name':'Test <Person>', 'first_name':'Test', 'last_name':'<Person>',
            'email':'test@example.test', 'annotation':'Coop', 'affiliation':'Coop'}])[0]
        q.demo_login(q.roster()[other]['code'])
        q.update_profile(other, {'name':'Test <Person>', 'email':'test@example.test',
                                'address':'PRIVATE ADDRESS', 'date_of_birth':'2000-01-01'})
        q.set_preferences(other, True, False)
        q.set_preferences(p, True, True)
        q.scan(p, payload('station','in-3p9d'))
        q.scan(p, payload('person',other))
        rows = contact_rows(q,p)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['Nachname'],'<Person>')
        self.assertEqual(rows[0]['E-Mail'],'test@example.test')
        msg=BytesParser(policy=policy.default).parsebytes(recap_draft(q,p))
        plain=msg.get_body(preferencelist=('plain',)).get_content()
        html=msg.get_body(preferencelist=('html',)).get_content()
        self.assertIn('Liebe Lea,',plain)
        self.assertIn('https://docs.google.com/forms/',html)
        self.assertIn('&lt;Person&gt;',html)
        self.assertNotIn('PRIVATE ADDRESS',plain+html)
        self.assertNotIn('2000-01-01',plain+html)
        self.assertNotIn('Erfüllte Quests',plain)
        q.set_preferences(other,False,False)
        self.assertNotIn('test@example.test',str(contact_rows(q,p)))

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
        body=mail.get_body(preferencelist=("plain",)).get_content()
        self.assertIn('Coop',body)
        self.assertIn('Institution / Zugehörigkeit',body)
        self.assertNotIn('alex@example.test',body)
        graph=q.public_network()
        self.assertNotIn('Coop',network_html(graph,q.public_counts()))
        self.assertIn('Coop',network_html(graph,q.public_counts(),True))
        self.assertEqual(q.completed(p),{"Detailhandel"})
