const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// --- Тема: по умолчанию следуем теме Telegram (colorScheme: "light" | "dark"),
// но человек может переключить вручную ползунком — тогда его выбор запоминается
// (localStorage) и имеет приоритет над темой Telegram, пока сам не переключит обратно.
function applyTheme() {
  const manual = localStorage.getItem("miniapp_theme");
  const scheme = manual === "light" || manual === "dark" ? manual : (tg.colorScheme === "dark" ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", scheme);
  const toggle = document.getElementById("theme-toggle");
  if (toggle) toggle.setAttribute("aria-checked", scheme === "dark" ? "true" : "false");
}
applyTheme();
tg.onEvent("themeChanged", applyTheme);

document.getElementById("theme-toggle").addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme");
  const next = current === "dark" ? "light" : "dark";
  localStorage.setItem("miniapp_theme", next);
  applyTheme();
});

const initData = tg.initData; // сырая строка — отправляем на бэкенд как есть, он сам проверит подпись

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": initData,
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    throw new Error(`API ${path} -> ${res.status}`);
  }
  return res.json();
}

async function apiUpload(path, formData) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "X-Telegram-Init-Data": initData }, // без Content-Type — fetch сам поставит multipart-границу
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`API ${path} -> ${res.status}`);
  }
  return res.json();
}

function countryCodeToFlag(code) {
  if (!code || code.length !== 2) return "🌐";
  return String.fromCodePoint(...[...code.toUpperCase()].map((c) => 127397 + c.charCodeAt(0)));
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// --- Навигация между экранами ---
const screens = [
  "home", "esim-countries", "esim-packages", "esim-checkout",
  "products", "my-esims", "balance", "chats", "chat",
];
const TAB_ROOTS = { home: "catalog", "my-esims": "my-esims", chats: "chats" };

let selectedCountry = null;
let selectedPackage = null;
let currentCategory = null; // {id, slug, icon, title, subtitle} — выбранная динамическая категория
let currentConversationId = null;
let chatReturnScreen = "chats"; // куда вернуться из чата: "products" или "chats"

function showScreen(name) {
  if (name !== "esim-checkout" && paymentPollTimer) {
    clearInterval(paymentPollTimer);
    paymentPollTimer = null;
  }
  if (name !== "chat" && chatPollTimer) {
    clearInterval(chatPollTimer);
    chatPollTimer = null;
  }

  for (const s of screens) {
    document.getElementById(`screen-${s}`).hidden = s !== name;
  }

  const isTabRoot = name in TAB_ROOTS;
  document.getElementById("back-btn").hidden = isTabRoot;

  const titles = {
    home: "eSIM Store",
    "esim-countries": t("home_esim_title"),
    "esim-packages": selectedCountry ? selectedCountry.name : "",
    "esim-checkout": t("checkout_title"),
    products: currentCategory ? currentCategory.title : "",
    "my-esims": t("tab_my_esims"),
    balance: t("nav_balance"),
    chats: t("tab_chats"),
    chat: "",
  };
  document.getElementById("header-title").textContent = titles[name] || "eSIM Store";

  const activeTab = isTabRoot ? TAB_ROOTS[name] :
    ["esim-countries", "esim-packages", "esim-checkout", "products"].includes(name) ? "catalog" :
    name === "chat" ? "chats" : null;
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === activeTab);
  });
}

document.getElementById("back-btn").addEventListener("click", () => {
  if (!document.getElementById("screen-esim-checkout").hidden) return showScreen("esim-packages");
  if (!document.getElementById("screen-esim-packages").hidden) return showScreen("esim-countries");
  if (!document.getElementById("screen-esim-countries").hidden) return showScreen("home");
  if (!document.getElementById("screen-products").hidden) return showScreen("home");
  if (!document.getElementById("screen-balance").hidden) return showScreen("my-esims");
  if (!document.getElementById("screen-chat").hidden) return showScreen(chatReturnScreen === "products" ? "products" : "chats");
  showScreen("home");
});

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    if (tab === "catalog") { loadHomeCategories(); showScreen("home"); }
    if (tab === "my-esims") { loadMyEsims(); showScreen("my-esims"); }
    if (tab === "chats") { loadChatsList(); showScreen("chats"); }
  });
});

document.querySelectorAll(".lang-btn").forEach((btn) => {
  btn.addEventListener("click", () => setLang(btn.dataset.lang));
});

