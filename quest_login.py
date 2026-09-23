"""Revocable, time-limited browser logins for the fictional rehearsal.

The browser holds a random bearer token, never an activation code. Only its
SHA-256 digest is persisted. This demo's JS cookie is not HttpOnly; production
authentication should use a server-managed HttpOnly cookie or OIDC.
"""
import hashlib
import secrets
import time

COOKIE_NAME = "afjd_rehearsal_login"
LOGIN_SECONDS = 12 * 60 * 60


class BrowserLogins:
    def __init__(self, quest):
        self.quest = quest
        with quest.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS browser_logins (digest TEXT PRIMARY KEY, person TEXT NOT NULL, expires REAL NOT NULL, epoch TEXT NOT NULL)")

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def issue(self, code):
        role, person = self.quest.demo_login(code)
        if role != "participant":
            raise ValueError("Only participant logins can be remembered.")
        token = secrets.token_urlsafe(32)
        with self.quest.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self.quest._load(db)
            db.execute("DELETE FROM browser_logins WHERE expires <= ? OR epoch != ?", (time.time(), str(state.reset_epoch)))
            db.execute("INSERT INTO browser_logins VALUES (?, ?, ?, ?)", (self.digest(token), person, time.time() + LOGIN_SECONDS, str(state.reset_epoch)))
        return token

    def resolve(self, token):
        if not isinstance(token, str) or len(token) != 43:
            return None
        with self.quest.connect() as db:
            row = db.execute("SELECT person, expires, epoch FROM browser_logins WHERE digest = ?", (self.digest(token),)).fetchone()
            state = self.quest._load(db)
            if row and row[1] > time.time() and row[2] == str(state.reset_epoch) and row[0] in state.active:
                return row[0]
        return None

    def revoke(self, token):
        if isinstance(token, str):
            with self.quest.connect() as db:
                db.execute("DELETE FROM browser_logins WHERE digest = ?", (self.digest(token),))
