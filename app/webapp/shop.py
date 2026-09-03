"""
Публичный сайт (не Mini App — обычные страницы для любого браузера, без Telegram).

Изначально был нужен для того, чтобы Idram увидел настоящий сайт с реальным
чекаутом, а не только Telegram-бота. Теперь на сайте — полный набор функций,
как и в боте: eSIM, лаунж/туры через чат, поддержка. Всё на том же бэкенде
(Order, Payment, Conversation, esimaccess) — просто ещё один "фронтенд" поверх
него, со своим email/паролем вместо Telegram-идентичности.

Регистрация ОБЯЗАТЕЛЬНА для покупки и для чата — без аккаунта можно только
смотреть каталог и лендинг. Есть восстановление пароля по email (см.
app/webapp/shop_email.py — если SMTP не настроен, ссылка на сброс дублируется
в бот поддержки, чтобы можно было тестировать).
"""
import secrets
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.config import settings
from app.database.db import get_session
from app.database.models import (
    Category, Conversation, ConversationMessage, ConversationStatus, Favorite, Order, OrderStatus,
    Package, Payment, PaymentProvider, PaymentStatus, Product, Review, TopUp, WebsiteAccount,
)
from app.rate_limit import is_blocked, register_failure, reset as reset_rate_limit
from app.services.payments import idram
from app.services.payments.oxapay import oxapay_client, OxaPayError
from app.webapp.notify_bots import support_notify_bot
from app.webapp.payments import _fulfill_order, REFERRAL_BONUS_PERCENT
from app.webapp.shop_auth import get_current_account, hash_password, verify_password
from app.webapp.shop_email import send_email
from app.webapp.shop_i18n import get_lang, t as translate

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "shop_templates")


