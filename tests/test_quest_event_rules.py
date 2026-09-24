import unittest
from quest_core import Quest, CHALLENGES, EXHIBITORS, payload, recap_draft
from quest_visuals import network_html, participant_positions

class EventRulesTests(unittest.TestCase):
    def test_six_new_quests_and_immediate_connections(self):
        q=Quest();p=q.activate('DEMO-264')
        q.scan(p,payload('station','ag-7v2x'))
        q.scan(p,payload('station','sv-5w8j'))
        self.assertFalse(q.completed(p))  # stand scans do not prove person exchanges
        q.scan(p,payload('station','fo-8b4q'))
        q.scan(p,payload('station','future-apero'))
        for other in ['p-ag-one','p-ag-two','p-rosie','p-2bc7r8','p-4jf9n3','p-9ls6d2']:
            q.scan(p,payload('person',other))
        self.assertEqual(q.completed(p),set(CHALLENGES))
        self.assertFalse(q.pending)
        self.assertIn(p,q.unlocked)
        self.assertFalse(q.sharing)
        before=len(q.connections)
        q.scan(p,payload('person','p-ag-one'))
        self.assertEqual(len(q.connections),before)

    def test_two_distinct_representatives_same_company_and_no_name_leak(self):
        q=Quest();p=q.activate('DEMO-264')
        for other in ['p-3nm9q4','p-6wx5t1']:
            q.annotate_company('STAFF-01',other,'ag-7v2x')
        q.scan(p,payload('person','p-3nm9q4'))
        q.scan(p,payload('person','p-3nm9q4'))
        self.assertNotIn('Landwirtschaft',q.completed(p))
        q.scan(p,payload('person','p-6wx5t1'))
        self.assertIn('Landwirtschaft',q.completed(p))
        self.assertEqual(len(q.public_network()['visits']),1)
        q.set_preferences(p,False,True)
        self.assertNotIn(b'Alex Keller',recap_draft(q,p))

    def test_exhibitor_ids_and_large_graph(self):
        self.assertEqual({r[0] for r in EXHIBITORS},set(range(2,27)))
        q=Quest()
        for detail in (False,True):
            html=network_html(q.public_network(),q.public_counts(),detail)
            self.assertIn('viewBox',html)
            self.assertNotIn('Lea Meier',html)
        self.assertIn('SQTS',network_html(q.public_network(),q.public_counts(),True))

    def test_hundred_people_are_separated_and_graph_has_no_height_cap(self):
        points=participant_positions(100)
        self.assertEqual(len(points),100)
        self.assertTrue(all(350 < x < 1250 and 210 < y < 680 for x,y in points))
        nearest=min(((x-a)**2+(y-b)**2)**.5 for i,(x,y) in enumerate(points) for a,b in points[i+1:])
        self.assertGreater(nearest,20)
        q=Quest();graph=q.public_network();graph['people']=100
        html=network_html(graph,q.public_counts())
        self.assertEqual(html.count('class="person"'),100)
        self.assertNotIn('max-height:360px',html)
        self.assertIn('requestFullscreen',html)
