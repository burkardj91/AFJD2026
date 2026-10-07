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

    def test_avatar_actions_follow_reward_state(self):
        from quest_reward_status import reward_avatar_html
        self.assertIn('?claim=r-membership-001',reward_avatar_html('reserved','r-membership-001','animal.png','Goat'))
        self.assertIn('?invitation=1',reward_avatar_html('unlocked',None,'animal.png','Goat'))
        for state in ('redeemed','exploring'):
            self.assertNotIn('<a ',reward_avatar_html(state,None,'animal.png','Goat'))
