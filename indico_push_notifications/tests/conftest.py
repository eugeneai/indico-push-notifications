# This file is part of Indico Push Notifications Plugin.
# Copyright (C) 2024 CERN
#
# Indico Push Notifications Plugin is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

"""
Pytest configuration and fixtures for Indico Push Notifications Plugin tests.

This file contains shared fixtures and configuration that can be used across
all test files in the plugin.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from indico.modules.users import User
from indico.core.db import db
from indico.core.settings import SettingsProxy

from indico_push_notifications import IndicoPushNotificationsPlugin
from indico_push_notifications.notifications import push_user_settings


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock(spec=User)
    user.id = 123
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.is_system = False
    user.is_admin = False

    # Mock secondary emails
    user.secondary_emails = []
    user.all_emails = ["test@example.com"]

    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user for testing."""
    user = Mock(spec=User)
    user.id = 999
    user.email = "admin@example.com"
    user.full_name = "Admin User"
    user.is_system = False
    user.is_admin = True

    # Mock secondary emails
    user.secondary_emails = []
    user.all_emails = ["admin@example.com"]

    return user


@pytest.fixture
def mock_event():
    """Create a mock event for testing."""
    event = Mock()
    event.id = 456
    event.title = "Test Event"
    event.start_dt = datetime(2024, 1, 1, 10, 0, 0)
    event.location = "Test Location"
    event.url = "https://indico.example.com/event/456"

    return event


@pytest.fixture
def plugin_instance():
    """Create an instance of the plugin for testing."""
    return IndicoPushNotificationsPlugin()


@pytest.fixture
def mock_push_user_settings():
    """Mock the push_user_settings SettingsProxy."""
    with patch('indico_push_notifications.notifications.push_user_settings') as mock_settings:
        # Configure mock to return sensible defaults
        mock_settings.get.side_effect = lambda user, key, default=None: {
            'telegram_chat_id': None,
            'telegram_username': None,
            'telegram_enabled': False,
            'telegram_linking_token': None,
            'telegram_linking_expires': None,
            'push_enabled': False,
            'push_subscriptions': [],
            'notification_preferences': None,
            'last_notification_sent': None,
        }.get(key, default)

        yield mock_settings


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    with patch('indico_push_notifications.notifications.db') as mock_db:
        mock_session = Mock()
        mock_db.session = mock_session
        yield mock_db


@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot functionality."""
    with patch('indico_push_notifications.telegram_bot') as mock_bot:
        # Mock bot functions
        mock_bot.send_telegram_message.return_value = True
        mock_bot.generate_telegram_link.return_value = "https://t.me/TestBot?start=ABC123"
        mock_bot.verify_telegram_linking.return_value = True
        mock_bot.unlink_telegram.return_value = True
        mock_bot.get_bot.return_value = Mock()

        yield mock_bot


@pytest.fixture
def mock_webpush():
    """Mock WebPush functionality."""
    with patch('indico_push_notifications.webpush') as mock_wp:
        # Mock webpush functions
        mock_wp.validate_push_subscription.return_value = True
        mock_wp.save_push_subscription.return_value = True
        mock_wp.delete_push_subscription.return_value = True
        mock_wp.send_push_notification.return_value = True
        mock_wp.get_vapid_credentials.return_value = {
            'public_key': 'test_public_key',
            'private_key': 'test_private_key',
            'email': 'test@example.com'
        }
        mock_wp.is_webpush_enabled.return_value = True

        yield mock_wp


@pytest.fixture
def mock_requests():
    """Mock requests library for API calls."""
    with patch('indico_push_notifications.telegram_bot.requests') as mock_req:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ok': True,
            'result': {
                'id': 123456789,
                'is_bot': True,
                'first_name': 'Test Bot',
                'username': 'test_bot'
            }
        }
        mock_req.get.return_value = mock_response
        mock_req.post.return_value = mock_response

        yield mock_req


@pytest.fixture
def sample_push_subscription():
    """Return a sample WebPush subscription for testing."""
    return {
        'endpoint': 'https://fcm.googleapis.com/fcm/send/abc123def456',
        'keys': {
            'auth': 'ABC123DEF456GHI789',
            'p256dh': 'JKL012MNO345PQR678'
        },
        'browser': 'Chrome',
        'platform': 'Linux x86_64',
        'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'created': '2024-01-15T10:30:00Z'
    }


@pytest.fixture
def sample_notification_email():
    """Return a sample email notification for testing."""
    return {
        'to': ['user1@example.com', 'user2@example.com'],
        'cc': ['manager@example.com'],
        'bcc': [],
        'subject': 'Test Notification',
        'body': 'This is a test notification body.',
        'html': '<p>This is a test notification body.</p>'
    }


@pytest.fixture
def mock_flask_session():
    """Mock Flask session."""
    with patch('indico_push_notifications.blueprint.session') as mock_session:
        mock_session.user = Mock(spec=User)
        mock_session.user.id = 123
        mock_session.user.is_admin = False
        yield mock_session


@pytest.fixture
def mock_flask_request():
    """Mock Flask request."""
    with patch('indico_push_notifications.blueprint.request') as mock_request:
        mock_request.get_json.return_value = {}
        mock_request.method = 'GET'
        yield mock_request


@pytest.fixture(autouse=True)
def mock_current_time():
    """Mock current time for consistent testing."""
    fixed_time = datetime(2024, 1, 1, 12, 0, 0)

    with patch('indico_push_notifications.notifications.now_utc') as mock_now:
        mock_now.return_value = fixed_time
        yield mock_now


@pytest.fixture
def enable_logging():
    """Enable debug logging for tests."""
    import logging
    logging.basicConfig(level=logging.DEBUG)
    yield
    logging.basicConfig(level=logging.WARNING)


# Configuration for pytest
def pytest_configure(config):
    """Configure pytest."""
    # Add custom markers
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires external services)"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "database: mark test as requiring database"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    skip_integration = pytest.mark.skip(reason="integration test - requires external services")
    skip_slow = pytest.mark.skip(reason="slow test")
    skip_database = pytest.mark.skip(reason="database test - requires database setup")

    for item in items:
        if "integration" in item.keywords and config.getoption("--skip-integration"):
            item.add_marker(skip_integration)
        if "slow" in item.keywords and config.getoption("--skip-slow"):
            item.add_marker(skip_slow)
        if "database" in item.keywords and config.getoption("--skip-database"):
            item.add_marker(skip_database)


# Command line options
def pytest_addoption(parser):
    """Add command line options."""
    parser.addoption(
        "--skip-integration",
        action="store_true",
        default=False,
        help="Skip integration tests"
    )
    parser.addoption(
        "--skip-slow",
        action="store_true",
        default=False,
        help="Skip slow tests"
    )
    parser.addoption(
        "--skip-database",
        action="store_true",
        default=False,
        help="Skip database tests"
    )
