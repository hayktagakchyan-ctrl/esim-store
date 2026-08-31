"""
Приём вебхуков от esimaccess. Настраивается в их личном кабинете: URL вида
https://<твой-домен>/webhooks/esimaccess — см. app.mount в app/webapp/app.py.

Что здесь реализовано (по документации esimaccess):
- Дедупликация по notifyId — они прямо предупреждают, что доставка не гарантированно
  однократная.
- ORDER_STATUS / GOT_RESOURCE — главное событие: запрашиваем esim/query по orderNo,
  чтобы получить iccid/QR, и переводим заказ в ACTIVE. Формат ответа (esimList,
  qrCodeUrl, ac и т.д.) полностью подтверждён документацией.
- ESIM_STATUS — обновляем last_esim_status/last_smdp_status (для админки), и если
  статус ушёл в CANCEL/REVOKED/SUSPENDED — это сигнал, что нужно вмешательство поддержки.
- DATA_USAGE / VALIDITY_USAGE — шлём клиенту уведомление в Telegram напрямую (не через
  бот-процесс — здесь создан отдельный лёгкий экземпляр Bot только для отправки).
- CHECK_HEALTH — просто 200 OK, без побочных эффектов.
"""
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database.db import get_session
from app.database.models import Order, OrderStatus, WebhookEvent
from app.services.esimaccess import esimaccess_client, ESimAccessError
from app.webapp.notify_bots import client_notify_bot as _notify_bot

router = APIRouter()

# IP, с которых esimaccess шлёт вебхуки (см. документацию, раздел IP Whitelist).
# Включается ESIMACCESS_WEBHOOK_ENFORCE_IP_ALLOWLIST=true в .env — по умолчанию выключено,
# т.к. за прокси/CDN реальный IP отправителя не всегда виден напрямую.
_ALLOWED_IPS = {"3.1.131.226", "54.254.74.88", "18.136.190.97", "18.136.60.197", "18.136.19.137"}


@router.post("/webhooks/esimaccess")
async def esimaccess_webhook(request: Request):
    if settings.ESIMACCESS_WEBHOOK_ENFORCE_IP_ALLOWLIST:
        client_ip = request.client.host if request.client else None
        if client_ip not in _ALLOWED_IPS:
            raise HTTPException(status_code=403, detail="IP не в списке разрешённых")

    try:
        payload = await request.json()
    except Exception:
        # esimaccess (или любой другой health-check) вполне может прислать пустое
        # тело или что-то не строго в формате JSON просто чтобы проверить, что
        # адрес вообще отвечает — падать на этом нельзя, иначе первая же попытка
        # подключить вебхук в их личном кабинете будет считаться неудачной.
        return {"ok": True}

    notify_type = payload.get("notifyType")
    notify_id = payload.get("notifyId")
    content = payload.get("content", {})

    if notify_type == "CHECK_HEALTH":
        return {"ok": True}

    if not notify_id:
        raise HTTPException(status_code=400, detail="Нет notifyId")

    async with get_session() as session:
        # Дедупликация: если notifyId уже видели — тихо подтверждаем и ничего не делаем.
        session.add(WebhookEvent(notify_id=notify_id, notify_type=notify_type or "unknown"))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return {"ok": True, "duplicate": True}

        if notify_type == "ORDER_STATUS":
            await _handle_order_status(session, content)
        elif notify_type == "ESIM_STATUS":
            await _handle_esim_status(session, content)
        elif notify_type == "DATA_USAGE":
            await _handle_data_usage(session, content)
        elif notify_type == "VALIDITY_USAGE":
            await _handle_validity_usage(session, content)
        # SMDP_EVENT — самый частый и низкоуровневый, для MVP не обрабатываем
        # (см. Developer Notes в документации: большинству интеграций достаточно ESIM_STATUS).

    return {"ok": True}


async def _get_order_by_transaction_id(session, transaction_id: str) -> Order | None:
    result = await session.execute(select(Order).where(Order.our_transaction_id == transaction_id))
    return result.scalar_one_or_none()


async def _handle_order_status(session, content: dict) -> None:
    if content.get("orderStatus") != "GOT_RESOURCE":
        return
    order = await _get_order_by_transaction_id(session, content.get("transactionId", ""))
    if order is None:
        return  # заказ не наш (либо ещё не привязан transactionId) — игнорируем

    order.esimaccess_order_no = content.get("orderNo")

    try:
        esim_list = await esimaccess_client.query_esim(order_no=order.esimaccess_order_no)
    except ESimAccessError:
        # Скорее всего 200010 — SM-DP+ ещё выделяет профиль (до ~30 сек по докам).
        # Оставляем PROVISIONING, следующий вебхук/ручная проверка в админке подхватит.
        await session.commit()
        return

    if not esim_list:
        # На всякий случай — success=true, но пусто. Ведём себя так же, как при 200010.
        await session.commit()
        return

    esim = esim_list[0]  # у нас всегда count=1 при заказе, так что один элемент и ожидаем
    order.iccid = esim.get("iccid")
    order.esimaccess_esim_tran_no = esim.get("esimTranNo")
    order.qr_code_data = esim.get("qrCodeUrl")
    order.activation_instructions = esim.get("ac")  # LPA-код для ручного ввода, если QR не сканируется
    order.status = OrderStatus.ACTIVE
    await session.commit()

    await session.refresh(order, attribute_names=["user"])
    if order.iccid:
        await _notify_bot.send_message(
            chat_id=order.user.telegram_id,
            text=(
                f"✅ Твой eSIM готов! Открой «Мои eSIM» в приложении, там появился QR-код "
                f"для активации (заказ №{order.id})."
            ),
        )


async def _handle_esim_status(session, content: dict) -> None:
    order = await _get_order_by_transaction_id(session, content.get("transactionId", ""))
    if order is None:
        return
    order.last_esim_status = content.get("esimStatus")
    order.last_smdp_status = content.get("smdpStatus")
    await session.commit()


async def _handle_data_usage(session, content: dict) -> None:
    order = await _find_order_by_esim_tran_no(session, content.get("esimTranNo", ""))
    if order is None:
        return
    await session.refresh(order, attribute_names=["user"])
    threshold_pct = int(float(content.get("remainThreshold", 0)) * 100)
    remain_mb = round(content.get("remain", 0) / 1048576)
    await _notify_bot.send_message(
        chat_id=order.user.telegram_id,
        text=f"📶 Осталось {threshold_pct}% трафика по твоему eSIM (≈{remain_mb} МБ). "
             f"Можно оформить докупку в разделе «Мои eSIM».",
    )


async def _handle_validity_usage(session, content: dict) -> None:
    order = await _find_order_by_esim_tran_no(session, content.get("esimTranNo", ""))
    if order is None:
        return
    await session.refresh(order, attribute_names=["user"])
    await _notify_bot.send_message(
        chat_id=order.user.telegram_id,
        text=f"⏳ Срок действия твоего eSIM истекает через {content.get('remain', '?')} дн. "
             f"После истечения докупить данные будет нельзя — оформи новый пакет заранее.",
    )


async def _find_order_by_esim_tran_no(session, esim_tran_no: str) -> Order | None:
    result = await session.execute(
        select(Order).where(Order.esimaccess_esim_tran_no == esim_tran_no)
    )
    return result.scalar_one_or_none()