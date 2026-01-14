#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example usage of Indico Push Notifications Plugin

This script demonstrates how to use the plugin's API and functionality.
It can be used for testing and as a reference for integration.
"""

import json
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def example_user_preferences():
    """Example: Working with user preferences."""
    print_header("User Preferences Example")

    # In a real Indico environment, you would import and use:
    # from indico_push_notifications.notifications import (
    #     get_user_preferences,
    #     update_user_preferences
    # )

    example_preferences = {
        "telegram": {
            "chat_id": "123456789",
            "username": "@example_user",
            "enabled": True,
            "linked": True
        },
        "push": {
            "enabled": True,
            "subscriptions_count": 2
        },
        "preferences": {
            "event_creation": True,
            "event_update": True,
            "registration_open": True,
            "registration_confirmation": False,
            "abstract_submission": True,
            "abstract_review": False,
            "reminder": True
        }
    }

    print("Example user preferences structure:")
    print(json.dumps(example_preferences, indent=2))

    # Example of updating preferences
    update_data = {
        "telegram_enabled": False,
        "push_enabled": True,
        "preferences": {
            "event_creation": True,
            "registration_open": False
        }
    }

    print("\nExample update data:")
    print(json.dumps(update_data, indent=2))


def example_notification_formatting():
    """Example: Formatting notifications for different channels."""
    print_header("Notification Formatting Example")

    # Example notification data
    subject = "New Event: CERN Open Day 2024"
    body = """The CERN Open Day 2024 has been scheduled for October 5th, 2024.

Join us for a day of scientific discovery, laboratory tours, and interactive exhibits.
All employees and their families are welcome!

Location: CERN Main Building
Time: 10:00 - 18:00"""

    context = {
        "type": "event_creation",
        "event_id": 12345,
        "event_url": "https://indico.example.com/event/12345",
        "source": "event_manager"
    }

    print("Original notification:")
    print(f"Subject: {subject}")
    print(f"Body: {body[:100]}...")
    print(f"Context: {json.dumps(context, indent=2)}")

    # In a real environment, you would use:
    # from indico_push_notifications.notifications import format_notification_message
    # formatted = format_notification_message(subject, body, context)

    example_formatted = {
        "telegram": "*New Event: CERN Open Day 2024*\n\nThe CERN Open Day 2024 has been scheduled for October 5th, 2024.\n\nJoin us for a day of scientific discovery, laboratory tours, and interactive exhibits.\nAll employees and their families are welcome!\n\nLocation: CERN Main Building\nTime: 10:00 - 18:00\n\n[📅 Open event](https://indico.example.com/event/12345)",
        "push": {
            "title": "New Event: CERN Open Day 2024",
            "body": "The CERN Open Day 2024 has been scheduled for October 5th, 2024.\n\nJoin us for a day of scientific discovery, laboratory tours, and interactive exhibits.\nAll employees and their families are welcome!\n\nLocation: CERN Main Building\nTime: 10:00 - 18:00",
            "icon": "/static/images/indico_square.png",
            "badge": "/static/images/indico_badge.png",
            "data": {
                "url": "https://indico.example.com/event/12345"
            }
        },
        "context": context
    }

    print("\nFormatted for Telegram (Markdown):")
    print(example_formatted["telegram"][:200] + "...")

    print("\nFormatted for Web Push:")
    print(json.dumps(example_formatted["push"], indent=2))


def example_telegram_linking():
    """Example: Telegram account linking process."""
    print_header("Telegram Linking Example")

    # Step 1: Generate linking URL
    linking_token = "ABC123DEF456"
    bot_username = "@IndicoBot"
    linking_url = f"https://t.me/{bot_username.lstrip('@')}?start={linking_token}"

    print("Step 1: Generate linking URL")
    print(f"Token: {linking_token}")
    print(f"Bot: {bot_username}")
    print(f"URL: {linking_url}")

    # Step 2: User clicks link and starts bot
    print("\nStep 2: User interaction in Telegram")
    print("User opens Telegram and clicks the link")
    print("Bot sends: 'Hello! Please send /start to link your account'")
    print("User sends: /start ABC123DEF456")

    # Step 3: Bot verifies token with Indico
    verification_data = {
        "token": linking_token,
        "chat_id": "987654321",
        "username": "@example_user"
    }

    print("\nStep 3: Bot verification request")
    print(f"POST /api/telegram/verify")
    print(f"Data: {json.dumps(verification_data, indent=2)}")

    # Step 4: Indico responds
    verification_response = {
        "success": True,
        "message": "Telegram account linked successfully"
    }

    print("\nStep 4: Indico response")
    print(f"Response: {json.dumps(verification_response, indent=2)}")

    # Step 5: Bot confirms to user
    print("\nStep 5: Bot confirmation")
    print("Bot sends: '✅ Your Telegram account has been linked to Indico!'")


def example_webpush_subscription():
    """Example: Web Push subscription flow."""
    print_header("Web Push Subscription Example")

    # Example subscription data from browser
    example_subscription = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/abc123def456",
        "keys": {
            "auth": "ABC123DEF456GHI789",
            "p256dh": "JKL012MNO345PQR678"
        },
        "browser": "Chrome",
        "platform": "Linux x86_64",
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "created": "2024-01-15T10:30:00Z"
    }

    print("Browser generates subscription:")
    print(json.dumps(example_subscription, indent=2))

    # Send to server
    print("\nSending to Indico API:")
    print("POST /api/push/subscribe")
    print(f"Data: {{'subscription': {{...}}}}")

    # Server response
    server_response = {
        "success": True,
        "message": "Subscription saved",
        "vapid_public_key": "BP4...public...key"
    }

    print("\nServer response:")
    print(json.dumps(server_response, indent=2))


def example_api_endpoints():
    """Example: Available API endpoints."""
    print_header("API Endpoints Example")

    endpoints = [
        {
            "method": "GET",
            "path": "/api/user/{user_id}/push-notifications/preferences",
            "description": "Get user notification preferences",
            "response": "User preferences object"
        },
        {
            "method": "POST",
            "path": "/api/user/{user_id}/push-notifications/preferences",
            "description": "Update user preferences",
            "request": "JSON with preferences",
            "response": "Success status"
        },
        {
            "method": "GET",
            "path": "/api/user/{user_id}/push-notifications/telegram/link",
            "description": "Generate Telegram linking URL",
            "response": "URL for Telegram bot"
        },
        {
            "method": "POST",
            "path": "/api/user/{user_id}/push-notifications/telegram/unlink",
            "description": "Unlink Telegram account",
            "response": "Success status"
        },
        {
            "method": "POST",
            "path": "/api/user/{user_id}/push-notifications/push/subscribe",
            "description": "Save Web Push subscription",
            "request": "Subscription object",
            "response": "Success status"
        },
        {
            "method": "POST",
            "path": "/api/user/{user_id}/push-notifications/push/unsubscribe",
            "description": "Delete Web Push subscription",
            "request": "Endpoint URL",
            "response": "Success status"
        },
        {
            "method": "GET",
            "path": "/api/user/{user_id}/push-notifications/push/subscriptions",
            "description": "Get user's Web Push subscriptions",
            "response": "List of subscriptions"
        },
        {
            "method": "POST",
            "path": "/api/user/{user_id}/push-notifications/test",
            "description": "Send test notification",
            "request": "Channel and message (optional)",
            "response": "Test results"
        }
    ]

    print("Available API endpoints:")
    for endpoint in endpoints:
        print(f"\n{endpoint['method']} {endpoint['path']}")
        print(f"  {endpoint['description']}")
        if 'request' in endpoint:
            print(f"  Request: {endpoint['request']}")
        print(f"  Response: {endpoint['response']}")


def example_integration_with_indico():
    """Example: Integration with Indico's notification system."""
    print_header("Indico Integration Example")

    print("1. Indico sends an email notification:")
    email_notification = {
        "to": ["user@example.com"],
        "cc": [],
        "bcc": [],
        "subject": "Registration confirmed for CERN Open Day 2024",
        "body": "Your registration for CERN Open Day 2024 has been confirmed...",
        "html": "<p>Your registration for CERN Open Day 2024 has been confirmed...</p>"
    }

    print(json.dumps(email_notification, indent=2))

    print("\n2. Plugin intercepts the notification:")
    print("   - Extracts recipient emails")
    print("   - Finds corresponding Indico users")
    print("   - Checks user notification preferences")
    print("   - Formats message for each enabled channel")
    print("   - Sends push notifications")

    print("\n3. Notification results:")
    results = {
        "user_123": {
            "telegram": {"sent": True, "error": None},
            "push": {"sent": True, "error": None}
        },
        "user_456": {
            "telegram": {"sent": False, "error": "Not linked"},
            "push": {"sent": True, "error": None}
        }
    }

    print(json.dumps(results, indent=2))


