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
    На SQLite (локальная разработка) такого типа блокировки нет — там гонки в
    принципе не бывает (обычно только один процесс работает с локальным файлом),
    поэтому просто пропускаем этот шаг.
    """
    async with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            await conn.execute(text("SELECT pg_advisory_lock(727272)"))
        try:
            await conn.run_sync(Base.metadata.create_all)
        finally:
            if engine.dialect.name == "postgresql":
                await conn.execute(text("SELECT pg_advisory_unlock(727272)"))


@asynccontextmanager
async def get_session():
    async with SessionLocal() as session:
        yield session