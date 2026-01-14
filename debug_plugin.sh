#!/bin/bash

# Indico Push Notifications Plugin - Comprehensive Debug Script
# This script provides complete debugging capabilities for the plugin

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PLUGIN_NAME="indico-push-notifications"
PLUGIN_MODULE="indico_push_notifications"
PLUGIN_DIR="/opt/indico/modules/indico-push-notifications"
INDICO_CONF="/opt/indico/etc/indico.conf"
INDICO_LOG="/var/log/indico/indico.log"
INDICO_ERROR_LOG="/var/log/indico/indico-error.log"
PLUGIN_LOG="$HOME/log/notify-plugin.log"
VENV_PATH="/opt/indico/.venv-3/bin/activate"

# Logging functions
log() {
    echo -e "$1"
}

success() {
    log "${GREEN}[✓] $1${NC}"
}

warning() {
    log "${YELLOW}[!] $1${NC}"
}

error() {
    log "${RED}[✗] $1${NC}"
}

info() {
    log "${BLUE}[i] $1${NC}"
}

debug() {
    log "${CYAN}[~] $1${NC}"
}

header() {
    log "\n${MAGENTA}=== $1 ===${NC}"
}

subheader() {
    log "${BLUE}--- $1 ---${NC}"
}

# Check if running on server
check_environment() {
    if [ ! -d "/opt/indico" ]; then
        error "This script must be run on the Indico server"
        error "Expected /opt/indico directory not found"
        exit 1
    fi

    if [ "$(whoami)" != "indico" ]; then
        warning "Running as $(whoami), recommended to run as 'indico' user"
        warning "Switch with: sudo -u indico -i"
    fi
}

# Activate virtual environment
activate_venv() {
    if [ -f "$VENV_PATH" ]; then
        source "$VENV_PATH"
        info "Virtual environment activated"
    else
        error "Virtual environment not found: $VENV_PATH"
        exit 1
    fi
}

# Check plugin installation
check_installation() {
    header "Plugin Installation Check"

    # Check pip installation
    if pip list | grep -q "$PLUGIN_NAME"; then
        success "Plugin installed via pip"
        pip list | grep "$PLUGIN_NAME"
    else
        error "Plugin NOT installed via pip"
        return 1
    fi

    # Check directory
    if [ -d "$PLUGIN_DIR" ]; then
        success "Plugin directory exists: $PLUGIN_DIR"
    else
        error "Plugin directory missing: $PLUGIN_DIR"
        return 1
    fi

    # Check critical files
    files=(
        "$PLUGIN_DIR/setup.py"
        "$PLUGIN_DIR/indico_push_notifications/__init__.py"
        "$PLUGIN_DIR/requirements.txt"
        "$PLUGIN_DIR/alembic.ini"
    )

    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            success "File exists: $(basename "$file")"
        else
            error "File missing: $(basename "$file")"
            return 1
        fi
    done

    return 0
}

# Check entry points
check_entry_points() {
    header "Entry Points Check"

    python -c "
import pkg_resources

print('Checking entry points...')
found = False
for ep in pkg_resources.iter_entry_points('indico.plugins'):
    print(f'  {ep.name} -> {ep.module_name}')
    if ep.name == '$PLUGIN_MODULE':
        found = True

if found:
    print('✅ Entry point registered')
else:
    print('❌ Entry point NOT registered')

# Try to load entry point
try:
    ep = pkg_resources.get_entry_info('$PLUGIN_NAME', 'indico.plugins', '$PLUGIN_MODULE')
    print(f'✅ Entry point details: {ep.module_name}')
except:
    print('❌ Cannot get entry point details')
"
}

# Check plugin availability in Indico
check_plugin_availability() {
    header "Plugin Availability in Indico"

    if command -v indico >/dev/null 2>&1; then
        info "Checking available plugins..."
        if indico setup list-plugins 2>/dev/null | grep -q "$PLUGIN_MODULE"; then
            success "Plugin is AVAILABLE in Indico"
            indico setup list-plugins 2>/dev/null | grep "$PLUGIN_MODULE"
        else
            error "Plugin is NOT available in Indico"
            return 1
        fi
    else
        warning "indico command not found, skipping availability check"
    fi

    return 0
}

