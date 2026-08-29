"""
Бэкенд Telegram Mini App. Отдельный процесс от ботов и от админки:
uvicorn app.webapp.app:app --port 8001

Публичный (без пароля), но каждый запрос, изменяющий данные или отдающий
персональные заказы, проверяет подпись initData (см. app/webapp/auth.py) —
поэтому "публичный" не значит "открытый кому угодно": подделать initData
без токена бота невозможно.
"""
from pathlib import Path
import logging
import uuid

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database.db import get_session

logging.basicConfig(level=logging.INFO)
from app.database.models import Package, User, Order, OrderStatus
from app.webapp.auth import get_current_user
from app.webapp import webhooks, payments, products, conversations, admin_chat, shop

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="eSIM Store — Mini App API")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SHOP_SESSION_SECRET_KEY,
    https_only=settings.SECURE_COOKIES,
    same_site="lax",
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """
    Общие защитные заголовки на каждый ответ. Есть один нюанс, из-за которого
    это не сделать одной строкой на всё приложение: Mini App (клиентский и
    инбокс поддержки) ДОЛЖНЫ разрешать встраивание в iframe самим Telegram
    (Telegram Web открывает Mini App именно так) — а вот публичный сайт
    (/shop/*) встраивать в чужие iframe нельзя вообще (защита от clickjacking).
    Поэтому frame-ancestors разный в зависимости от пути.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

    if request.url.path.startswith("/shop"):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    else:
        # Клиентский Mini App и /support-chat — встраивается Telegram Web.
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' https://web.telegram.org https://*.web.telegram.org"
        )
    return response


app.include_router(webhooks.router)
app.include_router(payments.router)
app.include_router(products.router)
app.include_router(conversations.router)
app.include_router(admin_chat.router)
app.include_router(shop.router)


@app.get("/api/countries")
async def list_countries():
    async with get_session() as session:
        result = await session.execute(
            select(Package.country_code, Package.country_name)
            .where(Package.is_active.is_(True))
            .distinct()
        )
        rows = result.all()
    return [{"code": code, "name": name} for code, name in rows]


@app.get("/api/packages")
async def list_packages(country: str):
    async with get_session() as session:
        result = await session.execute(
            select(Package).where(Package.country_code == country, Package.is_active.is_(True))
        )
        packages = list(result.scalars())
    return [
        {
            "id": p.id,
            "title": p.title,
            "data_amount_mb": p.data_amount_mb,
            "validity_days": p.validity_days,
            "price": float(p.sell_price),
            "currency": p.currency,
        }
        for p in packages
    ]


class CreateOrderRequest(BaseModel):
    package_id: int


@app.post("/api/orders")
async def create_order(body: CreateOrderRequest, user: User = Depends(get_current_user)):
    async with get_session() as session:
        package = await session.get(Package, body.package_id)
        if package is None:
            raise HTTPException(status_code=404, detail="Пакет не найден")

        order = Order(
            user_id=user.id,
            package_id=package.id,
            status=OrderStatus.PENDING_PAYMENT,
            price_charged=package.sell_price,
            currency=package.currency,
            our_transaction_id=str(uuid.uuid4()),
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

        # Оплата теперь отдельным шагом: см. POST /api/orders/{id}/pay (app/webapp/payments.py) —
        # фронтенд вызывает его сразу после создания заказа, когда клиент выберет способ оплаты.

    return {"order_id": order.id, "status": order.status.value}


@app.get("/api/my-orders")
async def my_orders(user: User = Depends(get_current_user)):
    async with get_session() as session:
        result = await session.execute(
            select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())
        )
        orders = list(result.scalars())
        for order in orders:
            await session.refresh(order, attribute_names=["package"])

    return [
        {
            "id": o.id,
            "package_title": o.package.title,
            "status": o.status.value,
            "iccid": o.iccid,
            "qr_code_data": o.qr_code_data,
            "activation_instructions": o.activation_instructions,
            "price": float(o.price_charged),
            "currency": o.currency,
        }
        for o in orders
    ]


# Статика инбокса чатов для админа — регистрируется ДО общего "/", иначе тот
# перехватит эти пути первым (он ловит вообще всё).
app.mount(
    "/support-chat", StaticFiles(directory=BASE_DIR / "support_chat_static", html=True), name="support_chat_static"
)

# Загруженные в чатах фото/файлы — раздаём статикой, чтобы <img>/<a href> в обоих
# Mini App работали напрямую. Папку создаём программно (mkdir), а не полагаемся,
# что она уже есть на диске, — пустые папки часто теряются при копировании файлов
# по отдельности (именно так это и сломалось один раз).
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Стили публичного сайта (app/webapp/shop.py) — тоже до catch-all "/".
app.mount("/shop-static", StaticFiles(directory=BASE_DIR / "shop_static"), name="shop_static")

# Статика клиентского магазина (index.html/app.js/style.css) — подключается ПОСЛЕДНЕЙ,
# чтобы не перехватывать запросы к /api/* и /support-chat/*.
app.mount("/", StaticFiles(directory=BASE_DIR / "static", html=True), name="static")
