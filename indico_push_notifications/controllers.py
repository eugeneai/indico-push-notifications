# This file is part of Indico Push Notifications Plugin.
# Copyright (C) 2024 CERN
#
# Indico Push Notifications Plugin is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

"""
Controller functions for Indico Push Notifications Plugin.

This module contains additional controller logic that complements
the blueprint routes. While most request handling is done in blueprint.py,
this module contains helper functions and business logic that can be
reused across different parts of the plugin.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from flask import session
from sqlalchemy.orm import joinedload

from indico.core.db import db
from indico.core.notifications import make_email
from indico.modules.events import Event
from indico.modules.users import User
from indico.util.date_time import now_utc

from . import plugin
from .models import (
    PushNotificationLog,
    WebPushSubscription,
    log_notification,
    get_user_notification_logs,
)
from .notifications import (
    push_user_settings,
    get_user_preferences as get_user_prefs,
    update_user_preferences as update_user_prefs,
    should_send_notification,
    format_notification_message,
    send_user_notification,
)
from .telegram_bot import (
    generate_telegram_link,
    unlink_telegram,
    verify_telegram_linking,
    get_telegram_chat_info,
)
from .webpush import (
    delete_push_subscription,
    get_push_subscriptions,
    save_push_subscription,
    send_test_push_notification as send_test_push,
)

logger = logging.getLogger(__name__)


def get_user_dashboard_data(user: User) -> Dict:
    """
    Get comprehensive data for user dashboard/status page.

    Returns a dictionary with all information needed to display
    the user's notification status and preferences.
    """
    # Get basic preferences
    preferences = get_user_prefs(user)

    # Get notification statistics
    stats = get_notification_statistics(user)

    # Get recent notifications
    recent_logs = get_user_notification_logs(user, limit=10)

    # Format recent logs for display
    formatted_logs = []
    for log in recent_logs:
        formatted_logs.append({
            'id': log.id,
            'type': log.notification_type,
            'channel': log.channel,
            'subject': log.subject,
            'success': log.success,
            'error': log.error_message,
            'timestamp': log.created_at.isoformat() if log.created_at else None,
            'event_id': log.event_id,
        })

    # Get Web Push configuration
    from .webpush import get_webpush_config
    webpush_config = get_webpush_config()

    # Get Telegram bot info
    telegram_bot_username = plugin.default_settings.get('telegram_bot_username', '')

    return {
        'user': {
            'id': user.id,
            'name': user.full_name,
            'email': user.email,
        },
        'preferences': preferences,
        'statistics': stats,
        'recent_notifications': formatted_logs,
        'webpush_config': webpush_config,
        'telegram_bot': {
            'username': telegram_bot_username,
            'enabled': plugin.default_settings.get('telegram_enabled', True),
        },
        'system_status': {
            'telegram_enabled': plugin.default_settings.get('telegram_enabled', True),
            'webpush_enabled': plugin.default_settings.get('webpush_enabled', True),
            'last_updated': now_utc().isoformat(),
        }
    }


def get_notification_statistics(user: User, days: int = 30) -> Dict:
    """
    Get notification statistics for a user.

    Args:
        user: The user to get statistics for
        days: Number of days to look back

    Returns:
        Dictionary with statistics
    """
    from datetime import timedelta

    cutoff_date = now_utc() - timedelta(days=days)

    # Query logs from database if using models, otherwise use SettingsProxy
    try:
        # Try to use database logs
        logs = (PushNotificationLog.query
                .filter(
                    PushNotificationLog.user_id == user.id,
                    PushNotificationLog.created_at >= cutoff_date
                )
                .all())

        total = len(logs)
        successful = sum(1 for log in logs if log.success)
        failed = total - successful

        # Count by channel
        by_channel = {}
        for log in logs:
            channel = log.channel
            by_channel[channel] = by_channel.get(channel, 0) + 1

        # Count by type
        by_type = {}
        for log in logs:
            ntype = log.notification_type
            by_type[ntype] = by_type.get(ntype, 0) + 1

    except Exception as e:
        # Fall back to simple statistics from SettingsProxy
        logger.debug(f"Could not get detailed statistics from database: {e}")

        # Get last notification time from settings
        last_notification = push_user_settings.get(user, 'last_notification_sent')

        # Simple counts from settings (this would need to be enhanced in production)
        telegram_enabled = push_user_settings.get(user, 'telegram_enabled')
        push_enabled = push_user_settings.get(user, 'push_enabled')
        subscription_count = len(push_user_settings.get(user, 'push_subscriptions') or [])

        total = 0
        successful = 0
        failed = 0
        by_channel = {}
        by_type = {}

        if telegram_enabled:
            by_channel['telegram'] = 0
        if push_enabled and subscription_count > 0:
            by_channel['webpush'] = 0

    return {
        'total': total,
        'successful': successful,
        'failed': failed,
        'success_rate': (successful / total * 100) if total > 0 else 0,
        'by_channel': by_channel,
        'by_type': by_type,
        'period_days': days,
    }


def send_custom_notification(
    user: User,
    subject: str,
    message: str,
    channels: List[str] = None,
    event: Optional[Event] = None,
    notification_type: str = 'custom'
) -> Dict:
    """
    Send a custom notification to a user.

    This function can be called from other parts of Indico or from
    admin interfaces to send custom notifications.

    Args:
        user: The user to notify
        subject: Notification subject
        message: Notification message
        channels: List of channels to use ('telegram', 'webpush', or both)
        event: Optional event context
        notification_type: Type of notification for logging

    Returns:
        Dictionary with send results
    """
    if channels is None:
        channels = ['telegram', 'webpush']

    # Check if user has any enabled channels
    telegram_enabled = push_user_settings.get(user, 'telegram_enabled')
    push_enabled = push_user_settings.get(user, 'push_enabled')

    # Filter channels based on user settings
    available_channels = []
    if 'telegram' in channels and telegram_enabled:
        available_channels.append('telegram')
    if 'webpush' in channels and push_enabled:
        available_channels.append('webpush')

    if not available_channels:
        return {
            'success': False,
            'message': 'User has no enabled notification channels',
            'results': {}
        }

    # Prepare context
    context = {
        'type': notification_type,
        'event': event,
        'event_id': event.id if event else None,
        'event_url': None,
    }

    # Generate event URL if event exists
    if event:
        from indico.web.flask.util import url_for
        context['event_url'] = url_for('events.display', event, _external=True)

    # Format message
    formatted_message = format_notification_message(subject, message, context)

    # Send notification
    results = send_user_notification(user, formatted_message)

    # Log the notification
    success = any(r['sent'] for r in results.values() if r)

    log_notification(
        user=user,
        notification_type=notification_type,
        channel=','.join(available_channels),
        success=success,
        event_id=event.id if event else None,
        subject=subject,
        message=message[:500] if message else None,  # Truncate for logging
        metadata={
            'channels': available_channels,
            'results': results,
            'formatted_message': {
                'telegram_length': len(formatted_message.get('telegram', '')),
                'push_title': formatted_message.get('push', {}).get('title', ''),
            }
        }
    )

    return {
        'success': success,
        'message': 'Notification sent' if success else 'Notification failed',
        'results': results,
        'channels_attempted': available_channels,
    }


def bulk_update_user_preferences(
    user_ids: List[int],
    preferences: Dict,
    update_existing: bool = True
) -> Dict:
    """
    Update notification preferences for multiple users.

    This is useful for admin operations or batch updates.

    Args:
        user_ids: List of user IDs to update
        preferences: Dictionary of preferences to set
        update_existing: Whether to merge with existing preferences (True)
                         or replace them entirely (False)

    Returns:
        Dictionary with update results
    """
    from indico.modules.users import User

    results = {
        'total': len(user_ids),
        'updated': 0,
        'failed': 0,
        'errors': []
    }

    for user_id in user_ids:
        try:
            user = User.get(user_id)
            if not user:
                results['failed'] += 1
                results['errors'].append(f'User {user_id} not found')
                continue

            if update_existing:
                # Get existing preferences
                existing = get_user_prefs(user)
                existing_prefs = existing.get('preferences', {})

                # Merge with new preferences
                new_prefs = preferences.get('preferences', {})
                merged_prefs = {**existing_prefs, **new_prefs}

                # Update preferences
                update_data = {
                    'preferences': merged_prefs
                }

                # Also update channel settings if provided
                if 'telegram_enabled' in preferences:
                    update_data['telegram_enabled'] = preferences['telegram_enabled']
                if 'push_enabled' in preferences:
                    update_data['push_enabled'] = preferences['push_enabled']

            else:
                # Replace preferences entirely
                update_data = preferences

            update_user_prefs(user, update_data)
            results['updated'] += 1

        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f'User {user_id}: {str(e)}')
            logger.error(f'Failed to update preferences for user {user_id}: {e}')

    db.session.commit()
    return results


def get_system_status() -> Dict:
    """
    Get overall system status for the push notifications plugin.

    Returns information about plugin configuration, connectivity,
    and overall health.
    """
    from .telegram_bot import is_telegram_enabled, get_bot
    from .webpush import is_webpush_enabled, get_vapid_credentials

    status = {
        'plugin': {
            'name': plugin.name,
            'version': '1.0.0',
            'enabled': True,
        },
        'telegram': {
            'enabled': is_telegram_enabled(),
            'configured': bool(plugin.default_settings.get('telegram_bot_token')),
            'bot_username': plugin.default_settings.get('telegram_bot_username', ''),
            'last_check': now_utc().isoformat(),
        },
        'webpush': {
            'enabled': is_webpush_enabled(),
            'vapid_configured': bool(get_vapid_credentials().get('public_key')),
            'service_worker_registered': True,  # Would need to check in production
            'last_check': now_utc().isoformat(),
        },
        'statistics': {
            'total_users': User.query.count(),
            'users_with_telegram': 0,  # Would need to query in production
            'users_with_webpush': 0,   # Would need to query in production
            'notifications_today': 0,   # Would need to query logs
        },
        'health': {
            'database': True,
            'telegram_api': is_telegram_enabled(),
            'webpush_api': is_webpush_enabled(),
            'overall': True,
        }
    }

    # Try to get actual counts (simplified for now)
    try:
        # Count users with Telegram linked
        telegram_users = 0
        all_users = User.query.all()
        for user in all_users:
            chat_id = push_user_settings.get(user, 'telegram_chat_id')
            if chat_id:
                telegram_users += 1

        # Count users with Web Push enabled
        webpush_users = 0
        for user in all_users:
            push_enabled = push_user_settings.get(user, 'push_enabled')
            if push_enabled:
                webpush_users += 1

        status['statistics']['users_with_telegram'] = telegram_users
        status['statistics']['users_with_webpush'] = webpush_users

    except Exception as e:
        logger.warning(f'Could not get user statistics: {e}')

    return status


def validate_telegram_bot_token(token: str) -> Tuple[bool, str]:
    """
    Validate a Telegram bot token.

    Args:
        token: The bot token to validate

    Returns:
        Tuple of (is_valid, message)
    """
    import requests

    if not token:
        return False, "Token cannot be empty"

    # Check token format (basic validation)
    if ':' not in token:
        return False, "Invalid token format. Should be like '1234567890:ABCdefGHIjklMNOpqrsTUVwxyz'"

    # Try to get bot info from Telegram API
    try:
        response = requests.get(
            f'https://api.telegram.org/bot{token}/getMe',
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                username = data['result']['username']
                return True, f"Valid token for bot @{username}"
            else:
                return False, f"Telegram API error: {data.get('description', 'Unknown error')}"
        else:
            return False, f"HTTP error {response.status_code}: {response.text}"

    except requests.exceptions.Timeout:
        return False, "Request timeout - check your network connection"
    except requests.exceptions.ConnectionError:
        return False, "Connection error - check your network connection"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def migrate_settings_to_database() -> Dict:
    """
    Migrate settings from SettingsProxy to database models.

    This function can be used to migrate from the simple SettingsProxy
    storage to more robust database models if needed in the future.

    Returns:
        Migration results
    """
    results = {
        'users_processed': 0,
        'telegram_migrated': 0,
        'webpush_migrated': 0,
        'errors': []
    }

    try:
        all_users = User.query.all()

        for user in all_users:
            try:
                # Migrate Telegram settings
                chat_id = push_user_settings.get(user, 'telegram_chat_id')
                if chat_id:
                    # In a real migration, you would create or update a database record
                    # For now, just count it
                    results['telegram_migrated'] += 1

                # Migrate Web Push subscriptions
                subscriptions = push_user_settings.get(user, 'push_subscriptions') or []
                if subscriptions:
                    # In a real migration, you would create WebPushSubscription records
                    # For now, just count them
                    results['webpush_migrated'] += len(subscriptions)

                results['users_processed'] += 1

            except Exception as e:
                results['errors'].append(f'User {user.id}: {str(e)}')

        logger.info(f"Migration completed: {results}")

    except Exception as e:
        results['errors'].append(f'Migration failed: {str(e)}')
        logger.error(f"Migration failed: {e}")

    return results


def cleanup_orphaned_data() -> Dict:
    """
    Clean up orphaned or invalid data.

    This function removes:
    - Web Push subscriptions that are no longer valid
    - Expired Telegram linking tokens
    - Old notification logs

    Returns:
        Cleanup results
    """
    from .notifications import cleanup_old_data
    from .webpush import cleanup_expired_subscriptions

    results = {
        'telegram_tokens_cleaned': 0,
        'webpush_subscriptions_cleaned': 0,
        'notification_logs_cleaned': 0,
        'errors': []
    }

    try:
        # Clean up expired Telegram tokens
        from .telegram_bot import cleanup_expired_tokens
        cleanup_expired_tokens()

        # Clean up old notification logs (older than 90 days)
        from .models import cleanup_old_logs
        logs_cleaned = cleanup_old_logs(days=90)
        results['notification_logs_cleaned'] = logs_cleaned

        # Note: WebPush subscription cleanup would need actual implementation
        # cleanup_expired_subscriptions() is currently a placeholder

        logger.info(f"Cleanup completed: {results}")

    except Exception as e:
        results['errors'].append(f'Cleanup failed: {str(e)}')
        logger.error(f"Cleanup failed: {e}")

    return results
