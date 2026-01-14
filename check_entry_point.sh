#!/bin/bash

# Indico Push Notifications Plugin - Entry Point Check Script
# This script checks if the plugin entry point is working on the server

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
LOG_FILE="$HOME/log/notify-plugin.log"

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

# Check environment
check_environment() {
    print_header "Environment Check"

    log_info "Host: $(hostname)"
    log_info "User: $(whoami)"
    log_info "Time: $(date)"
    log_info "Current directory: $(pwd)"

    if [ ! -d "/opt/indico" ]; then
        log_error "This script must be run on the Indico server"
        log_error "Expected /opt/indico directory not found"
        exit 1
    fi

    if [ "$(whoami)" != "indico" ]; then
        log_warning "Running as $(whoami), recommended to run as 'indico' user"
        log_info "Switch with: sudo -u indico -i"
    fi
}

# Activate virtual environment
activate_venv() {
    print_header "Virtual Environment"

    VENV_PATH="/opt/indico/.venv-3/bin/activate"

    if [ -f "$VENV_PATH" ]; then
        log_info "Activating virtual environment..."
        source "$VENV_PATH"

        if [[ "$VIRTUAL_ENV" == *".venv-3"* ]]; then
            log_success "Virtual environment activated: $VIRTUAL_ENV"
            log_info "Python: $(python --version 2>&1)"
            log_info "Pip: $(pip --version 2>&1 | head -1)"
        else
            log_warning "Virtual environment might not be activated correctly"
        fi
    else
        log_error "Virtual environment not found: $VENV_PATH"
        exit 1
    fi
}

# Check plugin installation
check_installation() {
    print_header "Plugin Installation"

    if [ ! -d "$PLUGIN_DIR" ]; then
        log_error "Plugin directory not found: $PLUGIN_DIR"
        return 1
    fi

    log_success "Plugin directory: $PLUGIN_DIR"
    cd "$PLUGIN_DIR" || {
        log_error "Cannot change to plugin directory"
        return 1
    }

    # Check pip installation
    log_info "Checking pip installation..."
    if pip list | grep -q "$PLUGIN_NAME"; then
        log_success "Plugin installed via pip"
        pip list | grep "$PLUGIN_NAME"
    else
        log_error "Plugin NOT installed via pip"
        return 1
    fi

    return 0
}

# Check entry points
check_entry_points() {
    print_header "Entry Points Check"

    log_info "Checking entry points with pkg_resources..."

    python -c "
import sys
import pkg_resources

print('=== All indico.plugins entry points ===')
entry_points = list(pkg_resources.iter_entry_points('indico.plugins'))
print(f'Found {len(entry_points)} entry points:')

found_our_plugin = False
for ep in entry_points:
    print(f'  - {ep.name}: {ep.module_name}')
    if ep.name == '$PLUGIN_MODULE':
        found_our_plugin = True

print()
if found_our_plugin:
    print('✅ Our plugin entry point found: $PLUGIN_MODULE')

    # Try to load the entry point
    try:
        ep = pkg_resources.get_entry_info('$PLUGIN_NAME', 'indico.plugins', '$PLUGIN_MODULE')
        print(f'✅ Entry point details:')
        print(f'   Module: {ep.module_name}')
        print(f'   Distribution: {ep.dist}')

        # Try to load the class
        plugin_class = ep.load()
        print(f'✅ Entry point loaded successfully')
        print(f'   Class: {plugin_class}')
        print(f'   Class name: {plugin_class.__name__}')

        # Try to create instance
        plugin_instance = plugin_class()
        print(f'✅ Plugin instance created')
        print(f'   Plugin name: {plugin_instance.name}')
        print(f'   Friendly name: {plugin_instance.friendly_name}')

    except Exception as e:
        print(f'❌ Error loading entry point: {e}')
        import traceback
        traceback.print_exc()

else:
    print('❌ Our plugin entry point NOT found')
    print('   Expected: $PLUGIN_MODULE')
" 2>&1
}

# Check direct import
check_direct_import() {
    print_header "Direct Import Test"

    cd "$PLUGIN_DIR" || return 1

    log_info "Testing direct import of plugin module..."

    python -c "
import sys
sys.path.insert(0, '.')

print('Testing direct import...')
try:
    import $PLUGIN_MODULE
    print('✅ Module imported successfully')
    print(f'   Module: {$PLUGIN_MODULE}')
    print(f'   File: {$PLUGIN_MODULE.__file__}')

    from $PLUGIN_MODULE import IndicoPushNotificationsPlugin
    print('✅ Plugin class imported successfully')

    plugin = IndicoPushNotificationsPlugin()
    print('✅ Plugin instance created')
    print(f'   Name: {plugin.name}')
    print(f'   Friendly name: {plugin.friendly_name}')

except ImportError as e:
    print(f'❌ Import error: {e}')
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
" 2>&1
}

