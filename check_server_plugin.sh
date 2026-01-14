#!/bin/bash

# Indico Push Notifications Plugin - Server Diagnostic Script
# This script helps diagnose why the plugin is not showing up in Indico on the server

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
PLUGIN_DIR="/opt/indico/modules/indico-push-notifications"
INDICO_CONF="/opt/indico/etc/indico.conf"
INDICO_LOG="/var/log/indico/indico.log"
INDICO_ERROR_LOG="/var/log/indico/indico-error.log"
VENV_PATH="/opt/indico/.venv-3/bin/activate"

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
    print_header "User Check"

    CURRENT_USER=$(whoami)
    if [ "$CURRENT_USER" = "indico" ]; then
        log_success "Running as indico user"
    else
        log_warning "Running as $CURRENT_USER (should be 'indico')"
        log_info "Switch user: sudo -u indico -i"
    fi
}

# Activate Indico virtual environment
activate_venv() {
    if [ -f "$VENV_PATH" ]; then
        log_info "Activating Indico virtual environment..."
        source "$VENV_PATH"
        if [[ "$VIRTUAL_ENV" == *".venv-3"* ]]; then
            log_success "Virtual environment activated: $VIRTUAL_ENV"
        else
            log_warning "Virtual environment might not be activated correctly"
        fi
    else
        log_error "Virtual environment not found: $VENV_PATH"
        return 1
    fi
}

# Check plugin installation
check_installation() {
    print_header "Plugin Installation Check"

    # Check if we're in plugin directory
    if [ "$(pwd)" != "$PLUGIN_DIR" ]; then
        log_info "Changing to plugin directory: $PLUGIN_DIR"
        cd "$PLUGIN_DIR" || {
            log_error "Cannot change to plugin directory"
            return 1
        }
    fi

    # Check pip installation
    log_info "Checking pip installation..."
    if pip list | grep -q "$PLUGIN_NAME"; then
        log_success "Plugin installed via pip"
        pip list | grep "$PLUGIN_NAME"
    else
        log_error "Plugin NOT installed via pip"
        return 1
    fi

    # Check directory structure
    log_info "Checking plugin structure..."
    if [ -d "indico_push_notifications" ]; then
        log_success "Plugin directory exists: indico_push_notifications/"
    else
        log_error "Plugin directory missing: indico_push_notifications/"
        return 1
    fi

    # Check critical files
    critical_files=(
        "indico_push_notifications/__init__.py"
        "setup.py"
        "alembic.ini"
        "requirements.txt"
    )

    for file in "${critical_files[@]}"; do
        if [ -f "$file" ]; then
            log_success "File exists: $file"
        else
            log_error "File missing: $file"
            return 1
        fi
    done

    # Check plugin class in __init__.py
    if grep -q "class IndicoPushNotificationsPlugin" "indico_push_notifications/__init__.py"; then
        log_success "Plugin class found in __init__.py"
    else
        log_error "Plugin class NOT found in __init__.py"
        return 1
    fi
}

# Check plugin imports
check_imports() {
    print_header "Plugin Import Check"

    log_info "Testing plugin import..."
    if python -c "
import sys
sys.path.insert(0, '.')
import $PLUGIN_MODULE
print('✅ Plugin imports successfully')
" 2>/dev/null; then
        log_success "Plugin imports OK"
    else
        log_error "Plugin import FAILED"
        python -c "
import sys
sys.path.insert(0, '.')
import $PLUGIN_MODULE
" 2>&1 | head -20
        return 1
    fi

    log_info "Testing plugin class import..."
    if python -c "
import sys
sys.path.insert(0, '.')
from $PLUGIN_MODULE import IndicoPushNotificationsPlugin
plugin = IndicoPushNotificationsPlugin()
print(f'✅ Plugin class: {plugin.name}')
print(f'✅ Plugin friendly name: {plugin.friendly_name}')
" 2>/dev/null; then
        log_success "Plugin class imports OK"
    else
        log_error "Plugin class import FAILED"
        python -c "
import sys
sys.path.insert(0, '.')
from $PLUGIN_MODULE import IndicoPushNotificationsPlugin
" 2>&1 | head -20
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

    # Check if entry point was found
    if python -c "
import pkg_resources
for ep in pkg_resources.iter_entry_points('indico.plugins'):
    if ep.name == '$PLUGIN_MODULE':
        exit(0)
exit(1)
" 2>/dev/null; then
        return 0
    else
        return 1
    fi
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
    log_info "Checking ENABLED_PLUGINS..."
    if grep -q "ENABLED_PLUGINS.*$PLUGIN_MODULE" "$INDICO_CONF"; then
        log_success "Plugin enabled in indico.conf"
        grep "ENABLED_PLUGINS" "$INDICO_CONF"
    elif grep -q "ENABLED_PLUGINS" "$INDICO_CONF"; then
        log_warning "Plugin NOT enabled in indico.conf"
        log_info "Current ENABLED_PLUGINS:"
        grep "ENABLED_PLUGINS" "$INDICO_CONF"
        log_info "Add '$PLUGIN_MODULE' to the list"
    else
        log_error "ENABLED_PLUGINS not found in indico.conf"
        log_info "Add: ENABLED_PLUGINS = ['$PLUGIN_MODULE']"
    fi

    # Check plugin-specific configuration
    log_info "Checking plugin configuration..."
    if grep -q "PUSH_NOTIFICATIONS" "$INDICO_CONF"; then
        log_success "Plugin configuration found in indico.conf"
        grep "PUSH_NOTIFICATIONS" "$INDICO_CONF" | head -10
    else
        log_warning "No plugin-specific configuration found"
        log_info "Add PUSH_NOTIFICATIONS configuration to indico.conf"
    fi
}

