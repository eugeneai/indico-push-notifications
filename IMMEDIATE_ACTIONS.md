# IMMEDIATE ACTIONS: Проверка загрузки плагина Indico Push Notifications

## 🚨 СРОЧНЫЕ ДЕЙСТВИЯ (5 минут)

### 1. Подключитесь к серверу и выполните быструю проверку:

```bash
# Подключение к серверу
ssh indico@nla2020

# Переход в директорию плагина
cd /opt/indico/modules/indico-push-notifications

# Активация окружения Indico
source /opt/indico/.venv-3/bin/activate
```

### 2. Запустите КРИТИЧЕСКИЕ проверки:

```bash
# ПРОВЕРКА 1: Установлен ли плагин?
echo "=== ПРОВЕРКА 1: Установка плагина ==="
pip list | grep indico-push-notifications
if [ $? -eq 0 ]; then
    echo "✅ Плагин установлен через pip"
else
    echo "❌ Плагин НЕ установлен через pip"
    echo "   Выполните: pip install -e . --break-system-packages"
fi

# ПРОВЕРКА 2: Зарегистрирован ли entry point?
echo -e "\n=== ПРОВЕРКА 2: Entry points ==="
python -c "
import pkg_resources
eps = [ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')]
print('Найдены entry points:', eps)
if 'indico_push_notifications' in eps:
    print('✅ Наш плагин зарегистрирован')
else:
    print('❌ Наш плагин НЕ зарегистрирован')
"

# ПРОВЕРКА 3: Включен ли в конфигурации?
echo -e "\n=== ПРОВЕРКА 3: Конфигурация Indico ==="
if grep -q "ENABLED_PLUGINS.*indico_push_notifications" /opt/indico/etc/indico.conf; then
    echo "✅ Плагин включен в конфигурации"
    grep "ENABLED_PLUGINS" /opt/indico/etc/indico.conf
else
    echo "❌ Плагин НЕ включен в конфигурации"
    echo "   Добавьте в /opt/indico/etc/indico.conf:"
    echo "   ENABLED_PLUGINS = ['indico_push_notifications']"
fi

# ПРОВЕРКА 4: Работают ли сервисы?
echo -e "\n=== ПРОВЕРКА 4: Системные сервисы ==="
if systemctl is-active --quiet indico; then
    echo "✅ Сервис indico работает"
else
    echo "❌ Сервис indico НЕ работает"
fi

if systemctl is-active --quiet indico-celery; then
    echo "✅ Сервис indico-celery работает"
else
    echo "⚠️  Сервис indico-celery НЕ работает"
fi
```

### 3. Проверьте загрузку плагина через Indico API:

```bash
echo -e "\n=== ПРОВЕРКА 5: Загрузка в Indico ==="
python -c "
try:
    from indico.core.plugins import plugin_engine
    
    # Все плагины, которые видит Indico
    all_plugins = list(plugin_engine.get_all_plugins().keys())
    print('Все обнаруженные плагины:', all_plugins)
    
    # Активные плагины
    active_plugins = list(plugin_engine.get_active_plugins().keys())
    print('Активные плагины:', active_plugins)
    
    if 'indico_push_notifications' in active_plugins:
        print('✅✅✅ ПЛАГИН АКТИВЕН В INDICO! ✅✅✅')
        print('   Проверьте: Админка → Плагины')
    elif 'indico_push_notifications' in all_plugins:
        print('⚠️  Плагин обнаружен, но НЕ активен')
        print('   Причина: Нет в ENABLED_PLUGINS или ошибка загрузки')
    else:
        print('❌❌❌ Плагин НЕ обнаружен Indico ❌❌❌')
        print('   Причина: Проблема с entry points или установкой')
        
except ImportError as e:
    print('❌ Не удалось импортировать Indico:', e)
except Exception as e:
    print('❌ Ошибка при проверке:', e)
    import traceback
    traceback.print_exc()
"
```

## 🔧 БЫСТРЫЕ ИСПРАВЛЕНИЯ

### Если плагин НЕ в entry points:
```bash
# Переустановите плагин
pip uninstall indico-push-notifications -y
pip install -e . --break-system-packages

# Проверьте снова
python -c "import pkg_resources; print([ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')])"
```

