# Indico Push Notifications Plugin - Troubleshooting Guide

## Плагин не отображается в Indico: Пошаговая диагностика

Если плагин не появляется в админке Indico (Админка → Плагины), выполните следующие шаги для диагностики.

### 🔍 Быстрая диагностика (5 минут)

#### 1. Подключитесь к серверу и проверьте базовые условия:

```bash
# Подключиться к серверу
ssh indico@nla2020

# Перейти в директорию плагина
cd /opt/indico/modules/indico-push-notifications

# Активировать окружение Indico
source /opt/indico/.venv-3/bin/activate
```

#### 2. Запустите быструю проверку:

```bash
# Проверка 1: Установлен ли плагин?
pip list | grep indico-push-notifications

# Проверка 2: Есть ли entry point?
python -c "
import pkg_resources
eps = [ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')]
print('Entry points:', eps)
if 'indico_push_notifications' in eps:
    print('✅ Entry point найден')
else:
    print('❌ Entry point НЕ найден')
"

# Проверка 3: Включен ли в конфигурации?
grep -i "enabled_plugins.*indico_push" /opt/indico/etc/indico.conf && echo "✅ В конфигурации" || echo "❌ НЕ в конфигурации"
```

### 📋 Полная диагностика

#### Шаг 1: Проверка установки плагина

```bash
# Переустановите плагин (если нужно)
cd /opt/indico/modules/indico-push-notifications
pip uninstall indico-push-notifications -y
pip install -e . --break-system-packages

# Проверьте установку
pip show indico-push-notifications
```

#### Шаг 2: Проверка entry points

Entry points - это механизм, через который Indico обнаруживает плагины. Без правильного entry point плагин не будет виден.

```bash
# Подробная проверка entry points
python -c "
import pkg_resources

print('=== Все entry points для indico.plugins ===')
for ep in pkg_resources.iter_entry_points('indico.plugins'):
    print(f'  {ep.name} -> {ep.module_name}')

print()
print('=== Наш плагин ===')
try:
    ep = pkg_resources.get_entry_info('indico-push-notifications', 'indico.plugins', 'indico_push_notifications')
    print(f'✅ Найден: {ep.module_name}')
except:
    print('❌ НЕ найден')
"
```

**Если entry point не найден:**
1. Проверьте `setup.py` - должен содержать:
   ```python
   entry_points={
       "indico.plugins": [
           "indico_push_notifications = indico_push_notifications:IndicoPushNotificationsPlugin"
       ]
   }
   ```
2. Переустановите плагин в development mode:
   ```bash
   pip install -e . --break-system-packages
   ```

#### Шаг 3: Проверка конфигурации Indico

```bash
# Просмотрите конфигурационный файл
sudo cat /opt/indico/etc/indico.conf | grep -i "enabled_plugins"

# Или отредактируйте
sudo nano /opt/indico/etc/indico.conf
```

**Убедитесь, что в файле есть:**
```python
ENABLED_PLUGINS = ['indico_push_notifications']
```

**Если плагин уже в списке, но не загружается:**
1. Проверьте синтаксис конфигурации:
   ```bash
   python -m py_compile /opt/indico/etc/indico.conf 2>/dev/null && echo "✅ Синтаксис OK" || echo "❌ Ошибка синтаксиса"
   ```
2. Убедитесь, что нет опечаток в имени плагина

#### Шаг 4: Проверка логов Indico

```bash
# Просмотр логов в реальном времени
tail -f /var/log/indico/indico.log | grep -i "plugin\|indico_push\|error"

# Поиск ошибок загрузки плагина
grep -i "plugin.*load\|indico_push\|import.*error" /var/log/indico/indico.log | tail -20

# Проверка через journalctl
sudo journalctl -u indico --since "10 minutes ago" | grep -i plugin
```

#### Шаг 5: Проверка через Indico API

