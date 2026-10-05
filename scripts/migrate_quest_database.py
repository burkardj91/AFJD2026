"""Copy an offline SQLite event into an empty PostgreSQL database; never overwrite."""
import argparse
import sqlite3
import sys
import tomllib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quest_database import connect, is_postgres

TABLES = {
    "event": "id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL, revision INTEGER NOT NULL",
    "browser_logins_4h": "digest TEXT PRIMARY KEY, person TEXT NOT NULL, expires REAL NOT NULL, epoch TEXT NOT NULL",
    "login_attempts": "bucket TEXT, created REAL",
    "smtp_deliveries": "id TEXT PRIMARY KEY, status TEXT NOT NULL, recipient TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP",
}


def migrate(source, destination, apply=False):
    if not is_postgres(destination):
        raise ValueError("The destination must be PostgreSQL.")
    source = Path(source).resolve(strict=True)
    db = sqlite3.connect(source.as_uri()+"?mode=ro", uri=True)
    try:
        db.execute("BEGIN")
        present = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "event" not in present:
            raise ValueError("Source contains no event.")
        rows = {name:db.execute(f"SELECT * FROM {name}").fetchall() if name in present else [] for name in TABLES}
        if len(rows["event"]) != 1:
            raise ValueError("Source must contain exactly one event.")
    finally:
        db.close()
    with connect(destination) as target:
        target.execute("BEGIN IMMEDIATE")
        for name in TABLES:
            if target.execute("SELECT to_regclass(?)", (name,)).fetchone()[0] is not None:
                raise ValueError("Destination already contains application tables. Nothing overwritten.")
        if apply:
            for name, schema in TABLES.items():
                target.execute(f"CREATE TABLE {name} ({schema})")
                for row in rows[name]:
                    placeholders = ",".join("?" for _ in row)
                    target.execute(f"INSERT INTO {name} VALUES ({placeholders})", row)
    return sum(map(len, rows.values()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--secrets", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        config = tomllib.loads(Path(args.secrets).read_text(encoding="utf-8"))
        count = migrate(args.source, config.get("QUEST_DATABASE_URL", ""), args.apply)
        print(f"{'Copied' if args.apply else 'Validated; no changes made'}: {count} rows.")
    except Exception:
        print("Migration failed; destination transaction rolled back. Check source, empty target and private configuration.",file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
