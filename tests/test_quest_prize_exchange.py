import unittest
from email import policy
from email.parser import BytesParser
from quest_core import Quest, CARDS
from unittest.mock import patch

class PrizeExchangeTests(unittest.TestCase):
    def prepared(self):
        q=Quest();p='p-8hd2v7';q.demo_login('AFJD-LM-264');q.simulate_completion(p)
        q.approve_draw(p,'STAFF-01')
        return q,p

    def test_event_confirmation_and_admin_prize(self):
        q,p=self.prepared();card=next(c for c,r in CARDS.items() if r[2]=='event')
        q.assign(p,card,staff=True)
        q.scan(p,'afjd:2026:reward:'+card)
        self.assertFalse(q.outbox, 'Scanning alone does not submit a claim')
        q.submit(p,card,{},True)
        self.assertEqual(len(q.outbox),1)
        msg=BytesParser(policy=policy.default).parsebytes(q.outbox['claim:'+card]['draft'].encode())
        self.assertEqual(msg['To'],'svial@svial.ch')
        self.assertEqual(msg['Cc'],'j.burkard@svial.ch')
        self.assertIn('keine Buchung',msg.get_body(preferencelist=('plain',)).get_content())
        self.assertIn('svial.ch/events',msg.get_body(preferencelist=('plain',)).get_content())
        self.assertTrue(q.claim_application_delivery('claim:'+card))
        self.assertIsNone(q.claim_application_delivery('claim:'+card))
        row=next(r for r in q.admin_people('ADMIN-01') if r['Person']==p)
        self.assertEqual(row['Gewinnreferenz'],CARDS[card][0]);self.assertEqual(row['Gewinnstatus'],'Bestätigt')
        with self.assertRaises(ValueError): q.return_prize(p,card,'STAFF-01','Anderer Gewinn gewünscht')

    def test_return_restores_inventory_and_excludes_membership(self):
        q,p=self.prepared();card=next(c for c,r in CARDS.items() if r[2]=='membership')
        q.assign(p,card,staff=True)
        with self.assertRaises(ValueError): q.return_prize(p,card,'ADMIN-01','Bereits SVIAL-Mitglied')
        q.return_prize(p,card,'STAFF-01','Bereits SVIAL-Mitglied')
        self.assertNotIn(card,q.assignments)
        with self.assertRaises(ValueError): q.return_prize(p,card,'STAFF-02','Bereits SVIAL-Mitglied')
        self.assertEqual(len(q.return_log),1)
        self.assertFalse(q.outbox)
        new=q.draw(p,'STAFF-02')
        self.assertNotEqual(CARDS[new][2],'membership')
        self.assertEqual(q.draw(p,'STAFF-01'),new)
        q.active.add('p-2bc7r8');q.unlocked.add('p-2bc7r8')
        q.assign('p-2bc7r8',card,staff=True)
        with self.assertRaises(ValueError): q.scan(p,'afjd:2026:reward:'+card)

    def test_no_alternative_preserves_card_and_collected_cannot_return(self):
        q,p=self.prepared();card=next(c for c,r in CARDS.items() if r[2]=='gift');q.assign(p,card,staff=True)
        q.assignments.update({c:'someone' for c in CARDS if c!=card})
        with self.assertRaises(ValueError): q.return_prize(p,card,'STAFF-01','Anderer Gewinn gewünscht')
        self.assertEqual(q.assignments[card],p)
        q.assignments={card:p};q.collect_gift('STAFF-01',card)
        with self.assertRaises(ValueError): q.return_prize(p,card,'STAFF-02','Anderer Gewinn gewünscht')
