#!/bin/bash

# One-line check for Indico Push Notifications Plugin on remote server
# Usage: ssh indico@nla2020 "bash -s" < one_line_check.sh

set -e

echo "========================================="
echo "  Indico Push Notifications - Quick Check"
echo "========================================="
echo "Time: $(date)"
echo "Host: $(hostname)"
echo "User: $(whoami)"
echo ""

# Change to plugin directory
cd /opt/indico/modules/indico-push-notifications 2>/dev/null || {
    echo "❌ ERROR: Plugin directory not found: /opt/indico/modules/indico-push-notifications"
    exit 1
}

# Activate virtual environment
if [ -f "/opt/indico/.venv-3/bin/activate" ]; then
    source "/opt/indico/.venv-3/bin/activate"
    echo "✅ Virtual environment activated"
else
    echo "❌ ERROR: Virtual environment not found: /opt/indico/.venv-3/bin/activate"
    exit 1
fi

echo ""
echo "=== CHECK 1: Plugin Installation ==="
if pip list | grep -q "indico-push-notifications"; then
    echo "✅ Plugin installed via pip"
    pip list | grep "indico-push-notifications"
else
    echo "❌ Plugin NOT installed via pip"
fi

echo ""
echo "=== CHECK 2: Entry Points ==="
python -c "
import pkg_resources
eps = [ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')]
print('Found entry points:', eps)
if 'indico_push_notifications' in eps:
    print('✅ Our plugin registered')
else:
    print('❌ Our plugin NOT registered')
"

echo ""
echo "=== CHECK 3: Configuration ==="
if [ -f "/opt/indico/etc/indico.conf" ]; then
    if grep -q "ENABLED_PLUGINS.*indico_push_notifications" /opt/indico/etc/indico.conf; then
        echo "✅ Plugin enabled in indico.conf"
        grep "ENABLED_PLUGINS" /opt/indico/etc/indico.conf | head -1
    else
        echo "❌ Plugin NOT enabled in indico.conf"
        echo "   Add: ENABLED_PLUGINS = ['indico_push_notifications']"
    fi
else
    echo "❌ Config file not found: /opt/indico/etc/indico.conf"
fi

echo ""
echo "=== CHECK 4: Indico Plugin Engine ==="
python -c "
try:
    from indico.core.plugins import plugin_engine

    active = list(plugin_engine.get_active_plugins().keys())
    print('Active plugins:', active)

    if 'indico_push_notifications' in active:
        print('✅✅✅ SUCCESS: Plugin ACTIVE in Indico! ✅✅✅')
        print('   Check: Admin → Plugins → Push Notifications')
    else:
        print('❌ Plugin NOT active in Indico')

        all_plugins = list(plugin_engine.get_all_plugins().keys())
        if 'indico_push_notifications' in all_plugins:
            print('⚠️  Plugin discovered but not active')
            print('   Check ENABLED_PLUGINS in indico.conf')
        else:
            print('❌ Plugin not discovered at all')
            print('   Check entry points and installation')

except ImportError as e:
    print('❌ Cannot import Indico:', e)
except Exception as e:
    print('❌ Error:', str(e))
"

echo ""
echo "=== CHECK 5: Services ==="
if systemctl is-active --quiet indico; then
    echo "✅ Indico service: RUNNING"
else
    echo "❌ Indico service: NOT RUNNING"
fi

if systemctl is-active --quiet indico-celery; then
    echo "✅ Indico-celery service: RUNNING"
else
    echo "⚠️  Indico-celery service: NOT RUNNING"
fi

echo ""
echo "=== CHECK 6: Recent Logs ==="
if [ -f "/var/log/indico/indico.log" ]; then
    echo "Last plugin messages in logs:"
    tail -100 /var/log/indico/indico.log | grep -i "plugin\|indico_push" | tail -3 || echo "   No recent plugin messages"
else
    echo "❌ Log file not found: /var/log/indico/indico.log"
fi

echo ""
echo "========================================="
echo "              SUMMARY"
echo "========================================="
echo ""
echo "If plugin is NOT showing up:"
echo "1. Reinstall: pip uninstall -y indico-push-notifications && pip install -e . --break-system-packages"
echo "2. Check config: sudo nano /opt/indico/etc/indico.conf"
echo "3. Restart: sudo systemctl restart indico indico-celery"
echo "4. Check logs: tail -f /var/log/indico/indico.log | grep -i plugin"
echo ""
echo "Quick fix command:"
echo "  cd /opt/indico/modules/indico-push-notifications && source /opt/indico/.venv-3/bin/activate && pip uninstall -y indico-push-notifications && pip install -e . --break-system-packages && sudo systemctl restart indico indico-celery"
echo ""
echo "========================================="
