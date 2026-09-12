"""
Отправка писем (подтверждение email, восстановление пароля) через Resend
(https://resend.com) — его HTTP API, а НЕ через SMTP.

Почему не SMTP: на Railway (и у многих других облачных хостингов) исходящий
SMTP-трафик на 587/465 порту либо заблокирован совсем, либо очень нестабилен —
именно это мы и поймали в логах ("OSError: Network is unreachable", потом
"TimeoutError: timed out" для двух РАЗНЫХ писем подряд — не совпадение, а
блокировка на уровне сети хостинга). Никакие трюки с IPv4/IPv6 внутри
приложения это не обходят, т.к. блокируется сам порт, а не конкретный адрес.
HTTP на 443 порту так не блокируют — поэтому Resend и любой другой
транзакционный email-сервис с HTTP API тут работает надёжно.

Настройка (см. RESEND_API_KEY в config.py):
1. Завести аккаунт на resend.com (есть бесплатный тариф).
2. Добавить и подтвердить свой домен (Resend даст DNS-записи — их нужно
   прописать у регистратора домена). Без своего домена можно слать только на
   e-mail владельца аккаунта Resend, через onboarding@resend.dev — годится
   для теста, не для реальных клиентов.
3. Взять API-ключ в личном кабинете Resend, положить в RESEND_API_KEY.
4. SMTP_FROM_EMAIL — адрес на подтверждённом домене, напр. noreply@kaline.am.

Если RESEND_API_KEY не задан — считаем, что почта осознанно не настроена (это
нормально для теста), функция возвращает (False, "not_configured").
Если ключ задан, но отправка всё равно не удалась — это уже РЕАЛЬНАЯ ошибка;
возвращаем (False, "<текст ошибки>") и пишем её в лог (Railway показывает
logging в логах сервиса), чтобы не гадать вслепую, почему письма не уходят.
"""
import logging

import httpx

from app.config import settings

email_logger = logging.getLogger("email")

RESEND_API_URL = "https://api.resend.com/emails"


def send_email(to: str, subject: str, body: str) -> tuple[bool, str | None]:
    """Возвращает (True, None) при успехе, иначе (False, "not_configured" | "<текст ошибки>")."""
    if not settings.RESEND_API_KEY:
        return False, "not_configured"

    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>",
                "to": [to],
                "subject": subject,
                "text": body,
            },
            timeout=15,
        )
        if response.status_code >= 400:
            error_text = f"HTTP {response.status_code}: {response.text[:300]}"
            email_logger.error("Resend отказал при отправке на %s — %s", to, error_text)
            return False, error_text
        return True, None
    except Exception as e:
        error_text = f"{type(e).__name__}: {e}"
        email_logger.error("Не удалось отправить письмо через Resend на %s — %s", to, error_text)
        return False, error_text
