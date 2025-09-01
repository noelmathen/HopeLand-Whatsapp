import os, json, mimetypes, logging, requests
from .config import GRAPH_API_BASE, WHATSAPP_TOKEN, MEDIA_CACHE_PATH

MEDIA_CACHE = {}

def _load_cache():
    global MEDIA_CACHE
    try:
        if os.path.isfile(MEDIA_CACHE_PATH):
            with open(MEDIA_CACHE_PATH, "r", encoding="utf-8") as f:
                MEDIA_CACHE = json.load(f)
    except Exception as e:
        logging.exception("Failed to load media cache: %s", e)
        MEDIA_CACHE = {}

def _save_cache():
    try:
        os.makedirs(os.path.dirname(MEDIA_CACHE_PATH), exist_ok=True)
        with open(MEDIA_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(MEDIA_CACHE, f)
    except Exception as e:
        logging.exception("Failed to save media cache: %s", e)

def init_media_cache():
    _load_cache()

def _upload_media(filepath: str) -> str:
    mime, _ = mimetypes.guess_type(filepath)
    if not mime:
        mime = "image/jpeg"
    url = f"{GRAPH_API_BASE}/media"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    data = {"messaging_product": "whatsapp"}
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Media file not found: {filepath}")
    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f, mime)}
        r = requests.post(url, headers=headers, data=data, files=files, timeout=60)
    if not r.ok:
        logging.error("Media upload failed (%s): %s", filepath, r.text)
        r.raise_for_status()
    media_id = r.json().get("id")
    if not media_id:
        raise RuntimeError(f"No media id returned for {filepath}: {r.text}")
    return media_id

def build_image_payload(img_entry: str) -> dict:
    if not img_entry:
        return {}
    entry = img_entry.strip()
    if entry.lower().startswith("http"):
        return {"link": entry}
    # local file path → id
    try:
        if entry in MEDIA_CACHE:
            return {"id": MEDIA_CACHE[entry]}
        media_id = _upload_media(entry)
        MEDIA_CACHE[entry] = media_id
        _save_cache()
        return {"id": media_id}
    except Exception as e:
        logging.exception("build_image_payload failed for %s: %s", entry, e)
        return {}
