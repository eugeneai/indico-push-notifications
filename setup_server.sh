#!/bin/bash

# Indico Push Notifications Plugin - Server Setup Script
# This script sets up the plugin on an Indico server

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_NAME="indico-push-notifications"
VENV_DIR="/opt/indico/.venv-3"
INDICO_DIR="/opt/indico"

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

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. This is not recommended."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if we're in plugin directory
    if [[ ! -f "$PLUGIN_DIR/setup.py" ]]; then
        log_error "Please run this script from the plugin directory"
        exit 1
    fi

    # Check Indico directory
    if [[ ! -d "$INDICO_DIR" ]]; then
        log_error "Indico directory not found at $INDICO_DIR"
        exit 1
    fi

    # Check virtual environment
    if [[ ! -d "$VENV_DIR" ]]; then
        log_error "Indico virtual environment not found at $VENV_DIR"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Activate virtual environment
activate_venv() {
    log_info "Activating Indico virtual environment..."

    if [[ -f "$VENV_DIR/bin/activate" ]]; then
        source "$VENV_DIR/bin/activate"
        log_success "Virtual environment activated"
    else
        log_error "Cannot activate virtual environment"
        exit 1
    fi
}

# Install plugin
install_plugin() {
    log_info "Installing plugin..."

    # Change to plugin directory
    cd "$PLUGIN_DIR"

    # Remove pyproject.toml if it causes issues
    if [[ -f "pyproject.toml" ]]; then
        log_warning "pyproject.toml may cause installation issues"
        read -p "Remove pyproject.toml? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            mv pyproject.toml pyproject.toml.backup
            log_info "Backed up pyproject.toml to pyproject.toml.backup"
        fi
    fi

    # Install in development mode
    if pip install -e . --break-system-packages; then
        log_success "Plugin installed successfully"
    else
        log_error "Failed to install plugin"
        log_info "Trying alternative installation method..."

        # Try without --break-system-packages
        if pip install -e .; then
            log_success "Plugin installed successfully (alternative method)"
        else
            log_error "All installation methods failed"
            exit 1
        fi
    fi

    # Restore pyproject.toml if backed up
    if [[ -f "pyproject.toml.backup" ]]; then
        mv pyproject.toml.backup pyproject.toml
        log_info "Restored pyproject.toml"
    fi
}

# Setup alembic configuration
setup_alembic() {
    log_info "Setting up Alembic configuration..."

    cd "$PLUGIN_DIR"

    # Create alembic.ini if it doesn't exist
    if [[ ! -f "alembic.ini" ]]; then
        log_warning "alembic.ini not found. Creating minimal configuration..."

        cat > alembic.ini << 'EOF'
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://indico:indico@localhost/indico

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
EOF

        log_success "Created alembic.ini"
    else
        log_info "alembic.ini already exists"
    fi

    # Check alembic directory
    if [[ ! -d "alembic" ]]; then
        log_error "alembic directory not found"
        log_info "Creating basic alembic structure..."

        mkdir -p alembic/versions
        log_success "Created alembic directory structure"
    else
        log_info "alembic directory exists"
    fi

    # Check for required alembic files
    if [[ ! -f "alembic/env.py" ]]; then
        log_error "alembic/env.py not found"
        log_info "Please copy alembic directory from the plugin source"
    else
        log_info "alembic/env.py exists"
    fi
}

# Install alembic if needed
install_alembic() {
    log_info "Checking for Alembic..."

    if ! python -c "import alembic" 2>/dev/null; then
        log_warning "Alembic not installed. Installing..."

        if pip install alembic --break-system-packages; then
            log_success "Alembic installed"
        else
            pip install alembic
            log_success "Alembic installed (alternative method)"
        fi
    else
        log_info "Alembic already installed"
    fi
}

# Run migrations
run_migrations() {
    log_info "Running database migrations..."

    cd "$PLUGIN_DIR"

    # Try Indico command first
    log_info "Trying 'indico db upgrade --plugin $PLUGIN_NAME'..."

    if command -v indico &> /dev/null; then
        if indico db upgrade --plugin "$PLUGIN_NAME"; then
            log_success "Migrations completed using Indico command"
            return 0
        else
            log_warning "Indico command failed"
        fi
    else
        log_warning "'indico' command not found"
    fi

    # Try alembic directly
    log_info "Trying alembic directly..."

    # Set database URL from environment or use default
    if [[ -z "$INDICO_DATABASE_URL" ]]; then
        log_warning "INDICO_DATABASE_URL not set. Using default from alembic.ini"
        export INDICO_DATABASE_URL="postgresql://indico:indico@localhost/indico"
    fi

    if alembic -c alembic.ini upgrade head; then
        log_success "Migrations completed using alembic"
        return 0
    else
        log_error "Alembic migration failed"

        # Try with --sql flag to see what would be executed
        log_info "Trying dry run to see SQL statements..."
        alembic -c alembic.ini upgrade head --sql || true

        return 1
    fi
}