# Check Indico plugin engine
check_indico_plugins() {
    print_header "Indico Plugin Engine Check"

    log_info "Checking Indico plugin engine..."
    python -c "
import sys
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
            print('   Check ENABLED_PLUGINS in indico.conf')
        else:
            print('❌ Plugin not even discovered')
            print('   Check entry points and installation')

except ImportError as e:
    print(f'❌ Cannot import Indico: {e}')
except Exception as e:
    print(f'❌ Error checking plugins: {e}')
    import traceback
    traceback.print_exc()
" 2>&1
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
    tail -100 "$INDICO_LOG" | grep -i "plugin\|$PLUGIN_MODULE\|push" | tail -20 || echo "No recent plugin messages"

    echo -e "\n${BLUE}Recent errors in indico-error.log:${NC}"
    tail -50 "$INDICO_ERROR_LOG" | grep -i "plugin\|$PLUGIN_MODULE\|push\|import\|error" || echo "No recent plugin errors"

    # Check for startup messages
    echo -e "\n${BLUE}Last Indico startup:${NC}"
    tail -200 "$INDICO_LOG" | grep -i "startup\|reload\|restart\|starting" | tail -5 || echo "No startup messages found"
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

    # Check service status
    log_info "Service status details:"
    echo "indico: $(systemctl is-active indico) - Last restart: $(systemctl show -p ActiveEnterTimestamp indico | cut -d= -f2 2>/dev/null || echo 'unknown')"
    echo "indico-celery: $(systemctl is-active indico-celery) - Last restart: $(systemctl show -p ActiveEnterTimestamp indico-celery | cut -d= -f2 2>/dev/null || echo 'unknown')"

    # Check if services need restart
    log_info "Checking if services need restart..."
    INDICO_PID=$(systemctl show -p MainPID indico | cut -d= -f2)
    if [ "$INDICO_PID" -ne 0 ]; then
        INDICO_START_TIME=$(stat -c %Y /proc/$INDICO_PID 2>/dev/null || echo 0)
        CONFIG_MOD_TIME=$(stat -c %Y "$INDICO_CONF" 2>/dev/null || echo 0)
        if [ "$CONFIG_MOD_TIME" -gt "$INDICO_START_TIME" ]; then
            log_warning "indico.conf was modified after Indico started - restart needed"
        fi
    fi
}

# Quick reinstall function
quick_reinstall() {
    print_header "Quick Reinstall"

    log_info "Reinstalling plugin..."

    # Backup problematic files
    if [ -f "pyproject.toml" ]; then
        log_info "Backing up pyproject.toml..."
        cp pyproject.toml pyproject.toml.backup
    fi

    # Uninstall
    log_info "Uninstalling plugin..."
    pip uninstall -y "$PLUGIN_NAME" 2>/dev/null || true

    # Reinstall
    log_info "Reinstalling plugin..."
    pip install -e . --break-system-packages

    # Restore backup
    if [ -f "pyproject.toml.backup" ]; then
        log_info "Restoring pyproject.toml..."
        mv pyproject.toml.backup pyproject.toml
    fi

    log_success "Reinstallation complete"
}

# Main diagnostic function
run_diagnostics() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Indico Push Notifications Plugin - Server Diagnostic${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo "Plugin: $PLUGIN_NAME"
    echo "Server: $(hostname)"
    echo "Time: $(date)"
    echo "User: $(whoami)"
    echo

    # Activate virtual environment
    activate_venv

    # Run all checks
    check_user
    check_installation
    check_imports
    check_entry_points
    check_configuration
    check_indico_plugins
    check_logs
    check_services

    print_header "Diagnostic Summary"

    echo -e "${GREEN}If plugin is not showing up:${NC}"
    echo "1. Check ENABLED_PLUGINS in $INDICO_CONF"
    echo "2. Restart Indico: sudo systemctl restart indico indico-celery"
    echo "3. Check logs: tail -f $INDICO_LOG | grep -i plugin"
    echo "4. Verify entry points are registered"
    echo "5. Make sure plugin is installed in development mode: pip install -e ."

    echo -e "\n${YELLOW}Quick fix sequence:${NC}"
    echo "  cd $PLUGIN_DIR"
    echo "  source $VENV_PATH"
    echo "  pip uninstall -y $PLUGIN_NAME"
    echo "  pip install -e . --break-system-packages"
    echo "  sudo systemctl restart indico indico-celery"
    echo "  tail -f $INDICO_LOG | grep -i plugin"
}

# Parse command line arguments
case "$1" in
    reinstall)
        activate_venv
        cd "$PLUGIN_DIR" || exit 1
        quick_reinstall
        echo -e "\n${YELLOW}Don't forget to restart Indico:${NC}"
        echo "  sudo systemctl restart indico indico-celery"
        ;;
    logs)
        check_logs
        ;;
    config)
        check_configuration
        ;;
    plugins)
        activate_venv
        check_indico_plugins
        ;;
    *)
        run_diagnostics
        ;;
esac

# Exit with appropriate code
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Diagnostic completed${NC}"
    exit 0
else
    echo -e "\n${RED}Diagnostic found issues${NC}"
    exit 1
fi
