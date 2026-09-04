"""
Единая схема БД. Используется клиентским ботом, ботом поддержки и админ-панелью —
все три компонента работают с одной и той же базой, поэтому вся история (заказы,
переписка с поддержкой) видна в одном месте.
"""
from datetime import datetime
import enum

from sqlalchemy import (
    BigInteger, String, Integer, Numeric, DateTime, ForeignKey, Text, Enum, JSON, Boolean, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Баланс и реферальная программа — то же самое, что у WebsiteAccount (сайт),
    # только для пользователей бота/Mini App. Отдельные поля, а не общий аккаунт,
    # потому что у бота и сайта разные способы входа (Telegram vs email) — их
    # объединение в один аккаунт было бы отдельной, более крупной задачей.
    balance: Mapped[float] = mapped_column(default=0.0)
    referral_code: Mapped[str | None] = mapped_column(String(16), unique=True, index=True, nullable=True)
    referred_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    referral_bonus_paid: Mapped[bool] = mapped_column(default=False)

    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Package(Base):
    """
    Локальный кэш пакетов из esimaccess — чтобы не дёргать их API на каждое
    открытие каталога клиентом. Обновляется периодической задачей (см. services/catalog_sync.py).
    """
    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    esimaccess_package_code: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    country_code: Mapped[str] = mapped_column(String(32), index=True)  # ISO-код страны, напр. "AM" — для региональных пакетов сюда пишется код региона (напр. "EU-42", "SAAEQAKWOMBH-6")
    country_name: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(255))                    # напр. "5 ГБ / 30 дней"
    data_amount_mb: Mapped[int] = mapped_column(Integer)
    validity_days: Mapped[int] = mapped_column(Integer)
    cost_price: Mapped[float] = mapped_column(Numeric(10, 2))          # закупочная цена (от esimaccess)
    sell_price: Mapped[float] = mapped_column(Numeric(10, 2))          # цена для клиента (с наценкой)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)     # можно скрыть пакет из каталога
    is_regional: Mapped[bool] = mapped_column(Boolean, default=False)  # пакет на регион (Европа/Азия/...), не на одну страну
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True) # сырой ответ API — на всякий случай
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PROVISIONING = "provisioning"   # заказ отправлен в esimaccess, ждём eSIM
    ACTIVE = "active"               # eSIM выдан клиенту
    FAILED = "failed"
    REFUNDED = "refunded"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id"))

    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING_PAYMENT, index=True)

    price_charged: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(8), default="USD")

    # Наш собственный идентификатор заказа, который мы отправляем esimaccess при
    # создании заказа (поле transactionId в их API) — по нему сопоставляем входящие
    # вебхуки с этим заказом. Генерируется до вызова create_order.
    our_transaction_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)

    # Данные от esimaccess (см. docs.esimaccess.com):
    esimaccess_order_no: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)     # orderNo
    esimaccess_esim_tran_no: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True) # esimTranNo — нужен для usage/query
    iccid: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    qr_code_data: Mapped[str | None] = mapped_column(Text, nullable=True)   # строка активации / ссылка на QR
    activation_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Последний известный статус из вебхуков ESIM_STATUS/SMDP_EVENT — для админки и диагностики,
    # не участвует в бизнес-логике (за неё отвечает OrderStatus выше).
    last_esim_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_smdp_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    refund_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Для заказов с САЙТА (не из Telegram) — там нет telegram-идентичности, поэтому
    # покупатель отслеживает заказ по email + случайной ссылке (guest_token), а не логином.
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guest_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    # Если покупатель на сайте вошёл в аккаунт (необязательно — можно и гостем) —
    # заказ также привязывается сюда, чтобы попасть в "Мои заказы".
    website_account_id: Mapped[int | None] = mapped_column(ForeignKey("website_accounts.id"), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="orders")
    package: Mapped["Package"] = relationship()
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")


class WebhookEvent(Base):
    """
    Лог входящих вебхуков от esimaccess — только для дедупликации по notifyId
    (они прямо предупреждают в документации, что доставка не гарантированно однократная).
    """
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    notify_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    notify_type: Mapped[str] = mapped_column(String(32))
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PaymentProvider(str, enum.Enum):
    IDRAM = "idram"
    WALLET_PAY = "wallet_pay"   # Telegram Wallet — покрывает и "крипту", и "Telegram-кошелёк" одним провайдером
    OXAPAY = "oxapay"           # крипта с ЛЮБОГО адреса/биржи, без привязки к Telegram-аккаунту
    TEST = "test"               # только для проверки — см. settings.ENABLE_TEST_PAYMENT
    BALANCE = "balance"         # оплата с внутреннего баланса сайта (см. WebsiteAccount.balance)


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"


