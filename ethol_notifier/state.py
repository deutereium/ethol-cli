import json
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parents[1] / "state.json"


def load_last_ids() -> set:
    """Load the set of notification IDs that have already been sent.
    Returns an empty set if the state file does not exist.
    """
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            return set(data.get("ids", []))
        except Exception:
            # Corrupted file – start fresh
            return set()
    return set()


def save_last_ids(ids: set) -> None:
    """Persist the set of processed notification IDs.
    Stored as a JSON object: {"ids": [<id>, ...]}
    """
    STATE_FILE.write_text(json.dumps({"ids": list(ids)}, indent=2))


def filter_new(notifications: list) -> list:
    """Given a list of notification dicts (each with an 'id' key),
    return only those whose IDs are not already stored.
    Does NOT modify state — call mark_sent() once an item has been
    successfully delivered.
    """
    seen = load_last_ids()
    return [n for n in notifications if n.get("id") not in seen]


def mark_sent(items: list) -> None:
    """Persist the given notification IDs as already sent.
    Only call this after the notification has been successfully delivered.
    """
    seen = load_last_ids()
    seen.update({n.get("id") for n in items})
    save_last_ids(seen)
