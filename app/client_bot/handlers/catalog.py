from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy import select

from app.client_bot.keyboards import main_menu_kb
from app.database.db import get_session
from app.database.models import User
from app.i18n import t, detect_lang

router = Router(name="catalog")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    lang = detect_lang(message.from_user.language_code)

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
            )
            session.add(user)
            await session.commit()

    await message.answer(t("welcome", lang), reply_markup=main_menu_kb(lang))


@router.message()
async def redirect_to_shop(message: Message) -> None:
    """
    Всё покупается и обсуждается внутри Mini App (каталог, чаты) — бот сам
    больше никакие сообщения не обрабатывает. Любой текст (кроме /start выше)
    просто мягко возвращает к кнопке магазина, а не проваливается в тишину и
    не запускает никакой старый флоу.
    """
    lang = detect_lang(message.from_user.language_code)
    await message.answer(t("use_shop_button_hint", lang), reply_markup=main_menu_kb(lang))
