"""
Idram — распространённая в Армении платёжная система. Протокол называется EDP
и работает так:

1. Мы генерируем HTML-форму со скрытыми полями и отправляем (редиректим) покупателя
   на хостед-страницу Idram — он платит там, не на нашей стороне.
2. Idram стучится СЕРВЕР-СЕРВЕР на наш RESULT_URL дважды:
   a. "Precheck" (EDP_PRECHECK=YES) — спрашивает, существует ли у нас такой заказ
      (EDP_BILL_NO) и наш ли это EDP_REC_ACCOUNT. Мы отвечаем текстом "OK", если да.
   b. "Payment confirmation" — приходит EDP_PAYER_ACCOUNT/EDP_TRANS_ID/EDP_TRANS_DATE
      и контрольная сумма EDP_CHECKSUM. Мы проверяем её и, если верна, помечаем
      заказ оплаченным и тоже отвечаем "OK".
3. Покупателя также редиректит на SUCCESS_URL/FAIL_URL — но это только для UX,
   источник истины — RESULT_URL из пункта 2, потому что редирект браузера покупатель
   может закрыть, подделать или просто не дождаться.

ПОДТВЕРЖДЕНО ОФИЦИАЛЬНЫМ ДОКУМЕНТОМ ("Idram Payment System merchant interface
description", прислан напрямую от Idram) — здесь больше не осталось ни одного
неподтверждённого места:
- Поля формы: EDP_LANGUAGE (RU/EN/AM — не путать с нашим внутренним кодом "hy",
  у Idram именно "AM"), EDP_REC_ACCOUNT, EDP_DESCRIPTION, EDP_AMOUNT, EDP_BILL_NO,
  SUCCESS_URL, FAIL_URL, RESULT_URL.
- Базовый адрес хостед-страницы — https://banking.idram.am/Payment/GetPayment
  (раньше здесь была заглушка с другим доменом — исправлено).
- Формула чек-суммы (см. verify_checksum ниже) — дословно совпадает с документом.
"""
from __future__ import annotations

import hashlib

from app.config import settings


def build_payment_form_fields(
    *,
    bill_no: str,
    amount: str,
    description: str,
    language: str = "RU",
    success_url: str | None = None,
    fail_url: str | None = None,
) -> dict[str, str]:
    """
    Поля скрытой HTML-формы, которую нужно отправить (POST) на settings.IDRAM_PAYMENT_URL.
    amount — строка с точкой как разделителем дробной части (напр. "9.00"), не float:
    Idram сверяет её побайтово в чек-сумме подтверждения, лишние нули/формат имеют значение.

    success_url/fail_url — по умолчанию ведут обратно в Telegram (Mini App), но сайт
    (app/webapp/shop.py) передаёт свои — прямо на страницу статуса заказа у гостя,
    так как открывать Telegram посетителю сайта было бы бессмысленно.
    """
    return {
        "EDP_LANGUAGE": language,
        "EDP_REC_ACCOUNT": settings.IDRAM_REC_ACCOUNT,
        "EDP_DESCRIPTION": description,
        "EDP_AMOUNT": amount,
        "EDP_BILL_NO": bill_no,
        "SUCCESS_URL": success_url or f"{settings.PUBLIC_BASE_URL}/pay/idram/success",
        "FAIL_URL": fail_url or f"{settings.PUBLIC_BASE_URL}/pay/idram/fail",
        "RESULT_URL": f"{settings.PUBLIC_BASE_URL}/webhooks/idram",
    }


def is_precheck(form: dict) -> bool:
    return form.get("EDP_PRECHECK") == "YES"


def verify_checksum(form: dict) -> bool:
    """
    Проверка EDP_CHECKSUM на "Payment confirmation" запросе (после precheck).
    Формула (подтверждена несколькими независимыми интеграциями):
        MD5("{EDP_REC_ACCOUNT}:{EDP_AMOUNT}:{SECRET_KEY}:{EDP_BILL_NO}:"
            "{EDP_PAYER_ACCOUNT}:{EDP_TRANS_ID}:{EDP_TRANS_DATE}")
    сравнивается регистронезависимо с присланным EDP_CHECKSUM.
    """
    required = (
        "EDP_REC_ACCOUNT", "EDP_AMOUNT", "EDP_BILL_NO",
        "EDP_PAYER_ACCOUNT", "EDP_TRANS_ID", "EDP_TRANS_DATE", "EDP_CHECKSUM",
    )
    if not all(k in form for k in required):
        return False

    text_to_hash = ":".join([
        form["EDP_REC_ACCOUNT"],
        form["EDP_AMOUNT"],
        settings.IDRAM_SECRET_KEY,
        form["EDP_BILL_NO"],
        form["EDP_PAYER_ACCOUNT"],
        form["EDP_TRANS_ID"],
        form["EDP_TRANS_DATE"],
    ])
    computed = hashlib.md5(text_to_hash.encode()).hexdigest()
    return computed.upper() == form["EDP_CHECKSUM"].upper()


def render_autosubmit_html(fields: dict[str, str]) -> str:
    """
    Простая самоотправляющаяся HTML-форма — открываем её в Telegram.WebApp.openLink()
    из Mini App, она сама переносит покупателя на страницу оплаты Idram.
    """
    inputs = "\n".join(
        f'<input type="hidden" name="{key}" value="{value}">' for key, value in fields.items()
    )
    return f"""<!DOCTYPE html>
<html><body onload="document.forms[0].submit()">
<form method="POST" action="{settings.IDRAM_PAYMENT_URL}">
{inputs}
</form>
</body></html>"""
