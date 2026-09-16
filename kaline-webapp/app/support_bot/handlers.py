"""
Бот поддержки теперь не занимается роутингом сообщений (это делает Mini App —
см. app/webapp/admin_chat.py) — его единственная задача: пускать в приватный
чат-инбокс только тебя, и присылать уведомление, когда придёт новое сообщение
от клиента (это уведомление отправляет сам webapp-процесс через этот же токен,
см. app/webapp/admin_chat.py — notify_bot).
"""
from aiogram import Router, F
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import settings
from app.i18n import t

router = Router(name="support_admin")


def _admin_chat_kb():
    builder = InlineKeyboardBuilder()
    chat_url = settings.PUBLIC_BASE_URL.rstrip("/") + "/support-chat/"
    builder.button(text=t("open_chats_button", "ru"), web_app=WebAppInfo(url=chat_url))
    builder.adjust(1)
    return builder.as_markup()


@router.message(F.chat.id != settings.SUPPORT_CHAT_ID)
async def ignore_strangers(message: Message) -> None:
    """Приватный бот. Кто угодно посторонний — полный игнор, ничего не отвечаем."""
    return


@router.message(F.chat.id == settings.SUPPORT_CHAT_ID)
async def open_inbox(message: Message) -> None:
    await message.answer("Чаты с клиентами:", reply_markup=_admin_chat_kb())
