from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import settings
from app.i18n import t


def main_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Единственная кнопка бота — дальше всё (каталог eSIM, лаунж, туры, чаты,
    "Мои eSIM") происходит внутри Mini App, у которой свой собственный таб-бар.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=t("open_shop_button", lang), web_app=WebAppInfo(url=settings.MINIAPP_URL))
    builder.adjust(1)
    return builder.as_markup()
