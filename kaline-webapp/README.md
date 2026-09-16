# eSIM Store — Telegram-боты + Mini App + админка

Три вида товаров для клиента: **eSIM** (полностью автоматически — оплата → esimaccess
→ QR), и **лаунж-доступ**/**туры** (это карточки, которые ты вносишь вручную через
админку — вместо оплаты клиент сразу попадает в чат с тобой, детали и цену обсуждаете
там). Всё клиентское — на трёх языках: русский, հայերեն, English.

Четыре независимых процесса, одна база данных:

1. **Клиентский бот** (`app/main.py`, часть) — предельно простой: одна кнопка
   «Открыть магазин» (web_app). Всё остальное — внутри Mini App.
2. **Бот поддержки** (`app/main.py`, часть) — приватный, пускает только тебя,
   открывает твой отдельный Mini App-инбокс чатов (см. ниже).
3. **Mini App** (`app/webapp/app.py`) — здесь ДВЕ разные Mini App на одном
   процессе: клиентский магазин (`/`: eSIM + лаунж + туры + «Мои eSIM» + чаты)
   и приватный инбокс чатов для тебя (`/support-chat/`, отдельная авторизация —
   пускает только твой telegram_id). Каждый запрос, отдающий персональные данные,
   проверяет подпись `initData` от Telegram (см. `app/webapp/auth.py`).
4. **Админ-панель** (`app/admin_panel/app.py`) — веб-интерфейс: заказы, пакеты eSIM,
   товары (лаунж/туры). Запускается отдельно.

## Как устроен чат с клиентом (лаунж/туры/поддержка)

Вместо старой пересылки сообщений реплаями — полноценный Mini App-инбокс:
- Клиент выбирает лаунж/тур в своём Mini App → нажимает «Спросить в чате» →
  открывается переписка прямо там же, в приложении.
- Тебе в бот поддержки падает уведомление, ты жмёшь «Открыть чаты» → видишь
  список ВСЕХ разговоров (кто, по какой теме, последнее сообщение, непрочитанные) →
  открываешь нужный → отвечаешь как в обычном мессенджере.
- У каждого клиента отдельная тема (Conversation) на каждый вопрос — если он
  спросил и про тур, и про лаунж, это два разных чата, не смешиваются.

## Запуск (разработка)

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# заполнить .env: токены ботов, свой telegram_id, реквизиты esimaccess

# терминал 1 — боты
python -m app.main

# терминал 2 — админка
uvicorn app.admin_panel.app:app --reload --port 8000

# терминал 3 — Mini App
uvicorn app.webapp.app:app --reload --port 8001
```

Админка будет на http://localhost:8000 (логин/пароль — из `.env`).

## Mini App — что нужно, чтобы открылась в Telegram

Telegram требует HTTPS для `web_app`-кнопок — `http://localhost` из самого Telegram
не откроется. Для разработки проще всего пробросить порт 8001 через туннель
(`ngrok http 8001` или `cloudflared tunnel --url http://localhost:8001`) и вписать
выданный HTTPS-адрес в `MINIAPP_URL` в `.env`. Для прода — обычный домен с сертификатом,
проксирующий на порт 8001 (nginx/caddy).

Также впиши username бота в `app/webapp/static/app.js` (`BOT_USERNAME`) — используется
кнопкой «Открыть чат с ботом» на вкладке поддержки.

## Как узнать свой SUPPORT_CHAT_ID

Проще всего написать что угодно боту [@userinfobot](https://t.me/userinfobot) —
он пришлёт твой числовой telegram_id. Это и есть `SUPPORT_CHAT_ID`.

## Оплата — Idram, Wallet Pay и OxaPay

Реализовано три способа оплаты, все подключены в чекауте Mini App:

- **Idram** (`app/services/payments/idram.py`) — драмы, редирект на хостед-страницу
  Idram, подтверждение через двухфазный колбэк на `/webhooks/idram` (precheck, затем
  подтверждение с проверкой контрольной суммы). **Полностью подтверждено** официальным
  документом "Idram Payment System merchant interface description" — включая точный
  адрес хостед-страницы (`https://banking.idram.am/Payment/GetPayment`) и формулу
  чек-суммы. Неподтверждённых мест не осталось.
- **Wallet Pay** (`app/services/payments/wallet_pay.py`) — оплата прямо из Telegram
  (@wallet, TON/USDT/BTC), для тех, у кого крипта уже лежит в Telegram-кошельке.
  Подтверждено официальной документацией https://docs.wallet.tg/pay/. Подтверждение
  оплаты — через опрос статуса (Mini App дергает `/api/orders/{id}/payment-status`
  каждые 3 секунды), а не вебхук: их вебхук подписан, но точный формат независимо
  не подтверждён, поэтому выбран более надёжный путь.
- **OxaPay** (`app/services/payments/oxapay.py`) — крипта с ЛЮБОГО адреса или
  биржи (например, прямой вывод с Bybit), без необходимости заводить Telegram
  Wallet. Хорошо дополняет Wallet Pay для тех, у кого крипта не в Telegram, а на
  бирже. Полностью подтверждено официальной документацией https://docs.oxapay.com/
  — включая точную формулу подписи вебхука (HMAC-SHA512 сырого тела запроса, ключ —
  тот же `OXAPAY_MERCHANT_API_KEY`, заголовок `hmac`).

Из всех трёх провайдеров неподтверждённых мест теперь не осталось нигде, кроме
формата вебхука Wallet Pay (не критично — используется опрос статуса вместо него).

Все три провайдера пишут в общую таблицу `payments` (не в `orders` напрямую) — так у
одного заказа может быть несколько попыток оплаты (напр. клиент начал через Idram,
передумал, заплатил через OxaPay).

**Что нужно в `.env`, чтобы это заработало:**
`IDRAM_REC_ACCOUNT`, `IDRAM_SECRET_KEY`, `IDRAM_PAYMENT_URL` (см. выше),
`WALLET_PAY_API_KEY` (токен с https://pay.wallet.tg/), `OXAPAY_MERCHANT_API_KEY`
(ключ из личного кабинета oxapay.com, раздел Merchant — регистрация самостоятельная,
без договоров), `PUBLIC_BASE_URL` (публичный HTTPS-адрес того же процесса
`app/webapp`, что и `MINIAPP_URL`, — нужен Idram и OxaPay для redirect/callback URL).

После того как оплата подтверждена (`Order.status = PAID`), заказ автоматически
уходит в esimaccess (`create_order`, теперь подтверждён — см. раздел ниже) и
переходит в `PROVISIONING`.

## eSIM Access — что уже подтверждено, а что ещё нет

По официальной документации (Partner API, `api.esimaccess.com`) подтверждено и реализовано
в `app/services/esimaccess.py`:

- Авторизация — один заголовок `RT-AccessCode: <твой ключ>`, без HMAC-подписи.
- `balance/query`, `location/list`, `esim/usage/query` — рабочие методы клиента.
- `esim/order` ("Order Profiles", создание заказа) — подключено: как только оплата
  (Idram/Wallet Pay/OxaPay) подтверждается, `app/webapp/payments.py` сам вызывает
  `create_order(...)` и переводит заказ в `PROVISIONING`.
- `esim/query` ("Query All Allocated Profiles") — **полностью подтверждено**, включая
  то, что `pager` обязателен даже при запросе по orderNo, и реальные названия полей
  ответа (`qrCodeUrl` — картинка QR, `ac` — код активации для ручного ввода). Вебхук
  `ORDER_STATUS` (`app/webapp/webhooks.py`) сам его вызывает и заполняет заказ —
  цепочка Mini App → оплата → esimaccess → QR клиенту работает целиком без заглушек.
- Вебхуки — полностью реализованы под все 6 типов событий из документации, с
  дедупликацией по `notifyId`.

**Единственное, чего всё ещё не хватает** — страница **"Query All Data Packages"**
(список пакетов с ценами), нужна только для автоматического наполнения каталога.
Пока пакеты добавляются вручную через админку (`/packages`) — рабочий способ, не
блокирует покупку.

**Важно:** у esimaccess нет sandbox-окружения — тестировать нужно в реальном личном
кабинете за реальные деньги, отменяя тестовые заказы вручную. Не гонять массовые тесты.

**Настройка вебхука** (в личном кабинете esimaccess): указать
`https://<твой-домен>/webhooks/esimaccess` (тот же процесс и домен, что и Mini App —
см. `MINIAPP_URL`). При первом сохранении придёт тестовый `CHECK_HEALTH` — если не
пришёл, домен/маршрут настроены неверно.

## Что ещё нужно доделать перед запуском в бой

- **Синхронизация каталога** — периодическая задача (cron / APScheduler), которая тянет
  `esimaccess_client.list_packages()` (когда появится) и обновляет таблицу `packages`,
  применяя наценку (`sell_price = cost_price * маржа`). До этого момента пакеты
  добавляются вручную через админку (`/packages`) — рабочий способ, просто не
  автоматический. `location/list` уже можно использовать прямо сейчас, чтобы
  засеять список стран.
- **Продакшен-БД** — переключить `DATABASE_URL` на Postgres и добавить Alembic-миграции
  вместо `init_db()` (он просто создаёт таблицы, если их нет — не ок для последующих
  изменений схемы без потери данных, а после сегодняшних правок схема уже менялась).
- **Деплой** — все три процесса (боты, админка, Mini App/вебхуки) держать через
  systemd/supervisor/Docker, чтобы перезапускались при падении.

## Структура проекта

```
app/
  config.py              — все настройки (из .env)
  bots.py                 — экземпляры Bot для обоих ботов (общие на процесс)
  i18n.py                  — переводы для сообщений бота (ru/hy/en)
  main.py                   — точка входа, запускает оба бота
  database/
    models.py              — схема БД: User, Package, Order, Payment, WebhookEvent,
                              Product (лаунж/туры, на 3 языках), Conversation/ConversationMessage (чаты)
    db.py                   — async engine/session
  services/
    esimaccess.py           — клиент API esimaccess (что подтверждено — см. выше)
    payments/
      idram.py                — форма/чек-сумма/колбэк Idram (EDP)
      wallet_pay.py             — клиент Wallet Pay (крипта через Telegram-кошелёк)
      oxapay.py                  — клиент OxaPay (крипта с любого адреса/биржи)
  client_bot/
    keyboards.py            — одна кнопка "Открыть магазин" (web_app)
    handlers/
      catalog.py              — /start, больше почти ничего — всё в Mini App
  support_bot/
    handlers.py              — только показывает кнопку "Открыть чаты" (web_app)
  admin_panel/
    app.py                    — FastAPI: /login, /orders/*, /packages/*, /products/* (лаунж/туры)
    templates/, static/         — HTML-шаблоны и стили
  webapp/
    app.py                     — точка сборки: подключает все роутеры + две статики (см. ниже)
    products.py                 — /api/products (лаунж/туры для клиента, с lang=ru|hy|en)
    conversations.py              — чаты со стороны клиента: /api/conversations, .../messages
    admin_chat.py                  — чаты со стороны админа: /support-chat/api/* (список, ответ)
    payments.py                     — /api/orders/{id}/pay, /payment-status, /pay/idram/*, /webhooks/idram
    webhooks.py                      — приём вебхуков esimaccess (/webhooks/esimaccess)
    auth.py                           — initData: get_current_user (клиент) и get_admin_user (админ-чат)
    notify_bots.py                     — общие лёгкие Bot-инстансы для отправки уведомлений
    static/                              — клиентский Mini App: index.html/app.js/style.css/i18n.js
    support_chat_static/                  — админский Mini App-инбокс: index.html/app.js/style.css
```

