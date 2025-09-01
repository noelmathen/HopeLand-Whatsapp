import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN    = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID   = os.environ.get("WHATSAPP_PHONE_ID", "")
VERIFY_TOKEN      = os.environ.get("VERIFY_TOKEN", "hopeland-verify")
HUMAN_CONTACT     = os.environ.get("HUMAN_CONTACT", "+974-55555555")
GRAPH_API_BASE    = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}"

# Admin protection
ADMIN_API_KEY     = os.environ.get("ADMIN_API_KEY", "")
ALLOWED_ADMIN_IPS = [ip.strip() for ip in os.environ.get("ALLOWED_ADMIN_IPS", "").split(",") if ip.strip()]

# Persistence
DATA_DIR          = os.environ.get("DATA_DIR", "/data")
LOG_DIR           = os.path.join(DATA_DIR, "logs")
MEDIA_CACHE_PATH  = os.path.join(DATA_DIR, "media_cache.json")
SHEET_STATE_PATH  = os.path.join(DATA_DIR, "sheet_state.json")

def init_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # stdout handler
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)

    # rotating file
    fh = RotatingFileHandler(os.path.join(LOG_DIR, "app.log"), maxBytes=10_000_000, backupCount=5)
    fh.setFormatter(fmt)
    root.addHandler(fh)

def warn_if_missing_secrets():
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        logging.warning("Missing WHATSAPP_TOKEN or WHATSAPP_PHONE_ID")
