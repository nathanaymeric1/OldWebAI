const form = document.querySelector("#prompt-form");
const promptInput = document.querySelector("#prompt");
const conversation = document.querySelector("#conversation");
const historyList = document.querySelector("#history-list");
const historyPanel = document.querySelector("#history-panel");
const clearHistory = document.querySelector("#clear-history");
const historyToggle = document.querySelector("#history-toggle");
const sendButton = document.querySelector("#send-button");

const STORAGE_KEY = "fdj-chat-history-v1";

let history = loadHistory();

historyToggle?.addEventListener("click", () => {
  historyPanel.classList.toggle("is-open");
});

clearHistory?.addEventListener("click", () => {
  history = [];
  saveHistory();
  renderHistory();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const prompt = promptInput.value.trim();
  if (!prompt) return;

  setBusy(true);
  renderConversation(prompt, "Thinking...", "pending");

  try {
    const response = await fetch("http://127.0.0.1:8000/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "The server rejected the request.");
    }

    renderConversation(prompt, data.reply, "assistant", data.model);

    history.unshift({
      id: crypto.randomUUID(),
      prompt,
      reply: data.reply,
      model: data.model,
      createdAt: new Date().toISOString()
    });

    history = history.slice(0, 50);
    saveHistory();
    renderHistory();
    promptInput.value = "";
  } catch (error) {
    renderConversation(
      prompt,
      error.message || "Something went wrong.",
      "error"
    );
  } finally {
    setBusy(false);
  }
});

function renderConversation(prompt, reply, kind, model = "") {
  conversation.innerHTML = "";

  const user = document.createElement("article");
  user.className = "message user";
  user.innerHTML = `
    <div class="message-head">YOU</div>
    <div class="message-body"></div>
  `;
  user.querySelector(".message-body").textContent = prompt;

  const assistant = document.createElement("article");
  assistant.className = `message ${kind === "error" ? "assistant error" : "assistant"}`;
  assistant.innerHTML = `
    <div class="message-head">
      ${kind === "error" ? "ERROR" : "REPLY"}
      <span class="model-label">${escapeHtml(model || "pending")}</span>
    </div>
    <div class="message-body"></div>
  `;
  assistant.querySelector(".message-body").textContent = reply;

  conversation.append(user, assistant);
}

function renderHistory() {
  if (!historyList) return;
  historyList.innerHTML = "";

  if (!history.length) {
    historyList.innerHTML = '<p class="muted">No prompts yet.</p>';
    return;
  }

  for (const item of history) {
    const button = document.createElement("button");
    button.className = "history-item";
    button.type = "button";

    const date = new Date(item.createdAt).toLocaleString();

    button.innerHTML = `
      <strong></strong>
      <span>${escapeHtml(item.model || "unknown model")} · ${escapeHtml(date)}</span>
    `;

    button.querySelector("strong").textContent = item.prompt;

    button.addEventListener("click", () => {
      renderConversation(item.prompt, item.reply, "assistant", item.model);
      promptInput.value = item.prompt;
      historyPanel?.classList.remove("is-open");
      promptInput.focus();
    });

    historyList.appendChild(button);
  }
}

const response = await fetch("http://127.0.0.1:8000/api/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    prompt: prompt,
    history: history.map(item => ({
      role: "user",
      content: item.prompt
    })).concat(history.map(item => ({
      role: "assistant",
      content: item.reply
    }))) // Or maintain a sequential chronological array of turns
  })
});

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
  } catch {
    return [];
  }
}

function saveHistory() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

function setBusy(isBusy) {
  sendButton.disabled = isBusy;
  sendButton.textContent = isBusy ? "Sending..." : "Send prompt";
  promptInput.disabled = isBusy;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

renderHistory();
