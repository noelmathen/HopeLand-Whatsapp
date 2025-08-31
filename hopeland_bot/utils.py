# hopeland_bot/utils.py
import logging
from functools import wraps
from typing import Callable, Any

def clip(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: max(0, n - 1)].rstrip() + "…"

def safe(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator: catch/log exceptions; never raise to caller."""
    @wraps(fn)
    def _wrap(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            logging.exception("Error in %s: %s", fn.__name__, e)
            return None
    return _wrap