```bash
# Проверьте, видит ли Indico плагин
python -c "
from indico.core.plugins import plugin_engine

# Все обнаруженные плагины
all_plugins = list(plugin_engine.get_all_plugins().keys())
print('Все плагины:', all_plugins)

# Активные плагины
active_plugins = list(plugin_engine.get_active_plugins().keys())
print('Активные плагины:', active_plugins)

if 'indico_push_notifications' in active_plugins:
    print('✅ Плагин активен в Indico')
elif 'indico_push_notifications' in all_plugins:
    print('⚠️  Плагин обнаружен, но не активен')
    print('   Проверьте ENABLED_PLUGINS в indico.conf')
else:
    print('❌ Плагин не обнаружен')
    print('   Проверьте entry points и установку')
"
```

#### Шаг 6: Проверка структуры плагина

```bash
# Убедитесь, что все файлы на месте
cd /opt/indico/modules/indico-push-notifications
ls -la

# Критичные файлы:
# ✅ setup.py - с правильными entry_points
# ✅ indico_push_notifications/__init__.py - с классом IndicoPushNotificationsPlugin
# ✅ requirements.txt - зависимости
# ✅ alembic.ini - миграции БД

# Проверьте класс плагина
grep -n "class IndicoPushNotificationsPlugin" indico_push_notifications/__init__.py
```

### 🚨 Частые проблемы и решения

#### Проблема 1: Entry point не регистрируется

**Симптомы:** Плагин не в списке entry points
**Решение:**
```bash
# Удалите pyproject.toml если он есть (может мешать)
cd /opt/indico/modules/indico-push-notifications
[ -f pyproject.toml ] && mv pyproject.toml pyproject.toml.backup

# Полная переустановка
pip uninstall indico-push-notifications -y
pip install -e . --break-system-packages

# Проверьте
python -c "import pkg_resources; print([ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')])"
```

#### Проблема 2: Ошибки импорта

**Симптомы:** В логах Indico ошибки импорта модулей
**Решение:**
```bash
# Установите зависимости
pip install -r requirements.txt

# Проверьте импорт вручную
cd /opt/indico/modules/indico-push-notifications
python -c "
import sys
sys.path.insert(0, '.')
try:
    import indico_push_notifications
    print('✅ Импорт работает')
except Exception as e:
    print(f'❌ Ошибка: {e}')
    import traceback
    traceback.print_exc()
"
```

#### Проблема 3: Плагин в конфигурации, но не загружается

**Симптомы:** Плагин в ENABLED_PLUGINS, но не активен
**Решение:**
1. Перезапустите Indico:
   ```bash
   sudo systemctl restart indico
   sudo systemctl restart indico-celery
   ```
2. Проверьте логи после перезапуска:
   ```bash
   tail -f /var/log/indico/indico.log | grep -i "startup\|plugin"
   ```
3. Убедитесь, что нет конфликтов с другими плагинами

#### Проблема 4: Конфликт версий Python

**Симптомы:** Разные версии Python в системе и в виртуальном окружении
**Решение:**
```bash
# Проверьте версии
python --version
/opt/indico/.venv-3/bin/python --version

# Убедитесь, что используете правильный Python
which python
which pip
```

### 🛠️ Скрипты для автоматической диагностики

#### Скрипт 1: Быстрая проверка (`quick_check.sh`)

```bash
#!/bin/bash
cd /opt/indico/modules/indico-push-notifications
source /opt/indico/.venv-3/bin/activate

echo "=== Быстрая проверка плагина ==="
echo "1. Установка: $(pip list | grep -q indico-push-notifications && echo '✅' || echo '❌')"
echo "2. Entry point: $(python -c \"import pkg_resources; eps=[ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')]; print('✅' if 'indico_push_notifications' in eps else '❌')\")"
echo "3. Конфигурация: $(grep -q \"enabled_plugins.*indico_push\" /opt/indico/etc/indico.conf && echo '✅' || echo '❌')"
echo "4. Сервисы: indico=$(systemctl is-active indico && echo '✅' || echo '❌'), celery=$(systemctl is-active indico-celery && echo '✅' || echo '❌')"
```

