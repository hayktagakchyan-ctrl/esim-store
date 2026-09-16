"""
Stripe — оплата картой, международно (в отличие от Idram, который работает
только с армянскими картами/счетами Idram, и в отличие от Wallet Pay/OxaPay,
которые про крипту). Использует Stripe Checkout — готовую хостед-страницу
оплаты, как и у остальных провайдеров в этом проекте: мы создаём сессию и
редиректим покупателя на неё, сама оплата проходит на стороне Stripe.

Подтверждено официальной документацией:
- https://docs.stripe.com/checkout/quickstart — создание Checkout Session
- https://docs.stripe.com/webhooks — проверка подписи вебхука

Требует пакет "stripe" (см. requirements.txt) и три настройки в .env:
STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY (пока не используется на бэкенде,
но понадобится, если добавите Stripe Elements вместо Checkout), STRIPE_WEBHOOK_SECRET.
"""
from __future__ import annotations

import stripe

from app.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripePaymentError(Exception):
    pass


async def create_checkout_session(
    *,
    amount: float,
    currency: str,
    description: str,
    success_url: str,
    cancel_url: str,
    client_reference_id: str,
    email: str | None = None,
) -> str:
    """
    Возвращает URL хостед-страницы Stripe Checkout, куда редиректить покупателя.
    client_reference_id — это то же самое, что external_payment_id у остальных
    провайдеров (наш UUID) — по нему сопоставляем вебхук с заказом/пополнением.
    """
    try:
        session = await stripe.checkout.Session.create_async(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": currency.lower(),
                    "product_data": {"name": description},
                    "unit_amount": round(amount * 100),  # Stripe считает в минимальных единицах (центах)
                },
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=client_reference_id,
            customer_email=email or None,
        )
    except stripe.StripeError as e:
        raise StripePaymentError(str(e)) from e

    return session.url


def verify_webhook(payload: bytes, sig_header: str) -> stripe.Event:
    """Проверяет подпись и парсит тело вебхука. Кидает stripe.SignatureVerificationError, если подпись не совпадает."""
    return stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