window.onLangChange = () => {
  // Перерисовать динамический (не статический data-i18n) контент активного экрана.
  if (!document.getElementById("screen-home").hidden) loadHomeCategories();
  if (!document.getElementById("screen-esim-packages").hidden) showScreen("esim-packages"); // обновит заголовок
  if (!document.getElementById("screen-products").hidden && currentCategory) loadProducts(currentCategory.slug);
  if (!document.getElementById("screen-my-esims").hidden) loadMyEsims();
  if (!document.getElementById("screen-chats").hidden) loadChatsList();
};

// --- Главный экран: eSIM (фиксированная) + категории из админки ---
document.getElementById("category-esim").addEventListener("click", () => {
  loadCountries();
  showScreen("esim-countries");
});

async function loadHomeCategories() {
  const categories = await api(`/api/categories?lang=${currentLang}`);
  const container = document.getElementById("dynamic-categories");
  container.innerHTML = "";
  for (const cat of categories) {
    const card = document.createElement("div");
    card.className = "category-card";
    card.innerHTML = `
      <div class="category-emoji">${cat.icon}</div>
      <div class="category-text">
        <div class="category-title">${escapeHtml(cat.title)}</div>
        <div class="category-subtitle">${cat.subtitle ? escapeHtml(cat.subtitle) : ""}</div>
      </div>
    `;
    card.addEventListener("click", () => {
      currentCategory = cat;
      loadProducts(cat.slug);
      showScreen("products");
    });
    container.appendChild(card);
  }
}

// --- eSIM: страны ---
let favoriteCodes = [];

async function loadCountries() {
  const countries = await api("/api/countries");
  try {
    favoriteCodes = (await api("/api/favorites")).codes || [];
  } catch (e) {
    favoriteCodes = [];
  }
  const list = document.getElementById("country-list");
  list.innerHTML = "";
  if (countries.length === 0) {
    list.innerHTML = `<div class="empty">${t("catalog_empty")}</div>`;
    return;
  }
  for (const c of countries) {
    const row = document.createElement("div");
    row.className = "row";
    row.dataset.code = c.code;
    const isFav = favoriteCodes.includes(c.code);
    row.innerHTML = `
      <span class="flag">${countryCodeToFlag(c.code)}</span>
      <div class="main"><div class="title">${c.name}</div></div>
      <button class="fav-heart-btn" data-code="${c.code}">${isFav ? "♥" : "♡"}</button>
      <span class="chevron">›</span>
    `;
    row.querySelector(".main").addEventListener("click", () => openCountry(c));
    row.querySelector(".flag").addEventListener("click", () => openCountry(c));
    row.querySelector(".chevron").addEventListener("click", () => openCountry(c));
    row.querySelector(".fav-heart-btn").addEventListener("click", async (e) => {
      e.stopPropagation();
      const result = await api("/api/favorites/toggle", {
        method: "POST",
        body: JSON.stringify({ country_code: c.code }),
      });
      e.target.textContent = result.is_favorite ? "♥" : "♡";
      if (result.is_favorite) favoriteCodes.push(c.code);
      else favoriteCodes = favoriteCodes.filter((code) => code !== c.code);
      if (!document.getElementById("filter-favorites-btn").classList.contains("active")) return;
      if (!result.is_favorite) row.hidden = true;
    });
    list.appendChild(row);
  }
}

document.getElementById("filter-all-btn").addEventListener("click", () => {
  document.getElementById("filter-all-btn").classList.add("active");
  document.getElementById("filter-favorites-btn").classList.remove("active");
  document.querySelectorAll("#country-list .row").forEach((row) => { row.hidden = false; });
});
document.getElementById("filter-favorites-btn").addEventListener("click", () => {
  document.getElementById("filter-favorites-btn").classList.add("active");
  document.getElementById("filter-all-btn").classList.remove("active");
  document.querySelectorAll("#country-list .row").forEach((row) => {
    row.hidden = !favoriteCodes.includes(row.dataset.code);
  });
});

document.getElementById("search-input").addEventListener("input", (e) => {
  const q = e.target.value.trim().toLowerCase();
  document.querySelectorAll("#country-list .row").forEach((row) => {
    const title = row.querySelector(".title").textContent.toLowerCase();
    row.style.display = title.includes(q) ? "" : "none";
  });
});

