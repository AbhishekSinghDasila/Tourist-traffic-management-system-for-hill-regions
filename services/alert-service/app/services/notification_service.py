"""
Notification service — Factory pattern for push notifications.
ConsolePushNotifier: logs to console (dev)
FCMPushNotifier: Firebase Cloud Messaging (production)
get_notifier(): factory returning the right implementation based on config.
"""
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("alert-service.notification")


class IPushNotifier(ABC):
    @abstractmethod
    def send_to_user(self, user_id: str, title: str, body: str, data: dict) -> bool: ...

    @abstractmethod
    def send_to_topic(self, topic: str, title: str, body: str, data: dict) -> int: ...


class ConsolePushNotifier(IPushNotifier):
    """Dev mock — prints to console instead of sending real push messages."""

    def send_to_user(self, user_id: str, title: str, body: str, data: dict) -> bool:
        logger.info(f"[MOCK PUSH] → user:{user_id} | {title}: {body} | data:{data}")
        return True

    def send_to_topic(self, topic: str, title: str, body: str, data: dict) -> int:
        logger.info(f"[MOCK PUSH] → topic:{topic} | {title}: {body} | data:{data}")
        return 1


class FCMPushNotifier(IPushNotifier):
    """Production — Firebase Cloud Messaging."""

    def __init__(self, credentials_path: str):
        try:
            import firebase_admin
            from firebase_admin import credentials
            if not firebase_admin._apps:
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred)
            self._initialized = True
        except Exception as e:
            logger.error(f"FCM init failed: {e}. Falling back to console.")
            self._initialized = False

    def send_to_user(self, user_id: str, title: str, body: str, data: dict) -> bool:
        if not self._initialized:
            logger.warning(f"[FCM FALLBACK] → user:{user_id} | {title}: {body}")
            return False
        try:
            from firebase_admin import messaging
            messaging.send(messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in data.items()},
                token=user_id,
            ))
            return True
        except Exception as e:
            logger.error(f"FCM send failed for {user_id}: {e}")
            return False

    def send_to_topic(self, topic: str, title: str, body: str, data: dict) -> int:
        if not self._initialized:
            logger.warning(f"[FCM FALLBACK] → topic:{topic} | {title}: {body}")
            return 0
        try:
            from firebase_admin import messaging
            messaging.send(messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in data.items()},
                topic=topic,
            ))
            return 1
        except Exception as e:
            logger.error(f"FCM topic send failed for {topic}: {e}")
            return 0


def get_notifier() -> IPushNotifier:
    """Factory — returns ConsolePushNotifier in dev, FCMPushNotifier in production."""
    from app.core.config import settings
    if settings.USE_FCM and settings.FCM_CREDENTIALS_PATH:
        return FCMPushNotifier(settings.FCM_CREDENTIALS_PATH)
    return ConsolePushNotifier()
