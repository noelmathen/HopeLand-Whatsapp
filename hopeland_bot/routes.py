import logging
from flask import Blueprint, request, jsonify
from .config import VERIFY_TOKEN
from .state import get_session
from .data import find_listing
from .whatsapp import send_category_menu, send_listings_menu, send_listing_details, send_text, send_selection_echo
from .sheets import log_enquiry
from .utils import admin_required

bp = Blueprint("routes", __name__)

@bp.get("/whatsapp/webhook")
def verify():
    try:
        mode = request.args.get("hub.mode"); token = request.args.get("hub.verify_token"); challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN: return challenge, 200
        return "forbidden", 403
    except Exception as e:
        logging.exception("Verification error: %s", e); return "forbidden", 403

@bp.post("/whatsapp/webhook")
def inbound():
    try:
        data = request.get_json(force=True, silent=True) or {}
        logging.info("Inbound: %s", data)
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                contact_name = ""
                try:
                    contacts = value.get("contacts", [])
                    if contacts and isinstance(contacts, list):
                        contact_name = contacts[0].get("profile", {}).get("name", "") or ""
                except Exception: pass

                for msg in messages:
                    try:
                        wa_id = msg.get("from")
                        if not wa_id: continue
                        sess = get_session(wa_id)
                        if sess.get("human"): continue

                        mtype = msg.get("type"); text_lower = ""; list_reply_id = None
                        if mtype == "text":
                            text_lower = (msg.get("text", {}).get("body") or "").strip().lower()
                        elif mtype == "interactive":
                            inter = msg.get("interactive", {})
                            if "list_reply" in inter: list_reply_id = inter["list_reply"]["id"]

                        if text_lower in {"hi","hello","hey","start","menu"}:
                            send_category_menu(wa_id); sess["state"]="MENU"; continue
                        if text_lower in {"1bhk","1 bhk"}:
                            send_listings_menu(wa_id,"1bhk"); sess["state"]="LIST_1BHK"; sess["last_cat"]="1bhk"; continue
                        if text_lower in {"studio","studios"}:
                            send_listings_menu(wa_id,"studio"); sess["state"]="LIST_STUDIO"; sess["last_cat"]="studio"; continue
                        if text_lower == "agent":
                            sess["human"]=True; send_text(wa_id,"Thanks. A leasing specialist will join shortly."); continue
                        if text_lower and sess["state"]=="NEW":
                            send_category_menu(wa_id); sess["state"]="MENU"; continue

                        if list_reply_id:
                            if list_reply_id == "cat_1bhk":
                                send_listings_menu(wa_id,"1bhk"); sess["state"]="LIST_1BHK"; sess["last_cat"]="1bhk"; continue
                            if list_reply_id == "cat_studio":
                                send_listings_menu(wa_id,"studio"); sess["state"]="LIST_STUDIO"; sess["last_cat"]="studio"; continue
                            if list_reply_id.startswith("listing_"):
                                listing_id = list_reply_id.replace("listing_","",1)
                                listing = find_listing(listing_id)
                                if listing:
                                    # 1) Untrimmed echo
                                    send_selection_echo(wa_id, listing)
                                    # 2) Log
                                    cat = sess.get("last_cat") or ("1bhk" if "1BHK" in (listing.get("title","").upper()) else "studio")
                                    try:
                                        log_enquiry(wa_number=wa_id, wa_name=contact_name, category=cat.upper(),
                                                    unit_id=listing.get("id",""), title=listing.get("title",""),
                                                    desc=listing.get("desc",""))
                                    except Exception: logging.exception("log_enquiry failed")
                                    # 3) Contact + photos
                                    send_listing_details(wa_id, listing)
                                    # 4) Show list again
                                    if sess.get("last_cat"): send_listings_menu(wa_id, sess["last_cat"])
                                else:
                                    send_text(wa_id,"Sorry, that listing is unavailable. Please choose another option.")
                                continue

                        if sess.get("last_cat"): send_listings_menu(wa_id, sess["last_cat"])
                        else: send_category_menu(wa_id)

                    except Exception as inner:
                        logging.exception("Error handling single message: %s", inner)
                        continue

        return jsonify(status="ok"), 200
    except Exception as e:
        logging.exception("Inbound webhook error: %s", e)
        return jsonify(status="error"), 200

# Admin endpoints — now protected
@bp.get("/admin/sheets/init")
@admin_required
def admin_sheets_init():
    from .sheets import _ensure_sheet, spreadsheet_url
    try:
        _, _, ws = _ensure_sheet(); url = spreadsheet_url()
        return {"ok": bool(ws), "url": url}, 200
    except Exception as e:
        logging.exception("Admin sheets init failed: %s", e)
        return {"ok": False, "error": str(e)}, 200

@bp.post("/admin/digest/send-now")
@admin_required
def admin_digest_now():
    try:
        from .digest import send_digest_once
        send_digest_once()
        return {"ok": True}, 200
    except Exception as e:
        logging.exception("Admin digest send failed: %s", e)
        return {"ok": False, "error": str(e)}, 200



# swallow favicon requests without cluttering logs
@bp.get("/favicon.ico")
def favicon():
    return ("", 204)
