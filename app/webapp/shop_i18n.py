"""
Переводы для сайта (app/webapp/shop.py) — страницы рендерятся сервером (Jinja2),
не SPA, поэтому язык хранится в cookie, а не в JS-переменной, как в Mini App.
"""
from fastapi import Request

TRANSLATIONS: dict[str, dict[str, str]] = {
    "brand": {"ru": "KaLine", "hy": "KaLine", "en": "KaLine"},

    "nav_home": {"ru": "Главная", "hy": "Գլխավոր", "en": "Home"},
    "nav_catalog": {"ru": "Тарифы", "hy": "Սակագներ", "en": "Plans"},
    "nav_services": {"ru": "Другие услуги", "hy": "Այլ ծառայություններ", "en": "Other services"},
    "nav_login": {"ru": "Войти", "hy": "Մուտք", "en": "Log in"},
    "nav_register": {"ru": "Регистрация", "hy": "Գրանցում", "en": "Sign up"},
    "nav_logout": {"ru": "Выйти", "hy": "Ելք", "en": "Log out"},
    "nav_my_orders": {"ru": "Мои заказы", "hy": "Իմ պատվերները", "en": "My orders"},
    "nav_my_chats": {"ru": "Мои чаты", "hy": "Իմ չաթերը", "en": "My chats"},

    "hero_badge": {
        "ru": "Твой цифровой роуминг",
        "hy": "Քո թվային ռոումինգը",
        "en": "Your digital roaming",
    },
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
    "home_view_all": {"ru": "Все направления", "hy": "Բոլոր ուղղությունները", "en": "All destinations"},
    "home_top_pick": {"ru": "Топ выбор", "hy": "Թոփ ընտրություն", "en": "Top pick"},
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
    "checkout_pay_stripe": {"ru": "Оплатить картой (Stripe)", "hy": "Վճարել քարտով (Stripe)", "en": "Pay by card (Stripe)"},
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
    "product_order_button": {"ru": "Заказать", "hy": "Պատվիրել", "en": "Order"},
    "product_estimated_price": {"ru": "Ориентировочная цена", "hy": "Մոտավոր գին", "en": "Estimated price"},
    "answer_yes": {"ru": "Да", "hy": "Այո", "en": "Yes"},
    "answer_no": {"ru": "Нет", "hy": "Ոչ", "en": "No"},
    "service_request_submit": {"ru": "Отправить заявку", "hy": "Ուղարկել հայտը", "en": "Submit request"},
    "nav_service_requests": {"ru": "Мои заявки", "hy": "Իմ հայտերը", "en": "My requests"},
    "service_status_submitted": {"ru": "На рассмотрении", "hy": "Դիտարկման փուլում", "en": "Under review"},
    "service_status_ready": {"ru": "Готово к оплате", "hy": "Պատրաստ է վճարման", "en": "Ready to pay"},
    "service_status_paid": {"ru": "Оплачено", "hy": "Վճարված է", "en": "Paid"},
    "service_status_cancelled": {"ru": "Отклонено", "hy": "Մերժված է", "en": "Declined"},
    "service_status_submitted_hint": {
        "ru": "Мы рассматриваем заявку — как только всё будет готово, придёт уведомление с оплатой.",
        "hy": "Հայտը դիտարկման փուլում է․ երբ ամեն ինչ պատրաստ լինի, կստանաք ծանուցում վճարման համար։",
        "en": "We're reviewing your request — you'll get a notification with payment once it's ready.",
    },
    "service_admin_note": {"ru": "Комментарий", "hy": "Մեկնաբանություն", "en": "Note"},
    "service_pay_balance_button": {"ru": "Оплатить с баланса", "hy": "Վճարել հաշվեկշռից", "en": "Pay from balance"},
    "service_insufficient_balance": {
        "ru": "Недостаточно средств на балансе — пополните его, чтобы оплатить.",
        "hy": "Հաշվեկշիռը բավարար չէ․ համալրեք այն վճարելու համար։",
        "en": "Not enough balance — top up to pay.",
    },
    "service_download_button": {"ru": "Скачать файл", "hy": "Ներբեռնել ֆայլը", "en": "Download file"},
    "service_client_note_label": {"ru": "Комментарий (необязательно)", "hy": "Մեկնաբանություն (կամընտիր)", "en": "Comment (optional)"},
    "service_file_upload_hint": {
        "ru": "Прикрепляй только то, что реально нужно для этого вопроса — файл увидит наша команда, чтобы обработать заявку (см. Политику конфиденциальности).",
        "hy": "Կցիր միայն այն, ինչ իրականում անհրաժեշտ է այս հարցի համար — ֆայլը կտեսնի մեր թիմը՝ հայտը մշակելու համար։",
        "en": "Only attach what's actually needed for this question — our team will see the file in order to process your request (see the Privacy Policy).",
    },
    "service_response_time_label": {"ru": "Обычно отвечаем", "hy": "Սովորաբար պատասխանում ենք", "en": "Typical response time"},
    "notif_open_btn": {"ru": "Открыть", "hy": "Բացել", "en": "Open"},
    "my_chats_title": {"ru": "Мои чаты", "hy": "Իմ չաթերը", "en": "My chats"},
    "my_chats_empty": {"ru": "Пока нет ни одного чата.", "hy": "Դեռ ոչ մի չաթ չկա։", "en": "No chats yet."},
    "new_support_chat": {"ru": "🆘 Написать в поддержку", "hy": "🆘 Գրել աջակցությանը", "en": "🆘 Contact support"},
    "chat_input_placeholder": {"ru": "Напиши сообщение…", "hy": "Գրիր հաղորդագրություն…", "en": "Type a message…"},
    "chat_label_you": {"ru": "Вы", "hy": "Դուք", "en": "You"},
    "chat_label_support": {"ru": "Поддержка", "hy": "Աջակցություն", "en": "Support"},
    "topic_support": {"ru": "Поддержка", "hy": "Աջակցություն", "en": "Support"},

    "status_pending_payment": {"ru": "Ждёт оплаты", "hy": "Սպասում է վճարման", "en": "Awaiting payment"},
    "status_paid": {"ru": "Оплачен, готовим eSIM", "hy": "Վճարված է, պատրաստում ենք", "en": "Paid, preparing your eSIM"},
    "status_provisioning": {"ru": "Оформляется", "hy": "Ձևակերպվում է", "en": "Processing"},
    "status_active": {"ru": "Активен", "hy": "Ակտիվ է", "en": "Active"},
    "status_failed": {"ru": "Ошибка оформления — напишите нам", "hy": "Սխալ․ գրեք մեզ", "en": "Error — please contact us"},
    "status_refunded": {"ru": "Возврат оформлен", "hy": "Վերադարձը կատարված է", "en": "Refunded"},

    "footer_bot_teaser": {
        "ru": "Твой цифровой роуминг — eSIM, доступ в лаунж-зоны и туры в одном месте.",
        "hy": "Քո թվային ռոումինգը՝ eSIM, լաունջ հասանելիություն և տուրեր մեկ վայրում։",
        "en": "Your digital roaming — eSIM, lounge access and tours in one place.",
    },

    "footer_privacy_link": {"ru": "Политика конфиденциальности", "hy": "Գաղտնիության քաղաքականություն", "en": "Privacy Policy"},
    "footer_terms_link": {"ru": "Условия использования", "hy": "Օգտագործման պայմաններ", "en": "Terms of Service"},
    "footer_cookies_link": {"ru": "Cookies", "hy": "Cookies", "en": "Cookies"},
    "agree_to_terms": {
        "ru": 'Регистрируясь, я соглашаюсь с <a href="/shop/terms">условиями использования</a> и <a href="/shop/privacy">политикой конфиденциальности</a>.',
        "hy": 'Գրանցվելով՝ ես համաձայն եմ <a href="/shop/terms">օգտագործման պայմաններին</a> և <a href="/shop/privacy">գաղտնիության քաղաքականությանը</a>։',
        "en": 'By registering, I agree to the <a href="/shop/terms">Terms of Service</a> and <a href="/shop/privacy">Privacy Policy</a>.',
    },

    "privacy_title": {"ru": "Политика конфиденциальности", "hy": "Գաղտնիության քաղաքականություն", "en": "Privacy Policy"},
    "privacy_body": {
        "ru": """
<p><strong>Какие данные мы собираем.</strong> Email и пароль (хранится не в открытом виде,
а в виде хеша — мы сами не можем его увидеть), история заказов (какой пакет/услугу купил,
статус, цена), переписка в чате поддержки, ответы в форме заказа услуги (лаунж/туры) —
включая файл, если вопрос его требует (например, скан билета). Если использовал
реферальную ссылку — кто кого пригласил. IP-адрес используется только для защиты от
подбора пароля и злоупотреблений.</p>
<p><strong>Зачем.</strong> Чтобы оформить и выдать заказ, показать историю покупок,
ответить на вопросы в чате, начислить реферальный бонус, защититься от мошенничества.</p>
<p><strong>С кем делимся.</strong> С платёжными системами (Idram, OxaPay, Stripe) — только
то, что нужно для проведения платежа. С esimaccess.com — данные о купленном пакете, чтобы
выпустить eSIM. С Resend (сервис отправки писем) — твой email и текст письма, когда мы
подтверждаем регистрацию или восстанавливаем пароль. Мы не продаём и не передаём твои
данные никому ещё.</p>
<p><strong>Cookies и похожие технологии.</strong> Один служебный cookie для входа в
аккаунт — без него сайт не запомнит, что ты вошёл. Отдельно в памяти браузера (localStorage)
сохраняются настройки интерфейса (светлая/тёмная тема, свёрнута ли боковая панель) — это
не cookie и не передаётся нам на сервер. Подробнее — на странице
<a href="/shop/cookies">Cookies</a>.</p>
<p><strong>Сколько храним.</strong> Пока существует аккаунт, либо пока это требуется по
закону (например, для бухгалтерского учёта).</p>
<p><strong>Твои права.</strong> Можешь запросить удаление аккаунта и своих данных — напиши в
поддержку через сайт.</p>
"""
,
        "hy": """
<p><strong>Ինչ տվյալներ ենք հավաքում։</strong> Էլ. փոստ և գաղտնաբառ (պահվում է որպես
հեշ, ոչ բացահայտ տեսքով), պատվերների պատմությունը, նամակագրությունը չաթում, պատասխանները
ծառայության պատվերի ձևաթղթում (լաունջ/տուրեր), այդ թվում՝ ֆայլը, եթե հարցը դա պահանջում
է։ Եթե օգտվել ես ռեֆերալ հղումից՝ ով ում է հրավիրել։ IP-հասցեն օգտագործվում է միայն
գաղտնաբառի ենթադրման դեմ պաշտպանության համար։</p>
<p><strong>Ինչու։</strong> Պատվերդ ձևակերպելու և տրամադրելու, գնումների պատմությունը
ցույց տալու, չաթում հարցերին պատասխանելու, ռեֆերալ բոնուս հաշվարկելու, խարդախությունից
պաշտպանվելու համար։</p>
<p><strong>Ում հետ ենք կիսվում։</strong> Վճարային համակարգերի հետ (Idram, OxaPay,
Stripe) — միայն վճարման համար անհրաժեշտ տվյալները։ esimaccess.com-ի հետ՝ գնված փաթեթի
մասին տվյալները՝ eSIM թողարկելու համար։ Resend-ի հետ (նամակների ուղարկման ծառայություն)՝
քո էլ. փոստը և նամակի տեքստը։ Ոչ ոքի չենք վաճառում քո տվյալները։</p>
<p><strong>Cookies և նմանատիպ տեխնոլոգիաներ։</strong> Մեկ ծառայողական cookie՝ հաշվի
մուտքի համար։ Առանձին՝ բրաուզերի հիշողությունում (localStorage) պահվում են ինտերֆեյսի
կարգավորումները (թեմա, կողային վահանակի վիճակը) — սա cookie չէ և մեզ չի փոխանցվում։
Մանրամասն՝ <a href="/shop/cookies">Cookies</a> էջում։</p>
<p><strong>Որքա՞ն ենք պահում։</strong> Քանի դեռ գոյություն ունի հաշիվը, կամ քանի դեռ դա
պահանջվում է օրենքով։</p>
<p><strong>Քո իրավունքները։</strong> Կարող ես պահանջել հաշվի և տվյալների ջնջում՝ գրելով
աջակցությանը կայքի միջոցով։</p>
"""
,
        "en": """
<p><strong>What we collect.</strong> Your email and password (stored as a hash, never in
plain text), order history, support chat messages, your answers in a service order form
(lounge/tours) — including a file if the question requires one (e.g. a ticket scan). If
you used a referral link — who referred whom. Your IP address is used only for abuse and
brute-force protection.</p>
<p><strong>Why.</strong> To process and deliver your orders, show your purchase history,
answer chat questions, credit referral bonuses, and protect against fraud.</p>
<p><strong>Who we share it with.</strong> Payment providers (Idram, OxaPay, Stripe) — only
what's needed to process payment. esimaccess.com — your purchased package details, to issue
the eSIM. Resend (email delivery service) — your email and the message text, when we
confirm registration or a password reset. We do not sell your data to anyone.</p>
<p><strong>Cookies and similar technology.</strong> One functional cookie to keep you
logged in. Separately, your browser's local storage keeps interface preferences (light/dark
theme, whether the sidebar is collapsed) — this is not a cookie and isn't sent to us.
Details on the <a href="/shop/cookies">Cookies</a> page.</p>
<p><strong>Retention.</strong> As long as your account exists, or as required by law (e.g.
accounting).</p>
<p><strong>Your rights.</strong> You can request account and data deletion — contact
support via the site.</p>
"""
,
    },

    "terms_title": {"ru": "Условия использования", "hy": "Օգտագործման պայմաններ", "en": "Terms of Service"},
    "terms_body": {
        "ru": """
<p>Мы продаём цифровые товары и услуги: eSIM с мобильным интернетом, доступ в лаунж-зоны
аэропортов, туры. Выдача eSIM зависит от партнёра esimaccess.com — в редких случаях
возможна задержка или отказ на их стороне, о чём мы сообщим и поможем решить вопрос.</p>
<p><strong>Оплата.</strong> Цены указаны в валюте пакета. Оплата — картой (Idram, Stripe)
или криптовалютой (OxaPay), либо с внутреннего баланса аккаунта. Оплачивая заказ, ты
подтверждаешь, что данные карты/кошелька принадлежат тебе.</p>
<p><strong>Возврат.</strong> Возвраты рассматриваются индивидуально нашей командой вручную
— напиши в поддержку через сайт, опиши ситуацию. Так как eSIM и доступ в лаунж/туры —
цифровые товары и услуги, которые активируются практически сразу после оплаты, полный
возврат не гарантирован, если товар/услуга уже были фактически предоставлены (например,
QR-код eSIM выпущен и активирован, доступ в лаунж использован). Если по нашей вине или по
вине esimaccess.com услуга не была оказана — сделаем возврат или замену.</p>
<p><strong>Заявки на услуги (лаунж, туры).</strong> Оформляются через форму на сайте.
Ориентировочная цена в карточке услуги может отличаться от финальной — обычно мы отвечаем
в срок, указанный в самой услуге; финальную цену и детали подтверждаем перед оплатой,
которую в этом случае можно провести с баланса аккаунта.</p>
<p><strong>Аккаунт.</strong> Один человек — один аккаунт. Ты отвечаешь за сохранность
своего пароля. Сервис предназначен для лиц старше 18 лет (или совершеннолетия по законам
твоей страны).</p>
<p><strong>Ограничение ответственности.</strong> Мы не несём ответственности за перебои в
работе сторонних сервисов (esimaccess, платёжные системы, сотовые операторы), от которых
зависит предоставление услуги.</p>
""",
        "hy": """
<p>Մենք վաճառում ենք թվային ապրանքներ և ծառայություններ՝ eSIM ինտերնետով, օդանավակայանի
լաունջ հասանելիություն, տուրեր։ eSIM-ի տրամադրումը կախված է esimaccess.com գործընկերոջից՝
հազվադեպ հնարավոր է ուշացում կամ մերժում նրանց կողմից, որի մասին կտեղեկացնենք և
կօգնենք լուծել հարցը։</p>
<p><strong>Վճարում։</strong> Գները նշված են փաթեթի արժույթով։ Վճարումը՝ քարտով (Idram,
Stripe), կրիպտոարժույթով (OxaPay), կամ հաշվի հաշվեկշռից։</p>
<p><strong>Վերադարձ։</strong> Վերադարձերը դիտարկվում են անհատապես մեր թիմի կողմից ձեռքով
— գրիր աջակցությանը կայքի միջոցով, նկարագրիր իրավիճակը։ Քանի որ eSIM-ը և լաունջ/տուր
հասանելիությունը թվային ապրանք/ծառայություն են, որոնք ակտիվանում են վճարումից անմիջապես
հետո, լրիվ վերադարձը երաշխավորված չէ, եթե ապրանքը/ծառայությունը արդեն փաստացի
տրամադրվել է։</p>
<p><strong>Ծառայությունների հայտեր (լաունջ, տուրեր)։</strong> Ձևակերպվում են կայքի ձևաթղթի
միջոցով։ Ապրանքի քարտում գինը մոտավոր է. վերջնական գինը և մանրամասները հաստատվում են
վճարումից առաջ, որը այս դեպքում կարելի է կատարել հաշվի հաշվեկշռից։</p>
<p><strong>Հաշիվ։</strong> Մեկ մարդ՝ մեկ հաշիվ։ Դու պատասխանատու ես գաղտնաբառիդ
պահպանման համար։ Ծառայությունը նախատեսված է 18 տարեկանից բարձր անձանց համար։</p>
<p><strong>Պատասխանատվության սահմանափակում։</strong> Մենք պատասխանատվություն չենք կրում
երրորդ կողմի ծառայությունների (esimaccess, վճարային համակարգեր, օպերատորներ) խափանումների
համար, որոնցից կախված է ծառայության մատուցումը։</p>
""",
        "en": """
<p>We sell digital goods and services: eSIM data plans, airport lounge access, and tours.
eSIM delivery depends on our partner esimaccess.com — in rare cases there may be a delay or
failure on their end, which we'll notify you about and help resolve.</p>
<p><strong>Payment.</strong> Prices are shown in the package's currency. Payment is by card
(Idram, Stripe), crypto (OxaPay), or from your account balance. By paying, you confirm the
card/wallet used belongs to you.</p>
<p><strong>Refunds.</strong> Refunds are reviewed individually by our team, by hand —
contact support via the site and describe the situation. Since eSIM and lounge/tour access
are digital goods and services that activate almost immediately after payment, a full
refund isn't guaranteed once the item/service has actually been provided (e.g. the eSIM QR
code has been issued and activated, or lounge access was used). If the service wasn't
delivered due to our fault or esimaccess.com's, we'll issue a refund or replacement.</p>
<p><strong>Service requests (lounge, tours).</strong> Submitted through the form on the
site. The estimated price on the service card may differ from the final one — we usually
respond within the time stated on the service itself; the final price and details are
confirmed before payment, which in this case can be made from your account balance.</p>
<p><strong>Account.</strong> One person, one account. You're responsible for keeping your
password secure. This service is intended for users 18 years or older (or the age of
majority in your jurisdiction).</p>
<p><strong>Limitation of liability.</strong> We are not responsible for outages of
third-party services (esimaccess, payment providers, mobile carriers) that the delivery of
the service depends on.</p>
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

    "nav_balance": {"ru": "Мой баланс", "hy": "Իմ հաշիվը", "en": "My balance"},
    "balance_current": {"ru": "Текущий баланс", "hy": "Ընթացիկ մնացորդ", "en": "Current balance"},
    "balance_topup_title": {"ru": "Пополнить баланс", "hy": "Համալրել հաշիվը", "en": "Top up balance"},
    "balance_amount_label": {"ru": "Сумма, $", "hy": "Գումար, $", "en": "Amount, $"},
    "balance_history_title": {"ru": "История пополнений", "hy": "Համալրումների պատմություն", "en": "Top-up history"},
    "checkout_pay_balance": {"ru": "Оплатить с баланса", "hy": "Վճարել հաշվից", "en": "Pay from balance"},
    "checkout_balance_low": {"ru": "Недостаточно на балансе — сейчас там", "hy": "Հաշվում բավարար չէ — այժմ կա", "en": "Not enough balance — you currently have"},

    "referral_title": {"ru": "Пригласи друга", "hy": "Հրավիրիր ընկերոջ", "en": "Invite a friend"},
    "referral_desc": {
        "ru": "Получай {percent}% от суммы первой покупки каждого приглашённого — начисляется на баланс автоматически. Отправь эту ссылку:",
        "hy": "Ստացիր {percent}% հրավիրվածի առաջին գնումից — ավտոմատ կերպով ավելացվում է հաշվին։ Ուղարկիր այս հղումը՝",
        "en": "Get {percent}% of each invited friend's first purchase — credited to your balance automatically. Share this link:",
    },

    "favorite_add": {"ru": "В избранное", "hy": "Ավելացնել ընտրյալներում", "en": "Add to favorites"},
    "favorite_remove": {"ru": "Убрать из избранного", "hy": "Հեռացնել ընտրյալներից", "en": "Remove from favorites"},

    "search_placeholder": {"ru": "Поиск по странам…", "hy": "Փնտրել երկրներ…", "en": "Search countries…"},
    "filter_all": {"ru": "Все", "hy": "Բոլորը", "en": "All"},
    "filter_europe": {"ru": "Европа", "hy": "Եվրոպա", "en": "Europe"},
    "filter_asia": {"ru": "Азия", "hy": "Ասիա", "en": "Asia"},
    "filter_favorites": {"ru": "★ Избранное", "hy": "★ Ընտրյալներ", "en": "★ Favorites"},

    "review_title": {"ru": "Оставить отзыв", "hy": "Թողնել կարծիք", "en": "Leave a review"},
    "review_placeholder": {"ru": "Как всё прошло? (необязательно)", "hy": "Ինչպե՞ս անցավ (ոչ պարտադիր)", "en": "How did it go? (optional)"},
    "review_submit": {"ru": "Отправить отзыв", "hy": "Ուղարկել կարծիքը", "en": "Submit review"},
    "review_thanks": {"ru": "Спасибо за отзыв!", "hy": "Շնորհակալություն կարծիքի համար!", "en": "Thanks for your review!"},
    "reviews_count": {"ru": "отзывов", "hy": "կարծիք", "en": "reviews"},
    "no_reviews_yet": {"ru": "Пока нет отзывов — стань первым.", "hy": "Դեռ կարծիքներ չկան։", "en": "No reviews yet — be the first."},
    "days_short": {"ru": "дн.", "hy": "օր", "en": "days"},

    "home_regions_title": {"ru": "Региональные пакеты", "hy": "Տարածաշրջանային փաթեթներ", "en": "Regional plans"},
    "region_from": {"ru": "от", "hy": "-ից", "en": "from"},
    "home_regions_show_all": {"ru": "Все направления", "hy": "Բոլոր ուղղությունները", "en": "Show all"},

    "coverage_eyebrow": {"ru": "География покрытия", "hy": "Ծածկույթի աշխարհագրություն", "en": "Coverage"},
    "coverage_title": {
        "ru": "Высокоскоростной интернет в любой точке",
        "hy": "Բարձր արագությամբ ինտերնետ ցանկացած կետում",
        "en": "High-speed data, everywhere you go",
    },
    "coverage_hint": {
        "ru": "Список стран и регионов — ниже",
        "hy": "Երկրների և տարածաշրջանների ցանկը՝ ներքևում",
        "en": "See the full list of countries and regions below",
    },

    "notif_title": {"ru": "Уведомления", "hy": "Ծանուցումներ", "en": "Notifications"},
    "notif_filter_all": {"ru": "Все", "hy": "Բոլորը", "en": "All"},
    "notif_filter_order": {"ru": "Заказы", "hy": "Պատվերներ", "en": "Orders"},
    "notif_filter_payment": {"ru": "Платежи", "hy": "Վճարումներ", "en": "Payments"},
    "notif_filter_system": {"ru": "Система", "hy": "Համակարգ", "en": "System"},
    "notif_empty": {"ru": "Пока нет уведомлений", "hy": "Դեռ ծանուցումներ չկան", "en": "No notifications yet"},

    "promo_title": {"ru": "Промокод", "hy": "Պրոմոկոդ", "en": "Promo code"},
    "promo_placeholder": {"ru": "Введи промокод", "hy": "Մուտքագրիր պրոմոկոդը", "en": "Enter promo code"},
    "promo_redeem_btn": {"ru": "Активировать", "hy": "Ակտիվացնել", "en": "Redeem"},
    "promo_not_found": {"ru": "Промокод не найден", "hy": "Պրոմոկոդը գոյություն չունի", "en": "Promo code not found"},
    "promo_expired": {"ru": "Срок действия промокода истёк", "hy": "Պրոմոկոդի ժամկետը լրացել է", "en": "This promo code has expired"},
    "promo_limit": {"ru": "Лимит активаций промокода исчерпан", "hy": "Ակտիվացումների սահմանաչափը սպառվել է", "en": "This promo code has reached its usage limit"},
    "promo_used": {"ru": "Ты уже активировал этот промокод", "hy": "Դու արդեն ակտիվացրել ես այս պրոմոկոդը", "en": "You've already redeemed this code"},

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
        "ru": "Напиши нам в поддержку прямо на сайте (кнопка в шапке) — разберёмся быстро.",
        "hy": "Գրիր մեզ աջակցությանը կայքում (կոճակը վերևում) — արագ կլուծենք։",
        "en": "Message support right here on the site (button in the header) — we'll sort it out fast.",
    },
    "faq_q4": {"ru": "На каких устройствах работает eSIM?", "hy": "Ո՞ր սարքերում է աշխատում eSIM-ը", "en": "Which devices support eSIM?"},
    "faq_a4": {
        "ru": "На большинстве смартфонов последних лет (iPhone начиная с XR/XS, многие Android-флагманы). Перед покупкой проверь в настройках телефона, поддерживает ли он eSIM.",
        "hy": "Վերջին տարիների սմարթֆոնների մեծ մասում (iPhone XR/XS-ից սկսած, շատ Android-ֆլագմաններ)։",
        "en": "Most recent smartphones (iPhone XR/XS and later, many Android flagships). Check your phone's settings before buying to confirm eSIM support.",
    },

    "cookies_title": {"ru": "Cookies", "hy": "Cookies", "en": "Cookies"},
    "cookies_body": {
        "ru": """
<p>Мы используем только один cookie — служебный, для входа в аккаунт (без него сайт не
запомнит, что ты вошёл). Он строго необходим для работы сайта, поэтому по закону не
требует отдельного согласия — но мы всё равно рассказываем о нём здесь для прозрачности.</p>
<p>Рекламных, аналитических или отслеживающих cookie мы не используем — на сайте нет ни
Google Analytics, ни рекламных пикселей, ни похожих систем.</p>
<p><strong>Локальное хранилище браузера (localStorage).</strong> Отдельно от cookies, в
памяти твоего браузера сохраняются настройки интерфейса — выбранная тема (светлая/тёмная)
и состояние боковой панели (свёрнута или нет). Это не передаётся на наш сервер и не
используется для отслеживания — только чтобы не спрашивать эти настройки заново при
следующем визите.</p>
<p>Шрифты и другие статические файлы (стили, скрипты) загружаются с нашего собственного
сервера, а не со сторонних CDN — так посторонние сервисы не получают данные о посетителях
сайта просто от того, что они на него зашли.</p>
""",
        "hy": """
<p>Մենք օգտագործում ենք միայն մեկ cookie՝ ծառայողական, հաշվի մուտքի համար։ Այն խիստ
անհրաժեշտ է կայքի աշխատանքի համար, ուստի օրենքով առանձին համաձայնություն չի պահանջում,
սակայն թափանցիկության համար այստեղ նշում ենք այն։</p>
<p>Գովազդային, վերլուծական կամ հետևող cookie-ներ չենք օգտագործում — կայքում չկա ոչ Google
Analytics, ոչ գովազդային պիքսելներ։</p>
<p><strong>Բրաուզերի տեղական հիշողություն (localStorage)։</strong> Cookie-ից առանձին,
բրաուզերիդ հիշողությունում պահվում են ինտերֆեյսի կարգավորումները՝ ընտրված թեման և
կողային վահանակի վիճակը։ Սա մեզ չի փոխանցվում և հետևման համար չի օգտագործվում։</p>
<p>Տառատեսակները և մյուս ստատիկ ֆայլերը բեռնվում են մեր սեփական սերվերից, ոչ թե
արտաքին CDN-ից։</p>
""",
        "en": """
<p>We use exactly one cookie — a functional one, to keep you logged in (without it the site
won't remember that you've signed in). It's strictly necessary for the site to work, so it
doesn't legally require separate consent — but we're describing it here anyway for
transparency.</p>
<p>We don't use advertising, analytics, or tracking cookies — there's no Google Analytics,
no ad pixels, nothing like that on the site.</p>
<p><strong>Browser local storage.</strong> Separately from cookies, your browser's local
storage keeps interface preferences — the chosen theme (light/dark) and whether the sidebar
is collapsed. This isn't sent to our server and isn't used for tracking — it's only there
so we don't have to ask again on your next visit.</p>
<p>Fonts and other static files (styles, scripts) are loaded from our own server, not from
third-party CDNs — so outside services don't get visitor data just from someone loading the
site.</p>
""",
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