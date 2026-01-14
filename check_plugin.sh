#!/bin/bash

# Indico Push Notifications Plugin - Diagnostic Script
# This script helps diagnose why the plugin is not showing up in Indico

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PLUGIN_NAME="indico-push-notifications"
PLUGIN_MODULE="indico_push_notifications"
INDICO_CONF="/opt/indico/etc/indico.conf"
INDICO_LOG="/var/log/indico/indico.log"
INDICO_ERROR_LOG="/var/log/indico/indico-error.log"

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

# Check if running in Indico environment
check_environment() {
    print_header "Environment Check"

    # Check Python version
    log_info "Python version: $(python --version 2>&1)"

    # Check virtual environment
    if [[ "$VIRTUAL_ENV" == *".venv-3"* ]]; then
        log_success "Running in Indico virtual environment"
    else
        log_warning "Not in Indico virtual environment"
        log_info "Activate with: source /opt/indico/.venv-3/bin/activate"
    fi

    # Check current directory
    log_info "Current directory: $(pwd)"
}

# Check plugin installation
check_installation() {
    print_header "Plugin Installation Check"

    # Check pip installation
    if pip list | grep -q "$PLUGIN_NAME"; then
        log_success "Plugin installed via pip"
        pip list | grep "$PLUGIN_NAME"
    else
        log_error "Plugin NOT installed via pip"
    fi

    # Check if directory exists
    if [ -d "$PLUGIN_MODULE" ]; then
        log_success "Plugin directory exists: $PLUGIN_MODULE/"
    else
        log_error "Plugin directory missing: $PLUGIN_MODULE/"
    fi

    # Check critical files
    critical_files=(
        "$PLUGIN_MODULE/__init__.py"
        "setup.py"
        "alembic.ini"
    )

    for file in "${critical_files[@]}"; do
        if [ -f "$file" ]; then
            log_success "File exists: $file"
        else
            log_error "File missing: $file"
        fi
    done
}

# Check plugin imports
check_imports() {
    print_header "Plugin Import Check"

    # Try to import the plugin
    log_info "Testing plugin import..."
    if python -c "import $PLUGIN_MODULE; print('✅ Plugin imports successfully')" 2>/dev/null; then
        log_success "Plugin imports OK"
    else
        log_error "Plugin import FAILED"
        python -c "import $PLUGIN_MODULE" 2>&1 | head -20
        return 1
    fi

    # Try to import plugin class
    log_info "Testing plugin class import..."
    if python -c "
from $PLUGIN_MODULE import IndicoPushNotificationsPlugin
plugin = IndicoPushNotificationsPlugin()
print(f'✅ Plugin class: {plugin.name}')
print(f'✅ Plugin friendly name: {plugin.friendly_name}')
" 2>/dev/null; then
        log_success "Plugin class imports OK"
    else
        log_error "Plugin class import FAILED"
        python -c "from $PLUGIN_MODULE import IndicoPushNotificationsPlugin" 2>&1 | head -20
        return 1
    fi
}

# Check entry points
check_entry_points() {
    print_header "Entry Points Check"

    log_info "Checking entry points..."
    python -c "
import pkg_resources

print('All indico.plugins entry points:')
found_our_plugin = False
for ep in pkg_resources.iter_entry_points('indico.plugins'):
    print(f'  - {ep.name}: {ep.module_name}')
    if ep.name == '$PLUGIN_MODULE':
        found_our_plugin = True

if found_our_plugin:
    print('✅ Our plugin entry point found')
else:
    print('❌ Our plugin entry point NOT found')

# Try to load our entry point
try:
    ep = pkg_resources.get_entry_info('$PLUGIN_NAME', 'indico.plugins', '$PLUGIN_MODULE')
    print(f'✅ Entry point details: {ep.module_name}')
except Exception as e:
    print(f'❌ Cannot get entry point: {e}')
" 2>&1
}

# Check Indico configuration
check_configuration() {
    print_header "Indico Configuration Check"

    if [ ! -f "$INDICO_CONF" ]; then
        log_error "Indico config file not found: $INDICO_CONF"
        return 1
    fi

    log_success "Indico config file: $INDICO_CONF"

    # Check if plugin is enabled
    if grep -q "ENABLED_PLUGINS.*$PLUGIN_MODULE" "$INDICO_CONF"; then
        log_success "Plugin enabled in indico.conf"
        grep "ENABLED_PLUGINS" "$INDICO_CONF"
    else
        log_error "Plugin NOT enabled in indico.conf"
        log_info "Add to indico.conf: ENABLED_PLUGINS = ['$PLUGIN_MODULE']"
    fi

    # Check plugin-specific configuration
    log_info "Checking plugin configuration..."
    if grep -q "PUSH_NOTIFICATIONS" "$INDICO_CONF"; then
        log_success "Plugin configuration found in indico.conf"
        grep "PUSH_NOTIFICATIONS" "$INDICO_CONF" | head -10
    else
        log_warning "No plugin-specific configuration found"
    fi
}

