import time
import logging
import requests
from .config import TG_BOT_TOKEN, TG_CHAT_ID

API_URL = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"

logger = logging.getLogger(__name__)


def send_message(text: str) -> None:
    """Send a plain‑text message to the configured Telegram chat.
    Handles rate‑limit (429) errors by respecting the ``retry_after``
    value returned by the Telegram API, and retries transient network /
    HTTP errors with exponential backoff. Raises if all attempts fail.
    """
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(API_URL, json=payload, timeout=10)
        except requests.RequestException as e:
            logger.warning(f"Telegram request failed (attempt {attempt}/{max_retries}): {e}")
            time.sleep(2 ** attempt)
            continue
        if resp.status_code == 429:
            # Telegram indicates how many seconds to wait before retrying.
            try:
                retry_after = int(resp.json().get("parameters", {}).get("retry_after", 1))
            except Exception:
                retry_after = 1
            # Simple back‑off: wait the suggested time plus a small jitter.
            time.sleep(retry_after + (attempt - 1) * 0.5)
            continue
        if resp.status_code >= 500:
            # Transient server error – back off and retry.
            logger.warning(
                f"Telegram returned {resp.status_code} (attempt {attempt}/{max_retries})."
            )
            time.sleep(2 ** attempt)
            continue
        # Raise for any other HTTP errors.
        resp.raise_for_status()
        # Successful send; exit loop.
        return None
    # If we exhaust retries, raise an exception.
    raise RuntimeError(f"Failed to send Telegram message after {max_retries} attempts.")

