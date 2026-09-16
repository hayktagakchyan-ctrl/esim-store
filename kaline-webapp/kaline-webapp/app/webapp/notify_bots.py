"""
Лёгкие Bot-инстансы только для отправки сообщений из процесса app/webapp
(вебхуки esimaccess, уведомления о новых сообщениях в чатах, ответы админа
клиенту). Этот процесс не поллит апдейты, поэтому безопасно работает
одновременно с app/main.py, где Bot с теми же токенами уже используется для
polling — конфликта нет, это независимые HTTP-вызовы к Bot API.

Один общий модуль, а не по экземпляру в каждом файле — чтобы не плодить лишние
httpx-сессии на один и тот же токен.
"""
from aiogram import Bot

from app.config import settings

client_notify_bot = Bot(token=settings.CLIENT_BOT_TOKEN)
support_notify_bot = Bot(token=settings.SUPPORT_BOT_TOKEN)
