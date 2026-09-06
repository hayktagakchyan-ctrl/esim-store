"""
Отправка писем (подтверждение email, восстановление пароля) через стандартный
smtplib, без сторонних библиотек — та же логика, что и с хешированием пароля:
не добавлять зависимостей, которые могут не встать на Windows без компилятора.

Работает с ЛЮБЫМ SMTP-провайдером (Gmail, Yandex, свой домен, транзакционные
сервисы вроде SendGrid/Mailgun через их SMTP-интерфейс) — просто нужны
правильные SMTP_* в .env/переменных окружения.

Если SMTP_HOST не задан — считаем, что почта осознанно не настроена (это
нормально для теста), функция возвращает (False, "not_configured").
Если SMTP_HOST задан, но отправка всё равно не удалась (неверный пароль,
не тот порт, провайдер заблокировал вход и т.п.) — это уже РЕАЛЬНАЯ ошибка,
не "не настроено"; возвращаем (False, "<текст ошибки>") и пишем её в лог
(Railway показывает print/logging в логах сервиса), чтобы не гадать вслепую,
почему письма не уходят, если .env вроде бы заполнен.
"""
import logging
import socket
import smtplib
from contextlib import contextmanager
from email.mime.text import MIMEText
from email.utils import formataddr

from app.config import settings

email_logger = logging.getLogger("email")


@contextmanager
def _force_ipv4_dns():
    """
    smtplib.SMTP(host, port) иногда падает с "Network is unreachable" — известная
    проблема контейнерных окружений (в т.ч. Railway): у хоста провайдера есть и
    IPv4-, и IPv6-адрес, Python пытается сначала IPv6, а у контейнера нет по нему
    маршрута наружу. На время подключения подменяем резолвер так, чтобы он отдавал
    только IPv4-адреса — сам smtplib при этом работает как обычно (включая
    starttls() — сертификат по-прежнему сверяется по имени хоста, не по IP).
    """
    original_getaddrinfo = socket.getaddrinfo

    def ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

    socket.getaddrinfo = ipv4_only_getaddrinfo
    try:
        yield
    finally:
        socket.getaddrinfo = original_getaddrinfo


def send_email(to: str, subject: str, body: str) -> tuple[bool, str | None]:
    """Возвращает (True, None) при успехе, иначе (False, "not_configured" | "<текст ошибки>")."""
    if not settings.SMTP_HOST:
        return False, "not_configured"

    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    # formataddr вместо простой f-строки — иначе если в SMTP_FROM_NAME окажется
    # запятая или другой спецсимвол, письмо у части почтовых клиентов может
    # сломаться или показать имя криво. formataddr сам всё правильно экранирует.
    message["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_FROM_EMAIL))
    message["To"] = to

    try:
        with _force_ipv4_dns():
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL, [to], message.as_string())
        return True, None
    except Exception as e:
        error_text = f"{type(e).__name__}: {e}"
        email_logger.error("Не удалось отправить письмо на %s через %s:%s — %s",
                            to, settings.SMTP_HOST, settings.SMTP_PORT, error_text)
        return False, error_text
