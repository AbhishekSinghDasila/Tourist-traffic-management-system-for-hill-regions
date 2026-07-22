"""
Seeds the police_stations table with real police stations
in Uttarakhand and Himachal Pradesh tourist areas.

Usage:
  docker compose -f docker-compose.dev.yml exec complaint-service python -m scripts.seed_police_stations
"""
import sys
sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.models.police_station import PoliceStation

STATIONS = [
    # ── Uttarakhand ───────────────────────────────────────
    {"name": "Nainital Kotwali",        "district": "nainital",   "state": "uttarakhand", "lat": 29.3919, "lng": 79.4542, "phone": "05942-235450"},
    {"name": "Mallital Police Post",    "district": "nainital",   "state": "uttarakhand", "lat": 29.3966, "lng": 79.4605, "phone": "05942-235451"},
    {"name": "Mussoorie Police Station","district": "mussoorie",  "state": "uttarakhand", "lat": 30.4539, "lng": 78.0644, "phone": "0135-2632011"},
    {"name": "Haridwar Kotwali",        "district": "haridwar",   "state": "uttarakhand", "lat": 29.9457, "lng": 78.1642, "phone": "01334-265000"},
    {"name": "Rishikesh Police Station","district": "rishikesh",  "state": "uttarakhand", "lat": 30.0869, "lng": 78.2676, "phone": "0135-2430040"},
    {"name": "Ranikhet Police Station", "district": "ranikhet",   "state": "uttarakhand", "lat": 29.6419, "lng": 79.4311, "phone": "05966-220200"},
    {"name": "Almora Kotwali",          "district": "almora",     "state": "uttarakhand", "lat": 29.5971, "lng": 79.6591, "phone": "05962-230200"},
    {"name": "Kedarnath Police Post",   "district": "kedarnath",  "state": "uttarakhand", "lat": 30.7352, "lng": 79.0669, "phone": "01364-233500"},
    {"name": "Badrinath Police Post",   "district": "badrinath",  "state": "uttarakhand", "lat": 30.7433, "lng": 79.4938, "phone": "01381-222421"},
    # ── Himachal Pradesh ──────────────────────────────────
    {"name": "Shimla Sadar",            "district": "shimla",     "state": "himachal_pradesh", "lat": 31.1048, "lng": 77.1734, "phone": "0177-2620300"},
    {"name": "Manali Police Station",   "district": "manali",     "state": "himachal_pradesh", "lat": 32.2396, "lng": 77.1887, "phone": "01902-252340"},
    {"name": "Dharamsala Kotwali",      "district": "dharamsala", "state": "himachal_pradesh", "lat": 32.2190, "lng": 76.3234, "phone": "01892-222126"},
]


def main():
    db = SessionLocal()
    try:
        existing = db.query(PoliceStation).count()
        if existing > 0:
            print(f"Police stations already seeded ({existing} records). Skipping.")
            return

        for s in STATIONS:
            db.add(PoliceStation(**s))
        db.commit()
        print(f"Seeded {len(STATIONS)} police stations across {len(set(s['district'] for s in STATIONS))} districts.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
