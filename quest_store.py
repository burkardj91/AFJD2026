"""Shared local rehearsal state. SQLite transactions serialize tablet mutations.

This is not production authentication: demo credentials are public.
"""
from dataclasses import fields
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
from quest_core import Quest

def encode(value):
    if isinstance(value, set):
        return {"$set":[encode(v) for v in sorted(value)]}
    if isinstance(value, tuple):
        return {"$tuple":[encode(v) for v in value]}
    if isinstance(value, list):
        return [encode(v) for v in value]
    if isinstance(value, dict):
        return {k:encode(v) for k,v in value.items()}
    return value

def decode(value):
    if isinstance(value, dict):
        if "$set" in value:
            return set(decode(v) for v in value["$set"])
        if "$tuple" in value:
            return tuple(decode(v) for v in value["$tuple"])
        return {k:decode(v) for k,v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value

class SharedQuest:
    MUTATIONS = {"demo_login","activate","update_profile","simulate_completion","scan","confirm","decline","set_preferences","assign","submit","draw","approve_draw","refresh"}

    def __init__(self, path=None, seed=None):
        self.path = str(path or os.environ.get("QUEST_DB_PATH") or Path(__file__).with_name(".localdata") / "quest_demo.sqlite3")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS event (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL, revision INTEGER NOT NULL)")
            initial = seed if seed is not None and not isinstance(seed, SharedQuest) else Quest()
            body = json.dumps(encode({f.name:getattr(initial,f.name,f.default_factory()) for f in fields(Quest)}))
            db.execute("INSERT OR IGNORE INTO event VALUES(1,?,0)", (body,))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            with db:
                yield db
        finally:
            db.close()

    def revision(self):
        with self.connect() as db:
            return db.execute("SELECT revision FROM event WHERE id=1").fetchone()[0]

    def _load(self, db):
        value = decode(json.loads(db.execute("SELECT body FROM event WHERE id=1").fetchone()[0]))
        return Quest(**value)

    def __getattr__(self, name):
        if name in {f.name for f in fields(Quest)}:
            with self.connect() as db:
                return getattr(self._load(db), name)
        if not hasattr(Quest, name):
            raise AttributeError(name)
        def call(*args, **kwargs):
            with self.connect() as db:
                if name in self.MUTATIONS:
                    db.execute("BEGIN IMMEDIATE")
                state = self._load(db)
                before = json.dumps(encode({f.name:getattr(state,f.name) for f in fields(Quest)}),sort_keys=True)
                result = getattr(state,name)(*args,**kwargs)
                if name in self.MUTATIONS:
                    after = json.dumps(encode({f.name:getattr(state,f.name) for f in fields(Quest)}),sort_keys=True)
                    if after != before:
                        db.execute("UPDATE event SET body=?, revision=revision+1 WHERE id=1", (after,))
                return result
        return call
