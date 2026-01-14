# This file is part of Indico Push Notifications Plugin.
# Copyright (C) 2024 CERN
#
# Indico Push Notifications Plugin is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from flask import session
from indico.core import signals
from indico.core.db import db
from indico.core.notifications import make_email
from indico.core.settings import SettingsProxy
from indico.modules.users import User
from indico.util.date_time import now_utc
from sqlalchemy.orm import joinedload

from . import plugin
from .telegram_bot import send_telegram_message
from .webpush import send_push_notification

logger = logging.getLogger(__name__)

# User settings proxy for push notifications
push_user_settings = SettingsProxy(
    "push_notifications",
    {
        "telegram_chat_id": None,
        "telegram_username": None,
        "telegram_enabled": False,
        "telegram_linking_token": None,
        "telegram_linking_expires": None,
        "push_enabled": False,
        "push_subscriptions": [],  # List of dicts: {endpoint, keys, created}
        "notification_preferences": None,  # Will use plugin defaults if None
        "last_notification_sent": None,
    },
    strict=False,
)


def get_user_preferences(user: User) -> Dict:
    """Get notification preferences for a user."""
    plugin_prefs = plugin.default_settings.get("default_notification_preferences", {})
    user_prefs = push_user_settings.get(user, "notification_preferences")

    if user_prefs is None:
        user_prefs = plugin_prefs

    # Merge with plugin defaults for any missing keys
    for key, value in plugin_prefs.items():
        if key not in user_prefs:
            user_prefs[key] = value

    # Get Telegram settings from database model
    from .models import get_telegram_settings

    telegram_settings = get_telegram_settings(user)

    return {
        "telegram": {
            "chat_id": telegram_settings.get("chat_id"),
            "username": telegram_settings.get("username"),
            "enabled": telegram_settings.get("enabled", False),
            "linked": telegram_settings.get("linked", False),
        },
        "push": {
            "enabled": push_user_settings.get(user, "push_enabled"),
            "subscriptions_count": len(
                push_user_settings.get(user, "push_subscriptions") or []
            ),
        },
        "preferences": user_prefs,
        "last_notification": push_user_settings.get(user, "last_notification_sent"),
    }


def update_user_preferences(user: User, data: Dict) -> None:
    """Update user notification preferences."""
    if "telegram_enabled" in data:
        # Use model helper function to update both database and SettingsProxy
        from .models import update_telegram_enabled

        update_telegram_enabled(user, bool(data["telegram_enabled"]))

    if "push_enabled" in data:
        push_user_settings.set(user, "push_enabled", bool(data["push_enabled"]))

    if "preferences" in data:
        # Validate preferences structure
        preferences = data["preferences"]
        if isinstance(preferences, dict):
            # Ensure all values are boolean
            validated_prefs = {}
            for key, value in preferences.items():
                if isinstance(value, bool):
                    validated_prefs[key] = value

            push_user_settings.set(user, "notification_preferences", validated_prefs)


def should_send_notification(user: User, notification_type: str) -> bool:
    """Check if we should send a notification of given type to the user."""
    # Check if user has any notification channel enabled
    from .models import get_telegram_settings

    telegram_settings = get_telegram_settings(user)
    telegram_enabled = telegram_settings.get("enabled", False)
    push_enabled = push_user_settings.get(user, "push_enabled")

    if not telegram_enabled and not push_enabled:
        return False

    # Check notification preferences
    prefs = push_user_settings.get(user, "notification_preferences")
    if prefs is None:
        prefs = plugin.default_settings.get("default_notification_preferences", {})

    # Check specific preference for this notification type
    if notification_type in prefs:
        return prefs[notification_type]

    # Default to True if preference not specified
    return True


