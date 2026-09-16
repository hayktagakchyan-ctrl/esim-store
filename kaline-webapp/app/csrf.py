"""
CSRF (Cross-Site Request Forgery) — защита форм на сессионных cookie (сайт,
админка) от подделки запроса со стороннего сайта.

Как работает: при первом же рендере страницы генерируем случайный токен и
кладём его в подписанную сессионную cookie (Starlette сама её подписывает —
подделать значение снаружи нельзя). Тот же токен кладём скрытым полем в
каждую форму. При отправке формы сверяем: токен из тела запроса должен
совпадать с токеном из cookie этого же браузера. Стороннему сайту токен
взять неоткуда — значит подделать запрос от имени залогиненного человека
он не может.

Это НЕ нужно для мини-аппа бота и чата поддержки в Telegram — там своя
авторизация через подписанные Telegram initData (не cookie), которую
чужой сайт в принципе не может воспроизвести. Поэтому CSRF-мидлвар
применяется только к путям сайта (/shop/*) и админки, но не к /api/*,
/support-chat/api/*, /webhooks/*.
"""
import secrets

from fastapi import Request


def get_or_create_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


async def verify_csrf(request: Request) -> bool:
    """
    Возвращает True, если токен из тела формы совпадает с токеном в сессии.

    Важный нюанс (нашёл на реальном тесте, не в теории): Starlette кэширует
    разобранное тело ВНУТРИ конкретного объекта Request, но мидлвар на базе
    BaseHTTPMiddleware (а @app.middleware("http") — это он и есть) успевает
    прочитать тело раньше, чем FastAPI создаст свой Request ниже по цепочке
    для Form(...) в самом роуте — и то, что тело уже "прочитано" из исходного
    ASGI-потока, туда не переносится. Без явного восстановления потока роут
    получал бы email/password и т.д. пустыми (проверено — так и было: 422
    "Field required" на все поля формы сразу после того как тут же читали
    request.form()). Чтобы это не сломать, вручную "переигрываем" уже
    прочитанные байты обратно в receive() — тогда и мидлвар, и сам роут
    видят одно и то же тело.
    """
    session_token = request.session.get("csrf_token")
    if not session_token:
        return False
    try:
        body = await request.body()
    except Exception:
        return False

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    request._receive = receive
    request._body = body  # на случай, если этот же объект Request переиспользуется дальше

    try:
        form = await request.form()
    except Exception:
        return False
    return secrets.compare_digest(form.get("csrf_token", ""), session_token)
