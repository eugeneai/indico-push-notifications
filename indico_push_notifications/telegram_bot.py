# This file is part of Indico Push Notifications Plugin.
# Copyright (C) 2024 CERN
#
# Indico Push Notifications Plugin is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import requests
from flask import current_app
from indico.core.db import db
from indico.modules.users import User
from indico.util.date_time import now_utc

from . import plugin
from .models import (
    TelegramUserLink,
    find_user_by_telegram_chat_id,
    find_user_by_telegram_token,
    get_or_create_telegram_link,
    remove_telegram_link,
    set_telegram_linking_token,
    update_telegram_link,
)
from .notifications import push_user_settings

logger = logging.getLogger(__name__)

# Telegram Bot API base URL
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/{method}"


def get_bot_token() -> Optional[str]:
    """Get Telegram bot token from plugin settings."""
    return plugin.default_settings.get("telegram_bot_token")


def get_bot_username() -> Optional[str]:
    """Get Telegram bot username from plugin settings."""
    return plugin.default_settings.get("telegram_bot_username")


def is_telegram_enabled() -> bool:
    """Check if Telegram notifications are enabled."""
    return plugin.default_settings.get("telegram_enabled", True) and bool(
        get_bot_token()
    )


def call_telegram_api(method: str, data: Dict = None, files: Dict = None) -> Dict:
    """Make a call to Telegram Bot API."""
    token = get_bot_token()
    if not token:
        raise ValueError("Telegram bot token not configured")

    url = TELEGRAM_API_URL.format(token=token, method=method)

    try:
        if files:
            response = requests.post(url, data=data, files=files, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)

        response.raise_for_status()
        result = response.json()

        if not result.get("ok"):
            logger.error(f"Telegram API error: {result}")
            raise Exception(f"Telegram API error: {result.get('description')}")

        return result.get("result", {})

    except requests.exceptions.RequestException as e:
        logger.error(f"Telegram API request failed: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Telegram API response: {e}")
        raise


def send_telegram_message(
    chat_id: str,
    message: str,
    parse_mode: str = None,
    disable_web_page_preview: bool = True,
    reply_markup: Dict = None,
) -> bool:
    """Send a message to a Telegram chat."""
    if not is_telegram_enabled():
        logger.warning("Telegram notifications are disabled")
        return False

    data = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": disable_web_page_preview,
    }

    if parse_mode:
        data["parse_mode"] = parse_mode

    if reply_markup:
        data["reply_markup"] = reply_markup

    try:
        result = call_telegram_api("sendMessage", data)
        logger.debug(f"Telegram message sent to {chat_id}: {result.get('message_id')}")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
        return False


def generate_telegram_link(user: User) -> Optional[str]:
    """Generate a Telegram linking URL for a user."""
    if not is_telegram_enabled():
        return None

    # Generate unique token
    token = secrets.token_urlsafe(32)
    expires = now_utc() + timedelta(hours=1)

    # Save token for verification
    push_user_settings.set(user, "telegram_linking_token", token)
    push_user_settings.set(user, "telegram_linking_expires", expires)

    # Also save in database for querying
    set_telegram_linking_token(user, token, expires)

    # Get bot username
    bot_username = get_bot_username()
    if not bot_username:
        logger.error("Telegram bot username not configured")
        return None

    # Remove @ if present
    if bot_username.startswith("@"):
        bot_username = bot_username[1:]

    # Generate deep link
    deep_link = f"https://t.me/{bot_username}?start={token}"

    logger.info(f"Generated Telegram link for user {user.id}: {deep_link}")
    return deep_link


