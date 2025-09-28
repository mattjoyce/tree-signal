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
const lastRefresh = document.querySelector("#last-refresh");
const refreshButton = document.querySelector("#refresh-button");
const intervalDisplay = document.querySelector("#refresh-interval");
const clientVersionLabel = document.querySelector("#client-version");

const CLIENT_VERSION = "v0.1.0";
if (clientVersionLabel) {
  clientVersionLabel.textContent = CLIENT_VERSION;
}

let refreshTimer = null;

function requestHeaders() {
  const headers = new Headers();
  headers.set("Content-Type", "application/json");
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

async function fetchHistories(frames) {
  const uniqueChannels = Array.from(new Set(frames.map((frame) => frame.path.join("."))));
  const results = await Promise.all(
    uniqueChannels.map((channel) => fetchJSON(`/v1/messages/${encodeURIComponent(channel)}`))
  );
  const historyMap = new Map();
  uniqueChannels.forEach((channel, index) => {
    historyMap.set(channel, results[index] || []);
  });
  return historyMap;
}

function renderLayout(frames, historyMap) {
  layoutStage.innerHTML = "";
  if (!frames.length) {
    const empty = document.createElement("p");
    empty.className = "message-empty";
    empty.textContent = "No panels yet. Send a message to create one.";
    layoutStage.appendChild(empty);
    return;
  }

  const topLevelCount = frames.filter((frame) => frame.path.length === 1).length;

  frames.forEach((frame) => {
    const channel = frame.path.join(".");
    const depth = frame.path.length - 1;
    const cell = document.createElement("div");
    cell.className = `layout-cell state-${frame.state.toLowerCase()}`;
    cell.dataset.depth = String(depth);
    cell.dataset.channel = channel;

    const isSingleTopLevel = depth === 0 && topLevelCount <= 1;
    const gapPercent = depth === 0 ? 0 : 0.6;
    const widthPercent = Math.max(frame.rect.width * 100 - gapPercent * 2, 0);
    const heightPercent = Math.max(frame.rect.height * 100 - gapPercent * 2, 0);
    const leftPercent = frame.rect.x * 100 + gapPercent;
    const topPercent = frame.rect.y * 100 + gapPercent;

    cell.style.left = `${leftPercent}%`;
    cell.style.top = `${topPercent}%`;
    cell.style.width = `${widthPercent}%`;
    cell.style.height = `${heightPercent}%`;

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

    const divider = document.createElement("div");
    divider.className = "divider";

    const messagesContainer = document.createElement("div");
    messagesContainer.className = "messages";
    const messages = historyMap.get(channel) || [];
    if (!messages.length) {
      const placeholder = document.createElement("div");
      placeholder.className = "snippet";
      placeholder.textContent = "No messages yet.";
      messagesContainer.appendChild(placeholder);
    } else {
      const latest = messages[messages.length - 1];
      const snippet = document.createElement("div");
      snippet.className = "snippet";
      snippet.dataset.severity = latest.severity;
      const time = document.createElement("time");
      time.dateTime = latest.received_at;
      time.textContent = new Date(latest.received_at).toLocaleTimeString();
      const content = document.createElement("div");
      content.textContent = latest.payload;
      snippet.append(time, content);
      messagesContainer.appendChild(snippet);
    }

    cell.append(header, metrics, divider, messagesContainer);
    layoutStage.appendChild(cell);
  });
}

async function refreshDashboard() {
  try {
    const layout = await fetchJSON("/v1/layout");
    const historyMap = await fetchHistories(layout);
    renderLayout(layout, historyMap);
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

refreshButton.addEventListener("click", () => {
  refreshDashboard();
});

refreshDashboard();
scheduleRefresh();
