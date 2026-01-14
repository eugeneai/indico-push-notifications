# Indico Push Notifications Plugin - Development Guide

This document provides instructions for developers working on the Indico Push Notifications Plugin.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Code Style and Quality](#code-style-and-quality)
4. [Testing](#testing)
5. [Database Migrations](#database-migrations)
6. [API Documentation](#api-documentation)
7. [Release Process](#release-process)
8. [Troubleshooting](#troubleshooting)

## Development Environment Setup

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)
- Git
- Virtual environment tool (venv or virtualenv)

### Quick Start

1. **Clone the repository** (if not already cloned):
   ```bash
   git clone <repository-url>
   cd indico-push-notifications
   ```

2. **Run the installation script**:
   ```bash
   ./install_and_test.sh
   ```
   Select option 1 for full installation.

3. **Or set up manually**:
   ```bash
   # Create virtual environment
   python -m venv .venv
   
   # Activate virtual environment
   source .venv/bin/activate  # On Linux/Mac
   # or
   .venv\Scripts\activate     # On Windows
   
   # Install in development mode
   pip install -e ".[dev]"
   ```

### Development Dependencies

The plugin includes several development dependencies:

- **pytest**: Testing framework
- **pytest-cov**: Test coverage reporting
- **black**: Code formatting
- **flake8**: Code linting
- **mypy**: Static type checking
- **pre-commit**: Git hooks for code quality

Install all development dependencies:
```bash
pip install -e ".[dev]"
```

## Project Structure

```
indico-push-notifications/
├── __init__.py              # Main plugin class
├── blueprint.py             # Flask routes and controllers
├── controllers.py           # Business logic and helper functions
├── forms.py                 # WTForms for user and admin settings
├── models.py                # Database models (optional)
├── notifications.py         # Core notification logic
├── telegram_bot.py          # Telegram bot implementation
├── webpush.py              # Web Push API integration
├── alembic/                 # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── static/                  # Static files
│   ├── service-worker.js
│   └── push-manager.js
├── templates/               # HTML templates
│   ├── user_preferences.html
│   └── push_script.js
├── tests/                   # Test suite
│   └── test_basic.py
├── docs/                    # Documentation (optional)
├── setup.py                 # Package configuration
├── requirements.txt         # Runtime dependencies
├── pyproject.toml          # Modern Python tooling
├── MANIFEST.in             # Package distribution files
├── .gitignore              # Git ignore rules
├── LICENSE                 # MIT License
├── README.md               # User documentation
├── README_DEVELOPMENT.md   # This file
├── example_usage.py        # Usage examples
├── example_indico.conf     # Example configuration
└── install_and_test.sh     # Installation script
```

## Code Style and Quality

### Code Formatting

We use **black** for automatic code formatting:

```bash
# Check formatting
black --check .

# Format all files
black .
```

### Linting

We use **flake8** for code linting:

```bash
# Run flake8
flake8 .
```

### Type Checking

We use **mypy** for static type checking:

```bash
# Run mypy
mypy --ignore-missing-imports .
```

### Pre-commit Hooks

Install pre-commit hooks to automatically check code quality before commits:

```bash
# Install hooks
pre-commit install

# Run hooks on all files
pre-commit run --all-files
```

The pre-commit configuration includes:
- trailing-whitespace fixer
- end-of-file fixer
- check-yaml
- black formatter
- flake8 linter
- mypy type checker

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=indico_push_notifications

# Run specific test file
pytest tests/test_basic.py

# Run specific test function
pytest tests/test_basic.py::TestPluginBasics::test_plugin_initialization
```

### Test Structure

Tests are organized by component:
- `TestPluginBasics`: Plugin initialization and configuration
- `TestUserPreferences`: User preference management
- `TestNotificationFormatting`: Message formatting
- `TestTelegramBot`: Telegram bot functionality
- `TestWebPush`: Web Push functionality
- `TestIntegration`: Integration between components

### Writing Tests

When writing tests:

1. **Use descriptive test names**: Test names should describe what is being tested
2. **Use fixtures for common setup**: Define fixtures in conftest.py or at module level
3. **Mock external dependencies**: Use `unittest.mock` to mock API calls and external services
4. **Test edge cases**: Include tests for error conditions and edge cases
5. **Keep tests independent**: Each test should be able to run independently

Example test structure:
```python
def test_functionality():
    # Setup
    mock_data = {...}
    
    # Exercise
    result = function_under_test(mock_data)
    
    # Verify
    assert result.expected_value == actual_value
    assert len(result.items) == expected_count
```

## Database Migrations

### Migration Setup

The plugin uses Alembic for database migrations. The migration environment is configured in `alembic/env.py`.

### Creating Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Create empty migration (manual)
alembic revision -m "Description of changes"
```

### Running Migrations

```bash
# Upgrade to latest version
alembic upgrade head

# Upgrade to specific version
alembic upgrade <revision_id>

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision_id>

# Show current revision
alembic current

# Show migration history
alembic history
```

### Migration Best Practices

1. **Always use autogenerate**: Let Alembic detect changes automatically when possible
2. **Review generated migrations**: Always review the generated migration script
3. **Test migrations**: Test both upgrade and downgrade paths
4. **Include data migrations**: When changing schemas, include data migration if needed
5. **Document breaking changes**: Note any breaking changes in migration comments

## API Documentation

### API Endpoints

The plugin provides REST API endpoints for:

- User preference management
- Telegram account linking
- Web Push subscription management
- Test notifications

See `example_usage.py` for detailed examples of API usage.

### Generating Documentation

To generate API documentation:

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Generate documentation
cd docs && make html
```

The documentation will be available at `docs/_build/html/index.html`.

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality (backward compatible)
- **PATCH** version for bug fixes (backward compatible)

### Release Checklist

1. **Update version numbers**:
   - `setup.py` (version)
   - `pyproject.toml` (version)
   - `__init__.py` (if version is stored there)

2. **Update CHANGELOG.md** (if exists):
   - Add new version section
   - List all changes since last release
   - Group changes by type (Added, Changed, Fixed, Removed)

3. **Run tests**:
   ```bash
   pytest --cov=indico_push_notifications
   ```

4. **Check code quality**:
   ```bash
   black --check .
   flake8 .
   mypy --ignore-missing-imports .
   ```

5. **Build package**:
   ```bash
   python setup.py sdist bdist_wheel
   ```

6. **Test installation**:
   ```bash
   pip install dist/indico-push-notifications-*.tar.gz
   ```

7. **Upload to PyPI** (if maintainer):
   ```bash
   twine upload dist/*
   ```

### Creating a New Release

1. Create a release branch:
   ```bash
   git checkout -b release/v1.0.0
   ```

2. Update version and changelog

3. Commit changes:
   ```bash
   git commit -m "Release v1.0.0"
   ```

4. Create tag:
   ```bash
   git tag -a v1.0.0 -m "Version 1.0.0"
   ```

5. Push to repository:
   ```bash
   git push origin release/v1.0.0
   git push origin v1.0.0
   ```

## Troubleshooting

### Common Issues

#### Import Errors

**Problem**: `ModuleNotFoundError` when importing plugin modules.

**Solution**: Make sure the plugin is installed in development mode:
```bash
pip install -e .
```

#### Database Connection Errors

**Problem**: Alembic cannot connect to database.

**Solution**: Check database URL configuration in `alembic.ini` or set `INDICO_DATABASE_URL` environment variable.

#### Test Failures

**Problem**: Tests fail due to missing dependencies.

**Solution**: Install all development dependencies:
```bash
pip install -e ".[dev]"
```

#### Code Quality Checks Fail

**Problem**: Black, flake8, or mypy checks fail.

**Solution**:
- Run `black .` to fix formatting
- Fix flake8 warnings manually
- Address mypy type errors

### Debugging

#### Enable Debug Logging

Add to your test or development script:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Debugging Telegram Bot

For Telegram bot debugging:
1. Use test bot token from @BotFatherTestBot
2. Enable debug mode in bot configuration
3. Check bot logs for API responses

#### Debugging Web Push

For Web Push debugging:
1. Use browser developer tools (F12)
2. Check Service Worker console
3. Test with local VAPID keys

### Getting Help

If you encounter issues not covered here:

1. **Check existing issues**: Look for similar issues in the issue tracker
2. **Review documentation**: Check README.md and example files
3. **Run examples**: Test with `example_usage.py`
4. **Enable debug logging**: Add detailed logging to identify issues
5. **Create minimal reproduction**: Create a minimal test case that reproduces the issue

## Contributing

### Contribution Guidelines

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Write tests**: Include tests for new functionality
4. **Ensure code quality**: Run black, flake8, and mypy
5. **Update documentation**: Update README or add docstrings as needed
6. **Submit pull request**: Describe changes and link to any related issues

### Code Review Process

1. **Automated checks**: CI runs tests and code quality checks
2. **Manual review**: Maintainers review code for:
   - Functionality correctness
   - Code quality and style
   - Test coverage
   - Documentation updates
3. **Feedback**: Address any feedback from reviewers
4. **Merge**: Once approved, code is merged to main branch

### Development Workflow

1. Start with an issue or feature request
2. Discuss approach in issue comments
3. Implement changes with tests
4. Submit pull request
5. Address review feedback
6. Merge and deploy

## Additional Resources

- [Indico Documentation](https://docs.getindico.io/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Python Telegram Bot Documentation](https://python-telegram-bot.org/)
- [Web Push Documentation](https://webpush-wg.github.io/webpush-protocol/)

## License

This project is licensed under the MIT License - see the LICENSE file for details.