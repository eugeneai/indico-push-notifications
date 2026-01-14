# This file is part of Indico Push Notifications Plugin.
# Copyright (C) 2024 CERN
#
# Indico Push Notifications Plugin is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

from indico.core.db import db
from indico.modules.users import User
from indico.util.date_time import now_utc

from . import plugin
from .notifications import push_user_settings

logger = logging.getLogger(__name__)


def get_vapid_credentials() -> Dict:
    """Get or generate VAPID credentials for Web Push."""
    public_key = plugin.default_settings.get("vapid_public_key")
    private_key = plugin.default_settings.get("vapid_private_key")
    email = plugin.default_settings.get("vapid_email", "admin@example.com")

    # Generate new keys if not configured
    if not public_key or not private_key:
        logger.info("Generating new VAPID keys for Web Push")
        vapid = Vapid()
        vapid.generate_keys()

        public_key = vapid.public_key
        private_key = vapid.private_key

        # Store in plugin settings (would need to be saved to config)
        logger.warning(
            "VAPID keys generated but not saved to plugin settings. "
            "Please configure them in the plugin admin interface."
        )

    return {
        "public_key": public_key,
        "private_key": private_key,
        "email": email,
    }


def is_webpush_enabled() -> bool:
    """Check if Web Push notifications are enabled."""
    return plugin.default_settings.get("webpush_enabled", True) and bool(
        get_vapid_credentials().get("public_key")
    )


def validate_push_subscription(subscription: Dict) -> bool:
    """Validate Web Push subscription data."""
    if not subscription:
        return False

    # Check required fields
    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys", {})

    if not endpoint or not keys:
        return False

    # Validate endpoint URL
    try:
        parsed = urlparse(endpoint)
        if not parsed.scheme or not parsed.netloc:
            return False
    except Exception:
        return False

    # Validate encryption keys
    auth = keys.get("auth")
    p256dh = keys.get("p256dh")

    if not auth or not p256dh:
        return False

    # Validate key formats (basic check)
    try:
        # Check if keys are valid base64
        import base64
        base64.urlsafe_b64decode(auth + "===")
        base64.urlsafe_b64decode(p256dh + "===")
    except Exception:
        return False

    return True


def save_push_subscription(user: User, subscription: Dict) -> bool:
    """Save Web Push subscription for a user."""
    if not is_webpush_enabled():
        logger.warning("Web Push notifications are disabled")
        return False

    if not validate_push_subscription(subscription):
        logger.error("Invalid push subscription data")
        return False

    # Get current subscriptions
    subscriptions = push_user_settings.get(user, "push_subscriptions") or []

    # Check if subscription already exists
    endpoint = subscription["endpoint"]
    existing_index = -1

    for i, sub in enumerate(subscriptions):
        if sub.get("endpoint") == endpoint:
            existing_index = i
            break

    # Prepare subscription data
    subscription_data = {
        "endpoint": endpoint,
        "keys": subscription["keys"],
        "created": now_utc().isoformat(),
        "updated": now_utc().isoformat(),
    }

    # Update or add subscription
    if existing_index >= 0:
        subscriptions[existing_index] = subscription_data
        logger.debug(f"Updated push subscription for user {user.id}")
    else:
        subscriptions.append(subscription_data)
        logger.debug(f"Added new push subscription for user {user.id}")

    # Save to user settings
    push_user_settings.set(user, "push_subscriptions", subscriptions)

    # Enable push notifications if not already enabled
    if not push_user_settings.get(user, "push_enabled"):
        push_user_settings.set(user, "push_enabled", True)

    return True


def delete_push_subscription(user: User, endpoint: str) -> bool:
    """Delete Web Push subscription for a user."""
    subscriptions = push_user_settings.get(user, "push_subscriptions") or []

    # Filter out the subscription
    original_count = len(subscriptions)
    subscriptions = [sub for sub in subscriptions if sub.get("endpoint") != endpoint]

    if len(subscriptions) < original_count:
        push_user_settings.set(user, "push_subscriptions", subscriptions)
        logger.debug(f"Deleted push subscription for user {user.id}")

        # Disable push notifications if no subscriptions left
        if not subscriptions:
            push_user_settings.set(user, "push_enabled", False)

        return True

    return False


