#!/bin/bash

# Indico Push Notifications Plugin - Status Check Script
# This script properly checks plugin status using Indico CLI commands

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PLUGIN_NAME="indico_push_notifications"
PLUGIN_FRIENDLY_NAME="Push Notifications"
INDICO_CONF="/opt/indico/etc/indico.conf"

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
    fi
}

# Check plugin installation via pip
check_pip_installation() {
    print_header "PIP Installation Check"

    if pip list | grep -q "indico-push-notifications"; then
        log_success "Plugin installed via pip"
        pip list | grep "indico-push-notifications"
    else
        log_error "Plugin NOT installed via pip"
        return 1
    fi
}

# Check if plugin is available in Indico
check_plugin_available() {
    print_header "Plugin Availability in Indico"

    log_info "Checking available plugins..."
    if indico setup list-plugins 2>/dev/null | grep -q "$PLUGIN_NAME"; then
        log_success "Plugin is AVAILABLE in Indico"
        indico setup list-plugins 2>/dev/null | grep "$PLUGIN_NAME"
    else
        log_error "Plugin is NOT available in Indico"
        return 1
    fi
}

# Check if plugin is active in Indico
check_plugin_active() {
    print_header "Plugin Activation Status"

    log_info "Checking active plugins..."

    # Try to get active plugins list
    if indico setup list-plugins --active 2>/dev/null | grep -q "$PLUGIN_NAME"; then
        log_success "Plugin is ACTIVE in Indico"
        indico setup list-plugins --active 2>/dev/null | grep "$PLUGIN_NAME"
        return 0
    else
        # Check if plugin is in available list but not active
        if indico setup list-plugins 2>/dev/null | grep -q "$PLUGIN_NAME"; then
            log_warning "Plugin is AVAILABLE but NOT ACTIVE"
            log_info "Activate with: indico setup activate-plugin $PLUGIN_NAME"
            return 1
        else
            log_error "Plugin not found in available plugins"
            return 1
        fi
    fi
}

# Check configuration
check_configuration() {
    print_header "Configuration Check"

    if [ ! -f "$INDICO_CONF" ]; then
        log_error "Indico config file not found: $INDICO_CONF"
        return 1
    fi

    log_success "Config file exists: $INDICO_CONF"

    # Check ENABLED_PLUGINS
    if grep -q "ENABLED_PLUGINS.*$PLUGIN_NAME" "$INDICO_CONF"; then
        log_success "Plugin enabled in indico.conf"
        grep "ENABLED_PLUGINS" "$INDICO_CONF"
    else
        log_warning "Plugin NOT explicitly enabled in indico.conf"
        log_info "Note: Plugins can be activated via CLI or web interface"
    fi

    # Check plugin-specific configuration
    log_info "Checking plugin configuration..."
    if grep -q "PUSH_NOTIFICATIONS" "$INDICO_CONF"; then
        log_success "Plugin configuration found in indico.conf"
        grep "PUSH_NOTIFICATIONS" "$INDICO_CONF" | head -5
    else
        log_warning "No plugin-specific configuration found"
    fi
}

# Check database migrations
check_migrations() {
    print_header "Database Migrations Check"

    log_info "Checking plugin migrations..."

    # Try to check migrations for the plugin
    if indico db --plugin "$PLUGIN_NAME" current 2>/dev/null; then
        log_success "Plugin migrations found"

        # Check if migrations are up to date
        log_info "Checking if migrations are up to date..."
        if indico db --plugin "$PLUGIN_NAME" heads 2>/dev/null | grep -q "(head)"; then
            log_success "Plugin migrations are up to date"
        else
            log_warning "Plugin migrations might not be up to date"
            log_info "Run: indico db upgrade --plugin $PLUGIN_NAME"
        fi
    else
        log_warning "Cannot check plugin migrations"
        log_info "Plugin might not have migrations or not properly installed"
    fi
}

# Check services
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

    # Show service status
    log_info "Service status details:"
    echo "  indico: $(systemctl is-active indico)"
    echo "  indico-celery: $(systemctl is-active indico-celery)"
}

