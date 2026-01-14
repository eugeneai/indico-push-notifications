# This file is part of Indico Push Notifications Plugin.
# Copyright (C) 2024 CERN
#
# Indico Push Notifications Plugin is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

"""
Alembic migration environment for Indico Push Notifications Plugin.

This file configures the Alembic migration environment for the plugin.
It's used to manage database schema changes for the plugin's models.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add the plugin directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Indico's database metadata
from indico.core.db import db as indico_db

# Import plugin models
from indico_push_notifications.models import *

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for 'autogenerate' support
target_metadata = indico_db.metadata

# Plugin-specific metadata - if you have separate metadata for the plugin
# plugin_metadata = db.MetaData()
# target_metadata = plugin_metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url():
    """Get the database URL from Indico configuration."""
    import os

    # First try environment variable
    db_url = os.environ.get("INDICO_DATABASE_URL")
    if db_url:
        return db_url

    # Try to read from Indico config file directly
    try:
        # Look for indico.conf in common locations
        config_paths = [
            "/opt/indico/indico.conf",
            "/etc/indico.conf",
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "indico.conf",
            ),
            os.path.expanduser("~/indico.conf"),
        ]

        for config_path in config_paths:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    content = f.read()
                    # Look for DATABASE_URL or SQLALCHEMY_DATABASE_URI
                    import re

                    # Try DATABASE_URL first (common in indico.conf)
                    match = re.search(
                        r'^\s*DATABASE_URL\s*=\s*[\'"]([^\'"]+)[\'"]',
                        content,
                        re.MULTILINE,
                    )
                    if match:
                        return match.group(1)
                    # Try SQLALCHEMY_DATABASE_URI
                    match = re.search(
                        r'^\s*SQLALCHEMY_DATABASE_URI\s*=\s*[\'"]([^\'"]+)[\'"]',
                        content,
                        re.MULTILINE,
                    )
                    if match:
                        return match.group(1)
    except Exception:
        pass

    # Fall back to alembic.ini
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Plugin-specific table prefix
        version_table="alembic_version_push_notifications",
        # Include only plugin tables in autogenerate
        include_object=include_object,
        # Compare types for autogenerate
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """Filter which objects to include in migrations.

    This function can be used to exclude certain tables or other
    database objects from being considered in autogenerate migrations.
    """
    if type_ == "table":
        # Only include tables that belong to this plugin
        # Plugin tables are prefixed with 'push_notification_' or 'telegram_' or 'webpush_'
        if name.startswith(("push_notification_", "telegram_", "webpush_")):
            return True
        # Also include alembic version table for this plugin
        if name == "alembic_version_push_notifications":
            return True
        return False
    return True


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get database URL
    database_url = get_database_url()

    # Update config with actual database URL
    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        configuration = {}
    configuration["sqlalchemy.url"] = database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Plugin-specific table prefix
            version_table="alembic_version_push_notifications",
            # Include only plugin tables in autogenerate
            include_object=include_object,
            # Compare types for autogenerate
            compare_type=True,
            compare_server_default=True,
            # Transaction per migration
            transaction_per_migration=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
