from io import BytesIO
from email import policy
from email.parser import BytesParser
import unittest
from openpyxl import Workbook
from quest_registration import read_eventfrog
from quest_core import Quest, contact_rows, recap_draft, payload


class ImportAddressTests(unittest.TestCase):
    def rows(self):
        book = Workbook(); sheet = book.active
        sheet.append(['Ticket-ID','Vorname','Nachname','E-Mail','Institution','Annotation','Strasse / Nr.','PLZ','Ort'])
        sheet.append(['T1','Test','Person','test@example.test','Coop','Coop','Privatweg 17','0800','Privatort'])
        data = BytesIO(); book.save(data)
        return read_eventfrog(data.getvalue())

    def test_prefill_membership_and_never_share_address_with_connections(self):
        q = Quest(); rows = self.rows()
        person = q.import_registrations('ADMIN-01',rows)[0]
        q.demo_login(q.roster()[person]['code'])
        address = 'Privatweg 17\n0800 Privatort'
        self.assertEqual(q.profile(person)['address'], address)
        self.assertEqual(q.profile(person)['affiliation'], 'Coop')
        lea = q.activate('DEMO-264')
        q.set_preferences(lea,True,True); q.set_preferences(person,True,True)
        q.scan(lea,payload('person',person))
        self.assertEqual(set(contact_rows(q,lea)[0]), {'Vorname','Nachname','Institution / Zugehörigkeit','E-Mail'})
        mail = BytesParser(policy=policy.default).parsebytes(recap_draft(q,lea))
        contents = '\n'.join(part.get_content() for part in mail.walk() if part.get_content_type() in {'text/plain','text/html'})
        for private in ['Privatweg','0800','Privatort']:
            self.assertNotIn(private,contents)
            self.assertNotIn(private,str(q.public_network()))
        q.simulate_completion(person); q.assign(person,'r-7mn4b2',staff=True)
        q.submit(person,'r-7mn4b2',dict(address=address, qualification='HAFL',study_programme='Agrarwissenschaften',date_of_birth='2000-01-01'),True)
        self.assertEqual(q.applications['r-7mn4b2']['details']['address'],address)

    def test_manual_correction_survives_profile_edit_and_reimport(self):
        q = Quest(); rows = self.rows(); person = q.import_registrations('ADMIN-01',rows)[0]
        q.demo_login(q.roster()[person]['code'])
        q.update_profile(person,dict(name='Test Person',email='test@example.test',address='Neue Adresse 5'))
        q.update_profile(person,dict(name='Test Person',email='test@example.test'))
        q.import_registrations('ADMIN-01',rows)
        self.assertEqual(q.profile(person)['address'],'Neue Adresse 5')
        rows[0].pop('address')
        q.import_registrations('ADMIN-01',rows)
        self.assertEqual(q.registrations[person]['address'],'Privatweg 17\n0800 Privatort')

    def test_duplicate_ticket_does_not_inherit_buyers_address(self):
        q = Quest(); row = self.rows()[0]
        first,second = q.import_registrations('ADMIN-01',[row,dict(row,source_id='ticket:T2')])
        self.assertTrue(q.profile(first)['address'])
        self.assertEqual(q.profile(second)['address'],'')
