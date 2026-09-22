import unittest
from quest_core import Quest, ORGANISATIONS, CLUSTERS, payload
from quest_visuals import network_html

class ClusterTests(unittest.TestCase):
    def test_catalogue_and_retail_deduplication(self):
        self.assertEqual(len({o[0] for o in ORGANISATIONS.values()}),len(ORGANISATIONS))
        self.assertTrue(all(o[2] in CLUSTERS for o in ORGANISATIONS.values()))
        q=Quest(); p=q.activate('DEMO-264')
        q.scan(p,payload('station','in-3p9d'))
        q.scan(p,payload('station','re-lidl'))
        self.assertEqual(q.completed(p),{'Retail'})
        graph=q.public_network()
        self.assertEqual(len(graph['visits']),2)
        self.assertEqual({graph['organisations'][i]['name'] for _,i in graph['visits']},{'Coop','Lidl'})
        svial=next(o for o in graph['organisations'] if o['name']=='SVIAL')
        self.assertEqual(svial['cluster'],'Services & Ecosystem')
        self.assertTrue(svial['connector'])
        html=network_html(graph,q.public_counts(),show_companies=True)
        self.assertIn('ORG-010',html)
        self.assertNotIn('Lea Meier',html)
        self.assertNotIn('AFJD-0264',html)
