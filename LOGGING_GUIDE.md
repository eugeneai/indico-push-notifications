# Indico Push Notifications Plugin - Logging Guide

## Overview

This plugin includes a comprehensive logging system that writes debug information to a separate log file (`~/log/notify-plugin.log`). This helps troubleshoot plugin loading issues and monitor plugin activity.

## Quick Start

### 1. Setup Logging on Server

```bash
# Connect to server
ssh indico@nla2020

# Navigate to plugin directory
cd /opt/indico/modules/indico-push-notifications

# Run setup script
./setup_logging.sh
```

### 2. Monitor Logs in Real-Time

```bash
# Method 1: Direct tail
tail -f ~/log/notify-plugin.log

# Method 2: Use monitoring script
~/monitor_plugin_logs.sh follow
```

### 3. Check Current Status

```bash
# Check log file status
~/monitor_plugin_logs.sh status

# Show recent errors
~/monitor_plugin_logs.sh errors

# Show last 50 lines
~/monitor_plugin_logs.sh tail 50
```

## Log File Location

- **Primary log:** `~/log/notify-plugin.log`
- **Backup logs:** `~/log/notify-plugin.log.backup.*`
- **Log directory:** `~/log/`

## What Gets Logged

### Plugin Initialization
- Plugin loading process
- Module imports (success/failure)
- Signal connections
- Configuration loading

### Runtime Operations
- Notification processing
- Telegram bot interactions
- Web Push operations
- User preference changes
- Error conditions and exceptions

### Debug Information
- Python environment details
- Import paths
- Configuration values (sensitive data masked)
- Signal connections

## Monitoring Commands

### Basic Monitoring
```bash
# Follow logs in real-time
~/monitor_plugin_logs.sh follow

# Show log status (size, last modified, etc.)
~/monitor_plugin_logs.sh status

# Show recent errors with context
~/monitor_plugin_logs.sh errors

# Show last N lines
~/monitor_plugin_logs.sh tail 100
```

### Log Management
```bash
# Clear log (creates backup)
~/monitor_plugin_logs.sh clear

# Manual backup
cp ~/log/notify-plugin.log ~/log/notify-plugin.log.backup.$(date +%Y%m%d_%H%M%S)
```

## Log Rotation

The logging system includes automatic log rotation:
- Logs rotate daily
- Keeps 30 days of history
- Compresses old logs
- Automatically managed by logrotate

Manual rotation check:
```bash
# Check logrotate configuration
sudo logrotate --debug /etc/logrotate.d/indico-push-notifications

# Force rotation
sudo logrotate -f /etc/logrotate.d/indico-push-notifications
```

## Troubleshooting with Logs

### Common Issues and What to Look For

#### 1. Plugin Not Loading
```bash
# Check for initialization messages
grep -i "initialization\|plugin.*load\|import" ~/log/notify-plugin.log | tail -20
```

#### 2. Import Errors
```bash
# Look for import failures
grep -i "import.*error\|failed.*import\|no module" ~/log/notify-plugin.log | tail -10
```

#### 3. Configuration Issues
```bash
# Check configuration loading
grep -i "config\|setting" ~/log/notify-plugin.log | tail -10
```

#### 4. Signal Connection Problems
```bash
# Check signal connections
grep -i "signal\|connect" ~/log/notify-plugin.log | tail -10
```

### Diagnostic Commands

```bash
# Full diagnostic check
cd /opt/indico/modules/indico-push-notifications
python test_logging.py

# Check log file health
ls -la ~/log/notify-plugin.log
wc -l ~/log/notify-plugin.log
tail -5 ~/log/notify-plugin.log

# Monitor plugin activity while testing
tail -f ~/log/notify-plugin.log &
# Then run plugin commands...
```

## Integration with Indico Logs

### Correlating with Indico System Logs
```bash
# Monitor both logs simultaneously
tail -f ~/log/notify-plugin.log /var/log/indico/indico.log | grep -i "plugin\|indico_push"

# Search for plugin references in system logs
grep -i "indico_push_notifications" /var/log/indico/indico.log | tail -20
```

### Timestamp Correlation
Plugin logs use format: `YYYY-MM-DD HH:MM:SS`
Indico logs use format: Check with `head -1 /var/log/indico/indico.log`

## Log Levels

The plugin uses standard Python logging levels:

1. **DEBUG** - Detailed information for debugging
2. **INFO** - General operational information
3. **WARNING** - Warning conditions
4. **ERROR** - Error conditions
5. **CRITICAL** - Critical conditions

To change log level, edit `indico_push_notifications/logger.py`:
```python
# Change this line:
self.logger.setLevel(logging.DEBUG)  # Current: DEBUG
# To:
self.logger.setLevel(logging.INFO)   # Less verbose
```

## Testing Logging System

### Run Comprehensive Test
```bash
cd /opt/indico/modules/indico-push-notifications
python test_logging.py
```

