// Простой словарь переводов + определение языка. Ничего не собирается сборщиком —
// обычный script-тег, как и остальной фронтенд этого Mini App.

const I18N = {
  tab_catalog: { ru: "Каталог", hy: "Կատալոգ", en: "Catalog" },
  tab_my_esims: { ru: "Мои eSIM", hy: "Իմ eSIM", en: "My eSIMs" },
  tab_chats: { ru: "Чаты", hy: "Չաթեր", en: "Chats" },

  home_esim_title: { ru: "eSIM с интернетом", hy: "eSIM ինտերնետով", en: "eSIM data plans" },
  home_esim_subtitle: { ru: "Более 100 стран", hy: "100+ երկիր", en: "100+ countries" },

  back: { ru: "Назад", hy: "Հետ", en: "Back" },

  search_country_placeholder: { ru: "Поиск страны", hy: "Փնտրել երկիր", en: "Search country" },
  catalog_empty: { ru: "Каталог пока пуст", hy: "Կատալոգը դեռ դատարկ է", en: "Catalog is empty for now" },
  packages_empty: { ru: "Для этой страны пока нет пакетов", hy: "Այս երկրի համար փաթեթներ դեռ չկան", en: "No packages for this country yet" },

  checkout_total: { ru: "Итого", hy: "Ընդամենը", en: "Total" },
  checkout_title: { ru: "Оформление", hy: "Ձևակերպում", en: "Checkout" },
  pay_idram: { ru: "Оплатить через Idram", hy: "Վճարել Idram-ով", en: "Pay with Idram" },
  pay_wallet: { ru: "Оплатить криптой из Telegram Wallet", hy: "Վճարել կրիպտոյով Telegram Wallet-ից", en: "Pay with crypto via Telegram Wallet" },
  pay_oxapay: { ru: "Оплатить криптой с биржи/кошелька", hy: "Վճարել կրիպտոյով բորսայից/դրամապանակից", en: "Pay with crypto from any wallet/exchange" },
  qr_hint: { ru: "После оплаты здесь появится QR-код для активации eSIM.", hy: "Վճարումից հետո այստեղ կհայտնվի eSIM-ի ակտիվացման QR-կոդը։", en: "The activation QR code will appear here after payment." },
  payment_waiting: { ru: "Ждём подтверждения оплаты…", hy: "Սպասում ենք վճարման հաստատմանը…", en: "Waiting for payment confirmation…" },

  my_esims_empty: { ru: "Пока нет купленных eSIM", hy: "Դեռ չկան գնված eSIM-ներ", en: "No eSIMs purchased yet" },
  greeting_hello: { ru: "Привет", hy: "Բարև", en: "Hello" },
  greeting_active_esims: { ru: "активных eSIM", hy: "ակտիվ eSIM", en: "active eSIMs" },
  stat_data: { ru: "Данные", hy: "Տվյալներ", en: "Data" },
  stat_validity: { ru: "Срок", hy: "Ժամկետ", en: "Validity" },
  days_short: { ru: "дн.", hy: "օր", en: "days" },
  data_left: { ru: "Осталось {gb} ГБ из {total} ГБ", hy: "Մնացել է {gb} ԳԲ {total} ԳԲ-ից", en: "{gb} GB left of {total} GB" },
  qr_download: { ru: "Скачать QR-код", hy: "Ներբեռնել QR-կոդը", en: "Download QR code" },

  onboarding_1_title: { ru: "Интернет в любой стране", hy: "Ինտերնետ ցանկացած երկրում", en: "Internet in any country" },
  onboarding_1_desc: { ru: "eSIM для более чем 100 стран — без походов в салон связи и без роуминга.", hy: "eSIM ավելի քան 100 երկրների համար — առանց ռոումինգի։", en: "eSIM for 100+ countries — no roaming, no store visits." },
  onboarding_2_title: { ru: "Выбери страну и тариф", hy: "Ընտրիր երկիրը և փաթեթը", en: "Pick a country and plan" },
  onboarding_2_desc: { ru: "QR-код появляется сразу после оплаты — активируй перед вылетом.", hy: "QR-կոդը հայտնվում է վճարումից անմիջապես հետո։", en: "QR code appears right after payment — activate before you fly." },
  onboarding_3_title: { ru: "Оплата с баланса", hy: "Վճարում հաշվից", en: "Pay from your balance" },
  onboarding_3_desc: { ru: "Пополняй баланс удобным способом и оплачивай заказы мгновенно.", hy: "Համալրիր հաշիվը և վճարիր ակնթարթորեն։", en: "Top up your balance and pay for orders instantly." },
  onboarding_skip: { ru: "Пропустить", hy: "Բաց թողնել", en: "Skip" },
  onboarding_next: { ru: "Далее", hy: "Հաջորդը", en: "Next" },
  onboarding_start: { ru: "Начать", hy: "Սկսել", en: "Get started" },

  nav_balance: { ru: "Мой баланс", hy: "Իմ հաշիվը", en: "My balance" },
  balance_current: { ru: "Текущий баланс", hy: "Ընթացիկ մնացորդ", en: "Current balance" },
  balance_topup_title: { ru: "Пополнить баланс", hy: "Համալրել հաշիվը", en: "Top up balance" },
  balance_amount_label: { ru: "Введи сумму, $", hy: "Մուտքագրիր գումարը, $", en: "Enter amount, $" },
  checkout_pay_balance: { ru: "Оплатить с баланса", hy: "Վճարել հաշվից", en: "Pay from balance" },
  checkout_insufficient_balance: { ru: "Недостаточно средств на балансе", hy: "Հաշվին բավարար միջոցներ չկան", en: "Not enough balance" },
  checkout_topup_cta: { ru: "Пополнить баланс", hy: "Համալրել հաշիվը", en: "Top up balance" },

  referral_title: { ru: "Пригласи друга", hy: "Հրավիրիր ընկերոջ", en: "Invite a friend" },
  referral_desc: {
    ru: "Получай {percent}% от суммы первой покупки каждого приглашённого — начисляется на баланс автоматически.",
    hy: "Ստացիր {percent}% հրավիրվածի առաջին գնումից — ավտոմատ կերպով ավելացվում է հաշվին։",
    en: "Get {percent}% of each invited friend's first purchase — credited to your balance automatically.",
  },

  filter_all: { ru: "Все", hy: "Բոլորը", en: "All" },
  filter_favorites: { ru: "★ Избранное", hy: "★ Ընտրյալներ", en: "★ Favorites" },
  filter_regions: { ru: "🌐 Регионы", hy: "🌐 Տարածաշրջաններ", en: "🌐 Regions" },
  favorite_add: { ru: "В избранное", hy: "Ավելացնել ընտրյալներում", en: "Add to favorites" },
  favorite_remove: { ru: "Убрать из избранного", hy: "Հեռացնել ընտրյալներից", en: "Remove from favorites" },

  reviews_count: { ru: "отзывов", hy: "կարծիք", en: "reviews" },
  no_reviews_yet: { ru: "Пока нет отзывов", hy: "Դեռ կարծիքներ չկան", en: "No reviews yet" },
  review_placeholder: { ru: "Как всё прошло? (необязательно)", hy: "Ինչպե՞ս անցավ", en: "How did it go? (optional)" },
  review_submit: { ru: "Отправить отзыв", hy: "Ուղարկել կարծիքը", en: "Submit review" },
  review_thanks: { ru: "Спасибо за отзыв!", hy: "Շնորհակալություն!", en: "Thanks for your review!" },

  tab_home: { ru: "Главная", hy: "Գլխավոր", en: "Home" },
  tab_browse: { ru: "Обзор", hy: "Դիտարկել", en: "Browse" },
  tab_profile: { ru: "Профиль", hy: "Պրոֆիլ", en: "Profile" },

  quick_buy_esim: { ru: "Купить eSIM", hy: "Գնել eSIM", en: "Buy eSIM" },
  quick_my_esims: { ru: "Мои eSIM", hy: "Իմ eSIM-երը", en: "My eSIMs" },
  quick_favorites: { ru: "Избранное", hy: "Ընտրյալներ", en: "Favorites" },
  quick_topup: { ru: "Пополнить", hy: "Համալրել", en: "Top up" },

  home_regions_title: { ru: "Региональные пакеты", hy: "Տարածաշրջանային փաթեթներ", en: "Regional plans" },
  region_from: { ru: "от", hy: "-ից", en: "from" },

  home_why_title: { ru: "Почему KaLine?", hy: "Ինչու՞ KaLine", en: "Why KaLine?" },
  why_instant: { ru: "Мгновенная активация", hy: "Ակնթարթային ակտիվացում", en: "Instant activation" },
  why_secure: { ru: "Надёжно и безопасно", hy: "Հուսալի և անվտանգ", en: "Reliable and secure" },
  why_no_roaming: { ru: "Без роуминга", hy: "Առանց ռոումինգի", en: "No roaming fees" },
  why_support: { ru: "Поддержка 24/7", hy: "Աջակցություն 24/7", en: "24/7 support" },

  profile_help: { ru: "Помощь и поддержка", hy: "Օգնություն և աջակցություն", en: "Help & support" },
  profile_language: { ru: "Язык", hy: "Լեզու", en: "Language" },

  notif_title: { ru: "Уведомления", hy: "Ծանուցումներ", en: "Notifications" },
  notif_filter_all: { ru: "Все", hy: "Բոլորը", en: "All" },
  notif_filter_order: { ru: "Заказы", hy: "Պատվերներ", en: "Orders" },
  notif_filter_payment: { ru: "Платежи", hy: "Վճարումներ", en: "Payments" },
  notif_filter_system: { ru: "Система", hy: "Համակարգ", en: "System" },
  notif_empty: { ru: "Пока нет уведомлений", hy: "Դեռ ծանուցումներ չկան", en: "No notifications yet" },

  promo_title: { ru: "Промокод", hy: "Պրոմոկոդ", en: "Promo code" },
  promo_placeholder: { ru: "Введи промокод", hy: "Մուտքագրիր պրոմոկոդը", en: "Enter promo code" },
  promo_redeem_btn: { ru: "Активировать", hy: "Ակտիվացնել", en: "Redeem" },
  promo_error: { ru: "Промокод не найден или уже использован", hy: "Պրոմոկոդը գոյություն չունի կամ արդեն օգտագործված է", en: "Promo code not found or already used" },
  qr_manual_hint: { ru: "Не сканируется? Введи вручную в настройках телефона:", hy: "Չի սկանավորվում: Մուտքագրիր ձեռքով հեռախոսի կարգավորումներում.", en: "Can't scan? Enter this manually in your phone settings:" },
  status_pending_payment: { ru: "Ждёт оплаты", hy: "Սպասում է վճարման", en: "Awaiting payment" },
  status_paid: { ru: "Оплачен", hy: "Վճարված է", en: "Paid" },
  status_provisioning: { ru: "Оформляется", hy: "Ձևակերպվում է", en: "Processing" },
  status_active: { ru: "Активен", hy: "Ակտիվ է", en: "Active" },
  status_failed: { ru: "Ошибка", hy: "Սխալ", en: "Error" },
  status_refunded: { ru: "Возврат", hy: "Վերադարձ", en: "Refunded" },

  products_empty: { ru: "Пока нет предложений — загляни позже", hy: "Առաջարկներ դեռ չկան, ստուգիր ավելի ուշ", en: "Nothing here yet — check back later" },
  product_ask_button: { ru: "Спросить в чате", hy: "Հարցնել չաթում", en: "Ask in chat" },

  chats_empty: { ru: "Пока нет ни одного чата", hy: "Դեռ ոչ մի չաթ չկա", en: "No chats yet" },
  chats_new_support: { ru: "🆘 Написать в поддержку", hy: "🆘 Գրել աջակցությանը", en: "🆘 Contact support" },
  chat_input_placeholder: { ru: "Напиши сообщение…", hy: "Գրիր հաղորդագրություն…", en: "Type a message…" },
};

function detectLang() {
  try {
    const stored = window.localStorage.getItem("esim_store_lang");
    if (stored === "ru" || stored === "hy" || stored === "en") return stored;
  } catch (e) {
    // приватный режим браузера может блокировать localStorage — не критично, просто определяем по Telegram
  }
  const tgLang = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code || "";
  if (tgLang.startsWith("hy")) return "hy";
  if (tgLang.startsWith("en")) return "en";
  return "ru";
}

let currentLang = detectLang();

function t(key) {
  const entry = I18N[key];
  if (!entry) return key;
  return entry[currentLang] || entry.ru || key;
}

function setLang(lang) {
  currentLang = lang;
  try {
    window.localStorage.setItem("esim_store_lang", lang);
  } catch (e) {
    // не критично, просто не запомнится между сессиями
  }
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.setAttribute("placeholder", t(el.dataset.i18nPlaceholder));
  });
  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.lang === lang);
  });
  if (window.onLangChange) window.onLangChange();
}