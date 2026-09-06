"""
Инбокс чатов для администратора — отдельный Mini App, открывается из бота
поддержки (см. app/support_bot/handlers.py), защищён get_admin_user (только
твой telegram_id, проверено токеном бота поддержки — см. app/webapp/auth.py).

Чаты бывают из двух источников — Mini App (Telegram, client_telegram_id) и
сайт (WebsiteAccount, website_account_id). Ответ клиенту доставляется по-разному:
в Telegram — сообщением от client_notify_bot, на сайте — письмом на email
(SMTP, см. app/webapp/shop_email.py) плюс сам ответ уже виден в чате на сайте
при следующем опросе (сайт просто читает ConversationMessage напрямую).

Здесь же лежит и раздача статики этого Mini App — смотри mount в app/webapp/app.py.
"""
from aiogram.types import FSInputFile
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select

from app.database.db import get_session
from app.database.models import Category, Conversation, ConversationMessage, ConversationStatus, WebsiteAccount
from app.webapp.auth import get_admin_user
from app.webapp.notify_bots import client_notify_bot
from app.webapp.shop_email import send_email
from app.webapp.uploads import save_attachment

router = APIRouter()


@router.get("/support-chat/api/conversations")
async def list_conversations(_=Depends(get_admin_user)):
    async with get_session() as session:
        result = await session.execute(select(Conversation).order_by(Conversation.updated_at.desc()))
        conversations = list(result.scalars())
        items = []
        for c in conversations:
            product_title = None
            if c.product_id:
                await session.refresh(c, attribute_names=["product"])
                if c.product:
                    product_title = c.product.title_ru

            topic_label = "Поддержка"
            if c.category_id:
                category = await session.get(Category, c.category_id)
                topic_label = category.title_ru if category else "—"

            if c.website_account_id:
                account = await session.get(WebsiteAccount, c.website_account_id)
                client_name = f"🌐 {account.email}" if account else "🌐 сайт"
            else:
                client_name = c.client_full_name or c.client_username or str(c.client_telegram_id)

            items.append({
                "id": c.id,
                "client_name": client_name,
                "topic_label": topic_label,
                "product_title": product_title,
                "status": c.status.value,
                "last_message_preview": c.last_message_preview,
                "unread": c.unread_by_admin,
                "updated_at": c.updated_at.isoformat(),
            })

    return items


@router.get("/support-chat/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: int, _=Depends(get_admin_user)):
    async with get_session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Чат не найден")

        conversation.unread_by_admin = False
        await session.commit()
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


async def _deliver_reply_to_client(conversation: Conversation, text: str) -> None:
    """Telegram — если чат из Mini App, email — если чат с сайта."""
    if conversation.client_telegram_id:
        try:
            await client_notify_bot.send_message(chat_id=conversation.client_telegram_id, text=text)
        except Exception:
            pass
    elif conversation.website_account_id:
        async with get_session() as session:
            account = await session.get(WebsiteAccount, conversation.website_account_id)
        if account:
            send_email(
                to=account.email,
                subject="Новый ответ в вашем чате — eSIM Store",
                body=f"Вам ответили:\n\n{text}\n\nОтветить можно на странице чата на сайте.",
            )


class ReplyRequest(BaseModel):
    text: str


@router.post("/support-chat/api/conversations/{conversation_id}/reply")
async def reply_to_conversation(
    conversation_id: int, body: ReplyRequest, _=Depends(get_admin_user)
):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Пустое сообщение")

    async with get_session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Чат не найден")

        session.add(ConversationMessage(conversation_id=conversation.id, direction="out", text=text))
        conversation.last_message_preview = text[:255]
        await session.commit()
        await session.refresh(conversation)

    await _deliver_reply_to_client(conversation, text)

    return {"ok": True}


@router.post("/support-chat/api/conversations/{conversation_id}/attachments")
async def reply_with_attachment(
    conversation_id: int,
    file: UploadFile = File(...),
    caption: str = Form(""),
    _=Depends(get_admin_user),
):
    async with get_session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Чат не найден")

        saved = await save_attachment(file, conversation_id)

        session.add(
            ConversationMessage(
                conversation_id=conversation.id,
                direction="out",
                text=caption.strip(),
                attachment_url=saved["url"],
                attachment_type=saved["type"],
                attachment_filename=saved["filename"],
            )
        )
        preview = "📷 Фото" if saved["type"] == "photo" else f"📎 {saved['filename']}"
        conversation.last_message_preview = (caption.strip() or preview)[:255]
        await session.commit()
        await session.refresh(conversation)

        client_telegram_id = conversation.client_telegram_id
        website_account_id = conversation.website_account_id
        disk_path = saved["disk_path"]
        attachment_type = saved["type"]

    if client_telegram_id:
        try:
            if attachment_type == "photo":
                await client_notify_bot.send_photo(
                    chat_id=client_telegram_id, photo=FSInputFile(disk_path), caption=caption.strip() or None
                )
            else:
                await client_notify_bot.send_document(
                    chat_id=client_telegram_id, document=FSInputFile(disk_path), caption=caption.strip() or None
                )
        except Exception:
            pass  # вложение уже сохранено и видно клиенту в Mini App — сбой пересылки в чат не критичен
    elif website_account_id:
        async with get_session() as session:
            account = await session.get(WebsiteAccount, website_account_id)
        if account:
            send_email(
                to=account.email,
                subject="Новый файл в вашем чате — eSIM Store",
                body="Вам прислали файл/фото — посмотреть можно на странице чата на сайте.",
            )

    return {"ok": True}


@router.post("/support-chat/api/conversations/{conversation_id}/close")
async def close_conversation(conversation_id: int, _=Depends(get_admin_user)):
    async with get_session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Чат не найден")
        conversation.status = ConversationStatus.CLOSED
        await session.commit()

    return {"ok": True}