# Check logs for errors
check_logs() {
    print_header "Logs Check"

    # Check if logs exist
    if [ ! -f "$INDICO_LOG" ]; then
        log_warning "Indico log file not found: $INDICO_LOG"
        return
    fi

    if [ ! -f "$INDICO_ERROR_LOG" ]; then
        log_warning "Indico error log file not found: $INDICO_ERROR_LOG"
        return
    fi

    log_info "Checking recent logs for plugin-related messages..."

    # Check for plugin loading messages
    echo -e "\n${BLUE}Recent plugin messages in indico.log:${NC}"
    tail -50 "$INDICO_LOG" | grep -i "plugin\|$PLUGIN_MODULE\|push" | tail -20 || echo "No recent plugin messages"

    echo -e "\n${BLUE}Recent errors in indico-error.log:${NC}"
    tail -20 "$INDICO_ERROR_LOG" | grep -i "plugin\|$PLUGIN_MODULE\|push\|import\|error" || echo "No recent plugin errors"

    # Check for startup messages
    echo -e "\n${BLUE}Last Indico startup:${NC}"
    tail -100 "$INDICO_LOG" | grep -i "startup\|reload\|restart" | tail -5 || echo "No startup messages found"
}

# Check Indico plugin engine
check_indico_plugins() {
    print_header "Indico Plugin Engine Check"

    log_info "Checking Indico plugin engine..."
    python -c "
import sys
sys.path.insert(0, '/opt/indico')

try:
    from indico.core.plugins import plugin_engine
    print('✅ Indico plugin engine imported')

    # Get active plugins
    active_plugins = list(plugin_engine.get_active_plugins().keys())
    print(f'Active plugins ({len(active_plugins)}): {active_plugins}')

    if '$PLUGIN_MODULE' in active_plugins:
        print('✅ Our plugin is active in Indico')
    else:
        print('❌ Our plugin is NOT active in Indico')

        # Check if plugin is discovered
        all_plugins = list(plugin_engine.get_all_plugins().keys())
        print(f'All discovered plugins ({len(all_plugins)}): {all_plugins}')

        if '$PLUGIN_MODULE' in all_plugins:
            print('⚠️  Plugin discovered but not active')
        else:
            print('❌ Plugin not even discovered')

except ImportError as e:
    print(f'❌ Cannot import Indico: {e}')
except Exception as e:
    print(f'❌ Error checking plugins: {e}')
" 2>&1
}

# Check systemd services
check_services() {
    print_header "System Services Check"

    log_info "Checking Indico services..."

    # Check indico service
    if systemctl is-active --quiet indico; then
        log_success "Indico service is running"
    else
        log_error "Indico service is NOT running"
    fi

    # Check indico-celery service
    if systemctl is-active --quiet indico-celery; then
        log_success "Indico-celery service is running"
    else
        log_warning "Indico-celery service is NOT running"
    fi

    # Check when services were last restarted
    log_info "Service status:"
    echo "indico: $(systemctl is-active indico) - $(systemctl show -p ActiveEnter indico | cut -d= -f2)"
    echo "indico-celery: $(systemctl is-active indico-celery) - $(systemctl show -p ActiveEnter indico-celery | cut -d= -f2)"
}

# Main diagnostic function
run_diagnostics() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Indico Push Notifications Plugin Diagnostic${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo "Plugin: $PLUGIN_NAME"
    echo "Time: $(date)"
    echo

    # Run all checks
    check_environment
    check_installation
    check_imports
    check_entry_points
    check_configuration
    check_logs
    check_indico_plugins
    check_services

    print_header "Diagnostic Summary"

    echo -e "${GREEN}Next steps if plugin is not showing up:${NC}"
    echo "1. Check all errors above"
    echo "2. Make sure plugin is in ENABLED_PLUGINS in indico.conf"
    echo "3. Restart Indico: sudo systemctl restart indico indico-celery"
    echo "4. Check logs after restart: tail -f /var/log/indico/indico.log"
    echo "5. If still not working, try: pip uninstall $PLUGIN_NAME && pip install -e . --break-system-packages"
    echo
    echo -e "${YELLOW}Quick fix commands:${NC}"
    echo "  cd /opt/indico/modules/indico-push-notifications"
    echo "  source /opt/indico/.venv-3/bin/activate"
    echo "  ./reinstall_plugin.sh"
    echo "  sudo systemctl restart indico indico-celery"
}

# Run diagnostics
run_diagnostics

# Exit with appropriate code
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Diagnostic completed successfully${NC}"
    exit 0
else
    echo -e "\n${RED}Diagnostic found issues${NC}"
    exit 1
fi