### Если плагин НЕ в конфигурации:
```bash
# Добавьте плагин в конфигурацию
sudo sh -c "echo \"ENABLED_PLUGINS = ['indico_push_notifications']\" >> /opt/indico/etc/indico.conf"

# ИЛИ отредактируйте файл
sudo nano /opt/indico/etc/indico.conf
# Добавьте: ENABLED_PLUGINS = ['indico_push_notifications']
```

### Если нужно перезапустить Indico:
```bash
# Перезапустите сервисы
sudo systemctl restart indico
sudo systemctl restart indico-celery

# Проверьте логи
echo "Следите за логами (Ctrl+C для остановки):"
tail -f /var/log/indico/indico.log | grep -i "plugin\|startup\|indico_push"
```

## 📋 КОМАНДА ДЛЯ ОДНОЙ СТРОКИ

Выполните ВСЕ проверки одной командой:

```bash
ssh indico@nla2020 "cd /opt/indico/modules/indico-push-notifications && source /opt/indico/.venv-3/bin/activate && echo '=== БЫСТРАЯ ДИАГНОСТИКА ===' && echo '1. Установка:' && (pip list | grep -q indico-push-notifications && echo '✅' || echo '❌') && echo '2. Entry points:' && python -c \"import pkg_resources; eps=[ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')]; print('✅' if 'indico_push_notifications' in eps else '❌')\" && echo '3. Конфигурация:' && (grep -q 'ENABLED_PLUGINS.*indico_push_notifications' /opt/indico/etc/indico.conf && echo '✅' || echo '❌') && echo '4. Indico видит плагин:' && python -c \"from indico.core.plugins import plugin_engine; active=list(plugin_engine.get_active_plugins().keys()); print('✅' if 'indico_push_notifications' in active else '❌')\""
```

## 🎯 ЧТО ДЕЛАТЬ ДАЛЬШЕ

### Если ВСЕ проверки пройдены (✅✅✅):
1. Плагин загружен в Indico
2. Проверьте веб-интерфейс: **Админка → Плагины**
3. Настройте параметры плагина

### Если есть проблемы (❌):
Выполните ПОЛНУЮ ПЕРЕУСТАНОВКУ:

```bash
# 1. Очистка
cd /opt/indico/modules/indico-push-notifications
source /opt/indico/.venv-3/bin/activate
pip uninstall -y indico-push-notifications
rm -rf indico_push_notifications.egg-info/ __pycache__/

# 2. Удалите pyproject.toml если есть (частая проблема)
[ -f pyproject.toml ] && mv pyproject.toml pyproject.toml.backup

# 3. Переустановка
pip install -e . --break-system-packages

# 4. Проверка
python -c "import pkg_resources; print('Entry points:', [ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')])"

# 5. Перезапуск
sudo systemctl restart indico indico-celery

# 6. Проверка логов
tail -f /var/log/indico/indico.log | grep -i "plugin"
```

## 📞 ЭКСТРЕННАЯ ПОМОЩЬ

### Проверьте логи на ошибки:
```bash
# Последние ошибки
tail -50 /var/log/indico/indico-error.log

# Поиск проблем с плагином
grep -i "indico_push\|plugin.*error\|import.*error" /var/log/indico/indico.log | tail -20
```

### Проверьте структуру плагина:
```bash
# Критичные файлы должны быть:
ls -la /opt/indico/modules/indico-push-notifications/
# ✅ setup.py
# ✅ indico_push_notifications/__init__.py
# ✅ requirements.txt
# ✅ alembic.ini
```

## 🏁 ИТОГОВАЯ ПРОВЕРКА УСПЕХА

Плагин УСПЕШНО загружен если:

```bash
python -c "
from indico.core.plugins import plugin_engine
active = list(plugin_engine.get_active_plugins().keys())
if 'indico_push_notifications' in active:
    print('🎉🎉🎉 УСПЕХ! Плагин активен в Indico 🎉🎉🎉')
    print('   Перейдите: Админка → Плагины → Push Notifications')
else:
    print('😞 Плагин все еще не активен')
    print('   Выполните полную переустановку (см. выше)')
"
```

---
**Время выполнения:** 5-10 минут  
**Следующий шаг:** Настройка Telegram бота и Web Push  
**Конфигурация:** `/opt/indico/etc/indico.conf`  
**Логи:** `/var/log/indico/indico.log`

*Выполните проверки СЕЙЧАС и сообщите результаты*