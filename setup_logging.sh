#!/bin/bash

# Indico Push Notifications Plugin - Logging Setup Script
# This script sets up debug logging for the plugin on the server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PLUGIN_DIR="/opt/indico/modules/indico-push-notifications"
LOG_DIR="$HOME/log"
LOG_FILE="notify-plugin.log"
LOG_PATH="$LOG_DIR/$LOG_FILE"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Check if running as indico user
check_user() {
    CURRENT_USER=$(whoami)
    if [ "$CURRENT_USER" = "indico" ]; then
        log_success "Running as indico user"
    else
        log_warning "Running as $CURRENT_USER (should be 'indico')"
        log_info "Switch user: sudo -u indico -i"
    fi
}

# Check plugin directory
check_plugin_dir() {
    print_header "Plugin Directory Check"

    if [ -d "$PLUGIN_DIR" ]; then
        log_success "Plugin directory exists: $PLUGIN_DIR"
        cd "$PLUGIN_DIR" || {
            log_error "Cannot change to plugin directory"
            return 1
        }
        log_info "Current directory: $(pwd)"
    else
        log_error "Plugin directory not found: $PLUGIN_DIR"
        return 1
    fi
}

# Create log directory
create_log_dir() {
    print_header "Log Directory Setup"

    if [ -d "$LOG_DIR" ]; then
        log_success "Log directory already exists: $LOG_DIR"
    else
        log_info "Creating log directory: $LOG_DIR"
        mkdir -p "$LOG_DIR"
        if [ $? -eq 0 ]; then
            log_success "Log directory created: $LOG_DIR"
        else
            log_error "Failed to create log directory"
            return 1
        fi
    fi

    # Set permissions
    log_info "Setting permissions on log directory..."
    chmod 755 "$LOG_DIR"
    log_success "Permissions set: 755"

    # Check if log file exists
    if [ -f "$LOG_PATH" ]; then
        log_info "Log file already exists: $LOG_PATH"
        log_info "Size: $(du -h "$LOG_PATH" | cut -f1)"
        log_info "Last modified: $(stat -c %y "$LOG_PATH")"
    else
        log_info "Log file will be created on first log message: $LOG_PATH"
    fi
}