# Update Indico configuration
update_indico_config() {
    log_info "Updating Indico configuration..."

    INDICO_CONF="$INDICO_DIR/indico.conf"

    if [[ ! -f "$INDICO_CONF" ]]; then
        log_warning "indico.conf not found at $INDICO_CONF"
        log_info "Please add the plugin manually to your Indico configuration"
        return 1
    fi

    # Check if plugin is already enabled
    if grep -q "indico_push_notifications" "$INDICO_CONF"; then
        log_info "Plugin already enabled in indico.conf"
        return 0
    fi

    # Create backup
    cp "$INDICO_CONF" "$INDICO_CONF.backup.$(date +%Y%m%d_%H%M%S)"

    # Add plugin to ENABLED_PLUGINS
    if grep -q "ENABLED_PLUGINS" "$INDICO_CONF"; then
        # Append to existing ENABLED_PLUGINS
        sed -i "s/ENABLED_PLUGINS = \[\(.*\)\]/ENABLED_PLUGINS = \[\1, 'indico_push_notifications'\]/" "$INDICO_CONF"
        log_success "Added plugin to ENABLED_PLUGINS in indico.conf"
    else
        # Add new ENABLED_PLUGINS section
        echo "" >> "$INDICO_CONF"
        echo "# Push Notifications Plugin" >> "$INDICO_CONF"
        echo "ENABLED_PLUGINS = ['indico_push_notifications']" >> "$INDICO_CONF"
        echo "" >> "$INDICO_CONF"
        echo "# Telegram Bot Configuration" >> "$INDICO_CONF"
        echo "# PUSH_NOTIFICATIONS_TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN'" >> "$INDICO_CONF"
        echo "# PUSH_NOTIFICATIONS_TELEGRAM_BOT_USERNAME = '@YourIndicoBot'" >> "$INDICO_CONF"
        echo "" >> "$INDICO_CONF"
        echo "# Web Push VAPID Configuration" >> "$INDICO_CONF"
        echo "# PUSH_NOTIFICATIONS_VAPID_PUBLIC_KEY = 'YOUR_PUBLIC_KEY'" >> "$INDICO_CONF"
        echo "# PUSH_NOTIFICATIONS_VAPID_PRIVATE_KEY = 'YOUR_PRIVATE_KEY'" >> "$INDICO_CONF"
        echo "# PUSH_NOTIFICATIONS_VAPID_EMAIL = 'admin@example.com'" >> "$INDICO_CONF"
        log_success "Added plugin configuration to indico.conf"
    fi

    log_info "Backup created at $INDICO_CONF.backup"
}

# Test plugin installation
test_installation() {
    log_info "Testing plugin installation..."

    cd "$PLUGIN_DIR"

    # Test Python import
    if python -c "import indico_push_notifications; print('✅ Plugin imports successfully')"; then
        log_success "Python import test passed"
    else
        log_error "Python import test failed"
        return 1
    fi

    # Test plugin class
    if python -c "from indico_push_notifications import IndicoPushNotificationsPlugin; plugin = IndicoPushNotificationsPlugin(); print(f'✅ Plugin class: {plugin.name}')"; then
        log_success "Plugin class test passed"
    else
        log_error "Plugin class test failed"
        return 1
    fi

    return 0
}

# Main function
main() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  Indico Push Notifications Plugin Setup${NC}"
    echo -e "${BLUE}========================================${NC}\n"

    # Check if running as root
    check_root

    # Check prerequisites
    check_prerequisites

    # Activate virtual environment
    activate_venv

    # Install plugin
    install_plugin

    # Setup alembic
    setup_alembic

    # Install alembic if needed
    install_alembic

    # Test installation
    if test_installation; then
        log_success "Installation tests passed"
    else
        log_error "Installation tests failed"
        exit 1
    fi

    # Run migrations
    if run_migrations; then
        log_success "Database migrations completed"
    else
        log_warning "Database migrations failed or partially completed"
        log_info "You may need to run migrations manually"
    fi

    # Update Indico configuration
    update_indico_config

    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}  Setup Completed Successfully!${NC}"
    echo -e "${GREEN}========================================${NC}\n"

    echo "Next steps:"
    echo "1. Configure the plugin in Indico admin interface"
    echo "2. Set up Telegram bot token (get from @BotFather)"
    echo "3. Generate VAPID keys for Web Push"
    echo "4. Restart Indico services"
    echo ""
    echo "Commands to restart Indico:"
    echo "  sudo systemctl restart indico"
    echo "  sudo systemctl restart indico-celery"
    echo ""
    echo "For troubleshooting, check:"
    echo "  - Indico logs: /var/log/indico/"
    echo "  - Plugin logs: Check Indico admin interface"
}

# Run main function
main "$@"