async function openCountry(country) {
  selectedCountry = country;
  const data = await api(`/api/packages?country=${encodeURIComponent(country.code)}`);
  const packages = data.packages;
  const list = document.getElementById("package-list");
  list.innerHTML = "";

  const isFav = favoriteCodes.includes(country.code);
  const ratingLine = data.review_count
    ? `★ ${data.avg_rating} · ${data.review_count} ${t("reviews_count")}`
    : t("no_reviews_yet");
  const header = document.createElement("div");
  header.className = "esims-greeting";
  header.style.paddingBottom = "10px";
  header.innerHTML = `
    <div style="font-size:34px;">${countryCodeToFlag(country.code)}</div>
    <div class="hint" style="margin-top:6px;">${ratingLine}</div>
    <button id="package-fav-btn" class="btn secondary" style="margin-top:10px;">${isFav ? "♥ " + t("favorite_remove") : "♡ " + t("favorite_add")}</button>
  `;
  list.appendChild(header);
  header.querySelector("#package-fav-btn").addEventListener("click", async (e) => {
    const result = await api("/api/favorites/toggle", {
      method: "POST",
      body: JSON.stringify({ country_code: country.code }),
    });
    if (result.is_favorite) favoriteCodes.push(country.code);
    else favoriteCodes = favoriteCodes.filter((c) => c !== country.code);
    e.target.textContent = result.is_favorite ? "♥ " + t("favorite_remove") : "♡ " + t("favorite_add");
  });

  if (packages.length === 0) {
    list.innerHTML += `<div class="empty">${t("packages_empty")}</div>`;
  } else {
    for (const p of packages) {
      const row = document.createElement("div");
      row.className = "package-row";
      const gb = (p.data_amount_mb / 1024).toFixed(1).replace(/\.0$/, "");
      row.innerHTML = `
        <div>${p.title || `${gb} GB · ${p.validity_days}d`}</div>
        <div class="price">${p.price} ${p.currency}</div>
      `;
      row.addEventListener("click", () => openCheckout(p));
      list.appendChild(row);
    }
  }
  showScreen("esim-packages");
}

let testPaymentEnabled = false;
let walletPayEnabled = true;
let oxapayEnabled = true;
let botUsername = "";

async function openCheckout(pkg) {
  selectedPackage = pkg;
  const summary = document.getElementById("checkout-summary");
  const gb = pkg.data_amount_mb ? (pkg.data_amount_mb / 1024).toFixed(1) : null;
  summary.innerHTML = `
    <div class="checkout-hero">
      <div class="checkout-hero-flag">${countryCodeToFlag(selectedCountry.code)}</div>
      <div class="checkout-hero-title">${escapeHtml(selectedCountry.name)}</div>
      <div class="checkout-hero-price">${pkg.price} <span>${pkg.currency}</span></div>
    </div>
    <div class="esim-stat-grid">
      ${gb ? `<div class="esim-stat"><div class="esim-stat-label">${t("stat_data")}</div><div class="esim-stat-value">${gb} GB</div></div>` : ""}
      ${pkg.validity_days ? `<div class="esim-stat"><div class="esim-stat-label">${t("stat_validity")}</div><div class="esim-stat-value">${pkg.validity_days} ${t("days_short")}</div></div>` : ""}
    </div>
  `;
  document.getElementById("payment-methods").hidden = false;
  document.getElementById("payment-waiting").hidden = true;
  document.getElementById("pay-walletpay-btn").hidden = !walletPayEnabled;
  document.getElementById("pay-oxapay-btn").hidden = !oxapayEnabled;
  document.getElementById("pay-test-btn").hidden = !testPaymentEnabled;

  const balanceBtn = document.getElementById("pay-balance-btn");
  balanceBtn.hidden = true;
  showScreen("esim-checkout");
  try {
    const balanceData = await api("/api/balance");
    if (balanceData.balance >= pkg.price) {
      balanceBtn.textContent = `${t("checkout_pay_balance")} ($${balanceData.balance.toFixed(2)})`;
      balanceBtn.hidden = false;
    }
  } catch (e) {
    // не критично — просто не покажем кнопку оплаты с баланса
  }
}

let paymentPollTimer = null;

