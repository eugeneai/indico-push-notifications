#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local diagnostic script for Indico Push Notifications Plugin
This script helps diagnose why the plugin is not showing up in Indico
"""

import os
import subprocess
import sys
from pathlib import Path

import pkg_resources


# Colors for terminal output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.BLUE}{'=' * 50}{Colors.NC}")
    print(f"{Colors.BLUE}  {text}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 50}{Colors.NC}")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}[✓] {text}{Colors.NC}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}[!] {text}{Colors.NC}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}[✗] {text}{Colors.NC}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.BLUE}[i] {text}{Colors.NC}")


def check_python_environment():
    """Check Python environment."""
    print_header("Python Environment Check")

    print_info(f"Python version: {sys.version}")
    print_info(f"Python executable: {sys.executable}")
    print_info(f"Current directory: {os.getcwd()}")

    # Check virtual environment
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        print_success("Running in a virtual environment")
    else:
        print_warning("Not running in a virtual environment")


def check_plugin_files():
    """Check if all required plugin files exist."""
    print_header("Plugin Files Check")

    plugin_dir = Path("indico_push_notifications")
    required_files = [
        plugin_dir / "__init__.py",
        Path("setup.py"),
        Path("alembic.ini"),
        Path("requirements.txt"),
    ]

    all_exist = True
    for file_path in required_files:
        if file_path.exists():
            print_success(f"File exists: {file_path}")
        else:
            print_error(f"File missing: {file_path}")
            all_exist = False

    # Check __init__.py for plugin class
    if (plugin_dir / "__init__.py").exists():
        with open(plugin_dir / "__init__.py", "r") as f:
            content = f.read()
            if "class IndicoPushNotificationsPlugin" in content:
                print_success("Plugin class found in __init__.py")
            else:
                print_error("Plugin class NOT found in __init__.py")
                all_exist = False

    return all_exist


def check_pip_installation():
    """Check if plugin is installed via pip."""
    print_header("PIP Installation Check")

    try:
        # Try to import pkg_resources and check for our package
        dist = pkg_resources.get_distribution("indico-push-notifications")
        print_success(f"Plugin installed via pip: {dist}")
        print_info(f"Version: {dist.version}")
        print_info(f"Location: {dist.location}")
        return True
    except pkg_resources.DistributionNotFound:
        print_error("Plugin NOT installed via pip")
        return False


def check_plugin_import():
    """Check if plugin can be imported."""
    print_header("Plugin Import Check")

    try:
        # Add current directory to path for local imports
        sys.path.insert(0, os.getcwd())

        # Try to import the plugin module
        import indico_push_notifications

        print_success("Plugin module imports successfully")

        # Try to import the plugin class
        from indico_push_notifications import IndicoPushNotificationsPlugin

        print_success("Plugin class imports successfully")

        # Create instance and check properties
        plugin = IndicoPushNotificationsPlugin()
        print_success(f"Plugin instance created: {plugin.name}")
        print_info(f"Friendly name: {plugin.friendly_name}")
        print_info(f"Description: {plugin.description}")

        return True
    except ImportError as e:
        print_error(f"Import error: {e}")
        return False
    except Exception as e:
        print_error(f"Error creating plugin instance: {e}")
        return False


def check_entry_points():
    """Check plugin entry points."""
    print_header("Entry Points Check")

    try:
        print_info("Checking all 'indico.plugins' entry points:")
        found_our_plugin = False

        for ep in pkg_resources.iter_entry_points("indico.plugins"):
            print_info(f"  - {ep.name}: {ep.module_name}")
            if ep.name == "indico_push_notifications":
                found_our_plugin = True

        if found_our_plugin:
            print_success("Our plugin entry point found")
        else:
            print_error("Our plugin entry point NOT found")

        # Try to get specific entry point
        try:
            ep = pkg_resources.get_entry_info(
                "indico-push-notifications",
                "indico.plugins",
                "indico_push_notifications",
            )
            print_success(f"Entry point details: {ep.module_name}")
            return True
        except Exception as e:
            print_error(f"Cannot get entry point details: {e}")
            return False

    except Exception as e:
        print_error(f"Error checking entry points: {e}")
        return False


def check_setup_py():
    """Check setup.py configuration."""
    print_header("setup.py Configuration Check")

    try:
        with open("setup.py", "r") as f:
            content = f.read()

        # Check for entry_points configuration
        if "'indico.plugins'" in content and "indico_push_notifications" in content:
            print_success("Entry points configured in setup.py")
        else:
            print_error("Entry points NOT configured in setup.py")

        # Check for plugin name
        if 'name="indico-push-notifications"' in content:
            print_success("Plugin name configured correctly")
        else:
            print_warning("Plugin name might be different")

        return True
    except FileNotFoundError:
        print_error("setup.py not found")
        return False
    except Exception as e:
        print_error(f"Error reading setup.py: {e}")
        return False


def check_dependencies():
    """Check plugin dependencies."""
    print_header("Dependencies Check")

    try:
        with open("requirements.txt", "r") as f:
            requirements = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]

        print_info(f"Found {len(requirements)} dependencies in requirements.txt")

        missing_deps = []
        for req in requirements:
            try:
                # Try to parse requirement
                req_obj = pkg_resources.Requirement.parse(
                    req.split("==")[0] if "==" in req else req
                )
                try:
                    pkg_resources.get_distribution(req_obj)
                    print_success(f"Dependency installed: {req}")
                except pkg_resources.DistributionNotFound:
                    print_warning(f"Dependency NOT installed: {req}")
                    missing_deps.append(req)
            except Exception as e:
                print_warning(f"Cannot parse requirement '{req}': {e}")

        if missing_deps:
            print_error(f"Missing {len(missing_deps)} dependencies")
            print_info("Install with: pip install " + " ".join(missing_deps))
            return False
        else:
            print_success("All dependencies are installed")
            return True

    except FileNotFoundError:
        print_error("requirements.txt not found")
        return False
    except Exception as e:
        print_error(f"Error checking dependencies: {e}")
        return False


def check_indico_integration():
    """Check basic Indico integration."""
    print_header("Indico Integration Check")

    try:
        # Try to import Indico core modules
        try:
            from indico.core.plugins import IndicoPlugin

            print_success("IndicoPlugin base class available")
        except ImportError:
            print_error("Cannot import IndicoPlugin - Indico might not be installed")
            return False

        # Check if our plugin inherits from IndicoPlugin
        from indico_push_notifications import IndicoPushNotificationsPlugin

        if issubclass(IndicoPushNotificationsPlugin, IndicoPlugin):
            print_success("Our plugin correctly inherits from IndicoPlugin")
        else:
            print_error("Our plugin does NOT inherit from IndicoPlugin")
            return False

        # Check plugin metadata
        plugin = IndicoPushNotificationsPlugin()
        required_attrs = ["name", "friendly_name", "description", "configurable"]
        for attr in required_attrs:
            if hasattr(plugin, attr):
                print_success(f"Plugin has attribute: {attr}")
            else:
                print_error(f"Plugin missing attribute: {attr}")
                return False

        return True

    except ImportError as e:
        print_error(f"Cannot import Indico modules: {e}")
        print_info("Make sure Indico is installed in the current environment")
        return False
    except Exception as e:
        print_error(f"Error checking Indico integration: {e}")
        return False


def run_quick_test():
    """Run a quick test of plugin functionality."""
    print_header("Quick Functionality Test")

    try:
        from indico_push_notifications import IndicoPushNotificationsPlugin

        plugin = IndicoPushNotificationsPlugin()

        # Test default settings
        default_settings = plugin.default_settings
        print_info(f"Default settings keys: {list(default_settings.keys())}")

        # Test user settings
        user_settings = plugin.default_user_settings
        print_info(f"User settings keys: {list(user_settings.keys())}")

        # Test that plugin has init method
        if hasattr(plugin, "init") and callable(plugin.init):
            print_success("Plugin has init() method")
        else:
            print_error("Plugin missing init() method")

        # Test that plugin has get_blueprints method
        if hasattr(plugin, "get_blueprints") and callable(plugin.get_blueprints):
            print_success("Plugin has get_blueprints() method")
        else:
            print_error("Plugin missing get_blueprints() method")

        return True

    except Exception as e:
        print_error(f"Quick test failed: {e}")
        return False


def generate_fix_commands():
    """Generate commands to fix common issues."""
    print_header("Fix Commands")

    print_info("If plugin is not installed via pip:")
    print("  pip install -e .")
    print()

    print_info("If entry points are missing:")
    print("  pip uninstall indico-push-notifications -y")
    print("  pip install -e .")
    print()

    print_info("If dependencies are missing:")
    print("  pip install -r requirements.txt")
    print()

    print_info("To check installation in development mode:")
    print("  python setup.py develop")
    print()

    print_info("To verify entry points after installation:")
    print(
        "  python -c \"import pkg_resources; print([ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')])\""
    )


def main():
    """Main diagnostic function."""
    print(f"{Colors.BLUE}{'=' * 60}{Colors.NC}")
    print(
        f"{Colors.BLUE}  Indico Push Notifications Plugin - Local Diagnostic{Colors.NC}"
    )
    print(f"{Colors.BLUE}{'=' * 60}{Colors.NC}")
    print(f"Time: {subprocess.check_output(['date']).decode().strip()}")
    print(f"Directory: {os.getcwd()}")
    print()

    # Run all checks
    checks = [
        ("Python Environment", check_python_environment),
        ("Plugin Files", check_plugin_files),
        ("PIP Installation", check_pip_installation),
        ("Plugin Import", check_plugin_import),
        ("Entry Points", check_entry_points),
        ("setup.py Configuration", check_setup_py),
        ("Dependencies", check_dependencies),
        ("Indico Integration", check_indico_integration),
        ("Quick Test", run_quick_test),
    ]

    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            if result is not None:
                results.append((check_name, result))
        except Exception as e:
            print_error(f"Check '{check_name}' failed with error: {e}")
            results.append((check_name, False))

    # Summary
    print_header("Diagnostic Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print_info(f"Passed: {passed}/{total} checks")

    if passed == total:
        print_success("All checks passed! Plugin should load correctly in Indico.")
    else:
        print_error(f"{total - passed} checks failed. Plugin may not load correctly.")

        # List failed checks
        print_info("\nFailed checks:")
        for check_name, result in results:
            if not result:
                print(f"  - {check_name}")

    # Generate fix commands
    generate_fix_commands()

    print_header("Next Steps")
    print("1. If all checks pass, the plugin should load in Indico")
    print("2. Make sure plugin is in ENABLED_PLUGINS in indico.conf")
    print("3. Restart Indico services after installation")
    print("4. Check Indico logs for plugin loading messages")
    print("5. Access plugin in Indico admin interface")

    return passed == total


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
