import os, json, logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional
import gspread
from google.oauth2.service_account import Credentials
from .config import SHEET_STATE_PATH

SCOPE = ["https://www.googleapis.com/auth/drive","https://www.googleapis.com/auth/spreadsheets"]

import os
SERVICE_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON","")
SHEET_ID     = os.environ.get("SHEET_ID","").strip()
SHEET_TITLE  = os.environ.get("SHEET_TITLE","HOPELAND Muither Leads").strip()
OWNERS_EMAILS= [e.strip() for e in os.environ.get("OWNERS_EMAILS","").split(",") if e.strip()]
LOCAL_TZ_NAME= os.environ.get("LOCAL_TZ","Asia/Qatar")

HEADERS = ["Timestamp UTC","Timestamp Local","WA Number","WA Name","Category","Unit ID","Title","Description","Reviewed"]

def _load_state_id() -> Optional[str]:
    try:
        if os.path.isfile(SHEET_STATE_PATH):
            with open(SHEET_STATE_PATH,"r",encoding="utf-8") as f:
                return (json.load(f) or {}).get("sheet_id")
    except Exception as e:
        logging.exception("Sheet state load failed: %s", e)
    return None

def _save_state_id(sheet_id: str):
    try:
        os.makedirs(os.path.dirname(SHEET_STATE_PATH), exist_ok=True)
        with open(SHEET_STATE_PATH,"w",encoding="utf-8") as f:
            json.dump({"sheet_id": sheet_id}, f)
    except Exception as e:
        logging.exception("Sheet state save failed: %s", e)

def _client():
    try:
        if not SERVICE_JSON or not os.path.isfile(SERVICE_JSON):
            raise FileNotFoundError("Service account JSON not found")
        creds = Credentials.from_service_account_file(SERVICE_JSON, scopes=SCOPE)
        return gspread.authorize(creds)
    except Exception as e:
        logging.exception("Google client init failed: %s", e)
        return None

def _ensure_sheet():
    gc = _client()
    if not gc: return None, None, None
    sid = SHEET_ID or _load_state_id()
    sh = None
    try:
        if sid:
            sh = gc.open_by_key(sid)
        else:
            sh = gc.create(SHEET_TITLE)
            _save_state_id(sh.id)
            logging.info("Created spreadsheet: https://docs.google.com/spreadsheets/d/%s", sh.id)
    except Exception as e:
        logging.exception("Open/create spreadsheet failed: %s", e)
        return gc, None, None
    try:
        ws = sh.sheet1
        if ws.row_values(1) != HEADERS:
            ws.clear(); ws.insert_row(HEADERS, 1)
    except Exception as e:
        logging.exception("Worksheet access failed: %s", e)
        return gc, sh, None
    if OWNERS_EMAILS:
        try:
            for email in OWNERS_EMAILS:
                try: sh.share(email, perm_type="user", role="writer", notify=True)
                except Exception: pass
        except Exception as e:
            logging.exception("Sharing failed: %s", e)
    return gc, sh, ws

def spreadsheet_url() -> Optional[str]:
    sid = SHEET_ID or _load_state_id()
    return f"https://docs.google.com/spreadsheets/d/{sid}" if sid else None

def log_enquiry(wa_number, wa_name, category, unit_id, title, desc) -> bool:
    gc, sh, ws = _ensure_sheet()
    if not ws: return False
    try:
        now_utc = datetime.now(timezone.utc)
        tz = ZoneInfo(LOCAL_TZ_NAME)
        now_local = now_utc.astimezone(tz)
        row = [
            now_utc.isoformat(timespec="seconds"),
            now_local.strftime("%Y-%m-%d %H:%M:%S"),
            wa_number, wa_name or "", category, unit_id, title, desc, "No"
        ]
        ws.insert_rows([row], row=2)
        return True
    except Exception as e:
        logging.exception("Insert to sheet failed: %s", e)
        return False

def get_rows_since(hours: int = 6):
    _, _, ws = _ensure_sheet()
    if not ws: return []
    try:
        vals = ws.get_all_values()
        if not vals or len(vals) < 2: return []
        hdr = vals[0]
        from datetime import datetime, timezone
        cutoff = datetime.now(timezone.utc).timestamp() - hours*3600
        rows = []
        for r in vals[1:]:
            rec = dict(zip(hdr, r))
            ts = rec.get("Timestamp UTC","")
            try:
                dt = datetime.fromisoformat(ts.replace("Z","+00:00"))
                if dt.timestamp() >= cutoff: rows.append(rec)
            except Exception:
                rows.append(rec)
        return rows
    except Exception as e:
        logging.exception("Read sheet failed: %s", e)
        return []
