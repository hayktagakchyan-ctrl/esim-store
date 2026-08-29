"""
Точка входа. Поднимает оба бота (клиентский + поддержка) одним asyncio-процессом,
поэтому они могут напрямую слать сообщения друг через друга (см. app/bots.py).

Клиентский бот теперь предельно простой: единственная кнопка "Открыть магазин"
(web_app). ВСЁ остальное — каталог eSIM, лаунж, туры, "Мои eSIM", чаты с
клиентами — живёт в Mini App (app/webapp) на обеих сторонах: у клиента и у тебя
(отдельный "инбокс"-Mini App, открывается из бота поддержки).

Запуск: python -m app.main   (из корня проекта esim_bot_project/)

Админ-панель (FastAPI) — отдельный процесс, запускается независимо:
uvicorn app.admin_panel.app:app --port 8000
Mini App + инбокс чатов (FastAPI) — тоже отдельный процесс:
uvicorn app.webapp.app:app --port 8001
"""
import asyncio
import logging

from aiogram import Dispatcher

from app.bots import client_bot, support_bot
from app.database.db import init_db

from app.client_bot.handlers import catalog
from app.support_bot import handlers as support_handlers

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    await init_db()

    client_dp = Dispatcher()
    client_dp.include_router(catalog.router)

    support_dp = Dispatcher()
    support_dp.include_router(support_handlers.router)

    await asyncio.gather(
        client_dp.start_polling(client_bot),
        support_dp.start_polling(support_bot),
    )


if __name__ == "__main__":
    asyncio.run(main())
