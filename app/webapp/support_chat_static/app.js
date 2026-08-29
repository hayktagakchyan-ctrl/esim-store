const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

const initData = tg.initData;

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": initData,
      ...(options.headers || {}),
    },
  });
  if (!res.ok) throw new Error(`API ${path} -> ${res.status}`);
  return res.json();
}

async function apiUpload(path, formData) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "X-Telegram-Init-Data": initData },
    body: formData,
  });
  if (!res.ok) throw new Error(`API ${path} -> ${res.status}`);
  return res.json();
}

let currentConversationId = null;
let listPollTimer = null;
let threadPollTimer = null;

function stopPolling() {
  if (listPollTimer) { clearInterval(listPollTimer); listPollTimer = null; }
  if (threadPollTimer) { clearInterval(threadPollTimer); threadPollTimer = null; }
}

function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function showList() {
  stopPolling();
  currentConversationId = null;
  document.getElementById("screen-list").hidden = false;
  document.getElementById("screen-thread").hidden = true;
  document.getElementById("back-btn").hidden = true;
  document.getElementById("header-title").textContent = "Чаты с клиентами";
  loadConversations();
  listPollTimer = setInterval(loadConversations, 5000);
}

async function loadConversations() {
  const conversations = await api("/support-chat/api/conversations");
  const list = document.getElementById("conversation-list");
  list.innerHTML = "";
  if (conversations.length === 0) {
    list.innerHTML = '<div class="empty">Пока нет ни одного чата</div>';
    return;
  }
  for (const c of conversations) {
    const row = document.createElement("div");
    row.className = "conv-row" + (c.unread ? " unread" : "");
    const topicLine = c.product_title ? `${c.topic_label} · ${c.product_title}` : c.topic_label;
    row.innerHTML = `
      <div class="row-top">
        <span class="client-name">${c.client_name}</span>
        <span class="time">${formatTime(c.updated_at)}</span>
      </div>
      <div class="topic-line">${topicLine}</div>
      <div class="preview">${c.last_message_preview || ""}</div>
    `;
    row.addEventListener("click", () => openConversation(c.id, c.client_name, topicLine));
    list.appendChild(row);
  }
}

function openConversation(id, clientName, topicLine) {
  stopPolling();
  currentConversationId = id;
  document.getElementById("screen-list").hidden = true;
  document.getElementById("screen-thread").hidden = false;
  document.getElementById("back-btn").hidden = false;
  document.getElementById("header-title").textContent = `${clientName} · ${topicLine}`;
  loadMessages();
  threadPollTimer = setInterval(loadMessages, 3000);
}

async function loadMessages() {
  if (!currentConversationId) return;
  const messages = await api(`/support-chat/api/conversations/${currentConversationId}/messages`);
  const list = document.getElementById("message-list");
  const wasAtBottom = list.scrollTop + list.clientHeight >= list.scrollHeight - 20;
  list.innerHTML = messages.map(renderBubble).join("");
  if (wasAtBottom || messages.length <= 1) {
    list.scrollTop = list.scrollHeight;
  }
}

function renderBubble(m) {
  let attachmentHtml = "";
  if (m.attachment_url && m.attachment_type === "photo") {
    attachmentHtml = `<a href="${m.attachment_url}" target="_blank"><img class="chat-image" src="${m.attachment_url}"></a>`;
  } else if (m.attachment_url) {
    attachmentHtml = `<a class="chat-file" href="${m.attachment_url}" target="_blank">📎 ${escapeHtml(m.attachment_filename || "file")}</a>`;
  }
  const textHtml = m.text ? `<div>${escapeHtml(m.text)}</div>` : "";
  return `<div class="bubble ${m.direction}">${attachmentHtml}${textHtml}</div>`;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

document.getElementById("back-btn").addEventListener("click", showList);

async function sendReply() {
  const input = document.getElementById("message-input");
  const text = input.value.trim();
  if (!text || !currentConversationId) return;
  input.value = "";
  try {
    await api(`/support-chat/api/conversations/${currentConversationId}/reply`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    await loadMessages();
  } catch (e) {
    tg.showAlert("Не получилось отправить, попробуй ещё раз.");
    input.value = text;
  }
}

document.getElementById("send-btn").addEventListener("click", sendReply);
document.getElementById("message-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendReply();
});

document.getElementById("chat-attach-btn").addEventListener("click", () => {
  document.getElementById("chat-file-input").click();
});

document.getElementById("chat-file-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file || !currentConversationId) return;

  const attachBtn = document.getElementById("chat-attach-btn");
  attachBtn.disabled = true;
  try {
    const formData = new FormData();
    formData.append("file", file);
    await apiUpload(`/support-chat/api/conversations/${currentConversationId}/attachments`, formData);
    await loadMessages();
  } catch (err) {
    tg.showAlert("Не получилось отправить, попробуй ещё раз.");
  } finally {
    attachBtn.disabled = false;
  }
});

showList();