class Payment(Base):
    """
    Одна попытка оплаты одного заказа. У заказа может быть больше одной попытки
    (например, клиент начал платить через Idram, передумал, попробовал Wallet Pay) —
    поэтому это отдельная таблица, а не поля прямо на Order.
    """
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)

    provider: Mapped[PaymentProvider] = mapped_column(Enum(PaymentProvider))
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING, index=True)

    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(8))

    # Для Idram: EDP_BILL_NO, который мы сами генерируем и по которому сверяем RESULT_URL.
    # Для Wallet Pay: externalId, который мы передаём в create_order.
    external_payment_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # Для Wallet Pay: числовой id заказа и payLink, которые возвращает их API.
    provider_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pay_link: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Для Idram: EDP_TRANS_ID/EDP_TRANS_DATE из подтверждения платежа — для сверки/поддержки.
    provider_transaction_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    raw_callback: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order: Mapped["Order"] = relationship(back_populates="payments")


class Category(Base):
    """
    Категория товаров, которые продаются через чат (не eSIM — у eSIM свой
    отдельный автоматический флоу). Раньше было жёстко зашито "лаунж" и "туры" —
    теперь это обычная таблица, категории добавляются/редактируются через
    админку (/categories), можно добавить сколько угодно новых.
    """
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # для API/внутренних ссылок, напр. "lounge"
    icon: Mapped[str] = mapped_column(String(8), default="🛍")               # эмодзи на карточке категории

    title_ru: Mapped[str] = mapped_column(String(255))
    title_hy: Mapped[str] = mapped_column(String(255))
    title_en: Mapped[str] = mapped_column(String(255))

    subtitle_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subtitle_hy: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subtitle_en: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)  # порядок карточек на главном экране, меньше = выше
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def title(self, lang: str) -> str:
        return {"ru": self.title_ru, "hy": self.title_hy, "en": self.title_en}.get(lang, self.title_ru)

    def subtitle(self, lang: str) -> str | None:
        return {
            "ru": self.subtitle_ru, "hy": self.subtitle_hy, "en": self.subtitle_en,
        }.get(lang, self.subtitle_ru)


class Product(Base):
    """
    Товар внутри категории (напр. конкретный лаунж или конкретный тур) — в
    отличие от eSIM, тут нет автоматической закупки у esimaccess: это просто
    карточка, которую ты сам вносишь через админку, а оформление идёт через
    чат (Conversation ниже), а не автоматическую оплату. Название/описание —
    на трёх языках сразу, колонки суффиксом _ru/_hy/_en.
    """
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)

    title_ru: Mapped[str] = mapped_column(String(255))
    title_hy: Mapped[str] = mapped_column(String(255))
    title_en: Mapped[str] = mapped_column(String(255))

    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_hy: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Ориентировочная цена — необязательна, финальная сумма обычно обсуждается в чате.
    price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category: Mapped["Category"] = relationship()

    def title(self, lang: str) -> str:
        return {"ru": self.title_ru, "hy": self.title_hy, "en": self.title_en}.get(lang, self.title_ru)

    def description(self, lang: str) -> str | None:
        return {
            "ru": self.description_ru, "hy": self.description_hy, "en": self.description_en,
        }.get(lang, self.description_ru)


class ConversationStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class Conversation(Base):
    """
    Один чат с одним клиентом по одной теме. Специально НЕ переиспользуется под
    несколько тем одновременно — если клиент спросил и про тур, и про лаунж,
    это два разных Conversation, чтобы в инбоксе администратора они не путались.

    category_id пустой (None) означает общий вопрос в поддержку, без привязки
    к конкретной категории товаров.

    Ровно один из client_telegram_id / website_account_id обязательно заполнен —
    чат либо из Mini App (Telegram), либо с сайта (аккаунт с email/паролем).
    """
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    client_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website_account_id: Mapped[int | None] = mapped_column(ForeignKey("website_accounts.id"), nullable=True, index=True)

    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)

    status: Mapped[ConversationStatus] = mapped_column(Enum(ConversationStatus), default=ConversationStatus.OPEN, index=True)

    last_message_preview: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unread_by_admin: Mapped[bool] = mapped_column(Boolean, default=True)  # сброс при открытии чата админом

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    category: Mapped["Category | None"] = relationship()
    product: Mapped["Product | None"] = relationship()
    messages: Mapped[list["ConversationMessage"]] = relationship(back_populates="conversation", order_by="ConversationMessage.created_at")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    direction: Mapped[str] = mapped_column(String(8))  # "in" (от клиента) / "out" (от админа)
    text: Mapped[str] = mapped_column(Text, default="")  # может быть пустым, если это просто фото/файл

    # Вложение — необязательное, одно на сообщение (фото или документ, не оба сразу).
    attachment_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    attachment_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # "photo" | "document"
    attachment_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)  # исходное имя, для документов

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class WebsiteAccount(Base):
    """
    Логин для сайта (app/webapp/shop.py) — email + пароль, обязателен для покупки
    и для чатов (лаунж/туры) — без входа посетитель может только смотреть каталог.
    "Мои заказы" и "Мои чаты" привязаны к аккаунту.
    """
    __tablename__ = "website_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Восстановление пароля — токен одноразовый, с истечением срока действия.
    password_reset_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Подтверждение email — без этого войти в аккаунт нельзя (значит, и купить/
    # написать в чат тоже нельзя, раз то и другое требует входа).
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    verification_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Баланс — пополняется через Idram/OxaPay (см. TopUp ниже), тратится на
    # оформление заказов как альтернатива прямой оплате за конкретный заказ.
    # Храним в той же валюте, что и заказы — USD.
    balance: Mapped[float] = mapped_column(default=0.0)

    # Реферальная программа — свой код (для ссылки-приглашения) и то, кто
    # пригласил ЭТОГО пользователя (если он сам пришёл по чужой ссылке).
    referral_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    referred_by_id: Mapped[int | None] = mapped_column(ForeignKey("website_accounts.id"), nullable=True)
    referral_bonus_paid: Mapped[bool] = mapped_column(default=False)  # чтобы начислить рефереру только один раз


class TopUp(Base):
    """Пополнение баланса — та же логика провайдеров (Idram/OxaPay), что и у Payment для заказов.
    Владелец — ЛИБО аккаунт сайта, ЛИБО пользователь бота (ровно один из двух)."""
    __tablename__ = "top_ups"

    id: Mapped[int] = mapped_column(primary_key=True)
    website_account_id: Mapped[int | None] = mapped_column(ForeignKey("website_accounts.id"), index=True, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    amount: Mapped[float] = mapped_column()
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    provider: Mapped[PaymentProvider] = mapped_column(Enum(PaymentProvider))
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    external_payment_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    provider_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pay_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Review(Base):
    """
    Отзыв на страну — оставить может только тот, у кого есть РЕАЛЬНЫЙ заказ
    в статусе ACTIVE по этой стране (проверяется при создании отзыва) — значит,
    эти цифры не накручены, растут только от настоящих покупателей. Владелец —
    ЛИБО аккаунт сайта, ЛИБО пользователь бота (ровно один из двух).
    """
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    website_account_id: Mapped[int | None] = mapped_column(ForeignKey("website_accounts.id"), index=True, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)  # один отзыв на один заказ
    country_code: Mapped[str] = mapped_column(String(32), index=True)
    rating: Mapped[int] = mapped_column()  # 1..5
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Favorite(Base):
    """Избранные страны — просто список кодов стран на аккаунт. Владелец —
    ЛИБО аккаунт сайта, ЛИБО пользователь бота (ровно один из двух)."""
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("website_account_id", "country_code", name="uq_favorite_account_country"),
        UniqueConstraint("user_id", "country_code", name="uq_favorite_user_country"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    website_account_id: Mapped[int | None] = mapped_column(ForeignKey("website_accounts.id"), index=True, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    country_code: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PromoCode(Base):
    """Промокод — начисляет фиксированную сумму на баланс при активации. Заводится вручную в админке."""
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    bonus_amount: Mapped[float] = mapped_column()          # сколько $ начисляется на баланс
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = без ограничения
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PromoCodeRedemption(Base):
    """Кто когда активировал какой промокод — не даёт активировать один и тот же код дважды."""
    __tablename__ = "promo_code_redemptions"
    __table_args__ = (
        UniqueConstraint("promo_code_id", "website_account_id", name="uq_promo_account"),
        UniqueConstraint("promo_code_id", "user_id", name="uq_promo_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    promo_code_id: Mapped[int] = mapped_column(ForeignKey("promo_codes.id"), index=True)
    website_account_id: Mapped[int | None] = mapped_column(ForeignKey("website_accounts.id"), index=True, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    redeemed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationType(str, enum.Enum):
    ORDER = "order"
    PAYMENT = "payment"
    SYSTEM = "system"


class Notification(Base):
    """Уведомление в приложении — не имеет отношения к push-сообщениям бота (те шлются отдельно,
    прямо в чат Telegram); это именно лента внутри Mini App/сайта, как история событий."""
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    website_account_id: Mapped[int | None] = mapped_column(ForeignKey("website_accounts.id"), index=True, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)