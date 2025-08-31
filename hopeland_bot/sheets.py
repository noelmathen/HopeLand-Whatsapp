# hopeland_bot/sheets.py
import os
import json
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional
import re

import gspread
from google.oauth2.service_account import Credentials

from .config import (
    HUMAN_CONTACT,
)
from .utils import safe

SCOPE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

# ENV
SERVICE_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
SHEET_ID = os.environ.get("SHEET_ID", "").strip()
SHEET_TITLE = os.environ.get("SHEET_TITLE", "HOPELAND Muither Leads").strip()
OWNERS_EMAILS = [e.strip() for e in os.environ.get("OWNERS_EMAILS", "").split(",") if e.strip()]
LOCAL_TZ_NAME = os.environ.get("LOCAL_TZ", "Asia/Qatar")

HEADERS = [
    "Timestamp UTC",
    "Timestamp Local",
    "WA Number",
    "WA Name",
    "Category",
    "Unit ID",
    "Title",
    "Description",
    "Reviewed"  # default "No"
]

STATE_FILE = "sheet_state.json"  # stores created sheet_id if env is empty

def _load_state_id() -> Optional[str]:
    try:
        if os.path.isfile(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("sheet_id")
    except Exception as e:
        logging.exception("Failed to load state file: %s", e)
    return None

def _save_state_id(sheet_id: str):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"sheet_id": sheet_id}, f)
    except Exception as e:
        logging.exception("Failed to save state file: %s", e)

def _client():
    try:
        if not SERVICE_JSON or not os.path.isfile(SERVICE_JSON):
            raise FileNotFoundError("Service account JSON not found or path not set.")
        creds = Credentials.from_service_account_file(SERVICE_JSON, scopes=SCOPE)
        return gspread.authorize(creds)
    except Exception as e:
        logging.exception("Google client init failed: %s", e)
        return None

def _ensure_sheet():
    """Return (gc, sh, ws) or (None, None, None)"""
    gc = _client()
    if not gc:
        return None, None, None

    raw_id = SHEET_ID or _load_state_id()
    sheet_id = _extract_sheet_id(raw_id) if raw_id else ""
    sh = None
    
    try:
        if sheet_id:
            sh = gc.open_by_key(sheet_id)
        else:
            # Create new
            sh = gc.create(SHEET_TITLE)
            sheet_id = sh.id
            _save_state_id(sheet_id)
            logging.info("Created spreadsheet: %s", f"https://docs.google.com/spreadsheets/d/{sheet_id}")
    except Exception as e:
        logging.exception("Failed to open/create spreadsheet: %s", e)
        return gc, None, None

    try:
        ws = sh.sheet1
        # Ensure headers exist
        first_row = ws.row_values(1)
        if first_row != HEADERS:
            ws.clear()
            ws.insert_row(HEADERS, 1)
    except Exception as e:
        logging.exception("Worksheet access failed: %s", e)
        return gc, sh, None

    # Share with owners if provided
    if OWNERS_EMAILS:
        try:
            for email in OWNERS_EMAILS:
                try:
                    sh.share(email, perm_type="user", role="writer", notify=True)
                except Exception:
                    # could already be shared; ignore
                    logging.debug("Share attempt for %s skipped or failed", email)
        except Exception as e:
            logging.exception("Sharing failed: %s", e)

    return gc, sh, ws


def spreadsheet_url() -> Optional[str]:
    sid = SHEET_ID or _load_state_id()
    if not sid:
        return None
    return f"https://docs.google.com/spreadsheets/d/{sid}"

@safe
def log_enquiry(
    wa_number: str,
    wa_name: str,
    category: str,
    unit_id: str,
    title: str,
    desc: str
) -> bool:
    """Insert newest-first (row 2). Default Reviewed=No."""
    gc, sh, ws = _ensure_sheet()
    if not ws:
        return False

    now_utc = datetime.now(timezone.utc)
    tz = ZoneInfo(LOCAL_TZ_NAME)
    now_local = now_utc.astimezone(tz)

    row = [
        now_utc.isoformat(timespec="seconds"),
        now_local.strftime("%Y-%m-%d %H:%M:%S"),
        wa_number,
        wa_name or "",
        category,
        unit_id,
        title,
        desc,
        "No"
    ]
    try:
        ws.insert_rows([row], row=2)  # insert after header, newest first
        return True
    except Exception as e:
        logging.exception("Failed to insert row: %s", e)
        return False

@safe
def get_rows_since(hours: int = 6) -> List[Dict[str, Any]]:
    """Read rows newer than now-`hours` based on UTC timestamp column 1."""
    _, _, ws = _ensure_sheet()
    if not ws:
        return []

    try:
        all_values = ws.get_all_values()
    except Exception as e:
        logging.exception("Failed to read sheet: %s", e)
        return []

    if not all_values or len(all_values) < 2:
        return []

    rows = []
    hdr = all_values[0]
    for r in all_values[1:]:
        try:
            rec = dict(zip(hdr, r))
            rows.append(rec)
        except Exception:
            continue

    # Filter by time
    try:
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        fresh = []
        for rec in rows:
            ts = rec.get("Timestamp UTC", "")
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.timestamp() >= cutoff:
                fresh.append(rec)
        return fresh
    except Exception as e:
        logging.exception("Timestamp filter failed: %s", e)
        return rows  # if parsing fails, better to send something than nothing


def _extract_sheet_id(maybe_url: str) -> str:
    if not maybe_url:
        return ""
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", maybe_url)
    return m.group(1) if m else maybe_url.strip()