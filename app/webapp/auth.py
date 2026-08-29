"""
Проверка подлинности initData, которую Telegram Mini App передаёт на бэкенд.

Алгоритм официальный (не меняется годами, в отличие от esimaccess — это
задокументированный публичный Bot API Telegram):
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

Коротко: секретный ключ = HMAC-SHA256("WebAppData", bot_token), затем
проверяемый хэш = HMAC-SHA256(secret_key, data_check_string) должен совпасть
с полем hash, которое прислал клиент.

Используется ДВУМЯ разными Mini App с разными ботами: обычным клиентским
магазином (CLIENT_BOT_TOKEN, get_current_user) и приватным инбоксом чатов для
администратора (SUPPORT_BOT_TOKEN, get_admin_user) — поэтому bot_token везде
передаётся явным параметром, а не берётся из настроек внутри функции.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException
from sqlalchemy import select

from app.config import settings
from app.database.db import get_session
from app.database.models import User

# Сколько секунд считаем initData ещё свежим (защита от повторного использования старых данных)
MAX_INIT_DATA_AGE_SECONDS = 24 * 60 * 60


def validate_init_data(init_data: str, bot_token: str) -> dict | None:
    """
    Возвращает распарсенные поля initData (включая user), если подпись верна
    и данные не протухли. Иначе — None. bot_token — токен ТОГО бота, из Mini App
    которого пришёл этот initData (клиентский или бот поддержки).
    """
    if not init_data:
        return None

    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    auth_date = int(parsed.get("auth_date", 0))
    if time.time() - auth_date > MAX_INIT_DATA_AGE_SECONDS:
        return None

    return parsed


def extract_telegram_user(parsed_init_data: dict) -> dict | None:
    """Достаёт объект user (id, username, first_name, ...) из уже провалидированных данных."""
    raw_user = parsed_init_data.get("user")
    if not raw_user:
        return None
    try:
        return json.loads(raw_user)
    except json.JSONDecodeError:
        return None


async def get_current_user(x_telegram_init_data: str = Header(default="")) -> User:
    """
    Зависимость для КЛИЕНТСКОГО Mini App (магазин). Проверяет initData токеном
    клиентского бота, находит или создаёт пользователя.
    """
    parsed = validate_init_data(x_telegram_init_data, settings.CLIENT_BOT_TOKEN)
    if parsed is None:
        raise HTTPException(status_code=401, detail="Недействительные данные Telegram")

    tg_user = extract_telegram_user(parsed)
    if tg_user is None or "id" not in tg_user:
        raise HTTPException(status_code=401, detail="Не удалось определить пользователя")

    async with get_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_user["id"]))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=tg_user["id"],
                username=tg_user.get("username"),
                full_name=" ".join(filter(None, [tg_user.get("first_name"), tg_user.get("last_name")])) or None,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


async def get_admin_user(x_telegram_init_data: str = Header(default="")) -> dict:
    """
    Зависимость для АДМИНСКОГО Mini App (инбокс чатов, открывается из бота
    поддержки). Проверяет initData токеном бота поддержки, и — в отличие от
    get_current_user — дополнительно требует, чтобы telegram_id совпадал с
    твоим SUPPORT_CHAT_ID: этот Mini App не для клиентов, а только для тебя,
    даже если кто-то посторонний каким-то образом получит на него ссылку.
    """
    parsed = validate_init_data(x_telegram_init_data, settings.SUPPORT_BOT_TOKEN)
    if parsed is None:
        raise HTTPException(status_code=401, detail="Недействительные данные Telegram")

    tg_user = extract_telegram_user(parsed)
    if tg_user is None or "id" not in tg_user:
        raise HTTPException(status_code=401, detail="Не удалось определить пользователя")

    if tg_user["id"] != settings.SUPPORT_CHAT_ID:
        raise HTTPException(status_code=403, detail="Доступ только для администратора")

    return tg_user
