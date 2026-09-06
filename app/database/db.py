"""
Единая точка создания движка и сессий SQLAlchemy (async).
Импортируется и ботами, и админ-панелью — база одна на все три компонента.
"""
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.database.models import Base


def _normalize_database_url(url: str) -> str:
    """
    Railway (и многие другие хостинги) выдают DATABASE_URL в виде обычного
    "postgres://..." или "postgresql://..." — без указания асинхронного драйвера.
    SQLAlchemy async нужен явно "postgresql+asyncpg://...", иначе он попытается
    использовать синхронный psycopg2 (которого у нас даже не установлено) и упадёт.
    Это позволяет просто вставить DATABASE_URL от Railway как есть, без ручной правки.
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(_normalize_database_url(settings.DATABASE_URL), echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """
    Создаёт таблицы, если их ещё нет. Для продакшена лучше заменить на Alembic-миграции.

    Три сервиса (webapp/bots/admin) стартуют почти одновременно и каждый вызывает
    это при старте — без блокировки это иногда приводило к гонке: несколько
    процессов одновременно пытались создать таблицы в пустой базе, и часть таблиц
    (например webhook_events) не успевала создаться. advisory lock Postgres не
    даёт второму и третьему сервису начать создание таблиц, пока первый не закончит.

    Важно: используем именно pg_advisory_XACT_lock (а не pg_advisory_lock +
    ручной unlock) — он снимается автоматически ровно в момент COMMIT/ROLLBACK
    этой же транзакции. Раньше был pg_advisory_lock с ручным unlock ДО commit —
    это оставляло окно, где второй сервис снимал блокировку, видел ещё
    незакоммиченный CREATE TABLE как "таблицы нет" (READ COMMITTED не видит
    чужой незакоммиченный DDL) и пытался создать её же — Postgres отвечал
    "relation already exists", и сервис падал при старте (воспроизвелось на
    проде при добавлении новых таблиц). pg_advisory_xact_lock не отпускает
    лок, пока CREATE TABLE не закоммитится по-настоящему — гонка невозможна.

    На SQLite (локальная разработка) такого типа блокировки нет — там гонки в
    принципе не бывает (обычно только один процесс работает с локальным файлом),
    поэтому просто пропускаем этот шаг.
    """
    async with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            await conn.execute(text("SELECT pg_advisory_xact_lock(727272)"))
        await conn.run_sync(Base.metadata.create_all)
        await _run_light_migrations(conn)


async def _run_light_migrations(conn) -> None:
    """
    create_all() создаёт только отсутствующие ТАБЛИЦЫ — новые колонки в уже
    существующих таблицах он не добавляет. Пока в проекте нет Alembic (см.
    комментарий выше), безопасные добавления колонок делаем тут вручную, через
    IF NOT EXISTS — выполнить это повторно (на каждом старте) ничего не сломает.
    """
    if conn.dialect.name != "postgresql":
        return  # ALTER ... IF NOT EXISTS в этом виде — синтаксис Postgres; на SQLite (локально) не нужно
    await conn.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS link_url VARCHAR(512)"))
    # Новое значение enum-а (Postgres хранит PaymentProvider как настоящий ENUM-тип в БД,
    # create_all() новые значения туда не добавляет — только ALTER TYPE, отдельно).
    await conn.execute(text("ALTER TYPE paymentprovider ADD VALUE IF NOT EXISTS 'stripe'"))

    # Вопрос формы заказа стал трёхъязычным (question_text_ru/hy/en вместо
    # одного question_text) — если таблица уже существует со старой колонкой,
    # добавляем новые и переносим туда старое значение как отправную точку
    # (админ потом поправит переводы на hy/en вручную).
    await conn.execute(text("ALTER TABLE product_questions ADD COLUMN IF NOT EXISTS question_text_ru VARCHAR(500)"))
    await conn.execute(text("ALTER TABLE product_questions ADD COLUMN IF NOT EXISTS question_text_hy VARCHAR(500)"))
    await conn.execute(text("ALTER TABLE product_questions ADD COLUMN IF NOT EXISTS question_text_en VARCHAR(500)"))
    old_column_exists = (await conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='product_questions' AND column_name='question_text'"
    ))).first()
    if old_column_exists is not None:
        for col in ("question_text_ru", "question_text_hy", "question_text_en"):
            await conn.execute(text(f"UPDATE product_questions SET {col} = question_text WHERE {col} IS NULL"))

    # То же самое для снимка вопроса в ответах (ServiceRequestAnswer) — было
    # одно поле question_text, стало три (см. комментарий в models.py).
    await conn.execute(text("ALTER TABLE service_request_answers ADD COLUMN IF NOT EXISTS question_text_ru VARCHAR(500)"))
    await conn.execute(text("ALTER TABLE service_request_answers ADD COLUMN IF NOT EXISTS question_text_hy VARCHAR(500)"))
    await conn.execute(text("ALTER TABLE service_request_answers ADD COLUMN IF NOT EXISTS question_text_en VARCHAR(500)"))
    old_answer_column_exists = (await conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='service_request_answers' AND column_name='question_text'"
    ))).first()
    if old_answer_column_exists is not None:
        for col in ("question_text_ru", "question_text_hy", "question_text_en"):
            await conn.execute(text(f"UPDATE service_request_answers SET {col} = question_text WHERE {col} IS NULL"))

    # Срок ответа по услуге (Product) и комментарий клиента (ServiceRequest) —
    # добавлены позже, тоже просто новые nullable-колонки в уже существующих таблицах.
    await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS response_time_text VARCHAR(255)"))
    await conn.execute(text("ALTER TABLE service_requests ADD COLUMN IF NOT EXISTS client_note TEXT"))


@asynccontextmanager
async def get_session():
    async with SessionLocal() as session:
        yield session