# Check plugin activation status
check_plugin_activation() {
    header "Plugin Activation Status"

    if command -v indico >/dev/null 2>&1; then
        info "Checking active plugins..."
        if indico setup list-plugins --active 2>/dev/null | grep -q "$PLUGIN_MODULE"; then
            success "Plugin is ACTIVE in Indico"
            indico setup list-plugins --active 2>/dev/null | grep "$PLUGIN_MODULE"
            return 0
        else
            warning "Plugin is NOT active in Indico"
            info "Activate with: indico setup activate-plugin $PLUGIN_MODULE"
            return 1
        fi
    else
        warning "indico command not found, skipping activation check"
        return 0
    fi
}

# Check configuration
check_configuration() {
    header "Configuration Check"

    if [ -f "$INDICO_CONF" ]; then
        success "Config file exists: $INDICO_CONF"

        # Check ENABLED_PLUGINS
        subheader "ENABLED_PLUGINS"
        if grep -q "ENABLED_PLUGINS.*$PLUGIN_MODULE" "$INDICO_CONF"; then
            success "Plugin enabled in config"
            grep "ENABLED_PLUGINS" "$INDICO_CONF"
        else
            warning "Plugin NOT explicitly enabled in config"
            info "Add: ENABLED_PLUGINS = ['$PLUGIN_MODULE']"
        fi

        # Check plugin-specific config
        subheader "Plugin Configuration"
        if grep -q "PUSH_NOTIFICATIONS" "$INDICO_CONF"; then
            success "Plugin configuration found"
            grep "PUSH_NOTIFICATIONS" "$INDICO_CONF" | head -5
        else
            warning "No plugin-specific configuration found"
        fi

        # Check for unknown config warnings
        subheader "Configuration Warnings"
        if grep -q "Ignoring unknown config key" "$INDICO_CONF" 2>/dev/null || \
           grep -q "Ignoring unknown config key" /var/log/indico/indico.log 2>/dev/null; then
            warning "Unknown config keys detected (normal during plugin development)"
            grep "Ignoring unknown config key.*PUSH_NOTIFICATIONS" /var/log/indico/indico.log 2>/dev/null | head -5 || true
        fi
    else
        error "Config file not found: $INDICO_CONF"
        return 1
    fi

    return 0
}

# Check database migrations
check_migrations() {
    header "Database Migrations"

    if command -v indico >/dev/null 2>&1; then
        info "Checking plugin migrations..."
        if indico db --plugin "$PLUGIN_MODULE" current 2>/dev/null; then
            success "Plugin migrations found"

            # Check migration status
            info "Migration status:"
            indico db --plugin "$PLUGIN_MODULE" current 2>/dev/null | head -5

            # Check if up to date
            if indico db --plugin "$PLUGIN_MODULE" heads 2>/dev/null | grep -q "(head)"; then
                success "Migrations are up to date"
            else
                warning "Migrations might not be up to date"
                info "Run: indico db upgrade --plugin $PLUGIN_MODULE"
            fi
        else
            warning "Cannot check plugin migrations"
            info "Plugin might not have migrations or not properly installed"
        fi
    else
        warning "indico command not found, skipping migration check"
    fi

    return 0
}

# Check services
check_services() {
    header "System Services"

    subheader "Indico Service"
    if systemctl is-active --quiet indico; then
        success "indico service: RUNNING"
        info "Status: $(systemctl is-active indico)"
        info "Since: $(systemctl show -p ActiveEnterTimestamp indico | cut -d= -f2 2>/dev/null || echo 'unknown')"
    else
        error "indico service: NOT RUNNING"
    fi

    subheader "Indico Celery Service"
    if systemctl is-active --quiet indico-celery; then
        success "indico-celery service: RUNNING"
        info "Status: $(systemctl is-active indico-celery)"
    else
        warning "indico-celery service: NOT RUNNING"
    fi

    # Check if services need restart
    subheader "Service Restart Check"
    INDICO_PID=$(systemctl show -p MainPID indico | cut -d= -f2 2>/dev/null || echo "0")
    if [ "$INDICO_PID" -ne 0 ] && [ -f "$INDICO_CONF" ]; then
        INDICO_START_TIME=$(stat -c %Y "/proc/$INDICO_PID" 2>/dev/null || echo 0)
        CONFIG_MOD_TIME=$(stat -c %Y "$INDICO_CONF" 2>/dev/null || echo 0)
        if [ "$CONFIG_MOD_TIME" -gt "$INDICO_START_TIME" ]; then
            warning "indico.conf was modified after Indico started"
            info "Restart recommended: sudo systemctl restart indico"
        else
            success "No restart needed (config not modified)"
        fi
    fi

    return 0
}

