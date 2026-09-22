#!/usr/bin/env python3

"""Fetch the dashboard after CAS login and inspect the response.
We also dump the list of cookies set by the server. This helps verify that
the session is truly authenticated.
"""

import sys
import os

# Ensure the package folder is on the import path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from ethol_notifier.auth import login

import requests

def main():
    sess = login()
    # Access the student dashboard (which loads the SPA)
    url = "https://ethol.pens.ac.id/mahasiswa/beranda"
    resp = sess.get(url, timeout=30, allow_redirects=True)
    print("Final URL:", resp.url)
    print("Status code:", resp.status_code)
    print("Number of cookies:", len(sess.cookies))
    for c in sess.cookies:
        print(f"  {c.name} = {c.value[:20]}…")
    # Save the raw HTML for manual inspection
    out_path = os.path.join(os.path.dirname(__file__), "dashboard_raw.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("Saved raw HTML to", out_path, "(first 200 chars):")
    print(resp.text[:200])

if __name__ == "__main__":
    main()
