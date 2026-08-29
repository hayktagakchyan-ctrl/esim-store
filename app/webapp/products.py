"""
Каталог категорий и товаров (лаунж, туры, и что угодно ещё, что добавишь через
админку /categories и /products) для клиентского Mini App. В отличие от Package
(eSIM), тут нет автоматической закупки — просто карточки, которые вносятся
вручную через админку, а покупка идёт через чат, не через оплату здесь.
"""
from fastapi import APIRouter
from sqlalchemy import select

from app.database.db import get_session
from app.database.models import Category, Product

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
        }
        for p in products
    ]
