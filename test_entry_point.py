#!/usr/bin/env python3
"""
Test script for Indico Push Notifications Plugin entry point loading.
This script simulates how Indico loads plugins through entry points.
"""

import os
import sys
from pathlib import Path

import pkg_resources

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_entry_point_discovery():
    """Test if entry point is discoverable by pkg_resources."""
    print("=" * 60)
    print("Testing Entry Point Discovery")
    print("=" * 60)

    try:
        # Get all indico.plugins entry points
        entry_points = list(pkg_resources.iter_entry_points("indico.plugins"))

        print(f"Found {len(entry_points)} entry points for 'indico.plugins':")
        for ep in entry_points:
            print(f"  - {ep.name}: {ep.module_name}")

        # Find our plugin
        our_plugin = None
        for ep in entry_points:
            if ep.name == "indico_push_notifications":
                our_plugin = ep
                break

        if our_plugin:
            print(f"\n✅ Found our plugin entry point: {our_plugin.name}")
            print(f"   Module: {our_plugin.module_name}")
            print(f"   Distribution: {our_plugin.dist}")
            return our_plugin
        else:
            print("\n❌ Our plugin entry point NOT found")
            return None

    except Exception as e:
        print(f"\n❌ Error discovering entry points: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_entry_point_loading(entry_point):
    """Test loading plugin through entry point."""
    print("\n" + "=" * 60)
    print("Testing Entry Point Loading")
    print("=" * 60)

    try:
        print(f"Loading entry point: {entry_point.name}")

        # Load the entry point (this is what Indico does)
        plugin_class = entry_point.load()

        print(f"✅ Entry point loaded successfully")
        print(f"   Loaded class: {plugin_class}")
        print(f"   Class name: {plugin_class.__name__}")

        return plugin_class

    except Exception as e:
        print(f"\n❌ Error loading entry point: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_plugin_instantiation(plugin_class):
    """Test creating plugin instance."""
    print("\n" + "=" * 60)
    print("Testing Plugin Instantiation")
    print("=" * 60)

    try:
        print("Creating plugin instance...")

        # Create plugin instance (this is what Indico does)
        plugin_instance = plugin_class()

        print(f"✅ Plugin instance created successfully")
        print(f"   Instance: {plugin_instance}")
        print(f"   Plugin name: {plugin_instance.name}")
        print(f"   Friendly name: {plugin_instance.friendly_name}")
        print(f"   Description: {plugin_instance.description}")

        return plugin_instance

    except Exception as e:
        print(f"\n❌ Error creating plugin instance: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_plugin_initialization(plugin_instance):
    """Test plugin initialization."""
    print("\n" + "=" * 60)
    print("Testing Plugin Initialization")
    print("=" * 60)

    try:
        print("Calling plugin.init()...")

        # Try to initialize (might fail without Indico context)
        plugin_instance.init()

        print(f"✅ Plugin initialization completed")

    except Exception as e:
        print(f"\n⚠️  Plugin initialization raised exception (may be expected):")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Message: {e}")

        # Check if it's the expected "working outside of application context" error
        if "Working outside of application context" in str(e):
            print("   ✅ This is the expected error without Flask app context")
        else:
            print("   ⚠️  Unexpected error during initialization")


def test_direct_import():
    """Test direct import of plugin module."""
    print("\n" + "=" * 60)
    print("Testing Direct Module Import")
    print("=" * 60)

    try:
        print("Importing indico_push_notifications module...")

        # Direct import (this happens when entry point is loaded)
        import indico_push_notifications

        print(f"✅ Module imported successfully")
        print(f"   Module: {indico_push_notifications}")
        print(f"   File: {indico_push_notifications.__file__}")

        # Check if plugin class is available
        from indico_push_notifications import IndicoPushNotificationsPlugin

        print(f"✅ Plugin class imported successfully")
        print(f"   Class: {IndicoPushNotificationsPlugin}")

        return True

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        import traceback

        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ Error during import: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_log_file():
    """Check if log file was created."""
    print("\n" + "=" * 60)
    print("Checking Log File")
    print("=" * 60)

    log_path = Path.home() / "log" / "notify-plugin.log"

    print(f"Log file path: {log_path}")

    if log_path.exists():
        print(f"✅ Log file exists")
        print(f"   Size: {log_path.stat().st_size} bytes")

        # Read last few lines
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                last_lines = lines[-10:] if len(lines) > 10 else lines

            print(f"\nLast {len(last_lines)} lines of log:")
            for line in last_lines:
                print(f"  {line.rstrip()}")

        except Exception as e:
            print(f"⚠️  Could not read log file: {e}")
    else:
        print(f"⚠️  Log file does not exist yet")
        print(f"   It will be created when logger writes first message")

        # Check log directory
        log_dir = log_path.parent
        if log_dir.exists():
            print(f"✅ Log directory exists: {log_dir}")
        else:
            print(f"⚠️  Log directory does not exist: {log_dir}")


def run_all_tests():
    """Run all tests."""
    print("Indico Push Notifications Plugin - Entry Point Test Suite")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Current dir: {os.getcwd()}")
    print(f"Script dir: {os.path.dirname(os.path.abspath(__file__))}")
    print()

    # Run tests
    tests_passed = 0
    tests_total = 0

    # Test 1: Direct import
    tests_total += 1
    if test_direct_import():
        tests_passed += 1

    # Test 2: Entry point discovery
    tests_total += 1
    entry_point = test_entry_point_discovery()
    if entry_point:
        tests_passed += 1

    # Test 3: Entry point loading
    tests_total += 1
    plugin_class = None
    if entry_point:
        plugin_class = test_entry_point_loading(entry_point)
        if plugin_class:
            tests_passed += 1

    # Test 4: Plugin instantiation
    tests_total += 1
    plugin_instance = None
    if plugin_class:
        plugin_instance = test_plugin_instantiation(plugin_class)
        if plugin_instance:
            tests_passed += 1

    # Test 5: Plugin initialization
    tests_total += 1
    if plugin_instance:
        test_plugin_initialization(plugin_instance)
        # Don't count this as pass/fail since it's expected to fail without context
        tests_total -= 1

    # Test 6: Check log file
    tests_total += 1
    check_log_file()
    # Don't count this as pass/fail
    tests_total -= 1

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests passed: {tests_passed}/{tests_total}")

    if tests_passed == tests_total:
        print("\n🎉 All tests passed! Entry point is working correctly.")
        print("Indico should be able to load the plugin.")
    else:
        print(f"\n⚠️  {tests_total - tests_passed} test(s) failed.")
        print("Check the errors above for details.")

    # Recommendations
    print("\n" + "=" * 60)
    print("Next Steps")
    print("=" * 60)
    print("1. Check log file: ~/log/notify-plugin.log")
    print("2. On server, run: python test_entry_point.py")
    print("3. Look for 'ENTRY POINT' messages in the log")
    print("4. If no entry point logs, check entry point registration")
    print("5. Reinstall plugin: pip install -e . --break-system-packages")

    return tests_passed == tests_total


def main():
    """Main function."""
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
