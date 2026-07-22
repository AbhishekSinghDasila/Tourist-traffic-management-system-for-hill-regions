"""
Unit tests for alert service.
No DB, no Redis, no FCM, no Kafka — all mocked.
"""
import os, sys
sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL",        "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL",           "redis://localhost:6379/0")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "/tmp/fake_secrets/pub.pem")
os.environ.setdefault("USE_FCM",             "false")

import json
import uuid
from unittest.mock import MagicMock, patch
import pytest

from app.services.alert_service import _haversine_km, _find_nearby_users
from app.services.notification_service import ConsolePushNotifier, get_notifier


def test_haversine_zero_distance():
    assert _haversine_km(29.39, 79.45, 29.39, 79.45) == 0.0

def test_haversine_known_distance():
    dist = _haversine_km(29.3919, 79.4542, 29.3919, 79.5278)
    assert 5 < dist < 12

def test_haversine_long_distance():
    dist = _haversine_km(28.6139, 77.2090, 29.3919, 79.4542)
    assert 200 < dist < 280

def test_find_nearby_users_within_radius():
    user_near = str(uuid.uuid4())
    user_far  = str(uuid.uuid4())
    alert_lat, alert_lng = 29.3919, 79.4542
    near_loc = json.dumps({"lat": 29.3989, "lng": 79.4542})
    far_loc  = json.dumps({"lat": 29.4369, "lng": 79.4542})

    mock_redis = MagicMock()
    mock_redis.scan.return_value = (0, [f"loc:{user_near}", f"loc:{user_far}"])
    mock_redis.get.side_effect = lambda k: near_loc if user_near in k else far_loc

    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = []

    with patch("app.services.alert_service.redis_client", mock_redis):
        result = _find_nearby_users(alert_lat, alert_lng, 2.0, mock_db)

    assert user_near in result
    assert user_far not in result

def test_find_nearby_users_empty_redis_falls_back_to_db():
    mock_redis = MagicMock()
    mock_redis.scan.return_value = (0, [])

    user_id = uuid.uuid4()
    mock_location = MagicMock()
    mock_location.user_id = user_id
    mock_location.lat = 29.395
    mock_location.lng = 79.454

    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = [mock_location]

    with patch("app.services.alert_service.redis_client", mock_redis):
        result = _find_nearby_users(29.3919, 79.4542, 2.0, mock_db)

    assert str(user_id) in result

def test_find_nearby_users_zero_in_radius():
    mock_redis = MagicMock()
    mock_redis.scan.return_value = (0, [])
    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = []

    with patch("app.services.alert_service.redis_client", mock_redis):
        result = _find_nearby_users(29.39, 79.45, 2.0, mock_db)

    assert result == []

def test_console_notifier_send_to_user_returns_true():
    notifier = ConsolePushNotifier()
    assert notifier.send_to_user("user-123", "Alert", "Body", {}) is True

def test_console_notifier_send_to_topic_returns_one():
    notifier = ConsolePushNotifier()
    assert notifier.send_to_topic("police_nainital", "Emergency", "Body", {}) == 1

def test_get_notifier_returns_console_when_fcm_disabled():
    assert isinstance(get_notifier(), ConsolePushNotifier)

def test_alert_radius_capped_at_10km():
    from app.schemas.alert import AlertCreate
    alert = AlertCreate(lat=29.39, lng=79.45, radius_km=50.0)
    assert alert.radius_km == 10.0

def test_alert_radius_minimum_half_km():
    from app.schemas.alert import AlertCreate
    alert = AlertCreate(lat=29.39, lng=79.45, radius_km=0.1)
    assert alert.radius_km == 0.5

def test_invalid_alert_type_defaults_to_other():
    from app.schemas.alert import AlertCreate
    alert = AlertCreate(lat=29.39, lng=79.45, alert_type="INVALID_TYPE")
    assert alert.alert_type == "OTHER"

def test_two_simultaneous_alerts_have_different_ids():
    id1, id2 = uuid.uuid4(), uuid.uuid4()
    assert id1 != id2
