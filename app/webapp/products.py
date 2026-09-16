"""
Каталог категорий и товаров (лаунж, туры, и что угодно ещё, что добавишь через
админку /categories и /products) для клиентского Mini App, а также заявки на
услуги через настраиваемую форму (ProductQuestion/ServiceRequest) — точный
аналог формы на сайте (/shop/services/product/{id}/request), просто с
авторизацией через Telegram initData вместо cookie-сессии. База данных с
самого начала поддерживала обоих владельцев (website_account_id ИЛИ user_id
у ServiceRequest) — этой части просто не хватало именно бот-стороны.
"""
from datetime import datetime

from aiogram.types import BufferedInputFile
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.config import settings
from app.database.db import get_session
from app.database.models import (
    Category, Product, ProductQuestion, QuestionType,
    ServiceRequest, ServiceRequestAnswer, ServiceRequestStatus, User,
)
from app.webapp.notify_bots import client_notify_bot
from app.webapp.auth import get_current_user
from app.webapp.uploads import save_service_file
from app.webapp.notify_bots import support_notify_bot

router = APIRouter()


@router.get("/api/categories")
async def list_categories(lang: str = "ru"):
    """Категории для главного экрана Mini App (карточка eSIM — отдельная, зашита во фронтенде)."""
    async with get_session() as session:
        result = await session.execute(
            select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order, Category.id)
        )
        categories = list(result.scalars())

    return [
        {
            "id": c.id,
            "slug": c.slug,
            "icon": c.icon,
            "title": c.title(lang),
            "subtitle": c.subtitle(lang),
        }
        for c in categories
    ]


@router.get("/api/products")
async def list_products(category: str, lang: str = "ru"):
    """category — slug категории (см. /api/categories)."""
    async with get_session() as session:
        cat_result = await session.execute(select(Category).where(Category.slug == category))
        cat = cat_result.scalar_one_or_none()
        if cat is None:
            return []

        result = await session.execute(
            select(Product).where(Product.category_id == cat.id, Product.is_active.is_(True))
        )
        products = list(result.scalars())

    return [
        {
            "id": p.id,
            "title": p.title(lang),
            "description": p.description(lang),
            "price": float(p.price) if p.price is not None else None,
            "currency": p.currency,
            "response_time_text": p.response_time_text,
        }
        for p in products
    ]


@router.get("/api/products/{product_id}/questions")
async def product_questions(product_id: int, lang: str = "ru"):
    async with get_session() as session:
        product = await session.get(Product, product_id)
        if product is None or not product.is_active:
            raise HTTPException(status_code=404, detail="Услуга не найдена")
        questions = list((await session.execute(
            select(ProductQuestion).where(ProductQuestion.product_id == product_id)
            .order_by(ProductQuestion.position, ProductQuestion.id)
        )).scalars())
    return {
        "product": {
            "id": product.id, "title": product.title(lang),
            "price": float(product.price) if product.price is not None else None,
            "currency": product.currency, "response_time_text": product.response_time_text,
        },
        "questions": [
            {"id": q.id, "question_text": q.text(lang), "question_type": q.question_type.value, "is_required": q.is_required}
            for q in questions
        ],
    }


def _service_request_owned_by(sr: ServiceRequest | None, user: User) -> ServiceRequest:
    if sr is None or sr.user_id != user.id:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return sr


@router.post("/api/service-requests")
async def create_service_request(request: Request, user: User = Depends(get_current_user)):
    form = await request.form()
    lang = request.headers.get("X-Lang", "ru")
    product_id = int(form.get("product_id"))
    client_note = (form.get("client_note") or "").strip() or None

    async with get_session() as session:
        product = await session.get(Product, product_id)
        if product is None or not product.is_active:
            raise HTTPException(status_code=404, detail="Услуга не найдена")
        questions = list((await session.execute(
            select(ProductQuestion).where(ProductQuestion.product_id == product_id)
            .order_by(ProductQuestion.position, ProductQuestion.id)
        )).scalars())

        sr = ServiceRequest(
            product_id=product_id, user_id=user.id, currency=product.currency,
            client_note=client_note,
        )
        session.add(sr)
        await session.flush()

        for q in questions:
            answer = ServiceRequestAnswer(
                service_request_id=sr.id, question_id=q.id,
                question_text_ru=q.question_text_ru, question_text_hy=q.question_text_hy, question_text_en=q.question_text_en,
                question_type=q.question_type,
            )
            if q.question_type == QuestionType.YES_NO:
                raw = form.get(f"answer_{q.id}")
                answer.answer_bool = (raw == "yes") if raw in ("yes", "no") else None
                if q.is_required and answer.answer_bool is None:
                    raise HTTPException(status_code=400, detail=f"Ответьте на вопрос: {q.text(lang)}")
            elif q.question_type == QuestionType.TEXT:
                raw = (form.get(f"answer_{q.id}") or "").strip()
                answer.answer_text = raw or None
                if q.is_required and not raw:
                    raise HTTPException(status_code=400, detail=f"Заполните: {q.text(lang)}")
            else:  # FILE
                upload = form.get(f"answer_file_{q.id}")
                if upload is not None and getattr(upload, "filename", ""):
                    saved = await save_service_file(upload, sr.id)
                    answer.answer_file_path = saved["url"]
                    answer.answer_file_filename = saved["filename"]
                    answer.answer_file_data = saved["data"]
                    answer.answer_file_content_type = saved["content_type"]
                elif q.is_required:
                    raise HTTPException(status_code=400, detail=f"Прикрепите файл: {q.text(lang)}")
            session.add(answer)

        await session.commit()
        request_id = sr.id

    try:
        await support_notify_bot.send_message(
            chat_id=settings.SUPPORT_CHAT_ID,
            text=f"🆕 Новая заявка на услугу (бот)\n{product.title('ru')}\nОт: user_id={user.id}\n"
                 f"Посмотреть в админке: заявка #{request_id}",
        )
    except Exception:
        pass

    return {"id": request_id}


