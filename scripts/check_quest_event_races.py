"""Isolated race/privacy checks; real SMTP and real event databases are never used."""
import sys, json, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import perf_counter
from unittest.mock import patch
from quest_core import Quest, contact_rows, recap_draft
from quest_store import SharedQuest
from quest_mail_worker import dispatch_due

def main():
    with tempfile.TemporaryDirectory() as folder:
        state=Quest()
        people=state.import_registrations('ADMIN-01', [dict(name=f'Stress Person {i}',email=f'person{i}@example.test',source_id=f'security:{i}') for i in range(100)])
        for i,p in enumerate(people):
            state.demo_login(state.registrations[p]['code'])
            state.set_preferences(p, i%2==0, True)
            state.profiles[p]={'address':f'PRIVATE-ADDRESS-{i}', 'date_of_birth':'1901-02-03'}
            state.simulate_completion(p)
            state.approve_draw(p,'STAFF-01')
        state.recap_deadline='2999-01-01T00:00:00+00:00'
        q=SharedQuest(Path(folder)/'isolated.db', seed=state)
        started=perf_counter()
        def compete(_): return SharedQuest(q.path).draw(people[0],'STAFF-01')
        with ThreadPoolExecutor(max_workers=100) as pool: cards=list(pool.map(compete,range(100)))
        assert len(set(cards))==1 and len(q.assignments)==1 and len(q.draw_log)==1
        print("PASS: 100 simultaneous requests assigned one prize", flush=True)
        card=cards[0]
        try: q.scan(people[1], 'https://afjd2026.streamlit.app/?claim='+card)
        except ValueError: pass
        else: raise AssertionError('Another person could claim prize')
        # Many clients repeatedly scan the same pair; only one edge survives.
        before=set(q.connections)
        def scan(_): return SharedQuest(q.path).scan(people[0],q.registrations[people[1]]['id'])
        with ThreadPoolExecutor(max_workers=100) as pool: list(pool.map(scan,range(100)))
        assert q.connections==before|{tuple(sorted(people[:2]))}
        rows=str(contact_rows(q,people[0]));draft=recap_draft(q,people[0]).decode()
        assert 'person1@example.test' not in rows+draft
        assert 'PRIVATE-ADDRESS-' not in rows+draft and '1901-02-03' not in rows+draft
        graph=json.dumps(q.public_network())
        for p in people:
            for private in (p, q.registrations[p]['id'], q.registrations[p]['code'], q.registrations[p]['email']):
                assert private not in graph
        print("PASS: duplicate scans, prize ownership and private data checks", flush=True)
        # Independent dispatchers compete for the same 100 due messages.
        state=q.snapshot();state.recap_deadline='2020-01-01T00:00:00+00:00'
        due=SharedQuest(Path(folder)/'due.db',seed=state)
        sent=[];lock=Lock()
        mail_started=perf_counter()
        def fake_send(draft,*args,**kwargs):
            with lock: sent.append(kwargs['delivery_scope'])
            return 'Simulated acceptance; no SMTP'
        with patch('quest_mail_worker.send_once',side_effect=fake_send):
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda _:dispatch_due(SharedQuest(due.path),{'enabled':True,'mode':'live'}),range(8)))
        assert len(sent)==100 and len(set(sent))==100
        assert all(row.get('attempted') for row in due.outbox.values())
        print(json.dumps({'simultaneous_same_prize_requests':100,'unique_prizes_assigned':1,
            'simultaneous_duplicate_scans':100,'mail_workers':8,'unique_mock_mail_deliveries':100,
            'privacy_and_cross_person_claim_checks':'passed','elapsed_seconds':round(perf_counter()-started,2),
            'mail_race_seconds':round(perf_counter()-mail_started,2),'real_emails_sent':0},indent=2))
if __name__=='__main__': main()
