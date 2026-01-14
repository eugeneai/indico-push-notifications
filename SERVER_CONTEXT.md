# Indico Push Notifications Plugin - Server Context & Troubleshooting Guide

## Серверная среда Indico

### Основные пути
```
/opt/indico/                    # Корневая директория Indico
├── etc/indico.conf            # Основной конфигурационный файл
├── .venv-3/                   # Виртуальное окружение Python 3
├── modules/                   # Директория для плагинов
│   └── indico-push-notifications/  # Наш плагин
└── indico/                    # Исходный код Indico
```

### Пользователи и права
- **Пользователь**: `indico`
- **Группа**: `www-data`
- **База данных**: PostgreSQL, пользователь `indico`

## Установка и настройка плагина

### 1. Копирование файлов на сервер

#### Способ A: Git синхронизация (рекомендуется)
```bash
# На локальной машине
git add .
git commit -m "Описание изменений"
git push origin master

# На сервере
cd /opt/indico/modules/indico-push-notifications
git pull origin master
```

#### Способ B: Ручное копирование через SCP
```bash
# Копирование с локальной машины на сервер
scp -r indico_push_notifications/ indico@nla2020:/opt/indico/modules/indico-push-notifications/
scp setup.py requirements.txt alembic.ini indico@nla2020:/opt/indico/modules/indico-push-notifications/

# Копирование alembic директории
scp -r alembic/ indico@nla2020:/opt/indico/modules/indico-push-notifications/
```

#### Способ C: Использование скрипта синхронизации
```bash
# На локальной машине
./sync_missing_files.sh sync
```

### 2. Установка плагина
```bash
# На сервере
cd /opt/indico/modules/indico-push-notifications

# Активация виртуального окружения Indico
source /opt/indico/.venv-3/bin/activate

# Установка плагина
pip install -e . --break-system-packages
```

### 3. Миграции базы данных
```bash
# На сервере
cd /opt/indico/modules/indico-push-notifications

# Вариант 1: Использовать команду Indico (предпочтительно)
indico db upgrade --plugin indico_push_notifications

# Вариант 2: Использовать alembic напрямую
export INDICO_DATABASE_URL="postgresql:///indico"
alembic -c alembic.ini upgrade head
```

### 4. Конфигурация Indico
```bash
# Редактирование конфигурационного файла
sudo nano /opt/indico/etc/indico.conf
```

Добавить или убедиться что есть:
```python
ENABLED_PLUGINS = ['indico_push_notifications']

# Telegram Bot Configuration
```

### 5. Перезапуск сервисов
```bash
# Перезапуск Indico
sudo systemctl restart indico
sudo systemctl restart indico-celery

# Проверка статуса
sudo systemctl status indico
sudo systemctl status indico-celery
```

## Диагностика проблем

### Плагин не отображается в админке

#### 1. Проверка базовых условий
```bash
# На сервере
cd /opt/indico/modules/indico-push-notifications

# Проверка установки плагина
pip list | grep indico-push-notifications

# Проверка импорта
python -c "import indico_push_notifications; print('✅ Plugin imports successfully')"

# Проверка класса плагина
python -c "from indico_push_notifications import IndicoPushNotificationsPlugin; p = IndicoPushNotificationsPlugin(); print(f'✅ Plugin: {p.name}')"
```

#### 2. Проверка конфигурации Indico
```bash
# Проверка наличия плагина в конфигурации
grep -i "enabled_plugins\|indico_push" /opt/indico/etc/indico.conf

# Проверка синтаксиса конфигурационного файла
python -m py_compile /opt/indico/etc/indico.conf 2>/dev/null && echo "✅ Config syntax OK" || echo "❌ Config syntax error"
```

#### 3. Проверка логов
```bash
# Просмотр логов Indico в реальном времени
tail -f /var/log/indico/indico.log | grep -i "plugin\|push\|indico_push"

# Просмотр ошибок
tail -f /var/log/indico/indico-error.log

# Просмотр через journalctl
sudo journalctl -u indico --since "10 minutes ago" | grep -i plugin
```

#### 4. Проверка загрузки плагина Indico
```bash
# Проверка списка плагинов через Python
python -c "
from indico.core.plugins import plugin_engine
plugins = list(plugin_engine.get_active_plugins().keys())
print('Active plugins:', plugins)
if 'indico_push_notifications' in plugins:
    print('✅ Our plugin is loaded')
else:
    print('❌ Our plugin is NOT loaded')
"
```

#### 5. Проверка точек входа (entry points)
```bash
# Проверка entry points плагина
python -c "
import pkg_resources
for entry_point in pkg_resources.iter_entry_points('indico.plugins'):
    print(f'{entry_point.name}: {entry_point.module_name}')
"

# Проверка нашего entry point
python -c "
import pkg_resources
try:
    ep = pkg_resources.get_entry_info('indico-push-notifications', 'indico.plugins', 'indico_push_notifications')
    print(f'✅ Entry point found: {ep.module_name}')
except:
    print('❌ Entry point not found')
"
```

