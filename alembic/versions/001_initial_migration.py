# This file is part of Indico Push Notifications Plugin.
# Copyright (C) 2024 CERN
#
# Indico Push Notifications Plugin is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

"""Initial migration for Indico Push Notifications Plugin

Create tables for push notification logs, Telegram bot sessions,
Web Push subscriptions, and notification templates.

Revision ID: 001_initial_migration
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

import sqlalchemy as sa
from indico.core.db.sqlalchemy import UTCDateTime
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_initial_migration"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create push_notification_logs table
    op.create_table(
        "push_notification_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "success", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for push_notification_logs
    op.create_index(
        op.f("ix_push_notification_logs_user_id"),
        "push_notification_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_push_notification_logs_notification_type"),
        "push_notification_logs",
        ["notification_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_push_notification_logs_created_at"),
        "push_notification_logs",
        ["created_at"],
        unique=False,
    )

    # Create telegram_bot_sessions table
    op.create_table(
        "telegram_bot_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bot_token", sa.String(length=100), nullable=False),
        sa.Column(
            "session_data", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("last_updated", UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bot_token"),
    )

    # Create index for telegram_bot_sessions
    op.create_index(
        op.f("ix_telegram_bot_sessions_bot_token"),
        "telegram_bot_sessions",
        ["bot_token"],
        unique=True,
    )

    # Create telegram_user_links table
    op.create_table(
        "telegram_user_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.String(length=50), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("linking_token", sa.String(length=100), nullable=True),
        sa.Column("token_expires", UTCDateTime(), nullable=True),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("last_used", UTCDateTime(), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("chat_id"),
    )

    # Create indexes for telegram_user_links
    op.create_index(
        op.f("ix_telegram_user_links_user_id"),
        "telegram_user_links",
        ["user_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_telegram_user_links_chat_id"),
        "telegram_user_links",
        ["chat_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_telegram_user_links_linking_token"),
        "telegram_user_links",
        ["linking_token"],
        unique=False,
    )

    # Create webpush_subscriptions table
    op.create_table(
        "webpush_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("keys", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("browser", sa.String(length=50), nullable=True),
        sa.Column("platform", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("last_used", UTCDateTime(), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for webpush_subscriptions
    op.create_index(
        op.f("ix_webpush_subscriptions_user_id"),
        "webpush_subscriptions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webpush_subscriptions_endpoint"),
        "webpush_subscriptions",
        ["endpoint"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webpush_subscriptions_created_at"),
        "webpush_subscriptions",
        ["created_at"],
        unique=False,
    )

    # Create notification_templates table
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("subject_template", sa.String(length=255), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for notification_templates
    op.create_index(
        op.f("ix_notification_templates_notification_type"),
        "notification_templates",
        ["notification_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_templates_name"),
        "notification_templates",
        ["name"],
        unique=False,
    )

    # Create default notification templates
    from datetime import datetime

    op.bulk_insert(
        sa.table(
            "notification_templates",
            sa.column("name", sa.String),
            sa.column("notification_type", sa.String),
            sa.column("channel", sa.String),
            sa.column("subject_template", sa.String),
            sa.column("body_template", sa.Text),
            sa.column("enabled", sa.Boolean),
            sa.column("created_at", UTCDateTime),
            sa.column("updated_at", UTCDateTime),
        ),
        [
            {
                "name": "Event Creation - Telegram",
                "notification_type": "event_creation",
                "channel": "telegram",
                "subject_template": "New Event: {event_title}",
                "body_template": 'A new event "{event_title}" has been created by {creator_name}.\n\nStart: {event_start_date}\nLocation: {event_location}\n\n[View Event]({event_url})',
                "enabled": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "Event Creation - Web Push",
                "notification_type": "event_creation",
                "channel": "webpush",
                "subject_template": "New Event: {event_title}",
                "body_template": 'A new event "{event_title}" has been created by {creator_name}. Starts {event_start_date} at {event_location}.',
                "enabled": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "Registration Open - Telegram",
                "notification_type": "registration_open",
                "channel": "telegram",
                "subject_template": "Registration Open: {event_title}",
                "body_template": 'Registration is now open for "{event_title}".\n\nDeadline: {registration_deadline}\n\n[Register Now]({event_url})',
                "enabled": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "Registration Open - Web Push",
                "notification_type": "registration_open",
                "channel": "webpush",
                "subject_template": "Registration Open: {event_title}",
                "body_template": 'Registration is now open for "{event_title}". Deadline: {registration_deadline}.',
                "enabled": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "Abstract Submission - Telegram",
                "notification_type": "abstract_submission",
                "channel": "telegram",
                "subject_template": "Abstract Submitted: {event_title}",
                "body_template": 'A new abstract has been submitted for "{event_title}" by {submitter_name}.\n\nTitle: {abstract_title}\n\n[View Abstract]({abstract_url})',
                "enabled": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "Abstract Submission - Web Push",
                "notification_type": "abstract_submission",
                "channel": "webpush",
                "subject_template": "Abstract Submitted: {event_title}",
                "body_template": 'A new abstract "{abstract_title}" has been submitted for "{event_title}" by {submitter_name}.',
                "enabled": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "Event Reminder - Telegram",
                "notification_type": "reminder",
                "channel": "telegram",
                "subject_template": "Reminder: {event_title}",
                "body_template": 'Reminder: "{event_title}" is starting soon.\n\nStart: {event_start_date}\nLocation: {event_location}\n\n[View Event]({event_url})',
                "enabled": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "Event Reminder - Web Push",
                "notification_type": "reminder",
                "channel": "webpush",
                "subject_template": "Reminder: {event_title}",
                "body_template": 'Reminder: "{event_title}" is starting soon at {event_start_date}. Location: {event_location}.',
                "enabled": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        ],
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("notification_templates")
    op.drop_table("webpush_subscriptions")
    op.drop_table("telegram_user_links")
    op.drop_table("telegram_bot_sessions")
    op.drop_table("push_notification_logs")
