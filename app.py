# app.py
import os
import time
import logging
from typing import Dict, List, Optional

from flask import Flask, request, jsonify
import requests

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

import mimetypes
MEDIA_CACHE = {}  


# ====== Config ======
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_ID", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "hopeland-verify")

if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
    print("WARNING: Set WHATSAPP_TOKEN and WHATSAPP_PHONE_ID in your environment or .env")

# Optional: number customers can call/WhatsApp for a human handoff
HUMAN_CONTACT = os.environ.get("HUMAN_CONTACT", "+974-55555555")  # replace with your real number

# ====== Flask ======
app = Flask(__name__)

# ====== Simple in-memory session/handoff flags (swap with Redis later) ======
SESSIONS: Dict[str, Dict] = {}  # wa_id -> {"human": bool, "state": str, "last_cat": Optional[str], "last_seen": float}

# ====== Data: Listings & images ======
# Put real, publicly-accessible HTTPS image links. WhatsApp Cloud API accepts "link" without pre-upload.
# Tip: host on an S3 bucket/Cloudflare/Imgur/your CDN. Each listing can have 1..N images.
LISTINGS: Dict[str, List[Dict]] = {
    "1bhk": [
        {
            "id": "R101",
            "title": "R101 — 1BHK (GF Main)",
            "desc": "GF main room, 2 windows, big hall, big room (ground floor).",
            "images": [
                "media/IMG-20250831-WA0001.jpg",
                "media/IMG-20250831-WA0002.jpg",
            ]
        },
        {
            "id": "R104",
            "title": "R104 — 1BHK",
            "desc": "Standard 1BHK.",
            "images": ["media/IMG-20250831-WA0001.jpg"]
        },
        {
            "id": "R105",
            "title": "R105 — 1BHK (Back Entrance)",
            "desc": "Back entrance, hall/room, window, bathroom with bathtub.",
            "images": ["media/IMG-20250831-WA0001.jpg"]
        },
        {
            "id": "R107",
            "title": "R107 — 1BHK BIG",
            "desc": "Big hall, kitchen, dressing room, modern bathroom, no partition.",
            "images": ["media/IMG-20250831-WA0001.jpg"]
        },
        {
            "id": "R108",
            "title": "R108 — 1BHK SMALL",
            "desc": "Long hall, big kitchen, dressing room, big room, big bathroom.",
            "images": ["media/IMG-20250831-WA0001.jpg"]
        },
        {
            "id": "R111",
            "title": "R111 — Big Premium 1BHK",
            "desc": "Separate passage, big room with 2 windows, big hall window, kitchen, dressing room.",
            "images": ["media/IMG-20250831-WA0001.jpg"]
        },
    ],
    "studio": [
        {
            "id": "R102",
            "title": "R102 — Big Studio (GF)",
            "desc": "Big room with window, separate kitchen.",
            "images": ["media/IMG-20250831-WA0001.jpg"]
        },
        {
            "id": "R103",
            "title": "R103 — Studio",
            "desc": "Standard studio.",
            "images": ["media/IMG-20250831-WA0001.jpg"]
        },
        {
            "id": "R106",
            "title": "R106 — Studio",
            "desc": "Separate entrance, closed kitchen, bathroom with bathtub.",
            "images": ["media/IMG-20250831-WA0001.jpg"]
        },
        {
            "id": "R109",
            "title": "R109 — Big Studio",
            "desc": "Big room, closed kitchen, bathroom with window.",
            "images": ["media/IMG-20250831-WA0001.jpg"]
        },
        {
            "id": "R110",
            "title": "R110 — Studio",
            "desc": "Big room, spacious kitchen, separate passage, window inside room.",
            "images": ["media/IMG-20250831-WA0001.jpg"]
        },
        {
            "id": "R112",
            "title": "R112 — Small Studio",
            "desc": "Outside room.",
            "images": ["media/IMG-20250831-WA0001.jpg"]
        },
        {
            "id": "R113",
            "title": "R113 — Small Studio",
            "desc": "Outside room.",
            "images": ["media/IMG-20250831-WA0001.jpg"]
        },
    ]
}

def upload_media(filepath: str) -> str:
    """Upload a local file to WhatsApp and return media_id. Caches by path."""
    if filepath in MEDIA_CACHE:
        return MEDIA_CACHE[filepath]

    # Guess MIME type
    mime, _ = mimetypes.guess_type(filepath)
    if not mime:
        mime = "image/jpeg"

    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    data = {"messaging_product": "whatsapp"}

    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f, mime)}
        r = requests.post(url, headers=headers, data=data, files=files, timeout=60)
    try:
        r.raise_for_status()
    except Exception as e:
        logging.error("Media upload failed for %s: %s | %s", filepath, e, r.text)
        raise

    media_id = r.json().get("id")
    if not media_id:
        raise RuntimeError(f"No media id returned for {filepath}: {r.text}")
    MEDIA_CACHE[filepath] = media_id
    return media_id

def build_image_payload(img_entry: str) -> dict:
    """Accepts either https URL or local file path; returns {'link':...} or {'id':...}."""
    if img_entry.lower().startswith("http"):
        return {"link": img_entry}
    # treat as local file
    media_id = upload_media(img_entry)
    return {"id": media_id}


# Helper to look up a listing by ID across categories
def find_listing(listing_id: str) -> Optional[Dict]:
    for cat in LISTINGS.values():
        for item in cat:
            if item["id"] == listing_id:
                return item
    return None

# ====== WhatsApp send helpers ======
def wa_post(payload: dict):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    try:
        r.raise_for_status()
    except Exception as e:
        logging.error("WhatsApp send error: %s | Payload: %s | Resp: %s", e, payload, r.text)
        raise
    return r.json()

