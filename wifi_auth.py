#!/usr/bin/env python3

"""Authenticate to the campus WiFi captive portal (one-shot).

Usage:
    python wifi_auth.py

Reads NETID/PASSWORD from .env (same credentials as Et-Hol).
Exits 0 on success or already-authenticated, 1 on error.
"""

import os
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Load credentials (parallel to ethol_notifier/config.py, but without
# requiring the Telegram env vars) ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

try:
    from dotenv import load_dotenv
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH)
    else:
        print("[WiFi Auth] Error: .env file not found.")
        sys.exit(1)
except ImportError:
    print("[WiFi Auth] Error: python-dotenv is not installed. Run: pip install python-dotenv")
    sys.exit(1)

NETID = os.getenv("NETID")
PASSWORD = os.getenv("PASSWORD")

if not NETID or not PASSWORD:
    print("[WiFi Auth] Error: NETID and PASSWORD must be set in .env")
    sys.exit(1)

# ── Portal discovery ───────────────────────────────────────────────────────────
# The captive portal hostname changes daily (iac2 today, iac33 tomorrow, etc.).
# We probe a well-known HTTP endpoint; the portal intercepts the request and
# redirects to today's login page.  HTTPS is skipped because the portal cannot
# intercept encrypted traffic — a plain HTTP request is required.
PROBE_URL = "http://detectportal.firefox.com/success.txt"
TIMEOUT = 15
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def fetch(url: str, **kwargs) -> requests.Response:
    """GET with retry on transient network errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=TIMEOUT, allow_redirects=False, **kwargs)
            return resp
        except requests.RequestException as e:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(RETRY_DELAY)
    raise RuntimeError("unreachable")  # satisfies type checkers


def post(url: str, data: dict) -> requests.Response:
    """POST with retry on transient network errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, data=data, timeout=TIMEOUT, allow_redirects=True)
            return resp
        except requests.RequestException as e:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(RETRY_DELAY)
    raise RuntimeError("unreachable")


def authenticate() -> int:
    """Perform the captive-portal login flow. Returns exit code."""
    print("[WiFi Auth] Probing captive portal …")

    # Step 1: probe a plain-HTTP URL — the portal intercepts and redirects us
    try:
        resp = fetch(PROBE_URL)
    except requests.RequestException as e:
        print(f"[WiFi Auth] Error: could not reach network (are you on campus WiFi?) — {e}")
        return 1

    # The portal should have intercepted and redirected us; the resolved URL is
    # the current day's login page.
    login_url = resp.url
    if "iac" not in login_url and "/index.php" not in login_url:
        print("[WiFi Auth] Error: probe did not hit the captive portal. "
              "Make sure you are connected to campus WiFi.")
        return 1

    print(f"[WiFi Auth] Portal found at {login_url}")

    # Step 2: fetch the login page
    try:
        resp = fetch(login_url)
    except requests.RequestException as e:
        print(f"[WiFi Auth] Error: could not load login page ({e})")
        return 1

    # Check if already authenticated — redirect away from the portal means success
    if resp.is_redirect:
        location = resp.headers.get("Location", "")
        if location and "iac" not in location and "/index.php" not in location:
            print("[WiFi Auth] Already authenticated — no login needed.")
            return 0

    # Step 3: parse the login form
    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form")
    if form is None:
        print("[WiFi Auth] Error: could not find login form on portal page.")
        return 1

    action = form.get("action", "")
    # Resolve relative action URLs against the login page base
    if action and not action.startswith(("http://", "https://", "//")):
        base = login_url.rsplit("/", 1)[0] + "/"
        action = base + action.lstrip("/")

    hidden = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        value = inp.get("value", "")
        if inp.get("type") == "hidden" and name:
            hidden[name] = value

    payload = {
        "username": NETID,
        "password": PASSWORD,
        **hidden,
    }

    print("[WiFi Auth] Authenticating …")

    # Step 4: POST credentials — allow_redirects=True so we follow the post-auth redirect
    try:
        resp = post(action or login_url, payload)
    except requests.RequestException as e:
        print(f"[WiFi Auth] Error: authentication request failed ({e})")
        return 1

    # Step 5: verify success by checking where we ended up
    final_url = resp.url
    if "iac" not in final_url and "/index.php" not in final_url:
        print("[WiFi Auth] Login successful.")
        return 0

    # Check for failure indicators in the response body
    failed_indicators = [
        "authentication failed",
        "invalid password",
        "salah",
        "gagal",
    ]
    if any(ind in resp.text.lower() for ind in failed_indicators):
        print("[WiFi Auth] Error: invalid credentials.")
        return 1

    print("[WiFi Auth] Warning: could not confirm authentication status.")
    return 1


if __name__ == "__main__":
    sys.exit(authenticate())
