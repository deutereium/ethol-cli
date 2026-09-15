import requests
from .config import TG_BOT_TOKEN, TG_CHAT_ID

API_URL = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"


def send_message(text: str) -> None:
    """Send a plain‑text message to the configured Telegram chat.
    Raises an exception on failure.
    """
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    resp = requests.post(API_URL, json=payload, timeout=10)
    resp.raise_for_status()
    # Telegram returns a JSON with ok=True on success – we could check but raise_for_status is enough
    return None
