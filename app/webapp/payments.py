"""
Оплата заказа — три провайдера на выбор клиента:
- Idram (см. app/services/payments/idram.py) — драмы, редирект на хостед-страницу,
  подтверждение через RESULT_URL (POST /webhooks/idram ниже).
- Wallet Pay (см. app/services/payments/wallet_pay.py) — крипта через Telegram-кошелёк,
  подтверждение через опрос статуса (см. GET /api/orders/{id}/payment-status).
- OxaPay (см. app/services/payments/oxapay.py) — крипта с ЛЮБОГО адреса/биржи
  (напр. вывод прямо с Bybit), Telegram-кошелёк не нужен. Подтверждение — через
  вебхук POST /webhooks/oxapay, с проверкой HMAC-подписи.

Как только Payment переходит в PAID, а Order — в PAID, сразу вызывается
_fulfill_order() ниже — она создаёт заказ у esimaccess (create_order уже
подтверждён документацией). Единственное, чего всё ещё не хватает для полного
цикла — список пакетов с ценами ("Query All Data Packages"), поэтому каталог
пока нужно наполнять вручную через админку (см. esimaccess_package_code у Package).
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.config import settings
from app.database.db import get_session
from app.database.models import (
    Order, OrderStatus, Payment, PaymentProvider, PaymentStatus, User, TopUp, WebsiteAccount,
    Notification, NotificationType,
)
from app.services.esimaccess import esimaccess_client
from app.services.payments import idram
from app.services.payments.wallet_pay import wallet_pay_client, WalletPayError
from app.services.payments.oxapay import oxapay_client, verify_webhook_signature, OxaPayError

# Отдельный логгер для Idram — там реальные деньги и придирчивая верификация
# (чек-сумма), поэтому важно видеть в логах Railway каждый шаг: что пришло,
# прошла ли проверка, что решили. При разборе спорного платежа это будет
# единственный след того, что реально произошло.
idram_logger = logging.getLogger("idram")
from app.webapp.auth import get_current_user

router = APIRouter()

PROVIDER_BY_METHOD = {
    "idram": PaymentProvider.IDRAM,
    "wallet_pay": PaymentProvider.WALLET_PAY,
    "oxapay": PaymentProvider.OXAPAY,
    "test": PaymentProvider.TEST,
}


@router.get("/api/test-payment-enabled")
async def test_payment_enabled():
    """
    Mini App спрашивает при открытии чекаута, какие способы оплаты показывать.
    Название эндпоинта осталось историческим (изначально был только про тестовую
    оплату) — теперь тут же и wallet_pay/oxapay, чтобы не плодить лишний запрос.
    """
    return {
        "enabled": settings.ENABLE_TEST_PAYMENT,  # тестовая оплата (старое имя поля)
        "wallet_pay": settings.ENABLE_WALLET_PAY,
        "oxapay": settings.ENABLE_OXAPAY,
        "bot_username": settings.CLIENT_BOT_USERNAME,
    }


async def _fulfill_order(session, order: Order) -> None:
    """
    Вызывается сразу после того, как Order переходит в PAID (из любого из трёх
    обработчиков платежей ниже) — создаёт заказ у esimaccess (теперь подтверждённый
    create_order, см. app/services/esimaccess.py). Дальше подхватит вебхук
    ORDER_STATUS (app/webapp/webhooks.py), который найдёт этот Order по
    our_transaction_id и сам получит ICCID/QR через query_esim.

    Ошибку esimaccess здесь намеренно не даём "уронить" обработчик платёжного
    вебхука целиком — деньги уже получены, ронять весь ответ провайдеру оплаты
    из-за проблемы на стороне esimaccess нельзя (иначе Idram/OxaPay решат, что
    мы не получили их уведомление, и будут слать повторно). Вместо этого — статус
    FAILED и причина в refund_reason, чтобы было видно в админке и можно было
    вручную разобраться/вернуть деньги.
    """
    if order.our_transaction_id is None:
        order.our_transaction_id = str(uuid.uuid4())[:50]

    await session.refresh(order, attribute_names=["package"])

    try:
        order_no = await esimaccess_client.create_order(
            transaction_id=order.our_transaction_id,
            package_code=order.package.esimaccess_package_code,
            count=1,
        )
        order.esimaccess_order_no = order_no
        order.status = OrderStatus.PROVISIONING
    except Exception as exc:  # esimaccess недоступен/отказал — не рушим обработку платежа
        order.status = OrderStatus.FAILED
        order.refund_reason = f"esimaccess create_order error: {exc}"

    await session.commit()


async def notify(session, *, website_account_id=None, user_id=None, type: NotificationType, title: str, body: str) -> None:
    """Кладёт запись в ленту уведомлений внутри приложения (не путать с сообщением
    от бота в Telegram — это отдельная, более "тихая" история событий)."""
    session.add(Notification(
        website_account_id=website_account_id, user_id=user_id,
        type=type, title=title, body=body,
    ))
    await session.commit()


async def _credit_topup(session, top_up: TopUp) -> None:
    """Подтверждённое пополнение — зачисляет деньги на баланс. Владелец пополнения —
    либо аккаунт сайта, либо пользователь бота (см. модель TopUp)."""
    top_up.status = PaymentStatus.PAID
    await session.commit()

    if top_up.website_account_id is not None:
        account = await session.get(WebsiteAccount, top_up.website_account_id)
        account.balance = round(account.balance + top_up.amount, 2)
    else:
        user = await session.get(User, top_up.user_id)
        user.balance = round(user.balance + top_up.amount, 2)
    await session.commit()

    await notify(
        session, website_account_id=top_up.website_account_id, user_id=top_up.user_id,
        type=NotificationType.PAYMENT, title="Баланс пополнен",
        body=f"На баланс зачислено ${top_up.amount:.2f}.",
    )


REFERRAL_BONUS_PERCENT = 10  # % от суммы первого успешного заказа реферала — зачисляется рефереру на баланс


async def maybe_credit_referral_bonus(session, order: Order) -> None:
    """
    Вызывается при переходе заказа в ACTIVE (см. app/webapp/webhooks.py).
    Разово (per referral_bonus_paid) зачисляет рефереру бонус на баланс —
    работает и для заказов с сайта (WebsiteAccount), и для заказов из бота
    (User) — смотрит, что из двух реально привязано к заказу.
    """
    if order.website_account_id is not None:
        model, owner_id = WebsiteAccount, order.website_account_id
    elif order.user_id is not None:
        model, owner_id = User, order.user_id
    else:
        return

    account = await session.get(model, owner_id)
    if account is None or account.referred_by_id is None or account.referral_bonus_paid:
        return

    referrer = await session.get(model, account.referred_by_id)
    if referrer is None:
        return

    bonus = round(float(order.price_charged) * REFERRAL_BONUS_PERCENT / 100, 2)
    referrer.balance = round(referrer.balance + bonus, 2)
    account.referral_bonus_paid = True
    await session.commit()

    ref_website_id = account.referred_by_id if model is WebsiteAccount else None
    ref_user_id = account.referred_by_id if model is User else None
    await notify(
        session, website_account_id=ref_website_id, user_id=ref_user_id,
        type=NotificationType.PAYMENT, title="Реферальный бонус",
        body=f"Тебе начислено ${bonus:.2f} — твой друг совершил первую покупку.",
    )


class InitiatePaymentRequest(BaseModel):
    method: str  # "idram" | "wallet_pay" | "oxapay" | "balance"


@router.post("/api/orders/{order_id}/pay")
async def initiate_payment(
    order_id: int, body: InitiatePaymentRequest, user: User = Depends(get_current_user)
):
    if body.method not in PROVIDER_BY_METHOD and body.method != "balance":
        raise HTTPException(status_code=400, detail="Неизвестный способ оплаты")
    if body.method == "test" and not settings.ENABLE_TEST_PAYMENT:
        # Проверка и на сервере, не только в интерфейсе — на случай, если кто-то
        # обратится к API напрямую, минуя саму кнопку (которая скрыта, если выключено).
        raise HTTPException(status_code=403, detail="Тестовая оплата отключена")
    if body.method == "wallet_pay" and not settings.ENABLE_WALLET_PAY:
        raise HTTPException(status_code=403, detail="Оплата через Wallet Pay временно недоступна")
    if body.method == "oxapay" and not settings.ENABLE_OXAPAY:
        raise HTTPException(status_code=403, detail="Оплата через OxaPay временно недоступна")

    async with get_session() as session:
        order = await session.get(Order, order_id)
        if order is None or order.user_id != user.id:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        if order.status != OrderStatus.PENDING_PAYMENT:
            raise HTTPException(status_code=409, detail="Заказ уже оплачен или отменён")

        external_id = str(uuid.uuid4())
        amount_str = f"{float(order.price_charged):.2f}"

        if body.method == "balance":
            db_user = await session.get(User, user.id)
            if db_user.balance < float(order.price_charged):
                raise HTTPException(status_code=402, detail="Недостаточно средств на балансе")
            db_user.balance = round(db_user.balance - float(order.price_charged), 2)
            payment = Payment(
                order_id=order.id, provider=PaymentProvider.BALANCE, status=PaymentStatus.PAID,
                amount=order.price_charged, currency=order.currency, external_payment_id=external_id,
            )
            session.add(payment)
            order.status = OrderStatus.PAID
            await session.commit()
            await _fulfill_order(session, order)
            redirect_url = None

        else:
            payment = Payment(
                order_id=order.id,
                provider=PROVIDER_BY_METHOD[body.method],
                status=PaymentStatus.PENDING,
                amount=order.price_charged,
                currency=order.currency,
                external_payment_id=external_id,
            )

            if body.method == "idram":
                session.add(payment)
                await session.commit()
                redirect_url = f"{settings.PUBLIC_BASE_URL}/pay/idram/{external_id}"

            elif body.method == "wallet_pay":
                try:
                    wp_order = await wallet_pay_client.create_order(
                        amount=amount_str,
                        currency_code=order.currency,
                        external_id=external_id,
                        description=f"Заказ №{order.id}",
                        customer_telegram_user_id=user.telegram_id,
                    )
                except WalletPayError as exc:
                    raise HTTPException(status_code=502, detail=f"Wallet Pay: {exc}")

                payment.provider_order_id = str(wp_order["id"])
                payment.pay_link = wp_order["payLink"]
                session.add(payment)
                await session.commit()
                redirect_url = wp_order["payLink"]

            elif body.method == "oxapay":
                try:
                    invoice = await oxapay_client.create_invoice(
                        amount=float(order.price_charged),
                        currency=order.currency,
                        order_id=external_id,
                        description=f"Заказ №{order.id}",
                        callback_url=f"{settings.PUBLIC_BASE_URL}/webhooks/oxapay",
                        return_url=f"{settings.PUBLIC_BASE_URL}/pay/oxapay/success",
                    )
                except OxaPayError as exc:
                    raise HTTPException(status_code=502, detail=f"OxaPay: {exc}")

                payment.provider_order_id = invoice["track_id"]
                payment.pay_link = invoice["payment_url"]
                session.add(payment)
                await session.commit()
                redirect_url = invoice["payment_url"]

            else:  # "test" — уже проверили выше, что settings.ENABLE_TEST_PAYMENT включён
                # Сразу "оплачен", без редиректа никуда. Дальше — тот же самый настоящий
                # вызов esimaccess, что и для любого реального способа оплаты выше.
                payment.status = PaymentStatus.PAID
                session.add(payment)
                order.status = OrderStatus.PAID
                await session.commit()
                await _fulfill_order(session, order)
                redirect_url = None

    return {"redirect_url": redirect_url, "payment_external_id": external_id}


@router.get("/api/orders/{order_id}/payment-status")
async def payment_status(order_id: int, user: User = Depends(get_current_user)):
    async with get_session() as session:
        order = await session.get(Order, order_id)
        if order is None or order.user_id != user.id:
            raise HTTPException(status_code=404, detail="Заказ не найден")

        result = await session.execute(
            select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc())
        )
        payment = result.scalars().first()

        # Idram подтверждает через вебхук (RESULT_URL) — здесь просто читаем то, что
        # он уже записал. Wallet Pay подтверждаем опросом прямо сейчас (см. модуль).
        if payment and payment.provider == PaymentProvider.WALLET_PAY and payment.status == PaymentStatus.PENDING:
            try:
                preview = await wallet_pay_client.get_order_preview(payment.provider_order_id)
                if preview.get("status") == "PAID":
                    payment.status = PaymentStatus.PAID
                    order.status = OrderStatus.PAID
                    await session.commit()
                    await _fulfill_order(session, order)
                elif preview.get("status") in ("EXPIRED", "CANCELLED"):
                    payment.status = PaymentStatus.FAILED
                    await session.commit()
            except WalletPayError:
                pass  # временная ошибка опроса — просто вернём текущий статус ниже

        return {
            "order_status": order.status.value,
            "payment_status": payment.status.value if payment else None,
        }


@router.get("/pay/idram/{external_id}", response_class=HTMLResponse)
async def idram_redirect_page(external_id: str):
    """Открывается из Mini App (Telegram.WebApp.openLink) или с сайта — сама переносит на Idram.
    Работает и с заказами (Payment), и с пополнениями баланса (TopUp)."""
    async with get_session() as session:
        payment = (
            await session.execute(select(Payment).where(Payment.external_payment_id == external_id))
        ).scalar_one_or_none()

        if payment is not None:
            order = (await session.execute(select(Order).where(Order.id == payment.order_id))).scalar_one()
            amount = payment.amount
            description = f"Заказ №{order.id}"
            success_url = fail_url = None
            if order.guest_token:  # заказ с сайта (не из Telegram) — вернуть на страницу заказа, а не в Telegram
                success_url = f"{settings.PUBLIC_BASE_URL}/shop/order/{order.guest_token}"
                fail_url = success_url
        else:
            top_up = (
                await session.execute(select(TopUp).where(TopUp.external_payment_id == external_id))
            ).scalar_one_or_none()
            if top_up is None:
                raise HTTPException(status_code=404, detail="Платёж не найден")
            amount = top_up.amount
            description = "Пополнение баланса"
            success_url = fail_url = f"{settings.PUBLIC_BASE_URL}/shop/account/balance"

    fields = idram.build_payment_form_fields(
        bill_no=external_id,
        amount=f"{float(amount):.2f}",
        description=description,
        success_url=success_url,
        fail_url=fail_url,
    )
    idram_logger.info("Redirect to Idram: bill_no=%s amount=%s", external_id, fields["EDP_AMOUNT"])
    return idram.render_autosubmit_html(fields)


@router.get("/pay/idram/success", response_class=HTMLResponse)
async def idram_success_page():
    return "<html><body>Оплата прошла успешно. Можешь вернуться в Telegram.</body></html>"


@router.get("/pay/idram/fail", response_class=HTMLResponse)
async def idram_fail_page():
    return "<html><body>Оплата не завершена. Попробуй ещё раз в приложении.</body></html>"


@router.post("/webhooks/idram", response_class=PlainTextResponse)
async def idram_webhook(request: Request):
    """RESULT_URL — сюда Idram шлёт precheck, а затем подтверждение платежа (за заказ ИЛИ за пополнение баланса)."""
    form = dict(await request.form())
    bill_no = form.get("EDP_BILL_NO", "")
    idram_logger.info(
        "Webhook received: bill_no=%s precheck=%s trans_id=%s",
        bill_no, idram.is_precheck(form), form.get("EDP_TRANS_ID"),
    )

    async with get_session() as session:
        payment = (
            await session.execute(select(Payment).where(Payment.external_payment_id == bill_no))
        ).scalar_one_or_none()
        top_up = None
        if payment is None:
            top_up = (
                await session.execute(select(TopUp).where(TopUp.external_payment_id == bill_no))
            ).scalar_one_or_none()

        if payment is None and top_up is None:
            idram_logger.warning("Webhook: unknown bill_no=%s — ignoring (responding ERROR)", bill_no)
            return "ERROR"  # не наш EDP_BILL_NO

        if idram.is_precheck(form):
            idram_logger.info("Precheck OK: bill_no=%s", bill_no)
            return "OK"

        if not idram.verify_checksum(form):
            idram_logger.error(
                "CHECKSUM MISMATCH: bill_no=%s — возможна попытка подделки или расхождение "
                "в реквизитах, платёж НЕ подтверждён.", bill_no,
            )
            return "ERROR"

        if payment is not None:
            payment.status = PaymentStatus.PAID
            payment.provider_transaction_id = form.get("EDP_TRANS_ID")
            payment.raw_callback = form
            await session.commit()

            order = await session.get(Order, payment.order_id)
            order.status = OrderStatus.PAID
            await session.commit()

            idram_logger.info("Payment CONFIRMED: order=%s bill_no=%s", order.id, bill_no)
            await _fulfill_order(session, order)
        else:
            await _credit_topup(session, top_up)
            idram_logger.info("Top-up CONFIRMED: top_up=%s bill_no=%s", top_up.id, bill_no)

    return "OK"


@router.get("/pay/oxapay/success", response_class=HTMLResponse)
async def oxapay_success_page():
    return "<html><body>Платёж отправлен, ждём подтверждения сети. Можешь вернуться в Telegram.</body></html>"


@router.post("/webhooks/oxapay", response_class=PlainTextResponse)
async def oxapay_webhook(request: Request, hmac_header: str = Header(default="", alias="hmac")):
    """
    callback_url из create_invoice. OxaPay сначала присылает статус "Paying" (тx в сети,
    ещё не подтверждена) — это НЕ финал, ждём вторую доставку со статусом "Paid".
    Подпись — заголовок "hmac", HMAC-SHA512(сырое тело запроса, ключ=OXAPAY_MERCHANT_API_KEY).
    """
    raw_body = await request.body()
    if not verify_webhook_signature(raw_body, hmac_header):
        return PlainTextResponse("Invalid HMAC signature", status_code=400)

    payload = await request.json()
    if payload.get("status") != "Paid":
        return "OK"  # "Paying" и промежуточные статусы — просто подтверждаем приём

    async with get_session() as session:
        payment = (
            await session.execute(select(Payment).where(Payment.external_payment_id == payload.get("order_id", "")))
        ).scalar_one_or_none()

        if payment is not None:
            payment.status = PaymentStatus.PAID
            payment.provider_transaction_id = payload.get("track_id")
            payment.raw_callback = payload
            await session.commit()

            order = await session.get(Order, payment.order_id)
            order.status = OrderStatus.PAID
            await session.commit()

            await _fulfill_order(session, order)
            return "OK"

        top_up = (
            await session.execute(select(TopUp).where(TopUp.external_payment_id == payload.get("order_id", "")))
        ).scalar_one_or_none()
        if top_up is not None:
            await _credit_topup(session, top_up)

    return "OK"


# --- Баланс и пополнение — версия для Mini App (Telegram User, не сайт) ---

@router.get("/api/balance")
async def get_balance(user: User = Depends(get_current_user)):
    async with get_session() as session:
        db_user = await session.get(User, user.id)
        if db_user.referral_code is None:
            # Старые пользователи (созданы до появления рефералки) — генерируем лениво при первом обращении.
            db_user.referral_code = secrets.token_urlsafe(6)
            await session.commit()

        top_ups = list((
            await session.execute(
                select(TopUp).where(TopUp.user_id == user.id).order_by(TopUp.created_at.desc()).limit(20)
            )
        ).scalars())

    return {
        "balance": db_user.balance,
        "referral_code": db_user.referral_code,
        "referral_percent": REFERRAL_BONUS_PERCENT,
        "top_ups": [
            {"amount": t.amount, "provider": t.provider.value, "status": t.status.value}
            for t in top_ups
        ],
    }


class TopUpRequest(BaseModel):
    amount: float
    method: str  # "idram" | "oxapay"


@router.post("/api/balance/topup")
async def topup_balance(body: TopUpRequest, user: User = Depends(get_current_user)):
    if body.amount < 1:
        raise HTTPException(status_code=400, detail="Минимальная сумма пополнения — $1")
    if body.method not in ("idram", "oxapay"):
        raise HTTPException(status_code=400, detail="Неизвестный способ оплаты")
    if body.method == "oxapay" and not settings.ENABLE_OXAPAY:
        raise HTTPException(status_code=403, detail="Оплата через OxaPay временно недоступна")

    external_id = str(uuid.uuid4())
    amount = round(body.amount, 2)

    async with get_session() as session:
        top_up = TopUp(
            user_id=user.id, amount=amount, currency="USD",
            provider=PaymentProvider.IDRAM if body.method == "idram" else PaymentProvider.OXAPAY,
            status=PaymentStatus.PENDING, external_payment_id=external_id,
        )

        if body.method == "idram":
            session.add(top_up)
            await session.commit()
            redirect_url = f"{settings.PUBLIC_BASE_URL}/pay/idram/{external_id}"
        else:
            try:
                invoice = await oxapay_client.create_invoice(
                    amount=amount, currency="USD", order_id=external_id,
                    description="Пополнение баланса",
                    callback_url=f"{settings.PUBLIC_BASE_URL}/webhooks/oxapay",
                    return_url=f"{settings.PUBLIC_BASE_URL}/pay/oxapay/success",
                )
            except OxaPayError as exc:
                raise HTTPException(status_code=502, detail=f"OxaPay: {exc}")
            top_up.provider_order_id = invoice["track_id"]
            top_up.pay_link = invoice["payment_url"]
            session.add(top_up)
            await session.commit()
            redirect_url = invoice["payment_url"]

    return {"redirect_url": redirect_url}