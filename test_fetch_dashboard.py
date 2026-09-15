#!/usr/bin/env python3

"""Test script to fetch the Et‑Hol student dashboard after login and
print the raw HTML of the notification panel.

The dashboard URL (after a successful CAS login) is:
    https://ethol.pens.ac.id/mahasiswa/beranda
"""

from ethol_notifier.auth import login
import requests

DASHBOARD_URL = "https://ethol.pens.ac.id/mahasiswa/beranda"

def main():
    try:
        sess = login()
        resp = sess.get(DASHBOARD_URL, timeout=30)
        resp.raise_for_status()
        html = resp.text
        # Simple heuristic: look for a container that likely holds notifications
        # Users can adjust the selector later if needed.
        print("--- Dashboard HTML snippet (first 500 chars) ---")
        print(html[:500])
        # Optionally, you could write the full HTML to a file for inspection
        with open("dashboard.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Full dashboard saved to dashboard.html")
    except Exception as e:
        print("Error fetching dashboard:", e)

if __name__ == "__main__":
    main()
