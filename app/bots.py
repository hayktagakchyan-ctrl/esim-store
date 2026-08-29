"""
Оба бота создаются здесь один раз и импортируются оттуда, где нужны.
Работая в одном процессе, хендлеры клиентского бота могут напрямую вызвать
support_bot.send_message(...) и наоборот — без HTTP-мостов между процессами.
"""
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings

client_bot = Bot(
    token=settings.CLIENT_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

support_bot = Bot(
    token=settings.SUPPORT_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