@router.get("/api/service-requests")
async def list_service_requests(lang: str = "ru", user: User = Depends(get_current_user)):
    async with get_session() as session:
        rows = list((await session.execute(
            select(ServiceRequest).where(ServiceRequest.user_id == user.id)
            .order_by(ServiceRequest.created_at.desc())
        )).scalars())
        for r in rows:
            await session.refresh(r, attribute_names=["product"])
    return [
        {"id": r.id, "product_title": r.product.title(lang), "status": r.status.value,
         "created_at": r.created_at.isoformat(), "final_price": float(r.final_price) if r.final_price is not None else None,
         "currency": r.currency}
        for r in rows
    ]


@router.get("/api/service-requests/{request_id}")
async def service_request_detail(request_id: int, lang: str = "ru", user: User = Depends(get_current_user)):
    async with get_session() as session:
        sr = _service_request_owned_by(await session.get(ServiceRequest, request_id), user)
        await session.refresh(sr, attribute_names=["answers", "product"])
        is_paid = sr.status == ServiceRequestStatus.PAID
        is_cancelled = sr.status == ServiceRequestStatus.CANCELLED
        return {
            "id": sr.id, "status": sr.status.value, "product_title": sr.product.title(lang),
            "final_price": float(sr.final_price) if sr.final_price is not None else None,
            "currency": sr.currency, "response_time_text": sr.product.response_time_text,
            "client_note": sr.client_note,
            # Причина отказа (или комментарий после оплаты) — та же логика, что
            # на сайте: admin_note виден при paid ИЛИ cancelled, файл — только paid.
            "admin_note": sr.admin_note if (is_paid or is_cancelled) else None,
            "deliverable_path": sr.deliverable_path if is_paid else None,
            "deliverable_filename": sr.deliverable_filename if is_paid else None,
            "answers": [
                {"question_text": a.text(lang), "question_type": a.question_type.value,
                 "answer_text": a.answer_text, "answer_bool": a.answer_bool,
                 "answer_file_path": a.answer_file_path, "answer_file_filename": a.answer_file_filename}
                for a in sr.answers
            ],
        }


@router.post("/api/service-requests/{request_id}/pay")
async def pay_service_request(request_id: int, user: User = Depends(get_current_user)):
    async with get_session() as session:
        db_user = await session.get(User, user.id)
        sr = _service_request_owned_by(await session.get(ServiceRequest, request_id), user)

        if sr.status != ServiceRequestStatus.READY or sr.final_price is None:
            raise HTTPException(status_code=400, detail="Эту заявку сейчас нельзя оплатить")
        if db_user.balance < float(sr.final_price):
            raise HTTPException(status_code=400, detail="Недостаточно средств на балансе")

        db_user.balance = round(db_user.balance - float(sr.final_price), 2)
        sr.status = ServiceRequestStatus.PAID
        sr.paid_at = datetime.utcnow()
        await session.refresh(sr, attribute_names=["product"])
        # Ссылка на файл внутри мини-аппа Telegram открывает его только во
        # внешнем браузере (переходы по ссылкам из Mini App так устроены,
        # обойти нельзя) — оттуда сохранить можно только вручную. Раз файл
        # уже лежит байтами в базе (см. deliverable_data), самый надёжный
        # способ отдать его — обычным сообщением от бота в чат: Telegram
        # тогда сам предложит штатное "Сохранить", как с любым файлом.
        deliverable_data = sr.deliverable_data
        deliverable_filename = sr.deliverable_filename
        product_title = sr.product.title("ru")
        telegram_id = user.telegram_id
        await session.commit()

    if deliverable_data:
        try:
            ext = (deliverable_filename or "").rsplit(".", 1)[-1].lower()
            file = BufferedInputFile(deliverable_data, filename=deliverable_filename or "file")
            caption = f"Заявка «{product_title}» оплачена — вот файл."
            if ext in ("jpg", "jpeg", "png", "webp"):
                await client_notify_bot.send_photo(chat_id=telegram_id, photo=file, caption=caption)
            else:
                await client_notify_bot.send_document(chat_id=telegram_id, document=file, caption=caption)
        except Exception:
            pass  # не срываем уже прошедшую оплату, если сообщение почему-то не ушло

    return {"ok": True}
