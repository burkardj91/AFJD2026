"""Read-path benchmark in a temporary database; no SMTP or live data."""
import sys,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from time import perf_counter
from quest_core import Quest
from quest_store import SharedQuest
state=Quest()
ids=state.import_registrations('ADMIN-01',[{'name':f'Benchmark User {i}','email':f'bench{i}@example.test','source_id':f'bench:{i}'} for i in range(100)])
for p in ids:
    state.demo_login(state.registrations[p]['code']);state.set_preferences(p,True,True)
state.recap_deadline='2020-01-01T00:00:00+00:00';state.queue_due_recaps()
with tempfile.TemporaryDirectory() as directory:
    q=SharedQuest(Path(directory)/'isolated.db',seed=state)
    start=perf_counter()
    for p in ids:
        q.profile(p);q.completed(p);q.active;q.reset_epoch;q.viewer_revision(p)
    render=perf_counter()-start
    start=perf_counter()
    for _ in range(100):q.viewer_revision(ids[0])
    idle=perf_counter()-start
    print(json.dumps({'participants':100,'read_batches_seconds':round(render,3),'unchanged_poll_checks_seconds':round(idle,3)},indent=2))
