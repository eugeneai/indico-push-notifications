# This file is part of Indico Push Notifications Plugin.
# Copyright (C) 2024 CERN
#
# Indico Push Notifications Plugin is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

import os
import sys
from datetime import datetime
from pathlib import Path

from indico.core.plugins import IndicoPlugin
from indico.core.signals import plugin

from .logger import get_logger, log_config, log_import, log_plugin_load, log_signal

__all__ = ["IndicoPushNotificationsPlugin"]

# Entry point logging - this runs when plugin is loaded by Indico
try:
    _entry_logger = get_logger("entry_point")
    _entry_logger.info("=" * 60)
    _entry_logger.info("ENTRY POINT: Plugin module imported by Indico")
    _entry_logger.info(f"Module: {__name__}")
    _entry_logger.info(f"File: {__file__}")
    _entry_logger.info(f"Python path: {sys.path}")
    _entry_logger.info("=" * 60)
except Exception as e:
    # Fallback logging if logger fails
    print(f"[ENTRY POINT ERROR] Failed to initialize logger: {e}")


class IndicoPushNotificationsPlugin(IndicoPlugin):
    """Indico Push Notifications Plugin.

    This plugin adds push notifications (Telegram and Web Push) to Indico.
    """

    # Plugin metadata
    name = "indico_push_notifications"
    friendly_name = "Push Notifications"
    description = "Adds Telegram and Web Push notifications to Indico"
    category = "Notification"
    configurable = True
    strict_settings = False

    def __init__(self, *args, **kwargs):
        """Initialize plugin with logging."""
        # Log entry point instantiation
        try:
            entry_logger = get_logger("entry_point")
            entry_logger.info("=" * 60)
            entry_logger.info("ENTRY POINT: Plugin class instantiated by Indico")
            entry_logger.info(f"Class: {self.__class__.__name__}")
            entry_logger.info(f"Args: {args}")
            entry_logger.info(f"Kwargs keys: {list(kwargs.keys())}")
            entry_logger.info("=" * 60)
        except Exception as e:
            print(f"[ENTRY POINT ERROR] Failed to log instantiation: {e}")

        super().__init__(*args, **kwargs)

        # Initialize plugin logger
        self.logger = get_logger()
        self.logger.info("=" * 60)
        self.logger.info(f"PLUGIN CONSTRUCTOR: {self.name}")
        self.logger.info(f"Friendly name: {self.friendly_name}")
        self.logger.info(f"Description: {self.description}")
        self.logger.info(f"Category: {self.category}")
        self.logger.info(f"Configurable: {self.configurable}")
        self.logger.info("=" * 60)

    # Default settings for the plugin
    default_settings = {
        "telegram_bot_token": "",
        "telegram_bot_username": "",
        "vapid_public_key": "",
        "vapid_private_key": "",
        "vapid_email": "",
        "webpush_enabled": True,
        "telegram_enabled": True,
        "default_notification_preferences": {
            "event_creation": True,
            "event_update": True,
            "registration_open": True,
            "registration_confirmation": True,
            "abstract_submission": True,
            "abstract_review": True,
            "reminder": True,
        },
    }

    # Default user settings
    default_user_settings = {
        "telegram_chat_id": None,
        "telegram_username": None,
        "telegram_enabled": False,
        "telegram_linking_token": None,
        "telegram_linking_expires": None,
        "push_enabled": False,
        "push_subscriptions": [],  # List of push subscription objects
        "notification_preferences": None,  # Will use plugin defaults if None
    }

    def init(self):
        """Initialize the plugin."""
        self.logger.info("=" * 60)
        self.logger.info(f"PLUGIN INITIALIZATION STARTED: {self.name}")
        self.logger.info(f"Time: {self._get_timestamp()}")
        self.logger.info(f"Python version: {sys.version}")
        self.logger.info(f"Python executable: {sys.executable}")
        self.logger.info(f"Python path: {sys.path}")
        self.logger.info(f"Current directory: {os.getcwd()}")
        self.logger.info(f"Plugin directory: {Path(__file__).parent}")
        self.logger.info(f"Plugin file: {__file__}")

        # Log environment variables related to Indico
        self.logger.info("Environment check:")
        for key in ["INDICO_CONFIG", "INDICO_DATABASE_URL", "VIRTUAL_ENV"]:
            if key in os.environ:
                self.logger.info(f"  {key}: {os.environ[key]}")
            else:
                self.logger.info(f"  {key}: (not set)")

        super().init()

        self.logger.info("Super().init() completed")

        # Log plugin information
        log_plugin_load(self)

        # Log default settings (masked)
        log_config(self.default_settings, "Default Settings")
        log_config(self.default_user_settings, "Default User Settings")

        # Import here to avoid circular imports
        self.logger.info("Starting module imports...")

        try:
            from . import blueprint

            log_import("blueprint", success=True)
        except ImportError as e:
            log_import("blueprint", success=False, error=str(e))
            self.logger.exception("Failed to import blueprint")
            raise

        try:
            from . import notifications

            log_import("notifications", success=True)
        except ImportError as e:
            log_import("notifications", success=False, error=str(e))
            self.logger.exception("Failed to import notifications")
            raise

        try:
            from . import telegram_bot

            log_import("telegram_bot", success=True)
        except ImportError as e:
            log_import("telegram_bot", success=False, error=str(e))
            self.logger.warning("Failed to import telegram_bot (optional)")

        try:
            from . import webpush

            log_import("webpush", success=True)
        except ImportError as e:
            log_import("webpush", success=False, error=str(e))
            self.logger.warning("Failed to import webpush (optional)")

        self.logger.info("All module imports completed")

        # Connect signals
        self.logger.info("Connecting signals...")
        self.connect_signals()
        self.logger.info("=" * 60)
        self.logger.info(f"PLUGIN INITIALIZATION COMPLETED: {self.name}")

    def connect_signals(self):
        """Connect plugin signals."""
        self.logger.info("Starting signal connections...")

        from indico.core import signals

        # Connect to notification sending
        try:
            signals.core.before_notification_send.connect(
                self._intercept_notifications, sender=None, weak=False
            )
            log_signal("core.before_notification_send", connected=True)
            self.logger.info("Connected to before_notification_send signal")
        except Exception as e:
            self.logger.error(f"Failed to connect to before_notification_send: {e}")

        # Connect to user profile menu
        try:
            signals.menu.items.connect_via("user-profile-sidemenu")(
                self._extend_user_profile_menu
            )
            log_signal("menu.items (user-profile-sidemenu)", connected=True)
            self.logger.info("Connected to user-profile-sidemenu signal")
        except Exception as e:
            self.logger.error(f"Failed to connect to user-profile-sidemenu: {e}")

        # Connect to get_blueprints signal
        try:
            plugin.get_blueprints.connect(self._get_blueprints, sender=self)
            log_signal("plugin.get_blueprints", connected=True)
            self.logger.info("Connected to get_blueprints signal")
        except Exception as e:
            self.logger.error(f"Failed to connect to get_blueprints: {e}")

        self.logger.info("Signal connections completed")

    def _intercept_notifications(self, sender, email, **kwargs):
        """Intercept notifications and send push copies."""
        self.logger.debug(
            f"Intercepting notification: {email.subject if hasattr(email, 'subject') else 'Unknown subject'}"
        )
        try:
            from .notifications import process_notification

            process_notification(email, **kwargs)
            self.logger.debug("Notification processed successfully")
        except Exception as e:
            self.logger.error(f"Failed to process notification: {e}")
            self.logger.exception("Notification processing error")

    def _extend_user_profile_menu(self, sender, user, **kwargs):
        """Add push notifications menu item to user profile."""
        self.logger.debug(
            f"Extending user profile menu for user: {user.id if user else 'None'}"
        )
        try:
            from indico.util.i18n import _
            from indico.web.menu import SideMenuItem

            from .blueprint import blueprint

            yield SideMenuItem(
                "push_notifications",
                _("Notifications"),
                blueprint.name + ".user_preferences",
                weight=55,
                disabled=user.is_system,
            )
            self.logger.debug("User profile menu extended successfully")
        except Exception as e:
            self.logger.error(f"Failed to extend user profile menu: {e}")
            yield None

    def _get_blueprints(self, sender, **kwargs):
        """Register plugin blueprints."""
        self.logger.info("Registering plugin blueprints...")
        try:
            from .blueprint import blueprint, user_blueprint

            self.logger.info(f"Blueprint found: {blueprint.name}")
            self.logger.info(f"User blueprint found: {user_blueprint.name}")
            yield blueprint
            yield user_blueprint
            self.logger.info("Blueprints registered successfully")
        except Exception as e:
            self.logger.error(f"Failed to register blueprints: {e}")
            self.logger.exception("Blueprint registration error")
            yield None

    def get_blueprints(self):
        """Get plugin blueprints (legacy method)."""
        self.logger.info("Getting blueprints (legacy method)")
        try:
            from .blueprint import blueprint, user_blueprint

            self.logger.info(f"Blueprint found: {blueprint.name}")
            self.logger.info(f"User blueprint found: {user_blueprint.name}")
            self.logger.info(f"Returning {blueprint.name}, {user_blueprint.name}")
            return [blueprint, user_blueprint]
        except Exception as e:
            self.logger.error(f"Failed to get blueprints: {e}")
            self.logger.exception("Blueprint error")
            return []

    def register_vapid_credentials(self):
        """Register VAPID credentials for Web Push."""
        self.logger.debug("Registering VAPID credentials")
        try:
            from .webpush import get_vapid_credentials

            credentials = get_vapid_credentials()
            self.logger.debug("VAPID credentials registered successfully")
            return credentials
        except Exception as e:
            self.logger.error(f"Failed to register VAPID credentials: {e}")
            return None

    def get_telegram_bot(self):
        """Get Telegram bot instance."""
        self.logger.debug("Getting Telegram bot instance")
        try:
            from .telegram_bot import get_bot

            bot = get_bot()
            self.logger.debug("Telegram bot retrieved successfully")
            return bot
        except Exception as e:
            self.logger.error(f"Failed to get Telegram bot: {e}")
            return None

    @property
    def user_settings(self):
        """Get user settings proxy."""
        self.logger.debug("Getting user settings proxy")
        try:
            from .notifications import push_user_settings

            self.logger.debug("User settings proxy retrieved successfully")
            return push_user_settings
        except Exception as e:
            self.logger.error(f"Failed to get user settings proxy: {e}")
            return None

    def get_notification_preferences(self, user):
        """Get notification preferences for a user."""
        self.logger.debug(
            f"Getting notification preferences for user: {user.id if user else 'None'}"
        )
        try:
            from .notifications import get_user_preferences

            preferences = get_user_preferences(user)
            self.logger.debug(f"Notification preferences retrieved: {preferences}")
            return preferences
        except Exception as e:
            self.logger.error(f"Failed to get notification preferences: {e}")
            return self.default_settings.get("default_notification_preferences", {})

    def _get_timestamp(self):
        """Get current timestamp for logging."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


# Entry point function that Indico calls
def create_plugin():
    """Create plugin instance - called by Indico entry point."""
    try:
        entry_logger = get_logger("entry_point")
        entry_logger.info("=" * 60)
        entry_logger.info("ENTRY POINT: create_plugin() called by Indico")
        entry_logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        entry_logger.info("Creating plugin instance...")

        plugin = IndicoPushNotificationsPlugin()

        entry_logger.info(f"Plugin created: {plugin.name}")
        entry_logger.info(f"Plugin ID: {id(plugin)}")
        entry_logger.info("=" * 60)

        return plugin
    except Exception as e:
        # Critical error - log to stderr as fallback
        print(f"[CRITICAL ENTRY POINT ERROR] Failed to create plugin: {e}")
        import traceback

        traceback.print_exc()

        # Try to create plugin without logging
        return IndicoPushNotificationsPlugin()
