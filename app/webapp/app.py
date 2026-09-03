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
import secrets
import uuid

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database.db import get_session, init_db

logging.basicConfig(level=logging.INFO)
from app.database.models import Package, User, Order, OrderStatus, Favorite, Review, TopUp, PaymentProvider, PaymentStatus
from app.webapp.auth import get_current_user
from app.webapp import webhooks, payments, products, conversations, admin_chat, shop

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="eSIM Store — Mini App API",
    # Swagger/ReDoc показывают полную карту всех эндпоинтов системы всем подряд —
    # удобно при разработке, но в проде это просто лишняя разведка для чужих
    # глаз без всякой пользы (это не публичный API-продукт). Выключаем там, где
    # SECURE_COOKIES=true (то есть на Railway), оставляем локально.
    docs_url=None if settings.SECURE_COOKIES else "/docs",
    redoc_url=None if settings.SECURE_COOKIES else "/redoc",
    openapi_url=None if settings.SECURE_COOKIES else "/openapi.json",
)


@app.on_event("startup")
async def on_startup():
    # На случай, если этот процесс запустится раньше ботов (обычная ситуация в
    # деплое с несколькими сервисами — порядок старта не гарантирован) — таблицы
    # должны быть готовы независимо от того, кто стартовал первым. create_all
    # безопасно вызывать много раз: существующие таблицы не трогает.
    await init_db()


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

        reviews = list((
            await session.execute(select(Review.rating).where(Review.country_code == country))
        ).scalars())

    review_count = len(reviews)
    avg_rating = round(sum(reviews) / review_count, 1) if review_count else None

    return {
        "packages": [
            {
                "id": p.id,
                "title": p.title,
                "data_amount_mb": p.data_amount_mb,
                "validity_days": p.validity_days,
                "price": float(p.sell_price),
                "currency": p.currency,
            }
            for p in packages
        ],
        "avg_rating": avg_rating,
        "review_count": review_count,
    }


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

        order_ids = [o.id for o in orders]
        reviewed_order_ids = set()
        if order_ids:
            reviewed_order_ids = set((
                await session.execute(select(Review.order_id).where(Review.order_id.in_(order_ids)))
            ).scalars())

    return {
        "full_name": user.full_name,
        "orders": [
            {
                "id": o.id,
                "package_title": o.package.title,
                "country_code": o.package.country_code,
                "data_amount_mb": o.package.data_amount_mb,
                "validity_days": o.package.validity_days,
                "status": o.status.value,
                "iccid": o.iccid,
                "qr_code_data": o.qr_code_data,
                "activation_instructions": o.activation_instructions,
                "price": float(o.price_charged),
                "currency": o.currency,
                "reviewed": o.id in reviewed_order_ids,
            }
            for o in orders
        ],
    }


@app.get("/api/favorites")
async def get_favorites(user: User = Depends(get_current_user)):
    async with get_session() as session:
        codes = list((
            await session.execute(select(Favorite.country_code).where(Favorite.user_id == user.id))
        ).scalars())
    return {"codes": codes}


class FavoriteToggleRequest(BaseModel):
    country_code: str


@app.post("/api/favorites/toggle")
async def toggle_favorite(body: FavoriteToggleRequest, user: User = Depends(get_current_user)):
    async with get_session() as session:
        existing = (
            await session.execute(
                select(Favorite).where(Favorite.user_id == user.id, Favorite.country_code == body.country_code)
            )
        ).scalar_one_or_none()
        if existing is not None:
            await session.delete(existing)
            is_favorite = False
        else:
            session.add(Favorite(user_id=user.id, country_code=body.country_code))
            is_favorite = True
        await session.commit()
    return {"is_favorite": is_favorite}


class ReviewRequest(BaseModel):
    rating: int
    comment: str = ""


@app.post("/api/orders/{order_id}/review")
async def submit_review(order_id: int, body: ReviewRequest, user: User = Depends(get_current_user)):
    if body.rating < 1 or body.rating > 5:
        raise HTTPException(status_code=400, detail="Оценка должна быть от 1 до 5")

    async with get_session() as session:
        order = await session.get(Order, order_id)
        if order is None or order.user_id != user.id:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        if order.status != OrderStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Отзыв можно оставить только на активированный eSIM")

        existing = (await session.execute(select(Review).where(Review.order_id == order.id))).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=400, detail="Отзыв на этот заказ уже оставлен")

        await session.refresh(order, attribute_names=["package"])
        session.add(Review(
            user_id=user.id, order_id=order.id,
            country_code=order.package.country_code, rating=body.rating, comment=body.comment.strip() or None,
        ))
        await session.commit()

    return {"ok": True}


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