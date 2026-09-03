"""
Отдельная веб-админка для просмотра заказов и оформления возвратов.
Запуск отдельно от ботов: uvicorn app.admin_panel.app:app --port 8000

Рассчитана на одного администратора (тебя) — поэтому авторизация простая:
логин/пароль из .env + сессионная cookie, без ролей и регистрации.
"""
from pathlib import Path

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import select

from app.config import settings
from app.database.db import get_session, init_db
from app.database.models import Category, Order, OrderStatus, Package, Product, User
from app.rate_limit import is_blocked, register_failure, reset as reset_rate_limit
from app.services.esimaccess import esimaccess_client, ESimAccessError
from app.webapp.payments import _fulfill_order

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="eSIM Store — Админка",
    docs_url=None if settings.SECURE_COOKIES else "/docs",
    redoc_url=None if settings.SECURE_COOKIES else "/redoc",
    openapi_url=None if settings.SECURE_COOKIES else "/openapi.json",
)


@app.on_event("startup")
async def on_startup():
    # Та же логика, что и в app/webapp/app.py — таблицы должны быть готовы
    # независимо от того, какой из трёх сервисов Railway стартовал первым.
    await init_db()


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.ADMIN_PANEL_SECRET_KEY,
    https_only=settings.SECURE_COOKIES,
    same_site="lax",
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    # Админка никогда никуда не встраивается — можно закрывать без исключений.
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    return response


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# (label, число закрашенных "делений сигнала" из 4, css-класс цвета) — используется в таблице заказов
STATUS_META = {
    OrderStatus.PENDING_PAYMENT: ("Ждёт оплаты", 1, "amber"),
    OrderStatus.PAID: ("Оплачен", 2, "blue"),
    OrderStatus.PROVISIONING: ("Оформляется", 3, "blue"),
    OrderStatus.ACTIVE: ("Активен", 4, "green"),
    OrderStatus.FAILED: ("Ошибка", 0, "red"),
    OrderStatus.REFUNDED: ("Возврат", 0, "red"),
}
templates.env.globals["STATUS_META"] = STATUS_META


def require_login(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=303, headers={"Location": "/login"})


@app.exception_handler(HTTPException)
async def redirect_to_login(request: Request, exc: HTTPException):
    if exc.status_code == 303:
        return RedirectResponse(url="/login")
    raise exc


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login")
async def login_submit(request: Request, login: str = Form(...), password: str = Form(...)):
    rate_key = f"{request.client.host}:{login}"
    if is_blocked(rate_key):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Слишком много попыток — подожди несколько минут."}
        )

    if login == settings.ADMIN_PANEL_LOGIN and password == settings.ADMIN_PANEL_PASSWORD:
        reset_rate_limit(rate_key)
        request.session["authenticated"] = True
        return RedirectResponse(url="/orders", status_code=302)

    register_failure(rate_key)
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Неверный логин или пароль"}
    )


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")


@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/orders")


@app.get("/orders", response_class=HTMLResponse)
async def orders_list(request: Request, status: str | None = None, _=Depends(require_login)):
    async with get_session() as session:
        query = select(Order).order_by(Order.created_at.desc())
        if status:
            query = query.where(Order.status == status)
        result = await session.execute(query)
        orders = list(result.scalars())
        for order in orders:
            await session.refresh(order, attribute_names=["user", "package"])

    return templates.TemplateResponse(
        "orders_list.html",
        {
            "request": request,
            "orders": orders,
            "statuses": list(OrderStatus),
            "current_status": status,
        },
    )


@app.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_detail(request: Request, order_id: int, _=Depends(require_login)):
    async with get_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        await session.refresh(order, attribute_names=["user", "package"])

    return templates.TemplateResponse(
        "order_detail.html", {"request": request, "order": order, "statuses": list(OrderStatus)}
    )


@app.post("/orders/{order_id}/refund")
async def refund_order(
    request: Request, order_id: int, reason: str = Form(""), _=Depends(require_login)
):
    async with get_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        order.status = OrderStatus.REFUNDED
        order.refund_reason = reason
        await session.commit()

        # TODO: когда подключится автоматический возврат у платёжного провайдера —
        # здесь же вызвать его API. Пока что у Idram/Wallet Pay/OxaPay это не
        # подтверждено документацией как отдельный однозначный эндпоинт — возврат
        # оформляется вручную в личном кабинете нужного провайдера, а этот статус
        # в первую очередь для твоего учёта и чтобы клиент видел актуальный статус.

    return RedirectResponse(url=f"/orders/{order_id}", status_code=302)


