#!/usr/bin/env python3

"""Fetch and display all Et‑Hol notifications.
Shows the most recent 5 notifications with a ✅ marker for those already
processed (i.e., present in state.json).
"""

import sys, os, json, datetime

# Add project root to import path
sys.path.append(os.path.abspath('.'))

from ethol_notifier.auth import login
from ethol_notifier.scraper import fetch_notifications
from ethol_notifier.state import load_last_ids


def parse_timestamp(ts: str) -> datetime.datetime:
    """Parse Et‑Hol timestamps (ISO or relative format) into a datetime.
    Falls back to parsing ISO format if possible.
    """
    try:
        return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except Exception:
        # Try to extract ISO part from strings like "Selasa, 15 September 2026 - 10:33"
        import re
        iso_match = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', ts)
        if iso_match:
            return datetime.datetime.fromisoformat(iso_match.group())
        return datetime.datetime.min


def main():
    try:
        sess = login()
    except Exception as e:
        print(f"[Error] Login failed: {e}")
        sys.exit(1)

    try:
        all_notes = fetch_notifications(sess)
    except Exception as e:
        print(f"[Error] Fetching notifications: {e}")
        sys.exit(1)

    # Load IDs we've already processed
    seen_ids = load_last_ids()

    # Sort by timestamp descending (newest first)
    def sort_key(note):
        ts = note.get('time', '')
        # Try to parse ISO timestamp from the entry itself if available
        iso = note.get('createdAt') or note.get('timestamp')
        dt = parse_timestamp(iso) if iso else parse_timestamp(ts)
        return dt

    sorted_notes = sorted(all_notes, key=sort_key, reverse=True)

    print(f"=== All notifications ({len(sorted_notes)}) ===")
    # Show the latest 5
    for n in sorted_notes[:5][::-1]:
        uid = n.get('id')
        is_seen = uid in seen_ids
        marker = "✅ " if is_seen else "   "
        time_str = n.get('time', '')
        text = n.get('text', '')
        print(f"{marker}[{time_str}] {text}")

if __name__ == "__main__":
    main()
