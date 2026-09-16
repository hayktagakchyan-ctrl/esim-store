"""
Ограничение частоты попыток (вход, регистрация, сброс пароля и т.п.) —
хранится в базе (RateLimitAttempt, см. database/models.py), а не в памяти
процесса, как было раньше. Разница на практике: раньше перезапуск сервиса
(обычное дело при каждом деплое) полностью сбрасывал счётчик неудачных
попыток — то есть защита от перебора паролей переставала работать ровно
в момент, когда деплоишь что-то ещё, и никак с этим не связанное. Плюс
если Railway когда-нибудь запустит больше одной копии сервиса (реплики),
у каждой была бы своя память — общего счётчика не было бы вообще. Теперь
и то, и другое не проблема — все читают одну и ту же таблицу.

Цель по-прежнему не "идеальная защита от распределённого брутфорса", а
просто не дать перебирать пароли в лоб простым скриптом по логину/паролю.
"""
import random
from datetime import datetime, timedelta

from sqlalchemy import select, func, delete

from app.database.db import get_session
from app.database.models import RateLimitAttempt

MAX_ATTEMPTS = 5
COOLDOWN_SECONDS = 5 * 60  # 5 минут


async def register_failure(key: str) -> None:
    async with get_session() as session:
        session.add(RateLimitAttempt(key=key))
        await session.commit()
        # Попутная уборка совсем старых записей — не архив, а короткий буфер.
        # Не на каждый вызов (незачем лишний раз дёргать базу) — примерно раз
        # на 20 попыток этого достаточно, чтобы таблица не росла бесконечно.
        if random.random() < 0.05:
            cutoff = datetime.utcnow() - timedelta(hours=1)
            await session.execute(delete(RateLimitAttempt).where(RateLimitAttempt.created_at < cutoff))
            await session.commit()


async def is_blocked(key: str) -> bool:
    cutoff = datetime.utcnow() - timedelta(seconds=COOLDOWN_SECONDS)
    async with get_session() as session:
        count = (await session.execute(
            select(func.count()).select_from(RateLimitAttempt)
            .where(RateLimitAttempt.key == key, RateLimitAttempt.created_at >= cutoff)
        )).scalar_one()
    return count >= MAX_ATTEMPTS


async def reset(key: str) -> None:
    async with get_session() as session:
        await session.execute(delete(RateLimitAttempt).where(RateLimitAttempt.key == key))
        await session.commit()