@app.post("/orders/{order_id}/refresh-esimaccess")
async def refresh_from_esimaccess(order_id: int, _=Depends(require_login)):
    """
    Ручной опрос esimaccess по orderNo — их же документация прямо советует так
    делать как запасной путь, если вебхук ORDER_STATUS не настроен или ещё не
    пришёл: "If this event is not received, fall back to polling the query endpoint."
    """
    async with get_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        if not order.esimaccess_order_no:
            raise HTTPException(status_code=400, detail="У заказа ещё нет esimaccess order id")

        try:
            esim_list = await esimaccess_client.query_esim(order_no=order.esimaccess_order_no)
        except ESimAccessError as exc:
            order.refund_reason = f"Ручная проверка: {exc}"
            await session.commit()
            return RedirectResponse(url=f"/orders/{order_id}", status_code=302)

        if esim_list:
            esim = esim_list[0]
            order.iccid = esim.get("iccid")
            order.esimaccess_esim_tran_no = esim.get("esimTranNo")
            order.qr_code_data = esim.get("qrCodeUrl")
            order.activation_instructions = esim.get("ac")
            order.status = OrderStatus.ACTIVE
            await session.commit()

    return RedirectResponse(url=f"/orders/{order_id}", status_code=302)


# telegram_id=0 никогда не встретится у настоящего пользователя Telegram (их ID всегда
# положительные) — используем как служебную метку "это тестовый заказ из админки".
TEST_USER_TELEGRAM_ID = 0


