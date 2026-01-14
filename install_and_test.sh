#!/bin/bash

# Indico Push Notifications Plugin - Installation and Test Script
# This script helps install and test the plugin in a development environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PLUGIN_NAME="indico-push-notifications"
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PLUGIN_DIR}/.venv"
INDICO_DIR="${PLUGIN_DIR}/../indico"  # Assuming Indico is in sibling directory

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "Python not found. Please install Python 3.7 or higher."
        exit 1
    fi

    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_info "Python version: $PYTHON_VERSION"

    # Check pip
    if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
        log_error "pip not found. Please install pip."
        exit 1
    fi

    # Check if Indico directory exists
    if [ ! -d "$INDICO_DIR" ]; then
        log_warning "Indico directory not found at $INDICO_DIR"
        log_warning "Please adjust INDICO_DIR variable or install Indico separately"
    fi

    log_success "Prerequisites check passed"
}

# Create virtual environment
create_venv() {
    log_info "Creating virtual environment..."

    if [ -d "$VENV_DIR" ]; then
        log_warning "Virtual environment already exists at $VENV_DIR"
        read -p "Recreate virtual environment? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_DIR"
        else
            log_info "Using existing virtual environment"
            return 0
        fi
    fi

    $PYTHON_CMD -m venv "$VENV_DIR"

    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
        log_success "Virtual environment created and activated"
    else
        log_error "Failed to create virtual environment"
        exit 1
    fi
}

# Install plugin in development mode
install_plugin() {
    log_info "Installing plugin in development mode..."

    source "$VENV_DIR/bin/activate"

    # Upgrade pip
    pip install --upgrade pip

    # Install plugin with development dependencies
    pip install -e ".[dev]"

    # Check installation
    if python -c "import $PLUGIN_NAME" &> /dev/null; then
        log_success "Plugin installed successfully"
    else
        log_error "Failed to import plugin"
        exit 1
    fi
}

# Run tests
run_tests() {
    log_info "Running tests..."

    source "$VENV_DIR/bin/activate"

    # Run pytest
    if python -m pytest tests/ -v; then
        log_success "Tests passed"
    else
        log_error "Tests failed"
        exit 1
    fi
}

# Check code quality
check_code_quality() {
    log_info "Checking code quality..."

    source "$VENV_DIR/bin/activate"

    # Check with black
    log_info "Running black..."
    if python -m black --check .; then
        log_success "Black check passed"
    else
        log_warning "Black found formatting issues"
        log_info "To fix formatting, run: black ."
    fi

    # Check with flake8
    log_info "Running flake8..."
    if python -m flake8 .; then
        log_success "Flake8 check passed"
    else
        log_warning "Flake8 found issues"
    fi

    # Check with mypy (optional)
    log_info "Running mypy..."
    if python -m mypy --ignore-missing-imports .; then
        log_success "Mypy check passed"
    else
        log_warning "Mypy found type issues"
    fi
}

# Generate documentation
generate_docs() {
    log_info "Generating documentation..."

    source "$VENV_DIR/bin/activate"

    # Check if Sphinx is installed
    if ! python -c "import sphinx" &> /dev/null; then
        log_warning "Sphinx not installed. Installing documentation dependencies..."
        pip install -e ".[docs]"
    fi

    # Create docs directory if it doesn't exist
    DOCS_DIR="${PLUGIN_DIR}/docs"
    if [ ! -d "$DOCS_DIR" ]; then
        mkdir -p "$DOCS_DIR"
    fi

    # Generate API documentation
    log_info "Generating API documentation..."
    if [ -f "${DOCS_DIR}/conf.py" ]; then
        cd "$DOCS_DIR" && make html
        log_success "Documentation generated at ${DOCS_DIR}/_build/html/index.html"
    else
        log_warning "No Sphinx configuration found. Skipping documentation generation."
    fi
}

# Create example configuration
create_example_config() {
    log_info "Creating example configuration..."

    CONFIG_FILE="${PLUGIN_DIR}/example_indico.conf"

    cat > "$CONFIG_FILE" << EOF
# Example Indico Configuration for Push Notifications Plugin
# Copy this to your indico.conf and adjust values

# Enable the plugin
ENABLED_PLUGINS = ['indico_push_notifications']

# Telegram Bot Configuration
# Get token from @BotFather on Telegram
PUSH_NOTIFICATIONS_TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
PUSH_NOTIFICATIONS_TELEGRAM_BOT_USERNAME = "@YourIndicoBot"

# Web Push VAPID Configuration
# Generate keys with: openssl ecparam -name prime256v1 -genkey -noout -out vapid_private.pem
# Then extract public key: openssl ec -in vapid_private.pem -pubout -out vapid_public.pem
PUSH_NOTIFICATIONS_VAPID_PUBLIC_KEY = "YOUR_VAPID_PUBLIC_KEY_HERE"
PUSH_NOTIFICATIONS_VAPID_PRIVATE_KEY = "YOUR_VAPID_PRIVATE_KEY_HERE"
PUSH_NOTIFICATIONS_VAPID_EMAIL = "admin@example.com"

# Plugin Settings (can also be configured in admin interface)
PUSH_NOTIFICATIONS_WEBPUSH_ENABLED = True
PUSH_NOTIFICATIONS_TELEGRAM_ENABLED = True

# Default notification preferences
PUSH_NOTIFICATIONS_DEFAULT_PREFERENCES = {
    'event_creation': True,
    'event_update': True,
    'registration_open': True,
    'registration_confirmation': True,
    'abstract_submission': True,
    'abstract_review': True,
    'reminder': True,
}
EOF

    log_success "Example configuration created at $CONFIG_FILE"
    log_info "Please update the values with your actual configuration"
}

