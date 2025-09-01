import logging
from functools import wraps
from typing import Callable, Any
from flask import request
from .config import ADMIN_API_KEY, ALLOWED_ADMIN_IPS

def clip(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: max(0, n - 1)].rstrip() + "…"

def safe(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def _wrap(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            logging.exception("Error in %s: %s", fn.__name__, e)
            return None
    return _wrap

def admin_required(fn):
    @wraps(fn)
    def _wrap(*args, **kwargs):
        # IP allowlist, if provided
        if ALLOWED_ADMIN_IPS:
            try:
                ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
                ip = ip.split(",")[0].strip()
                if ip not in ALLOWED_ADMIN_IPS:
                    return {"ok": False, "error": "forbidden ip"}, 403
            except Exception:
                return {"ok": False, "error": "forbidden"}, 403
        # API key check
        key = request.headers.get("X-Admin-Key") or request.args.get("key")
        if not ADMIN_API_KEY or key != ADMIN_API_KEY:
            return {"ok": False, "error": "unauthorized"}, 401
        return fn(*args, **kwargs)
    return _wrap
