# hopeland_bot/config.py
import os
import logging
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_ID", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "hopeland-verify")
HUMAN_CONTACT = os.environ.get("HUMAN_CONTACT", "+974-55555555")
GRAPH_API_BASE = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}"

def init_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def warn_if_missing_secrets():
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        logging.warning("Set WHATSAPP_TOKEN and WHATSAPP_PHONE_ID in your environment or .env")