#### 6. Проверка структуры плагина
```bash
# Проверка необходимых файлов
cd /opt/indico/modules/indico-push-notifications
ls -la

# Критичные файлы которые должны быть:
# - setup.py
# - indico_push_notifications/__init__.py
# - indico_push_notifications/__init__.py с классом IndicoPushNotificationsPlugin
# - pyproject.toml (может вызывать проблемы)

# Проверка класса плагина в __init__.py
grep -n "class IndicoPushNotificationsPlugin" indico_push_notifications/__init__.py
```

### Частые проблемы и решения

#### Проблема 1: Плагин не загружается
**Симптомы**: Плагин не появляется в списке плагинов админки
**Решение**:
```bash
# 1. Удалить pyproject.toml если он вызывает проблемы
cd /opt/indico/modules/indico-push-notifications
mv pyproject.toml pyproject.toml.backup

# 2. Переустановить плагин
pip uninstall indico-push-notifications -y
pip install -e . --break-system-packages

# 3. Проверить entry points
python -c "import pkg_resources; print([ep.name for ep in pkg_resources.iter_entry_points('indico.plugins')])"
```

#### Проблема 2: Ошибки импорта
**Симптомы**: Ошибки в логах при загрузке плагина
**Решение**:
```bash
# Проверить зависимости
pip install python-telegram-bot pywebpush cryptography

# Проверить импорт вручную
cd /opt/indico/modules/indico-push-notifications
python -c "import sys; sys.path.insert(0, '.'); import indico_push_notifications"
```

#### Проблема 3: Конфликт версий Python
**Симптомы**: Разные версии Python в системе
**Решение**:
```bash
# Проверить версии Python
pyenv versions
python --version
/opt/indico/.venv-3/bin/python --version

# Убедиться что используем правильный Python
which python
which pip
```

### Скрипты для диагностики

#### Скрипт проверки плагина
```bash
#!/bin/bash
# check_plugin.sh

echo "=== Indico Push Notifications Plugin Diagnostic ==="
echo

echo "1. Checking installation..."
pip list | grep indico-push-notifications || echo "❌ Plugin not installed"

echo
echo "2. Checking imports..."
python -c "
try:
    import indico_push_notifications
    print('✅ Plugin imports OK')
    
    from indico_push_notifications import IndicoPushNotificationsPlugin
    plugin = IndicoPushNotificationsPlugin()
    print(f'✅ Plugin class: {plugin.name}')
except Exception as e:
    print(f'❌ Import error: {e}')
"

echo
echo "3. Checking configuration..."
grep -i "enabled_plugins\|push_notifications" /opt/indico/etc/indico.conf || echo "❌ Not in config"

echo
echo "4. Checking logs..."
tail -20 /var/log/indico/indico.log | grep -i "plugin\|push" || echo "No recent plugin logs"

echo
echo "=== Diagnostic complete ==="
```

#### Скрипт переустановки
```bash
#!/bin/bash
# reinstall_plugin.sh

echo "Reinstalling Indico Push Notifications Plugin..."
cd /opt/indico/modules/indico-push-notifications

# Backup problematic files
[ -f pyproject.toml ] && mv pyproject.toml pyproject.toml.backup

# Uninstall
pip uninstall indico-push-notifications -y

# Reinstall
pip install -e . --break-system-packages

# Restore backup
[ -f pyproject.toml.backup ] && mv pyproject.toml.backup pyproject.toml

echo "✅ Reinstallation complete"
echo "Restart Indico: sudo systemctl restart indico indico-celery"
```

## Быстрые команды для следующей сессии

### При подключении к серверу:
```bash
# 1. Подключиться к серверу
ssh indico@nla2020

# 2. Перейти в директорию плагина
cd /opt/indico/modules/indico-push-notifications

# 3. Активировать окружение
source /opt/indico/.venv-3/bin/activate

# 4. Проверить статус
./check_plugin.sh
```

### Если плагин не виден:
```bash
# 1. Проверить логи
tail -f /var/log/indico/indico.log | grep -i plugin

# 2. Переустановить
./reinstall_plugin.sh

# 3. Перезапустить Indico
sudo systemctl restart indico indico-celery

# 4. Проверить в браузере
#    Залогиниться как админ → Админка → Плагины
```

### Для обновления кода:
```bash
# На локальной машине
git add .
git commit -m "Описание изменений"
git push origin master

# На сервере
cd /opt/indico/modules/indico-push-notifications
git pull origin master
pip install -e . --break-system-packages
sudo systemctl restart indico indico-celery
```

## Контакты и ссылки

- **Сервер**: nla2020 (192.168.191.169)
- **Пользователь**: indico
- **Путь к плагину**: /opt/indico/modules/indico-push-notifications
- **Конфигурация**: /opt/indico/etc/indico.conf
- **Логи**: /var/log/indico/

## Текущий статус (на 13.01.2026)

✅ **Сделано:**
- Плагин установлен через pip
- Миграции базы данных выполнены
- Telegram бот создан (@conference_icc_ru_bot)
- VAPID ключи сгенерированы
- Конфигурация добавлена в indico.conf
- Indico перезапущен

❌ **Проблема:**
- Плагин не отображается в админке Indico

🔧 **Следующие шаги:**
1. Проверить загрузку плагина через диагностический скрипт
2. Проверить entry points
3. Проверить логи на ошибки импорта
4. При необходимости переустановить плагин