#### Скрипт 2: Полная диагностика (`check_server_plugin.sh`)

Запустите полную диагностику:
```bash
cd /opt/indico/modules/indico-push-notifications
./check_server_plugin.sh
```

### 🔄 Процесс переустановки

Если ничего не помогает, выполните полную переустановку:

```bash
# 1. Перейдите в директорию плагина
cd /opt/indico/modules/indico-push-notifications

# 2. Активируйте окружение
source /opt/indico/.venv-3/bin/activate

# 3. Удалите старую версию
pip uninstall -y indico-push-notifications

# 4. Очистите временные файлы
rm -rf indico_push_notifications.egg-info/ __pycache__/ indico_push_notifications/__pycache__/

# 5. Удалите проблемные файлы (если есть)
[ -f pyproject.toml ] && mv pyproject.toml pyproject.toml.backup

# 6. Установите заново
pip install -e . --break-system-packages

# 7. Проверьте entry points
python -c "import pkg_resources; print('Entry points:', [ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')])"

# 8. Перезапустите Indico
sudo systemctl restart indico
sudo systemctl restart indico-celery

# 9. Проверьте логи
tail -f /var/log/indico/indico.log | grep -i "plugin\|startup"
```

### 📊 Проверка через веб-интерфейс

После успешной загрузки плагина:

1. Залогиньтесь в Indico как администратор
2. Перейдите: **Админка → Плагины**
3. Найдите **"Push Notifications"** в списке
4. Нажмите на плагин для настройки параметров

### 📝 Чек-лист успешной загрузки

- [ ] Плагин установлен через pip: `pip list | grep indico-push-notifications`
- [ ] Entry point зарегистрирован: `indico_push_notifications` в списке entry points
- [ ] Плагин в конфигурации: `indico_push_notifications` в `ENABLED_PLUGINS`
- [ ] Indico видит плагин: `indico_push_notifications` в активных плагинах
- [ ] Нет ошибок в логах: `tail -f /var/log/indico/indico.log`
- [ ] Сервисы работают: `systemctl status indico`
- [ ] Плагин отображается в веб-интерфейсе: Админка → Плагины

### 🆘 Экстренная помощь

Если после всех проверок плагин не загружается:

1. **Проверьте права доступа:**
   ```bash
   ls -la /opt/indico/modules/indico-push-notifications
   ls -la /opt/indico/etc/indico.conf
   ```

2. **Проверьте зависимости Indico:**
   ```bash
   pip list | grep indico
   ```

3. **Создайте минимальный тестовый плагин:**
   ```bash
   # Создайте простой плагин для проверки
   cat > /tmp/test_plugin.py << 'EOF'
   from indico.core.plugins import IndicoPlugin
   class TestPlugin(IndicoPlugin):
       name = 'test_plugin'
       friendly_name = 'Test Plugin'
   EOF
   
   # Проверьте, загружается ли он
   ```

4. **Обратитесь к логам системы:**
   ```bash
   sudo dmesg | tail -20
   sudo journalctl -xe | tail -50
   ```

### 📞 Контакты и ссылки

- **Сервер:** nla2020 (192.168.191.169)
- **Пользователь:** indico
- **Директория плагина:** `/opt/indico/modules/indico-push-notifications`
- **Конфигурация:** `/opt/indico/etc/indico.conf`
- **Логи:** `/var/log/indico/`
- **Сервисы:** `indico`, `indico-celery`

### 🎯 Итоговая команда для проверки

```bash
ssh indico@nla2020 "cd /opt/indico/modules/indico-push-notifications && source /opt/indico/.venv-3/bin/activate && python -c \"from indico.core.plugins import plugin_engine; print('Активные плагины:', list(plugin_engine.get_active_plugins().keys()))\""
```

Если команда возвращает `indico_push_notifications` в списке - плагин загружен успешно!

---
*Последнее обновление: $(date)*
*Для дополнительной помощи проверьте SERVER_CONTEXT.md*