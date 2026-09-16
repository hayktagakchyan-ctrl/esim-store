"""
Чаты со стороны клиента (Mini App). Тема чата теперь определяется category_id
(динамическая категория из БД, добавляется через /categories) — либо пусто
(None), тогда это общий вопрос в поддержку без привязки к товару.

У каждого клиента на каждую категорию+товар максимум один ОТКРЫТЫЙ разговор
(см. logic ниже), чтобы не плодить дубли при повторных заходах в один и тот же чат.

Ответ администратора приходит через app/webapp/admin_chat.py — тот же самый
Conversation, просто с направлением "out". Клиент видит его через простой опрос
(polling), так же как остальной Mini App (см. GET .../messages ниже).

Вложения (фото/файлы) — см. save_attachment() в app/webapp/uploads.py: файл
сохраняется на диск и раздаётся статикой (/uploads/...) для показа в Mini App,
плюс пересылается настоящим фото/документом в Telegram через FSInputFile —
так уведомление о новом сообщении не теряет вложение, даже если админ сейчас
не смотрит в свой чат-инбокс.
"""
from aiogram.types import FSInputFile
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select

from app.database.db import get_session
from app.database.models import (
    Category, Conversation, ConversationMessage, ConversationStatus, Product, User,
)
from app.webapp.auth import get_current_user
from app.webapp.notify_bots import support_notify_bot
from app.webapp.uploads import save_attachment
from app.config import settings

router = APIRouter()


async def _topic_label(session, category_id: int | None, lang: str = "ru") -> str:
    if category_id is None:
        # Небольшой встроенный словарь — тут всего одно слово, не требует полноценного i18n.py
        return {"ru": "Поддержка", "hy": "Աջակցություն", "en": "Support"}.get(lang, "Поддержка")
    category = await session.get(Category, category_id)
    return category.title(lang) if category else "—"


@router.get("/api/conversations")
async def list_my_conversations(lang: str = "ru", user: User = Depends(get_current_user)):
    async with get_session() as session:
        result = await session.execute(
            select(Conversation)
            .where(Conversation.client_telegram_id == user.telegram_id)
            .order_by(Conversation.updated_at.desc())
        )
        conversations = list(result.scalars())

        items = []
        for c in conversations:
            product_title = None
            if c.product_id:
                await session.refresh(c, attribute_names=["product"])
                if c.product:
                    product_title = c.product.title(lang)
            items.append({
                "id": c.id,
                "topic_label": await _topic_label(session, c.category_id, lang),
                "product_title": product_title,
                "status": c.status.value,
                "last_message_preview": c.last_message_preview,
                "updated_at": c.updated_at.isoformat(),
            })

    return items


class StartConversationRequest(BaseModel):
    category_id: int | None = None  # None = общая поддержка
    product_id: int | None = None


@router.post("/api/conversations")
async def start_conversation(body: StartConversationRequest, user: User = Depends(get_current_user)):
    async with get_session() as session:
        if body.category_id is not None:
            category = await session.get(Category, body.category_id)
            if category is None:
                raise HTTPException(status_code=404, detail="Категория не найдена")

        # Переиспользуем уже открытый разговор на ту же тему+товар, а не плодим дубли.
        query = select(Conversation).where(
            Conversation.client_telegram_id == user.telegram_id,
            Conversation.category_id == body.category_id,
            Conversation.product_id == body.product_id,
            Conversation.status == ConversationStatus.OPEN,
        )
        existing = (await session.execute(query)).scalar_one_or_none()
        if existing:
            return {"conversation_id": existing.id}

        if body.product_id is not None:
            product = await session.get(Product, body.product_id)
            if product is None:
                raise HTTPException(status_code=404, detail="Товар не найден")

        conversation = Conversation(
            client_telegram_id=user.telegram_id,
            client_username=user.username,
            client_full_name=user.full_name,
            category_id=body.category_id,
            product_id=body.product_id,
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)
        return {"conversation_id": conversation.id}


@router.get("/api/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: int, user: User = Depends(get_current_user)):
    async with get_session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None or conversation.client_telegram_id != user.telegram_id:
            raise HTTPException(status_code=404, detail="Чат не найден")
        await session.refresh(conversation, attribute_names=["messages"])

    return [
        {
            "direction": m.direction,
            "text": m.text,
            "attachment_url": m.attachment_url,
            "attachment_type": m.attachment_type,
            "attachment_filename": m.attachment_filename,
            "created_at": m.created_at.isoformat(),
        }
        for m in conversation.messages
    ]


class SendMessageRequest(BaseModel):
    text: str


async def _notify_admin_new_message(session, conversation: Conversation, client_label: str, preview: str) -> None:
    topic_label = await _topic_label(session, conversation.category_id)
    try:
        await support_notify_bot.send_message(
            chat_id=settings.SUPPORT_CHAT_ID,
            text=f"🆕 Новое сообщение\nОт: {client_label}\nТема: {topic_label}\n\n{preview}",
        )
    except Exception:
        pass  # не срываем ответ клиенту из-за сбоя уведомления — сообщение уже сохранено


@router.post("/api/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int, body: SendMessageRequest, user: User = Depends(get_current_user)
):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Пустое сообщение")

    async with get_session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None or conversation.client_telegram_id != user.telegram_id:
            raise HTTPException(status_code=404, detail="Чат не найден")

        session.add(ConversationMessage(conversation_id=conversation.id, direction="in", text=text))
        conversation.last_message_preview = text[:255]
        conversation.unread_by_admin = True
        conversation.status = ConversationStatus.OPEN  # клиент написал повторно — считаем открытым снова
        await session.commit()

        client_label = conversation.client_full_name or conversation.client_username or str(user.telegram_id)
        await _notify_admin_new_message(session, conversation, client_label, text)

    return {"ok": True}


@router.post("/api/conversations/{conversation_id}/attachments")
async def send_attachment(
    conversation_id: int,
    file: UploadFile = File(...),
    caption: str = Form(""),
    user: User = Depends(get_current_user),
):
    async with get_session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None or conversation.client_telegram_id != user.telegram_id:
            raise HTTPException(status_code=404, detail="Чат не найден")

        saved = await save_attachment(file, conversation_id)

        session.add(
            ConversationMessage(
                conversation_id=conversation.id,
                direction="in",
                text=caption.strip(),
                attachment_url=saved["url"],
                attachment_type=saved["type"],
                attachment_filename=saved["filename"],
            )
        )
        preview = "📷 Фото" if saved["type"] == "photo" else f"📎 {saved['filename']}"
        conversation.last_message_preview = (caption.strip() or preview)[:255]
        conversation.unread_by_admin = True
        conversation.status = ConversationStatus.OPEN
        await session.commit()

        client_label = conversation.client_full_name or conversation.client_username or str(user.telegram_id)
        topic_label = await _topic_label(session, conversation.category_id)
        disk_path = saved["disk_path"]
        attachment_type = saved["type"]

    tg_caption = f"🆕 От: {client_label}\nТема: {topic_label}" + (f"\n\n{caption.strip()}" if caption.strip() else "")
    try:
        if attachment_type == "photo":
            await support_notify_bot.send_photo(
                chat_id=settings.SUPPORT_CHAT_ID, photo=FSInputFile(disk_path), caption=tg_caption
            )
        else:
            await support_notify_bot.send_document(
                chat_id=settings.SUPPORT_CHAT_ID, document=FSInputFile(disk_path), caption=tg_caption
            )
    except Exception:
        pass  # вложение уже сохранено и видно в инбоксе — сбой пересылки в Telegram не критичен

    return {"ok": True}
