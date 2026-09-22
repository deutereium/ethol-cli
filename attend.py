#!/usr/bin/env python3

"""Attend a class on Et-Hol via the presensi API.

Finds the currently-open presensi window for the given class id and submits
your attendance, exactly like clicking the green "Presensi" button on the
class page:

    https://ethol.pens.ac.id/mahasiswa/matakuliah/<class_id>

Usage:
    python attend.py <class_id> [--year 2026] [--semester 1] [--verbose]
    python attend.py [--year 2026] [--semester 1] [--verbose]

When no class_id is given, all enrolled classes are fetched and every class
with an open presensi window is attended automatically.

Exit codes:
    0  attended successfully (or already attended)
    1  login / lookup / network error
    2  presensi window is not open (button greyed out)
"""

import argparse
import base64
import json
import sys
import os
import time
from datetime import datetime

sys.path.append(os.path.abspath('.'))

from ethol_notifier.auth import login
from ethol_notifier.scraper import (
    get_class_list,
    fetch_active_presensi,
    fetch_attendance_history,
    submit_attendance,
    fetch_config,
)


def current_year_semester():
    """Guess the academic year/semester based on the current date.

    Dec-Feb => semester 2 of the running year; Aug-Jan => semester 1.
    """
    now = datetime.now()
    if now.month >= 7:
        return now.year, 1
    return now.year - 1, 2


def resolve_year_semester(sess, args):
    """Resolve (year, semester) in priority order:
    explicit args -> fetch_config -> date-based fallback.
    """
    year, semester = args.year, args.semester
    if year is None or semester is None:
        try:
            config = fetch_config(sess)
            year = config.get("tahun_aktif") or year
            semester = config.get("semester_aktif") or semester
        except Exception:
            pass
    if year is None or semester is None:
        year, semester = current_year_semester()
    return year, semester


