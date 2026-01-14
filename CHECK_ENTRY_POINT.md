# Indico Push Notifications Plugin - Entry Point Debugging Guide

## Overview

Entry points are the mechanism through which Indico discovers and loads plugins. If a plugin's entry point is not properly registered, Indico will not see the plugin at all. This guide helps diagnose and fix entry point issues.

## Quick Status Check

### 1. Basic Entry Point Check
```bash
# On the server, run:
python -c "
import pkg_resources
eps = [ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')]
print('Found entry points:', eps)
if 'indico_push_notifications' in eps:
    print('✅ Entry point registered')
else:
    print('❌ Entry point NOT registered')
"
```

### 2. Detailed Entry Point Inspection
```bash
python -c "
import pkg_resources
print('=== All indico.plugins entry points ===')
for ep in pkg_resources.iter_entry_points('indico.plugins'):
    print(f'  {ep.name} -> {ep.module_name} ({ep.dist})')
"
```

## Entry Point Diagnostics

### What to Look For

**✅ Working entry point:**
```
indico_push_notifications -> indico_push_notifications (indico-push-notifications 1.0.0)
```

**❌ Missing entry point:**
- `indico_push_notifications` not in the list
- Different name or module path

**⚠️ Problematic entry point:**
- Wrong module name
- Wrong distribution name
- Import errors when loading

## Common Entry Point Problems

### Problem 1: Entry Point Not Registered
**Symptoms:**
- Plugin not in entry points list
- `indico setup list-plugins` doesn't show plugin

**Solution:**
```bash
# Reinstall in development mode
cd /opt/indico/modules/indico-push-notifications
pip uninstall -y indico-push-notifications
pip install -e . --break-system-packages

# Verify
python -c "import pkg_resources; print([ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')])"
```

### Problem 2: Wrong Entry Point Configuration
**Symptoms:**
- Entry point exists but with wrong module path
- Import errors when Indico tries to load it

**Check setup.py:**
```python
# Correct configuration in setup.py:
entry_points={
    "indico.plugins": [
        "indico_push_notifications = indico_push_notifications:IndicoPushNotificationsPlugin"
    ]
}
```

**Verify:**
- Module path: `indico_push_notifications` (package name)
- Class name: `IndicoPushNotificationsPlugin` (exact class name)
- No typos or incorrect indentation

### Problem 3: pyproject.toml Conflict
**Symptoms:**
- Entry points work intermittently
- Reinstall doesn't fix the issue

**Solution:**
```bash
# Temporarily remove pyproject.toml
cd /opt/indico/modules/indico-push-notifications
mv pyproject.toml pyproject.toml.backup
pip uninstall -y indico-push-notifications
pip install -e . --break-system-packages

# Test
python -c "import pkg_resources; print([ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')])"

# If it works, you can delete pyproject.toml or keep backup
```

## Step-by-Step Debugging

### Step 1: Check Current State
```bash
# 1. Check installation
pip list | grep indico-push-notifications

# 2. Check entry points
python -c "
import pkg_resources
for ep in pkg_resources.iter_entry_points('indico.plugins'):
    print(f'{ep.name}: {ep.module_name} ({ep.dist})')
"

# 3. Check Indico plugin list
indico setup list-plugins 2>/dev/null | grep -i push
```

### Step 2: Test Entry Point Loading
```bash
python -c "
import pkg_resources

# Find our entry point
for ep in pkg_resources.iter_entry_points('indico.plugins'):
    if ep.name == 'indico_push_notifications':
        print(f'Found: {ep.name}')
        
        # Try to load it
        try:
            plugin_class = ep.load()
            print(f'✅ Loaded: {plugin_class.__name__}')
            
            # Try to create instance
            plugin = plugin_class()
            print(f'✅ Created: {plugin.name}')
            
        except Exception as e:
            print(f'❌ Load error: {e}')
            import traceback
            traceback.print_exc()
        break
else:
    print('❌ Entry point not found')
"
```

### Step 3: Check Logs for Entry Point Activity
```bash
# Check if entry point logging is working
tail -f ~/log/notify-plugin.log | grep -i "entry point\|plugin.*load"

# Or check recent logs
grep -i "entry point\|plugin.*load\|initialization" ~/log/notify-plugin.log | tail -10
```

## Advanced Diagnostics

### Test Direct Import (Bypassing Entry Points)
```bash
cd /opt/indico/modules/indico-push-notifications
python -c "
import sys
sys.path.insert(0, '.')
try:
    import indico_push_notifications
    print('✅ Module imports directly')
    
    from indico_push_notifications import IndicoPushNotificationsPlugin
    plugin = IndicoPushNotificationsPlugin()
    print(f'✅ Plugin class works: {plugin.name}')
    
except Exception as e:
    print(f'❌ Direct import failed: {e}')
    import traceback
    traceback.print_exc()
"
```