def get_push_subscriptions(user: User) -> List[Dict]:
    """Get all Web Push subscriptions for a user."""
    subscriptions = push_user_settings.get(user, "push_subscriptions") or []

    # Return only necessary information (exclude private keys)
    result = []
    for sub in subscriptions:
        result.append({
            "endpoint": sub.get("endpoint"),
            "created": sub.get("created"),
            "updated": sub.get("updated"),
        })

    return result


def send_push_notification(subscription: Dict, message: Dict) -> bool:
    """Send a Web Push notification."""
    if not is_webpush_enabled():
        logger.warning("Web Push notifications are disabled")
        return False

    if not validate_push_subscription(subscription):
        logger.error("Invalid subscription for push notification")
        return False

    # Get VAPID credentials
    vapid_credentials = get_vapid_credentials()
    if not vapid_credentials["public_key"]:
        logger.error("VAPID credentials not configured")
        return False

    try:
        # Prepare notification data
        notification_data = {
            "title": message.get("title", "Indico Notification"),
            "body": message.get("body", ""),
            "icon": message.get("icon", "/static/images/indico_square.png"),
            "badge": message.get("badge", "/static/images/indico_badge.png"),
            "timestamp": int(datetime.now().timestamp() * 1000),  # milliseconds
        }

        # Add URL for navigation if provided
        if "data" in message and "url" in message["data"]:
            notification_data["data"] = {"url": message["data"]["url"]}

        # Send push notification
        webpush(
            subscription_info=subscription,
            data=json.dumps(notification_data),
            vapid_private_key=vapid_credentials["private_key"],
            vapid_claims={
                "sub": f"mailto:{vapid_credentials['email']}",
            },
        )

        logger.debug(f"Push notification sent to {subscription['endpoint'][:50]}...")
        return True

    except WebPushException as e:
        # Handle specific WebPush errors
        if e.response is not None:
            status = e.response.status_code

            if status == 404 or status == 410:
                # Subscription expired or invalid
                logger.warning(f"Push subscription expired: {subscription['endpoint'][:50]}...")
                # Note: Caller should clean up expired subscriptions
            elif status == 429:
                # Too many requests
                logger.warning("Too many push notifications, rate limited")
            else:
                logger.error(f"WebPush error {status}: {e}")
        else:
            logger.error(f"WebPush error: {e}")

        return False

    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return False


def send_test_push_notification(user: User, message: str = None) -> Dict:
    """Send a test Web Push notification to a user."""
    if not is_webpush_enabled():
        return {
            "success": False,
            "error": "Web Push notifications are disabled",
            "sent": 0,
            "total": 0,
        }

    if message is None:
        message = "This is a test push notification from Indico."

    subscriptions = push_user_settings.get(user, "push_subscriptions") or []

    if not subscriptions:
        return {
            "success": False,
            "error": "No push subscriptions found",
            "sent": 0,
            "total": 0,
        }

    test_message = {
        "title": "Test Notification",
        "body": message,
        "icon": "/static/images/indico_square.png",
        "badge": "/static/images/indico_badge.png",
        "data": {"url": "/"},
    }

    sent_count = 0
    errors = []

    for subscription in subscriptions:
        try:
            success = send_push_notification(subscription, test_message)
            if success:
                sent_count += 1
        except Exception as e:
            errors.append(f"{subscription.get('endpoint', 'unknown')[:30]}: {str(e)}")

    success = sent_count > 0

    result = {
        "success": success,
        "sent": sent_count,
        "total": len(subscriptions),
        "errors": errors if errors else None,
    }

    if not success and errors:
        result["error"] = "; ".join(errors[:3])  # Limit error message length

    return result


def cleanup_expired_subscriptions() -> None:
    """Clean up expired push subscriptions."""
    # This would typically involve:
    # 1. Tracking failed sends
    # 2. Removing subscriptions that consistently fail
    # 3. Removing very old subscriptions

    # For now, just log that cleanup would happen
    logger.info("Push subscription cleanup would run here")

    # In a real implementation, you might:
    # - Query all users with push subscriptions
    # - Check last successful notification time
    # - Remove subscriptions older than X days
    # - Remove subscriptions with too many consecutive failures


def get_webpush_config() -> Dict:
    """Get Web Push configuration for client-side."""
    if not is_webpush_enabled():
        return {"enabled": False}

    vapid_credentials = get_vapid_credentials()

    return {
        "enabled": True,
        "vapid_public_key": vapid_credentials["public_key"],
        "service_worker_path": "/static/push-notifications/service-worker.js",
    }
