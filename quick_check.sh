#!/bin/bash

# Indico Push Notifications Plugin - Quick Check Script
# Run this on the server to quickly check if plugin is loading

set -e

# Colors
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

header() {
    log "\n${BLUE}=== $1 ===${NC}"
}

# Check if running on server
check_server() {
    if [ ! -d "/opt/indico" ]; then
        error "This script should be run on the Indico server"
        error "Expected /opt/indico directory"
        exit 1
    fi
}

# Activate environment
activate_env() {
    if [ -f "/opt/indico/.venv-3/bin/activate" ]; then
        source "/opt/indico/.venv-3/bin/activate"
        info "Activated Indico virtual environment"
    else
        warning "Could not find virtual environment at /opt/indico/.venv-3/bin/activate"
    fi
}

# Check 1: Plugin installation
check_installation() {
    header "1. Plugin Installation"

    if pip list | grep -q "$PLUGIN_NAME"; then
        success "Plugin installed via pip"
        pip list | grep "$PLUGIN_NAME"
    else
        error "Plugin NOT installed via pip"
        return 1
    fi

    if [ -d "$PLUGIN_DIR" ]; then
        success "Plugin directory exists: $PLUGIN_DIR"
    else
        error "Plugin directory missing: $PLUGIN_DIR"
        return 1
    fi

    return 0
}

