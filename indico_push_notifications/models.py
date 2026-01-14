# This file is part of Indico Push Notifications Plugin.
# Copyright (C) 2024 CERN
#
# Indico Push Notifications Plugin is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

"""
Database models for Indico Push Notifications Plugin.

Note: This plugin primarily uses SettingsProxy for storing user settings,
so database models are only needed for more complex data structures
or for data that needs complex queries.
"""

from datetime import datetime
from typing import Dict, List, Optional

from indico.core.db import db
from indico.core.db.sqlalchemy import UTCDateTime
from indico.modules.users import User
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship


class PushNotificationLog(db.Model):
    """Log of sent push notifications for auditing and debugging."""

    __tablename__ = "push_notification_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type = Column(String(50), nullable=False, index=True)
    channel = Column(String(20), nullable=False)  # 'telegram', 'webpush', 'both'
    event_id = Column(
        Integer, ForeignKey("events.events.id", ondelete="CASCADE"), nullable=True
    )
    subject = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)
    extra_data = Column(
        JSON, nullable=True
    )  # Additional data like subscription info, message IDs, etc.
    created_at = Column(UTCDateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship(
        "User", backref=db.backref("push_notification_logs", lazy="dynamic")
    )
    event = relationship(
        "Event", backref=db.backref("push_notification_logs", lazy="dynamic")
    )

    def __repr__(self):
        return f"<PushNotificationLog {self.id}: {self.notification_type} to user {self.user_id}>"


class TelegramBotSession(db.Model):
    """Store Telegram bot session data for persistence across restarts."""

    __tablename__ = "telegram_bot_sessions"

    id = Column(Integer, primary_key=True)
    bot_token = Column(String(100), nullable=False, unique=True, index=True)
    session_data = Column(JSON, nullable=False)  # Serialized bot session
    last_updated = Column(UTCDateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<TelegramBotSession for token {self.bot_token[:10]}...>"


class TelegramUserLink(db.Model):
    """Store Telegram user links for queryable relationships."""

    __tablename__ = "telegram_user_links"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    chat_id = Column(String(50), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=True)
    linking_token = Column(String(100), nullable=True, index=True)
    token_expires = Column(UTCDateTime, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    last_used = Column(UTCDateTime, nullable=True)
    created_at = Column(UTCDateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        UTCDateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("User", backref=db.backref("telegram_user_link", lazy=True))

    def __repr__(self):
        return (
            f"<TelegramUserLink {self.id}: user {self.user_id} -> chat {self.chat_id}>"
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "username": self.username,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }


class WebPushSubscription(db.Model):
    """Alternative storage for Web Push subscriptions (instead of SettingsProxy)."""

    __tablename__ = "webpush_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint = Column(Text, nullable=False, index=True)
    keys = Column(JSON, nullable=False)  # {p256dh: "...", auth: "..."}
    browser = Column(String(50), nullable=True)
    platform = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    last_used = Column(UTCDateTime, nullable=True)
    created_at = Column(UTCDateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        UTCDateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship(
        "User", backref=db.backref("webpush_subscriptions", lazy="dynamic")
    )

    def __repr__(self):
        return f"<WebPushSubscription {self.id} for user {self.user_id}>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "endpoint": self.endpoint[:100] + "..."
            if len(self.endpoint) > 100
            else self.endpoint,
            "browser": self.browser,
            "platform": self.platform,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "enabled": self.enabled,
        }


class NotificationTemplate(db.Model):
    """Custom notification templates for different event types."""

    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    notification_type = Column(String(50), nullable=False, index=True)
    channel = Column(
        String(20), nullable=False
    )  # 'telegram', 'webpush', 'email', 'all'
    subject_template = Column(String(255), nullable=False)
    body_template = Column(Text, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(UTCDateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        UTCDateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<NotificationTemplate {self.id}: {self.name}>"

    def render(self, context: Dict) -> Dict:
        """Render template with context variables."""
        # Simple template rendering - in production, use a proper templating engine
        import re

        subject = self.subject_template
        body = self.body_template

        for key, value in context.items():
            placeholder = f"{{{key}}}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))

        return {"subject": subject, "body": body, "channel": self.channel}


# Helper functions for model operations
def get_or_create_telegram_link(user: User) -> TelegramUserLink:
    """Get or create a Telegram user link for the given user."""
    link = TelegramUserLink.query.filter_by(user_id=user.id).first()
    if not link:
        link = TelegramUserLink(user_id=user.id)
        db.session.add(link)
        db.session.flush()

        # Sync with SettingsProxy
        from .notifications import push_user_settings

        push_user_settings.set(user, "telegram_chat_id", None)
        push_user_settings.set(user, "telegram_username", None)
        push_user_settings.set(user, "telegram_enabled", False)
    return link


def find_user_by_telegram_token(token: str) -> Optional[User]:
    """Find user by Telegram linking token."""
    link = TelegramUserLink.query.filter_by(linking_token=token).first()
    if link and link.token_expires and link.token_expires > datetime.utcnow():
        return link.user
    return None


def find_user_by_telegram_chat_id(chat_id: str) -> Optional[User]:
    """Find user by Telegram chat ID."""
    link = TelegramUserLink.query.filter_by(chat_id=chat_id).first()
    if link:
        return link.user
    return None


def update_telegram_link(
    user: User, chat_id: str, username: str = None
) -> TelegramUserLink:
    """Update or create Telegram link for user."""
    link = get_or_create_telegram_link(user)
    link.chat_id = chat_id
    link.username = username
    link.linking_token = None
    link.token_expires = None
    link.enabled = True
    link.updated_at = datetime.utcnow()

    # Sync with SettingsProxy
    from .notifications import push_user_settings

    push_user_settings.set(user, "telegram_chat_id", chat_id)
    push_user_settings.set(user, "telegram_username", username)
    push_user_settings.set(user, "telegram_enabled", True)

    return link


def remove_telegram_link(user: User) -> bool:
    """Remove Telegram link for user."""
    link = TelegramUserLink.query.filter_by(user_id=user.id).first()
    if link:
        db.session.delete(link)

        # Sync with SettingsProxy
        from .notifications import push_user_settings

        push_user_settings.set(user, "telegram_chat_id", None)
        push_user_settings.set(user, "telegram_username", None)
        push_user_settings.set(user, "telegram_enabled", False)
        push_user_settings.set(user, "telegram_linking_token", None)
        push_user_settings.set(user, "telegram_linking_expires", None)

        return True
    return False


def set_telegram_linking_token(
    user: User, token: str, expires: datetime
) -> TelegramUserLink:
    """Set Telegram linking token for user."""
    link = get_or_create_telegram_link(user)
    link.linking_token = token
    link.token_expires = expires
    link.updated_at = datetime.utcnow()

    # Sync with SettingsProxy
    from .notifications import push_user_settings

    push_user_settings.set(user, "telegram_linking_token", token)
    push_user_settings.set(user, "telegram_linking_expires", expires)

    return link


def log_notification(
    user: User,
    notification_type: str,
    channel: str,
    success: bool,
    event_id: Optional[int] = None,
    subject: Optional[str] = None,
    message: Optional[str] = None,
    error_message: Optional[str] = None,
    extra_data: Optional[Dict] = None,
) -> PushNotificationLog:
    """Log a notification attempt to the database."""
    log_entry = PushNotificationLog(
        user_id=user.id,
        notification_type=notification_type,
        channel=channel,
        event_id=event_id,
        subject=subject,
        message=message,
        success=success,
        error_message=error_message,
        extra_data=extra_data or {},
    )

    db.session.add(log_entry)
    return log_entry


def get_user_notification_logs(
    user: User, limit: int = 100, offset: int = 0
) -> List[PushNotificationLog]:
    """Get notification logs for a user."""
    return (
        PushNotificationLog.query.filter_by(user_id=user.id)
        .order_by(PushNotificationLog.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def cleanup_old_logs(days: int = 30) -> int:
    """Clean up notification logs older than specified days."""
    from datetime import timedelta

    from indico.util.date_time import now_utc

    cutoff_date = now_utc() - timedelta(days=days)

    result = PushNotificationLog.query.filter(
        PushNotificationLog.created_at < cutoff_date
    ).delete()

    db.session.commit()
    return result


# Helper functions for syncing between SettingsProxy and database models
def sync_telegram_settings_to_db(user: User) -> TelegramUserLink:
    """Sync Telegram settings from SettingsProxy to database model."""
    from .notifications import push_user_settings

    link = get_or_create_telegram_link(user)

    # Get values from SettingsProxy
    chat_id = push_user_settings.get(user, "telegram_chat_id")
    username = push_user_settings.get(user, "telegram_username")
    enabled = push_user_settings.get(user, "telegram_enabled")
    linking_token = push_user_settings.get(user, "telegram_linking_token")
    linking_expires = push_user_settings.get(user, "telegram_linking_expires")

    # Update database model
    if chat_id:
        link.chat_id = chat_id
    if username:
        link.username = username
    if enabled is not None:
        link.enabled = enabled
    if linking_token:
        link.linking_token = linking_token
    if linking_expires:
        link.token_expires = linking_expires

    link.updated_at = datetime.utcnow()
    return link


def sync_telegram_settings_from_db(user: User) -> Dict:
    """Sync Telegram settings from database model to SettingsProxy."""
    from .notifications import push_user_settings

    link = TelegramUserLink.query.filter_by(user_id=user.id).first()
    if not link:
        return {}

    # Update SettingsProxy
    settings = {}
    if link.chat_id:
        push_user_settings.set(user, "telegram_chat_id", link.chat_id)
        settings["telegram_chat_id"] = link.chat_id
    if link.username:
        push_user_settings.set(user, "telegram_username", link.username)
        settings["telegram_username"] = link.username
    if link.enabled is not None:
        push_user_settings.set(user, "telegram_enabled", link.enabled)
        settings["telegram_enabled"] = link.enabled
    if link.linking_token:
        push_user_settings.set(user, "telegram_linking_token", link.linking_token)
        settings["telegram_linking_token"] = link.linking_token
    if link.token_expires:
        push_user_settings.set(user, "telegram_linking_expires", link.token_expires)
        settings["telegram_linking_expires"] = link.token_expires

    return settings


def get_telegram_settings(user: User) -> Dict:
    """Get Telegram settings, preferring database over SettingsProxy."""
    link = TelegramUserLink.query.filter_by(user_id=user.id).first()
    if link:
        # Return from database
        return {
            "chat_id": link.chat_id,
            "username": link.username,
            "enabled": link.enabled,
            "linked": link.chat_id is not None,
            "linking_token": link.linking_token,
            "token_expires": link.token_expires.isoformat()
            if link.token_expires
            else None,
            "last_used": link.last_used.isoformat() if link.last_used else None,
            "created_at": link.created_at.isoformat() if link.created_at else None,
            "updated_at": link.updated_at.isoformat() if link.updated_at else None,
        }
    else:
        # Fall back to SettingsProxy
        from .notifications import push_user_settings

        return {
            "chat_id": push_user_settings.get(user, "telegram_chat_id"),
            "username": push_user_settings.get(user, "telegram_username"),
            "enabled": push_user_settings.get(user, "telegram_enabled"),
            "linked": push_user_settings.get(user, "telegram_chat_id") is not None,
            "linking_token": push_user_settings.get(user, "telegram_linking_token"),
            "token_expires": push_user_settings.get(user, "telegram_linking_expires"),
            "last_used": None,
            "created_at": None,
            "updated_at": None,
        }


def update_telegram_enabled(user: User, enabled: bool) -> bool:
    """Update Telegram enabled status in both database and SettingsProxy."""
    from .notifications import push_user_settings

    # Update SettingsProxy
    push_user_settings.set(user, "telegram_enabled", enabled)

    # Update database if link exists
    link = TelegramUserLink.query.filter_by(user_id=user.id).first()
    if link:
        link.enabled = enabled
        link.updated_at = datetime.utcnow()

    return True
