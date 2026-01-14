# Проверка загрузки плагина Indico Push Notifications

## Быстрая диагностика

### 1. Проверка базовых условий на сервере

```bash
# Подключиться к серверу
ssh indico@nla2020

# Перейти в директорию плагина
cd /opt/indico/modules/indico-push-notifications

# Активировать окружение Indico
source /opt/indico/.venv-3/bin/activate
```

### 2. Быстрые команды для проверки

#### Проверка установки плагина:
```bash
# Проверить установлен ли плагин через pip
pip list | grep indico-push-notifications

# Проверить entry points
python -c "
import pkg_resources
for ep in pkg_resources.iter_entry_points('indico.plugins'):
    print(f'{ep.name}: {ep.module_name}')
"
```

#### Проверка импорта плагина:
```bash
# Проверить может ли плагин импортироваться
python -c "
import sys
sys.path.insert(0, '.')
import indico_push_notifications
print('✅ Plugin imports successfully')

from indico_push_notifications import IndicoPushNotificationsPlugin
plugin = IndicoPushNotificationsPlugin()
print(f'✅ Plugin class: {plugin.name}')
"
```

#### Проверка конфигурации Indico:
```bash
# Проверить конфигурационный файл
grep -i "enabled_plugins\|indico_push" /opt/indico/etc/indico.conf

# Проверить синтаксис конфигурации
python -m py_compile /opt/indico/etc/indico.conf 2>/dev/null && echo "✅ Config syntax OK" || echo "❌ Config syntax error"
```

### 3. Проверка через Indico API

```bash
# Проверить загрузку плагина через Indico
python -c "
from indico.core.plugins import plugin_engine

# Получить все активные плагины
active_plugins = list(plugin_engine.get_active_plugins().keys())
print('Active plugins:', active_plugins)

if 'indico_push_notifications' in active_plugins:
    print('✅ Our plugin is loaded and active')
else:
    print('❌ Our plugin is NOT active')
    
    # Проверить все обнаруженные плагины
    all_plugins = list(plugin_engine.get_all_plugins().keys())
    print('All discovered plugins:', all_plugins)
    
    if 'indico_push_notifications' in all_plugins:
        print('⚠️  Plugin discovered but not active (check ENABLED_PLUGINS)')
    else:
        print('❌ Plugin not discovered at all (check entry points)')
"
```

## Подробная диагностика

### Шаг 1: Проверка логов Indico

```bash
# Просмотр логов в реальном времени
tail -f /var/log/indico/indico.log | grep -i "plugin\|push\|indico_push"

# Просмотр ошибок
tail -f /var/log/indico/indico-error.log

# Поиск сообщений о загрузке плагинов
grep -i "loading plugin\|plugin.*load\|indico_push" /var/log/indico/indico.log | tail -20

# Проверка через journalctl
sudo journalctl -u indico --since "10 minutes ago" | grep -i plugin
```

### Шаг 2: Проверка entry points

Entry points - это механизм, через который Indico обнаруживает плагины. Проверьте:

```bash
# Проверить все entry points плагинов
python -c "
import pkg_resources

print('=== All indico.plugins entry points ===')
for ep in pkg_resources.iter_entry_points('indico.plugins'):
    print(f'  {ep.name}: {ep.module_name} ({ep.dist})')

print()
print('=== Our plugin entry point ===')
try:
    ep = pkg_resources.get_entry_info('indico-push-notifications', 'indico.plugins', 'indico_push_notifications')
    print(f'✅ Found: {ep.module_name}')
    print(f'   Distribution: {ep.dist}')
except:
    print('❌ Entry point not found')
"
```

### Шаг 3: Проверка структуры плагина

```bash
# Перейти в директорию плагина
cd /opt/indico/modules/indico-push-notifications

# Проверить критичные файлы
ls -la

# Должны присутствовать:
# - setup.py (с entry_points)
# - indico_push_notifications/__init__.py (с классом IndicoPushNotificationsPlugin)
# - requirements.txt
# - alembic.ini

# Проверить класс плагина
grep -n "class IndicoPushNotificationsPlugin" indico_push_notifications/__init__.py

# Проверить setup.py на наличие entry_points
grep -A5 -B5 "entry_points" setup.py
```

