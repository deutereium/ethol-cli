import time
from datetime import datetime
import logging

from .auth import login
from .scraper import fetch_notifications
from .state import filter_new
from .telegram import send_message

# Set up simple console logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 5 * 60  # 5 minutes
START_HOUR = 5   # 05:00
END_HOUR = 21   # up to but not including 21:00


def _within_active_hours(now: datetime) -> bool:
    return START_HOUR <= now.hour < END_HOUR


def run() -> None:
    logger.info("Notifier started. Scheduler running every 15 minutes.")

    while True:
        now = datetime.now()
        if _within_active_hours(now):
            logger.info("Checking for new notifications...")
            try:
                sess = login()
                notifications = fetch_notifications(sess)
                logger.info(f"Fetched {len(notifications)} total notifications from API.")

                new = filter_new(notifications)
                logger.info(f"Found {len(new)} new unread notification(s).")

                for n in new:
                    msg = (
                        "🔔 <b>NEW NOTIFICATION</b>\n\n"
                        f"📅 <i>{n.get('time', 'N/A')}</i>\n"
                        f"📝 {n.get('text', 'No content')}"
                    )
                    send_message(msg)
                    logger.info(f"Sent notification to Telegram: {n.get('text', '')[:30]}...")
            except Exception as e:
                logger.error(f"Error during check: {e}")
        else:
            logger.info("Outside active hours (05:00-21:00). Sleeping.")

        time.sleep(CHECK_INTERVAL_SECONDS)
