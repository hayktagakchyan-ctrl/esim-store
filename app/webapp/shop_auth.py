"""
Авторизация для сайта (app/webapp/shop.py) — email + пароль, сессия в cookie
(Starlette SessionMiddleware, подписанная тем же принципом, что и в админке).

Хеширование пароля — намеренно на стандартной библиотеке (hashlib.pbkdf2_hmac),
без bcrypt/passlib: у тебя уже был болезненный опыт с пакетами, которым для
установки на Windows нужен компилятор (asyncpg) — pbkdf2_hmac того же уровня
надёжности (рекомендован OWASP), но не требует вообще ничего, кроме Python.
"""
from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import Request
from sqlalchemy import select

from app.database.db import get_session
from app.database.models import WebsiteAccount

_PBKDF2_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split("$", 1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return hmac.compare_digest(derived.hex(), hash_hex)


async def get_current_account(request: Request) -> WebsiteAccount | None:
    """None означает "гость, не вошёл в аккаунт" — это нормальное, поддерживаемое состояние."""
    account_id = request.session.get("account_id")
    if not account_id:
        return None
    async with get_session() as session:
        return await session.get(WebsiteAccount, account_id)