def _country_flag(code: str) -> str:
    """
    ISO-код страны → эмодзи-флаг. Никаких картинок — это просто два Unicode-символа
    "regional indicator" (буква A = U+1F1E6, и так далее по алфавиту), которые
    современные шрифты сами рисуют как флаг. Бесплатно, без вопросов лицензии,
    в отличие от настоящих фотографий.
    """
    code = (code or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return "🌐"
    return "".join(chr(0x1F1E6 + ord(ch) - ord("A")) for ch in code)


def _country_hue(code: str) -> int:
    """Стабильный (для одной и той же страны — всегда одинаковый) цветовой тон,
    чтобы у карточек стран были разные, но воспроизводимые градиенты — в диапазоне
    фирменной гаммы (голубой-синий-фиолетовый, между --accent-gradient концами),
    а не по всему спектру, чтобы не выбиваться из премиальной палитры KaLine."""
    return 190 + sum(ord(c) for c in (code or "")) * 37 % 100  # 190..290: cyan → blue → purple


templates.env.filters["flag"] = _country_flag
templates.env.filters["hue"] = _country_hue


def _safe_next(next_url: str) -> str:
    """
    `next` приходит от клиента (query/form параметр) — если использовать его как
    есть в редиректе, можно получить open redirect (напр. next=https://evil.com,
    и после логина человека уносит на фишинговый сайт). Разрешаем только
    относительные пути внутри нашего же сайта.
    """
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return "/shop/"

STATUS_KEYS = {
    OrderStatus.PENDING_PAYMENT: "status_pending_payment",
    OrderStatus.PAID: "status_paid",
    OrderStatus.PROVISIONING: "status_provisioning",
    OrderStatus.ACTIVE: "status_active",
    OrderStatus.FAILED: "status_failed",
    OrderStatus.REFUNDED: "status_refunded",
}

RESET_TOKEN_TTL = timedelta(hours=2)
VERIFICATION_TOKEN_TTL = timedelta(hours=48)


async def render(request: Request, template_name: str, **context):
    """Общий рендер: добавляет lang/t()/account во все страницы сайта разом."""
    lang = get_lang(request)
    account = await get_current_account(request)
    context.update({
        "request": request,
        "lang": lang,
        "t": lambda key: translate(key, lang),
        "account": account,
    })
    return templates.TemplateResponse(template_name, context)


def require_login_redirect(request: Request) -> RedirectResponse:
    return RedirectResponse(url=f"/shop/login?next={request.url.path}", status_code=302)


@router.get("/shop/set-lang/{lang}")
async def set_lang(lang: str, next: str = "/shop/"):
    if lang not in ("ru", "hy", "en"):
        lang = "ru"
    response = RedirectResponse(url=_safe_next(next), status_code=302)
    response.set_cookie("site_lang", lang, max_age=60 * 60 * 24 * 365)
    return response


# --- Витрина: eSIM ---

@router.get("/shop/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    return await render(request, "privacy.html")


@router.get("/shop/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    return await render(request, "terms.html")


@router.get("/shop/", response_class=HTMLResponse)
async def shop_home(request: Request):
    async with get_session() as session:
        result = await session.execute(
            select(Package.country_code, Package.country_name)
            .where(Package.is_active.is_(True))
            .distinct()
            .order_by(Package.country_name)
        )
        countries = result.all()

    return await render(
        request, "home.html", countries=[{"code": c, "name": n} for c, n in countries]
    )


@router.get("/shop/catalog", response_class=HTMLResponse)
async def shop_catalog(request: Request):
    async with get_session() as session:
        result = await session.execute(
            select(Package.country_code, Package.country_name)
            .where(Package.is_active.is_(True))
            .distinct()
            .order_by(Package.country_name)
        )
        countries = result.all()

    return await render(
        request, "catalog.html", countries=[{"code": c, "name": n} for c, n in countries]
    )


@router.get("/shop/country/{country_code}", response_class=HTMLResponse)
async def shop_country(request: Request, country_code: str):
    account = await get_current_account(request)
    async with get_session() as session:
        result = await session.execute(
            select(Package).where(Package.country_code == country_code, Package.is_active.is_(True))
        )
        packages = list(result.scalars())

        reviews = list((
            await session.execute(select(Review).where(Review.country_code == country_code))
        ).scalars())
        review_count = len(reviews)
        avg_rating = round(sum(r.rating for r in reviews) / review_count, 1) if review_count else None

        is_favorite = False
        if account is not None:
            fav = (
                await session.execute(
                    select(Favorite).where(Favorite.website_account_id == account.id, Favorite.country_code == country_code)
                )
            ).scalar_one_or_none()
            is_favorite = fav is not None

    if not packages:
        raise HTTPException(status_code=404, detail="Пакеты для этой страны не найдены")

    return await render(
        request, "packages.html", packages=packages, country_name=packages[0].country_name,
        country_code=country_code, avg_rating=avg_rating, review_count=review_count, is_favorite=is_favorite,
    )


@router.get("/shop/checkout/{package_id}", response_class=HTMLResponse)
async def shop_checkout_form(request: Request, package_id: int):
    account = await get_current_account(request)
    if account is None:
        return require_login_redirect(request)

    async with get_session() as session:
        package = await session.get(Package, package_id)
        if package is None:
            raise HTTPException(status_code=404, detail="Пакет не найден")
        db_account = await session.get(WebsiteAccount, account.id)

    return await render(
        request, "checkout.html", package=package, error=None,
        test_payment_enabled=settings.ENABLE_TEST_PAYMENT,
        oxapay_enabled=settings.ENABLE_OXAPAY,
        balance=db_account.balance,
        can_pay_from_balance=float(db_account.balance) >= float(package.sell_price),
    )


@router.post("/shop/checkout/{package_id}", response_class=HTMLResponse)
async def shop_checkout_submit(request: Request, package_id: int, method: str = Form(...)):
    account = await get_current_account(request)
    if account is None:
        return require_login_redirect(request)

    if method not in ("idram", "oxapay", "test", "balance"):
        raise HTTPException(status_code=400, detail="Неизвестный способ оплаты")
    if method == "test" and not settings.ENABLE_TEST_PAYMENT:
        # Проверка и на сервере, не только скрытая кнопка в интерфейсе — на случай
        # прямого обращения к этому адресу в обход формы.
        raise HTTPException(status_code=403, detail="Тестовая оплата отключена")
    if method == "oxapay" and not settings.ENABLE_OXAPAY:
        raise HTTPException(status_code=403, detail="Оплата через OxaPay временно недоступна")

    async with get_session() as session:
        package = await session.get(Package, package_id)
        if package is None:
            raise HTTPException(status_code=404, detail="Пакет не найден")

        if method == "balance":
            db_account = await session.get(WebsiteAccount, account.id)
            if db_account.balance < float(package.sell_price):
                return await render(
                    request, "checkout.html", package=package,
                    error="На балансе недостаточно средств — пополни его в «Мой баланс».",
                    test_payment_enabled=settings.ENABLE_TEST_PAYMENT,
                    oxapay_enabled=settings.ENABLE_OXAPAY, balance=db_account.balance,
                    can_pay_from_balance=False,
                )

        order = Order(
            user_id=None,
            package_id=package.id,
            status=OrderStatus.PENDING_PAYMENT,
            price_charged=package.sell_price,
            currency=package.currency,
            email=account.email,
            guest_token=uuid.uuid4().hex,
            website_account_id=account.id,
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

        external_id = str(uuid.uuid4())
        provider = {
            "idram": PaymentProvider.IDRAM,
            "oxapay": PaymentProvider.OXAPAY,
            "test": PaymentProvider.TEST,
            "balance": PaymentProvider.BALANCE,
        }[method]
        payment = Payment(
            order_id=order.id,
            provider=provider,
            status=PaymentStatus.PENDING,
            amount=order.price_charged,
            currency=order.currency,
            external_payment_id=external_id,
        )

        if method == "idram":
            session.add(payment)
            await session.commit()
            redirect_url = f"/pay/idram/{external_id}"
        elif method == "oxapay":
            try:
                invoice = await oxapay_client.create_invoice(
                    amount=float(order.price_charged),
                    currency=order.currency,
                    order_id=external_id,
                    description=f"Заказ №{order.id}",
                    callback_url=f"{settings.PUBLIC_BASE_URL}/webhooks/oxapay",
                    return_url=f"{settings.PUBLIC_BASE_URL}/shop/order/{order.guest_token}",
                )
            except OxaPayError as exc:
                current_balance = (await session.get(WebsiteAccount, account.id)).balance
                return await render(
                    request, "checkout.html", package=package,
                    error=f"Платёжная система временно недоступна: {exc}",
                    test_payment_enabled=settings.ENABLE_TEST_PAYMENT,
                    oxapay_enabled=settings.ENABLE_OXAPAY, balance=current_balance,
                    can_pay_from_balance=float(current_balance) >= float(package.sell_price),
                )
            payment.provider_order_id = invoice["track_id"]
            payment.pay_link = invoice["payment_url"]
            session.add(payment)
            await session.commit()
            redirect_url = invoice["payment_url"]
        elif method == "balance":
            db_account = await session.get(WebsiteAccount, account.id)
            db_account.balance = round(db_account.balance - float(order.price_charged), 2)
            payment.status = PaymentStatus.PAID
            session.add(payment)
            order.status = OrderStatus.PAID
            await session.commit()
            await _fulfill_order(session, order)
            redirect_url = f"/shop/order/{order.guest_token}"
        else:  # test — уже проверили выше, что settings.ENABLE_TEST_PAYMENT включён
            payment.status = PaymentStatus.PAID
            session.add(payment)
            order.status = OrderStatus.PAID
            await session.commit()
            await _fulfill_order(session, order)
            redirect_url = f"/shop/order/{order.guest_token}"

    return RedirectResponse(url=redirect_url, status_code=303)


@router.get("/shop/order/{guest_token}", response_class=HTMLResponse)
async def shop_order_status(request: Request, guest_token: str):
    account = await get_current_account(request)
    if account is None:
        return require_login_redirect(request)

    async with get_session() as session:
        result = await session.execute(select(Order).where(Order.guest_token == guest_token))
        order = result.scalar_one_or_none()
        if order is None or order.website_account_id != account.id:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        await session.refresh(order, attribute_names=["package"])

        if order.status == OrderStatus.PAID and order.esimaccess_order_no is None:
            await _fulfill_order(session, order)
            await session.refresh(order)

    still_waiting = order.status in (OrderStatus.PENDING_PAYMENT, OrderStatus.PAID, OrderStatus.PROVISIONING)

    existing_review = None
    if order.status == OrderStatus.ACTIVE:
        async with get_session() as session:
            existing_review = (
                await session.execute(select(Review).where(Review.order_id == order.id))
            ).scalar_one_or_none()

    return await render(
        request, "order_status.html",
        order=order, status_key=STATUS_KEYS[order.status], still_waiting=still_waiting,
        existing_review=existing_review,
    )


# --- Другие услуги (лаунж/туры) — через чат, как в Mini App ---

@router.get("/shop/services", response_class=HTMLResponse)
async def shop_services(request: Request):
    async with get_session() as session:
        result = await session.execute(
            select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order, Category.id)
        )
        categories = list(result.scalars())

    lang = get_lang(request)
    return await render(
        request, "services.html",
        categories=[{"slug": c.slug, "icon": c.icon, "title": c.title(lang), "subtitle": c.subtitle(lang)} for c in categories],
    )


@router.get("/shop/services/{slug}", response_class=HTMLResponse)
async def shop_service_products(request: Request, slug: str):
    lang = get_lang(request)
    account = await get_current_account(request)
    async with get_session() as session:
        category = (await session.execute(select(Category).where(Category.slug == slug))).scalar_one_or_none()
        if category is None:
            raise HTTPException(status_code=404, detail="Категория не найдена")
        products = list(
            (await session.execute(
                select(Product).where(Product.category_id == category.id, Product.is_active.is_(True))
            )).scalars()
        )

    return await render(
        request, "service_products.html",
        category_id=category.id,
        category_slug=slug,
        category_title=category.title(lang),
        logged_in=account is not None,
        products=[
            {"id": p.id, "title": p.title(lang), "description": p.description(lang),
             "price": float(p.price) if p.price is not None else None, "currency": p.currency}
            for p in products
        ],
    )


async def _notify_admin_new_message(client_label: str, topic_label: str, preview: str) -> None:
    try:
        await support_notify_bot.send_message(
            chat_id=settings.SUPPORT_CHAT_ID,
            text=f"🆕 Новое сообщение (сайт)\nОт: {client_label}\nТема: {topic_label}\n\n{preview}",
        )
    except Exception:
        pass


@router.post("/shop/chat/start")
async def start_chat(request: Request, category_id: str = Form(""), product_id: str = Form("")):
    account = await get_current_account(request)
    if account is None:
        return require_login_redirect(request)

    cat_id = int(category_id) if category_id else None
    prod_id = int(product_id) if product_id else None

    async with get_session() as session:
        query = select(Conversation).where(
            Conversation.website_account_id == account.id,
            Conversation.category_id == cat_id,
            Conversation.product_id == prod_id,
            Conversation.status == ConversationStatus.OPEN,
        )
        existing = (await session.execute(query)).scalar_one_or_none()
        if existing:
            return RedirectResponse(url=f"/shop/chat/{existing.id}", status_code=302)

        conversation = Conversation(
            website_account_id=account.id,
            category_id=cat_id,
            product_id=prod_id,
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)
        conversation_id = conversation.id

    return RedirectResponse(url=f"/shop/chat/{conversation_id}", status_code=302)


@router.get("/shop/chat/{conversation_id}", response_class=HTMLResponse)
async def chat_page(request: Request, conversation_id: int):
    account = await get_current_account(request)
    if account is None:
        return require_login_redirect(request)

    lang = get_lang(request)
    async with get_session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None or conversation.website_account_id != account.id:
            raise HTTPException(status_code=404, detail="Чат не найден")

        topic_label = translate("topic_support", lang)
        if conversation.category_id:
            category = await session.get(Category, conversation.category_id)
            if category:
                topic_label = category.title(lang)

    return await render(request, "chat.html", conversation_id=conversation_id, topic_label=topic_label)


@router.get("/shop/api/chat/{conversation_id}/messages")
async def chat_messages(request: Request, conversation_id: int):
    account = await get_current_account(request)
    if account is None:
        raise HTTPException(status_code=401, detail="Войдите в аккаунт")

    async with get_session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None or conversation.website_account_id != account.id:
            raise HTTPException(status_code=404, detail="Чат не найден")
        await session.refresh(conversation, attribute_names=["messages"])

    return [
        {
            "direction": m.direction, "text": m.text,
            "attachment_url": m.attachment_url, "attachment_type": m.attachment_type,
            "attachment_filename": m.attachment_filename, "created_at": m.created_at.isoformat(),
        }
        for m in conversation.messages
    ]


@router.post("/shop/api/chat/{conversation_id}/messages")
async def chat_send(request: Request, conversation_id: int, text: str = Form(...)):
    account = await get_current_account(request)
    if account is None:
        raise HTTPException(status_code=401, detail="Войдите в аккаунт")

    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Пустое сообщение")

    async with get_session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None or conversation.website_account_id != account.id:
            raise HTTPException(status_code=404, detail="Чат не найден")

        session.add(ConversationMessage(conversation_id=conversation.id, direction="in", text=text))
        conversation.last_message_preview = text[:255]
        conversation.unread_by_admin = True
        conversation.status = ConversationStatus.OPEN
        await session.commit()

        topic_label = "Поддержка"
        if conversation.category_id:
            category = await session.get(Category, conversation.category_id)
            if category:
                topic_label = category.title_ru

    await _notify_admin_new_message(account.email, topic_label, text)
    return {"ok": True}


@router.get("/shop/account/chats", response_class=HTMLResponse)
async def my_chats(request: Request):
    account = await get_current_account(request)
    if account is None:
        return require_login_redirect(request)

    lang = get_lang(request)
    async with get_session() as session:
        result = await session.execute(
            select(Conversation)
            .where(Conversation.website_account_id == account.id)
            .order_by(Conversation.updated_at.desc())
        )
        conversations = list(result.scalars())

        items = []
        for c in conversations:
            topic_label = translate("topic_support", lang)
            if c.category_id:
                category = await session.get(Category, c.category_id)
                if category:
                    topic_label = category.title(lang)
            items.append({"id": c.id, "topic_label": topic_label, "last_message_preview": c.last_message_preview})

    return await render(request, "account_chats.html", chats=items)


# --- Аккаунт: регистрация / вход / выход / сброс пароля ---

async def _send_verification_email(session, account: WebsiteAccount) -> None:
    token = secrets.token_urlsafe(32)
    account.verification_token = token
    account.verification_sent_at = datetime.utcnow()
    await session.commit()

    verify_link = f"{settings.PUBLIC_BASE_URL}/shop/verify-email/{token}"
    sent = send_email(
        to=account.email, subject="Подтверди email — eSIM Store",
        body=f"Перейди по ссылке, чтобы подтвердить email и получить доступ к покупкам и чатам "
             f"(ссылка действует 48 часов):\n{verify_link}",
    )
    if not sent:
        # SMTP ещё не настроен — дублируем ссылку в бот поддержки, чтобы можно было тестировать.
        try:
            await support_notify_bot.send_message(
                chat_id=settings.SUPPORT_CHAT_ID,
                text=f"✉️ Подтверждение email\nEmail: {account.email}\n"
                     f"Ссылка (SMTP не настроен, письмо не отправлено): {verify_link}",
            )
        except Exception:
            pass


@router.get("/shop/register", response_class=HTMLResponse)
async def register_form(request: Request, next: str = "/shop/", ref: str = ""):
    return await render(request, "register.html", error=None, next=next, ref=ref)


@router.post("/shop/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    next: str = Form("/shop/"),
    agree: bool = Form(False),
    ref: str = Form(""),
):
    email = email.strip().lower()
    if not agree:
        return await render(request, "register.html", error="Нужно согласиться с условиями использования.", next=next, ref=ref)
    if "@" not in email or "." not in email:
        return await render(request, "register.html", error="Введите настоящий email.", next=next, ref=ref)
    if len(password) < 8:
        return await render(request, "register.html", error="Пароль должен быть не короче 8 символов.", next=next, ref=ref)
    if password != password_confirm:
        return await render(request, "register.html", error="Пароли не совпадают.", next=next, ref=ref)

    async with get_session() as session:
        existing = (await session.execute(select(WebsiteAccount).where(WebsiteAccount.email == email))).scalar_one_or_none()
        if existing is not None:
            return await render(request, "register.html", error="Аккаунт с таким email уже существует.", next=next, ref=ref)

        referred_by_id = None
        if ref:
            referrer = (
                await session.execute(select(WebsiteAccount).where(WebsiteAccount.referral_code == ref))
            ).scalar_one_or_none()
            if referrer is not None:
                referred_by_id = referrer.id

        account = WebsiteAccount(
            email=email,
            password_hash=hash_password(password),
            referral_code=secrets.token_urlsafe(6),
            referred_by_id=referred_by_id,
        )
        session.add(account)
        await session.commit()
        await session.refresh(account)

        await _send_verification_email(session, account)

    # Сессию НЕ выдаём — сначала нужно подтвердить email по ссылке из письма.
    return await render(request, "check_email.html", email=email, next=next)


@router.post("/shop/resend-verification", response_class=HTMLResponse)
async def resend_verification(request: Request, email: str = Form(...), next: str = Form("/shop/")):
    email = email.strip().lower()
    rate_key = f"{request.client.host}:{email}:verify"

    if not is_blocked(rate_key):
        register_failure(rate_key)  # используем как счётчик отправок, не только неудач
        async with get_session() as session:
            account = (await session.execute(select(WebsiteAccount).where(WebsiteAccount.email == email))).scalar_one_or_none()
            if account is not None and not account.is_verified:
                await _send_verification_email(session, account)

    # Один и тот же ответ независимо от результата — не раскрываем, существует ли email.
    return await render(request, "check_email.html", email=email, next=next)


@router.get("/shop/verify-email/{token}", response_class=HTMLResponse)
async def verify_email(request: Request, token: str):
    async with get_session() as session:
        account = (
            await session.execute(select(WebsiteAccount).where(WebsiteAccount.verification_token == token))
        ).scalar_one_or_none()

        if account is None:
            return await render(request, "verify_email_result.html", success=False, expired=False)

        if account.is_verified:
            # Уже подтверждено — сюда попадаем, когда по ссылке кто-то переходит повторно.
            # Это нормально и ожидаемо: пока не настроен SMTP, ссылка приходит обычным
            # сообщением в Telegram, а Telegram сам иногда переходит по ссылкам в
            # сообщениях, чтобы сделать превью — то есть настоящий клик человека может
            # оказаться уже вторым по счёту. Раньше здесь стирался токен после первого
            # перехода, и настоящий клик после превью-бота показывал ложную ошибку.
            request.session["account_id"] = account.id
            return await render(request, "verify_email_result.html", success=True, expired=False)

        if account.verification_sent_at is None or datetime.utcnow() - account.verification_sent_at > VERIFICATION_TOKEN_TTL:
            return await render(request, "verify_email_result.html", success=False, expired=True, email=account.email)

        account.is_verified = True
        account.verification_sent_at = None
        # Токен намеренно НЕ обнуляем — см. комментарий выше про повторные переходы.
        await session.commit()
        account_id = account.id

    # Подтвердил email — сразу и логиним, лишний раз вводить пароль не нужно.
    request.session["account_id"] = account_id
    return await render(request, "verify_email_result.html", success=True, expired=False)


@router.get("/shop/login", response_class=HTMLResponse)
async def login_form(request: Request, next: str = "/shop/"):
    return await render(request, "login.html", error=None, next=next)


@router.post("/shop/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...), next: str = Form("/shop/")):
    email = email.strip().lower()
    rate_key = f"{request.client.host}:{email}"

    if is_blocked(rate_key):
        return await render(
            request, "login.html", error="Слишком много попыток — подожди несколько минут и попробуй снова.", next=next,
        )

    async with get_session() as session:
        account = (await session.execute(select(WebsiteAccount).where(WebsiteAccount.email == email))).scalar_one_or_none()

    if account is None or not verify_password(password, account.password_hash):
        register_failure(rate_key)
        return await render(request, "login.html", error="Неверный email или пароль.", next=next)

    if not account.is_verified:
        return await render(
            request, "login.html",
            error="Email ещё не подтверждён — проверь почту (или запроси письмо ещё раз).",
            next=next, unverified_email=email,
        )

    reset_rate_limit(rate_key)
    request.session["account_id"] = account.id
    return RedirectResponse(url=_safe_next(next), status_code=302)


@router.get("/shop/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/shop/", status_code=302)


@router.get("/shop/forgot-password", response_class=HTMLResponse)
async def forgot_password_form(request: Request):
    return await render(request, "forgot_password.html", error=None, sent=False)


@router.post("/shop/forgot-password", response_class=HTMLResponse)
async def forgot_password_submit(request: Request, email: str = Form(...)):
    email = email.strip().lower()
    rate_key = f"{request.client.host}:{email}:reset"

    if is_blocked(rate_key):
        # Тот же самый ответ, что и в обычном случае — не выдаём, что сработал лимит,
        # иначе это тоже способ проверить, существует ли такой email в базе.
        return await render(request, "forgot_password.html", error=None, sent=True)
    register_failure(rate_key)  # считаем каждый запрос как "попытку", не только неудачную

    async with get_session() as session:
        account = (await session.execute(select(WebsiteAccount).where(WebsiteAccount.email == email))).scalar_one_or_none()
        if account is not None:
            token = secrets.token_urlsafe(32)
            account.password_reset_token = token
            account.password_reset_expires = datetime.utcnow() + RESET_TOKEN_TTL
            await session.commit()

            reset_link = f"{settings.PUBLIC_BASE_URL}/shop/reset-password/{token}"
            sent = send_email(
                to=email, subject="Восстановление пароля — eSIM Store",
                body=f"Перейдите по ссылке, чтобы задать новый пароль (ссылка действует 2 часа):\n{reset_link}",
            )
            if not sent:
                # SMTP ещё не настроен — дублируем ссылку в бот поддержки, чтобы можно было тестировать.
                try:
                    await support_notify_bot.send_message(
                        chat_id=settings.SUPPORT_CHAT_ID,
                        text=f"🔑 Запрос сброса пароля\nEmail: {email}\nСсылка (SMTP не настроен, письмо не отправлено): {reset_link}",
                    )
                except Exception:
                    pass

    # Одинаковый ответ независимо от того, найден ли email — чтобы не раскрывать,
    # какие адреса зарегистрированы.
    return await render(request, "forgot_password.html", error=None, sent=True)


@router.get("/shop/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str):
    async with get_session() as session:
        account = (await session.execute(select(WebsiteAccount).where(WebsiteAccount.password_reset_token == token))).scalar_one_or_none()

    valid = account is not None and account.password_reset_expires and account.password_reset_expires > datetime.utcnow()
    return await render(request, "reset_password.html", token=token, valid=valid, error=None)


@router.post("/shop/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_submit(request: Request, token: str, password: str = Form(...)):
    async with get_session() as session:
        account = (await session.execute(select(WebsiteAccount).where(WebsiteAccount.password_reset_token == token))).scalar_one_or_none()
        valid = account is not None and account.password_reset_expires and account.password_reset_expires > datetime.utcnow()

        if not valid:
            return await render(request, "reset_password.html", token=token, valid=False, error=None)

        if len(password) < 8:
            return await render(request, "reset_password.html", token=token, valid=True, error="Пароль должен быть не короче 8 символов.")

        account.password_hash = hash_password(password)
        account.password_reset_token = None
        account.password_reset_expires = None
        await session.commit()

    return RedirectResponse(url="/shop/login", status_code=302)


@router.get("/shop/account/orders", response_class=HTMLResponse)
async def my_orders(request: Request):
    account = await get_current_account(request)
    if account is None:
        return require_login_redirect(request)

    async with get_session() as session:
        result = await session.execute(
            select(Order).where(Order.website_account_id == account.id).order_by(Order.created_at.desc())
        )
        orders = list(result.scalars())
        for o in orders:
            await session.refresh(o, attribute_names=["package"])

    return await render(request, "account_orders.html", orders=orders, status_keys=STATUS_KEYS)


@router.get("/shop/account/settings", response_class=HTMLResponse)
async def account_settings(request: Request):
    account = await get_current_account(request)
    if account is None:
        return require_login_redirect(request)
    return await render(request, "account_settings.html", error=None, success=False)


@router.post("/shop/account/settings", response_class=HTMLResponse)
async def account_settings_submit(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
):
    account = await get_current_account(request)
    if account is None:
        return require_login_redirect(request)

    if not verify_password(current_password, account.password_hash):
        return await render(request, "account_settings.html", error="settings_password_wrong_current", success=False)
    if new_password != new_password_confirm:
        return await render(request, "account_settings.html", error="settings_password_mismatch", success=False)
    if len(new_password) < 8:
        return await render(request, "account_settings.html", error="password_too_short", success=False)

    async with get_session() as session:
        db_account = await session.get(WebsiteAccount, account.id)
        db_account.password_hash = hash_password(new_password)
        await session.commit()

    return await render(request, "account_settings.html", error=None, success=True)


# --- Баланс, пополнение, реферальная программа ---

@router.get("/shop/account/balance", response_class=HTMLResponse)
async def account_balance(request: Request):
    account = await get_current_account(request)
    if account is None:
        return require_login_redirect(request)

    async with get_session() as session:
        db_account = await session.get(WebsiteAccount, account.id)
        top_ups = list((
            await session.execute(
                select(TopUp).where(TopUp.website_account_id == account.id).order_by(TopUp.created_at.desc()).limit(20)
            )
        ).scalars())

    referral_link = f"{settings.PUBLIC_BASE_URL}/shop/register?ref={db_account.referral_code}"
    return await render(
        request, "account_balance.html",
        balance=db_account.balance, top_ups=top_ups, referral_link=referral_link,
        referral_percent=REFERRAL_BONUS_PERCENT, error=None,
    )


@router.post("/shop/account/balance/topup", response_class=HTMLResponse)
async def account_balance_topup(request: Request, amount: str = Form(...), method: str = Form(...)):
    account = await get_current_account(request)
    if account is None:
        return require_login_redirect(request)

    try:
        amount_value = round(float(amount), 2)
    except ValueError:
        amount_value = 0
    if amount_value < 1:
        return await render(
            request, "account_balance.html", balance=account.balance, top_ups=[],
            referral_link=f"{settings.PUBLIC_BASE_URL}/shop/register?ref={account.referral_code}",
            referral_percent=REFERRAL_BONUS_PERCENT, error="Минимальная сумма пополнения — $1.",
        )
    if method not in ("idram", "oxapay"):
        raise HTTPException(status_code=400, detail="Неизвестный способ оплаты")
    if method == "oxapay" and not settings.ENABLE_OXAPAY:
        raise HTTPException(status_code=403, detail="Оплата через OxaPay временно недоступна")

    external_id = str(uuid.uuid4())
    async with get_session() as session:
        top_up = TopUp(
            website_account_id=account.id, amount=amount_value, currency="USD",
            provider=PaymentProvider.IDRAM if method == "idram" else PaymentProvider.OXAPAY,
            status=PaymentStatus.PENDING, external_payment_id=external_id,
        )

        if method == "idram":
            session.add(top_up)
            await session.commit()
            redirect_url = f"/pay/idram/{external_id}"
        else:
            try:
                invoice = await oxapay_client.create_invoice(
                    amount=amount_value, currency="USD", order_id=external_id,
                    description="Пополнение баланса",
                    callback_url=f"{settings.PUBLIC_BASE_URL}/webhooks/oxapay",
                    return_url=f"{settings.PUBLIC_BASE_URL}/shop/account/balance",
                )
            except OxaPayError as exc:
                return await render(
                    request, "account_balance.html", balance=account.balance, top_ups=[],
                    referral_link=f"{settings.PUBLIC_BASE_URL}/shop/register?ref={account.referral_code}",
                    referral_percent=REFERRAL_BONUS_PERCENT,
                    error=f"Платёжная система временно недоступна: {exc}",
                )
            top_up.provider_order_id = invoice["track_id"]
            top_up.pay_link = invoice["payment_url"]
            session.add(top_up)
            await session.commit()
            redirect_url = invoice["payment_url"]

    return RedirectResponse(url=redirect_url, status_code=303)


# --- Избранное ---

@router.post("/shop/favorites/toggle")
async def toggle_favorite(request: Request, country_code: str = Form(...)):
    account = await get_current_account(request)
    if account is None:
        return require_login_redirect(request)

    async with get_session() as session:
        existing = (
            await session.execute(
                select(Favorite).where(Favorite.website_account_id == account.id, Favorite.country_code == country_code)
            )
        ).scalar_one_or_none()
        if existing is not None:
            await session.delete(existing)
        else:
            session.add(Favorite(website_account_id=account.id, country_code=country_code))
        await session.commit()

    referer = request.headers.get("referer", "/shop/catalog")
    return RedirectResponse(url=referer, status_code=302)


# --- Отзывы ---

@router.post("/shop/order/{guest_token}/review")
async def submit_review(request: Request, guest_token: str, rating: int = Form(...), comment: str = Form("")):
    account = await get_current_account(request)
    if account is None:
        return require_login_redirect(request)
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Оценка должна быть от 1 до 5")

    async with get_session() as session:
        order = (await session.execute(select(Order).where(Order.guest_token == guest_token))).scalar_one_or_none()
        if order is None or order.website_account_id != account.id:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        if order.status != OrderStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Отзыв можно оставить только на активированный eSIM")

        existing = (await session.execute(select(Review).where(Review.order_id == order.id))).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=400, detail="Отзыв на этот заказ уже оставлен")

        await session.refresh(order, attribute_names=["package"])
        session.add(Review(
            website_account_id=account.id, order_id=order.id,
            country_code=order.package.country_code, rating=rating, comment=comment.strip() or None,
        ))
        await session.commit()

    return RedirectResponse(url=f"/shop/order/{guest_token}", status_code=302)


@router.get("/shop/api/favorites")
async def api_favorites(request: Request):
    account = await get_current_account(request)
    if account is None:
        return {"codes": []}
    async with get_session() as session:
        favs = list((
            await session.execute(select(Favorite.country_code).where(Favorite.website_account_id == account.id))
        ).scalars())
    return {"codes": favs}