def send_text(to: str, body: str):
    wa_post({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body}
    })

def send_category_menu(to: str):
    intro = (
        "Welcome to *HOPELAND Real Estates*.\n"
        "Muither, Qatar — quality units in a well-kept villa.\n\n"
        "What are you looking for today?"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": intro},
            "action": {
                "button": "Browse",
                "sections": [{
                    "title": "Select a category",
                    "rows": [
                        {"id": "cat_1bhk", "title": "1BHK", "description": "Spacious 1-bedroom units"},
                        {"id": "cat_studio", "title": "Studio", "description": "Affordable studio options"}
                    ]
                }]
            }
        }
    }
    wa_post(payload)
    
def clip(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: max(0, n - 1)].rstrip() + "…"


def send_listings_menu(to: str, category_key: str):
    assert category_key in LISTINGS
    cat_title = "1BHK" if category_key == "1bhk" else "Studio"
    listings = LISTINGS[category_key]

    rows = []
    for item in listings:
        # ultra-short, standards-compliant title; all detail goes to description
        short_title = clip(f"{item['id']} {cat_title}", 24)   # <= 24
        short_desc  = clip(f"{item['title']} — {item['desc']}", 72)  # <= 72
        rows.append({
            "id": f"listing_{item['id']}",
            "title": short_title,
            "description": short_desc
        })

    body_text = clip(f"We have the following listings for *{cat_title}*. "
                     "Select an option to see photos.", 1024)
    section_title = clip(f"{cat_title} Muither Villa", 24)  # belt-and-suspenders
    button_label  = clip("View options", 20)

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_label,
                "sections": [{
                    "title": section_title,
                    "rows": rows
                }]
            }
        }
    }
    wa_post(payload)



def build_contact_message(listing: Dict) -> str:
    # Professional, not cheesy. Mentions unit code and nudges to call.
    return (
        f"Thanks for your interest in *{listing['title']}* (Unit *{listing['id']}*, Muither).\n"
        f"For the quickest details and booking, please *call* us on *{HUMAN_CONTACT}*.\n"
        f"Kindly mention *Unit {listing['id']}* so we can assist immediately."
    )



def send_listing_details(to: str, listing: Dict):
    # 1) Always send the contact message first
    send_text(to, (
        f"Thanks for your interest in *{listing['title']}* (Unit *{listing['id']}*, Muither).\n"
        f"For the quickest details and booking, please *call* us on *{HUMAN_CONTACT}*.\n"
        f"Kindly mention *Unit {listing['id']}* so we can assist immediately."
    ))

    # 2) Photos (if any)
    imgs = listing.get("images") or []
    if imgs:
        send_text(to, f"Here are a few photos of *Unit {listing['id']}*.")
        for idx, img in enumerate(imgs, start=1):
            try:
                image_field = build_image_payload(img)   # << magic here
                wa_post({
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "image",
                    "image": {**image_field, "caption": f"Unit {listing['id']} — photo {idx}"}
                })
                time.sleep(0.2)
            except Exception:
                logging.exception("Failed to send image for %s (%s)", listing["id"], img)
    else:
        # send_text(to, f"Photos for *Unit {listing['id']}* will be shared on request.")
        pass

    # 3) Nudge to continue
    send_text(to, "To keep browsing, type *menu* to return to categories.")



# ====== Webhook endpoints ======
@app.get("/whatsapp/webhook")
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "forbidden", 403

@app.post("/whatsapp/webhook")
def inbound():
    data = request.get_json(force=True, silent=True) or {}
    # Basic logging so you can debug quickly
    logging.info("Inbound: %s", data)

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            for msg in messages:
                wa_id = msg.get("from")
                if not wa_id:
                    continue

                sess = SESSIONS.setdefault(wa_id, {"human": False, "state": "NEW", "last_cat": None, "last_seen": time.time()})
                sess["last_seen"] = time.time()

                # Respect human-mode: if you toggled to a human desk, bot stays silent
                if sess.get("human"):
                    continue

                mtype = msg.get("type")
                text_lower = ""
                list_reply_id = None
                button_reply_id = None

                if mtype == "text":
                    text_lower = msg["text"]["body"].strip().lower()
                elif mtype == "interactive":
                    inter = msg.get("interactive", {})
                    if "list_reply" in inter:
                        list_reply_id = inter["list_reply"]["id"]
                    if "button_reply" in inter:
                        button_reply_id = inter["button_reply"]["id"]

                # Commands typed by users
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
                    send_text(wa_id, "Thanks. A leasing specialist will join shortly. If you need immediate help, call us at " + HUMAN_CONTACT)
                    continue
                if text_lower and sess["state"] == "NEW":
                    # unknown text; start menu
                    send_category_menu(wa_id)
                    sess["state"] = "MENU"
                    continue

                # Interactive replies (preferred)
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
                            send_listing_details(wa_id, listing)
                            # stay in same category
                            if sess.get("last_cat"):
                                send_listings_menu(wa_id, sess["last_cat"])
                        else:
                            send_text(wa_id, "Sorry, that listing is unavailable. Please choose another option.")
                        continue

                # Fallback: if nothing matched and we're mid-flow, remind menu
                if sess.get("last_cat"):
                    send_listings_menu(wa_id, sess["last_cat"])
                else:
                    send_category_menu(wa_id)

    return jsonify(status="ok")


@app.get("/health")
def health():
    return "ok", 200

    
if __name__ == "__main__":
    # Run with: python app.py
    port = int(os.environ.get("PORT", "3000"))
    app.run(host="0.0.0.0", port=port)
