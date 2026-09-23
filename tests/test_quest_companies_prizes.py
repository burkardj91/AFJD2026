import unittest
from datetime import datetime,timezone,timedelta
from collections import Counter
from quest_core import Quest, CARDS, payload

class CompanyPrizeTests(unittest.TestCase):
    def test_company_contacts_aggregate_but_retain_people(self):
        q=Quest(); p=q.activate('DEMO-264'); a=q.activate('DEMO-137'); b=q.activate('DEMO-189')
        for contact in [a,b,a]:
            q.scan(p,payload('person',contact))
        self.assertEqual(q.completed(p),{'Retail'})
        self.assertEqual(q.company_contacts[p],{a,b})
        self.assertEqual(q.visits[p],{'re-lidl'})
        graph=q.public_network()
        self.assertEqual(graph['people'],1)
        self.assertEqual(len(graph['visits']),1)
        q.confirm(a,p);q.confirm(b,p)
        self.assertEqual(len(q.people(p)),2)
        self.assertNotIn('Connect',q.completed(p))
        self.assertEqual(q.public_network()['connections'],[])

    def test_inventory_and_membership_validation(self):
        self.assertEqual(Counter(c[2] for c in CARDS.values()),{'membership':50,'event':20,'gift':60,'sfr':5})
        valid={'address':'Demo street','organisation':'Demo School','study_programme':'Food','date_of_birth':'2000-01-01'}
        for missing in valid:
            q=Quest();p=q.activate('DEMO-264');q.simulate_completion(p);q.assign(p,'r-7mn4b2',staff=True)
            details=dict(valid);details.pop(missing)
            with self.assertRaises(ValueError):q.submit(p,'r-7mn4b2',details,True)
            self.assertFalse(q.outbox)
        q.submit(p,'r-7mn4b2',valid,True)
        mail=q.outbox['claim:r-7mn4b2']['draft']
        self.assertIn('31.12.2027',mail)
        self.assertIn('Gratismitgliedschaft AFJD Lea Meier',mail)
        q=Quest();p=q.activate('DEMO-264');q.simulate_completion(p);q.assign(p,'r-2kh8w5',staff=True)
        q.submit(p,'r-2kh8w5',{},True)
        self.assertEqual(len(q.applications),1)

    def test_recap_queue_once_and_opt_in(self):
        q=Quest();p=q.activate('DEMO-264');q.activate('DEMO-137')
        q.scan(p,payload('person','p-3nm9q4'));q.set_preferences(p,False,True)
        deadline=datetime.now(timezone.utc)+timedelta(minutes=1)
        q.schedule_recaps('STAFF-01',deadline.isoformat())
        q.queue_due_recaps(deadline-timedelta(seconds=1));self.assertFalse(q.outbox)
        q.queue_due_recaps(deadline);q.queue_due_recaps(deadline)
        self.assertEqual(list(q.outbox),['recap:'+p])
        self.assertIn('Lidl',q.outbox['recap:'+p]['draft'])
        self.assertIn('Alex Keller',q.outbox['recap:'+p]['draft'])
