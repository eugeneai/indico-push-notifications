#!/usr/bin/env python3
"""
Test script for Indico Push Notifications Plugin logging functionality.
This script tests the logging module and plugin initialization.
"""

import logging
import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_logger_module():
    """Test the logger module directly."""
    print("=" * 60)
    print("Testing logger module...")
    print("=" * 60)

    try:
        from indico_push_notifications.logger import (
            clear_log,
            debug,
            error,
            get_log_file_path,
            get_logger,
            info,
            log_config,
            read_last_lines,
            setup_logging,
            warning,
        )

        # Setup logging
        logger = setup_logging("test_logger")

        # Test basic logging
        logger.info("Testing logger module...")
        debug("Debug message test")
        info("Info message test")
        warning("Warning message test")
        error("Error message test")

        # Test configuration logging
        test_config = {
            "plugin_name": "indico_push_notifications",
            "telegram_enabled": True,
            "webpush_enabled": False,
            "test_token": "secret_123",
            "test_key": "key_456",
        }

        log_config(test_config, "Test Configuration")

        # Get log file path
        log_path = get_log_file_path()
        print(f"Log file: {log_path}")
        print(f"Log file exists: {log_path.exists()}")

        # Read last lines
        print("\nLast 5 lines of log:")
        print(read_last_lines(5))

        print("\n✅ Logger module test completed successfully")
        return True

    except Exception as e:
        print(f"❌ Logger module test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_plugin_import():
    """Test importing the plugin module."""
    print("\n" + "=" * 60)
    print("Testing plugin import...")
    print("=" * 60)

    try:
        # Try to import the plugin
        import indico_push_notifications

        print("✅ Plugin module imported successfully")

        # Check if plugin class exists
        from indico_push_notifications import IndicoPushNotificationsPlugin

        print("✅ Plugin class imported successfully")

        # Create plugin instance
        plugin = IndicoPushNotificationsPlugin()
        print(f"✅ Plugin instance created: {plugin.name}")
        print(f"  Friendly name: {plugin.friendly_name}")
        print(f"  Description: {plugin.description}")
        print(f"  Category: {plugin.category}")

        # Test default settings
        print(f"\nDefault settings keys: {list(plugin.default_settings.keys())}")
        print(f"User settings keys: {list(plugin.default_user_settings.keys())}")

        print("\n✅ Plugin import test completed successfully")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Plugin import test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_plugin_init():
    """Test plugin initialization."""
    print("\n" + "=" * 60)
    print("Testing plugin initialization...")
    print("=" * 60)

    try:
        from indico_push_notifications import IndicoPushNotificationsPlugin

        # Create plugin instance
        plugin = IndicoPushNotificationsPlugin()

        # Try to initialize (this might fail without Indico context, but we can test)
        print("Testing plugin initialization...")

        # Check if init method exists
        if hasattr(plugin, "init") and callable(plugin.init):
            print("✅ Plugin has init() method")

            # Try to call init (might fail without proper context)
            try:
                plugin.init()
                print("✅ Plugin init() called successfully")
            except Exception as e:
                print(
                    f"⚠️  Plugin init() raised exception (expected without Indico context): {type(e).__name__}"
                )
                print(f"   Message: {e}")
        else:
            print("❌ Plugin missing init() method")
            return False

        print("\n✅ Plugin initialization test completed")
        return True

    except Exception as e:
        print(f"❌ Plugin initialization test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_indico_integration():
    """Test basic Indico integration."""
    print("\n" + "=" * 60)
    print("Testing Indico integration...")
    print("=" * 60)

    try:
        # Try to import Indico base class
        from indico.core.plugins import IndicoPlugin

        print("✅ IndicoPlugin base class imported")

        from indico_push_notifications import IndicoPushNotificationsPlugin

        # Check inheritance
        if issubclass(IndicoPushNotificationsPlugin, IndicoPlugin):
            print("✅ Plugin correctly inherits from IndicoPlugin")
        else:
            print("❌ Plugin does NOT inherit from IndicoPlugin")
            return False

        # Create instance and check required attributes
        plugin = IndicoPushNotificationsPlugin()
        required_attrs = ["name", "friendly_name", "description", "configurable"]

        for attr in required_attrs:
            if hasattr(plugin, attr):
                print(f"✅ Plugin has attribute: {attr}")
            else:
                print(f"❌ Plugin missing attribute: {attr}")
                return False

        print("\n✅ Indico integration test completed successfully")
        return True

    except ImportError as e:
        print(f"⚠️  Cannot import Indico modules: {e}")
        print("   This is expected if Indico is not installed in current environment")
        return True  # Not a failure for this test
    except Exception as e:
        print(f"❌ Indico integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_log_file_operations():
    """Test log file operations."""
    print("\n" + "=" * 60)
    print("Testing log file operations...")
    print("=" * 60)

    try:
        from indico_push_notifications.logger import (
            clear_log,
            get_log_file_path,
            info,
            read_last_lines,
        )

        # Get log file path
        log_path = get_log_file_path()
        print(f"Log file path: {log_path}")

        # Check if log directory exists
        log_dir = log_path.parent
        print(f"Log directory: {log_dir}")
        print(f"Log directory exists: {log_dir.exists()}")

        if not log_dir.exists():
            print("Creating log directory...")
            log_dir.mkdir(parents=True, exist_ok=True)
            print(f"Log directory created: {log_dir.exists()}")

        # Write test message
        info("Test message from test_logging.py")

        # Read log
        print("\nReading log file...")
        log_content = read_last_lines(10)
        print("Last 10 lines:")
        print(log_content)

        # Test log clearing (optional)
        print("\nTesting log clearing...")
        response = input("Clear log file? (y/N): ").strip().lower()
        if response == "y":
            if clear_log():
                print("✅ Log cleared successfully")
            else:
                print("⚠️  Log clearing failed or not needed")

        print("\n✅ Log file operations test completed")
        return True

    except Exception as e:
        print(f"❌ Log file operations test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("Indico Push Notifications Plugin - Logging Test Suite")
    print("=" * 60)

    tests = [
        ("Logger Module", test_logger_module),
        ("Plugin Import", test_plugin_import),
        ("Plugin Initialization", test_plugin_init),
        ("Indico Integration", test_indico_integration),
        ("Log File Operations", test_log_file_operations),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\nRunning test: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed successfully!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    # Final instructions
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("1. Check log file: ~/log/notify-plugin.log")
    print("2. Test on server: scp test_logging.py indico@nla2020:/tmp/")
    print(
        "3. Run on server: cd /opt/indico/modules/indico-push-notifications && python /tmp/test_logging.py"
    )
    print("4. Check logs: tail -f ~/log/notify-plugin.log")

    return passed == total


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