### Check Python Package Structure
```bash
# Verify package structure
cd /opt/indico/modules/indico-push-notifications
find . -name "*.py" -type f | grep -v __pycache__ | sort

# Check __init__.py
head -50 indico_push_notifications/__init__.py

# Check if plugin class is defined
grep -n "class IndicoPushNotificationsPlugin" indico_push_notifications/__init__.py
```

### Verify Distribution Metadata
```bash
# Check what pip installed
pip show indico-push-notifications

# Check egg-info
ls -la /opt/indico/.venv-3/lib/python*/site-packages/ | grep indico-push

# Check entry_points.txt in egg-info
find /opt/indico/.venv-3 -name "entry_points.txt" -type f | xargs grep -l "indico.plugins" 2>/dev/null
```

## Fix Procedures

### Complete Reinstall Procedure
```bash
# 1. Clean removal
cd /opt/indico/modules/indico-push-notifications
pip uninstall -y indico-push-notifications
rm -rf indico_push_notifications.egg-info/ build/ dist/ __pycache__/

# 2. Remove problematic files
[ -f pyproject.toml ] && mv pyproject.toml pyproject.toml.backup

# 3. Fresh install
pip install -e . --break-system-packages

# 4. Verify
python -c "
import pkg_resources
eps = [ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')]
print('Entry points after reinstall:', eps)
print('✅ Success' if 'indico_push_notifications' in eps else '❌ Failed')
"
```

### Manual Entry Point Registration (Emergency)
If automatic registration fails, you can manually check:

1. **Check setup.py syntax:**
```bash
python -m py_compile setup.py && echo "✅ setup.py syntax OK" || echo "❌ setup.py syntax error"
```

2. **Check package structure:**
```bash
python -c "from setuptools import find_packages; print('Packages:', find_packages())"
```

3. **Manual build and install:**
```bash
python setup.py develop
```

## Monitoring Entry Point Loading

### Real-time Monitoring Script
```bash
#!/bin/bash
# monitor_entry_points.sh
echo "Monitoring entry point loading..."
while true; do
    clear
    echo "=== $(date) ==="
    echo ""
    echo "Entry points:"
    python -c "
import pkg_resources
for ep in pkg_resources.iter_entry_points('indico.plugins'):
    print(f'  {ep.name}')
" 2>/dev/null
    echo ""
    echo "Log file (~/log/notify-plugin.log):"
    tail -5 ~/log/notify-plugin.log 2>/dev/null || echo "  (log file not found)"
    echo ""
    echo "Press Ctrl+C to stop"
    sleep 5
done
```

### Check After Indico Restart
```bash
# Restart Indico and monitor logs
sudo systemctl restart indico indico-celery
tail -f /var/log/indico/indico.log | grep -i "plugin.*load\|entry.*point"
```

## Success Indicators

✅ **Entry point working correctly when:**
1. `indico_push_notifications` appears in pkg_resources entry points
2. Entry point can be loaded without errors
3. Plugin class can be instantiated
4. Log file shows entry point initialization messages
5. `indico setup list-plugins` shows the plugin
6. Plugin appears in Indico admin interface

## Troubleshooting Checklist

- [ ] Plugin installed via pip: `pip list | grep indico-push-notifications`
- [ ] Entry point registered: `indico_push_notifications` in entry points list
- [ ] Entry point loadable: No import errors when loading
- [ ] Plugin class exists: `IndicoPushNotificationsPlugin` class defined
- [ ] Module importable: Direct import works
- [ ] Logging active: Messages appear in `~/log/notify-plugin.log`
- [ ] Indico sees plugin: Appears in `indico setup list-plugins`
- [ ] No pyproject.toml conflicts: File removed or compatible

## Quick Reference Commands

```bash
# One-line status check
python -c "import pkg_resources; print('Entry points:', [ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')])"

# Quick fix
cd /opt/indico/modules/indico-push-notifications && pip uninstall -y indico-push-notifications && pip install -e . --break-system-packages

# Check logs
tail -f ~/log/notify-plugin.log | grep -i "entry\|plugin"

# Verify in Indico
indico setup list-plugins | grep indico_push_notifications
```

## Getting Help

If entry point issues persist:

1. **Collect debug information:**
```bash
cd /opt/indico/modules/indico-push-notifications
python test_entry_point.py
```

2. **Check system logs:**
```bash
sudo journalctl -u indico --since "5 minutes ago" | grep -i plugin
```

3. **Verify file permissions:**
```bash
ls -la /opt/indico/modules/indico-push-notifications/
ls -la /opt/indico/.venv-3/lib/python*/site-packages/indico_push_notifications*
```

---

**Remember:** Entry points are registered when the package is installed via pip. If you modify the plugin code without reinstalling, entry points won't update. Always reinstall after significant changes to `setup.py` or the plugin class structure.

*Last updated: $(date)*