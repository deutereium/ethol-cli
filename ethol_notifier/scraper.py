import requests
import json
import hashlib

# Endpoint for all notifications (returns a JSON list directly)
ALL_NOTIF_ENDPOINT = "https://ethol.pens.ac.id/api/notifikasi/mahasiswa?filterNotif=SEMUA"
UNREAD_COUNT_ENDPOINT = "https://ethol.pens.ac.id/api/notifikasi/mahasiswa-belum-baca"


def _extract_notifications(data) -> list:
    """Convert the raw API response into a list of dicts:
        [{"id": <uid>, "text": <msg>, "time": <ts>}, ...]
    The endpoint returns a **JSON list** of objects with keys:
        idNotifikasi, keterangan, waktuNotifikasi, createdAt, etc.
    """
    notifications = []
    # Expect data to be a list of notification objects
    items = data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []

    for entry in items:
        if not isinstance(entry, dict):
            continue
        # Map Et‑Hol fields to our canonical fields
        uid = entry.get("idNotifikasi") or entry.get("id")
        title = entry.get("keterangan") or entry.get("title") or ""

        # In Et‑Hol, "dataTerkait" can be a string (e.g. "222694-4") or a dict
        data_terkait = entry.get("dataTerkait")
        detail = ""
        if isinstance(data_terkait, dict):
            detail = data_terkait.get("keterangan") or ""

        # Fallback to other message fields
        detail = detail or entry.get("pesan") or entry.get("message") or ""

        # Construct a readable text
        if title and detail and detail != title:
            text = f"{title}: {detail}"
        else:
            text = title or detail

        ts = entry.get("waktuNotifikasi") or entry.get("createdAt") or entry.get("timestamp") or ""
        if not uid:
            uid = hashlib.sha256(f"{ts}:{text}".encode()).hexdigest()
        notifications.append({"id": uid, "text": text, "time": ts})
    return notifications


def fetch_notifications(session: requests.Session) -> list:
    """Fetch all notifications using filterNotif=SEMUA.
    Returns a list of dictionaries with ``id``, ``text``, and ``time`` keys.
    """
    resp = session.get(ALL_NOTIF_ENDPOINT, timeout=30, headers={"Accept": "application/json"})
    resp.raise_for_status()
    data = resp.json()
    return _extract_notifications(data)
