import requests
import json
import hashlib

# Endpoint for all notifications (returns a JSON list directly)
ALL_NOTIF_ENDPOINT = "https://ethol.pens.ac.id/api/notifikasi/mahasiswa?filterNotif=SEMUA"
UNREAD_COUNT_ENDPOINT = "https://ethol.pens.ac.id/api/notifikasi/mahasiswa-belum-baca"

# Presensi / attendance API (reverse-engineered from the SPA bundle)
CONFIG_ENDPOINT = "https://ethol.pens.ac.id/api/auth/config"
KULIAH_ENDPOINT = "https://ethol.pens.ac.id/api/kuliah"
PRESENSI_AKTIF_ENDPOINT = "https://ethol.pens.ac.id/api/presensi/aktif-kuliah"
PRESENSI_MASUK_ENDPOINT = "https://ethol.pens.ac.id/api/presensi/mahasiswa"
PRESENSI_RIWAYAT_ENDPOINT = "https://ethol.pens.ac.id/api/presensi/riwayat"


def extract_class_number(entry: dict):
    """Extract the class (kuliah) identifier from a raw notification object.

    ``dataTerkait`` is either a string like ``"222694-4"`` (class-schema) or a
    dict carrying the class details. Returns ``(nomor, jenis_schema)`` or
    ``(None, None)`` when it cannot be parsed.
    """
    data_terkait = entry.get("dataTerkait") if isinstance(entry, dict) else None
    if isinstance(data_terkait, str):
        parts = data_terkait.strip().split("-")
        if parts and parts[0].isdigit():
            nomor = int(parts[0])
            schema = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
            return nomor, schema
    if isinstance(data_terkait, dict):
        nomor = (
            data_terkait.get("nomor")
            or data_terkait.get("kuliah")
            or data_terkait.get("id")
            or data_terkait.get("nomorKuliah")
        )
        schema = data_terkait.get("jenis_schema") or data_terkait.get("jenisSchema")
        if nomor is not None:
            return int(nomor) if str(nomor).isdigit() else nomor, schema
    if isinstance(entry, dict):
        for key in ("nomorKuliah", "kuliah", "idKuliah"):
            value = entry.get(key)
            if value is not None:
                return int(value) if str(value).isdigit() else value, entry.get("jenis_schema")
    return None, None


def fetch_config(session: requests.Session) -> dict:
    """Fetch the active year/semester configuration."""
    resp = session.get(CONFIG_ENDPOINT, timeout=30, headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()


def get_class_list(session: requests.Session, tahun: int, semester: int) -> list:
    """List the student's enrolled classes for the given year/semester.

    Returns a list of dicts: ``{id, nama, jenis_schema, kelas, pararel, dosen}``.
    """
    resp = session.get(
        KULIAH_ENDPOINT, params={"tahun": tahun, "semester": semester}, timeout=30,
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()
    items = data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []
    classes = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        matakuliah = entry.get("matakuliah") or {}
        classes.append({
            "id": entry.get("nomor"),
            "nama": matakuliah.get("nama") or entry.get("nama") or "",
            "jenis_schema": entry.get("jenisSchema") or entry.get("jenis_schema"),
            "kuliah_asal": entry.get("kuliah_asal"),
            "kelas": entry.get("kelas"),
            "pararel": entry.get("pararel"),
            "dosen": entry.get("dosen"),
        })
    return classes


def fetch_active_presensi(session: requests.Session, kuliah: int, jenis_schema: int) -> list:
    """Return the list of active presensi entries for a class.

    Attendance is currently possible when an entry has ``open == 1``; that
    entry also carries the ``key`` needed to submit attendance.
    """
    resp = session.get(
        PRESENSI_AKTIF_ENDPOINT,
        params={"kuliah": kuliah, "jenis_schema": jenis_schema},
        timeout=30,
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []


def fetch_attendance_history(session: requests.Session, kuliah: int, jenis_schema: int, nomor: int) -> list:
    """Return the recorded attendance history for a class and student number."""
    resp = session.get(
        PRESENSI_RIWAYAT_ENDPOINT,
        params={"kuliah": kuliah, "jenis_schema": jenis_schema, "nomor": nomor},
        timeout=30,
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []


def submit_attendance(session: requests.Session, kuliah: int, jenis_schema: int,
                      mahasiswa: int, key, kuliah_asal=None) -> dict:
    """Submit (attend) a class presensi.

    ``key`` must come from the currently-open presensi entry
    (see :func:`fetch_active_presensi`).
    """
    payload = {
        "kuliah": kuliah,
        "jenis_schema": jenis_schema,
        "mahasiswa": mahasiswa,
        "key": key,
        "kuliah_asal": kuliah_asal,
    }
    resp = session.post(PRESENSI_MASUK_ENDPOINT, json=payload, timeout=30,
                        headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()


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
