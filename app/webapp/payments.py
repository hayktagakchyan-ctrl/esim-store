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
from app.database.models import Order, OrderStatus, Payment, PaymentProvider, PaymentStatus, User
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


class InitiatePaymentRequest(BaseModel):
    method: str  # "idram" | "wallet_pay" | "oxapay"


@router.post("/api/orders/{order_id}/pay")
async def initiate_payment(
    order_id: int, body: InitiatePaymentRequest, user: User = Depends(get_current_user)
):
    if body.method not in PROVIDER_BY_METHOD:
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
    """Открывается из Mini App (Telegram.WebApp.openLink) или с сайта — сама переносит на Idram."""
    async with get_session() as session:
        result = await session.execute(
            select(Payment).where(Payment.external_payment_id == external_id)
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            raise HTTPException(status_code=404, detail="Платёж не найден")

        result = await session.execute(select(Order).where(Order.id == payment.order_id))
        order = result.scalar_one()

    success_url = None
    fail_url = None
    if order.guest_token:  # заказ с сайта (не из Telegram) — вернуть на страницу заказа, а не в Telegram
        success_url = f"{settings.PUBLIC_BASE_URL}/shop/order/{order.guest_token}"
        fail_url = success_url

    fields = idram.build_payment_form_fields(
        bill_no=payment.external_payment_id,
        amount=f"{float(payment.amount):.2f}",
        description=f"Заказ №{order.id}",
        success_url=success_url,
        fail_url=fail_url,
    )
    idram_logger.info(
        "Redirect to Idram: order=%s bill_no=%s amount=%s",
        order.id, payment.external_payment_id, fields["EDP_AMOUNT"],
    )
    return idram.render_autosubmit_html(fields)


@router.get("/pay/idram/success", response_class=HTMLResponse)
async def idram_success_page():
    return "<html><body>Оплата прошла успешно. Можешь вернуться в Telegram.</body></html>"


@router.get("/pay/idram/fail", response_class=HTMLResponse)
async def idram_fail_page():
    return "<html><body>Оплата не завершена. Попробуй ещё раз в приложении.</body></html>"


@router.post("/webhooks/idram", response_class=PlainTextResponse)
async def idram_webhook(request: Request):
    """RESULT_URL — сюда Idram шлёт precheck, а затем подтверждение платежа."""
    form = dict(await request.form())
    bill_no = form.get("EDP_BILL_NO", "")
    idram_logger.info(
        "Webhook received: bill_no=%s precheck=%s trans_id=%s",
        bill_no, idram.is_precheck(form), form.get("EDP_TRANS_ID"),
    )

    async with get_session() as session:
        result = await session.execute(
            select(Payment).where(Payment.external_payment_id == bill_no)
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            idram_logger.warning("Webhook: unknown bill_no=%s — ignoring (responding ERROR)", bill_no)
            return "ERROR"  # не наш EDP_BILL_NO

        if idram.is_precheck(form):
            # EDP_REC_ACCOUNT сверяет сам Idram на своей стороне; нам достаточно
            # подтвердить, что EDP_BILL_NO существует как наш ожидающий оплаты платёж.
            idram_logger.info("Precheck OK: bill_no=%s order=%s", bill_no, payment.order_id)
            return "OK"

        if not idram.verify_checksum(form):
            idram_logger.error(
                "CHECKSUM MISMATCH: bill_no=%s order=%s — возможна попытка подделки "
                "или расхождение в реквизитах, платёж НЕ подтверждён.",
                bill_no, payment.order_id,
            )
            return "ERROR"

        payment.status = PaymentStatus.PAID
        payment.provider_transaction_id = form.get("EDP_TRANS_ID")
        payment.raw_callback = form
        await session.commit()

        order = await session.get(Order, payment.order_id)
        order.status = OrderStatus.PAID
        await session.commit()

        idram_logger.info(
            "Payment CONFIRMED: order=%s bill_no=%s amount=%s trans_id=%s payer=%s",
            order.id, bill_no, form.get("EDP_AMOUNT"), form.get("EDP_TRANS_ID"), form.get("EDP_PAYER_ACCOUNT"),
        )

        await _fulfill_order(session, order)
        idram_logger.info(
            "Order fulfillment result: order=%s status=%s esimaccess_order_no=%s",
            order.id, order.status.value, order.esimaccess_order_no,
        )

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
        result = await session.execute(
            select(Payment).where(Payment.external_payment_id == payload.get("order_id", ""))
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            return "OK"  # не наш order_id — молча подтверждаем, чтобы OxaPay не ретраил

        payment.status = PaymentStatus.PAID
        payment.provider_transaction_id = payload.get("track_id")
        payment.raw_callback = payload
        await session.commit()

        order = await session.get(Order, payment.order_id)
        order.status = OrderStatus.PAID
        await session.commit()

        await _fulfill_order(session, order)

    return "OK"
