# This file is part of Indico Push Notifications Plugin.
# Copyright (C) 2024 CERN
#
# Indico Push Notifications Plugin is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

from wtforms import BooleanField, FieldList, FormField, StringField
from wtforms.validators import Optional

from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import IndicoPasswordField, JSONField
from indico.web.forms.validators import HiddenUnless, UsedIf


class NotificationPreferenceForm(IndicoForm):
    """Form for individual notification preference."""

    event_creation = BooleanField(
        "Event creation",
        description="Notifications when new events are created",
        default=True,
    )
    event_update = BooleanField(
        "Event updates",
        description="Notifications when events are updated",
        default=True,
    )
    registration_open = BooleanField(
        "Registration opens",
        description="Notifications when registration opens for events",
        default=True,
    )
    registration_confirmation = BooleanField(
        "Registration confirmations",
        description="Notifications when registrations are confirmed",
        default=True,
    )
    abstract_submission = BooleanField(
        "Abstract submissions",
        description="Notifications when abstracts are submitted",
        default=True,
    )
    abstract_review = BooleanField(
        "Abstract reviews",
        description="Notifications when abstracts are reviewed",
        default=True,
    )
    reminder = BooleanField(
        "Reminders",
        description="Notifications for event reminders",
        default=True,
    )


class TelegramSettingsForm(IndicoForm):
    """Form for Telegram notification settings."""

    enabled = BooleanField(
        "Enable Telegram notifications",
        description="Receive notifications in Telegram",
        default=False,
    )
    username = StringField(
        "Telegram username",
        description="Your Telegram username (read-only)",
        render_kw={"readonly": True},
    )
    chat_id = StringField(
        "Chat ID",
        description="Your Telegram chat ID (read-only)",
        render_kw={"readonly": True},
    )


class WebPushSettingsForm(IndicoForm):
    """Form for Web Push notification settings."""

    enabled = BooleanField(
        "Enable Web Push notifications",
        description="Receive browser push notifications",
        default=False,
    )
    subscriptions_count = StringField(
        "Active subscriptions",
        description="Number of devices registered for push notifications",
        render_kw={"readonly": True},
    )


class UserPreferencesForm(IndicoForm):
    """Main form for user notification preferences."""

    # Telegram settings
    telegram = FormField(
        TelegramSettingsForm,
        label="Telegram Notifications",
        description="Configure Telegram notifications",
    )

    # Web Push settings
    webpush = FormField(
        WebPushSettingsForm,
        label="Web Push Notifications",
        description="Configure browser push notifications",
    )

    # Notification preferences
    preferences = FormField(
        NotificationPreferenceForm,
        label="Notification Preferences",
        description="Choose which types of notifications to receive",
    )

    def __init__(self, *args, **kwargs):
        """Initialize form with user data."""
        super().__init__(*args, **kwargs)
        self._user = kwargs.get("user")

    def populate_from_user(self, user_data):
        """Populate form fields from user data."""
        if not user_data:
            return

        # Telegram data
        if "telegram" in user_data:
            telegram_data = user_data["telegram"]
            self.telegram.enabled.data = telegram_data.get("enabled", False)
            self.telegram.username.data = telegram_data.get("username", "")
            self.telegram.chat_id.data = telegram_data.get("chat_id", "")

        # Web Push data
        if "webpush" in user_data:
            webpush_data = user_data["webpush"]
            self.webpush.enabled.data = webpush_data.get("enabled", False)
            self.webpush.subscriptions_count.data = str(
                webpush_data.get("subscriptions_count", 0)
            )

        # Preferences data
        if "preferences" in user_data:
            preferences_data = user_data["preferences"]
            for field_name in self.preferences._fields:
                if field_name in preferences_data:
                    setattr(
                        self.preferences, field_name, preferences_data[field_name]
                    )

    def to_dict(self):
        """Convert form data to dictionary for saving."""
        data = {
            "telegram_enabled": self.telegram.enabled.data,
            "push_enabled": self.webpush.enabled.data,
            "preferences": {},
        }

        # Add notification preferences
        for field_name in self.preferences._fields:
            field = getattr(self.preferences, field_name)
            data["preferences"][field_name] = field.data

        return data


