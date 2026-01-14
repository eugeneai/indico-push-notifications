# This file is part of Indico Push Notifications Plugin.
# Copyright (C) 2024 CERN
#
# Indico Push Notifications Plugin is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

"""
Basic tests for Indico Push Notifications Plugin.

These tests cover the core functionality of the plugin.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from indico.modules.users import User
from indico.core.db import db

from indico_push_notifications import IndicoPushNotificationsPlugin
from indico_push_notifications.notifications import (
    push_user_settings,
    get_user_preferences,
    update_user_preferences,
    should_send_notification,
    format_notification_message,
)
from indico_push_notifications.telegram_bot import (
    generate_telegram_link,
    verify_telegram_linking,
)
from indico_push_notifications.webpush import (
    validate_push_subscription,
    get_vapid_credentials,
)


class TestPluginBasics:
    """Test basic plugin functionality."""

    def test_plugin_initialization(self):
        """Test that the plugin initializes correctly."""
        plugin = IndicoPushNotificationsPlugin()

        assert plugin.name == "indico_push_notifications"
        assert plugin.friendly_name == "Push Notifications"
        assert plugin.description == "Adds Telegram and Web Push notifications to Indico"
        assert plugin.category == "Notification"
        assert plugin.configurable is True

        # Check default settings
        assert "telegram_bot_token" in plugin.default_settings
        assert "vapid_public_key" in plugin.default_settings
        assert "default_notification_preferences" in plugin.default_settings

        # Check default user settings
        assert "telegram_chat_id" in plugin.default_user_settings
        assert "push_enabled" in plugin.default_user_settings
        assert "notification_preferences" in plugin.default_user_settings

    def test_plugin_default_settings_structure(self):
        """Test that default settings have the correct structure."""
        plugin = IndicoPushNotificationsPlugin()

        default_prefs = plugin.default_settings["default_notification_preferences"]

        # Check all expected notification types are present
        expected_types = [
            "event_creation",
            "event_update",
            "registration_open",
            "registration_confirmation",
            "abstract_submission",
            "abstract_review",
            "reminder",
        ]

        for pref_type in expected_types:
            assert pref_type in default_prefs
            assert isinstance(default_prefs[pref_type], bool)
            assert default_prefs[pref_type] is True  # All defaults should be True


class TestUserPreferences:
    """Test user preference management."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = Mock(spec=User)
        user.id = 123
        user.email = "test@example.com"
        user.full_name = "Test User"
        return user

    def test_get_user_preferences_empty(self, mock_user):
        """Test getting preferences for a user with no settings."""
        with patch.object(push_user_settings, 'get') as mock_get:
            # Mock the SettingsProxy responses
            mock_get.side_effect = lambda user, key: {
                'telegram_chat_id': None,
                'telegram_username': None,
                'telegram_enabled': False,
                'push_enabled': False,
                'push_subscriptions': [],
                'notification_preferences': None,
                'last_notification_sent': None,
            }.get(key)

            prefs = get_user_preferences(mock_user)

            assert 'telegram' in prefs
            assert 'push' in prefs
            assert 'preferences' in prefs

            # Telegram should show as not linked
            assert prefs['telegram']['linked'] is False
            assert prefs['telegram']['enabled'] is False

            # Push should show as not enabled
            assert prefs['push']['enabled'] is False
            assert prefs['push']['subscriptions_count'] == 0

            # Preferences should use defaults
            assert prefs['preferences']['event_creation'] is True
            assert prefs['preferences']['event_update'] is True

    def test_update_user_preferences(self, mock_user):
        """Test updating user preferences."""
        with patch.object(push_user_settings, 'set') as mock_set:
            update_data = {
                'telegram_enabled': True,
                'push_enabled': True,
                'preferences': {
                    'event_creation': False,
                    'registration_open': True,
                }
            }

            update_user_preferences(mock_user, update_data)

            # Check that set was called with correct values
            assert mock_set.call_count >= 3

            # Check specific calls
            calls = [call[0] for call in mock_set.call_args_list]

            # Should have called set for telegram_enabled
            assert (mock_user, 'telegram_enabled', True) in calls

            # Should have called set for push_enabled
            assert (mock_user, 'push_enabled', True) in calls

            # Should have called set for notification_preferences
            # Find the preferences call
            prefs_call = next((call for call in calls if call[1] == 'notification_preferences'), None)
            assert prefs_call is not None
            assert prefs_call[2]['event_creation'] is False
            assert prefs_call[2]['registration_open'] is True

    def test_should_send_notification(self, mock_user):
        """Test notification sending logic."""
        # Test with no channels enabled
        with patch.object(push_user_settings, 'get') as mock_get:
            mock_get.side_effect = lambda user, key: {
                'telegram_enabled': False,
                'push_enabled': False,
                'notification_preferences': None,
            }.get(key)

            result = should_send_notification(mock_user, 'event_creation')
            assert result is False

        # Test with channel enabled but preference disabled
        with patch.object(push_user_settings, 'get') as mock_get:
            mock_get.side_effect = lambda user, key: {
                'telegram_enabled': True,
                'push_enabled': False,
                'notification_preferences': {'event_creation': False},
            }.get(key)

            result = should_send_notification(mock_user, 'event_creation')
            assert result is False

        # Test with channel enabled and preference enabled
        with patch.object(push_user_settings, 'get') as mock_get:
            mock_get.side_effect = lambda user, key: {
                'telegram_enabled': True,
                'push_enabled': False,
                'notification_preferences': {'event_creation': True},
            }.get(key)

            result = should_send_notification(mock_user, 'event_creation')
            assert result is True


