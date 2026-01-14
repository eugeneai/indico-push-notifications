#!/bin/bash

# Indico Push Notifications Plugin - Missing Files Sync Script
# This script syncs missing files from local development to Indico server

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_NAME="indico-push-notifications"

# Remote server configuration (update these)
REMOTE_USER="indico"
REMOTE_HOST="nla2020"  # Change to your server hostname
REMOTE_DIR="/opt/indico/modules/indico-push-notifications"

# Files that MUST exist for plugin to work
ESSENTIAL_FILES=(
    "alembic.ini"
    "alembic/env.py"
    "alembic/script.py.mako"
    "alembic/versions/001_initial_migration.py"
    "setup.py"
    "requirements.txt"
    "indico_push_notifications/__init__.py"
    "indico_push_notifications/blueprint.py"
    "indico_push_notifications/notifications.py"
    "indico_push_notifications/telegram_bot.py"
    "indico_push_notifications/webpush.py"
    "indico_push_notifications/forms.py"
    "indico_push_notifications/models.py"
    "indico_push_notifications/controllers.py"
)

# Files that are nice to have
OPTIONAL_FILES=(
    "pyproject.toml"
    "README.md"
    "README_DEVELOPMENT.md"
    "CHANGELOG.md"
    "LICENSE"
    "MANIFEST.in"
    ".gitignore"
    "example_usage.py"
    "example_indico.conf"
    "install_and_test.sh"
    "sync_missing_files.sh"
    "indico_push_notifications/templates/user_preferences.html"
    "indico_push_notifications/static/service-worker.js"
    "indico_push_notifications/static/push-manager.js"
    "indico_push_notifications/tests/test_basic.py"
    "indico_push_notifications/tests/conftest.py"
)

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

# Check if file exists locally
check_local_file() {
    local file="$1"
    if [[ -f "$LOCAL_DIR/$file" ]] || [[ -d "$LOCAL_DIR/$file" ]]; then
        return 0
    else
        return 1
    fi
}

