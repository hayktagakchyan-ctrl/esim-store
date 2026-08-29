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
  "products", "my-esims", "chats", "chat",
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
async function loadCountries() {
  const countries = await api("/api/countries");
  const list = document.getElementById("country-list");
  list.innerHTML = "";
  if (countries.length === 0) {
    list.innerHTML = `<div class="empty">${t("catalog_empty")}</div>`;
    return;
  }
  for (const c of countries) {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <span class="flag">${countryCodeToFlag(c.code)}</span>
      <div class="main"><div class="title">${c.name}</div></div>
      <span class="chevron">›</span>
    `;
    row.addEventListener("click", () => openCountry(c));
    list.appendChild(row);
  }
}

document.getElementById("search-input").addEventListener("input", (e) => {
  const q = e.target.value.trim().toLowerCase();
  document.querySelectorAll("#country-list .row").forEach((row) => {
    const title = row.querySelector(".title").textContent.toLowerCase();
    row.style.display = title.includes(q) ? "" : "none";
  });
});

async function openCountry(country) {
  selectedCountry = country;
  const packages = await api(`/api/packages?country=${encodeURIComponent(country.code)}`);
  const list = document.getElementById("package-list");
  list.innerHTML = "";
  if (packages.length === 0) {
    list.innerHTML = `<div class="empty">${t("packages_empty")}</div>`;
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

function openCheckout(pkg) {
  selectedPackage = pkg;
  const summary = document.getElementById("checkout-summary");
  summary.innerHTML = `
    <div class="row-line"><span>${selectedCountry.name}</span><span>${pkg.title}</span></div>
    <div class="row-line total"><span>${t("checkout_total")}</span><span>${pkg.price} ${pkg.currency}</span></div>
  `;
  document.getElementById("payment-methods").hidden = false;
  document.getElementById("payment-waiting").hidden = true;
  document.getElementById("pay-walletpay-btn").hidden = !walletPayEnabled;
  document.getElementById("pay-oxapay-btn").hidden = !oxapayEnabled;
  document.getElementById("pay-test-btn").hidden = !testPaymentEnabled;
  showScreen("esim-checkout");
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
    if (method === "test") {
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

document.getElementById("pay-idram-btn").addEventListener("click", () => payWith("idram"));
document.getElementById("pay-walletpay-btn").addEventListener("click", () => payWith("wallet_pay"));
document.getElementById("pay-oxapay-btn").addEventListener("click", () => payWith("oxapay"));
document.getElementById("pay-test-btn").addEventListener("click", () => payWith("test"));

// --- Мои eSIM ---
async function loadMyEsims() {
  const orders = await api("/api/my-orders");
  const list = document.getElementById("my-esims-list");
  list.innerHTML = "";
  if (orders.length === 0) {
    list.innerHTML = `<div class="empty">${t("my_esims_empty")}</div>`;
    return;
  }
  for (const o of orders) {
    const card = document.createElement("div");
    card.className = "esim-card";
    card.innerHTML = `
      <div>${o.package_title}</div>
      <div class="status">${t("status_" + o.status)}</div>
      ${o.qr_code_data ? `<img class="qr-image" src="${o.qr_code_data}" alt="QR">` : ""}
      ${o.activation_instructions ? `<div class="hint">${t("qr_manual_hint")}</div><div class="iccid">${o.activation_instructions}</div>` : ""}
      ${o.iccid ? `<div class="iccid">ICCID: ${o.iccid}</div>` : ""}
    `;
    list.appendChild(card);
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
  })
  .catch(() => { testPaymentEnabled = false; });