async function payWith(method) {
  const methodButtons = document.getElementById("payment-methods");
  methodButtons.querySelectorAll("button").forEach((b) => (b.disabled = true));
  try {
    const order = await api("/api/orders", {
      method: "POST",
      body: JSON.stringify({ package_id: selectedPackage.id }),
    });
    const payInit = await api(`/api/orders/${order.order_id}/pay`, {
      method: "POST",
      body: JSON.stringify({ method }),
    });
    if (method === "test" || method === "balance") {
      // Заказ уже оплачен и отправлен в esimaccess на сервере — никуда переходить не нужно.
    } else if (method === "wallet_pay") {
      tg.openTelegramLink(payInit.redirect_url);
    } else {
      tg.openLink(payInit.redirect_url);
    }
    document.getElementById("payment-methods").hidden = true;
    document.getElementById("payment-waiting").hidden = false;
    pollPaymentStatus(order.order_id);
  } catch (e) {
    tg.showAlert("Error, please try again.");
    methodButtons.querySelectorAll("button").forEach((b) => (b.disabled = false));
  }
}

function pollPaymentStatus(orderId) {
  if (paymentPollTimer) clearInterval(paymentPollTimer);
  paymentPollTimer = setInterval(async () => {
    try {
      const status = await api(`/api/orders/${orderId}/payment-status`);
      if (status.payment_status === "paid") {
        clearInterval(paymentPollTimer);
        tg.showAlert(t("qr_hint"));
        showScreen("home");
      } else if (status.payment_status === "failed") {
        clearInterval(paymentPollTimer);
        document.getElementById("payment-methods").hidden = false;
        document.getElementById("payment-waiting").hidden = true;
        document.getElementById("payment-methods").querySelectorAll("button").forEach((b) => (b.disabled = false));
      }
    } catch (e) {
      // временная ошибка сети — пробуем на следующем тике
    }
  }, 3000);
}

async function loadBalance() {
  const data = await api("/api/balance");
  document.getElementById("balance-amount").textContent = `$${data.balance.toFixed(2)}`;
  document.getElementById("referral-desc").textContent = t("referral_desc").replace("{percent}", data.referral_percent);
  document.getElementById("referral-link-input").value = `https://t.me/${botUsername}?start=${data.referral_code}`;

  const history = document.getElementById("topup-history");
  history.innerHTML = "";
  for (const tu of data.top_ups) {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `<span class="title">$${tu.amount.toFixed(2)} — ${tu.provider}</span><span class="hint">${tu.status}</span>`;
    history.appendChild(row);
  }
}

async function submitTopup(method) {
  const input = document.getElementById("topup-amount-input");
  const amount = parseFloat(input.value);
  if (!amount || amount < 1) {
    tg.showAlert(t("balance_amount_label"));
    return;
  }
  try {
    const result = await api("/api/balance/topup", {
      method: "POST",
      body: JSON.stringify({ amount, method }),
    });
    tg.openLink(result.redirect_url);
  } catch (e) {
    tg.showAlert("Error, please try again.");
  }
}

document.getElementById("topup-idram-btn").addEventListener("click", () => submitTopup("idram"));
document.getElementById("topup-oxapay-btn").addEventListener("click", () => submitTopup("oxapay"));
document.getElementById("pay-balance-btn").addEventListener("click", () => payWith("balance"));
document.getElementById("pay-idram-btn").addEventListener("click", () => payWith("idram"));
document.getElementById("pay-walletpay-btn").addEventListener("click", () => payWith("wallet_pay"));
document.getElementById("pay-oxapay-btn").addEventListener("click", () => payWith("oxapay"));
document.getElementById("pay-test-btn").addEventListener("click", () => payWith("test"));