# Test logging functionality
test_logging() {
    print_header "Testing Logging Functionality"

    log_info "Running logging test..."

    # Create test script
    TEST_SCRIPT="/tmp/test_plugin_logging.py"
    cat > "$TEST_SCRIPT" << 'EOF'
#!/usr/bin/env python3
"""
Test script for plugin logging.
"""
import sys
import os

# Add plugin directory to path
sys.path.insert(0, '/opt/indico/modules/indico-push-notifications')

try:
    from indico_push_notifications.logger import setup_logging, info, error, log_config

    # Setup logging
    logger = setup_logging("test_setup")

    # Test logging
    info("=" * 60)
    info("LOGGING TEST FROM SETUP SCRIPT")
    info("=" * 60)
    info("Python version: %s", sys.version)
    info("Current directory: %s", os.getcwd())
    info("User: %s", os.getenv('USER', 'unknown'))

    # Test configuration logging
    test_config = {
        "test": True,
        "plugin_name": "indico_push_notifications",
        "log_file": os.path.expanduser("~/log/notify-plugin.log")
    }

    log_config(test_config, "Test Configuration")

    info("Logging test completed successfully")
    print("✅ Logging test completed")
    print("Check log file: ~/log/notify-plugin.log")

except Exception as e:
    print(f"❌ Logging test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

    # Run test
    log_info "Executing test script..."
    if python3 "$TEST_SCRIPT"; then
        log_success "Logging test completed successfully"
    else
        log_error "Logging test failed"
        return 1
    fi

    # Cleanup
    rm -f "$TEST_SCRIPT"
}

# Check current logs
check_current_logs() {
    print_header "Current Logs Check"

    if [ -f "$LOG_PATH" ]; then
        log_info "Current log file: $LOG_PATH"
        log_info "File size: $(wc -l < "$LOG_PATH") lines"

        echo -e "\n${BLUE}Last 10 lines of log:${NC}"
        tail -10 "$LOG_PATH" 2>/dev/null || echo "  (empty or cannot read)"

        echo -e "\n${BLUE}Recent errors (if any):${NC}"
        grep -i "error\|exception\|traceback" "$LOG_PATH" | tail -5 2>/dev/null || echo "  No recent errors found"
    else
        log_info "Log file does not exist yet: $LOG_PATH"
        log_info "It will be created when plugin logs first message"
    fi
}

# Setup log rotation
setup_log_rotation() {
    print_header "Log Rotation Setup"

    # Check if logrotate is installed
    if ! command -v logrotate &> /dev/null; then
        log_warning "logrotate not installed. Manual log rotation required."
        return 0
    fi

    # Create logrotate configuration
    LOGROTATE_CONF="/etc/logrotate.d/indico-push-notifications"

    log_info "Creating logrotate configuration: $LOGROTATE_CONF"

    sudo tee "$LOGROTATE_CONF" > /dev/null << EOF
$LOG_PATH {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 indico indico
    sharedscripts
    postrotate
        # Restart Indico to reopen log files if needed
        systemctl try-reload-or-restart indico > /dev/null 2>&1 || true
    endscript
}
EOF

    if [ $? -eq 0 ]; then
        log_success "Logrotate configuration created"
        log_info "Configuration:"
        cat "$LOGROTATE_CONF"

        # Test logrotate configuration
        log_info "Testing logrotate configuration..."
        if sudo logrotate --debug "$LOGROTATE_CONF"; then
            log_success "Logrotate configuration test passed"
        else
            log_warning "Logrotate configuration test had issues"
        fi
    else
        log_error "Failed to create logrotate configuration"
    fi
}

# Create monitoring script
create_monitoring_script() {
    print_header "Monitoring Script Setup"

    MONITOR_SCRIPT="$HOME/monitor_plugin_logs.sh"

    log_info "Creating monitoring script: $MONITOR_SCRIPT"

    cat > "$MONITOR_SCRIPT" << 'EOF'
#!/bin/bash
# Plugin Log Monitor Script
# Usage: ./monitor_plugin_logs.sh [follow|status|errors|clear]

set -e

LOG_FILE="$HOME/log/notify-plugin.log"
LOG_DIR="$HOME/log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    echo "Plugin Log Monitor"
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  follow      Follow log file in real-time (default)"
    echo "  status      Show log file status"
    echo "  errors      Show recent errors"
    echo "  clear       Clear log file (with backup)"
    echo "  tail [N]    Show last N lines (default: 20)"
    echo "  help        Show this help"
}

check_log_file() {
    if [ ! -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}Log file does not exist: $LOG_FILE${NC}"
        echo "It will be created when plugin logs first message."
        return 1
    fi
    return 0
}

cmd_follow() {
    check_log_file || return 1
    echo -e "${BLUE}Following log file: $LOG_FILE${NC}"
    echo -e "${BLUE}Press Ctrl+C to stop${NC}"
    echo ""
    tail -f "$LOG_FILE"
}

cmd_status() {
    echo -e "${BLUE}=== Log File Status ===${NC}"
    echo "Log file: $LOG_FILE"

    if [ -f "$LOG_FILE" ]; then
        echo "Exists: Yes"
        echo "Size: $(du -h "$LOG_FILE" | cut -f1)"
        echo "Lines: $(wc -l < "$LOG_FILE")"
        echo "Last modified: $(stat -c %y "$LOG_FILE")"
        echo ""
        echo -e "${BLUE}Last 5 lines:${NC}"
        tail -5 "$LOG_FILE"
    else
        echo -e "${YELLOW}Exists: No${NC}"
        echo "The log file will be created when the plugin logs its first message."
    fi
}

cmd_errors() {
    check_log_file || return 1
    echo -e "${BLUE}=== Recent Errors ===${NC}"
    echo "Log file: $LOG_FILE"
    echo ""

    # Show errors with context
    grep -n -B2 -A2 -i "error\|exception\|traceback\|failed" "$LOG_FILE" | tail -50 || \
        echo "No errors found in log file."
}

cmd_clear() {
    check_log_file || return 1

    echo -e "${YELLOW}=== Clear Log File ===${NC}"
    echo "This will backup the current log and create a new empty one."
    echo -n "Are you sure? (y/N): "
    read -r response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        BACKUP_FILE="${LOG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$LOG_FILE" "$BACKUP_FILE"
        > "$LOG_FILE"
        echo -e "${GREEN}Log cleared. Backup saved to: $BACKUP_FILE${NC}"
    else
        echo "Operation cancelled."
    fi
}

cmd_tail() {
    check_log_file || return 1
    LINES=${1:-20}
    echo -e "${BLUE}=== Last $LINES lines ===${NC}"
    tail -n "$LINES" "$LOG_FILE"
}

# Main
case "$1" in
    follow|"")
        cmd_follow
        ;;
    status)
        cmd_status
        ;;
    errors)
        cmd_errors
        ;;
    clear)
        cmd_clear
        ;;
    tail)
        cmd_tail "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac
EOF

    chmod +x "$MONITOR_SCRIPT"

    if [ $? -eq 0 ]; then
        log_success "Monitoring script created: $MONITOR_SCRIPT"
        log_info "Usage:"
        echo "  $MONITOR_SCRIPT follow     # Follow logs in real-time"
        echo "  $MONITOR_SCRIPT status     # Show log status"
        echo "  $MONITOR_SCRIPT errors     # Show recent errors"
        echo "  $MONITOR_SCRIPT tail 50    # Show last 50 lines"
        echo "  $MONITOR_SCRIPT clear      # Clear log (with backup)"
    else
        log_error "Failed to create monitoring script"
    fi
}

# Main function
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Indico Push Notifications - Logging Setup${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo "Time: $(date)"
    echo "Host: $(hostname)"
    echo "User: $(whoami)"
    echo ""

    # Run setup steps
    check_user
    check_plugin_dir
    create_log_dir
    test_logging
    check_current_logs
    setup_log_rotation
    create_monitoring_script

    print_header "Setup Complete"

    echo -e "${GREEN}✅ Logging setup completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}Summary:${NC}"
    echo "  Log directory: $LOG_DIR"
    echo "  Log file: $LOG_PATH"
    echo "  Monitoring script: $HOME/monitor_plugin_logs.sh"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Check log file: tail -f $LOG_PATH"
    echo "2. Use monitor script: $HOME/monitor_plugin_logs.sh"
    echo "3. Restart Indico to apply logging: sudo systemctl restart indico"
    echo "4. Check plugin logs in real-time: $HOME/monitor_plugin_logs.sh follow"
    echo ""
    echo -e "${YELLOW}Quick commands:${NC}"
    echo "  tail -f $LOG_PATH"
    echo "  $HOME/monitor_plugin_logs.sh status"
    echo "  $HOME/monitor_plugin_logs.sh errors"
}

# Run main function
main

# Exit with success
exit 0
