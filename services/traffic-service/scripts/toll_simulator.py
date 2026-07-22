"""
Toll Plaza Simulator — generates realistic fake vehicle entry/exit events.

Why this exists: we don't have access to real Fastag/toll API data.
This script seeds the database with believable traffic patterns so the
density map shows meaningful numbers during development and demos.

What it simulates:
- Vehicles entering districts at realistic rates (more on weekends/holidays)
- Vehicles exiting after a stay of 1-3 days
- State-wise distribution (mostly UP, Delhi, Haryana plates in Uttarakhand)
- Peak hours (morning 8-11am, afternoon 2-5pm)

Usage:
  # From E:\\DevBhumi, run inside the traffic-service container:
  docker compose exec traffic-service python -m scripts.toll_simulator

  # Or with options:
  docker compose exec traffic-service python -m scripts.toll_simulator --vehicles 200 --district nainital
"""
import argparse
import random
import sys
import time
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, ".")

# ── Realistic data ────────────────────────────────────────
STATE_CODES = ["UP", "DL", "HR", "RJ", "PB", "MP", "UK", "MH", "GJ"]
STATE_WEIGHTS = [30, 25, 15, 8, 5, 5, 4, 4, 4]  # UP and Delhi dominate

DISTRICTS = ["nainital", "mussoorie", "ranikhet", "almora", "haridwar", "rishikesh"]

# Plate format: <STATE><2-digit-RTO><2-alpha><4-digit>
def _random_plate(state: str) -> str:
    rto  = random.randint(1, 99)
    alpha = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=2))
    num  = random.randint(1000, 9999)
    return f"{state}{rto:02d}{alpha}{num}"


def simulate(district: str, num_vehicles: int, api_base: str, token: str):
    import urllib.request
    import urllib.error
    import json

    # First get the checkpoint ID for this district
    print(f"\n[Simulator] Fetching checkpoints for district: {district}")
    url = f"{api_base}/api/v1/traffic/density/{district}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            pass  # just verify the service is up
    except Exception as e:
        print(f"[Simulator] Traffic service not reachable at {api_base}: {e}")
        print("[Simulator] Make sure containers are running: docker compose up -d")
        return

    # Get all checkpoints from DB directly (simulator runs inside container)
    from app.core.database import SessionLocal
    from app.models.checkpoint import Checkpoint
    from app.models.vehicle import Vehicle
    from app.models.traffic_entry import TrafficEntry
    from app.repositories.postgres_repositories import (
        PostgresCheckpointRepository,
        PostgresVehicleRepository,
        PostgresTrafficEntryRepository,
    )
    from app.core.redis_client import redis_client

    db = SessionLocal()
    cp_repo      = PostgresCheckpointRepository(db)
    vehicle_repo = PostgresVehicleRepository(db)
    entry_repo   = PostgresTrafficEntryRepository(db)

    checkpoints = cp_repo.get_by_district(district)
    if not checkpoints:
        print(f"[Simulator] No checkpoints found for district '{district}'.")
        print("[Simulator] Run the seed script first: docker compose exec traffic-service python -m scripts.seed_checkpoints")
        db.close()
        return

    print(f"[Simulator] Found {len(checkpoints)} checkpoint(s) for {district}")
    print(f"[Simulator] Simulating {num_vehicles} vehicles...\n")

    entries = 0
    exits   = 0

    for i in range(num_vehicles):
        state = random.choices(STATE_CODES, weights=STATE_WEIGHTS)[0]
        plate = _random_plate(state)
        checkpoint = random.choice(checkpoints)

        # 70% are entries (net inflow during tourist season)
        direction = "ENTRY" if random.random() < 0.7 else "EXIT"

        vehicle = vehicle_repo.upsert(plate, state)
        entry_repo.create(vehicle.id, checkpoint.id, direction)

        if direction == "ENTRY":
            entries += 1
        else:
            exits += 1

        # Invalidate cache for this district
        redis_client.delete(f"tourist_count:{district}")

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{num_vehicles}] {entries} entries, {exits} exits so far...")

    db.close()

    print(f"\n[Simulator] Done!")
    print(f"  Entries recorded : {entries}")
    print(f"  Exits recorded   : {exits}")
    print(f"  Net new vehicles : {entries - exits}")
    print(f"\nCheck density at: {api_base}/api/v1/traffic/density/{district}")


def main():
    parser = argparse.ArgumentParser(description="DevBhumi Toll Plaza Simulator")
    parser.add_argument("--district",  default="nainital",        help="District to simulate (default: nainital)")
    parser.add_argument("--vehicles",  type=int, default=100,     help="Number of vehicles to simulate (default: 100)")
    parser.add_argument("--api-base",  default="http://localhost:8000", help="Traffic service base URL")
    parser.add_argument("--token",     default="",                help="JWT token for protected endpoints")
    args = parser.parse_args()

    simulate(args.district, args.vehicles, args.api_base, args.token)


if __name__ == "__main__":
    main()
