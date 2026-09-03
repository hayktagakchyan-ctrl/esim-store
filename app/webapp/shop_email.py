"""
Отправка писем (сейчас — только восстановление пароля) через стандартный
smtplib, без сторонних библиотек — та же логика, что и с хешированием пароля:
не добавлять зависимостей, которые могут не встать на Windows без компилятора.

Работает с ЛЮБЫМ SMTP-провайдером (Gmail, Yandex, свой домен, транзакционные
сервисы вроде SendGrid/Mailgun через их SMTP-интерфейс) — просто нужны
правильные SMTP_* в .env.

Если SMTP_HOST не задан — письмо не отправляется, функция возвращает False,
и вызывающий код (app/webapp/shop.py) сам решает, что показать пользователю
и продублировать ли ссылку в бот поддержки для тестирования.
"""
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from app.config import settings


def send_email(to: str, subject: str, body: str) -> bool:
    if not settings.SMTP_HOST:
        return False

    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    # formataddr вместо простой f-строки — иначе если в SMTP_FROM_NAME окажется
    # запятая или другой спецсимвол, письмо у части почтовых клиентов может
    # сломаться или показать имя криво. formataddr сам всё правильно экранирует.
    message["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_FROM_EMAIL))
    message["To"] = to

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [to], message.as_string())
        return True
    except Exception:
        return False
