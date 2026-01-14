# Quick Status Commands for Indico Push Notifications Plugin

## One-Line Status Check

```bash
# Check if plugin is available and active
indico setup list-plugins | grep -A1 -B1 "indico_push_notifications"
```

## Complete Status Check (3 commands)

```bash
# 1. Check installation
pip list | grep indico-push-notifications && echo "✅ Installed" || echo "❌ Not installed"

# 2. Check availability in Indico
indico setup list-plugins | grep -q "indico_push_notifications" && echo "✅ Available in Indico" || echo "❌ Not available"

# 3. Check activation status
indico setup list-plugins --active 2>/dev/null | grep -q "indico_push_notifications" && echo "✅ ACTIVE" || echo "⚠️  Available but NOT active"
```

## Quick Activation Sequence

```bash
# Activate the plugin
indico setup activate-plugin indico_push_notifications

# Run migrations
indico db upgrade --plugin indico_push_notifications

# Restart services
sudo systemctl restart indico indico-celery

# Verify activation
indico setup list-plugins --active 2>/dev/null | grep "indico_push_notifications" && echo "✅ Plugin activated!" || echo "❌ Activation failed"
```

## Web Interface Check

After activation:
1. Log into Indico as admin
2. Go to: **Admin → Plugins**
3. Look for **"Push Notifications"** in the list
4. Click to configure plugin settings

## Troubleshooting Commands

### If plugin not showing up:
```bash
# Reinstall plugin
cd /opt/indico/modules/indico-push-notifications
pip uninstall -y indico-push-notifications
pip install -e . --break-system-packages

# Check entry points
python -c "import pkg_resources; print('Entry points:', [ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')])"
```

### If configuration warnings appear:
```bash
# Check config file
grep -i "push_notifications\|enabled_plugins" /opt/indico/etc/indico.conf

# The warnings about unknown config keys are normal until plugin is fully activated
```

### Check logs:
```bash
# Monitor logs in real-time
tail -f /var/log/indico/indico.log | grep -i "plugin\|indico_push"

# Recent errors
tail -50 /var/log/indico/indico-error.log
```

## Status Summary Command

```bash
echo "=== Plugin Status ===" && \
echo "Installation: $(pip list | grep -q indico-push-notifications && echo '✅' || echo '❌')" && \
echo "Available: $(indico setup list-plugins 2>/dev/null | grep -q indico_push_notifications && echo '✅' || echo '❌')" && \
echo "Active: $(indico setup list-plugins --active 2>/dev/null | grep -q indico_push_notifications && echo '✅' || echo '❌')" && \
echo "Services: indico=$(systemctl is-active indico && echo '✅' || echo '❌'), celery=$(systemctl is-active indico-celery && echo '✅' || echo '❌')"
```

## Quick Reference

| Command | Purpose | Expected Output |
|---------|---------|-----------------|
| `indico setup list-plugins` | List all available plugins | Should include `indico_push_notifications` |
| `indico setup list-plugins --active` | List active plugins | Should include `indico_push_notifications` after activation |
| `indico setup activate-plugin indico_push_notifications` | Activate plugin | Success message |
| `indico db upgrade --plugin indico_push_notifications` | Run plugin migrations | Migration output |
| `sudo systemctl restart indico indico-celery` | Restart Indico | Services restart |

## Current Status (Based on your output)

✅ **GOOD NEWS:** Plugin is AVAILABLE in Indico (`indico_push_notifications` appears in plugin list)

⚠️ **NEXT STEP:** Need to ACTIVATE the plugin and run migrations

## Immediate Actions Required

1. **Activate plugin:**
   ```bash
   indico setup activate-plugin indico_push_notifications
   ```

2. **Run migrations:**
   ```bash
   indico db upgrade --plugin indico_push_notifications
   ```

3. **Restart Indico:**
   ```bash
   sudo systemctl restart indico indico-celery
   ```

4. **Verify in web interface:**
   - Log into Indico
   - Go to Admin → Plugins
   - Check for "Push Notifications"

## Notes

- The warnings about `Ignoring unknown config key` are normal - they show that Indico is reading your configuration
- Plugin appears as "Indico Push Notifications Plugin." in the list (note the trailing dot)
- Once activated, the plugin settings will be accessible in the web interface

---
*Last updated: $(date)*