# Check 2: Entry points
check_entry_points() {
    header "2. Entry Points"

    python -c "
import pkg_resources

print('Checking entry points...')
found = False
for ep in pkg_resources.iter_entry_points('indico.plugins'):
    if ep.name == '$PLUGIN_MODULE':
        found = True
        print('✅ Found: ' + ep.name + ' -> ' + ep.module_name)

if found:
    print('✅ Entry point registered')
else:
    print('❌ Entry point NOT found')
    print('Available entry points:')
    for ep in pkg_resources.iter_entry_points('indico.plugins'):
        print('  - ' + ep.name + ' -> ' + ep.module_name)
" 2>&1

    # Check return value
    python -c "
import pkg_resources
for ep in pkg_resources.iter_entry_points('indico.plugins'):
    if ep.name == '$PLUGIN_MODULE':
        exit(0)
exit(1)
" >/dev/null 2>&1

    if [ $? -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# Check 3: Configuration
check_configuration() {
    header "3. Indico Configuration"

    if [ ! -f "$INDICO_CONF" ]; then
        error "Config file not found: $INDICO_CONF"
        return 1
    fi

    success "Config file exists: $INDICO_CONF"

    # Check ENABLED_PLUGINS
    if grep -q "ENABLED_PLUGINS.*$PLUGIN_MODULE" "$INDICO_CONF"; then
        success "Plugin enabled in indico.conf"
        grep "ENABLED_PLUGINS" "$INDICO_CONF"
    else
        error "Plugin NOT enabled in indico.conf"
        info "Add to $INDICO_CONF:"
        info "ENABLED_PLUGINS = ['$PLUGIN_MODULE']"
        return 1
    fi

    return 0
}

# Check 4: Plugin import
check_import() {
    header "4. Plugin Import Test"

    cd "$PLUGIN_DIR" || {
        error "Cannot cd to $PLUGIN_DIR"
        return 1
    }

    python -c "
import sys
sys.path.insert(0, '.')
try:
    import $PLUGIN_MODULE
    print('✅ Plugin imports successfully')

    from $PLUGIN_MODULE import IndicoPushNotificationsPlugin
    plugin = IndicoPushNotificationsPlugin()
    print(f'✅ Plugin class: {plugin.name}')
    print(f'✅ Friendly name: {plugin.friendly_name}')
    exit(0)
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
" 2>&1

    return $?
}

# Check 5: Indico plugin engine
check_indico_plugins() {
    header "5. Indico Plugin Engine"

    python -c "
try:
    from indico.core.plugins import plugin_engine
    print('✅ Indico plugin engine loaded')

    active = list(plugin_engine.get_active_plugins().keys())
    print(f'Active plugins ({len(active)}): {active}')

    if '$PLUGIN_MODULE' in active:
        print('✅ Our plugin is ACTIVE in Indico')
        exit(0)
    else:
        print('❌ Our plugin is NOT active in Indico')

        # Check all discovered plugins
        all_plugins = list(plugin_engine.get_all_plugins().keys())
        print(f'All plugins ({len(all_plugins)}): {all_plugins}')

        if '$PLUGIN_MODULE' in all_plugins:
            print('⚠️  Plugin discovered but not active')
            print('   Check ENABLED_PLUGINS in indico.conf')
        else:
            print('❌ Plugin not discovered at all')
            print('   Check entry points and installation')
        exit(1)

except ImportError as e:
    print(f'❌ Cannot import Indico: {e}')
    exit(1)
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
" 2>&1

    return $?
}

# Check 6: Logs
check_logs() {
    header "6. Recent Logs"

    if [ ! -f "$INDICO_LOG" ]; then
        warning "Log file not found: $INDICO_LOG"
        return 0
    fi

    info "Last 10 lines of indico.log:"
    tail -10 "$INDICO_LOG"

    info "\nSearching for plugin messages..."
    if tail -50 "$INDICO_LOG" | grep -i "plugin\|$PLUGIN_MODULE\|push" >/dev/null; then
        success "Found plugin messages in logs"
        tail -50 "$INDICO_LOG" | grep -i "plugin\|$PLUGIN_MODULE\|push" | tail -5
    else
        warning "No recent plugin messages in logs"
    fi

    return 0
}

# Check 7: Services
check_services() {
    header "7. System Services"

    if systemctl is-active --quiet indico; then
        success "Indico service is running"
    else
        error "Indico service is NOT running"
    fi

    if systemctl is-active --quiet indico-celery; then
        success "Indico-celery service is running"
    else
        warning "Indico-celery service is NOT running"
    fi

    info "Service status:"
    echo "  indico: $(systemctl is-active indico)"
    echo "  indico-celery: $(systemctl is-active indico-celery)"

    return 0
}

# Main function
main() {
    log "${BLUE}========================================${NC}"
    log "${BLUE}  Indico Push Notifications - Quick Check${NC}"
    log "${BLUE}========================================${NC}"
    log "Time: $(date)"
    log "Host: $(hostname)"
    log "User: $(whoami)"

    check_server
    activate_env

    # Run checks
    checks=(
        "check_installation"
        "check_entry_points"
        "check_configuration"
        "check_import"
        "check_indico_plugins"
        "check_logs"
        "check_services"
    )

    results=()
    for check in "${checks[@]}"; do
        if $check; then
            results+=("✅")
        else
            results+=("❌")
        fi
    done

    # Summary
    header "SUMMARY"

    check_names=(
        "Installation"
        "Entry Points"
        "Configuration"
        "Import Test"
        "Indico Plugins"
        "Logs"
        "Services"
    )

    for i in "${!check_names[@]}"; do
        echo "  ${results[$i]} ${check_names[$i]}"
    done

    passed=$(echo "${results[@]}" | grep -o "✅" | wc -l)
    total=${#checks[@]}

    log "\n${BLUE}Results: $passed/$total checks passed${NC}"

    if [ $passed -eq $total ]; then
        success "\nAll checks passed! Plugin should be loading correctly."
        info "Check Indico admin interface → Plugins"
    else
        error "\nSome checks failed. Plugin may not be loading."

        header "NEXT STEPS"
        echo "1. Check ENABLED_PLUGINS in $INDICO_CONF"
        echo "2. Restart Indico: sudo systemctl restart indico indico-celery"
        echo "3. Check logs: tail -f $INDICO_LOG | grep -i plugin"
        echo "4. Reinstall plugin:"
        echo "   cd $PLUGIN_DIR"
        echo "   pip uninstall -y $PLUGIN_NAME"
        echo "   pip install -e . --break-system-packages"
    fi

    header "QUICK COMMANDS"
    echo "Check plugin in Indico:"
    echo "  python -c \"from indico.core.plugins import plugin_engine; print('Active:', list(plugin_engine.get_active_plugins().keys()))\""
    echo ""
    echo "Restart services:"
    echo "  sudo systemctl restart indico indico-celery"
    echo ""
    echo "Monitor logs:"
    echo "  tail -f $INDICO_LOG | grep -i plugin"
}

# Run main function
main

# Exit with appropriate code
if [ $? -eq 0 ]; then
    exit 0
else
    exit 1
fi