### Шаг 4: Проверка конфигурации Indico

```bash
# Просмотреть конфигурационный файл
sudo cat /opt/indico/etc/indico.conf | grep -i "enabled_plugins\|push_notifications"

# Или отредактировать конфигурацию
sudo nano /opt/indico/etc/indico.conf
```

Убедитесь, что в конфигурации есть:
```python
ENABLED_PLUGINS = ['indico_push_notifications']

# Конфигурация плагина (опционально, но рекомендуется)
PUSH_NOTIFICATIONS_TELEGRAM_BOT_TOKEN = 'ваш_токен'
PUSH_NOTIFICATIONS_TELEGRAM_BOT_USERNAME = '@ваш_бот'
PUSH_NOTIFICATIONS_VAPID_PUBLIC_KEY = 'ваш_публичный_ключ'
PUSH_NOTIFICATIONS_VAPID_PRIVATE_KEY = 'ваш_приватный_ключ'
PUSH_NOTIFICATIONS_VAPID_EMAIL = 'ваш_email'
```

### Шаг 5: Проверка сервисов Indico

```bash
# Проверить статус сервисов
sudo systemctl status indico
sudo systemctl status indico-celery

# Перезапустить сервисы (если нужно)
sudo systemctl restart indico
sudo systemctl restart indico-celery

# Проверить логи после перезапуска
tail -f /var/log/indico/indico.log | grep -i "startup\|plugin"
```

## Скрипты для автоматической проверки

### Скрипт 1: Быстрая проверка (check_plugin_quick.sh)

```bash
#!/bin/bash
echo "=== Quick Plugin Check ==="
cd /opt/indico/modules/indico-push-notifications
source /opt/indico/.venv-3/bin/activate

echo "1. Checking pip installation..."
pip list | grep indico-push-notifications || echo "❌ Not installed"

echo "2. Checking entry points..."
python -c "
import pkg_resources
eps = [ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')]
print('Found:', eps)
if 'indico_push_notifications' in eps:
    print('✅ Entry point OK')
else:
    print('❌ Entry point missing')
"

echo "3. Checking config..."
grep -i "enabled_plugins.*indico_push" /opt/indico/etc/indico.conf && echo "✅ In config" || echo "❌ Not in config"

echo "4. Checking logs..."
tail -5 /var/log/indico/indico.log | grep -i plugin && echo "✅ Plugin messages in log" || echo "⚠️ No plugin messages"
```

### Скрипт 2: Полная диагностика (diagnose_plugin.py)

```python
#!/usr/bin/env python3
import sys
import pkg_resources
import subprocess

def check_entry_points():
    print("Checking entry points...")
    found = False
    for ep in pkg_resources.iter_entry_points('indico.plugins'):
        print(f"  - {ep.name}: {ep.module_name}")
        if ep.name == 'indico_push_notifications':
            found = True
    
    if found:
        print("✅ Entry point found")
        return True
    else:
        print("❌ Entry point not found")
        return False

def check_config():
    print("\nChecking configuration...")
    try:
        with open('/opt/indico/etc/indico.conf', 'r') as f:
            content = f.read()
            if 'indico_push_notifications' in content:
                print("✅ Plugin in config")
                return True
            else:
                print("❌ Plugin not in config")
                return False
    except FileNotFoundError:
        print("❌ Config file not found")
        return False

def check_logs():
    print("\nChecking logs...")
    try:
        result = subprocess.run(
            ['tail', '-20', '/var/log/indico/indico.log'],
            capture_output=True,
            text=True
        )
        if 'plugin' in result.stdout.lower() or 'indico_push' in result.stdout.lower():
            print("✅ Plugin messages in logs")
            return True
        else:
            print("⚠️ No plugin messages in recent logs")
            return False
    except Exception as e:
        print(f"❌ Error checking logs: {e}")
        return False

def main():
    print("=== Indico Push Notifications Plugin Diagnostic ===")
    
    results = []
    results.append(('Entry Points', check_entry_points()))
    results.append(('Configuration', check_config()))
    results.append(('Logs', check_logs()))
    
    print("\n=== Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All checks passed - plugin should be loading")
    else:
        print("❌ Some checks failed - see above for details")
        
        print("\n=== Next Steps ===")
        print("1. Check ENABLED_PLUGINS in /opt/indico/etc/indico.conf")
        print("2. Restart Indico: sudo systemctl restart indico indico-celery")
        print("3. Check logs: tail -f /var/log/indico/indico.log")

if __name__ == '__main__':
    main()
```

