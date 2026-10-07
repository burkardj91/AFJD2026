import unittest
from quest_core import Quest, CARDS
from quest_reward_status import reward_status

class RewardStatusTests(unittest.TestCase):
    def test_status_tracks_existing_facts_without_mutating_them(self):
        from copy import deepcopy
        q=Quest();p=q.activate('DEMO-264')
        self.assertEqual(reward_status(q,p)[:2],('exploring','Entdecke die Veranstaltung'))
        q.simulate_completion(p)
        self.assertEqual(reward_status(q,p)[0],'unlocked')
        card=next(c for c,r in CARDS.items() if r[2]=='gift')
        q.assign(p,card,staff=True)
        self.assertEqual(reward_status(q,p)[0],'reserved')
        before=deepcopy(q.__dict__);reward_status(q,p)
        self.assertEqual(q.__dict__,before)
        q.collect_gift('STAFF-01',card)
        self.assertEqual(reward_status(q,p)[0],'redeemed')
