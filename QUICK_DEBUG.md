# Indico Push Notifications Plugin - Quick Debug Guide

## 🚨 IMMEDIATE ACTION REQUIRED

Based on your current status, the plugin is **AVAILABLE** but **NOT ACTIVE**. Here's what to do:

### 1. ACTIVATE THE PLUGIN (30 seconds)
```bash
# On the server, run:
indico setup activate-plugin indico_push_notifications
```

### 2. VERIFY ACTIVATION
```bash
# Check if plugin is now active
indico setup list-plugins --active | grep indico_push_notifications
```

### 3. RUN MIGRATIONS
```bash
# Apply database migrations
indico db upgrade --plugin indico_push_notifications
```

### 4. RESTART INDICO
```bash
# Restart services
sudo systemctl restart indico indico-celery
```

### 5. CHECK IN WEB INTERFACE
1. Log into Indico as admin
2. Go to: **Admin → Plugins**
3. Look for **"Push Notifications"**
4. Click to configure

## 📊 CURRENT STATUS (from your output)

✅ **GOOD:**
- Plugin detected by Indico (`indico_push_notifications` in plugin list)
- Configuration file is being read (warnings show it's parsing your config)
- All dependencies likely installed

⚠️ **ISSUE:**
- Plugin is **available but not active**
- Need to activate via CLI or web interface

## 🔧 QUICK FIX SCRIPT

Save this as `fix_plugin.sh` and run it:

```bash
#!/bin/bash
echo "=== Fixing Indico Push Notifications Plugin ==="
echo "1. Activating plugin..."
indico setup activate-plugin indico_push_notifications
echo "2. Running migrations..."
indico db upgrade --plugin indico_push_notifications
echo "3. Restarting services..."
sudo systemctl restart indico indico-celery
echo "4. Checking status..."
indico setup list-plugins --active | grep indico_push_notifications && \
    echo "✅ Plugin activated successfully!" || \
    echo "❌ Activation failed, check logs"
echo "=== Done ==="
```

## 📝 ONE-LINE FIX

```bash
indico setup activate-plugin indico_push_notifications && \
indico db upgrade --plugin indico_push_notifications && \
sudo systemctl restart indico indico-celery && \
echo "Check: indico setup list-plugins --active | grep indico_push_notifications"
```

## 🔍 WHAT THOSE WARNINGS MEAN

The warnings `Ignoring unknown config key PUSH_NOTIFICATIONS_*` mean:
- ✅ Indico IS reading your config file
- ✅ Your plugin settings ARE being parsed
- ⚠️ Indico doesn't know what to do with them YET (because plugin isn't active)
- ✅ This is NORMAL and will be fixed after activation

## 🎯 VERIFICATION STEPS

After running the fix:

### Check 1: CLI Verification
```bash
# Should show plugin as active
indico setup list-plugins --active | grep "indico_push_notifications"
```

### Check 2: Web Interface
1. Login to Indico
2. Admin → Plugins
3. "Push Notifications" should appear
4. Click to access settings

### Check 3: Logs
```bash
# Check for activation messages
tail -f /var/log/indico/indico.log | grep -i "plugin.*indico_push"
```

## 🆘 IF STILL NOT WORKING

### Option A: Complete Reinstall
```bash
cd /opt/indico/modules/indico-push-notifications
pip uninstall -y indico-push-notifications
pip install -e . --break-system-packages
indico setup activate-plugin indico_push_notifications
sudo systemctl restart indico indico-celery
```

### Option B: Debug Mode
```bash
# Enable debug logging
cd /opt/indico/modules/indico-push-notifications
python -c "
from indico_push_notifications.logger import setup_logging, info
logger = setup_logging('debug')
info('Testing plugin loading')
print('Check ~/log/notify-plugin.log')
"

# Then activate and check logs
indico setup activate-plugin indico_push_notifications
tail -f ~/log/notify-plugin.log
```

## 📞 QUICK REFERENCE

| Command | Purpose | Expected Result |
|---------|---------|-----------------|
| `indico setup list-plugins` | List all plugins | Shows `indico_push_notifications` |
| `indico setup list-plugins --active` | List active plugins | Should show plugin AFTER activation |
| `indico setup activate-plugin indico_push_notifications` | Activate plugin | Success message |
| `indico db upgrade --plugin indico_push_notifications` | Run migrations | Migration output |
| `sudo systemctl restart indico indico-celery` | Restart services | Services restart |

## 🎉 SUCCESS INDICATORS

Plugin is working when:
1. ✅ `indico setup list-plugins --active` shows `indico_push_notifications`
2. ✅ No errors in `/var/log/indico/indico.log`
3. ✅ Plugin appears in Admin → Plugins web interface
4. ✅ Can click plugin to access settings page

## ⏱️ TIME ESTIMATE

- **Activation:** 30 seconds
- **Migrations:** 1-2 minutes
- **Restart:** 30 seconds
- **Verification:** 1 minute
- **Total:** ~3-4 minutes

## 🚀 NEXT STEPS AFTER ACTIVATION

1. Configure Telegram bot token
2. Set up VAPID keys for Web Push
3. Configure notification preferences
4. Test with a sample event

---

**EXECUTE NOW:** Run the activation command and report back!

```bash
indico setup activate-plugin indico_push_notifications
```

Then check: `indico setup list-plugins --active`
