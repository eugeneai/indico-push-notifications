# How to Check if Indico Push Notifications Plugin is Loading

## Quick Start: One-Command Check

Run this command from your local machine to check the plugin status on the server:

```bash
ssh indico@nla2020 "cd /opt/indico/modules/indico-push-notifications && source /opt/indico/.venv-3/bin/activate && python -c \"from indico.core.plugins import plugin_engine; active=list(plugin_engine.get_active_plugins().keys()); print('Active plugins:', active); print('✅ SUCCESS' if 'indico_push_notifications' in active else '❌ PLUGIN NOT ACTIVE')\""
```

## Step-by-Step Manual Check

### 1. Connect to Server and Prepare Environment

```bash
# Connect to the Indico server
ssh indico@nla2020

# Navigate to plugin directory
cd /opt/indico/modules/indico-push-notifications

# Activate Indico's Python environment
source /opt/indico/.venv-3/bin/activate
```

### 2. Run the 5 Critical Checks

#### Check 1: Plugin Installation
```bash
pip list | grep indico-push-notifications
```
**Expected:** Should show `indico-push-notifications 1.0.0`

#### Check 2: Entry Points Registration
```bash
python -c "
import pkg_resources
eps = [ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')]
print('Registered plugins:', eps)
print('✅ Found' if 'indico_push_notifications' in eps else '❌ Missing')
"
```
**Expected:** `indico_push_notifications` should be in the list

#### Check 3: Configuration
```bash
grep -i "enabled_plugins" /opt/indico/etc/indico.conf
```
**Expected:** Should include `'indico_push_notifications'` in the ENABLED_PLUGINS list

#### Check 4: Indico Plugin Engine
```bash
python -c "
from indico.core.plugins import plugin_engine
active = list(plugin_engine.get_active_plugins().keys())
print('Active plugins in Indico:', active)
if 'indico_push_notifications' in active:
    print('✅✅✅ PLUGIN IS LOADED AND ACTIVE! ✅✅✅')
    print('Check: Admin → Plugins → Push Notifications')
else:
    print('❌ Plugin not active')
    all_plugins = list(plugin_engine.get_all_plugins().keys())
    print('All discovered plugins:', all_plugins)
"
```

#### Check 5: Service Status
```bash
systemctl status indico --no-pager -l | head -20
systemctl status indico-celery --no-pager -l | head -20
```

### 3. Check Logs for Errors

```bash
# Real-time log monitoring
tail -f /var/log/indico/indico.log | grep -i "plugin\|indico_push\|error"

# Recent errors
tail -50 /var/log/indico/indico-error.log

# Search for plugin loading messages
grep -i "loading plugin\|plugin.*load\|indico_push" /var/log/indico/indico.log | tail -10
```

## Common Problems and Solutions

### Problem 1: Plugin not in entry points
**Symptoms:** `indico_push_notifications` not in registered plugins list
**Solution:**
```bash
# Reinstall in development mode
pip uninstall indico-push-notifications -y
pip install -e . --break-system-packages

# Verify
python -c "import pkg_resources; print([ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')])"
```

### Problem 2: Plugin not in configuration
**Symptoms:** Plugin not in ENABLED_PLUGINS
**Solution:**
```bash
# Edit configuration
sudo nano /opt/indico/etc/indico.conf

# Add or ensure this line exists:
ENABLED_PLUGINS = ['indico_push_notifications']

# Restart Indico
sudo systemctl restart indico indico-celery
```

### Problem 3: Plugin discovered but not active
**Symptoms:** Plugin in all_plugins but not in active_plugins
**Solution:**
1. Check ENABLED_PLUGINS configuration
2. Check for import errors in logs
3. Restart Indico services

### Problem 4: Import errors in logs
**Symptoms:** Python import errors in `/var/log/indico/indico.log`
**Solution:**
```bash
# Install missing dependencies
pip install -r requirements.txt

# Test import manually
python -c "import indico_push_notifications; print('✅ Import successful')"
```