def get_student_nomor(sess) -> int:
    """Decode the JWT 'token' cookie to obtain the student 'nomor'."""
    token = None
    for c in sess.cookies:
        if c.name == "token":
            token = c.value
            break
    if not token:
        raise RuntimeError("No 'token' cookie found on the session.")
    parts = token.split(".")
    if len(parts) < 2:
        raise RuntimeError("Malformed token cookie.")
    payload_b64 = parts[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    nomor = payload.get("nomor")
    if nomor is None:
        raise RuntimeError("JWT payload has no 'nomor'.")
    return nomor


def main():
    parser = argparse.ArgumentParser(description="Attend a class presensi on Et-Hol.")
    parser.add_argument("class_id", nargs="?", type=int,
                        help="Class id (from fetch-attendance.py). Omit to auto-attend all available classes.")
    parser.add_argument("--year", type=int, default=None, help="Academic year (default: auto).")
    parser.add_argument("--semester", type=int, default=None, help="Semester 1/2 (default: auto).")
    parser.add_argument("--verbose", action="store_true", help="Print API response details.")
    args = parser.parse_args()

    try:
        sess = login()
    except Exception as e:
        print(f"[Error] Login failed: {e}")
        sys.exit(1)

    try:
        nomor = get_student_nomor(sess)
    except Exception as e:
        print(f"[Error] Could not read student number: {e}")
        sys.exit(1)

    year, semester = resolve_year_semester(sess, args)

    # Single-class mode: class_id was provided.
    if args.class_id is not None:
        try:
            classes = get_class_list(sess, year, semester)
            cls = next((c for c in classes if c["id"] == args.class_id), None)
        except Exception:
            cls = None
        if cls is None:
            print(f"[Error] Class {args.class_id} not found in your enrollment.")
            sys.exit(1)

        class_id = cls["id"]
        jenis_schema = cls["jenis_schema"]
        class_name = cls["nama"] or str(class_id)

        if jenis_schema is None:
            print(f"[Error] No jenis_schema known for class {class_id} ({class_name}).")
            sys.exit(1)

        status, msg = attend_class(sess, nomor, class_id, jenis_schema, class_name,
                                   args.verbose, kuliah_asal=cls.get("kuliah_asal"))
        if status == "not_open":
            print(msg)
            sys.exit(2)
        elif status == "already_attended":
            print(msg)
            sys.exit(0)
        elif status == "attended":
            print(msg)
            sys.exit(0)
        else:
            print(msg)
            sys.exit(1)

    # Auto mode: no class_id -> attend every class with an open presensi window.
    try:
        classes = get_class_list(sess, year, semester)
    except Exception as e:
        print(f"[Error] Fetching class list: {e}")
        sys.exit(1)

    attended_count = 0
    already_count = 0
    error_count = 0
    any_open = False
    for cls in classes:
        class_id = cls["id"]
        jenis_schema = cls["jenis_schema"]
        class_name = cls["nama"] or str(class_id)
        if class_id is None or jenis_schema is None:
            continue
        status, msg = attend_class(sess, nomor, class_id, jenis_schema, class_name,
                                   args.verbose, kuliah_asal=cls.get("kuliah_asal"))
        if status == "not_open":
            continue
        any_open = True
        if status == "already_attended":
            already_count += 1
        elif status == "attended":
            attended_count += 1
        elif status == "error":
            error_count += 1
        print(msg)

    if not any_open:
        print("[Not Available] No class currently has an open presensi window.")
        sys.exit(2)
    if attended_count == 0 and already_count == 0:
        if error_count:
            print(f"[Error] {error_count} class(es) open but their attendance could not be confirmed.")
        else:
            print("[Error] No class could be attended.")
        sys.exit(1)
    print(f"[Done] Attended {attended_count} class(es); {already_count} already attended.")
    sys.exit(0)


def attend_class(sess, nomor, class_id, jenis_schema, class_name, verbose, kuliah_asal=None):
    """Attend a single class. Returns (status, message).

    statuses: 'attended', 'already_attended', 'not_open', 'error'

    ``kuliah_asal`` mirrors the class's own ``kuliah_asal`` value from the
    SPA submit payload (normally the class id itself, ``None`` when the
    class list omits it).
    """
    # 1. Check the open presensi window.
    try:
        active = fetch_active_presensi(sess, class_id, jenis_schema)
    except Exception as e:
        return "error", f"[Error] Could not check presensi status for [{class_id}] {class_name}: {e}"

    open_entries = [e for e in active if e.get("open") == 1]
    if not open_entries:
        return "not_open", f"[Not Available] Presensi is not currently open for [{class_id}] {class_name}."

    key = open_entries[0].get("key")
    if not key:
        return "error", f"[Error] Open presensi entry has no 'key' field for [{class_id}] {class_name}."

    if verbose:
        print(json.dumps(open_entries[0], indent=2, ensure_ascii=False))

    # 2. Already attended?
    try:
        history = fetch_attendance_history(sess, class_id, jenis_schema, nomor)
    except Exception:
        history = []
    if any(h.get("key") == key for h in history):
        return "already_attended", f"class {class_name} already attended"

    # 3. Submit attendance.
    try:
        result = submit_attendance(sess, class_id, jenis_schema, nomor, key,
                                   kuliah_asal=kuliah_asal)
    except Exception as e:
        return "error", f"[Error] Attendance submission failed for [{class_id}] {class_name}: {e}"

    sukses = result.get("sukses", result.get("status") == "success")
    pesan = (result.get("pesan") or "").lower()
    if sukses or verbose:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    # 4. Verify via riwayat. The server may commit the record slightly after
    #    returning `sukses: False`, so retry a few times before giving up.
    attended = False
    for attempt in range(3):
        try:
            history = fetch_attendance_history(sess, class_id, jenis_schema, nomor)
            attended = any(h.get("key") == key for h in history)
        except Exception:
            attended = bool(sukses)
        if attended:
            break
        time.sleep(1.5)

    if attended:
        if sukses:
            return "attended", f"[Success] Attended class [{class_id}] {class_name}"
        return "already_attended", f"class {class_name} already attended"

    # The server flatly rejecting the key usually means the session is
    # already mirrored in the DB (duplicate or "sudah melakukan").
    if "sudah" in pesan or "ganda" in pesan or "duplikat" in pesan:
        return "already_attended", f"class {class_name} already attended"

    return "error", f"[Error] Attendance may not have been recorded for [{class_id}] {class_name}. Server response: {result}"


if __name__ == "__main__":
    main()