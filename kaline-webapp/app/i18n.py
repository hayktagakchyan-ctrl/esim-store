"""
Простой словарь переводов для сообщений бота (не Mini App — там свой, в
app/webapp/static/i18n.js, с тем же набором языков).

Язык определяется по Telegram language_code пользователя: "hy" -> армянский,
"en" (и производные "en-US" и т.п.) -> английский, всё остальное -> русский
по умолчанию (это язык, на котором чаще всего пишет сама аудитория магазина).
"""

TRANSLATIONS: dict[str, dict[str, str]] = {
    "welcome": {
        "ru": "Привет! Здесь можно купить eSIM с интернетом, доступ в лаунж-зону "
              "аэропорта или тур — выбирай, что нужно, в магазине.",
        "hy": "Բարև! Այստեղ կարող ես գնել eSIM ինտերնետով, օդանավակայանի "
              "լաունջ հասանելիություն կամ տուր — ընտրիր, ինչ է պետք, խանութում։",
        "en": "Hi! Here you can buy an eSIM with data, airport lounge access, or a "
              "tour — open the shop and pick what you need.",
    },
    "open_shop_button": {
        "ru": "🛍 Открыть магазин",
        "hy": "🛍 Բացել խանութը",
        "en": "🛍 Open shop",
    },
    "use_shop_button_hint": {
        "ru": "Всё — каталог, покупки, переписка — внутри магазина 👇",
        "hy": "Ամեն ինչ՝ կատալոգը, գնումները, նամակագրությունը՝ խանութի ներսում 👇",
        "en": "Everything — catalog, purchases, chat — happens inside the shop 👇",
    },
    "support_new_message_admin": {
        # Всегда на русском — это видит только владелец в приватном боте поддержки,
        # он один, язык клиента здесь не имеет значения.
        "ru": "🆕 Новое сообщение\nОт: {name}\nТема: {topic}\n\n{preview}",
    },
    "open_chats_button": {
        "ru": "💬 Открыть чаты",
    },
}


def t(key: str, lang: str) -> str:
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get("ru", key))


def detect_lang(language_code: str | None) -> str:
    if not language_code:
        return "ru"
    code = language_code.lower()
    if code.startswith("hy"):
        return "hy"
    if code.startswith("en"):
        return "en"
    return "ru"