# Check plugin logs
check_plugin_logs() {
    header "Plugin Logs"

    if [ -f "$PLUGIN_LOG" ]; then
        success "Plugin log file exists: $PLUGIN_LOG"
        info "Size: $(wc -l < "$PLUGIN_LOG") lines"
        info "Last modified: $(stat -c %y "$PLUGIN_LOG" 2>/dev/null || echo 'unknown')"

        subheader "Last 10 lines of plugin log:"
        tail -10 "$PLUGIN_LOG" 2>/dev/null || echo "  (cannot read log file)"

        subheader "Recent errors in plugin log:"
        grep -i "error\|exception\|traceback\|failed" "$PLUGIN_LOG" | tail -5 2>/dev/null || \
            echo "  No recent errors found"

        subheader "Plugin initialization messages:"
        grep -i "initialization\|init\|plugin.*load" "$PLUGIN_LOG" | tail -5 2>/dev/null || \
            echo "  No initialization messages found"
    else
        warning "Plugin log file not found: $PLUGIN_LOG"
        info "Log file will be created when plugin logs first message"
        info "Check directory: $HOME/log/"
        ls -la "$HOME/log/" 2>/dev/null || echo "  Log directory does not exist"
    fi

    return 0
}

# Check Indico system logs
check_indico_logs() {
    header "Indico System Logs"

    if [ -f "$INDICO_LOG" ]; then
        success "Indico log file exists: $INDICO_LOG"

        subheader "Recent plugin messages in indico.log:"
        tail -100 "$INDICO_LOG" | grep -i "plugin\|$PLUGIN_MODULE\|push" | tail -5 2>/dev/null || \
            echo "  No recent plugin messages"

        subheader "Recent errors in indico.log:"
        tail -50 "$INDICO_LOG" | grep -i "error.*plugin\|plugin.*error" | tail -3 2>/dev/null || \
            echo "  No recent plugin errors"

        subheader "Indico startup messages:"
        tail -200 "$INDICO_LOG" | grep -i "startup\|starting\|reload\|restart" | tail -3 2>/dev/null || \
            echo "  No startup messages found"
    else
        warning "Indico log file not found: $INDICO_LOG"
    fi

    if [ -f "$INDICO_ERROR_LOG" ]; then
        subheader "Recent errors in indico-error.log:"
        tail -20 "$INDICO_ERROR_LOG" | grep -i "plugin\|$PLUGIN_MODULE" 2>/dev/null || \
            echo "  No plugin errors in error log"
    fi

    return 0
}

# Test plugin import
test_plugin_import() {
    header "Plugin Import Test"

    cd "$PLUGIN_DIR" || {
        error "Cannot change to plugin directory"
        return 1
    }

    python -c "
import sys
sys.path.insert(0, '.')
print('Testing plugin import...')
try:
    import $PLUGIN_MODULE
    print('✅ Plugin module imports successfully')

    from $PLUGIN_MODULE import IndicoPushNotificationsPlugin
    plugin = IndicoPushNotificationsPlugin()
    print(f'✅ Plugin class: {plugin.name}')
    print(f'✅ Friendly name: {plugin.friendly_name}')
    print(f'✅ Description: {plugin.description}')

    # Test default settings
    print(f'✅ Default settings: {len(plugin.default_settings)} keys')
    print(f'✅ User settings: {len(plugin.default_user_settings)} keys')

except ImportError as e:
    print(f'❌ Import error: {e}')
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
"
}

# Test logging functionality
test_logging() {
    header "Logging Functionality Test"

    cd "$PLUGIN_DIR" || {
        error "Cannot change to plugin directory"
        return 1
    }

    python -c "
import sys
sys.path.insert(0, '.')
print('Testing logging functionality...')
try:
    from indico_push_notifications.logger import setup_logging, info, debug, error

    logger = setup_logging('debug_test')
    debug('Debug test message')
    info('Info test message')
    error('Error test message')

    print('✅ Logging test completed')
    print('Check log file: ~/log/notify-plugin.log')

except Exception as e:
    print(f'❌ Logging test failed: {e}')
    import traceback
    traceback.print_exc()
"
}

# Quick fix functions
quick_activate() {
    header "Quick Activation"

    if command -v indico >/dev/null 2>&1; then
        info "Activating plugin..."
        if indico setup activate-plugin "$PLUGIN_MODULE" 2>/dev/null; then
            success "Plugin activated"
        else
            error "Failed to activate plugin"
            return 1
        fi
    else
        error "indico command not found, cannot activate plugin"
        return 1
    fi

    return 0
}