class TestNotificationFormatting:
    """Test notification message formatting."""

    def test_format_notification_message_basic(self):
        """Test basic message formatting."""
        subject = "Test Subject"
        body = "This is a test notification body."
        context = {
            'type': 'test',
            'event': None,
            'event_id': None,
            'event_url': None,
        }

        result = format_notification_message(subject, body, context)

        assert 'telegram' in result
        assert 'push' in result
        assert 'context' in result

        # Telegram message should include subject and body
        assert subject in result['telegram']
        assert body in result['telegram']

        # Push message should have title and body
        assert result['push']['title'] == subject
        assert result['push']['body'] == body

        # Context should be preserved
        assert result['context'] == context

    def test_format_notification_message_with_event(self):
        """Test message formatting with event context."""
        subject = "Event Updated"
        body = "The event 'Test Event' has been updated."
        context = {
            'type': 'event_update',
            'event': Mock(id=456),
            'event_id': 456,
            'event_url': 'https://indico.example.com/event/456',
        }

        result = format_notification_message(subject, body, context)

        # Telegram message should include event URL
        assert 'https://indico.example.com/event/456' in result['telegram']

        # Push message should have URL in data
        assert result['push']['data']['url'] == 'https://indico.example.com/event/456'

    def test_format_notification_message_truncation(self):
        """Test that long messages are truncated."""
        subject = "Test"
        body = "A" * 1000  # Very long body
        context = {'type': 'test'}

        result = format_notification_message(subject, body, context)

        # Body should be truncated to around 500 characters
        assert len(result['push']['body']) <= 503  # 500 + "..."
        assert result['push']['body'].endswith('...')


