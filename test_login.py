#!/usr/bin/env python3

"""Simple test script to verify CAS login for Et‑Hol.
It uses the same login logic as the notifier. If login succeeds, it prints
"Login successful"; otherwise it prints the exception.
"""

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
