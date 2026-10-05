"""Isolated storage stress check; no server, real participants or SMTP calls."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory
from time import perf_counter
import json
from quest_store import SharedQuest
from quest_core import Quest, payload


def main():
    count = 100
    state = Quest()
    people = state.import_registrations("ADMIN-01", [
        {"name":f"Load Person {i}", "email":f"load{i}@example.test", "source_id":f"load:{i}"}
        for i in range(count)])
    for person in people:
        state.active.add(person)
        state.simulate_completion(person)
        state.approve_draw(person, "STAFF-01")
    with TemporaryDirectory() as folder:
        path = Path(folder)/"stress.sqlite3"
        q = SharedQuest(path, seed=state)
        initial_connections = set(q.connections)
        def client(index):
            start = perf_counter()
            session = SharedQuest(path)
            person, target = people[index], people[(index+1)%count]
            session.scan(person, payload("person", target))
            session.scan(person, payload("person", target))  # idempotent repeat
            card = session.draw(person, "STAFF-01")
            assert session.draw(person, "STAFF-02") == card
            session.viewer_revision(person)
            return perf_counter()-start
        start = perf_counter()
        with ThreadPoolExecutor(max_workers=count) as pool:
            durations = sorted(pool.map(client, range(count)))
        elapsed = perf_counter()-start
        saved = SharedQuest(path)
        expected = initial_connections | {tuple(sorted((people[i],people[(i+1)%count]))) for i in range(count)}
        assert saved.connections == expected, "Missing or duplicate connections"
        assert len(saved.assignments) == count, "Lost prize assignment"
        assert len(set(saved.assignments.values())) == count, "Duplicate winner assignment"
        assert len(saved.draw_log) == count, "Duplicate draw"
        print(json.dumps({"clients":count,"errors":0,"elapsed_seconds":round(elapsed,2),
            "client_p95_seconds":round(durations[94],2),"client_max_seconds":round(durations[-1],2),
            "scope":"local SQLite storage only; not Streamlit Cloud/browser capacity"},indent=2))


if __name__ == "__main__":
    main()