def verify_telegram_linking(token: str, chat_id: str, username: str = None) -> bool:
    """Verify Telegram linking token and link account."""
    if not is_telegram_enabled():
        return False

    # Find user by token
    user = find_user_by_telegram_token(token)
    if not user:
        return False

    # Check if token is expired
    expires = push_user_settings.get(user, "telegram_linking_expires")
    if expires and expires < now_utc():
        logger.warning(f"Expired linking token for user {user.id}")
        # Clean up expired token
        push_user_settings.set(user, "telegram_linking_token", None)
        push_user_settings.set(user, "telegram_linking_expires", None)
        return False

    # Link Telegram account
    push_user_settings.set_multi(
        user,
        {
            "telegram_chat_id": chat_id,
            "telegram_username": username,
            "telegram_enabled": True,
            "telegram_linking_token": None,  # Clear token
            "telegram_linking_expires": None,  # Clear expiration
        },
    )

    # Send welcome message
    welcome_message = (
        "✅ *Account linked successfully!*\n\n"
        "Your Telegram account has been linked to your Indico profile. "
        "You will now receive notifications about:\n"
        "• New events\n"
        "• Registration confirmations\n"
        "• Abstract submissions\n"
        "• Reminders\n\n"
        "Use /help to see available commands."
    )

    try:
        send_telegram_message(
            chat_id=chat_id,
            message=welcome_message,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Failed to send welcome message to {chat_id}: {e}")

    logger.info(f"Linked Telegram account {chat_id} to user {user.id}")
    return True


def find_user_by_linking_token(token: str) -> Optional[User]:
    """Find user by Telegram linking token."""
    # Use model helper function
    return find_user_by_telegram_token(token)


def find_user_by_chat_id(chat_id: str) -> Optional[User]:
    """Find user by Telegram chat ID."""
    # Use model helper function
    return find_user_by_telegram_chat_id(chat_id)


def unlink_telegram(user: User) -> bool:
    """Unlink Telegram account from user."""
    chat_id = push_user_settings.get(user, "telegram_chat_id")

    # Send goodbye message if possible
    if chat_id:
        goodbye_message = (
            "👋 *Account unlinked*\n\n"
            "Your Telegram account has been unlinked from your Indico profile. "
            "You will no longer receive notifications.\n\n"
            "To link again, visit your Indico profile settings."
        )

        try:
            send_telegram_message(
                chat_id=chat_id,
                message=goodbye_message,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.debug(
                f"Could not send goodbye message (account already unlinked): {e}"
            )

    # Clear Telegram settings
    push_user_settings.set_multi(
        user,
        {
            "telegram_chat_id": None,
            "telegram_username": None,
            "telegram_enabled": False,
            "telegram_linking_token": None,
            "telegram_linking_expires": None,
        },
    )

    logger.info(f"Unlinked Telegram account from user {user.id}")
    return True


def get_telegram_chat_info(chat_id: str) -> Optional[Dict]:
    """Get information about a Telegram chat."""
    if not is_telegram_enabled():
        return None

    try:
        result = call_telegram_api("getChat", {"chat_id": chat_id})
        return result
    except Exception as e:
        logger.error(f"Failed to get chat info for {chat_id}: {e}")
        return None


def get_telegram_link(user: User) -> Optional[TelegramUserLink]:
    """Get Telegram link for user from database."""
    return TelegramUserLink.query.filter_by(user_id=user.id).first()


def set_webhook(url: str) -> bool:
    """Set Telegram webhook URL for receiving updates."""
    if not is_telegram_enabled():
        return False

    try:
        result = call_telegram_api("setWebhook", {"url": url})
        logger.info(f"Telegram webhook set to: {url}")
        return True
    except Exception as e:
        logger.error(f"Failed to set Telegram webhook: {e}")
        return False


def delete_webhook() -> bool:
    """Delete Telegram webhook."""
    if not is_telegram_enabled():
        return False

    try:
        result = call_telegram_api("deleteWebhook")
        logger.info("Telegram webhook deleted")
        return True
    except Exception as e:
        logger.error(f"Failed to delete Telegram webhook: {e}")
        return False


def get_webhook_info() -> Optional[Dict]:
    """Get current webhook information."""
    if not is_telegram_enabled():
        return None

    try:
        result = call_telegram_api("getWebhookInfo")
        return result
    except Exception as e:
        logger.error(f"Failed to get webhook info: {e}")
        return None


def process_telegram_update(update: Dict) -> None:
    """Process incoming Telegram update (webhook or polling)."""
    if not is_telegram_enabled():
        return

    # Handle different update types
    if "message" in update:
        process_message(update["message"])
    elif "callback_query" in update:
        process_callback_query(update["callback_query"])


def process_message(message: Dict) -> None:
    """Process incoming Telegram message."""
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    user_info = message.get("from", {})

    if not text:
        return

    # Handle commands
    if text.startswith("/"):
        command = text.split()[0].lower()
        handle_command(chat_id, command, text, user_info)


def handle_command(chat_id: str, command: str, full_text: str, user_info: Dict) -> None:
    """Handle Telegram bot commands."""
    username = user_info.get("username")
    user_id = user_info.get("id")

    if command == "/start":
        handle_start_command(chat_id, full_text, username)
    elif command == "/help":
        handle_help_command(chat_id)
    elif command == "/status":
        handle_status_command(chat_id)
    elif command == "/unlink":
        handle_unlink_command(chat_id)
    elif command == "/preferences":
        handle_preferences_command(chat_id)
    else:
        handle_unknown_command(chat_id)


def handle_start_command(chat_id: str, full_text: str, username: str = None) -> None:
    """Handle /start command with optional token."""
    parts = full_text.split()
    if len(parts) > 1:
        # /start <token> - linking account
        token = parts[1]
        success = verify_telegram_linking(token, chat_id, username)

        if success:
            message = (
                "✅ *Welcome!*\n\n"
                "Your Telegram account has been successfully linked to your Indico profile. "
                "You will now receive notifications about events, registrations, and more.\n\n"
                "Use /help to see available commands."
            )
        else:
            message = (
                "❌ *Linking failed*\n\n"
                "The linking token is invalid or has expired. "
                "Please generate a new link from your Indico profile settings."
            )
    else:
        # Just /start - show welcome message
        message = (
            "👋 *Hello!*\n\n"
            "I'm the Indico notification bot. "
            "I can send you notifications about events, registrations, abstracts, and reminders.\n\n"
            "To get started, you need to link your Telegram account to your Indico profile:\n"
            "1. Go to your Indico profile settings\n"
            "2. Find the 'Notifications' section\n"
            "3. Click 'Link Telegram account'\n"
            "4. Use the provided link to connect with me\n\n"
            "Use /help to see all available commands."
        )

    send_telegram_message(
        chat_id=chat_id,
        message=message,
        parse_mode="Markdown",
    )


def handle_help_command(chat_id: str) -> None:
    """Handle /help command."""
    message = (
        "📚 *Available commands:*\n\n"
        "*/start* - Start the bot or link your account\n"
        "*/help* - Show this help message\n"
        "*/status* - Check your notification status\n"
        "*/unlink* - Unlink your Telegram account\n"
        "*/preferences* - Manage notification preferences\n\n"
        "To change notification settings, please visit your Indico profile."
    )

    send_telegram_message(
        chat_id=chat_id,
        message=message,
        parse_mode="Markdown",
    )


def handle_status_command(chat_id: str) -> None:
    """Handle /status command."""
    # Find user by chat_id
    user = find_user_by_chat_id(chat_id)

    if user:
        from .notifications import get_user_preferences

        prefs = get_user_preferences(user)

        status = "✅ Enabled" if prefs["telegram"]["enabled"] else "❌ Disabled"
        last_notification = prefs.get("last_notification", "Never") or "Never"

        message = (
            f"📊 *Your notification status:*\n\n"
            f"• Account: @{prefs['telegram']['username'] or 'Not set'}\n"
            f"• Telegram notifications: {status}\n"
            f"• Push notifications: {'✅ Enabled' if prefs['push']['enabled'] else '❌ Disabled'}\n"
            f"• Last notification: {last_notification}\n\n"
            f"Use /preferences to manage your settings."
        )
    else:
        message = (
            "❌ *Account not linked*\n\n"
            "Your Telegram account is not linked to any Indico profile. "
            "Use /start with a linking token from your Indico settings."
        )

    send_telegram_message(
        chat_id=chat_id,
        message=message,
        parse_mode="Markdown",
    )


def handle_unlink_command(chat_id: str) -> None:
    """Handle /unlink command."""
    user = find_user_by_chat_id(chat_id)

    if user:
        # Create confirmation keyboard
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Yes, unlink", "callback_data": "unlink_confirm"},
                    {"text": "❌ Cancel", "callback_data": "unlink_cancel"},
                ]
            ]
        }

        message = (
            "⚠️ *Confirm unlinking*\n\n"
            "Are you sure you want to unlink your Telegram account from Indico?\n\n"
            "You will stop receiving all notifications."
        )

        send_telegram_message(
            chat_id=chat_id,
            message=message,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    else:
        message = "Your account is not linked to Indico."

        send_telegram_message(
            chat_id=chat_id,
            message=message,
            parse_mode="Markdown",
        )


def handle_preferences_command(chat_id: str) -> None:
    """Handle /preferences command."""
    user = find_user_by_chat_id(chat_id)

    if user:
        from .notifications import get_user_preferences

        prefs = get_user_preferences(user)

        # Create preferences keyboard
        keyboard = {"inline_keyboard": []}

        for pref_name, pref_value in prefs["preferences"].items():
            emoji = "✅" if pref_value else "❌"
            callback_data = f"pref_toggle_{pref_name}"
            keyboard["inline_keyboard"].append(
                [{"text": f"{emoji} {pref_name}", "callback_data": callback_data}]
            )

        message = (
            "⚙️ *Notification preferences*\n\n"
            "Toggle preferences by clicking the buttons below:\n\n"
            "Changes will take effect immediately."
        )

        send_telegram_message(
            chat_id=chat_id,
            message=message,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    else:
        message = "Please link your account first using /start."

        send_telegram_message(
            chat_id=chat_id,
            message=message,
            parse_mode="Markdown",
        )


def handle_unknown_command(chat_id: str) -> None:
    """Handle unknown commands."""
    message = (
        "🤔 *Unknown command*\n\n"
        "I don't recognize that command. Use /help to see available commands."
    )

    send_telegram_message(
        chat_id=chat_id,
        message=message,
        parse_mode="Markdown",
    )


def process_callback_query(callback_query: Dict) -> None:
    """Process callback query from inline keyboard."""
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    data = callback_query.get("data", "")
    query_id = callback_query.get("id")

    if not data or not chat_id:
        return

    # Answer callback query (remove loading animation)
    try:
        call_telegram_api("answerCallbackQuery", {"callback_query_id": query_id})
    except Exception:
        pass  # Ignore errors in answering callback

    # Handle different callback actions
    if data == "unlink_confirm":
        handle_unlink_confirm(chat_id)
    elif data == "unlink_cancel":
        handle_unlink_cancel(chat_id)
    elif data.startswith("pref_toggle_"):
        pref_name = data[12:]  # Remove "pref_toggle_" prefix
        handle_preference_toggle(chat_id, pref_name)


def handle_unlink_confirm(chat_id: str) -> None:
    """Handle unlink confirmation."""
    user = find_user_by_chat_id(chat_id)
    if user:
        unlink_telegram(user)
        db.session.commit()

        message = "✅ Your account has been unlinked from Indico."
    else:
        message = "❌ Account not found."

    send_telegram_message(
        chat_id=chat_id,
        message=message,
        parse_mode="Markdown",
    )


def handle_unlink_cancel(chat_id: str) -> None:
    """Handle unlink cancellation."""
    message = "Unlinking cancelled. Your account remains linked."

    send_telegram_message(
        chat_id=chat_id,
        message=message,
        parse_mode="Markdown",
    )


def handle_preference_toggle(chat_id: str, pref_name: str) -> None:
    """Handle preference toggle."""
    user = find_user_by_chat_id(chat_id)
    if not user:
        send_telegram_message(
            chat_id=chat_id,
            message="Please link your account first using /start.",
            parse_mode="Markdown",
        )
        return

    # Get current preferences
    prefs = push_user_settings.get(user, "notification_preferences")
    if prefs is None:
        prefs = plugin.default_settings.get("default_notification_preferences", {})

    # Toggle preference
    if pref_name in prefs:
        prefs[pref_name] = not prefs[pref_name]
        push_user_settings.set(user, "notification_preferences", prefs)
        db.session.commit()

        # Update message with new state
        emoji = "✅" if prefs[pref_name] else "❌"
        message = f"{emoji} *{pref_name}* is now {'enabled' if prefs[pref_name] else 'disabled'}."

        send_telegram_message(
            chat_id=chat_id,
            message=message,
            parse_mode="Markdown",
        )
    else:
        send_telegram_message(
            chat_id=chat_id,
            message=f"Unknown preference: {pref_name}",
            parse_mode="Markdown",
        )


def cleanup_expired_tokens() -> None:
    """Clean up expired linking tokens."""
    from indico.core.db import db

    # Find all users with expired tokens
    users = User.query.all()
    cleaned_count = 0

    for user in users:
        expires = push_user_settings.get(user, "telegram_linking_expires")
        if expires and expires < now_utc():
            # Token expired, clean it up
            push_user_settings.set(user, "telegram_linking_token", None)
            push_user_settings.set(user, "telegram_linking_expires", None)
            cleaned_count += 1

    if cleaned_count > 0:
        db.session.commit()
        logger.info(f"Cleaned up {cleaned_count} expired Telegram linking tokens")


def get_bot() -> Dict:
    """Get bot information."""
    if not is_telegram_enabled():
        return {"enabled": False}

    try:
        bot_info = call_telegram_api("getMe")
        return {
            "enabled": True,
            "username": bot_info.get("username"),
            "name": bot_info.get("first_name"),
            "id": bot_info.get("id"),
        }
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
        return {"enabled": False, "error": str(e)}


def start_polling() -> None:
    """Start polling for Telegram updates (for development)."""
    if not is_telegram_enabled():
        logger.warning("Telegram not enabled, skipping polling")
        return

    logger.info("Starting Telegram bot polling...")
    offset = 0

    while True:
        try:
            # Get updates
            updates = call_telegram_api("getUpdates", {"offset": offset, "timeout": 30})

            for update in updates:
                offset = update["update_id"] + 1
                process_telegram_update(update)

        except Exception as e:
            logger.error(f"Error in Telegram polling: {e}")
            import time

            time.sleep(5)
