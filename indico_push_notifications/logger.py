"""
Logging module for Indico Push Notifications Plugin.
Provides debug logging to a separate file for troubleshooting.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path


class PluginLogger:
    """Logger for plugin debugging and monitoring."""

    # Default log directory
    LOG_DIR = Path.home() / "log"
    LOG_FILE = "notify-plugin.log"

    def __init__(self, name="indico_push_notifications"):
        """Initialize logger.

        Args:
            name: Logger name (default: "indico_push_notifications")
        """
        self.name = name
        self.logger = None
        self._setup_logger()

    def _setup_logger(self):
        """Setup logger with file and console handlers."""
        # Create logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)

        # Clear any existing handlers
        self.logger.handlers.clear()

        # Create log directory if it doesn't exist
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = self.LOG_DIR / self.LOG_FILE

        # Create formatters
        detailed_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        simple_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
        )

        # File handler (detailed logs)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)

        # Console handler (simple output)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Log initialization
        self.logger.info(f"Plugin logger initialized. Log file: {log_path}")
        self.logger.info(f"Logger name: {self.name}")
        self.logger.info(f"Python version: {os.sys.version}")
        self.logger.info(f"Working directory: {os.getcwd()}")

    def debug(self, msg, *args, **kwargs):
        """Log debug message."""
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """Log info message."""
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """Log warning message."""
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """Log error message."""
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        """Log critical message."""
        self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(msg, *args, **kwargs)

    def log_plugin_load(self, plugin_instance):
        """Log plugin loading information."""
        self.info("=" * 60)
        self.info(f"PLUGIN LOADING: {plugin_instance.name}")
        self.info(f"Friendly name: {plugin_instance.friendly_name}")
        self.info(f"Description: {plugin_instance.description}")
        self.info(f"Category: {plugin_instance.category}")
        self.info(f"Configurable: {plugin_instance.configurable}")
        self.info("=" * 60)

    def log_config(self, config_dict, title="Configuration"):
        """Log configuration dictionary."""
        self.info(f"=== {title} ===")
        for key, value in config_dict.items():
            if isinstance(value, dict):
                self.info(f"  {key}:")
                for subkey, subvalue in value.items():
                    self.info(f"    {subkey}: {subvalue}")
            else:
                # Mask sensitive data
                if any(
                    sensitive in key.lower()
                    for sensitive in ["token", "key", "secret", "password"]
                ):
                    self.info(f"  {key}: {'*' * 8}")
                else:
                    self.info(f"  {key}: {value}")
        self.info("=" * 60)

    def log_import(self, module_name, success=True, error=None):
        """Log module import attempt."""
        if success:
            self.debug(f"Import successful: {module_name}")
        else:
            self.error(f"Import failed: {module_name}")
            if error:
                self.error(f"Import error: {error}")

    def log_signal(self, signal_name, connected=True):
        """Log signal connection."""
        status = "connected" if connected else "disconnected"
        self.debug(f"Signal {signal_name}: {status}")

    def get_log_file_path(self):
        """Get path to log file."""
        return self.LOG_DIR / self.LOG_FILE

    def read_last_lines(self, lines=50):
        """Read last N lines from log file."""
        log_path = self.get_log_file_path()
        if not log_path.exists():
            return "Log file does not exist yet."

        try:
            with open(log_path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                return "".join(last_lines)
        except Exception as e:
            return f"Error reading log file: {e}"

    def clear_log(self):
        """Clear log file (keep backup)."""
        log_path = self.get_log_file_path()
        if log_path.exists():
            backup_path = log_path.with_suffix(".log.backup")
            try:
                import shutil

                shutil.copy2(log_path, backup_path)
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(f"Log cleared at {datetime.now()}\n")
                self.info(f"Log cleared. Backup saved to: {backup_path}")
                return True
            except Exception as e:
                self.error(f"Failed to clear log: {e}")
                return False
        return True


# Global logger instance
_logger_instance = None


def get_logger(name="indico_push_notifications"):
    """Get or create global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = PluginLogger(name)
    return _logger_instance


def setup_logging(name="indico_push_notifications"):
    """Setup logging and return logger instance."""
    return get_logger(name)


# Convenience functions
def debug(msg, *args, **kwargs):
    """Log debug message using global logger."""
    get_logger().debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    """Log info message using global logger."""
    get_logger().info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    """Log warning message using global logger."""
    get_logger().warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    """Log error message using global logger."""
    get_logger().error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    """Log critical message using global logger."""
    get_logger().critical(msg, *args, **kwargs)


def exception(msg, *args, **kwargs):
    """Log exception with traceback using global logger."""
    get_logger().exception(msg, *args, **kwargs)


def log_plugin_load(plugin_instance):
    """Log plugin loading information."""
    get_logger().log_plugin_load(plugin_instance)


def log_config(config_dict, title="Configuration"):
    """Log configuration dictionary."""
    get_logger().log_config(config_dict, title)


def log_import(module_name, success=True, error=None):
    """Log module import attempt."""
    get_logger().log_import(module_name, success, error)


def log_signal(signal_name, connected=True):
    """Log signal connection."""
    get_logger().log_signal(signal_name, connected)


def get_log_file_path():
    """Get path to log file."""
    return get_logger().get_log_file_path()


def read_last_lines(lines=50):
    """Read last N lines from log file."""
    return get_logger().read_last_lines(lines)


def clear_log():
    """Clear log file."""
    return get_logger().clear_log()


# Test function
def test_logging():
    """Test logging functionality."""
    logger = setup_logging()
    logger.info("Testing plugin logger...")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Test configuration logging
    test_config = {
        "telegram_bot_token": "secret_token_123",
        "telegram_bot_username": "@test_bot",
        "webpush_enabled": True,
        "vapid_public_key": "public_key_123",
        "vapid_private_key": "private_key_456",
    }
    logger.log_config(test_config, "Test Configuration")

    logger.info("Logging test completed")
    print(f"Log file: {logger.get_log_file_path()}")


if __name__ == "__main__":
    test_logging()
