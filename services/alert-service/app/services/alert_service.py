"""
AlertService — emergency alert dispatch.

Flow:
1. Emergency team triggers alert via POST /api/v1/alerts
2. _find_nearby_users() scans Redis for users within radius_km
3. ConsolePushNotifier (dev) or FCMPushNotifier (prod) notifies each user
4. Police station notified via topic broadcast
5. Alert + recipients saved to DB
6. ambulance.alert Kafka event published (graceful degradation)
"""
import json
import logging
import math
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import redis_client
from app.models.alert import EmergencyAlert, AlertRecipient, UserLocation
from app.services.notification_service import get_notifier

logger = logging.getLogger("alert-service.dispatch")


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _find_nearby_users(alert_lat: float, alert_lng: float, radius_km: float, db: Session) -> list[str]:
    """
    Finds user_ids within radius_km of alert location.
    Redis first (fast), Postgres fallback if Redis empty.
    """
    nearby = []

    cursor = 0
    while True:
        cursor, keys = redis_client.scan(cursor, match="loc:*", count=100)
        for key in keys:
            data = redis_client.get(key)
            if not data:
                continue
            try:
                loc = json.loads(data)
                dist = _haversine_km(alert_lat, alert_lng, loc["lat"], loc["lng"])
                if dist <= radius_km:
                    user_id = key.replace("loc:", "")
                    nearby.append(user_id)
            except (json.JSONDecodeError, KeyError):
                continue
        if cursor == 0:
            break

    # DB fallback if Redis had nothing
    if not nearby:
        db_locations = db.query(UserLocation).all()
        for loc in db_locations:
            dist = _haversine_km(alert_lat, alert_lng, loc.lat, loc.lng)
            if dist <= radius_km:
                nearby.append(str(loc.user_id))

    logger.info(f"Found {len(nearby)} users within {radius_km}km of alert")
    return nearby


def update_user_location(user_id: str, lat: float, lng: float, district: Optional[str], db: Session) -> None:
    """Update user location in Redis (1hr TTL) and Postgres."""
    loc_data = json.dumps({"lat": lat, "lng": lng, "district": district})
    redis_client.setex(f"loc:{user_id}", 3600, loc_data)

    existing = db.query(UserLocation).filter(UserLocation.user_id == UUID(user_id)).first()
    if existing:
        existing.lat = lat
        existing.lng = lng
        existing.district = district
        existing.updated_at = datetime.now(timezone.utc)
    else:
        db.add(UserLocation(user_id=UUID(user_id), lat=lat, lng=lng, district=district))
    db.commit()


def dispatch_alert(
    triggered_by: str,
    alert_type: str,
    description: Optional[str],
    lat: float,
    lng: float,
    district: Optional[str],
    radius_km: float,
    db: Session,
) -> EmergencyAlert:
    """Full alert dispatch — creates alert, finds users, sends notifications."""

    # Step 1: Create alert record
    alert = EmergencyAlert(
        triggered_by=UUID(triggered_by),
        alert_type=alert_type,
        description=description,
        lat=lat, lng=lng,
        district=district,
        radius_km=radius_km,
        status="ACTIVE",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    logger.info(f"Alert {alert.id} created: {alert_type} at lat={lat}, lng={lng}")

    notifier = get_notifier()
    recipients_created = 0

    title = f"🚨 Emergency — {alert_type.replace('_', ' ').title()}"
    body  = description or "Emergency vehicle requires clear passage. Please cooperate."
    data  = {"alert_id": str(alert.id), "alert_type": alert_type,
             "lat": str(lat), "lng": str(lng)}

    # Step 2: Notify nearby users
    for user_id in _find_nearby_users(lat, lng, radius_km, db):
        success = notifier.send_to_user(user_id, title, body, data)
        db.add(AlertRecipient(
            alert_id=alert.id,
            recipient_type="USER",
            recipient_id=user_id,
            channel="PUSH" if settings.USE_FCM else "CONSOLE",
            delivery_status="DELIVERED" if success else "FAILED",
            delivered_at=datetime.now(timezone.utc) if success else None,
        ))
        recipients_created += 1

    # Step 3: Notify police station via topic
    if district:
        topic = f"police_{district.lower().replace(' ', '_')}"
        count = notifier.send_to_topic(
            topic,
            f"🚨 Emergency Alert — {alert_type}",
            f"Emergency at lat={lat:.4f}, lng={lng:.4f}. Clear traffic corridor.",
            data,
        )
        db.add(AlertRecipient(
            alert_id=alert.id,
            recipient_type="POLICE_STATION",
            recipient_id=topic,
            channel="PUSH" if settings.USE_FCM else "CONSOLE",
            delivery_status="DELIVERED" if count > 0 else "PENDING",
            delivered_at=datetime.now(timezone.utc) if count > 0 else None,
        ))
        recipients_created += 1

    # Step 4: Update recipient count
    alert.recipient_count = recipients_created
    db.commit()
    db.refresh(alert)

    # Step 5: Publish Kafka event (graceful degradation)
    _publish_kafka_event({
        "event_type": "ambulance.alert",
        "alert_id": str(alert.id),
        "alert_type": alert_type,
        "lat": lat, "lng": lng,
        "district": district,
        "radius_km": radius_km,
        "recipient_count": recipients_created,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, settings.KAFKA_BOOTSTRAP_SERVERS)

    logger.info(f"Alert {alert.id} dispatched to {recipients_created} recipients")
    return alert


def cancel_alert(alert_id: UUID, cancelled_by: str, reason: str, db: Session) -> Optional[EmergencyAlert]:
    """Cancel a false alarm. Sends cancellation push to all previously-delivered recipients."""
    alert = db.query(EmergencyAlert).filter(EmergencyAlert.id == alert_id).first()
    if not alert or alert.status != "ACTIVE":
        return None

    alert.status = "CANCELLED"
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()

    notifier = get_notifier()
    delivered = (db.query(AlertRecipient)
                 .filter(AlertRecipient.alert_id == alert_id)
                 .filter(AlertRecipient.delivery_status == "DELIVERED")
                 .all())

    cancel_data = {"alert_id": str(alert_id), "status": "CANCELLED"}
    for r in delivered:
        if r.recipient_type == "USER":
            notifier.send_to_user(r.recipient_id, "✅ Alert Cancelled", f"Reason: {reason}", cancel_data)
        else:
            notifier.send_to_topic(r.recipient_id, "✅ Alert Cancelled", f"Reason: {reason}", cancel_data)

    logger.info(f"Alert {alert_id} cancelled by {cancelled_by}. Reason: {reason}")
    db.refresh(alert)
    return alert


def _publish_kafka_event(event: dict, servers: str) -> bool:
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(
            bootstrap_servers=servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=3000, retries=1,
        )
        producer.send("ambulance.alert", value=event)
        producer.flush(timeout=5)
        producer.close()
        logger.info(f"Published ambulance.alert for {event.get('alert_id')}")
        return True
    except Exception as e:
        logger.warning(f"Kafka unavailable: {e}")
        return False