### Quick Test
```bash
cd /opt/indico/modules/indico-push-notifications
python -c "
from indico_push_notifications.logger import setup_logging, info
logger = setup_logging('quick_test')
info('Quick logging test successful')
print('Check ~/log/notify-plugin.log')
"
```

## Security Considerations

### Sensitive Data Masking
The logger automatically masks:
- Tokens (contains 'token' in key name)
- Keys (contains 'key' in key name)
- Secrets (contains 'secret' in key name)
- Passwords (contains 'password' in key name)

Example: `telegram_bot_token: ********`

### File Permissions
- Log directory: `755` (rwxr-xr-x)
- Log files: `644` (rw-r--r--)
- Owned by `indico` user

## Maintenance

### Regular Checks
```bash
# Check log file size
du -h ~/log/notify-plugin.log

# Check disk usage
df -h ~/log/

# Check for old backup files
find ~/log/ -name "*.backup.*" -mtime +30 -ls
```

### Cleanup Old Logs
```bash
# Remove backups older than 60 days
find ~/log/ -name "*.backup.*" -mtime +60 -delete

# Clear current log (with backup)
~/monitor_plugin_logs.sh clear
```

## Common Scenarios

### Scenario 1: Plugin Not Showing in Admin Interface
```bash
# Check initialization logs
~/monitor_plugin_logs.sh errors
grep -i "init\|blueprint\|signal" ~/log/notify-plugin.log | tail -20

# Check Indico logs for plugin references
grep -i "indico_push" /var/log/indico/indico.log | tail -10
```

### Scenario 2: Configuration Not Loading
```bash
# Check config parsing
grep -i "config\|setting\|default" ~/log/notify-plugin.log | tail -15

# Verify config file access
ls -la /opt/indico/etc/indico.conf
grep -i "push_notifications\|enabled_plugins" /opt/indico/etc/indico.conf
```

### Scenario 3: Import Errors
```bash
# Check module imports
grep -i "import\|module\|failed" ~/log/notify-plugin.log | grep -v "successful" | tail -10

# Test imports manually
cd /opt/indico/modules/indico-push-notifications
python -c "import indico_push_notifications; print('Import OK')"
```

## Emergency Procedures

### Log File Too Large
```bash
# Immediate cleanup
cp ~/log/notify-plugin.log ~/log/notify-plugin.log.backup.emergency
echo "Log cleared at $(date)" > ~/log/notify-plugin.log

# Or use the monitor script
~/monitor_plugin_logs.sh clear
```

### Logging Not Working
```bash
# Check Python logging configuration
cd /opt/indico/modules/indico-push-notifications
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
print('Basic logging test')
"

# Check file permissions
ls -la ~/log/
ls -la ~/log/notify-plugin.log

# Test direct file write
echo 'Test at $(date)' >> ~/log/notify-plugin.log
```

## Support and Debugging

### Collect Debug Information
```bash
# Create debug package
DEBUG_DIR="/tmp/plugin_debug_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$DEBUG_DIR"
cp ~/log/notify-plugin.log "$DEBUG_DIR/"
cp /var/log/indico/indico.log "$DEBUG_DIR/" 2>/dev/null || true
indico setup list-plugins > "$DEBUG_DIR/plugins.txt" 2>/dev/null || true
pip list > "$DEBUG_DIR/pip_list.txt"
tar -czf "$DEBUG_DIR.tar.gz" "$DEBUG_DIR"
echo "Debug package: $DEBUG_DIR.tar.gz"
```

### Common Error Messages

1. **"No module named 'indico'"** - Indico not in Python path
2. **"ImportError: cannot import name"** - Circular import or missing dependency
3. **"Permission denied"** - Log file/directory permissions issue
4. **"No handlers could be found"** - Logger not properly initialized

## Best Practices

1. **Regular Monitoring**: Check logs daily during development
2. **Error Alerts**: Set up monitoring for ERROR/CRITICAL messages
3. **Log Retention**: Keep 30 days of logs for debugging
4. **Backup Before Clear**: Always backup before clearing logs
5. **Correlate Logs**: Check both plugin and Indico logs for issues

## Quick Reference Card

```bash
# Setup
./setup_logging.sh

# Monitor
~/monitor_plugin_logs.sh follow
~/monitor_plugin_logs.sh status
~/monitor_plugin_logs.sh errors

# Maintenance
~/monitor_plugin_logs.sh clear
find ~/log/ -name "*.backup.*" -mtime +30 -delete

# Debug
grep -i "error\|exception" ~/log/notify-plugin.log | tail -10
tail -f ~/log/notify-plugin.log /var/log/indico/indico.log | grep -i plugin
```

---
*Last Updated: $(date)*
*For additional help, check SERVER_CONTEXT.md and CHECK_PLUGIN_LOADING.md*