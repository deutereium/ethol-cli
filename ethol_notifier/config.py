import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file)
BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    raise FileNotFoundError(f"Missing .env file at {ENV_PATH}")

# Export needed variables (will raise KeyError if missing)
NETID = os.getenv("NETID")
PASSWORD = os.getenv("PASSWORD")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

if not all([NETID, PASSWORD, TG_BOT_TOKEN, TG_CHAT_ID]):
    missing = [k for k, v in {"NETID": NETID, "PASSWORD": PASSWORD, "TG_BOT_TOKEN": TG_BOT_TOKEN, "TG_CHAT_ID": TG_CHAT_ID}.items() if not v]
    raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")
