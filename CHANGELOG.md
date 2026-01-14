# Changelog

All notable changes to the Indico Push Notifications Plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial plugin structure with core functionality
- Telegram notifications with account linking
- Web Push notifications with VAPID authentication
- User preference management system
- Integration with Indico's notification system
- Comprehensive API endpoints
- Database models for logging and subscriptions
- Alembic migrations for database schema management
- Test suite with pytest
- Development tools and scripts
- Example usage and configuration files
- Documentation for users and developers

### Features
- **Telegram Integration**: Users can link their Telegram accounts to receive notifications
- **Web Push Support**: Browser-based push notifications with service worker
- **User Preferences**: Granular control over notification types and channels
- **Admin Configuration**: Plugin settings configurable through Indico admin interface
- **Notification Logging**: Audit trail of all sent notifications
- **Test Notifications**: Ability to send test notifications for debugging
- **Multi-device Support**: Multiple Web Push subscriptions per user
- **Template System**: Customizable notification templates for different event types

### Technical Details
- Built as a standard Indico plugin using Flask Blueprints
- Uses SettingsProxy for user preference storage
- Implements proper error handling and logging
- Includes comprehensive test coverage
- Follows Python best practices and code style guidelines
- Supports database migrations with Alembic
- Provides REST API for integration with other systems

## [1.0.0] - 2024-01-01

### Added
- Initial release of Indico Push Notifications Plugin
- Complete implementation of all core features
- Full documentation and examples
- Ready for production use

### Security
- Secure Telegram account linking with time-limited tokens
- VAPID authentication for Web Push notifications
- CSRF protection for all API endpoints
- Proper input validation and sanitization

### Performance
- Efficient notification processing with batch operations
- Asynchronous notification sending where possible
- Database indexing for performance optimization
- Caching of frequently accessed data

### Compatibility
- Compatible with Indico 3.x
- Supports Python 3.7+
- Works with PostgreSQL, MySQL, and SQLite databases
- Cross-browser Web Push support (Chrome, Firefox, Safari, Edge)

## Installation and Upgrade Notes

### First Installation
1. Install the plugin: `pip install indico-push-notifications`
2. Add to `indico.conf`: `ENABLED_PLUGINS = ['indico_push_notifications']`
3. Configure Telegram bot token and VAPID keys
4. Run migrations: `indico db upgrade --plugin indico_push_notifications`
5. Configure plugin settings in Indico admin interface

### Upgrading
- Always backup your database before upgrading
- Run migrations: `indico db upgrade --plugin indico_push_notifications`
- Check release notes for any breaking changes
- Test notification functionality after upgrade

## Deprecation Notices
- None in initial release

## Breaking Changes
- None in initial release

## Known Issues
- Web Push requires HTTPS for production use
- Some browsers may have limitations on notification permissions
- Telegram bot must be configured with appropriate privacy settings

## Future Plans
- Scheduled notifications and reminders
- Notification analytics and reporting
- Advanced template customization
- Bulk notification sending
- Mobile app integration
- Additional notification channels (SMS, Slack, etc.)

---

*This changelog is automatically generated based on the project's commit history and release tags.*