def get_notification_recipients(email: Dict) -> Set[User]:
    """Extract User objects from email recipients."""
    recipients = set()

    # Extract emails from all recipient fields
    emails = set()
    emails.update(email.get("to", []))
    emails.update(email.get("cc", []))
    emails.update(email.get("bcc", []))

    # Find users by email
    for email_addr in emails:
        # Query user by email (including secondary emails)
        user = User.query.filter(
            db.or_(
                User.all_emails.contains([email_addr]),
                User.secondary_emails.any(email=email_addr),
            )
        ).first()

        if user:
            recipients.add(user)

    return recipients


def extract_notification_context(**kwargs) -> Dict:
    """Extract context information from notification kwargs."""
    context = {
        "type": "generic",
        "event": None,
        "event_id": None,
        "event_url": None,
        "source": kwargs.get("sender", "unknown"),
    }

    # Try to extract event from kwargs
    event = kwargs.get("event")
    if event:
        context["event"] = event
        context["event_id"] = event.id
        # Generate event URL
        from indico.web.flask.util import url_for

        context["event_url"] = url_for("events.display", event, _external=True)

    # Try to determine notification type from sender
    sender = kwargs.get("sender", "")
    if "event" in sender.lower():
        context["type"] = "event"
    elif "registration" in sender.lower():
        context["type"] = "registration"
    elif "abstract" in sender.lower():
        context["type"] = "abstract"
    elif "reminder" in sender.lower():
        context["type"] = "reminder"

    return context


def format_notification_message(subject: str, body: str, context: Dict) -> Dict:
    """Format notification message for different channels."""
    # Truncate body for push notifications
    max_body_length = 500
    if len(body) > max_body_length:
        preview_body = body[:max_body_length] + "..."
    else:
        preview_body = body

    # Create message for Telegram (Markdown)
    telegram_message = f"*{subject}*\n\n{preview_body}"

    # Create message for Web Push
    push_message = {
        "title": subject,
        "body": preview_body,
        "icon": "/static/images/indico_square.png",  # Default Indico icon
        "badge": "/static/images/indico_badge.png",
    }

    # Add event URL if available
    if context.get("event_url"):
        telegram_message += f"\n\n[📅 Open event]({context['event_url']})"
        push_message["data"] = {"url": context["event_url"]}

    return {
        "telegram": telegram_message,
        "push": push_message,
        "context": context,
    }


def send_user_notification(user: User, formatted_message: Dict) -> Dict:
    """Send notification to user through all enabled channels."""
    results = {
        "telegram": {"sent": False, "error": None},
        "push": {"sent": False, "error": None},
    }

    # Send Telegram notification
    from .models import get_telegram_settings

    telegram_settings = get_telegram_settings(user)
    telegram_enabled = telegram_settings.get("enabled", False)
    telegram_chat_id = telegram_settings.get("chat_id")

    if telegram_enabled and telegram_chat_id:
        try:
            success = send_telegram_message(
                chat_id=telegram_chat_id,
                message=formatted_message["telegram"],
                parse_mode="Markdown",
            )
            results["telegram"]["sent"] = success

            # Update last_used timestamp in database
            from datetime import datetime

            from .models import get_or_create_telegram_link

            link = get_or_create_telegram_link(user)
            link.last_used = datetime.utcnow()

        except Exception as e:
            results["telegram"]["error"] = str(e)
            logger.error(f"Failed to send Telegram notification to user {user.id}: {e}")

    # Send Web Push notifications
    push_enabled = push_user_settings.get(user, "push_enabled")
    subscriptions = push_user_settings.get(user, "push_subscriptions") or []

    if push_enabled and subscriptions:
        push_sent = False
        for subscription in subscriptions:
            try:
                success = send_push_notification(
                    subscription=subscription,
                    message=formatted_message["push"],
                )
                if success:
                    push_sent = True
            except Exception as e:
                logger.error(f"Failed to send push notification to user {user.id}: {e}")

        results["push"]["sent"] = push_sent

    # Update last notification time
    if results["telegram"]["sent"] or results["push"]["sent"]:
        push_user_settings.set(user, "last_notification_sent", now_utc())

    return results


