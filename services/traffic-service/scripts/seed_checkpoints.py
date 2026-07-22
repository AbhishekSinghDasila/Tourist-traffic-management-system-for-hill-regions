"""
Seeds the checkpoints table with real toll plazas and entry points
for Uttarakhand and Himachal Pradesh hill districts.

Coordinates are real GPS locations of actual toll plazas/entry gates.

Usage (from inside the traffic-service container):
  docker compose exec traffic-service python -m scripts.seed_checkpoints
"""
import sys
sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.models.checkpoint import Checkpoint

CHECKPOINTS = [
    # ── Uttarakhand ───────────────────────────────────────
    # Nainital
    {"name": "Bhowali Toll Plaza",     "district": "nainital",   "state": "uttarakhand", "lat": 29.3919, "lng": 79.5278, "capacity": "5000"},
    {"name": "Kathgodam Entry Gate",   "district": "nainital",   "state": "uttarakhand", "lat": 29.2695, "lng": 79.5228, "capacity": "5000"},
    # Mussoorie
    {"name": "Dehradun-Mussoorie Gate","district": "mussoorie",  "state": "uttarakhand", "lat": 30.4598, "lng": 78.0644, "capacity": "4000"},
    {"name": "Kempty Fall Checkpoint", "district": "mussoorie",  "state": "uttarakhand", "lat": 30.4833, "lng": 78.0167, "capacity": "4000"},
    # Haridwar
    {"name": "Haridwar Entry Toll",    "district": "haridwar",   "state": "uttarakhand", "lat": 29.9457, "lng": 78.1642, "capacity": "8000"},
    {"name": "Roorkee Bypass Gate",    "district": "haridwar",   "state": "uttarakhand", "lat": 29.8543, "lng": 77.8880, "capacity": "8000"},
    # Rishikesh
    {"name": "Rishikesh Toll Plaza",   "district": "rishikesh",  "state": "uttarakhand", "lat": 30.0869, "lng": 78.2676, "capacity": "6000"},
    {"name": "Neelkanth Entry",        "district": "rishikesh",  "state": "uttarakhand", "lat": 30.1191, "lng": 78.3733, "capacity": "6000"},
    # Ranikhet
    {"name": "Ranikhet Entry Gate",    "district": "ranikhet",   "state": "uttarakhand", "lat": 29.6419, "lng": 79.4311, "capacity": "2000"},
    # Almora
    {"name": "Almora Toll Naya",       "district": "almora",     "state": "uttarakhand", "lat": 29.5971, "lng": 79.6591, "capacity": "2500"},
    # Kedarnath
    {"name": "Gaurikund Entry",        "district": "kedarnath",  "state": "uttarakhand", "lat": 30.6450, "lng": 79.2690, "capacity": "3000"},
    # Badrinath
    {"name": "Joshimath Toll",         "district": "badrinath",  "state": "uttarakhand", "lat": 30.5579, "lng": 79.5645, "capacity": "3000"},

    # ── Himachal Pradesh ──────────────────────────────────
    # Shimla
    {"name": "Shoghi Toll Plaza",      "district": "shimla",     "state": "himachal_pradesh", "lat": 31.0184, "lng": 77.1925, "capacity": "6000"},
    {"name": "Tara Devi Checkpoint",   "district": "shimla",     "state": "himachal_pradesh", "lat": 31.0724, "lng": 77.0554, "capacity": "6000"},
    # Manali
    {"name": "Kullu-Manali Toll",      "district": "manali",     "state": "himachal_pradesh", "lat": 32.2396, "lng": 77.1887, "capacity": "5000"},
    {"name": "Bhuntar Airport Gate",   "district": "manali",     "state": "himachal_pradesh", "lat": 31.8787, "lng": 77.1523, "capacity": "5000"},
    # Dharamsala
    {"name": "Gaggal Toll Plaza",      "district": "dharamsala", "state": "himachal_pradesh", "lat": 32.1657, "lng": 76.2736, "capacity": "4000"},
    {"name": "Dharamsala Entry",       "district": "dharamsala", "state": "himachal_pradesh", "lat": 32.2190, "lng": 76.3234, "capacity": "4000"},
]


def main():
    db = SessionLocal()
    try:
        existing = db.query(Checkpoint).count()
        if existing > 0:
            print(f"Checkpoints already seeded ({existing} records). Skipping.")
            print("To re-seed: truncate the checkpoints table first.")
            return

        created = 0
        for cp_data in CHECKPOINTS:
            cp = Checkpoint(**cp_data)
            db.add(cp)
            created += 1

        db.commit()
        print(f"Seeded {created} checkpoints across {len(set(c['district'] for c in CHECKPOINTS))} districts.")
        print("\nDistricts seeded:")
        for district in sorted(set(c['district'] for c in CHECKPOINTS)):
            count = sum(1 for c in CHECKPOINTS if c['district'] == district)
            print(f"  {district}: {count} checkpoint(s)")

    finally:
        db.close()


if __name__ == "__main__":
    main()
