import requests
from bs4 import BeautifulSoup
from .config import NETID, PASSWORD

CAS_LOGIN_URL = "https://login.pens.ac.id/cas/login?service=https%3A%2F%2Fethol.pens.ac.id%2Fapi%2Fauth%2Fcas-callback"
CAS_CALLBACK_URL = "https://ethol.pens.ac.id/api/auth/cas-callback"


def _extract_hidden_fields(html: str) -> dict:
    """Parse the login page and collect all hidden <input> fields.
    These typically include `lt`, `execution`, `_eventId`, etc.
    """
    soup = BeautifulSoup(html, "html.parser")
    hidden = {}
    for inp in soup.find_all("input", type="hidden"):
        name = inp.get("name")
        value = inp.get("value", "")
        if name:
            hidden[name] = value
    return hidden


def login() -> requests.Session:
    """Perform the CAS login flow and return an authenticated Session.
    The Session will contain the Et‑Hol authentication cookie after the
    final redirect to the CAS callback endpoint.
    """
    sess = requests.Session()
    # Step 1: GET the login page to obtain hidden fields
    resp = sess.get(CAS_LOGIN_URL, timeout=30)
    resp.raise_for_status()
    hidden = _extract_hidden_fields(resp.text)

    # Step 2: POST credentials + hidden fields
    payload = {
        "username": NETID,
        "password": PASSWORD,
        **hidden,
    }
    post_resp = sess.post(CAS_LOGIN_URL, data=payload, timeout=30, allow_redirects=True)
    post_resp.raise_for_status()

    # The CAS server should redirect to the callback URL which sets the Et‑Hol cookie
    # Follow any remaining redirects manually to ensure the callback is hit
    if CAS_CALLBACK_URL not in post_resp.url:
        # Force a GET to the callback URL to obtain the session cookie
        callback_resp = sess.get(CAS_CALLBACK_URL, timeout=30)
        callback_resp.raise_for_status()

    # At this point, sess.cookies should contain the Et‑Hol auth cookie
    return sess
