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

  nav_balance: { ru: "Мой баланс", hy: "Իմ հաշիվը", en: "My balance" },
  balance_current: { ru: "Текущий баланс", hy: "Ընթացիկ մնացորդ", en: "Current balance" },
  balance_topup_title: { ru: "Пополнить баланс", hy: "Համալրել հաշիվը", en: "Top up balance" },
  balance_amount_label: { ru: "Введи сумму, $", hy: "Մուտքագրիր գումարը, $", en: "Enter amount, $" },
  checkout_pay_balance: { ru: "Оплатить с баланса", hy: "Վճարել հաշվից", en: "Pay from balance" },

  referral_title: { ru: "Пригласи друга", hy: "Հրավիրիր ընկերոջ", en: "Invite a friend" },
  referral_desc: {
    ru: "Получай {percent}% от суммы первой покупки каждого приглашённого — начисляется на баланс автоматически.",
    hy: "Ստացիր {percent}% հրավիրվածի առաջին գնումից — ավտոմատ կերպով ավելացվում է հաշվին։",
    en: "Get {percent}% of each invited friend's first purchase — credited to your balance automatically.",
  },

  filter_all: { ru: "Все", hy: "Բոլորը", en: "All" },
  filter_favorites: { ru: "★ Избранное", hy: "★ Ընտրյալներ", en: "★ Favorites" },
  favorite_add: { ru: "В избранное", hy: "Ավելացնել ընտրյալներում", en: "Add to favorites" },
  favorite_remove: { ru: "Убрать из избранного", hy: "Հեռացնել ընտրյալներից", en: "Remove from favorites" },

  reviews_count: { ru: "отзывов", hy: "կարծիք", en: "reviews" },
  no_reviews_yet: { ru: "Пока нет отзывов", hy: "Դեռ կարծիքներ չկան", en: "No reviews yet" },
  review_placeholder: { ru: "Как всё прошло? (необязательно)", hy: "Ինչպե՞ս անցավ", en: "How did it go? (optional)" },
  review_submit: { ru: "Отправить отзыв", hy: "Ուղարկել կարծիքը", en: "Submit review" },
  review_thanks: { ru: "Спасибо за отзыв!", hy: "Շնորհակալություն!", en: "Thanks for your review!" },
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