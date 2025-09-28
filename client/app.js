const params = new URLSearchParams(window.location.search);

if (params.has("api")) {
  window.localStorage.setItem("tree-signal.api", params.get("api"));
}
if (params.has("apiKey")) {
  window.localStorage.setItem("tree-signal.apiKey", params.get("apiKey"));
}
if (params.has("refresh")) {
  window.localStorage.setItem("tree-signal.refreshMs", params.get("refresh"));
}

const API_BASE = window.localStorage.getItem("tree-signal.api") || "http://localhost:8000";
const API_KEY = window.localStorage.getItem("tree-signal.apiKey") || null;
const REFRESH_INTERVAL_MS = Number(window.localStorage.getItem("tree-signal.refreshMs") || "5000");

const layoutStage = document.querySelector("#layout-stage");
const messageContainer = document.querySelector("#message-list");
const messageTemplate = document.querySelector("#message-item-template");
const lastRefresh = document.querySelector("#last-refresh");
const refreshButton = document.querySelector("#refresh-button");
const channelForm = document.querySelector("#channel-form");
const channelInput = document.querySelector("#channel-input");
const intervalDisplay = document.querySelector("#refresh-interval");
const messagesChannelLabel = document.querySelector("#messages-channel");
const clientVersionLabel = document.querySelector("#client-version");

const CLIENT_VERSION = "v0.1.0";
if (clientVersionLabel) {
  clientVersionLabel.textContent = CLIENT_VERSION;
}

let currentChannel = channelInput.value.trim() || "alpha.beta";

let refreshTimer = null;

function requestHeaders() {
  const headers = new Headers();
  if (API_KEY) {
    headers.set("x-api-key", API_KEY);
  }
  return headers;
}

async function fetchJSON(path) {
  const response = await fetch(`${API_BASE}${path}`, { headers: requestHeaders() });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Request failed (${response.status}): ${detail}`);
  }
  return response.json();
}

function renderLayout(frames) {
  layoutStage.innerHTML = "";
  frames.forEach((frame) => {
    const channel = frame.path.join(".");
    const depth = frame.path.length - 1;
    const cell = document.createElement("div");
    cell.className = `layout-cell state-${frame.state.toLowerCase()}`;
    cell.dataset.depth = String(depth);
    cell.dataset.channel = channel;
    cell.style.left = `${frame.rect.x * 100}%`;
    cell.style.top = `${frame.rect.y * 100}%`;
    cell.style.width = `${frame.rect.width * 100}%`;
    cell.style.height = `${frame.rect.height * 100}%`;

    if (channel === currentChannel) {
      cell.classList.add("selected");
    }

    const header = document.createElement("header");
    const pathSpan = document.createElement("span");
    pathSpan.className = "path";
    pathSpan.textContent = channel;
    const stateSpan = document.createElement("span");
    stateSpan.className = "state";
    stateSpan.textContent = frame.state;
    header.append(pathSpan, stateSpan);

    const metrics = document.createElement("div");
    metrics.className = "metrics";
    metrics.textContent = `w=${frame.weight.toFixed(2)} // ${frame.rect.width.toFixed(2)}×${frame.rect.height.toFixed(2)}`;

    cell.append(header, metrics);
    cell.addEventListener("click", () => {
      selectChannel(channel);
    });

    layoutStage.appendChild(cell);
  });
}

function renderMessages(messages) {
  messageContainer.innerHTML = "";
  if (!messages.length) {
    const empty = document.createElement("p");
    empty.className = "message-empty";
    empty.textContent = "No messages yet.";
    messageContainer.appendChild(empty);
    return;
  }

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

async function refreshDashboard(channel = currentChannel) {
  if (!channel) {
    return;
  }
  currentChannel = channel;
  channelInput.value = currentChannel;
  messagesChannelLabel.textContent = currentChannel;
  try {
    const [layout, messages] = await Promise.all([
      fetchJSON("/v1/layout"),
      fetchJSON(`/v1/messages/${encodeURIComponent(currentChannel)}`),
    ]);

    renderLayout(layout);
    renderMessages(messages);
    lastRefresh.textContent = `Last refresh: ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    console.error(error);
    lastRefresh.textContent = `Error: ${error.message}`;
  }
}

function scheduleRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
  intervalDisplay.textContent = `(auto ${Math.round(REFRESH_INTERVAL_MS / 1000)}s)`;
  refreshTimer = setInterval(() => refreshDashboard(), REFRESH_INTERVAL_MS);
}

function selectChannel(channel) {
  refreshDashboard(channel);
  scheduleRefresh();
}

refreshButton.addEventListener("click", () => {
  refreshDashboard();
});

channelForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const channel = channelInput.value.trim();
  if (!channel) {
    return;
  }
  selectChannel(channel);
});

// initial load
selectChannel(currentChannel);
