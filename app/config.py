"""
Централизованная конфигурация проекта.
Все секреты берутся из переменных окружения (.env) — никогда не хардкодить их в коде.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Telegram: два независимых бота ---
    CLIENT_BOT_TOKEN: str          # токен основного (клиентского) бота
    SUPPORT_BOT_TOKEN: str         # токен приватного бота поддержки
    SUPPORT_CHAT_ID: int           # твой личный telegram_id — только сюда бот поддержки будет писать/принимать

    # --- База данных ---
    # По умолчанию SQLite для разработки. Для продакшена — Postgres:
    # postgresql+asyncpg://user:password@host:5432/dbname
    DATABASE_URL: str = "sqlite+aiosqlite:///./esim_bot.db"

    # --- eSIM Access API ---
    ESIMACCESS_ACCESS_CODE: str = ""   # ключ из личного кабинета esimaccess (заголовок RT-AccessCode)
    # Секрет вебхуков esimaccess не подписывает запросы — но можно ограничить приём
    # по их IP (см. app/webapp/webhooks.py) через этот флаг.
    ESIMACCESS_WEBHOOK_ENFORCE_IP_ALLOWLIST: bool = False

    # --- Админ-панель ---
    ADMIN_PANEL_SECRET_KEY: str = "change-me"   # для подписи сессионной cookie
    ADMIN_PANEL_LOGIN: str = "admin"
    ADMIN_PANEL_PASSWORD: str = "change-me"

    # --- Сайт (app/webapp/shop.py) — сессия для логина покупателей ---
    SHOP_SESSION_SECRET_KEY: str = "change-me-too"

    # --- Email (восстановление пароля на сайте) ---
    # Если SMTP_HOST пуст — письма не отправляются, но ссылка на сброс пароля
    # дублируется тебе в бот поддержки, чтобы можно было тестировать до того,
    # как настроишь реальную почту.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@example.com"
    SMTP_FROM_NAME: str = "eSIM Store"  # то, что клиент увидит как имя отправителя вместо голого адреса
    SMTP_USE_TLS: bool = True

    # --- Оплата: Idram (AMD, карты/счёт Idram) ---
    # Протокол EDP полностью подтверждён официальным документом "Idram Payment
    # System merchant interface description" — включая сам адрес хостед-страницы.
    IDRAM_REC_ACCOUNT: str = ""        # твой IdramID (EDP_REC_ACCOUNT)
    IDRAM_SECRET_KEY: str = ""         # секретный ключ, выдаёт Idram
    IDRAM_PAYMENT_URL: str = "https://banking.idram.am/Payment/GetPayment"

    # --- Оплата: Wallet Pay (Telegram-кошелёк — покрывает и крипту, и сам Telegram Wallet) ---
    # Подтверждено официальной документацией https://docs.wallet.tg/pay/
    WALLET_PAY_API_KEY: str = ""       # токен из https://pay.wallet.tg/

    # --- Оплата: OxaPay (крипта с ЛЮБОГО адреса/биржи — напр. вывод прямо с Bybit,
    # без необходимости заводить Telegram Wallet). Подтверждено официальной
    # документацией https://docs.oxapay.com/ (включая формулу подписи вебхука).
    OXAPAY_MERCHANT_API_KEY: str = ""  # ключ из личного кабинета oxapay.com, раздел Merchant

    # Публичный адрес этого же процесса (app/webapp) — нужен для RESULT_URL/SUCCESS_URL/FAIL_URL
    # у Idram и для колбэков. Обычно совпадает с MINIAPP_URL без пути /miniapp.
    PUBLIC_BASE_URL: str = "https://example.com"

    # --- Mini App ---
    # Публичный HTTPS-адрес, где будет жить Mini App (нужен для кнопки в боте).
    # Для локальной разработки можно временно прокинуть через ngrok/cloudflared.
    MINIAPP_URL: str = "https://example.com/miniapp"

    # --- Тестовая оплата ---
    # Включает кнопку "🧪 Тестовая оплата" в чекауте Mini App — сразу помечает заказ
    # оплаченным и по-настоящему отправляет его в esimaccess (спишет с баланса),
    # без реального платёжного провайдера. Для проверки всей цепочки как настоящий
    # клиент — QR придёт в "Мои eSIM" именно тому, кто нажал.
    # ОБЯЗАТЕЛЬНО выключить (false) перед реальным запуском для клиентов — иначе
    # любой клиент сможет "оплатить" заказ бесплатно.
    ENABLE_TEST_PAYMENT: bool = False

    # --- Включение/выключение отдельных способов оплаты ---
    # Пока не готов Wallet Pay/OxaPay (нет ключа, не зарегистрировался) — можно
    # временно скрыть кнопку в интерфейсе, оставив только Idram. Это не удаляет
    # интеграцию из кода — просто прячет кнопку И блокирует сам эндпоинт на
    # сервере (на случай прямого обращения в обход кнопки).
    ENABLE_WALLET_PAY: bool = True
    ENABLE_OXAPAY: bool = True


    # --- Безопасность ---
    # На Railway (или любом хостинге за HTTPS) обязательно поставь true — тогда
    # сессионные cookie (админки и сайта) будут отправляться только по HTTPS.
    # Локально при разработке (http://localhost) оставь false, иначе логин не
    # сохранится — браузер просто не примет cookie без https.
    SECURE_COOKIES: bool = False

    # Наценка по умолчанию при импорте пакетов из esimaccess (см. /packages/import
    # в админке) — например 50 значит цена клиенту = закупочная × 1.5. Можно
    # менять цену вручную у каждого пакета после импорта, это только стартовое значение.
    ESIMACCESS_DEFAULT_MARKUP_PERCENT: float = 50.0


settings = Settings()
