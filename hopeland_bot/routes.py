# hopeland_bot/routes.py  (only the inner handler changes shown)
import logging
from flask import Blueprint, request, jsonify
from .config import VERIFY_TOKEN
from .state import get_session
from .data import find_listing
from .whatsapp import send_category_menu, send_listings_menu, send_listing_details, send_text
from .sheets import log_enquiry
import os

bp = Blueprint("routes", __name__)

@bp.post("/whatsapp/webhook")
def inbound():
    try:
        data = request.get_json(force=True, silent=True) or {}
        logging.info("Inbound: %s", data)

        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                # best-effort name
                contact_name = ""
                try:
                    contacts = value.get("contacts", [])
                    if contacts and isinstance(contacts, list):
                        contact_name = contacts[0].get("profile", {}).get("name", "") or ""
                except Exception:
                    pass

                for msg in messages:
                    try:
                        wa_id = msg.get("from")
                        if not wa_id:
                            continue

                        sess = get_session(wa_id)
                        if sess.get("human"):
                            continue

                        mtype = msg.get("type")
                        text_lower = ""
                        list_reply_id = None

                        if mtype == "text":
                            text_lower = (msg.get("text", {}).get("body") or "").strip().lower()
                        elif mtype == "interactive":
                            inter = msg.get("interactive", {})
                            if "list_reply" in inter:
                                list_reply_id = inter["list_reply"]["id"]

                        # commands...
                        if text_lower in {"hi", "hello", "hey", "start", "menu"}:
                            send_category_menu(wa_id)
                            sess["state"] = "MENU"
                            continue
                        if text_lower in {"1bhk", "1 bhk"}:
                            send_listings_menu(wa_id, "1bhk")
                            sess["state"] = "LIST_1BHK"; sess["last_cat"] = "1bhk"
                            continue
                        if text_lower in {"studio", "studios"}:
                            send_listings_menu(wa_id, "studio")
                            sess["state"] = "LIST_STUDIO"; sess["last_cat"] = "studio"
                            continue
                        if text_lower == "agent":
                            sess["human"] = True
                            send_text(wa_id, "Thanks. A leasing specialist will join shortly.")
                            continue
                        if text_lower and sess["state"] == "NEW":
                            send_category_menu(wa_id)
                            sess["state"] = "MENU"
                            continue

                        # Interactive replies
                        if list_reply_id:
                            if list_reply_id == "cat_1bhk":
                                send_listings_menu(wa_id, "1bhk")
                                sess["state"] = "LIST_1BHK"; sess["last_cat"] = "1bhk"
                                continue
                            if list_reply_id == "cat_studio":
                                send_listings_menu(wa_id, "studio")
                                sess["state"] = "LIST_STUDIO"; sess["last_cat"] = "studio"
                                continue
                            if list_reply_id.startswith("listing_"):
                                listing_id = list_reply_id.replace("listing_", "", 1)
                                listing = find_listing(listing_id)
                                if listing:
                                    # Log to Google Sheet (best effort)
                                    cat = sess.get("last_cat") or ("1bhk" if "1BHK" in listing.get("title","").upper() else "studio")
                                    try:
                                        log_enquiry(
                                            wa_number=wa_id,
                                            wa_name=contact_name,
                                            category=cat.upper(),
                                            unit_id=listing.get("id",""),
                                            title=listing.get("title",""),
                                            desc=listing.get("desc","")
                                        )
                                    except Exception:
                                        logging.exception("log_enquiry failed")
                                    # Send the contact msg + photos
                                    send_listing_details(wa_id, listing)
                                    # Return to list menu
                                    if sess.get("last_cat"):
                                        send_listings_menu(wa_id, sess["last_cat"])
                                else:
                                    send_text(wa_id, "Sorry, that listing is unavailable. Please choose another option.")
                                continue

                        # Fallback
                        if sess.get("last_cat"):
                            send_listings_menu(wa_id, sess["last_cat"])
                        else:
                            send_category_menu(wa_id)

                    except Exception as inner:
                        logging.exception("Error handling single message: %s", inner)
                        continue

        return jsonify(status="ok"), 200

    except Exception as e:
        logging.exception("Inbound webhook error: %s", e)
        return jsonify(status="error"), 200


# --- Admin debug endpoints (safe to keep; they do nothing destructive) ---
@bp.get("/admin/sheets/init")
def admin_sheets_init():
    from .sheets import _ensure_sheet, spreadsheet_url
    try:
        gc, sh, ws = _ensure_sheet()
        url = spreadsheet_url()
        ok = bool(ws)
        # Gather some breadcrumbs for you
        info = {
            "ok": ok,
            "url": url,
            "has_gc": bool(gc),
            "has_sh": bool(sh),
            "env_json": bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")),
            "env_sheet_id": bool(os.environ.get("SHEET_ID", "").strip()),
            "env_title": os.environ.get("SHEET_TITLE", ""),
        }
        return info, 200
    except Exception as e:
        import logging, traceback
        logging.exception("Admin sheets init failed: %s", e)
        return {"ok": False, "error": str(e)}, 200


@bp.post("/admin/digest/send-now")
def admin_digest_now():
    from .scheduler import send_6h_digest
    try:
        send_6h_digest()
        return {"ok": True}, 200
    except Exception as e:
        import logging
        logging.exception("Admin digest send failed: %s", e)
        return {"ok": False, "error": str(e)}, 200


# swallow favicon requests without cluttering logs
@bp.get("/favicon.ico")
def favicon():
    return ("", 204)