// --- Мои eSIM ---
async function loadMyEsims() {
  const data = await api("/api/my-orders");
  const orders = data.orders || [];
  const list = document.getElementById("my-esims-list");
  list.innerHTML = "";

  const activeCount = orders.filter(o => o.status === "active").length;
  const greetingName = (data.full_name || "").split(" ")[0] || "";
  const header = document.createElement("div");
  header.className = "esims-greeting";
  header.innerHTML = `
    <div class="hint">${t("greeting_hello")}${greetingName ? ", " + escapeHtml(greetingName) : ""}</div>
    <div class="esims-count">${activeCount}</div>
    <div class="hint">${t("greeting_active_esims")}</div>
    <button id="open-balance-btn" class="btn secondary" style="margin-top:12px;">💰 ${t("nav_balance")}</button>
  `;
  list.appendChild(header);
  document.getElementById("open-balance-btn").addEventListener("click", () => {
    loadBalance();
    showScreen("balance");
  });

  if (orders.length === 0) {
    list.innerHTML += `<div class="empty">${t("my_esims_empty")}</div>`;
    return;
  }
  for (const o of orders) {
    const card = document.createElement("div");
    card.className = "esim-card";
    const gb = o.data_amount_mb ? (o.data_amount_mb / 1024).toFixed(1) : null;
    card.innerHTML = `
      <div class="esim-card-top">
        <div class="esim-flag">${countryCodeToFlag(o.country_code)}</div>
        <div class="esim-card-main">
          <div class="esim-title">${escapeHtml(o.package_title)}</div>
          <div class="status">${t("status_" + o.status)}</div>
        </div>
        <div class="esim-price">${o.price} ${o.currency}</div>
      </div>
      <div class="esim-stat-grid">
        ${gb ? `<div class="esim-stat"><div class="esim-stat-label">${t("stat_data")}</div><div class="esim-stat-value">${gb} GB</div></div>` : ""}
        ${o.validity_days ? `<div class="esim-stat"><div class="esim-stat-label">${t("stat_validity")}</div><div class="esim-stat-value">${o.validity_days} ${t("days_short")}</div></div>` : ""}
      </div>
      ${o.qr_code_data ? `<img class="qr-image" src="${o.qr_code_data}" alt="QR">` : ""}
      ${o.activation_instructions ? `<div class="hint">${t("qr_manual_hint")}</div><div class="iccid">${o.activation_instructions}</div>` : ""}
      ${o.iccid ? `<div class="iccid">ICCID: ${o.iccid}</div>` : ""}
      ${o.status === "active" && !o.reviewed ? `
        <div class="review-block">
          <select class="review-rating-select">
            <option value="5">★★★★★</option>
            <option value="4">★★★★</option>
            <option value="3">★★★</option>
            <option value="2">★★</option>
            <option value="1">★</option>
          </select>
          <input type="text" class="review-comment-input" placeholder="${t("review_placeholder")}">
          <button class="btn review-submit-btn">${t("review_submit")}</button>
        </div>
      ` : ""}
    `;
    list.appendChild(card);

    const reviewBtn = card.querySelector(".review-submit-btn");
    if (reviewBtn) {
      reviewBtn.addEventListener("click", async () => {
        reviewBtn.disabled = true;
        try {
          await api(`/api/orders/${o.id}/review`, {
            method: "POST",
            body: JSON.stringify({
              rating: parseInt(card.querySelector(".review-rating-select").value, 10),
              comment: card.querySelector(".review-comment-input").value,
            }),
          });
          card.querySelector(".review-block").outerHTML = `<p class="hint">${t("review_thanks")}</p>`;
        } catch (e) {
          reviewBtn.disabled = false;
          tg.showAlert("Error, please try again.");
        }
      });
    }
  }
}

// --- Категории (лаунж/туры/что угодно ещё): список товаров ---
async function loadProducts(categorySlug) {
  const products = await api(`/api/products?category=${categorySlug}&lang=${currentLang}`);
  const list = document.getElementById("products-list");
  list.innerHTML = "";
  if (products.length === 0) {
    list.innerHTML = `<div class="empty">${t("products_empty")}</div>`;
    return;
  }
  for (const p of products) {
    const card = document.createElement("div");
    card.className = "product-card";
    card.innerHTML = `
      <div class="product-title">${escapeHtml(p.title)}</div>
      ${p.description ? `<div class="product-description">${escapeHtml(p.description)}</div>` : ""}
      <div class="product-bottom">
        <span class="product-price"></span>
        <button class="ask-btn" data-id="${p.id}">${t("product_ask_button")}</button>
      </div>
    `;
    if (p.price !== null) {
      card.querySelector(".product-price").textContent = `${p.price} ${p.currency}`;
    }
    card.querySelector(".ask-btn").addEventListener("click", () => startProductChat(p.id));
    list.appendChild(card);
  }
}

async function startProductChat(productId) {
  const res = await api("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ category_id: currentCategory.id, product_id: productId }),
  });
  currentConversationId = res.conversation_id;
  chatReturnScreen = "products";
  await loadChatMessages();
  showScreen("chat");
}

