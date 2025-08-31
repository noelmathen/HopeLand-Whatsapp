# hopeland_bot/state.py
import time
from typing import Dict

SESSIONS: Dict[str, Dict] = {}  # wa_id -> session dict

def get_session(wa_id: str) -> Dict:
    sess = SESSIONS.setdefault(
        wa_id,
        {"human": False, "state": "NEW", "last_cat": None, "last_seen": time.time()}
    )
    sess["last_seen"] = time.time()
    return sess
