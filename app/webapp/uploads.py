"""
Сохранение вложений (фото/файлы) из чатов на диск, чтобы их можно было:
- показать в обоих Mini App (клиентском и админском) через обычный <img>/<a href>
  по статическому URL (см. mount("/uploads", ...) в app/webapp/app.py);
- переслать как настоящее фото/документ в Telegram через FSInputFile (см.
  app/webapp/conversations.py и admin_chat.py).

Файлы физически лежат в app/webapp/uploads/conversations/{conversation_id}/ —
имя на диске всегда случайное (UUID), оригинальное имя сохраняется отдельно
в БД (ConversationMessage.attachment_filename) только для отображения.
"""
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024  # 20 МБ — с запасом хватает на фото и большинство документов

UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"

IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# Важно: проверять нужно РАСШИРЕНИЕ файла, а не только заявленный content-type.
# Content-type в multipart-запросе задаёт сам клиент — можно соврать (прислать
# "image/png" с настоящим содержимым .html/.svg внутри). А вот раздаёт файл
# StaticFiles именно по расширению на диске — значит, дыра для сохранённого
# XSS была бы именно тут, если бы мы доверяли только content-type. Поэтому
# расширение — это и есть настоящий защитный барьер, белый список ниже.
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif",  # изображения
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt",  # документы
}


async def save_attachment(file: UploadFile, conversation_id: int) -> dict:
    """Возвращает {"url", "type", "filename", "disk_path"}. Кидает HTTPException при проблеме."""
    contents = await file.read()
    if len(contents) > MAX_ATTACHMENT_SIZE:
        raise HTTPException(status_code=413, detail="Файл слишком большой (максимум 20 МБ)")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Пустой файл")

    original_name = file.filename or "file"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Такой тип файла не поддерживается — можно фото (jpg/png/webp/gif) "
                   "или документы (pdf/doc/docx/xls/xlsx/txt).",
        )

    conv_dir = UPLOADS_DIR / "conversations" / str(conversation_id)
    conv_dir.mkdir(parents=True, exist_ok=True)

    disk_name = f"{uuid.uuid4().hex}{suffix}"
    disk_path = conv_dir / disk_name

    with open(disk_path, "wb") as f:
        f.write(contents)

    attachment_type = "photo" if (file.content_type in IMAGE_CONTENT_TYPES) else "document"

    return {
        "url": f"/uploads/conversations/{conversation_id}/{disk_name}",
        "type": attachment_type,
        "filename": original_name,
        "disk_path": disk_path,
    }
