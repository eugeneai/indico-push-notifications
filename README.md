# Indico Push Notifications Plugin

Плагин для отправки push-уведомлений и Telegram-уведомлений в Indico.

## Возможности

- **Telegram уведомления**: Привязка Telegram аккаунта, отправка уведомлений о событиях
- **Web Push уведомления**: Браузерные push-уведомления через Service Worker
- **Интеграция с системой уведомлений Indico**: Автоматическая отправка копий email-уведомлений
- **Гибкие настройки пользователя**: Включение/выключение типов уведомлений, настройка предпочтений

## Архитектура

### 1. Хранение данных

#### UserSettingsProxy (рекомендуемый подход)
```python
push_user_settings = SettingsProxy('push_notifications', {
    'telegram_chat_id': None,        # ID чата в Telegram (123456789)
    'telegram_username': None,       # @username для отображения
    'telegram_enabled': False,       # Включить Telegram уведомления
    'telegram_linking_token': None,  # Временный токен для привязки
    'telegram_linking_expires': None,# Время жизни токена
    
    'push_enabled': False,           # Включить Web Push уведомления
    'push_subscriptions': [],        # Список подписок Web Push
    
    'notification_preferences': {    # Какие события уведомлять
        'event_creation': True,
        'registration': True,
        'abstract_submission': True,
        'reminders': True
    }
})
```

### 2. Процесс привязки Telegram

```
1. Пользователь в Indico:
   - Заходит в Настройки → Уведомления → Telegram
   - Нажимает "Привязать Telegram аккаунт"
   - Получает уникальную ссылку: t.me/IndicoBot?start=ABC123

2. Пользователь в Telegram:
   - Переходит по ссылке (открывает бота)
   - Нажимает "Start"
   - Бот отправляет запрос в Indico API
   - Indico подтверждает привязку

3. Результат:
   - Telegram Chat ID сохраняется в настройках пользователя
   - Уведомления автоматически включаются
   - Пользователь видит статус "✅ Привязано"
```

### 3. Web Push уведомления

```
1. Пользователь в браузере:
   - Разрешает получение уведомлений
   - Браузер генерирует подписку (endpoint + keys)

2. Сохранение подписки:
   - Отправляется в Indico через API
   - Сохраняется в настройках пользователя
   - Service Worker регистрируется

3. Отправка уведомлений:
   - Indico отправляет уведомление через Web Push API
   - Браузер показывает native notification
   - Service Worker обрабатывает клики
```

### 4. Интеграция с системой Indico

```python
# Перехват email-уведомлений через сигналы
@signals.core.before_notification_send.connect
def intercept_notifications(sender, email, **kwargs):
    # Определяем получателей
    # Проверяем настройки каждого пользователя
    # Отправляем в Telegram / Web Push
```

## Структура проекта

```
indico-push-notifications/
├── __init__.py              # Основной класс плагина
├── blueprint.py             # Маршруты Flask
├── controllers.py           # Контроллеры
├── forms.py                 # Формы для настроек
├── models.py                # Модели базы данных (если нужны)
├── notifications.py         # Логика отправки уведомлений
├── telegram_bot.py          # Логика Telegram бота
├── webpush.py              # Логика Web Push
├── templates/               # Шаблоны
│   ├── user_preferences.html
│   └── push_script.js
├── static/                  # Статические файлы
│   ├── service-worker.js
│   └── push-manager.js
├── alembic/                 # Миграции (если нужны)
│   └── versions/
├── tests/                   # Тесты
├── setup.py                 # Установка
├── requirements.txt         # Зависимости
└── README.md               # Этот файл
```

## Зависимости

- `python-telegram-bot` или `requests` для Telegram API
- `pywebpush` для Web Push API
- `cryptography` для шифрования Web Push

## Конфигурация

### Indico конфигурация
```python
# indico.conf
```

### Конфигурация плагина
```python
# В админке Indico
{
    "telegram_bot_username": "@IndicoBot",
    "webpush_enabled": true,
    "default_notification_preferences": {
        "event_creation": true,
        "registration": true
    }
}
```

## Установка

1. Установить плагин:
```bash
pip install indico-push-notifications
```

2. Добавить в `indico.conf`:
```python
ENABLED_PLUGINS = ['indico_push_notifications']
```

3. Настроить в админке Indico:
   - Telegram Bot Token
   - VAPID ключи для Web Push
   - Настройки по умолчанию

4. Запустить миграции (если нужны):
```bash
indico db upgrade --plugin indico_push_notifications
```

## Использование

### Для пользователей:
1. Зайти в "Мой профиль" → "Настройки" → "Уведомления"
2. Привязать Telegram аккаунт
3. Разрешить push-уведомления в браузере
4. Настроить предпочтения

### Для администраторов:
1. Создать бота через @BotFather
2. Получить VAPID ключи для Web Push
3. Настроить плагин в админке Indico
4. Мониторить статистику отправки

## Безопасность

- Telegram: Токены привязки с ограниченным временем жизни
- Web Push: Шифрование end-to-end через VAPID
- API: Аутентификация через Indico сессии и API ключи
- Данные: Хранение только необходимой информации

## Мониторинг

- Логирование всех отправленных уведомлений
- Статистика по каналам (Telegram/Web Push)
- Отслеживание ошибок отправки
- Админ-панель с метриками

## Разработка

### Локальная установка:
```bash
git clone <repository>
cd indico-push-notifications
pip install -e .
```

### Запуск тестов:
```bash
pytest tests/
```

### Создание миграций:
```bash
indico db migrate --plugin indico_push_notifications -m "Описание изменений"
```

## Лицензия

MIT License

## Поддержка

- Документация: [ссылка на docs]
- Issues: [ссылка на issue tracker]
- Контакты: [email/chat]