@app.post("/orders/test-order")
async def create_test_order(package_id: int = Form(...), _=Depends(require_login)):
    """
    Симулятор сделки — создаёт заказ, сразу помеченный оплаченным (минуя реальную
    оплату), и по-настоящему отправляет его в esimaccess через тот же самый
    _fulfill_order, что используют настоящие платежи. Это единственный способ
    проверить, что интеграция с esimaccess реально работает (ключ верный, баланс
    достаточный, create_order/query_esim отрабатывают), не разбираясь параллельно
    с оплатой. ВНИМАНИЕ: списывает деньги с твоего реального баланса esimaccess.
    """
    async with get_session() as session:
        package = await session.get(Package, package_id)
        if package is None:
            raise HTTPException(status_code=404, detail="Пакет не найден")

        result = await session.execute(select(User).where(User.telegram_id == TEST_USER_TELEGRAM_ID))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=TEST_USER_TELEGRAM_ID, full_name="Тестовый заказ (админка)")
            session.add(user)
            await session.commit()
            await session.refresh(user)

        order = Order(
            user_id=user.id,
            package_id=package.id,
            status=OrderStatus.PAID,  # сразу "оплачен" — тестируем именно esimaccess, не платёжку
            price_charged=package.sell_price,
            currency=package.currency,
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

        await _fulfill_order(session, order)
        order_id = order.id

    return RedirectResponse(url=f"/orders/{order_id}", status_code=302)


@app.get("/packages", response_class=HTMLResponse)
async def packages_list(request: Request, _=Depends(require_login)):
    async with get_session() as session:
        result = await session.execute(select(Package).order_by(Package.country_name, Package.title))
        packages = list(result.scalars())

    return templates.TemplateResponse(
        "packages_list.html", {"request": request, "packages": packages}
    )


@app.get("/packages/import", response_class=HTMLResponse)
async def package_import_form(request: Request, _=Depends(require_login)):
    return templates.TemplateResponse(
        "package_import_form.html",
        {
            "request": request, "error": None, "imported": None,
            "default_markup": settings.ESIMACCESS_DEFAULT_MARKUP_PERCENT,
        },
    )


@app.post("/packages/import", response_class=HTMLResponse)
async def package_import_submit(
    request: Request,
    country_code: str = Form(...),
    country_name: str = Form(...),
    markup_percent: float = Form(...),
    _=Depends(require_login),
):
    country_code = country_code.strip().upper()
    country_name = country_name.strip()

    try:
        remote_packages = await esimaccess_client.list_packages(location_code=country_code)
    except ESimAccessError as exc:
        return templates.TemplateResponse(
            "package_import_form.html",
            {
                "request": request, "imported": None, "default_markup": markup_percent,
                "error": f"esimaccess ответил ошибкой: {exc}. Путь/формат этого запроса не "
                         f"подтверждён их документацией — возможно, угадан неверно.",
            },
        )
    except Exception as exc:
        return templates.TemplateResponse(
            "package_import_form.html",
            {
                "request": request, "imported": None, "default_markup": markup_percent,
                "error": f"Не удалось получить список пакетов: {exc}",
            },
        )

    created, skipped, updated = 0, 0, 0
    async with get_session() as session:
        for item in remote_packages:
            code = item.get("package_code")
            cost_price = item.get("cost_price")
            if not code or cost_price is None:
                skipped += 1
                continue

            existing = (
                await session.execute(select(Package).where(Package.esimaccess_package_code == code))
            ).scalar_one_or_none()

            sell_price = round(cost_price * (1 + markup_percent / 100), 2)

            if existing is not None:
                existing.cost_price = cost_price
                existing.sell_price = sell_price
                updated += 1
                continue

            package = Package(
                country_code=item.get("country_code") or country_code,
                country_name=country_name,
                title=item.get("title") or code,
                esimaccess_package_code=code,
                data_amount_mb=item.get("data_amount_mb") or 0,
                validity_days=item.get("validity_days") or 0,
                cost_price=cost_price,
                sell_price=sell_price,
                currency="USD",
                is_active=True,
            )
            session.add(package)
            created += 1

        await session.commit()

    return templates.TemplateResponse(
        "package_import_form.html",
        {
            "request": request, "error": None, "default_markup": markup_percent,
            "imported": {"created": created, "updated": updated, "skipped": skipped, "total": len(remote_packages)},
        },
    )


@app.get("/packages/new", response_class=HTMLResponse)
async def package_new_form(request: Request, _=Depends(require_login)):
    return templates.TemplateResponse("package_form.html", {"request": request, "package": None})


@app.post("/packages/new")
async def package_create(
    request: Request,
    country_code: str = Form(...),
    country_name: str = Form(...),
    title: str = Form(...),
    esimaccess_package_code: str = Form(...),
    data_amount_mb: int = Form(...),
    validity_days: int = Form(...),
    cost_price: float = Form(...),
    sell_price: float = Form(...),
    currency: str = Form("USD"),
    is_active: bool = Form(False),
    _=Depends(require_login),
):
    async with get_session() as session:
        package = Package(
            country_code=country_code.strip().upper(),
            country_name=country_name.strip(),
            title=title.strip(),
            esimaccess_package_code=esimaccess_package_code.strip(),
            data_amount_mb=data_amount_mb,
            validity_days=validity_days,
            cost_price=cost_price,
            sell_price=sell_price,
            currency=currency.strip().upper(),
            is_active=is_active,
        )
        session.add(package)
        await session.commit()

    return RedirectResponse(url="/packages", status_code=302)


@app.get("/packages/{package_id}/edit", response_class=HTMLResponse)
async def package_edit_form(request: Request, package_id: int, _=Depends(require_login)):
    async with get_session() as session:
        package = await session.get(Package, package_id)
        if package is None:
            raise HTTPException(status_code=404, detail="Пакет не найден")

    return templates.TemplateResponse(
        "package_form.html", {"request": request, "package": package}
    )


@app.post("/packages/{package_id}/edit")
async def package_update(
    request: Request,
    package_id: int,
    country_code: str = Form(...),
    country_name: str = Form(...),
    title: str = Form(...),
    esimaccess_package_code: str = Form(...),
    data_amount_mb: int = Form(...),
    validity_days: int = Form(...),
    cost_price: float = Form(...),
    sell_price: float = Form(...),
    currency: str = Form("USD"),
    is_active: bool = Form(False),
    _=Depends(require_login),
):
    async with get_session() as session:
        package = await session.get(Package, package_id)
        if package is None:
            raise HTTPException(status_code=404, detail="Пакет не найден")

        package.country_code = country_code.strip().upper()
        package.country_name = country_name.strip()
        package.title = title.strip()
        package.esimaccess_package_code = esimaccess_package_code.strip()
        package.data_amount_mb = data_amount_mb
        package.validity_days = validity_days
        package.cost_price = cost_price
        package.sell_price = sell_price
        package.currency = currency.strip().upper()
        package.is_active = is_active
        await session.commit()

    return RedirectResponse(url="/packages", status_code=302)


@app.post("/packages/{package_id}/delete")
async def package_delete(package_id: int, _=Depends(require_login)):
    async with get_session() as session:
        package = await session.get(Package, package_id)
        if package is None:
            raise HTTPException(status_code=404, detail="Пакет не найден")
        await session.delete(package)
        await session.commit()

    return RedirectResponse(url="/packages", status_code=302)


@app.get("/categories", response_class=HTMLResponse)
async def categories_list(request: Request, _=Depends(require_login)):
    async with get_session() as session:
        result = await session.execute(select(Category).order_by(Category.sort_order, Category.id))
        categories = list(result.scalars())

    return templates.TemplateResponse(
        "categories_list.html", {"request": request, "categories": categories}
    )


@app.get("/categories/new", response_class=HTMLResponse)
async def category_new_form(request: Request, _=Depends(require_login)):
    return templates.TemplateResponse("category_form.html", {"request": request, "category": None})


@app.post("/categories/new")
async def category_create(
    request: Request,
    slug: str = Form(...),
    icon: str = Form("🛍"),
    title_ru: str = Form(...),
    title_hy: str = Form(...),
    title_en: str = Form(...),
    subtitle_ru: str = Form(""),
    subtitle_hy: str = Form(""),
    subtitle_en: str = Form(""),
    sort_order: int = Form(0),
    is_active: bool = Form(False),
    _=Depends(require_login),
):
    async with get_session() as session:
        category = Category(
            slug=slug.strip().lower().replace(" ", "-"),
            icon=icon.strip() or "🛍",
            title_ru=title_ru.strip(),
            title_hy=title_hy.strip(),
            title_en=title_en.strip(),
            subtitle_ru=subtitle_ru.strip() or None,
            subtitle_hy=subtitle_hy.strip() or None,
            subtitle_en=subtitle_en.strip() or None,
            sort_order=sort_order,
            is_active=is_active,
        )
        session.add(category)
        await session.commit()

    return RedirectResponse(url="/categories", status_code=302)


@app.get("/categories/{category_id}/edit", response_class=HTMLResponse)
async def category_edit_form(request: Request, category_id: int, _=Depends(require_login)):
    async with get_session() as session:
        category = await session.get(Category, category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Категория не найдена")

    return templates.TemplateResponse(
        "category_form.html", {"request": request, "category": category}
    )


@app.post("/categories/{category_id}/edit")
async def category_update(
    request: Request,
    category_id: int,
    slug: str = Form(...),
    icon: str = Form("🛍"),
    title_ru: str = Form(...),
    title_hy: str = Form(...),
    title_en: str = Form(...),
    subtitle_ru: str = Form(""),
    subtitle_hy: str = Form(""),
    subtitle_en: str = Form(""),
    sort_order: int = Form(0),
    is_active: bool = Form(False),
    _=Depends(require_login),
):
    async with get_session() as session:
        category = await session.get(Category, category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Категория не найдена")

        category.slug = slug.strip().lower().replace(" ", "-")
        category.icon = icon.strip() or "🛍"
        category.title_ru = title_ru.strip()
        category.title_hy = title_hy.strip()
        category.title_en = title_en.strip()
        category.subtitle_ru = subtitle_ru.strip() or None
        category.subtitle_hy = subtitle_hy.strip() or None
        category.subtitle_en = subtitle_en.strip() or None
        category.sort_order = sort_order
        category.is_active = is_active
        await session.commit()

    return RedirectResponse(url="/categories", status_code=302)


@app.post("/categories/{category_id}/delete")
async def category_delete(category_id: int, _=Depends(require_login)):
    async with get_session() as session:
        category = await session.get(Category, category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Категория не найдена")

        products_count = (
            await session.execute(select(Product).where(Product.category_id == category_id))
        ).scalars().first()
        if products_count is not None:
            return RedirectResponse(url="/categories?error=has_products", status_code=302)

        await session.delete(category)
        await session.commit()

    return RedirectResponse(url="/categories", status_code=302)


@app.get("/products", response_class=HTMLResponse)
async def products_list(request: Request, category_id: int | None = None, _=Depends(require_login)):
    async with get_session() as session:
        query = select(Product).order_by(Product.category_id, Product.title_ru)
        if category_id:
            query = query.where(Product.category_id == category_id)
        result = await session.execute(query)
        products = list(result.scalars())
        for p in products:
            await session.refresh(p, attribute_names=["category"])

        all_categories = list(
            (await session.execute(select(Category).order_by(Category.sort_order, Category.id))).scalars()
        )

    return templates.TemplateResponse(
        "products_list.html",
        {"request": request, "products": products, "categories": all_categories, "current_category_id": category_id},
    )


@app.get("/products/new", response_class=HTMLResponse)
async def product_new_form(request: Request, _=Depends(require_login)):
    async with get_session() as session:
        categories = list(
            (await session.execute(select(Category).order_by(Category.sort_order, Category.id))).scalars()
        )
    if not categories:
        return RedirectResponse(url="/categories?error=need_category_first", status_code=302)

    return templates.TemplateResponse(
        "product_form.html", {"request": request, "product": None, "categories": categories}
    )


@app.post("/products/new")
async def product_create(
    request: Request,
    category_id: int = Form(...),
    title_ru: str = Form(...),
    title_hy: str = Form(...),
    title_en: str = Form(...),
    description_ru: str = Form(""),
    description_hy: str = Form(""),
    description_en: str = Form(""),
    price: str = Form(""),
    currency: str = Form("USD"),
    is_active: bool = Form(False),
    _=Depends(require_login),
):
    async with get_session() as session:
        product = Product(
            category_id=category_id,
            title_ru=title_ru.strip(),
            title_hy=title_hy.strip(),
            title_en=title_en.strip(),
            description_ru=description_ru.strip() or None,
            description_hy=description_hy.strip() or None,
            description_en=description_en.strip() or None,
            price=float(price) if price.strip() else None,
            currency=currency.strip().upper(),
            is_active=is_active,
        )
        session.add(product)
        await session.commit()

    return RedirectResponse(url="/products", status_code=302)


@app.get("/products/{product_id}/edit", response_class=HTMLResponse)
async def product_edit_form(request: Request, product_id: int, _=Depends(require_login)):
    async with get_session() as session:
        product = await session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Товар не найден")
        categories = list(
            (await session.execute(select(Category).order_by(Category.sort_order, Category.id))).scalars()
        )

    return templates.TemplateResponse(
        "product_form.html", {"request": request, "product": product, "categories": categories}
    )


@app.post("/products/{product_id}/edit")
async def product_update(
    request: Request,
    product_id: int,
    category_id: int = Form(...),
    title_ru: str = Form(...),
    title_hy: str = Form(...),
    title_en: str = Form(...),
    description_ru: str = Form(""),
    description_hy: str = Form(""),
    description_en: str = Form(""),
    price: str = Form(""),
    currency: str = Form("USD"),
    is_active: bool = Form(False),
    _=Depends(require_login),
):
    async with get_session() as session:
        product = await session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Товар не найден")

        product.category_id = category_id
        product.title_ru = title_ru.strip()
        product.title_hy = title_hy.strip()
        product.title_en = title_en.strip()
        product.description_ru = description_ru.strip() or None
        product.description_hy = description_hy.strip() or None
        product.description_en = description_en.strip() or None
        product.price = float(price) if price.strip() else None
        product.currency = currency.strip().upper()
        product.is_active = is_active
        await session.commit()

    return RedirectResponse(url="/products", status_code=302)


@app.post("/products/{product_id}/delete")
async def product_delete(product_id: int, _=Depends(require_login)):
    async with get_session() as session:
        product = await session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Товар не найден")
        await session.delete(product)
        await session.commit()

    return RedirectResponse(url="/products", status_code=302)