# Run example usage script
run_examples() {
    log_info "Running example usage script..."

    source "$VENV_DIR/bin/activate"

    if [ -f "${PLUGIN_DIR}/example_usage.py" ]; then
        python "${PLUGIN_DIR}/example_usage.py"
        log_success "Example script completed"
    else
        log_warning "Example usage script not found"
    fi
}

# Setup development environment
setup_dev_env() {
    log_info "Setting up development environment..."

    # Install pre-commit hooks
    if command -v pre-commit &> /dev/null || python -c "import pre_commit" &> /dev/null; then
        log_info "Installing pre-commit hooks..."
        pre-commit install
        log_success "Pre-commit hooks installed"
    else
        log_warning "pre-commit not installed. Skipping hook installation."
        log_info "Install with: pip install pre-commit"
    fi

    # Create .env file for development
    ENV_FILE="${PLUGIN_DIR}/.env"
    if [ ! -f "$ENV_FILE" ]; then
        cat > "$ENV_FILE" << EOF
# Development environment variables
DEBUG=True
TESTING=True

# Telegram test bot (use @BotFatherTestBot for testing)
TELEGRAM_BOT_TOKEN=test_token
TELEGRAM_BOT_USERNAME=@test_bot

# Web Push test keys
VAPID_PUBLIC_KEY=test_public_key
VAPID_PRIVATE_KEY=test_private_key
VAPID_EMAIL=test@example.com
EOF
        log_success "Created development environment file at $ENV_FILE"
    fi
}

# Main menu
show_menu() {
    echo -e "\n${BLUE}Indico Push Notifications Plugin${NC}"
    echo "================================"
    echo "1. Full installation and test"
    echo "2. Check prerequisites only"
    echo "3. Create virtual environment"
    echo "4. Install plugin"
    echo "5. Run tests"
    echo "6. Check code quality"
    echo "7. Generate documentation"
    echo "8. Create example configuration"
    echo "9. Run examples"
    echo "10. Setup development environment"
    echo "11. Clean up"
    echo "0. Exit"
    echo -n "Select option: "
}

# Clean up
cleanup() {
    log_info "Cleaning up..."

    read -p "Remove virtual environment? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -d "$VENV_DIR" ]; then
            rm -rf "$VENV_DIR"
            log_success "Virtual environment removed"
        fi
    fi

    read -p "Remove build artifacts? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "${PLUGIN_DIR}/build" "${PLUGIN_DIR}/dist" "${PLUGIN_DIR}/*.egg-info"
        log_success "Build artifacts removed"
    fi

    read -p "Remove cache files? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        find "$PLUGIN_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find "$PLUGIN_DIR" -type f -name "*.pyc" -delete
        find "$PLUGIN_DIR" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
        find "$PLUGIN_DIR" -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
        log_success "Cache files removed"
    fi
}

# Full installation and test
full_installation() {
    log_info "Starting full installation and test..."

    check_prerequisites
    create_venv
    install_plugin
    run_tests
    check_code_quality
    create_example_config
    setup_dev_env

    log_success "Full installation completed successfully!"
    log_info "Next steps:"
    log_info "1. Update example_indico.conf with your configuration"
    log_info "2. Add the plugin to your Indico installation"
    log_info "3. Run the plugin with: indico run"
}

# Main execution
main() {
    # Check if running in plugin directory
    if [ ! -f "${PLUGIN_DIR}/setup.py" ]; then
        log_error "Please run this script from the plugin directory"
        exit 1
    fi

    while true; do
        show_menu
        read option

        case $option in
            1)
                full_installation
                ;;
            2)
                check_prerequisites
                ;;
            3)
                create_venv
                ;;
            4)
                install_plugin
                ;;
            5)
                run_tests
                ;;
            6)
                check_code_quality
                ;;
            7)
                generate_docs
                ;;
            8)
                create_example_config
                ;;
            9)
                run_examples
                ;;
            10)
                setup_dev_env
                ;;
            11)
                cleanup
                ;;
            0)
                log_info "Exiting..."
                exit 0
                ;;
            *)
                log_error "Invalid option"
                ;;
        esac

        echo
        read -p "Press Enter to continue..."
    done
}

# Run main function
main "$@"
