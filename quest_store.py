"""Transactional shared event state with SQLite and optional PostgreSQL storage."""
from dataclasses import fields
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import threading
from quest_database import connect, is_postgres
import json
import os
from pathlib import Path
from importlib import import_module

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

_initialization_lock = threading.Lock()
_initialized = set()

class SharedQuest:
    MUTATIONS = {"reset_activities","prepare_reserves","return_prize","reset_imports","set_annotation","claim_application_delivery","claim_recap_delivery","correct_registration","mark_recap_delivery","import_registrations","collect_gift","annotate_company","schedule_recaps","queue_due_recaps","configure_raffle","resolve_raffle","reset_demo","demo_login","activate_badge","activate","update_profile","simulate_completion","scan","confirm","decline","set_preferences","assign","submit","draw","approve_draw","refresh"}

    def __init__(self, path=None, seed=None):
        # Resolve the current model on construction: Streamlit may reload quest_core
        # while keeping this storage module imported. Never retain its old class.
        self.model = import_module("quest_core").Quest
        self.path = str(path or os.environ.get("QUEST_DATABASE_URL") or os.environ.get("QUEST_DB_PATH") or Path(__file__).with_name(".localdata") / "quest_demo.sqlite3")
        self._cached_revision = None
        self._cached_state = None
        with _initialization_lock:
            if self.path not in _initialized or (not is_postgres(self.path) and not Path(self.path).exists()):
                with self.connect() as db:
                    if not is_postgres(self.path):
                        db.execute("PRAGMA journal_mode=WAL")
                        db.execute("PRAGMA synchronous=FULL")
                    db.execute("BEGIN IMMEDIATE")
                    db.execute("CREATE TABLE IF NOT EXISTS event (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL, revision INTEGER NOT NULL)")
                    db.execute("CREATE TABLE IF NOT EXISTS browser_logins_4h (digest TEXT PRIMARY KEY, person TEXT NOT NULL, expires REAL NOT NULL, epoch TEXT NOT NULL)")
                    db.execute("CREATE TABLE IF NOT EXISTS login_attempts (bucket TEXT, created REAL)")
                    db.execute("CREATE TABLE IF NOT EXISTS smtp_deliveries (id TEXT PRIMARY KEY, status TEXT NOT NULL, recipient TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
                    initial = seed if seed is not None and not isinstance(seed, SharedQuest) else self.model()
                    body = json.dumps(encode({f.name:getattr(initial,f.name,f.default_factory()) for f in fields(self.model)}))
                    db.execute("INSERT OR IGNORE INTO event VALUES(1,?,0)", (body,))
                _initialized.add(self.path)

    def connect(self):
        return connect(self.path)

    def snapshot(self):
        """A detached, consistent view. Never expose the cached mutable model."""
        with self.connect() as db:
            revision = db.execute("SELECT revision FROM event WHERE id=1").fetchone()[0]
            if revision != self._cached_revision:
                # Fetch revision with body to avoid tagging a newer body with an
                # older revision when another client commits between reads.
                body, revision = db.execute("SELECT body, revision FROM event WHERE id=1").fetchone()
                self._cached_state = self._decode(body)
                self._cached_revision = revision
        return deepcopy(self._cached_state)

    def viewer_revision(self, person=None):
        if not person:
            return str(self.revision())
        state = self.snapshot()
        contacts = state.people(person)
        cards = {c for c,p in state.assignments.items() if p == person}
        value = [state.reset_epoch, state.profile(person), state.completed(person),
                 {p:state.profile(p) for p in contacts}, contacts & state.sharing,
                 person in state.sharing, person in state.recap, person in state.privacy_reviewed,
                 person in state.unlocked, state.draw_approvals.get(person),
                 state.visits.get(person), state.company_contacts.get(person),
                 {c:state.applications.get(c) for c in cards}, cards,
                 state.registrations.get(person)]
        return hashlib.sha256(json.dumps(encode(value),sort_keys=True).encode()).hexdigest()

    def maintenance(self):
        """Cheap no-op before deadlines; mutating methods recheck under lock."""
        state = self.snapshot()
        now = datetime.now(timezone.utc)
        if state.raffle.get("status") == "scheduled" and now >= datetime.fromisoformat(state.raffle["deadline"]):
            self.resolve_raffle()
        if state.recap_deadline and now >= datetime.fromisoformat(state.recap_deadline):
            missing = any("recap:"+p not in state.outbox and not state.registrations.get(p,{}).get("identity_pending") for p in state.recap & state.active)
            if missing:
                self.queue_due_recaps()

    def revision(self):
        with self.connect() as db:
            return db.execute("SELECT revision FROM event WHERE id=1").fetchone()[0]

    def _load(self, db):
        return self._decode(db.execute("SELECT body FROM event WHERE id=1").fetchone()[0])

    def _decode(self, body):
        value = decode(json.loads(body))
        if value.get("catalog_version", 0) < 2:
            for person, company in import_module("quest_core").DEFAULT_AFFILIATIONS.items():
                value.setdefault("affiliations", {}).setdefault(person, company)
            value["catalog_version"] = 2
        if not value.get("recap_deadline"):
            value["recap_deadline"] = "2026-10-08T21:00:00+02:00"
        state = self.model(**value)
        for sender, target in list(state.pending):
            state.connections.add(tuple(sorted((sender, target))))
        state.pending.clear()
        if state.catalog_version < 4:
            from quest_registration import MENTORING_ANNOTATIONS
            for person, row in state.registrations.items():
                if row.get("annotation", "").strip().casefold() in MENTORING_ANNOTATIONS:
                    state.affiliations[person] = "sv-5w8j"
            # Re-evaluate stored scans against the published quests. Already
            # assigned prizes remain reserved; obsolete approvals do not.
            state.unlocked = set(state.assignments.values())
            for person in state.active:
                state.refresh(person)
            state.draw_approvals = {p:v for p,v in state.draw_approvals.items() if p in state.unlocked}
            state.catalog_version = 4
        return state

    def __getattr__(self, name):
        if name in {f.name for f in fields(self.model)}:
            return getattr(self.snapshot(), name)
        if not hasattr(self.model, name):
            raise AttributeError(name)
        def call(*args, **kwargs):
            if name not in self.MUTATIONS:
                return getattr(self.snapshot(),name)(*args,**kwargs)
            with self.connect() as db:
                if name in self.MUTATIONS:
                    db.execute("BEGIN IMMEDIATE")
                state = self._load(db)
                before = json.dumps(encode({f.name:getattr(state,f.name) for f in fields(self.model)}),sort_keys=True)
                if name in self.MUTATIONS and name != "resolve_raffle":
                    state.resolve_raffle()
                    state.queue_due_recaps()
                result = getattr(state,name)(*args,**kwargs)
                if name in self.MUTATIONS:
                    after = json.dumps(encode({f.name:getattr(state,f.name) for f in fields(self.model)}),sort_keys=True)
                    if after != before:
                        db.execute("UPDATE event SET body=?, revision=revision+1 WHERE id=1", (after,))
                return result
        return call