# Check logs for plugin messages
check_logs() {
    print_header "Logs Check"

    INDICO_LOG="/var/log/indico/indico.log"

    if [ ! -f "$INDICO_LOG" ]; then
        log_warning "Indico log file not found: $INDICO_LOG"
        return
    fi

    log_info "Checking recent logs for plugin messages..."

    # Check for plugin loading messages
    echo -e "\n${BLUE}Recent plugin messages:${NC}"
    tail -100 "$INDICO_LOG" | grep -i "plugin.*$PLUGIN_NAME\|$PLUGIN_NAME.*plugin" | tail -5 || echo "  No recent plugin messages found"

    # Check for errors
    echo -e "\n${BLUE}Recent errors:${NC}"
    tail -100 "$INDICO_LOG" | grep -i "error.*$PLUGIN_NAME\|$PLUGIN_NAME.*error" | tail -3 || echo "  No recent plugin errors found"
}

# Activate plugin
activate_plugin() {
    print_header "Activating Plugin"

    log_info "Activating $PLUGIN_FRIENDLY_NAME plugin..."

    if indico setup activate-plugin "$PLUGIN_NAME" 2>/dev/null; then
        log_success "Plugin activated successfully"
        log_info "Restart Indico to apply changes: sudo systemctl restart indico indico-celery"
    else
        log_error "Failed to activate plugin"
        log_info "Check if plugin is already active or if there are errors"
    fi
}

# Run database migrations
run_migrations() {
    print_header "Running Database Migrations"

    log_info "Running migrations for $PLUGIN_FRIENDLY_NAME plugin..."

    if indico db upgrade --plugin "$PLUGIN_NAME" 2>/dev/null; then
        log_success "Migrations completed successfully"
    else
        log_error "Failed to run migrations"
        log_info "Try: indico db upgrade (for all plugins)"
    fi
}

# Main diagnostic function
run_diagnostics() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Indico Push Notifications Plugin - Status Check${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo "Plugin: $PLUGIN_NAME ($PLUGIN_FRIENDLY_NAME)"
    echo "Time: $(date)"
    echo "Host: $(hostname)"
    echo "User: $(whoami)"
    echo ""

    # Run checks
    check_user
    check_pip_installation
    check_plugin_available
    check_plugin_active
    check_configuration
    check_migrations
    check_services
    check_logs

    print_header "Diagnostic Summary"

    echo -e "${GREEN}If plugin is available but not active:${NC}"
    echo "1. Activate plugin: indico setup activate-plugin $PLUGIN_NAME"
    echo "2. Run migrations: indico db upgrade --plugin $PLUGIN_NAME"
    echo "3. Restart Indico: sudo systemctl restart indico indico-celery"
    echo "4. Check web interface: Admin → Plugins"

    echo -e "\n${YELLOW}Quick commands:${NC}"
    echo "  Check status: indico setup list-plugins | grep $PLUGIN_NAME"
    echo "  Activate: indico setup activate-plugin $PLUGIN_NAME"
    echo "  Migrations: indico db upgrade --plugin $PLUGIN_NAME"
    echo "  Restart: sudo systemctl restart indico indico-celery"
}

# Parse command line arguments
case "$1" in
    activate)
        activate_plugin
        ;;
    migrate)
        run_migrations
        ;;
    status)
        check_plugin_available
        check_plugin_active
        ;;
    logs)
        check_logs
        ;;
    help|--help|-h)
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  (no command)  Run full diagnostics"
        echo "  activate      Activate the plugin"
        echo "  migrate       Run database migrations"
        echo "  status        Check plugin status"
        echo "  logs          Check logs for plugin messages"
        echo "  help          Show this help"
        ;;
    *)
        run_diagnostics
        ;;
esac

# Exit with appropriate code
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Check completed${NC}"
    exit 0
else
    echo -e "\n${YELLOW}Check completed with warnings${NC}"
    exit 0
fi
