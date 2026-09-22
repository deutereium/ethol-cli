#!/usr/bin/env python3

"""List all enrolled classes with their current presensi (attendance) status.

Run this right after the Et-Hol notifier fires to see which classes have an
open presensi window. Each row shows the class name, class id (usable as the
argument to ``attend.py``), and whether attendance is currently available.

Usage:
    python fetch-attendance.py [--only-available] [--json] [--year 2026] [--semester 1]
"""

import argparse
import json
import sys
import os
from datetime import datetime

sys.path.append(os.path.abspath('.'))

from ethol_notifier.auth import login
from ethol_notifier.scraper import (
    fetch_config,
    get_class_list,
    fetch_active_presensi,
)


def current_year_semester():
    """Guess the academic year/semester based on the current date.
    Dec-Feb => semester 2 of the running year; Aug-Jan => semester 1.
    """
    now = datetime.now()
    if now.month >= 7:
        return now.year, 1
    return now.year - 1, 2


def main():
    parser = argparse.ArgumentParser(description="List classes and their presensi status.")
    parser.add_argument("--only-available", action="store_true",
                        help="Only show classes with an open presensi window.")
    parser.add_argument("--json", action="store_true",
                        help="Print the result as JSON.")
    parser.add_argument("--year", type=int, default=None,
                        help="Academic year (default: auto-detect).")
    parser.add_argument("--semester", type=int, default=None,
                        help="Semester 1/2 (default: auto-detect).")
    args = parser.parse_args()

    try:
        sess = login()
    except Exception as e:
        print(f"[Error] Login failed: {e}")
        sys.exit(1)

    if args.year is None or args.semester is None:
        try:
            config = fetch_config(sess)
            year = config.get("tahun_aktif") or args.year
            semester = config.get("semester_aktif") or args.semester
        except Exception:
            year, semester = current_year_semester()
    if args.year is not None:
        year = args.year
    if args.semester is not None:
        semester = args.semester

    try:
        classes = get_class_list(sess, year, semester)
    except Exception as e:
        print(f"[Error] Fetching class list: {e}")
        sys.exit(1)

    rows = []
    for cls in classes:
        class_id = cls["id"]
        jenis_schema = cls["jenis_schema"]
        status = "closed"
        open_info = None
        if class_id is not None and jenis_schema is not None:
            try:
                active = fetch_active_presensi(sess, class_id, jenis_schema)
                open_entries = [e for e in active if e.get("open") == 1]
                if open_entries:
                    status = "available"
                    open_info = open_entries[0]
            except Exception as e:
                status = f"error ({e})"
        rows.append({
            "id": class_id,
            "nama": cls["nama"],
            "kelas": cls["kelas"],
            "pararel": cls["pararel"],
            "dosen": cls["dosen"],
            "jenis_schema": jenis_schema,
            "status": status,
            "open": open_info,
        })

    if args.only_available:
        rows = [r for r in rows if r["status"] == "available"]

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return

    print(f"=== Kelas {year} semester {semester} ({datetime.now():%H:%M:%S}) ===")
    if not rows:
        print("(none)")
        return
    for r in rows:
        marker = {
            "available": "🟢",
            "closed": "⚪",
        }.get(r["status"], "🔴")
        name = r["nama"] or "?"
        kelas = r["kelas"] or ""
        if r["pararel"]:
            kelas += f" Pararel {r['pararel']}"
        print(f"{marker} [{r['id']}] {name}  ({kelas})  → {r['status']}")


if __name__ == "__main__":
    main()