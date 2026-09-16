"""
Wallet Pay — платежи через встроенный кошелёк Telegram (@wallet, на блокчейне TON).
Один этот провайдер закрывает сразу два пункта из требований: "крипта" и
"Telegram-кошелёк" — платить можно в TON/USDT/BTC прямо из Telegram, отдельно
крипто-провайдер не нужен.

Подтверждено официальной документацией https://docs.wallet.tg/pay/ и совпадает
в нескольких независимых клиентах (python/JS/TS/Ruby):
- base_url = https://pay.wallet.tg
- Авторизация — заголовок "Wpay-Store-Api-Key: <токен>" (токен выдаётся на pay.wallet.tg)
- POST /wpay/store-api/v1/order — создать заказ
- GET  /wpay/store-api/v1/order/preview?id=<id> — проверить статус заказа

НЕ ПОДТВЕРЖДЕНО: точный формат и подпись вебхука "completedOrder"
(https://docs.wallet.tg/pay/#operation/completedOrder) — независимые источники
подтверждают, что вебхук подписан, но не точный алгоритм. Поэтому здесь используется
более надёжный путь — polling: Mini App периодически спрашивает у нас статус заказа,
мы в этот момент дёргаем get_order_preview(). Вебхук можно добавить позже как
ускоряющую (но не единственную) проверку, сверив его по офиц. документации.
"""
from __future__ import annotations

import httpx

from app.config import settings


class WalletPayError(Exception):
    def __init__(self, message: str, status: str | None = None):
        self.status = status
        super().__init__(message)


class WalletPayClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url="https://pay.wallet.tg",
            headers={
                "Wpay-Store-Api-Key": settings.WALLET_PAY_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def create_order(
        self,
        *,
        amount: str,
        currency_code: str,
        external_id: str,
        description: str,
        customer_telegram_user_id: int,
        timeout_seconds: int = 3600,
    ) -> dict:
        """
        currency_code: валюта ЦЕНЫ, например "USD" — Wallet Pay сам покажет покупателю
        эквивалент в TON/USDT/BTC на выбор. amount — строка, напр. "9.00".
        external_id — наш Payment.external_payment_id, для сопоставления при опросе статуса.
        """
        payload = {
            "amount": {"currencyCode": currency_code, "amount": amount},
            "description": description,
            "externalId": external_id,
            "timeoutSeconds": timeout_seconds,
            "customerTelegramUserId": customer_telegram_user_id,
            "returnUrl": "https://t.me/wallet",
            "failReturnUrl": "https://t.me/wallet",
        }
        try:
            response = await self._client.post("/wpay/store-api/v1/order", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Частая причина 400 здесь — пустой/неверный WALLET_PAY_API_KEY в .env.
            raise WalletPayError(f"HTTP {exc.response.status_code}: {exc.response.text}")
        except httpx.RequestError as exc:
            raise WalletPayError(f"Сетевая ошибка: {exc}")

        data = response.json()
        if data.get("status") != "SUCCESS":
            raise WalletPayError(data.get("message", "Unknown Wallet Pay error"), data.get("status"))
        return data["data"]

    async def get_order_preview(self, provider_order_id: str) -> dict:
        """Статус заказа: data.status ∈ {ACTIVE, PAID, EXPIRED, CANCELLED, ...}."""
        try:
            response = await self._client.get(
                "/wpay/store-api/v1/order/preview", params={"id": provider_order_id}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise WalletPayError(f"HTTP {exc.response.status_code}: {exc.response.text}")
        except httpx.RequestError as exc:
            raise WalletPayError(f"Сетевая ошибка: {exc}")

        data = response.json()
        if data.get("status") != "SUCCESS":
            raise WalletPayError(data.get("message", "Unknown Wallet Pay error"), data.get("status"))
        return data["data"]


wallet_pay_client = WalletPayClient()