## Quick Diagnostic Script

Save this as `check_plugin.sh` on the server:

```bash
#!/bin/bash
cd /opt/indico/modules/indico-push-notifications
source /opt/indico/.venv-3/bin/activate

echo "=== Plugin Status Check ==="
echo "1. Installed: $(pip list | grep -q indico-push-notifications && echo '✅' || echo '❌')"
echo "2. Entry point: $(python -c \"import pkg_resources; eps=[ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')]; print('✅' if 'indico_push_notifications' in eps else '❌')\")"
echo "3. In config: $(grep -q 'indico_push_notifications' /opt/indico/etc/indico.conf && echo '✅' || echo '❌')"
echo "4. Active in Indico: $(python -c \"from indico.core.plugins import plugin_engine; active=list(plugin_engine.get_active_plugins().keys()); print('✅' if 'indico_push_notifications' in active else '❌')\")"
echo "5. Services: indico=$(systemctl is-active indico && echo '✅' || echo '❌'), celery=$(systemctl is-active indico-celery && echo '✅' || echo '❌')"
```

## Complete Reinstall Procedure

If nothing works, perform a complete reinstall:

```bash
# 1. Clean up
cd /opt/indico/modules/indico-push-notifications
source /opt/indico/.venv-3/bin/activate
pip uninstall -y indico-push-notifications
rm -rf indico_push_notifications.egg-info/ __pycache__/

# 2. Remove problematic files
[ -f pyproject.toml ] && mv pyproject.toml pyproject.toml.backup

# 3. Reinstall
pip install -e . --break-system-packages

# 4. Verify entry points
python -c "import pkg_resources; print('Entry points:', [ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')])"

# 5. Restart services
sudo systemctl restart indico indico-celery

# 6. Monitor logs
tail -f /var/log/indico/indico.log | grep -i "plugin\|startup"
```

## Verification in Web Interface

After successful loading:
1. Log into Indico as administrator
2. Go to **Admin → Plugins**
3. Look for **"Push Notifications"** in the plugins list
4. Click on it to access plugin settings

## Emergency Commands

### Check plugin loading in real-time:
```bash
watch -n 5 'cd /opt/indico/modules/indico-push-notifications && source /opt/indico/.venv-3/bin/activate && python -c "from indico.core.plugins import plugin_engine; print(\"Active:\", list(plugin_engine.get_active_plugins().keys()))"'
```

### One-line status check:
```bash
cd /opt/indico/modules/indico-push-notifications && source /opt/indico/.venv-3/bin/activate && python -c "from indico.core.plugins import plugin_engine; active=list(plugin_engine.get_active_plugins().keys()); print('✅ Loaded' if 'indico_push_notifications' in active else '❌ Not loaded'); print('All active:', active)"
```

## Key Files and Locations

- **Plugin directory:** `/opt/indico/modules/indico-push-notifications`
- **Indico config:** `/opt/indico/etc/indico.conf`
- **Logs:** `/var/log/indico/indico.log`
- **Error logs:** `/var/log/indico/indico-error.log`
- **Services:** `indico`, `indico-celery`

## Success Indicators

The plugin is successfully loading when:
1. ✅ `indico_push_notifications` appears in entry points
2. ✅ Plugin is in `ENABLED_PLUGINS` in `indico.conf`
3. ✅ `indico_push_notifications` is in active plugins list
4. ✅ No import errors in logs
5. ✅ Plugin appears in Admin → Plugins web interface

## Getting Help

If issues persist:
1. Check all logs: `sudo journalctl -u indico --since "1 hour ago"`
2. Verify file permissions: `ls -la /opt/indico/modules/indico-push-notifications/`
3. Test minimal plugin import: `python -c "import sys; sys.path.insert(0, '.'); import indico_push_notifications"`

---
*Last updated: $(date)*  
*For detailed server context, see SERVER_CONTEXT.md*