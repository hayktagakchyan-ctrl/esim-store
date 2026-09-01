"""
Переводы для сайта (app/webapp/shop.py) — страницы рендерятся сервером (Jinja2),
не SPA, поэтому язык хранится в cookie, а не в JS-переменной, как в Mini App.
"""
from fastapi import Request

TRANSLATIONS: dict[str, dict[str, str]] = {
    "brand": {"ru": "KaLine", "hy": "KaLine", "en": "KaLine"},

    "nav_catalog": {"ru": "Тарифы", "hy": "Սակագներ", "en": "Plans"},
    "nav_services": {"ru": "Другие услуги", "hy": "Այլ ծառայություններ", "en": "Other services"},
    "nav_login": {"ru": "Войти", "hy": "Մուտք", "en": "Log in"},
    "nav_register": {"ru": "Регистрация", "hy": "Գրանցում", "en": "Sign up"},
    "nav_logout": {"ru": "Выйти", "hy": "Ելք", "en": "Log out"},
    "nav_my_orders": {"ru": "Мои заказы", "hy": "Իմ պատվերները", "en": "My orders"},
    "nav_my_chats": {"ru": "Мои чаты", "hy": "Իմ չաթերը", "en": "My chats"},

    "hero_title": {
        "ru": "Интернет в поездке — за пару минут",
        "hy": "Ինտերնետ ճամփորդության ընթացքում՝ մի քանի րոպեում",
        "en": "Travel data, ready in minutes",
    },
    "hero_subtitle": {
        "ru": "eSIM для более чем 100 стран. Оплата картой или криптой, QR-код сразу после оплаты — без походов в салон связи и без роуминга.",
        "hy": "eSIM ավելի քան 100 երկրների համար։ Վճարում քարտով կամ կրիպտոյով, QR-կոդ՝ անմիջապես վճարումից հետո։",
        "en": "eSIM data for 100+ countries. Pay by card or crypto, get your QR code instantly — no roaming fees, no SIM shops.",
    },
    "hero_cta": {"ru": "Выбрать тариф", "hy": "Ընտրել սակագին", "en": "Browse plans"},

    "feature_countries_title": {"ru": "100+ стран", "hy": "100+ երկիր", "en": "100+ countries"},
    "feature_countries_desc": {
        "ru": "От отдельных стран до целых регионов — Европа, Азия, обе Америки.",
        "hy": "Առանձին երկրներից մինչև ամբողջ տարածաշրջաններ։",
        "en": "From single countries to whole regions — Europe, Asia, the Americas.",
    },
    "feature_instant_title": {"ru": "Мгновенная выдача", "hy": "Ակնթարթային տրամադրում", "en": "Instant delivery"},
    "feature_instant_desc": {
        "ru": "QR-код появляется сразу после подтверждения оплаты — активируй перед вылетом.",
        "hy": "QR-կոդը հայտնվում է վճարման հաստատումից անմիջապես հետո։",
        "en": "Your QR code appears right after payment — activate before you fly.",
    },
    "feature_payment_title": {"ru": "Гибкая оплата", "hy": "Ճկուն վճարում", "en": "Flexible payment"},
    "feature_payment_desc": {
        "ru": "Банковская карта через Idram или криптовалюта — выбирай удобное.",
        "hy": "Բանկային քարտ Idram-ով կամ կրիպտոարժույթ։",
        "en": "Bank card via Idram, or crypto — whichever you prefer.",
    },

    "how_title": {"ru": "Как это работает", "hy": "Ինչպես է դա աշխատում", "en": "How it works"},
    "how_step1_title": {"ru": "Выбери страну и тариф", "hy": "Ընտրիր երկիրը և սակագինը", "en": "Pick a country & plan"},
    "how_step2_title": {"ru": "Оплати", "hy": "Վճարիր", "en": "Pay"},
    "how_step3_title": {"ru": "Активируй eSIM", "hy": "Ակտիվացրու eSIM-ը", "en": "Activate your eSIM"},
    "how_step3_desc": {
        "ru": "Отсканируй QR-код в настройках телефона — готово.",
        "hy": "Սկանավորիր QR-կոդը հեռախոսի կարգավորումներում։",
        "en": "Scan the QR code in your phone settings — done.",
    },

    "catalog_title": {"ru": "Выбери страну", "hy": "Ընտրիր երկիրը", "en": "Choose a country"},
    "back_to_countries": {"ru": "← Все страны", "hy": "← Բոլոր երկրները", "en": "← All countries"},
    "back_to_plans": {"ru": "← Назад к тарифам", "hy": "← Հետ սակագներին", "en": "← Back to plans"},

    "checkout_title": {"ru": "Оформление заказа", "hy": "Պատվերի ձևակերպում", "en": "Checkout"},
    "checkout_login_required": {
        "ru": "Чтобы оформить заказ, нужно войти в аккаунт — это займёт минуту.",
        "hy": "Պատվեր կատարելու համար պետք է մուտք գործել հաշիվ։",
        "en": "You need to be logged in to place an order — it only takes a minute.",
    },
    "checkout_pay_idram": {"ru": "Оплатить картой через Idram", "hy": "Վճարել քարտով Idram-ով", "en": "Pay by card via Idram"},
    "checkout_pay_oxapay": {"ru": "Оплатить криптовалютой", "hy": "Վճարել կրիպտոարժույթով", "en": "Pay with crypto"},
    "checkout_hint": {
        "ru": "После оплаты откроется страница заказа с QR-кодом активации — сохрани на неё ссылку.",
        "hy": "Վճարումից հետո կբացվի պատվերի էջը՝ ակտիվացման QR-կոդով։",
        "en": "After payment you'll see your order page with the activation QR code — save the link.",
    },
    "activation_code_label": {
        "ru": "Код активации (если QR не сканируется):",
        "hy": "Ակտիվացման կոդ (եթե QR-ը չի սկանավորվում)․",
        "en": "Activation code (if the QR won't scan):",
    },
    "logged_in_as": {"ru": "Вошёл как", "hy": "Մուտք եք գործել որպես", "en": "Logged in as"},

    "register_title": {"ru": "Регистрация", "hy": "Գրանցում", "en": "Create an account"},
    "login_title": {"ru": "Вход", "hy": "Մուտք", "en": "Log in"},
    "email_label": {"ru": "Email", "hy": "Էլ. փոստ", "en": "Email"},
    "password_label": {"ru": "Пароль", "hy": "Գաղտնաբառ", "en": "Password"},
    "register_submit": {"ru": "Создать аккаунт", "hy": "Ստեղծել հաշիվ", "en": "Create account"},
    "login_submit": {"ru": "Войти", "hy": "Մուտք", "en": "Log in"},
    "no_account_yet": {"ru": "Ещё нет аккаунта?", "hy": "Դեռ հաշիվ չունե՞ք։", "en": "Don't have an account?"},
    "have_account": {"ru": "Уже есть аккаунт?", "hy": "Արդեն ունե՞ք հաշիվ։", "en": "Already have an account?"},
    "forgot_password_link": {"ru": "Забыли пароль?", "hy": "Մոռացե՞լ եք գաղտնաբառը։", "en": "Forgot password?"},
    "forgot_password_title": {"ru": "Восстановление пароля", "hy": "Գաղտնաբառի վերականգնում", "en": "Reset password"},
    "forgot_password_submit": {"ru": "Отправить ссылку", "hy": "Ուղարկել հղումը", "en": "Send reset link"},
    "forgot_password_sent": {
        "ru": "Если такой email зарегистрирован — на него отправлена ссылка для сброса пароля.",
        "hy": "Եթե այդպիսի էլ. փոստ գրանցված է, ուղարկվել է հղում գաղտնաբառը վերականգնելու համար։",
        "en": "If that email is registered, a password reset link has been sent to it.",
    },
    "check_email_title": {"ru": "Проверь почту", "hy": "Ստուգիր փոստդ", "en": "Check your email"},
    "check_email_text": {
        "ru": "Мы отправили письмо со ссылкой для подтверждения на",
        "hy": "Հաստատման հղումով նամակ ուղարկվել է հասցեին՝",
        "en": "We sent a confirmation link to",
    },
    "resend_verification": {"ru": "Отправить письмо ещё раз", "hy": "Կրկին ուղարկել նամակը", "en": "Resend email"},
    "verify_email_title": {"ru": "Подтверждение email", "hy": "Էլ. փոստի հաստատում", "en": "Email verification"},
    "verify_email_success": {
        "ru": "Email подтверждён — теперь можно оформлять заказы и писать в чат.",
        "hy": "Էլ. փոստը հաստատված է — այժմ կարող եք պատվիրել և գրել չաթում։",
        "en": "Email confirmed — you can now check out and use chat.",
    },
    "verify_email_expired": {
        "ru": "Ссылка устарела (действует 48 часов). Запроси новую.",
        "hy": "Հղումը հնացել է (գործում է 48 ժամ)։ Խնդրիր նոր հղում։",
        "en": "This link has expired (valid for 48 hours). Request a new one.",
    },
    "verify_email_invalid": {
        "ru": "Ссылка недействительна — возможно, email уже подтверждён ранее.",
        "hy": "Հղումն անվավեր է․ գուցե էլ. փոստն արդեն հաստատված է։",
        "en": "This link is invalid — the email may already be verified.",
    },
    "reset_password_title": {"ru": "Новый пароль", "hy": "Նոր գաղտնաբառ", "en": "Set a new password"},
    "reset_password_submit": {"ru": "Сохранить пароль", "hy": "Պահպանել գաղտնաբառը", "en": "Save password"},
    "reset_password_invalid": {
        "ru": "Ссылка недействительна или устарела — запросите новую.",
        "hy": "Հղումն անվավեր է կամ ժամկետանց է․ պահանջեք նոր հղում։",
        "en": "This link is invalid or has expired — please request a new one.",
    },

    "my_orders_title": {"ru": "Мои заказы", "hy": "Իմ պատվերները", "en": "My orders"},
    "my_orders_empty": {"ru": "Пока нет заказов.", "hy": "Դեռ պատվերներ չկան։", "en": "No orders yet."},

    "services_title": {"ru": "Другие услуги", "hy": "Այլ ծառայություններ", "en": "Other services"},
    "services_empty": {"ru": "Пока ничего нет — загляните позже.", "hy": "Դեռ ոչինչ չկա։", "en": "Nothing here yet — check back later."},
    "product_ask_button": {"ru": "Спросить в чате", "hy": "Հարցնել չաթում", "en": "Ask in chat"},
    "my_chats_title": {"ru": "Мои чаты", "hy": "Իմ չաթերը", "en": "My chats"},
    "my_chats_empty": {"ru": "Пока нет ни одного чата.", "hy": "Դեռ ոչ մի չաթ չկա։", "en": "No chats yet."},
    "new_support_chat": {"ru": "🆘 Написать в поддержку", "hy": "🆘 Գրել աջակցությանը", "en": "🆘 Contact support"},
    "chat_input_placeholder": {"ru": "Напиши сообщение…", "hy": "Գրիր հաղորդագրություն…", "en": "Type a message…"},
    "topic_support": {"ru": "Поддержка", "hy": "Աջակցություն", "en": "Support"},

    "status_pending_payment": {"ru": "Ждёт оплаты", "hy": "Սպասում է վճարման", "en": "Awaiting payment"},
    "status_paid": {"ru": "Оплачен, готовим eSIM", "hy": "Վճարված է, պատրաստում ենք", "en": "Paid, preparing your eSIM"},
    "status_provisioning": {"ru": "Оформляется", "hy": "Ձևակերպվում է", "en": "Processing"},
    "status_active": {"ru": "Активен", "hy": "Ակտիվ է", "en": "Active"},
    "status_failed": {"ru": "Ошибка оформления — напишите нам", "hy": "Սխալ․ գրեք մեզ", "en": "Error — please contact us"},
    "status_refunded": {"ru": "Возврат оформлен", "hy": "Վերադարձը կատարված է", "en": "Refunded"},

    "footer_bot_teaser": {
        "ru": "Также в нашем Telegram-боте: доступ в лаунж-зоны аэропортов и туры.",
        "hy": "Նաև մեր Telegram-բոտում՝ օդանավակայանի լաունջ հասանելիություն և տուրեր։",
        "en": "Also in our Telegram bot: airport lounge access and tours.",
    },

    "footer_privacy_link": {"ru": "Политика конфиденциальности", "hy": "Գաղտնիության քաղաքականություն", "en": "Privacy Policy"},
    "footer_terms_link": {"ru": "Условия использования", "hy": "Օգտագործման պայմաններ", "en": "Terms of Service"},
    "agree_to_terms": {
        "ru": 'Регистрируясь, я соглашаюсь с <a href="/shop/terms">условиями использования</a> и <a href="/shop/privacy">политикой конфиденциальности</a>.',
        "hy": 'Գրանցվելով՝ ես համաձայն եմ <a href="/shop/terms">օգտագործման պայմաններին</a> և <a href="/shop/privacy">գաղտնիության քաղաքականությանը</a>։',
        "en": 'By registering, I agree to the <a href="/shop/terms">Terms of Service</a> and <a href="/shop/privacy">Privacy Policy</a>.',
    },

    "privacy_title": {"ru": "Политика конфиденциальности", "hy": "Գաղտնիության քաղաքականություն", "en": "Privacy Policy"},
    "privacy_body": {
        "ru": """
<p><strong>Какие данные мы собираем.</strong> Email и пароль (хранится не в открытом виде,
а в виде хеша — мы сами не можем его увидеть), история твоих заказов (какой пакет/услугу
купил, статус, цена), переписка в чате поддержки/лаунжа/туров, если ты им пользовался.
IP-адрес используется только для защиты от подбора пароля и злоупотреблений.</p>
<p><strong>Зачем.</strong> Чтобы оформить и выдать твой заказ, показать историю покупок,
ответить на вопросы в чате, защититься от мошенничества.</p>
<p><strong>С кем делимся.</strong> С платёжными системами (Idram, OxaPay) — только то, что
нужно для проведения платежа. С esimaccess.com — данные о купленном пакете, чтобы выпустить
eSIM. Мы не продаём и не передаём твои данные никому ещё.</p>
<p><strong>Cookies.</strong> Используем один служебный cookie для входа в аккаунт — без него
сайт не запомнит, что ты вошёл.</p>
<p><strong>Сколько храним.</strong> Пока существует твой аккаунт, либо пока это требуется по
закону (например, для бухгалтерского учёта).</p>
<p><strong>Твои права.</strong> Можешь запросить удаление аккаунта и своих данных — напиши в
поддержку через бот.</p>
""",
        "hy": """
<p><strong>Ինչ տվյալներ ենք հավաքում։</strong> Էլ. փոստ և գաղտնաբառ (պահվում է ոչ
բացահայտ տեսքով, այլ որպես հեշ), քո պատվերների պատմությունը (ինչ ես գնել, կարգավիճակ,
գին), նամակագրությունը չաթում, եթե օգտվել ես դրանից։ IP-հասցեն օգտագործվում է միայն
գաղտնաբառի ենթադրման դեմ պաշտպանության համար։</p>
<p><strong>Ինչու։</strong> Պատվերդ ձևակերպելու և տրամադրելու, գնումների պատմությունը
ցույց տալու, չաթում հարցերին պատասխանելու, խարդախությունից պաշտպանվելու համար։</p>
<p><strong>Ում հետ ենք կիսվում։</strong> Վճարային համակարգերի հետ (Idram, OxaPay) — միայն
վճարման համար անհրաժեշտ տվյալները։ esimaccess.com-ի հետ՝ գնված փաթեթի մասին տվյալները՝
eSIM թողարկելու համար։ Քո տվյալները ոչ ոքի չենք վաճառում։</p>
<p><strong>Cookies.</strong> Օգտագործում ենք մեկ ծառայողական cookie՝ հաշվի մուտքի համար։</p>
<p><strong>Որքա՞ն ենք պահում։</strong> Քանի դեռ գոյություն ունի քո հաշիվը, կամ քանի դեռ դա
պահանջվում է օրենքով։</p>
<p><strong>Քո իրավունքները։</strong> Կարող ես պահանջել հաշվի և տվյալների ջնջում՝ գրելով
աջակցությանը բոտի միջոցով։</p>
""",
        "en": """
<p><strong>What we collect.</strong> Your email and password (stored as a hash, never in
plain text — we can't see it either), your order history (what you bought, status, price),
support/lounge/tour chat messages if you've used them. Your IP address is used only for
abuse and brute-force protection.</p>
<p><strong>Why.</strong> To process and deliver your orders, show your purchase history,
answer chat questions, and protect against fraud.</p>
<p><strong>Who we share it with.</strong> Payment providers (Idram, OxaPay) — only what's
needed to process payment. esimaccess.com — your purchased package details, to issue the
eSIM. We do not sell your data to anyone.</p>
<p><strong>Cookies.</strong> One functional cookie to keep you logged in.</p>
<p><strong>Retention.</strong> As long as your account exists, or as required by law (e.g.
accounting).</p>
<p><strong>Your rights.</strong> You can request account and data deletion — contact support
via the bot.</p>
""",
    },

    "terms_title": {"ru": "Условия использования", "hy": "Օգտագործման պայմաններ", "en": "Terms of Service"},
    "terms_body": {
        "ru": """
<p>Мы продаём цифровые товары и услуги: eSIM с мобильным интернетом, доступ в лаунж-зоны
аэропортов, туры. Выдача eSIM зависит от партнёра esimaccess.com — в редких случаях
возможна задержка или отказ на их стороне, о чём мы сообщим и поможем решить вопрос
(возврат или замена).</p>
<p><strong>Оплата.</strong> Цены указаны в валюте пакета. Оплата — картой через Idram или
криптовалютой. Оплачивая заказ, ты подтверждаешь, что данные карты/кошелька принадлежат
тебе.</p>
<p><strong>Возврат.</strong> Если что-то пошло не так с твоим заказом — напиши в поддержку,
разберём ситуацию индивидуально.</p>
<p><strong>Аккаунт.</strong> Один человек — один аккаунт. Ты отвечаешь за сохранность своего
пароля. Сервис предназначен для лиц старше 18 лет (или совершеннолетия по законам твоей
страны).</p>
<p><strong>Лаунж и туры</strong> оформляются через переписку с нами — итоговые условия и
цена согласовываются в чате перед оплатой.</p>
<p><strong>Ограничение ответственности.</strong> Мы не несём ответственности за перебои в
работе сторонних сервисов (esimaccess, платёжные системы, сотовые операторы), от которых
зависит предоставление услуги.</p>
""",
        "hy": """
<p>Մենք վաճառում ենք թվային ապրանքներ և ծառայություններ՝ eSIM ինտերնետով, օդանավակայանի
լաունջ հասանելիություն, տուրեր։ eSIM-ի տրամադրումը կախված է esimaccess.com գործընկերոջից՝
հազվադեպ հնարավոր է ուշացում կամ մերժում նրանց կողմից, որի մասին կտեղեկացնենք և
կօգնենք լուծել հարցը (վերադարձ կամ փոխարինում)։</p>
<p><strong>Վճարում։</strong> Գները նշված են փաթեթի արժույթով։ Վճարումը՝ քարտով Idram-ի
միջոցով կամ կրիպտոարժույթով։</p>
<p><strong>Վերադարձ։</strong> Եթե ինչ-որ բան այն չէ քո պատվերի հետ՝ գրիր աջակցությանը,
կքննարկենք առանձին։</p>
<p><strong>Հաշիվ։</strong> Մեկ մարդ՝ մեկ հաշիվ։ Դու պատասխանատու ես գաղտնաբառիդ
պահպանման համար։ Ծառայությունը նախատեսված է 18 տարեկանից բարձր անձանց համար։</p>
<p><strong>Լաունջ և տուրեր</strong> ձևակերպվում են մեզ հետ նամակագրության միջոցով՝
վերջնական պայմանները և գինը համաձայնեցվում են չաթում մինչ վճարումը։</p>
<p><strong>Պատասխանատվության սահմանափակում։</strong> Մենք պատասխանատվություն չենք կրում
երրորդ կողմի ծառայությունների (esimaccess, վճարային համակարգեր, օպերատորներ) խափանումների
համար, որոնցից կախված է ծառայության մատուցումը։</p>
""",
        "en": """
<p>We sell digital goods and services: eSIM data plans, airport lounge access, and tours.
eSIM delivery depends on our partner esimaccess.com — in rare cases there may be a delay or
failure on their end, which we'll notify you about and help resolve (refund or replacement).</p>
<p><strong>Payment.</strong> Prices are shown in the package's currency. Payment is by card
via Idram or by crypto. By paying, you confirm the card/wallet used belongs to you.</p>
<p><strong>Refunds.</strong> If something went wrong with your order, contact support and
we'll review it individually.</p>
<p><strong>Account.</strong> One person, one account. You're responsible for keeping your
password secure. This service is intended for users 18 years or older (or the age of
majority in your jurisdiction).</p>
<p><strong>Lounge and tours</strong> are arranged through chat with us — final terms and
price are agreed in chat before payment.</p>
<p><strong>Limitation of liability.</strong> We are not liable for outages of third-party
services (esimaccess, payment providers, mobile carriers) that the service depends on.</p>
""",
    },

    "password_confirm_label": {"ru": "Повтори пароль", "hy": "Կրկնիր գաղտնաբառը", "en": "Confirm password"},
    "show_all_countries": {"ru": "Показать все страны", "hy": "Ցույց տալ բոլոր երկրները", "en": "Show all countries"},

    "nav_support": {"ru": "Поддержка", "hy": "Աջակցություն", "en": "Support"},
    "nav_settings": {"ru": "Настройки", "hy": "Կարգավորումներ", "en": "Settings"},

    "settings_title": {"ru": "Настройки аккаунта", "hy": "Հաշվի կարգավորումներ", "en": "Account settings"},
    "settings_email_label": {"ru": "Email аккаунта", "hy": "Հաշվի էլ. փոստ", "en": "Account email"},
    "settings_change_password_title": {"ru": "Сменить пароль", "hy": "Փոխել գաղտնաբառը", "en": "Change password"},
    "current_password_label": {"ru": "Текущий пароль", "hy": "Ընթացիկ գաղտնաբառ", "en": "Current password"},
    "new_password_label": {"ru": "Новый пароль", "hy": "Նոր գաղտնաբառ", "en": "New password"},
    "new_password_confirm_label": {"ru": "Повтори новый пароль", "hy": "Կրկնիր նոր գաղտնաբառը", "en": "Confirm new password"},
    "settings_save_button": {"ru": "Сохранить", "hy": "Պահպանել", "en": "Save"},
    "settings_password_changed": {"ru": "Пароль изменён.", "hy": "Գաղտնաբառը փոխվել է։", "en": "Password changed."},
    "settings_password_wrong_current": {"ru": "Текущий пароль указан неверно.", "hy": "Ընթացիկ գաղտնաբառը սխալ է։", "en": "Current password is incorrect."},
    "settings_password_mismatch": {"ru": "Новые пароли не совпадают.", "hy": "Նոր գաղտնաբառերը չեն համընկնում։", "en": "New passwords don't match."},
    "password_too_short": {"ru": "Пароль должен быть не короче 8 символов.", "hy": "Գաղտնաբառը պետք է լինի առնվազն 8 նիշ։", "en": "Password must be at least 8 characters."},

    "faq_title": {"ru": "Частые вопросы", "hy": "Հաճախակի հարցեր", "en": "FAQ"},
    "faq_q1": {"ru": "Как быстро активируется eSIM?", "hy": "Որքա՞ն արագ է ակտիվանում eSIM-ը", "en": "How fast does the eSIM activate?"},
    "faq_a1": {
        "ru": "Сразу после подтверждения оплаты — QR-код появляется на странице заказа обычно в течение минуты.",
        "hy": "Վճարման հաստատումից անմիջապես հետո՝ QR-կոդը սովորաբար հայտնվում է րոպեների ընթացքում։",
        "en": "Right after payment confirmation — the QR code usually appears within a minute.",
    },
    "faq_q2": {"ru": "Нужен ли отдельный номер телефона?", "hy": "Անհրաժե՞շտ է առանձին հեռախոսահամար", "en": "Do I need a separate phone number?"},
    "faq_a2": {
        "ru": "Нет — eSIM даёт только интернет, звонки и СМС остаются на твоей основной SIM-карте.",
        "hy": "Ոչ, eSIM-ը տալիս է միայն ինտերնետ, զանգերն ու SMS-ները մնում են հիմնական SIM-ի վրա։",
        "en": "No — the eSIM only provides data; calls and SMS stay on your regular SIM.",
    },
    "faq_q3": {"ru": "Что если оплата прошла, а eSIM не пришёл?", "hy": "Իսկ եթե վճարումը եղավ, բայց eSIM-ը չեկա՞վ", "en": "What if I paid but didn't receive the eSIM?"},
    "faq_a3": {
        "ru": "Напиши нам в поддержку прямо на сайте (кнопка в шапке) или в Telegram-боте — разберёмся быстро.",
        "hy": "Գրիր մեզ աջակցությանը կայքում (կոճակը վերևում) կամ Telegram-բոտում — արագ կլուծենք։",
        "en": "Message support right here on the site (button in the header) or via the Telegram bot — we'll sort it out fast.",
    },
    "faq_q4": {"ru": "На каких устройствах работает eSIM?", "hy": "Ո՞ր սարքերում է աշխատում eSIM-ը", "en": "Which devices support eSIM?"},
    "faq_a4": {
        "ru": "На большинстве смартфонов последних лет (iPhone начиная с XR/XS, многие Android-флагманы). Перед покупкой проверь в настройках телефона, поддерживает ли он eSIM.",
        "hy": "Վերջին տարիների սմարթֆոնների մեծ մասում (iPhone XR/XS-ից սկսած, շատ Android-ֆլագմաններ)։",
        "en": "Most recent smartphones (iPhone XR/XS and later, many Android flagships). Check your phone's settings before buying to confirm eSIM support.",
    },
}


def get_lang(request: Request) -> str:
    cookie_lang = request.cookies.get("site_lang")
    if cookie_lang in ("ru", "hy", "en"):
        return cookie_lang
    accept_language = request.headers.get("accept-language", "")
    if accept_language.startswith("hy"):
        return "hy"
    if accept_language.startswith("en"):
        return "en"
    return "ru"


def t(key: str, lang: str) -> str:
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get("ru", key))