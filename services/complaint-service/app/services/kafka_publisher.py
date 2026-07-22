"""
Kafka publisher — publishes complaint.created events.

Why Kafka instead of direct HTTP call to notification service?
- Decouples complaint submission from notification delivery
- If notification service is slow/down, complaint submission still succeeds
- Kafka retains the event — notification service picks it up when it recovers
- Provides an audit trail of all events for free

Event schema (complaint.created topic):
{
  "event_type": "complaint.created",
  "complaint_id": "uuid",
  "station_id": "uuid or null",
  "district": "nainital",
  "category": "LITTERING",
  "plate_number": "UK07BC1234 or null",
  "lat": 29.39,
  "lng": 79.52,
  "timestamp": "2026-06-27T00:00:00Z"
}

Note: user_id is deliberately NOT included in the Kafka event.
The notification service only needs to know which station to alert,
not who filed the complaint.

Graceful degradation: if Kafka is unavailable (Week 1-4 dev without Kafka),
the publish call is skipped with a warning log. Complaint submission
still succeeds — Kafka is enhancement, not dependency.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

logger = logging.getLogger("complaint-service.kafka")


def publish_complaint_created(
    complaint_id: UUID,
    station_id: Optional[UUID],
    district: Optional[str],
    category: str,
    plate_number: Optional[str],
    lat: float,
    lng: float,
    kafka_servers: str = "kafka:9092",
) -> bool:
    """
    Publishes a complaint.created event to Kafka.
    Returns True if published, False if Kafka unavailable (graceful degradation).
    Complaint submission is NOT rolled back on Kafka failure.
    """
    event = {
        "event_type": "complaint.created",
        "complaint_id": str(complaint_id),
        "station_id": str(station_id) if station_id else None,
        "district": district,
        "category": category,
        "plate_number": plate_number,
        "lat": lat,
        "lng": lng,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(
            bootstrap_servers=kafka_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=3000,   # fail fast if Kafka is down
            retries=1,
        )
        producer.send("complaint.created", value=event)
        producer.flush(timeout=5)
        producer.close()
        logger.info(f"Published complaint.created for {complaint_id}")
        return True

    except Exception as e:
        # Week 1-4: Kafka not running — log warning, don't fail the request
        logger.warning(f"Kafka unavailable, skipping event publish: {e}")
        return False
