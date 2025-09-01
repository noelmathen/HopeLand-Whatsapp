import time, logging, requests
from typing import Dict, List
from .config import GRAPH_API_BASE, WHATSAPP_TOKEN, HUMAN_CONTACT
from .utils import clip, safe
from .data import LISTINGS
from .media import build_image_payload

def _wa_post(payload: dict) -> bool:
    try:
        url = f"{GRAPH_API_BASE}/messages"
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if not r.ok:
            logging.error("WA POST failed: %s | Payload=%s", r.text, payload); return False
        return True
    except Exception as e:
        logging.exception("WA POST error: %s | Payload=%s", e, payload); return False

@safe
def send_text(to: str, body: str):
    _wa_post({"messaging_product":"whatsapp","to":to,"type":"text","text":{"body":body}})

@safe
def send_category_menu(to: str):
    intro = ("Welcome to *HOPELAND Real Estates*.\n"
             "Muither, Qatar — quality units in a well-kept villa.\n\n"
             "What are you looking for today?")
    payload = {
        "messaging_product":"whatsapp","to":to,"type":"interactive",
        "interactive":{"type":"list","body":{"text":intro},
            "action":{"button":"Browse","sections":[{
                "title":"Select a category",
                "rows":[
                    {"id":"cat_1bhk","title":"1BHK","description":"Spacious 1-bedroom units"},
                    {"id":"cat_studio","title":"Studio","description":"Affordable studio options"}
                ]}]}}}
    ok = _wa_post(payload)
    if not ok: send_text(to, "Categories:\n• 1BHK\n• Studio\nType *1BHK* or *Studio* to continue.")

def _send_listings_menu_text_fallback(to: str, category_key: str):
    cat_title = "1BHK" if category_key == "1bhk" else "Studio"
    items: List[Dict] = LISTINGS[category_key]
    lines = [f"{cat_title} listings:"]
    for it in items:
        lines.append(f"• {it['id']} — {clip(it['title'], 32)}")
    lines.append("Reply with the code (e.g., R101) to receive photos.")
    send_text(to, "\n".join(lines))

@safe
def send_listings_menu(to: str, category_key: str):
    assert category_key in LISTINGS
    cat_title = "1BHK" if category_key == "1bhk" else "Studio"
    rows = []
    for item in LISTINGS[category_key]:
        rows.append({
            "id": f"listing_{item['id']}",
            "title": clip(f"{item['id']} {cat_title}", 24),
            "description": clip(f"{item['title']} — {item['desc']}", 72)
        })
    payload = {
        "messaging_product":"whatsapp","to":to,"type":"interactive",
        "interactive":{"type":"list","body":{"text":f"We have the following listings for *{cat_title}*. Select an option to see photos."},
            "action":{"button":"View options","sections":[{
                "title": clip(f"{cat_title} Muither Villa", 24), "rows": rows }]}}}
    ok = _wa_post(payload)
    if not ok: _send_listings_menu_text_fallback(to, category_key)

def build_contact_message(listing: Dict) -> str:
    return (f"Thanks for your interest in *{listing['title']}* (Unit *{listing['id']}*, Muither).\n"
            f"For the quickest details and booking, please *call* us on *{HUMAN_CONTACT}*.\n"
            f"Kindly mention *Unit {listing['id']}* so we can assist immediately.")

@safe
def send_selection_echo(to: str, listing: Dict):
    title = listing.get("title",""); desc = listing.get("desc","")
    body = f"You selected:\n*{title}*\n\n{desc}".strip()
    send_text(to, body)

@safe
def send_listing_details(to: str, listing: Dict):
    send_text(to, build_contact_message(listing))
    imgs = listing.get("images") or []
    if imgs:
        send_text(to, f"Here are a few photos of *Unit {listing['id']}*.")
        for idx, img in enumerate(imgs, start=1):
            image_field = build_image_payload(img)
            if not image_field: continue
            _wa_post({"messaging_product":"whatsapp","to":to,"type":"image",
                      "image":{**image_field,"caption":f"Unit {listing['id']} — photo {idx}"}})
            time.sleep(0.2)
    send_text(to, "To keep browsing, type *menu* to return to categories.")
