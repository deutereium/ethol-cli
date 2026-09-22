#!/usr/bin/env python3

"""Attend a class on Et-Hol via the presensi API.

Finds the currently-open presensi window for the given class id and submits
your attendance, exactly like clicking the green "Presensi" button on the
class page:

    https://ethol.pens.ac.id/mahasiswa/matakuliah/<class_id>

Usage:
    python attend.py <class_id> [--year 2026] [--semester 1] [--verbose]

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

sys.path.append(os.path.abspath('.'))

from ethol_notifier.auth import login
from ethol_notifier.scraper import (
    get_class_list,
    fetch_active_presensi,
    fetch_attendance_history,
    submit_attendance,
)


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
    parser.add_argument("class_id", type=int, help="Class id (from fetch-attendance.py).")
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

    # Resolve the class + find its jenis_schema.
    resolver_year, resolver_semester = args.year, args.semester
    if resolver_year is None or resolver_semester is None:
        try:
            from ethol_notifier.scraper import fetch_config
            config = fetch_config(sess)
            resolver_year = config.get("tahun_aktif") or resolver_year
            resolver_semester = config.get("semester_aktif") or resolver_semester
        except Exception:
            pass

    cls = None
    if resolver_year is not None and resolver_semester is not None:
        try:
            classes = get_class_list(sess, resolver_year, resolver_semester)
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

    # 1. Check the open presensi window.
    try:
        active = fetch_active_presensi(sess, class_id, jenis_schema)
    except Exception as e:
        print(f"[Error] Could not check presensi status: {e}")
        sys.exit(1)

    open_entries = [e for e in active if e.get("open") == 1]
    if not open_entries:
        print(f"[Not Available] Presensi is not currently open for [{class_id}] {class_name}.")
        sys.exit(2)

    key = open_entries[0].get("key")
    if not key:
        print(f"[Error] Open presensi entry has no 'key' field.")
        sys.exit(1)

    if args.verbose:
        print(json.dumps(open_entries[0], indent=2, ensure_ascii=False))

    # 2. Already attended?
    try:
        history = fetch_attendance_history(sess, class_id, jenis_schema, nomor)
    except Exception:
        history = []
    if any(h.get("key") == key for h in history):
        print(f"[Already Attended] [{class_id}] {class_name}")
        sys.exit(0)

    # 3. Submit attendance.
    try:
        result = submit_attendance(sess, class_id, jenis_schema, nomor, key)
    except Exception as e:
        print(f"[Error] Attendance submission failed: {e}")
        sys.exit(1)

    sukses = result.get("sukses", result.get("status") == "success")
    if sukses or args.verbose:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    # 4. Verify via riwayat.
    try:
        history = fetch_attendance_history(sess, class_id, jenis_schema, nomor)
        attended = any(h.get("key") == key for h in history)
    except Exception:
        attended = bool(sukses)

    if attended:
        print(f"[Success] Attended class [{class_id}] {class_name}")
        sys.exit(0)

    print(f"[Error] Attendance may not have been recorded. Server response: {result}")
    sys.exit(1)


if __name__ == "__main__":
    main()