"""
Unit tests for TrafficDensityService.

All tests use in-memory mock repositories — no database, no Redis, no network.
This is Liskov Substitution in action: MockCheckpointRepository and
MockTrafficEntryRepository implement the same interfaces as the Postgres
versions, so the service layer can't tell the difference.

Run with:
  cd services/traffic-service
  pytest tests/test_density_service.py -v
"""
import os, sys
sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL",       "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL",          "redis://localhost:6379/0")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH","/tmp/fake_secrets/pub.pem")

from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from app.models.checkpoint import Checkpoint
from app.repositories.interfaces import ICheckpointRepository, ITrafficEntryRepository
from app.services.density_service import TrafficDensityService, DISTRICT_CAPACITIES


# ── Mock implementations ──────────────────────────────────
class MockCheckpointRepository(ICheckpointRepository):
    def __init__(self, checkpoints: list):
        self._checkpoints = checkpoints

    def get_by_id(self, checkpoint_id):
        return next((c for c in self._checkpoints if c.id == checkpoint_id), None)

    def get_by_district(self, district):
        return [c for c in self._checkpoints if c.district == district]

    def get_all_active(self):
        return [c for c in self._checkpoints if c.is_active]


class MockTrafficEntryRepository(ITrafficEntryRepository):
    def __init__(self, counts_by_district: dict):
        self._counts = counts_by_district

    def create(self, vehicle_id, checkpoint_id, direction):
        pass  # not needed for density tests

    def count_active_by_district(self, district):
        return self._counts.get(district.lower(), 0)

    def count_active_all_districts(self):
        return self._counts.copy()

    def mark_timed_out(self, older_than_hours=18):
        return 0


def _make_checkpoint(district: str, state: str = "uttarakhand") -> Checkpoint:
    cp = Checkpoint()
    cp.id       = uuid4()
    cp.name     = f"{district.title()} Toll Plaza"
    cp.district = district
    cp.state    = state
    cp.lat      = 29.0
    cp.lng      = 79.0
    cp.is_active = True
    cp.capacity  = str(DISTRICT_CAPACITIES.get(district, 3000))
    return cp


# ── Tests ─────────────────────────────────────────────────
@pytest.fixture
def mock_redis():
    """Patch Redis so tests don't need a real Redis server."""
    with patch("app.services.density_service.redis_client") as mock:
        mock.get.return_value = None   # always cache miss
        mock.setex.return_value = True
        mock.delete.return_value = 1
        yield mock


def test_green_risk_level_below_60_percent(mock_redis):
    checkpoints = [_make_checkpoint("nainital")]
    # 2000 vehicles out of 5000 capacity = 40% → GREEN
    svc = TrafficDensityService(
        MockCheckpointRepository(checkpoints),
        MockTrafficEntryRepository({"nainital": 2000}),
    )
    result = svc.get_district_density("nainital")
    assert result.district == "nainital"
    assert result.active_vehicles == 2000
    assert result.risk_level == "GREEN"
    assert result.percentage == 40.0
    assert result.cached == False


def test_amber_risk_level_60_to_85_percent(mock_redis):
    checkpoints = [_make_checkpoint("nainital")]
    # 3500 / 5000 = 70% → AMBER
    svc = TrafficDensityService(
        MockCheckpointRepository(checkpoints),
        MockTrafficEntryRepository({"nainital": 3500}),
    )
    result = svc.get_district_density("nainital")
    assert result.risk_level == "AMBER"
    assert result.percentage == 70.0


def test_red_risk_level_above_85_percent(mock_redis):
    checkpoints = [_make_checkpoint("nainital")]
    # 4500 / 5000 = 90% → RED
    svc = TrafficDensityService(
        MockCheckpointRepository(checkpoints),
        MockTrafficEntryRepository({"nainital": 4500}),
    )
    result = svc.get_district_density("nainital")
    assert result.risk_level == "RED"
    assert result.percentage == 90.0


def test_percentage_capped_at_100(mock_redis):
    checkpoints = [_make_checkpoint("nainital")]
    # 7000 vehicles but capacity is 5000 — should cap at 100%, not 140%
    svc = TrafficDensityService(
        MockCheckpointRepository(checkpoints),
        MockTrafficEntryRepository({"nainital": 7000}),
    )
    result = svc.get_district_density("nainital")
    assert result.percentage == 100.0
    assert result.active_vehicles == 7000  # raw count still correct


def test_cached_response_served_from_redis(mock_redis):
    mock_redis.get.return_value = "3000"  # simulate cache hit
    checkpoints = [_make_checkpoint("nainital")]
    svc = TrafficDensityService(
        MockCheckpointRepository(checkpoints),
        MockTrafficEntryRepository({}),  # empty — DB should NOT be called
    )
    result = svc.get_district_density("nainital")
    assert result.cached == True
    assert result.active_vehicles == 3000


def test_all_districts_sorted_by_percentage_descending(mock_redis):
    checkpoints = [
        _make_checkpoint("nainital"),   # capacity 5000
        _make_checkpoint("mussoorie"),  # capacity 4000
        _make_checkpoint("ranikhet"),   # capacity 2000
    ]
    svc = TrafficDensityService(
        MockCheckpointRepository(checkpoints),
        MockTrafficEntryRepository({
            "nainital":  1000,   # 20%
            "mussoorie": 3200,   # 80%
            "ranikhet":  1800,   # 90%
        }),
    )
    result = svc.get_all_districts_density()
    percentages = [d.percentage for d in result.districts]
    assert percentages == sorted(percentages, reverse=True)
    assert result.districts[0].district == "ranikhet"  # highest %


def test_zero_vehicles_gives_green_zero_percent(mock_redis):
    checkpoints = [_make_checkpoint("almora")]
    svc = TrafficDensityService(
        MockCheckpointRepository(checkpoints),
        MockTrafficEntryRepository({"almora": 0}),
    )
    result = svc.get_district_density("almora")
    assert result.active_vehicles == 0
    assert result.percentage == 0.0
    assert result.risk_level == "GREEN"


def test_total_vehicles_is_sum_of_all_districts(mock_redis):
    checkpoints = [_make_checkpoint("nainital"), _make_checkpoint("mussoorie")]
    svc = TrafficDensityService(
        MockCheckpointRepository(checkpoints),
        MockTrafficEntryRepository({"nainital": 1000, "mussoorie": 500}),
    )
    result = svc.get_all_districts_density()
    assert result.total_active_vehicles == 1500
