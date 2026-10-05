"""Server-lifetime recap dispatcher. No Streamlit calls inside worker threads."""
import threading
from quest_store import SharedQuest
from quest_mail import send_once

_lock = threading.Lock()
_workers = {}


def dispatch_due(q, config):
    if config.get("enabled") is not True or config.get("auto_send", True) is not True:
        return
    q.maintenance()
    for key, entry in q.outbox.items():
        if entry.get("attempted"):
            continue
        draft = q.claim_recap_delivery(key) if entry.get("kind") == "recap" else q.claim_application_delivery(key)
        if draft is None:
            continue
        try:
            status = send_once(draft.encode("utf-8"), config, q.path, "ADMIN-01", delivery_scope="scheduled:"+str(q.reset_epoch)+":"+key)
        except ValueError as error:
            status = str(error)
        except Exception:
            status = "Versand unterbrochen. Vor erneutem Versand das Absenderpostfach prüfen."
        q.mark_recap_delivery(key, status)


def ensure_worker(path, config):
    """One worker per database; refresh configuration without spawning duplicates."""
    with _lock:
        if path in _workers:
            _workers[path]["config"] = dict(config)
            return
        state = {"config":dict(config)}
        _workers[path] = state
        def run():
            q = None
            while True:
                try:
                    if q is None:
                        q = SharedQuest(path)
                    with _lock:
                        current = dict(state["config"])
                    q.maintenance()
                    if current.get("enabled") is True and current.get("auto_send", True) is True:
                        dispatch_due(q, current)
                except Exception:
                    # Never log credentials or participant data. A later tick
                    # may recover storage availability; attempted mail is not retried.
                    q = None
                threading.Event().wait(5)
        threading.Thread(target=run, name="afjd-recap-dispatch", daemon=True).start()
