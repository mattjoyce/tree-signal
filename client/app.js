const API_BASE = window.localStorage.getItem("tree-signal.api") || "http://localhost:8000";

const layoutContainer = document.querySelector("#layout-grid");
const layoutTemplate = document.querySelector("#layout-item-template");
const messageContainer = document.querySelector("#message-list");
const messageTemplate = document.querySelector("#message-item-template");
const lastRefresh = document.querySelector("#last-refresh");
const refreshButton = document.querySelector("#refresh-button");
const channelForm = document.querySelector("#channel-form");
const channelInput = document.querySelector("#channel-input");

async function fetchJSON(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Request failed (${response.status}): ${detail}`);
  }
  return response.json();
}

function renderLayout(frames) {
  layoutContainer.innerHTML = "";
  frames.forEach((frame) => {
    const node = layoutTemplate.content.cloneNode(true);
    node.querySelector(".layout-item__path").textContent = frame.path.join(".");
    node.querySelector(".layout-item__state").textContent = frame.state;
    node.querySelector(".layout-item__weight").textContent = frame.weight.toFixed(2);
    node
      .querySelector(".layout-item__rect")
      .textContent = `${frame.rect.x.toFixed(2)}, ${frame.rect.y.toFixed(2)} → ${frame.rect.width.toFixed(2)}×${frame.rect.height.toFixed(2)}`;
    layoutContainer.appendChild(node);
  });
}

function renderMessages(messages) {
  messageContainer.innerHTML = "";
  messages.forEach((message) => {
    const node = messageTemplate.content.cloneNode(true);
    const article = node.querySelector(".message-item");
    const badge = node.querySelector(".badge");
    const timestamp = node.querySelector(".timestamp");
    const payload = node.querySelector(".payload");

    badge.textContent = message.severity.toUpperCase();
    badge.dataset.severity = message.severity;
    const date = new Date(message.received_at);
    timestamp.textContent = date.toLocaleString();
    payload.textContent = message.payload;

    messageContainer.appendChild(article);
  });
}

async function refreshDashboard(channel) {
  try {
    const [layout, messages] = await Promise.all([
      fetchJSON("/v1/layout"),
      fetchJSON(`/v1/messages/${encodeURIComponent(channel)}`),
    ]);

    renderLayout(layout);
    renderMessages(messages);
    lastRefresh.textContent = `Last refresh: ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    console.error(error);
    lastRefresh.textContent = `Error: ${error.message}`;
  }
}

refreshButton.addEventListener("click", () => {
  refreshDashboard(channelInput.value.trim());
});

channelForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const channel = channelInput.value.trim();
  if (!channel) {
    return;
  }
  refreshDashboard(channel);
});

// initial load
refreshDashboard(channelInput.value.trim());
