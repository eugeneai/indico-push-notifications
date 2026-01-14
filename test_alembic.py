#!/usr/bin/env python3
"""
Test script for Alembic migrations in Indico Push Notifications Plugin.
This script helps test and debug migration issues.
"""

import os
import subprocess
import sys
from pathlib import Path


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)


def test_alembic_config():
    """Test if alembic.ini is correctly configured."""
    print_header("Testing Alembic Configuration")

    current_dir = Path(__file__).parent
    alembic_ini = current_dir / "alembic.ini"

    if not alembic_ini.exists():
        print(f"❌ ERROR: alembic.ini not found at {alembic_ini}")
        return False

    print(f"✅ Found alembic.ini at {alembic_ini}")

    # Check script_location
    with open(alembic_ini, "r") as f:
        content = f.read()
        if "script_location = alembic" in content:
            print("✅ script_location is set to 'alembic'")
        else:
            print("❌ ERROR: script_location not set to 'alembic'")
            return False

    # Check if alembic directory exists
    alembic_dir = current_dir / "alembic"
    if alembic_dir.exists():
        print(f"✅ Found alembic directory at {alembic_dir}")

        # Check for required files
        required_files = ["env.py", "script.py.mako"]
        for file in required_files:
            if (alembic_dir / file).exists():
                print(f"✅ Found {file}")
            else:
                print(f"❌ ERROR: Missing {file}")
                return False
    else:
        print(f"❌ ERROR: alembic directory not found at {alembic_dir}")
        return False

    return True


def test_database_url():
    """Test database URL configuration."""
    print_header("Testing Database Configuration")

    # Check environment variable
    db_url = os.environ.get("INDICO_DATABASE_URL")
    if db_url:
        print(f"✅ Found INDICO_DATABASE_URL environment variable")
        # Mask password for security
        masked_url = db_url
        if "@" in db_url:
            parts = db_url.split("@")
            if ":" in parts[0]:
                user_pass = parts[0].split(":")
                if len(user_pass) == 3:  # postgresql://user:pass@host/db
                    masked_url = f"{user_pass[0]}://{user_pass[1]}:****@{parts[1]}"
                elif len(user_pass) == 2:  # user:pass@host/db
                    masked_url = f"{user_pass[0]}:****@{parts[1]}"
        print(f"   Database URL: {masked_url}")
    else:
        print("⚠️  WARNING: INDICO_DATABASE_URL environment variable not set")
        print("   Using default from alembic.ini")

    return True


def test_alembic_commands():
    """Test basic alembic commands."""
    print_header("Testing Alembic Commands")

    current_dir = Path(__file__).parent

    # Test 1: alembic current
    print("\n1. Testing 'alembic current':")
    try:
        result = subprocess.run(
            ["alembic", "-c", str(current_dir / "alembic.ini"), "current"],
            capture_output=True,
            text=True,
            cwd=current_dir,
        )

        if result.returncode == 0:
            if result.stdout.strip():
                print(f"✅ Current revision: {result.stdout.strip()}")
            else:
                print("✅ No migrations applied yet (empty database)")
        else:
            print(f"❌ ERROR: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ ERROR: 'alembic' command not found. Make sure alembic is installed.")
        return False

    # Test 2: alembic history
    print("\n2. Testing 'alembic history':")
    try:
        result = subprocess.run(
            ["alembic", "-c", str(current_dir / "alembic.ini"), "history"],
            capture_output=True,
            text=True,
            cwd=current_dir,
        )

        if result.returncode == 0:
            if result.stdout.strip():
                print("✅ Migration history:")
                for line in result.stdout.strip().split("\n"):
                    print(f"   {line}")
            else:
                print("✅ No migration history found")
        else:
            print(f"❌ ERROR: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ ERROR: 'alembic' command not found")
        return False

    return True


def test_migration_dry_run():
    """Test migration upgrade in dry-run mode."""
    print_header("Testing Migration Dry Run")

    current_dir = Path(__file__).parent

    print("Testing 'alembic upgrade head --sql' (dry run):")
    try:
        result = subprocess.run(
            [
                "alembic",
                "-c",
                str(current_dir / "alembic.ini"),
                "upgrade",
                "head",
                "--sql",
            ],
            capture_output=True,
            text=True,
            cwd=current_dir,
            timeout=30,
        )

        if result.returncode == 0:
            print("✅ Dry run successful")
            # Count SQL statements
            sql_lines = [line for line in result.stdout.split("\n") if line.strip()]
            print(f"   Generated {len(sql_lines)} SQL statements")

            # Show first few statements
            if sql_lines:
                print("\n   First 3 SQL statements:")
                for i, line in enumerate(sql_lines[:3]):
                    print(
                        f"   {i + 1}. {line[:100]}..."
                        if len(line) > 100
                        else f"   {i + 1}. {line}"
                    )
        else:
            print(f"❌ ERROR: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ ERROR: Command timed out")
        return False
    except FileNotFoundError:
        print("❌ ERROR: 'alembic' command not found")
        return False

    return True


def test_indico_integration():
    """Test integration with Indico."""
    print_header("Testing Indico Integration")

    try:
        # Try to import Indico
        import indico

        print(
            f"✅ Indico version: {indico.__version__ if hasattr(indico, '__version__') else 'unknown'}"
        )
    except ImportError:
        print("⚠️  WARNING: Indico not installed in current environment")
        print("   This is normal if testing outside Indico environment")

    try:
        # Try to import plugin
        import indico_push_notifications

        print("✅ Plugin package imported successfully")

        from indico_push_notifications import IndicoPushNotificationsPlugin

        print("✅ Plugin class imported successfully")

        # Check plugin metadata
        plugin = IndicoPushNotificationsPlugin()
        print(f"✅ Plugin name: {plugin.name}")
        print(f"✅ Plugin friendly name: {plugin.friendly_name}")

    except ImportError as e:
        print(f"❌ ERROR: Failed to import plugin: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

    return True


def main():
    """Main test function."""
    print_header("Alembic Migration Test Suite")
    print("Testing Indico Push Notifications Plugin migrations\n")

    tests = [
        ("Alembic Configuration", test_alembic_config),
        ("Database Configuration", test_database_url),
        ("Alembic Commands", test_alembic_commands),
        ("Migration Dry Run", test_migration_dry_run),
        ("Indico Integration", test_indico_integration),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ ERROR in {test_name}: {e}")
            results.append((test_name, False))

    # Print summary
    print_header("Test Summary")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")
    print()

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "=" * 60)

    if passed == total:
        print("🎉 All tests passed! You can run migrations with:")
        print("\n   alembic -c alembic.ini upgrade head")
        print("\nOr using Indico command:")
        print("\n   indico db upgrade --plugin indico_push_notifications")
    else:
        print("⚠️  Some tests failed. Please fix issues before running migrations.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