class AdminSettingsForm(IndicoForm):
    """Form for admin plugin settings."""

    telegram_bot_token = IndicoPasswordField(
        "Telegram Bot Token",
        description="Token for your Telegram bot (from @BotFather)",
        toggle=True,
    )
    telegram_bot_username = StringField(
        "Telegram Bot Username",
        description="Username of your Telegram bot (e.g., @IndicoBot)",
    )
    telegram_enabled = BooleanField(
        "Enable Telegram notifications",
        description="Allow users to receive Telegram notifications",
        default=True,
    )

    vapid_public_key = StringField(
        "VAPID Public Key",
        description="Public key for Web Push authentication",
    )
    vapid_private_key = IndicoPasswordField(
        "VAPID Private Key",
        description="Private key for Web Push authentication",
        toggle=True,
    )
    vapid_email = StringField(
        "VAPID Email",
        description="Email address for VAPID claims (mailto: format)",
        validators=[UsedIf(lambda form, field: form.vapid_public_key.data)],
    )
    webpush_enabled = BooleanField(
        "Enable Web Push notifications",
        description="Allow users to receive browser push notifications",
        default=True,
    )

    # Default notification preferences
    default_event_creation = BooleanField(
        "Event creation (default)",
        description="Default setting for event creation notifications",
        default=True,
    )
    default_event_update = BooleanField(
        "Event updates (default)",
        description="Default setting for event update notifications",
        default=True,
    )
    default_registration_open = BooleanField(
        "Registration opens (default)",
        description="Default setting for registration open notifications",
        default=True,
    )
    default_registration_confirmation = BooleanField(
        "Registration confirmations (default)",
        description="Default setting for registration confirmation notifications",
        default=True,
    )
    default_abstract_submission = BooleanField(
        "Abstract submissions (default)",
        description="Default setting for abstract submission notifications",
        default=True,
    )
    default_abstract_review = BooleanField(
        "Abstract reviews (default)",
        description="Default setting for abstract review notifications",
        default=True,
    )
    default_reminder = BooleanField(
        "Reminders (default)",
        description="Default setting for reminder notifications",
        default=True,
    )

    def populate_from_settings(self, settings):
        """Populate form from plugin settings."""
        if not settings:
            return

        # Telegram settings
        self.telegram_bot_token.data = settings.get("telegram_bot_token", "")
        self.telegram_bot_username.data = settings.get("telegram_bot_username", "")
        self.telegram_enabled.data = settings.get("telegram_enabled", True)

        # Web Push settings
        self.vapid_public_key.data = settings.get("vapid_public_key", "")
        self.vapid_private_key.data = settings.get("vapid_private_key", "")
        self.vapid_email.data = settings.get("vapid_email", "")
        self.webpush_enabled.data = settings.get("webpush_enabled", True)

        # Default preferences
        default_prefs = settings.get("default_notification_preferences", {})
        self.default_event_creation.data = default_prefs.get("event_creation", True)
        self.default_event_update.data = default_prefs.get("event_update", True)
        self.default_registration_open.data = default_prefs.get(
            "registration_open", True
        )
        self.default_registration_confirmation.data = default_prefs.get(
            "registration_confirmation", True
        )
        self.default_abstract_submission.data = default_prefs.get(
            "abstract_submission", True
        )
        self.default_abstract_review.data = default_prefs.get("abstract_review", True)
        self.default_reminder.data = default_prefs.get("reminder", True)

    def to_settings_dict(self):
        """Convert form data to settings dictionary."""
        data = {
            "telegram_bot_token": self.telegram_bot_token.data,
            "telegram_bot_username": self.telegram_bot_username.data,
            "telegram_enabled": self.telegram_enabled.data,
            "vapid_public_key": self.vapid_public_key.data,
            "vapid_private_key": self.vapid_private_key.data,
            "vapid_email": self.vapid_email.data,
            "webpush_enabled": self.webpush_enabled.data,
            "default_notification_preferences": {
                "event_creation": self.default_event_creation.data,
                "event_update": self.default_event_update.data,
                "registration_open": self.default_registration_open.data,
                "registration_confirmation": self.default_registration_confirmation.data,
                "abstract_submission": self.default_abstract_submission.data,
                "abstract_review": self.default_abstract_review.data,
                "reminder": self.default_reminder.data,
            },
        }

        # Only include VAPID email if public key is set
        if not self.vapid_public_key.data:
            data["vapid_email"] = ""

        return data
