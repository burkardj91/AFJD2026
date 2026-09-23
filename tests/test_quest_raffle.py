import unittest
import tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
from quest_core import Quest, ROSTER, payload
from quest_store import SharedQuest

class RaffleTests(unittest.TestCase):
    def test_deadline_eligibility_and_no_reroll(self):
        q=Quest(); p=q.activate('DEMO-264'); q.activate('DEMO-137')
        q.scan(p,payload('station','in-3p9d'))
        deadline=datetime.now(timezone.utc)+timedelta(minutes=5)
        with self.assertRaises(ValueError): q.configure_raffle('participant',deadline.isoformat())
        q.configure_raffle('STAFF-01',deadline.isoformat(),3,1)
        q.resolve_raffle(deadline-timedelta(seconds=1)); self.assertEqual(q.raffle['status'],'scheduled')
        q.resolve_raffle(deadline); self.assertEqual(q.raffle['winners'],[p])
        q.simulate_completion('p-3nm9q4'); q.resolve_raffle(deadline+timedelta(seconds=1))
        self.assertEqual(q.raffle['winners'],[p])
        self.assertNotIn('Lea',str(q.public_raffle()))
        with self.assertRaises(ValueError): q.configure_raffle('STAFF-01',(deadline+timedelta(hours=1)).isoformat())

    def test_concurrent_screens_and_late_scan(self):
        q=Quest()
        for row in ROSTER.values():
            p=q.activate(row['code']); q.scan(p,payload('station','ag-7v2x'))
        q.raffle={'status':'scheduled','deadline':(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(),'count':3,'minimum':1}
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'test.db'; SharedQuest(db,seed=q)
            with ThreadPoolExecutor(2) as pool:
                list(pool.map(lambda _:SharedQuest(db).resolve_raffle(),range(2)))
            state=SharedQuest(db); result=state.public_raffle()
            self.assertEqual(len(set(result['winner_badges'])),3)
            state.resolve_raffle(); self.assertEqual(state.public_raffle(),result)
            state.reset_demo('STAFF-01','RESET'); self.assertFalse(state.raffle)
        q=Quest(); p=q.activate('DEMO-264');q.raffle={'status':'scheduled','deadline':(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(),'count':5,'minimum':1}
        with tempfile.TemporaryDirectory() as folder:
            state=SharedQuest(Path(folder)/'late.db',seed=q)
            state.scan(p,payload('station','ag-7v2x'))
            self.assertEqual(state.raffle['winners'],[])