def example_configuration():
    """Example: Plugin configuration."""
    print_header("Configuration Example")

    # Plugin settings in indico.conf
    indico_conf_example = """
# Indico Configuration for Push Notifications Plugin
ENABLED_PLUGINS = ['indico_push_notifications']

# Telegram Bot Configuration
PUSH_NOTIFICATIONS_TELEGRAM_BOT_TOKEN = "......"
PUSH_NOTIFICATIONS_TELEGRAM_BOT_USERNAME = "@IndicoBot"

# Web Push VAPID Configuration
PUSH_NOTIFICATIONS_VAPID_PUBLIC_KEY = "BP4...public...key"
PUSH_NOTIFICATIONS_VAPID_PRIVATE_KEY = "private...key"
PUSH_NOTIFICATIONS_VAPID_EMAIL = "admin@example.com"
"""

    print("indico.conf settings:")
    print(indico_conf_example)

    # Default plugin settings
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
        }
    }

    print("\nDefault plugin settings:")
    print(json.dumps(default_settings, indent=2))


def main():
    """Run all examples."""
    print("Indico Push Notifications Plugin - Usage Examples")
    print("=" * 60)

    example_configuration()
    example_user_preferences()
    example_notification_formatting()
    example_telegram_linking()
    example_webpush_subscription()
    example_api_endpoints()
    example_integration_with_indico()

    print_header("Summary")
    print("""
The Indico Push Notifications Plugin provides:
1. Telegram notifications with account linking
2. Web Push notifications for browsers
3. Integration with Indico's email notification system
4. User-configurable preferences
5. Comprehensive API for management

To use the plugin:
1. Install with: pip install indico-push-notifications
2. Configure in indico.conf
3. Enable in Indico admin interface
4. Users configure preferences in their profile
""")

    print("\nFor more information, see:")
    print("- README.md for installation and setup")
    print("- tests/ for examples of testing")
    print("- controllers.py for API usage")
    print("- notifications.py for core logic")


if __name__ == "__main__":
    main()
