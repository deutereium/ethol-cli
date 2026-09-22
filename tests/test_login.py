#!/usr/bin/env python3

"""Simple test script to verify CAS login for Et‑Hol.
It uses the same login logic as the notifier. If login succeeds, it prints
"Login successful"; otherwise it prints the exception.
"""

import sys
import os

# Ensure the package folder is on the import path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from ethol_notifier.auth import login

def main():
    try:
        sess = login()
        # If we get here, the session should contain the Et‑Hol cookie.
        # Print a short confirmation and a few cookies for visibility.
        print("Login successful")
        for c in sess.cookies:
            print(f"Cookie: {c.name}={c.value}")
    except Exception as e:
        print("Login failed:", e)

if __name__ == "__main__":
    main()
