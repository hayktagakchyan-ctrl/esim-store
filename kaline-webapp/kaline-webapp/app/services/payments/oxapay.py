"""
OxaPay — приём крипты с ЛЮБОГО адреса или биржи (в т.ч. прямым выводом с Bybit),
без необходимости заводить Telegram Wallet. Хорошо дополняет Wallet Pay: тем, у
кого крипта уже в Telegram — Wallet Pay удобнее (один клик), тем, у кого она на
бирже — OxaPay удобнее (обычный адрес для перевода, ждать создания/пополнения
Telegram-кошелька не нужно).

Подтверждено официальной документацией https://docs.oxapay.com/ (актуальная,
НЕ legacy, версия API):
- base_url = https://api.oxapay.com/v1
- Авторизация — заголовок "merchant_api_key: <ключ>"
- POST /payment/invoice — создать счёт, в ответе data.track_id и data.payment_url
- Вебхук на callback_url: сначала статус "Paying" (тx в сети, ещё не подтверждена),
  затем "Paid" — только "Paid" считается окончательным подтверждением.
- Подпись вебхука — заголовок "hmac" = HMAC-SHA512(raw_body, key=MERCHANT_API_KEY).
  Формула и код проверки приведены прямо в официальной документации — совпадает
  с тем, что реализовано ниже.
"""
from __future__ import annotations

import hashlib
import hmac

import httpx

from app.config import settings


class OxaPayError(Exception):
    def __init__(self, message: str, error: dict | None = None):
        self.error = error
        super().__init__(message)


class OxaPayClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url="https://api.oxapay.com/v1",
            headers={
                "merchant_api_key": settings.OXAPAY_MERCHANT_API_KEY,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def create_invoice(
        self,
        *,
        amount: float,
        currency: str,
        order_id: str,
        description: str,
        callback_url: str,
        return_url: str,
        email: str | None = None,
        lifetime_minutes: int = 60,
    ) -> dict:
        """
        currency здесь — валюта ЦЕНЫ (напр. "USD"), не обязательно крипта: OxaPay сам
        покажет плательщику эквивалент в разных монетах на выбор. Возвращает
        {"track_id": ..., "payment_url": ..., "expired_at": ..., "date": ...}.
        """
        payload = {
            "amount": amount,
            "currency": currency,
            "lifetime": lifetime_minutes,
            "order_id": order_id,
            "description": description,
            "callback_url": callback_url,
            "return_url": return_url,
        }
        if email:
            payload["email"] = email

        response = await self._client.post("/payment/invoice", json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Частая причина 400/401 здесь — пустой/неверный OXAPAY_MERCHANT_API_KEY в .env.
            raise OxaPayError(f"HTTP {exc.response.status_code}: {exc.response.text}")
        except httpx.RequestError as exc:
            raise OxaPayError(f"Сетевая ошибка: {exc}")

        data = response.json()
        if data.get("status") != 200:
            raise OxaPayError(data.get("message", "Unknown OxaPay error"), data.get("error"))
        return data["data"]


def verify_webhook_signature(raw_body: bytes, hmac_header: str) -> bool:
    """
    Проверка подписи колбэка (см. https://docs.oxapay.com/webhook — формула и пример
    кода на Python там приведены дословно так же, как реализовано ниже).
    """
    if not hmac_header:
        return False
    computed = hmac.new(
        settings.OXAPAY_MERCHANT_API_KEY.encode(), raw_body, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(computed, hmac_header)


oxapay_client = OxaPayClient()