# Check log file
check_log_file() {
    print_header "Log File Check"

    log_info "Checking plugin log file..."

    if [ -f "$LOG_FILE" ]; then
        log_success "Log file exists: $LOG_FILE"
        log_info "Size: $(wc -l < "$LOG_FILE") lines"
        log_info "Last modified: $(stat -c %y "$LOG_FILE" 2>/dev/null || echo 'unknown')"

        echo -e "\n${BLUE}=== Last 15 lines of log ===${NC}"
        tail -15 "$LOG_FILE" 2>/dev/null || echo "  (cannot read log file)"

        echo -e "\n${BLUE}=== Entry point messages ===${NC}"
        grep -i "entry point\|plugin.*load\|initialization" "$LOG_FILE" | tail -10 2>/dev/null || \
            echo "  No entry point messages found"

        echo -e "\n${BLUE}=== Recent errors ===${NC}"
        grep -i "error\|exception\|traceback\|failed" "$LOG_FILE" | tail -5 2>/dev/null || \
            echo "  No recent errors found"
    else
        log_warning "Log file not found: $LOG_FILE"
        log_info "It will be created when plugin logs first message"

        # Check log directory
        LOG_DIR="$(dirname "$LOG_FILE")"
        if [ -d "$LOG_DIR" ]; then
            log_info "Log directory exists: $LOG_DIR"
        else
            log_warning "Log directory does not exist: $LOG_DIR"
            log_info "Create with: mkdir -p $LOG_DIR"
        fi
    fi
}

# Test entry point with logging
test_entry_point_with_logging() {
    print_header "Entry Point Test with Logging"

    cd "$PLUGIN_DIR" || return 1

    log_info "Testing entry point with logging enabled..."

    python -c "
import sys
import os
sys.path.insert(0, '.')

# First, test logging
try:
    from indico_push_notifications.logger import setup_logging, info
    logger = setup_logging('entry_point_test')
    info('=' * 60)
    info('ENTRY POINT TEST STARTED')
    info('=' * 60)
    info('Python: ' + sys.version)
    info('Current dir: ' + os.getcwd())
except Exception as e:
    print(f'❌ Logger setup failed: {e}')
    import traceback
    traceback.print_exc()

# Test entry point
print('\\n=== Testing entry point ===')
try:
    import pkg_resources

    # Find our entry point
    for ep in pkg_resources.iter_entry_points('indico.plugins'):
        if ep.name == '$PLUGIN_MODULE':
            print(f'✅ Found entry point: {ep.name}')

            # Load it
            plugin_class = ep.load()
            print(f'✅ Loaded class: {plugin_class.__name__}')

            # Create instance
            plugin = plugin_class()
            print(f'✅ Created instance: {plugin.name}')

            # Log success
            try:
                from indico_push_notifications.logger import info
                info('Entry point test successful')
                info(f'Plugin: {plugin.name}')
                info('=' * 60)
                info('ENTRY POINT TEST COMPLETED')
                info('=' * 60)
            except:
                pass

            break
    else:
        print('❌ Entry point not found')

except Exception as e:
    print(f'❌ Entry point test failed: {e}')
    import traceback
    traceback.print_exc()
" 2>&1
}

# Check Indico plugin list
check_indico_plugins() {
    print_header "Indico Plugin List"

    if command -v indico >/dev/null 2>&1; then
        log_info "Checking Indico plugin list..."

        echo -e "\n${BLUE}=== All available plugins ===${NC}"
        indico setup list-plugins 2>/dev/null || echo "  (indico command failed)"

        echo -e "\n${BLUE}=== Active plugins ===${NC}"
        indico setup list-plugins --active 2>/dev/null 2>&1 || echo "  (could not get active plugins)"

        echo -e "\n${BLUE}=== Looking for our plugin ===${NC}"
        if indico setup list-plugins 2>/dev/null | grep -q "$PLUGIN_MODULE"; then
            log_success "Plugin found in Indico plugin list"
            indico setup list-plugins 2>/dev/null | grep "$PLUGIN_MODULE"
        else
            log_error "Plugin NOT found in Indico plugin list"
        fi
    else
        log_warning "indico command not found, skipping Indico plugin check"
    fi
}

# Main function
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Indico Push Notifications - Entry Point Check${NC}"
    echo -e "${BLUE}========================================${NC}"

    # Run checks
    check_environment
    activate_venv
    check_installation
    check_entry_points
    check_direct_import
    check_log_file
    test_entry_point_with_logging
    check_indico_plugins

    print_header "Summary"

    echo -e "${GREEN}If entry point is working:${NC}"
    echo "1. Entry point should appear in pkg_resources list"
    echo "2. Plugin should import successfully"
    echo "3. Log file should contain entry point messages"
    echo "4. Plugin should appear in 'indico setup list-plugins'"

    echo -e "\n${YELLOW}If entry point is NOT working:${NC}"
    echo "1. Reinstall plugin: pip install -e . --break-system-packages"
    echo "2. Check setup.py entry_points configuration"
    echo "3. Verify plugin is in Python path"
    echo "4. Check for import errors in log file"

    echo -e "\n${BLUE}Quick commands:${NC}"
    echo "  Reinstall: pip uninstall -y $PLUGIN_NAME && pip install -e . --break-system-packages"
    echo "  Check entry points: python -c \"import pkg_resources; print([ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')])\""
    echo "  Check logs: tail -f $LOG_FILE"
    echo "  Check Indico: indico setup list-plugins | grep $PLUGIN_MODULE"

    echo -e "\n${BLUE}Log file:${NC} $LOG_FILE"
    echo -e "${BLUE}Plugin dir:${NC} $PLUGIN_DIR"
}

# Run main function
main

# Exit with success
exit 0
