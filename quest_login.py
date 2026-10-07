"""Revocable, time-limited browser logins for the fictional rehearsal.

The browser holds a random bearer token, never an activation code. Only its
SHA-256 digest is persisted. This demo's JS cookie is not HttpOnly; production
authentication should use a server-managed HttpOnly cookie or OIDC.
"""
import hashlib
import secrets
import time

COOKIE_NAME = "afjd_rehearsal_login_4h"
LOGIN_SECONDS = 4 * 60 * 60


class BrowserLogins:
    def __init__(self, quest, allow_demo=True):
        self.quest = quest
        self.allow_demo = allow_demo
        with quest.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS browser_logins_4h (digest TEXT PRIMARY KEY, person TEXT NOT NULL, expires REAL NOT NULL, epoch TEXT NOT NULL)")

    @staticmethod
    def epoch(state, person):
        version = state.registrations.get(person, {}).get("auth_version", 0)
        return str(state.reset_epoch)+(":"+str(version) if version else "")

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def issue(self, code):
        role, person = self.quest.demo_login(code)
        if role != "participant":
            raise ValueError("Nur persÃ¶nliche Teilnehmenden-ZugÃ¤nge kÃ¶nnen gespeichert werden.")
        if not self.allow_demo and person not in self.quest.registrations:
            raise ValueError("Demo-Zugänge sind deaktiviert. Verwende deinen Code vom Welcome Desk.")
        token = secrets.token_urlsafe(32)
        with self.quest.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self.quest._load(db)
            db.execute("DELETE FROM browser_logins_4h WHERE expires <= ? ", (time.time(),))
            db.execute("INSERT INTO browser_logins_4h VALUES (?, ?, ?, ?)", (self.digest(token), person, time.time() + LOGIN_SECONDS, self.epoch(state, person)))
        return token

    def resolve(self, token):
        if not isinstance(token, str) or len(token) != 43:
            return None
        with self.quest.connect() as db:
            row = db.execute("SELECT person, expires, epoch FROM browser_logins_4h WHERE digest = ?", (self.digest(token),)).fetchone()
            state = self.quest._load(db)
            if row and row[1] > time.time() and row[2] == self.epoch(state, row[0]) and row[0] in state.active:
                if self.allow_demo or row[0] in state.registrations:
                    return row[0]
        return None

    def revoke(self, token):
        if isinstance(token, str):
            with self.quest.connect() as db:
                db.execute("DELETE FROM browser_logins_4h WHERE digest = ?", (self.digest(token),))


def guarded_login(quest, code, source, allow_demo=True):
    """Limit failed guesses per browser address and initials, across sessions."""
    import re
    prefix=re.match(r"AFJD-[A-Z]{2}-",code.strip().upper())
    bucket=hashlib.sha256((str(source or "unknown")+":"+(prefix.group() if prefix else "other")).encode()).hexdigest()
    now=time.time()
    with quest.connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS login_attempts (bucket TEXT, created REAL)")
        db.execute("DELETE FROM login_attempts WHERE created < ?",(now-300,))
        count=db.execute("SELECT COUNT(*) FROM login_attempts WHERE bucket=?",(bucket,)).fetchone()[0]
    if count>=5:
        raise ValueError("Zu viele ungültige Versuche. Bitte warte fünf Minuten oder frage am Welcome Desk nach.")
    try:
        if not allow_demo:
            allowed = {"ADMIN-01", "STAFF-01", "STAFF-02", "SCREEN-01"} | {r["code"] for r in quest.registrations.values()}
            if code.strip().upper() not in allowed:
                raise ValueError("Gib deinen gültigen persönlichen Zugangscode vom Welcome Desk ein.")
        return quest.demo_login(code)
    except ValueError:
        with quest.connect() as db: db.execute("INSERT INTO login_attempts VALUES (?,?)",(bucket,now))
        raise
