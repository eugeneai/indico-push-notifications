# This file is part of Indico Push Notifications Plugin.
# Copyright (C) 2024 CERN
#
# Indico Push Notifications Plugin is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

from flask import Blueprint, jsonify, request, session
from werkzeug.exceptions import BadRequest, Forbidden

from indico.core.db import db
from indico.modules.users import User
from indico.web.rh import RH

from . import plugin
from .notifications import (
    get_user_preferences,
    send_test_notification,
    update_user_preferences,
)
from .telegram_bot import (
    generate_telegram_link,
    unlink_telegram,
    verify_telegram_linking,
)
from .webpush import (
    delete_push_subscription,
    get_push_subscriptions,
    save_push_subscription,
    send_test_push_notification,
)

# Create blueprint
blueprint = Blueprint(
    "indico_push_notifications",
    __name__,
    url_prefix="/event/<int:event_id>/push-notifications",
)

# Remove event_id from URL pattern for user routes
user_blueprint = Blueprint(
    "indico_push_notifications_user",
    __name__,
    url_prefix="/user/<int:user_id>/push-notifications",
)


class RHPushNotificationsBase(RH):
    """Base class for push notifications RHs."""

    def _check_access(self):
        """Check if user can access push notifications."""
        if not session.user:
            raise Forbidden("Authentication required")
        if session.user.id != self.user.id and not session.user.is_admin:
            raise Forbidden("You can only access your own notifications")


class RHUserPreferences(RHPushNotificationsBase):
    """Get or update user notification preferences."""

    def _process_GET(self):
        """Get user notification preferences."""
        preferences = get_user_preferences(self.user)
        return jsonify(preferences)

    def _process_POST(self):
        """Update user notification preferences."""
        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")

        update_user_preferences(self.user, data)
        db.session.commit()

        return jsonify({"success": True, "message": "Preferences updated"})


class RHTelegramLink(RHPushNotificationsBase):
    """Generate Telegram linking URL."""

    def _process_GET(self):
        """Generate Telegram linking URL."""
        link = generate_telegram_link(self.user)
        return jsonify({"link": link, "success": True})


class RHTelegramUnlink(RHPushNotificationsBase):
    """Unlink Telegram account."""

    def _process_POST(self):
        """Unlink Telegram account."""
        unlink_telegram(self.user)
        db.session.commit()

        return jsonify({"success": True, "message": "Telegram account unlinked"})


class RHTelegramVerify(RHPushNotificationsBase):
    """Verify Telegram linking (called by bot)."""

    # Skip normal access check for bot API
    def _check_access(self):
        pass

    def _check_bot_access(self):
        """Check if request is from authorized bot."""
        # In production, use API key or signature verification
        # For now, allow any request (will be secured in production)
        return True

    def _process_POST(self):
        """Verify Telegram linking token."""
        if not self._check_bot_access():
            raise Forbidden("Unauthorized bot")

        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")

        token = data.get("token")
        chat_id = data.get("chat_id")
        username = data.get("username")

        if not all([token, chat_id]):
            raise BadRequest("Missing required fields")

        success = verify_telegram_linking(token, chat_id, username)
        if success:
            db.session.commit()

        return jsonify({"success": success})


class RHPushSubscribe(RHPushNotificationsBase):
    """Save Web Push subscription."""

    def _process_POST(self):
        """Save Web Push subscription."""
        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")

        subscription = data.get("subscription")
        if not subscription:
            raise BadRequest("No subscription provided")

        save_push_subscription(self.user, subscription)
        db.session.commit()

        return jsonify({"success": True, "message": "Subscription saved"})


class RHPushUnsubscribe(RHPushNotificationsBase):
    """Delete Web Push subscription."""

    def _process_POST(self):
        """Delete Web Push subscription."""
        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")

        endpoint = data.get("endpoint")
        if not endpoint:
            raise BadRequest("No endpoint provided")

        delete_push_subscription(self.user, endpoint)
        db.session.commit()

        return jsonify({"success": True, "message": "Subscription deleted"})


class RHPushSubscriptions(RHPushNotificationsBase):
    """Get user's Web Push subscriptions."""

    def _process_GET(self):
        """Get user's Web Push subscriptions."""
        subscriptions = get_push_subscriptions(self.user)
        return jsonify({"subscriptions": subscriptions})


class RHTestNotification(RHPushNotificationsBase):
    """Send test notification."""

    def _process_POST(self):
        """Send test notification."""
        data = request.get_json() or {}
        channel = data.get("channel", "all")  # telegram, push, or all
        message = data.get("message", "Test notification from Indico")

        result = send_test_notification(self.user, channel, message)
        return jsonify(result)


class RHTestPushNotification(RHPushNotificationsBase):
    """Send test Web Push notification."""

    def _process_POST(self):
        """Send test Web Push notification."""
        data = request.get_json() or {}
        message = data.get("message", "Test push notification from Indico")

        result = send_test_push_notification(self.user, message)
        return jsonify(result)


# Register user routes
with user_blueprint.add_url_rule(
    "/preferences", "user_preferences", RHUserPreferences, methods=["GET", "POST"]
):
    pass

with user_blueprint.add_url_rule(
    "/telegram/link", "telegram_link", RHTelegramLink, methods=["GET"]
):
    pass

with user_blueprint.add_url_rule(
    "/telegram/unlink", "telegram_unlink", RHTelegramUnlink, methods=["POST"]
):
    pass

with user_blueprint.add_url_rule(
    "/telegram/verify", "telegram_verify", RHTelegramVerify, methods=["POST"]
):
    pass

with user_blueprint.add_url_rule(
    "/push/subscribe", "push_subscribe", RHPushSubscribe, methods=["POST"]
):
    pass

with user_blueprint.add_url_rule(
    "/push/unsubscribe", "push_unsubscribe", RHPushUnsubscribe, methods=["POST"]
):
    pass

with user_blueprint.add_url_rule(
    "/push/subscriptions", "push_subscriptions", RHPushSubscriptions, methods=["GET"]
):
    pass

with user_blueprint.add_url_rule(
    "/test", "test_notification", RHTestNotification, methods=["POST"]
):
    pass

with user_blueprint.add_url_rule(
    "/test/push", "test_push_notification", RHTestPushNotification, methods=["POST"]
):
    pass

# Register both blueprints
__all__ = ["blueprint", "user_blueprint"]
