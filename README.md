# Airy v1 — production-ready Telegram userbot framework

Модульный, асинхронный userbot на Telethon с горячей перезагрузкой, диагностикой и готовностью к деплою на бесплатных хостингах.

## Особенности

- **Модульная архитектура** — плагины в `modules/`
- **Горячая перезагрузка** — `.reload module` без остановки
- **EventBus** — слабое связывание команд и watcher-ов
- **AsyncKVStorage** — атомарное JSON-хранилище
- **Healthcheck** — HTTP `/health` для Railway/Render
- **Graceful shutdown** — безопасная остановка с таймаутами
- **Diagnostics** — кольцевой буфер ошибок в storage
- **Reconnect** — авто-переподключение с backoff
- **Termux / VPS / free hosting** — переносимость без изменений

---

## Требования

- Python 3.8+
- Telegram `api_id` и `api_hash` (получить на [my.telegram.org](https://my.telegram.org/apps))
- `SESSION_STRING` — обязательно для headless-деплоя

---

## Получение SESSION_STRING (обязательно для headless-деплоя)

**Без этой строки бот не сможет автоматически войти в аккаунт на Railway/Render/VPS.**  
Выполните на локальной машине (где есть доступ к терминалу Telegram):

```bash
pip install telethon
python -c "
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(input('API_ID: '))
API_HASH = input('API_HASH: ')

async def main():
    async with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        await client.start()
        print('SESSION_STRING:', client.session.save())

asyncio.run(main())
"