# Check if file exists remotely (via SSH)
check_remote_file() {
    local file="$1"
    if ssh "$REMOTE_USER@$REMOTE_HOST" "test -e '$REMOTE_DIR/$file'" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Sync a single file
sync_file() {
    local file="$1"
    local is_essential="$2"

    if ! check_local_file "$file"; then
        if [[ "$is_essential" == "essential" ]]; then
            log_error "Essential file missing locally: $file"
            return 1
        else
            log_warning "Optional file missing locally: $file"
            return 0
        fi
    fi

    if check_remote_file "$file"; then
        log_info "File exists on server: $file"
        return 0
    fi

    log_info "Syncing $file to server..."

    # Create remote directory if needed
    local remote_dir=$(dirname "$REMOTE_DIR/$file")
    ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p '$remote_dir'" 2>/dev/null

    # Sync the file
    if scp -r "$LOCAL_DIR/$file" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/$file" 2>/dev/null; then
        log_success "Synced: $file"
        return 0
    else
        log_error "Failed to sync: $file"
        return 1
    fi
}

# Create minimal alembic.ini if missing
create_minimal_alembic_ini() {
    local remote_file="$REMOTE_DIR/alembic.ini"

    log_info "Creating minimal alembic.ini on server..."

    ssh "$REMOTE_USER@$REMOTE_HOST" "cat > '$remote_file' << 'EOF'
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
EOF" 2>/dev/null

    if ssh "$REMOTE_USER@$REMOTE_HOST" "test -f '$remote_file'" 2>/dev/null; then
        log_success "Created minimal alembic.ini on server"
        return 0
    else
        log_error "Failed to create alembic.ini on server"
        return 1
    fi
}

# Run migrations on server
run_migrations() {
    log_info "Running database migrations on server..."

    # Try Indico command first
    log_info "Trying: indico db upgrade --plugin $PLUGIN_NAME"
    if ssh "$REMOTE_USER@$REMOTE_HOST" "cd '$REMOTE_DIR' && indico db upgrade --plugin $PLUGIN_NAME" 2>/dev/null; then
        log_success "Migrations completed using Indico command"
        return 0
    fi

    # Try alembic directly
    log_info "Trying: alembic upgrade head"
    if ssh "$REMOTE_USER@$REMOTE_HOST" "cd '$REMOTE_DIR' && export INDICO_DATABASE_URL='postgresql://indico:indico@localhost/indico' && alembic -c alembic.ini upgrade head" 2>/dev/null; then
        log_success "Migrations completed using alembic"
        return 0
    fi

    log_error "Failed to run migrations"
    return 1
}

# Check SSH connection
check_ssh() {
    log_info "Checking SSH connection to $REMOTE_USER@$REMOTE_HOST..."

    if ssh -q "$REMOTE_USER@$REMOTE_HOST" "exit" 2>/dev/null; then
        log_success "SSH connection successful"
        return 0
    else
        log_error "SSH connection failed"
        log_info "Please ensure:"
        log_info "1. SSH key is set up for passwordless login"
        log_info "2. Remote host is accessible"
        log_info "3. User '$REMOTE_USER' has access to '$REMOTE_DIR'"
        return 1
    fi
}

# Main sync function
sync_files() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  Syncing Files to Indico Server${NC}"
    echo -e "${BLUE}========================================${NC}\n"

    # Check SSH connection
    if ! check_ssh; then
        exit 1
    fi

    # Check remote directory exists
    log_info "Checking remote directory: $REMOTE_DIR"
    if ! ssh "$REMOTE_USER@$REMOTE_HOST" "test -d '$REMOTE_DIR'" 2>/dev/null; then
        log_error "Remote directory does not exist: $REMOTE_DIR"
        log_info "Creating directory..."
        ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p '$REMOTE_DIR'" 2>/dev/null
    fi

    # Sync essential files
    echo -e "\n${BLUE}Syncing Essential Files:${NC}"
    local essential_errors=0
    for file in "${ESSENTIAL_FILES[@]}"; do
        if ! sync_file "$file" "essential"; then
            essential_errors=$((essential_errors + 1))
        fi
    done

    # Create alembic.ini if still missing
    if ! check_remote_file "alembic.ini"; then
        create_minimal_alembic_ini
    fi

    # Sync optional files
    echo -e "\n${BLUE}Syncing Optional Files:${NC}"
    local optional_errors=0
    for file in "${OPTIONAL_FILES[@]}"; do
        if ! sync_file "$file" "optional"; then
            optional_errors=$((optional_errors + 1))
        fi
    done

    # Summary
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  Sync Summary${NC}"
    echo -e "${BLUE}========================================${NC}"

    local total_essential=${#ESSENTIAL_FILES[@]}
    local total_optional=${#OPTIONAL_FILES[@]}
    local essential_success=$((total_essential - essential_errors))
    local optional_success=$((total_optional - optional_errors))

    echo -e "Essential files: ${GREEN}$essential_success/$total_essential${NC} synced"
    echo -e "Optional files:  ${GREEN}$optional_success/$total_optional${NC} synced"

    if [[ $essential_errors -eq 0 ]]; then
        log_success "All essential files synced successfully!"

        # Ask to run migrations
        echo
        read -p "Run database migrations on server? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_migrations
        fi

        # Show next steps
        echo -e "\n${GREEN}Next steps on server:${NC}"
        echo "1. Activate Indico virtual environment:"
        echo "   source /opt/indico/.venv-3/bin/activate"
        echo "2. Install/update plugin:"
        echo "   cd $REMOTE_DIR && pip install -e . --break-system-packages"
        echo "3. Run migrations (if not done):"
        echo "   indico db upgrade --plugin $PLUGIN_NAME"
        echo "4. Add to indico.conf:"
        echo "   ENABLED_PLUGINS = ['indico_push_notifications']"
        echo "5. Restart Indico:"
        echo "   sudo systemctl restart indico indico-celery"
    else
        log_error "Some essential files failed to sync"
        echo -e "\n${YELLOW}Manual steps required:${NC}"
        echo "1. Check which files failed above"
        echo "2. Manually copy missing files to server"
        echo "3. Ensure alembic.ini exists in $REMOTE_DIR"
        echo "4. Run migrations manually"
    fi
}

# Help function
show_help() {
    echo -e "${BLUE}Indico Push Notifications Plugin - File Sync Script${NC}"
    echo
    echo "Usage: $0 [OPTION]"
    echo
    echo "Options:"
    echo "  sync        Sync files to server (default)"
    echo "  check       Check which files are missing on server"
    echo "  migrate     Run migrations on server only"
    echo "  help        Show this help message"
    echo
    echo "Configuration:"
    echo "  Edit the following variables in this script:"
    echo "  - REMOTE_USER: $REMOTE_USER"
    echo "  - REMOTE_HOST: $REMOTE_HOST"
    echo "  - REMOTE_DIR: $REMOTE_DIR"
    echo
    echo "Prerequisites:"
    echo "  1. SSH key authentication to $REMOTE_USER@$REMOTE_HOST"
    echo "  2. Write access to $REMOTE_DIR on server"
    echo "  3. Local files in $LOCAL_DIR"
}

# Check missing files only
check_missing() {
    echo -e "\n${BLUE}Checking missing files on server:${NC}"

    if ! check_ssh; then
        exit 1
    fi

    local missing_essential=()
    local missing_optional=()

    echo -e "\n${BLUE}Essential files missing:${NC}"
    for file in "${ESSENTIAL_FILES[@]}"; do
        if ! check_remote_file "$file"; then
            missing_essential+=("$file")
            echo "  ❌ $file"
        fi
    done

    echo -e "\n${BLUE}Optional files missing:${NC}"
    for file in "${OPTIONAL_FILES[@]}"; do
        if ! check_remote_file "$file"; then
            missing_optional+=("$file")
            echo "  ⚠️  $file"
        fi
    done

    echo -e "\n${BLUE}Summary:${NC}"
    echo "Missing essential files: ${#missing_essential[@]}"
    echo "Missing optional files:  ${#missing_optional[@]}"

    if [[ ${#missing_essential[@]} -eq 0 ]]; then
        log_success "All essential files are present on server!"
    else
        log_warning "Some essential files are missing"
    fi
}

# Parse command line argument
case "${1:-sync}" in
    "sync")
        sync_files
        ;;
    "check")
        check_missing
        ;;
    "migrate")
        check_ssh
        run_migrations
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "Unknown option: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac

exit 0