// --- Чаты: список ---
async function loadChatsList() {
  const conversations = await api(`/api/conversations?lang=${currentLang}`);
  const list = document.getElementById("chats-list");
  list.innerHTML = "";
  if (conversations.length === 0) {
    list.innerHTML = `<div class="empty">${t("chats_empty")}</div>`;
    return;
  }
  for (const c of conversations) {
    const row = document.createElement("div");
    row.className = "row";
    const subtitle = c.product_title ? `${c.topic_label} · ${c.product_title}` : c.topic_label;
    row.innerHTML = `
      <div class="main">
        <div class="title">${escapeHtml(subtitle)}</div>
        <div class="subtitle">${c.last_message_preview ? escapeHtml(c.last_message_preview) : ""}</div>
      </div>
      <span class="chevron">›</span>
    `;
    row.addEventListener("click", () => {
      currentConversationId = c.id;
      chatReturnScreen = "chats";
      loadChatMessages();
      showScreen("chat");
    });
    list.appendChild(row);
  }
}

document.getElementById("new-support-chat-btn").addEventListener("click", async () => {
  const res = await api("/api/conversations", {
    method: "POST",
    body: JSON.stringify({}),
  });
  currentConversationId = res.conversation_id;
  chatReturnScreen = "chats";
  await loadChatMessages();
  showScreen("chat");
});

// --- Чат: переписка ---
let chatPollTimer = null;

async function loadChatMessages() {
  if (!currentConversationId) return;
  const messages = await api(`/api/conversations/${currentConversationId}/messages`);
  const list = document.getElementById("chat-messages");
  const wasAtBottom = list.scrollTop + list.clientHeight >= list.scrollHeight - 20;
  list.innerHTML = messages.map(renderChatBubble).join("");
  if (wasAtBottom || messages.length <= 1) {
    list.scrollTop = list.scrollHeight;
  }
  if (chatPollTimer) clearInterval(chatPollTimer);
  chatPollTimer = setInterval(loadChatMessages, 3000);
}

function renderChatBubble(m) {
  const side = m.direction === "in" ? "mine" : "theirs";
  let attachmentHtml = "";
  if (m.attachment_url && m.attachment_type === "photo") {
    attachmentHtml = `<a href="${m.attachment_url}" target="_blank"><img class="chat-image" src="${m.attachment_url}"></a>`;
  } else if (m.attachment_url) {
    attachmentHtml = `<a class="chat-file" href="${m.attachment_url}" target="_blank">📎 ${escapeHtml(m.attachment_filename || "file")}</a>`;
  }
  const textHtml = m.text ? `<div>${escapeHtml(m.text)}</div>` : "";
  return `<div class="bubble ${side}">${attachmentHtml}${textHtml}</div>`;
}

async function sendChatMessage() {
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  if (!text || !currentConversationId) return;
  input.value = "";
  try {
    await api(`/api/conversations/${currentConversationId}/messages`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    await loadChatMessages();
  } catch (e) {
    tg.showAlert("Error, please try again.");
    input.value = text;
  }
}

document.getElementById("chat-send-btn").addEventListener("click", sendChatMessage);
document.getElementById("chat-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChatMessage();
});

document.getElementById("chat-attach-btn").addEventListener("click", () => {
  document.getElementById("chat-file-input").click();
});

document.getElementById("chat-file-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  e.target.value = ""; // сброс, чтобы можно было выбрать тот же файл ещё раз
  if (!file || !currentConversationId) return;

  const attachBtn = document.getElementById("chat-attach-btn");
  attachBtn.disabled = true;
  try {
    const formData = new FormData();
    formData.append("file", file);
    await apiUpload(`/api/conversations/${currentConversationId}/attachments`, formData);
    await loadChatMessages();
  } catch (err) {
    tg.showAlert("Error, please try again.");
  } finally {
    attachBtn.disabled = false;
  }
});

// --- Старт ---
setLang(currentLang);
loadHomeCategories();
showScreen("home");

api("/api/test-payment-enabled")
  .then((res) => {
    testPaymentEnabled = res.enabled;
    walletPayEnabled = res.wallet_pay;
    oxapayEnabled = res.oxapay;
    botUsername = res.bot_username || "";
  })
  .catch(() => { testPaymentEnabled = false; });