## Частые проблемы и решения

### Проблема 1: Плагин не в списке entry points
**Решение:**
```bash
cd /opt/indico/modules/indico-push-notifications
pip uninstall indico-push-notifications -y
pip install -e . --break-system-packages
```

### Проблема 2: Плагин в entry points, но не загружается
**Решение:**
1. Проверьте `ENABLED_PLUGINS` в `indico.conf`
2. Перезапустите Indico: `sudo systemctl restart indico indico-celery`
3. Проверьте логи на ошибки импорта

### Проблема 3: Ошибки импорта в логах
**Решение:**
```bash
# Проверить зависимости
pip install -r requirements.txt

# Проверить импорт вручную
cd /opt/indico/modules/indico-push-notifications
python -c "import indico_push_notifications" 2>&1
```

### Проблема 4: Конфликт с pyproject.toml
**Решение:**
```bash
cd /opt/indico/modules/indico-push-notifications
mv pyproject.toml pyproject.toml.backup
pip uninstall indico-push-notifications -y
pip install -e . --break-system-packages
# Если работает, можно удалить backup: rm pyproject.toml.backup
```

## Проверка через веб-интерфейс

После того как плагин загрузится:
1. Залогиньтесь в Indico как администратор
2. Перейдите в Админку → Плагины
3. Найдите "Push Notifications" в списке плагинов
4. Нажмите на плагин для настройки

## Мониторинг загрузки плагина

### Команда для постоянного мониторинга:
```bash
# Следить за логами в реальном времени
tail -f /var/log/indico/indico.log | grep --color -i "plugin\|indico_push\|error"

# Или использовать watch для периодической проверки
watch -n 5 'cd /opt/indico/modules/indico-push-notifications && source /opt/indico/.venv-3/bin/activate && python -c "from indico.core.plugins import plugin_engine; print(\"Active:\", list(plugin_engine.get_active_plugins().keys()))"'
```

## Экстренные меры

Если ничего не помогает:

1. **Полная переустановка:**
```bash
cd /opt/indico/modules/indico-push-notifications
source /opt/indico/.venv-3/bin/activate

# Удалить все следы плагина
pip uninstall -y indico-push-notifications
rm -rf indico_push_notifications.egg-info/ __pycache__/ indico_push_notifications/__pycache__/

# Переустановить
pip install -e . --break-system-packages

# Проверить
python -c "import pkg_resources; print([ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')])"

# Перезапустить Indico
sudo systemctl restart indico indico-celery
```

2. **Проверка через интерактивный Python:**
```bash
cd /opt/indico
source .venv-3/bin/activate
python

# В интерактивной сессии:
>>> from indico.core.plugins import plugin_engine
>>> list(plugin_engine.get_active_plugins().keys())
>>> import indico_push_notifications
>>> from indico_push_notifications import IndicoPushNotificationsPlugin
>>> plugin = IndicoPushNotificationsPlugin()
>>> plugin.name
```

## Контакты для помощи

- **Логи:** `/var/log/indico/`
- **Конфигурация:** `/opt/indico/etc/indico.conf`
- **Плагин:** `/opt/indico/modules/indico-push-notifications`
- **Сервисы:** `indico`, `indico-celery`

Последнее обновление: $(date)