class TestTelegramBot:
    """Test Telegram bot functionality."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = Mock(spec=User)
        user.id = 123
        return user

    def test_generate_telegram_link(self, mock_user):
        """Test Telegram linking token generation."""
        with patch.object(push_user_settings, 'get') as mock_get, \
             patch.object(push_user_settings, 'set') as mock_set, \
             patch('secrets.token_urlsafe') as mock_token:

            # Mock token generation
            mock_token.return_value = 'ABC123DEF456'

            # Mock current time
            mock_now = datetime(2024, 1, 1, 12, 0, 0)

            with patch('indico_push_notifications.telegram_bot.now_utc') as mock_now_utc:
                mock_now_utc.return_value = mock_now

                # Mock plugin settings
                with patch('indico_push_notifications.telegram_bot.plugin') as mock_plugin:
                    mock_plugin.default_settings.get.return_value = '@IndicoBot'

                    link = generate_telegram_link(mock_user)

                    # Should return a Telegram link
                    assert link.startswith('https://t.me/IndicoBot?start=')
                    assert 'ABC123DEF456' in link

                    # Should have saved the token
                    mock_set.assert_called_with(
                        mock_user,
                        'telegram_linking_token',
                        'ABC123DEF456'
                    )

    def test_verify_telegram_linking(self, mock_user):
        """Test Telegram linking verification."""
        # Create a mock query to find user by token
        mock_user2 = Mock(spec=User)
        mock_user2.id = 456

        with patch('indico_push_notifications.telegram_bot.find_user_by_linking_token') as mock_find, \
             patch.object(push_user_settings, 'set') as mock_set:

            # Mock finding the user
            mock_find.return_value = mock_user2

            # Test successful verification
            result = verify_telegram_linking('valid_token', 'chat123', 'testuser')

            assert result is True

            # Should have updated user settings
            assert mock_set.call_count >= 3

            # Check specific calls
            calls = [call[0] for call in mock_set.call_args_list]
            assert (mock_user2, 'telegram_chat_id', 'chat123') in calls
            assert (mock_user2, 'telegram_username', 'testuser') in calls
            assert (mock_user2, 'telegram_enabled', True) in calls
            assert (mock_user2, 'telegram_linking_token', None) in calls

        # Test failed verification (user not found)
        with patch('indico_push_notifications.telegram_bot.find_user_by_linking_token') as mock_find:
            mock_find.return_value = None

            result = verify_telegram_linking('invalid_token', 'chat123', 'testuser')

            assert result is False


class TestWebPush:
    """Test Web Push functionality."""

    def test_validate_push_subscription_valid(self):
        """Test validation of valid push subscription."""
        valid_subscription = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/abc123',
            'keys': {
                'auth': 'abc123',
                'p256dh': 'def456'
            }
        }

        # Mock base64 decoding
        with patch('base64.urlsafe_b64decode') as mock_b64:
            mock_b64.return_value = b'test'

            result = validate_push_subscription(valid_subscription)

            assert result is True

    def test_validate_push_subscription_invalid(self):
        """Test validation of invalid push subscriptions."""
        # Missing endpoint
        invalid1 = {
            'keys': {'auth': 'abc', 'p256dh': 'def'}
        }
        assert validate_push_subscription(invalid1) is False

        # Missing keys
        invalid2 = {
            'endpoint': 'https://example.com'
        }
        assert validate_push_subscription(invalid2) is False

        # Invalid URL
        invalid3 = {
            'endpoint': 'not-a-url',
            'keys': {'auth': 'abc', 'p256dh': 'def'}
        }
        assert validate_push_subscription(invalid3) is False

        # Empty subscription
        assert validate_push_subscription({}) is False
        assert validate_push_subscription(None) is False

    def test_get_vapid_credentials(self):
        """Test VAPID credential generation/retrieval."""
        # Test with no configured keys (should generate)
        with patch('indico_push_notifications.webpush.plugin') as mock_plugin, \
             patch('indico_push_notifications.webpush.Vapid') as mock_vapid_class:

            # Mock plugin settings
            mock_plugin.default_settings.get.side_effect = lambda key: {
                'vapid_public_key': '',
                'vapid_private_key': '',
                'vapid_email': 'admin@example.com'
            }.get(key, '')

            # Mock VAPID instance
            mock_vapid = Mock()
            mock_vapid.public_key = 'public_key_123'
            mock_vapid.private_key = 'private_key_456'
            mock_vapid_class.return_value = mock_vapid

            credentials = get_vapid_credentials()

            assert credentials['public_key'] == 'public_key_123'
            assert credentials['private_key'] == 'private_key_456'
            assert credentials['email'] == 'admin@example.com'

            # Should have generated keys
            mock_vapid.generate_keys.assert_called_once()

        # Test with configured keys
        with patch('indico_push_notifications.webpush.plugin') as mock_plugin:
            mock_plugin.default_settings.get.side_effect = lambda key: {
                'vapid_public_key': 'configured_public',
                'vapid_private_key': 'configured_private',
                'vapid_email': 'configured@example.com'
            }.get(key, '')

            credentials = get_vapid_credentials()

            assert credentials['public_key'] == 'configured_public'
            assert credentials['private_key'] == 'configured_private'
            assert credentials['email'] == 'configured@example.com'


class TestIntegration:
    """Test integration between components."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = Mock(spec=User)
        user.id = 123
        user.email = "test@example.com"
        return user

    def test_end_to_end_preference_flow(self, mock_user):
        """Test the complete flow of setting and getting preferences."""
        # Start with no preferences
        with patch.object(push_user_settings, 'get') as mock_get, \
             patch.object(push_user_settings, 'set') as mock_set:

            # Mock initial state
            mock_get.side_effect = lambda user, key: {
                'telegram_chat_id': None,
                'telegram_username': None,
                'telegram_enabled': False,
                'push_enabled': False,
                'push_subscriptions': [],
                'notification_preferences': None,
                'last_notification_sent': None,
            }.get(key)

            # Get initial preferences
            initial_prefs = get_user_preferences(mock_user)
            assert initial_prefs['telegram']['linked'] is False
            assert initial_prefs['push']['enabled'] is False

            # Update preferences
            update_data = {
                'telegram_enabled': True,
                'push_enabled': True,
                'preferences': {
                    'event_creation': True,
                    'registration_open': False,
                }
            }

            # Reset mock for update
            mock_get.reset_mock()
            mock_set.reset_mock()

            # Mock updated state for get_user_preferences
            def get_side_effect(key):
                if key == 'telegram_chat_id':
                    return None
                elif key == 'telegram_username':
                    return None
                elif key == 'telegram_enabled':
                    return True
                elif key == 'push_enabled':
                    return True
                elif key == 'push_subscriptions':
                    return []
                elif key == 'notification_preferences':
                    return {'event_creation': True, 'registration_open': False}
                elif key == 'last_notification_sent':
                    return None
                return None

            mock_get.side_effect = get_side_effect

            update_user_preferences(mock_user, update_data)

            # Get updated preferences
            updated_prefs = get_user_preferences(mock_user)

            assert updated_prefs['telegram']['enabled'] is True
            assert updated_prefs['push']['enabled'] is True
            assert updated_prefs['preferences']['event_creation'] is True
            assert updated_prefs['preferences']['registration_open'] is False

    def test_notification_decision_flow(self, mock_user):
        """Test the complete notification decision flow."""
        # Setup user with specific preferences
        with patch.object(push_user_settings, 'get') as mock_get:
            def get_side_effect(key):
                if key == 'telegram_enabled':
                    return True
                elif key == 'push_enabled':
                    return False  # Push disabled
