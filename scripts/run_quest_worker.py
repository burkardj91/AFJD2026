"""Run scheduled dispatch outside Streamlit, e.g. a managed scheduled job.

python scripts/run_quest_worker.py --secrets /private/secrets.toml [--once]
The same QUEST_DATABASE_URL and email configuration must be used by both.
"""
import argparse
import sys
import time
import tomllib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quest_store import SharedQuest
from quest_mail_worker import dispatch_due
from quest_database import is_postgres


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--secrets", required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    config = tomllib.loads(Path(args.secrets).read_text(encoding="utf-8"))
    location = config.get("QUEST_DATABASE_URL", "")
    if not is_postgres(location):
        parser.error("An external worker requires the same PostgreSQL database as the app.")
    try:
        q = SharedQuest(location)
        while True:
            q.maintenance()
            dispatch_due(q, config.get("email", {}))
            if args.once:
                return
            time.sleep(5)
    except Exception:
        # Do not expose connection strings or participant data in scheduler logs.
        print("AFJD worker failed. Check database availability and private configuration.",file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