def process_notification(email: Dict, **kwargs) -> None:
    """Process an email notification and send push copies."""
    # Check if plugin is enabled
    if not plugin.default_settings.get(
        "telegram_enabled", True
    ) and not plugin.default_settings.get("webpush_enabled", True):
        return

    # Extract recipients
    recipients = get_notification_recipients(email)
    if not recipients:
        return

    # Extract context
    context = extract_notification_context(**kwargs)

    # Format message
    formatted_message = format_notification_message(
        subject=email.get("subject", "Notification"),
        body=email.get("body", ""),
        context=context,
    )

    # Determine notification type from context
    notification_type = context["type"]

    # Send to each recipient
    for user in recipients:
        # Check if we should send notification to this user
        if not should_send_notification(user, notification_type):
            continue

        # Send notification
        results = send_user_notification(user, formatted_message)

        # Log results
        if results["telegram"]["sent"] or results["push"]["sent"]:
            logger.info(
                f"Sent push notification to user {user.id} "
                f"(telegram: {results['telegram']['sent']}, "
                f"push: {results['push']['sent']})"
            )
        else:
            logger.debug(
                f"No push notification sent to user {user.id} "
                f"(channels disabled or failed)"
            )


def send_test_notification(
    user: User, channel: str = "all", message: str = None
) -> Dict:
    """Send a test notification to the user."""
    if message is None:
        message = "This is a test notification from Indico Push Notifications plugin."

    formatted_message = format_notification_message(
        subject="Test Notification",
        body=message,
        context={"type": "test", "event_url": None},
    )

    results = {}

    if channel in ["all", "telegram"]:
        from .models import get_telegram_settings

        telegram_settings = get_telegram_settings(user)
        telegram_enabled = telegram_settings.get("enabled", False)
        telegram_chat_id = telegram_settings.get("chat_id")

        if telegram_enabled and telegram_chat_id:
            try:
                success = send_telegram_message(
                    chat_id=telegram_chat_id,
                    message=formatted_message["telegram"],
                    parse_mode="Markdown",
                )
                results["telegram"] = {"sent": success, "error": None}

                # Update last_used timestamp in database
                from datetime import datetime

                from .models import get_or_create_telegram_link

                link = get_or_create_telegram_link(user)
                link.last_used = datetime.utcnow()

            except Exception as e:
                results["telegram"] = {"sent": False, "error": str(e)}
        else:
            results["telegram"] = {
                "sent": False,
                "error": "Telegram not enabled or not linked",
            }

    if channel in ["all", "push"]:
        push_enabled = push_user_settings.get(user, "push_enabled")
        subscriptions = push_user_settings.get(user, "push_subscriptions") or []

        if push_enabled and subscriptions:
            push_sent = False
            push_errors = []

            for subscription in subscriptions:
                try:
                    success = send_push_notification(
                        subscription=subscription,
                        message=formatted_message["push"],
                    )
                    if success:
                        push_sent = True
                except Exception as e:
                    push_errors.append(str(e))

            results["push"] = {
                "sent": push_sent,
                "error": "; ".join(push_errors) if push_errors else None,
            }
        else:
            results["push"] = {
                "sent": False,
                "error": "Push not enabled or no subscriptions",
            }

    # Update last notification time if any were sent
    if any(r.get("sent", False) for r in results.values()):
        push_user_settings.set(user, "last_notification_sent", now_utc())

    return {
        "success": any(r.get("sent", False) for r in results.values()),
        "results": results,
        "message": "Test notification sent"
        if any(r.get("sent", False) for r in results.values())
        else "No notifications sent",
    }


def cleanup_old_data() -> None:
    """Clean up old linking tokens and expired data."""
    from .telegram_bot import cleanup_expired_tokens

    cleanup_expired_tokens()

    # Could also clean up old push subscriptions here
    logger.info("Cleaned up old push notification data")
