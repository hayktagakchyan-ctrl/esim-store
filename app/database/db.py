"""
Единая точка создания движка и сессий SQLAlchemy (async).
Импортируется и ботами, и админ-панелью — база одна на все три компонента.
"""
from contextlib import asynccontextmanager

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
    """Создаёт таблицы, если их ещё нет. Для продакшена лучше заменить на Alembic-миграции."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session():
    async with SessionLocal() as session:
        yield session
