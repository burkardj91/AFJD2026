"""Shared SQL transport for event state, browser logins and SMTP receipts."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import threading

_lock = threading.Lock()
_pools = {}


def is_postgres(location):
    return str(location).startswith(("postgresql://", "postgres://"))


class PostgresConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, parameters=()):
        # Only internal SQL statements pass through this adapter; values always
        # remain bound parameters. Match SQLite's single event writer semantics.
        if sql == "BEGIN IMMEDIATE":
            return self.connection.execute("SELECT pg_advisory_xact_lock(20261008)")
        sql = sql.replace("?", "%s").replace(" REAL", " DOUBLE PRECISION")
        sql = sql.replace("created_at TEXT DEFAULT CURRENT_TIMESTAMP", "created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP")
        if sql.startswith("INSERT OR IGNORE"):
            sql = sql.replace("INSERT OR IGNORE", "INSERT", 1) + " ON CONFLICT DO NOTHING"
        return self.connection.execute(sql, parameters)


@contextmanager
def connect(location):
    location = str(location)
    if is_postgres(location):
        from psycopg_pool import ConnectionPool
        with _lock:
            if location not in _pools:
                _pools[location] = ConnectionPool(location, min_size=1, max_size=8,
                    timeout=20, open=True, kwargs={"connect_timeout":10,
                    "options":"-c statement_timeout=20000 -c lock_timeout=15000"})
            pool = _pools[location]
        with pool.connection() as db:
            yield PostgresConnection(db)
    else:
        Path(location).parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(location, timeout=30)
        try:
            db.execute("PRAGMA busy_timeout=30000")
            with db:
                yield db
        finally:
            db.close()
