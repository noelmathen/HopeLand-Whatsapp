# hopeland_bot/data.py
from typing import Dict, List

# Your listings (same content you shared; mix of with/without photos is fine)
LISTINGS: Dict[str, List[dict]] = {
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

def find_listing(listing_id: str):
    for cat in LISTINGS.values():
        for item in cat:
            if item.get("id") == listing_id:
                return item
    return None