quick_migrate() {
    header "Quick Migration"

    if command -v indico >/dev/null 2>&1; then
        info "Running migrations..."
        if indico db upgrade --plugin "$PLUGIN_MODULE" 2>/dev/null; then
            success "Migrations completed"
        else
            error "Failed to run migrations"
            return 1
        fi
    else
        error "indico command not found, cannot run migrations"
        return 1
    fi

    return 0
}

quick_restart() {
    header "Quick Restart"

    info "Restarting Indico services..."
    if sudo systemctl restart indico indico-celery 2>/dev/null; then
        success "Services restarted"
        info "Waiting 3 seconds for services to start..."
        sleep 3

        # Check services after restart
        if systemctl is-active --quiet indico && systemctl is-active --quiet indico-celery; then
            success "Services are running after restart"
        else
            warning "Some services might not be running properly"
        fi
    else
        error "Failed to restart services"
        return 1
    fi

    return 0
}

quick_reinstall() {
    header "Quick Reinstall"

    cd "$PLUGIN_DIR" || {
        error "Cannot change to plugin directory"
        return 1
    }

    info "Reinstalling plugin..."

    # Backup problematic files
    [ -f "pyproject.toml" ] && mv pyproject.toml pyproject.toml.backup

    # Uninstall
    pip uninstall -y "$PLUGIN_NAME" 2>/dev/null || true

    # Reinstall
    pip install -e . --break-system-packages

    # Restore backup
    [ -f "pyproject.toml.backup" ] && mv pyproject.toml.backup pyproject.toml

    success "Plugin reinstalled"
    return 0
}

# Main diagnostic function
run_diagnostics() {
    header "Indico Push Notifications Plugin - Comprehensive Debug"
    info "Time: $(date)"
    info "Host: $(hostname)"
    info "User: $(whoami)"
    info "Plugin: $PLUGIN_NAME ($PLUGIN_MODULE)"

    check_environment
    activate_venv

    # Run all checks
    local results=()
    local checks=(
        "check_installation"
        "check_entry_points"
        "check_plugin_availability"
        "check_plugin_activation"
        "check_configuration"
        "check_migrations"
        "check_services"
        "check_plugin_logs"
        "check_indico_logs"
        "test_plugin_import"
        "test_logging"
    )

    for check in "${checks[@]}"; do
        if $check; then
            results+=("✅")
        else
            results+=("❌")
        fi
    done

    # Summary
    header "Diagnostic Summary"

    check_names=(
        "Installation"
        "Entry Points"
        "Availability"
        "Activation"
        "Configuration"
        "Migrations"
        "Services"
        "Plugin Logs"
        "Indico Logs"
        "Import Test"
        "Logging Test"
    )

    for i in "${!check_names[@]}"; do
        echo "  ${results[$i]} ${check_names[$i]}"
    done

    passed=$(echo "${results[@]}" | grep -o "✅" | wc -l)
    total=${#checks[@]}

    echo ""
    info "Results: $passed/$total checks passed"

    if [ $passed -eq $total ]; then
        success "All checks passed! Plugin should be working correctly."
        info "Check web interface: Admin → Plugins → Push Notifications"
    else
        warning "$((total - passed)) check(s) failed. See details above."
    fi

    # Recommendations
    header "Recommended Actions"

    if ! indico setup list-plugins --active 2>/dev/null | grep -q "$PLUGIN_MODULE"; then
        echo "1. Activate plugin: indico setup activate-plugin $PLUGIN_MODULE"
    fi

    if [ ! -f "$PLUGIN_LOG" ] || [ ! -s "$PLUGIN_LOG" ]; then
        echo "2. Test logging: Run 'test_logging' function above"
    fi

    echo "3. Restart services if config changed: sudo systemctl restart indico indico-celery"
    echo "4. Monitor logs: tail -f $PLUGIN_LOG"
    echo "5. Check web interface: Admin → Plugins → Push Notifications"

    # Quick commands
    header "Quick Commands"

    echo "Check status: indico setup list-plugins | grep $PLUGIN_MODULE"
    echo "Activate: indico setup activate-plugin $PLUGIN_MODULE"
    echo "Migrations: indico db upgrade --plugin $PLUGIN_MODULE"
    echo "Restart: sudo systemctl restart indico indico-celery"
    echo "Monitor: tail -f $PLUGIN_LOG"
    echo "Debug: $0 test (run all tests)"
}
