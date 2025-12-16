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
if (params.has("debug")) {
  window.localStorage.setItem("tree-signal.showDebug", params.get("debug"));
}

// Auto-detect API base URL - if client is on port 8014, assume API is on 8013 on same host
const DEFAULT_API_BASE = window.location.port === "8014" 
  ? `${window.location.protocol}//${window.location.hostname}:8013`
  : window.location.port === "8001" 
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : "http://localhost:8013";
  
const API_BASE = window.localStorage.getItem("tree-signal.api") || DEFAULT_API_BASE;
const API_KEY = window.localStorage.getItem("tree-signal.apiKey") || null;
const REFRESH_INTERVAL_MS = Number(window.localStorage.getItem("tree-signal.refreshMs") || "5000");
const SHOW_DEBUG = window.localStorage.getItem("tree-signal.showDebug") === "true";

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

  const orderedFrames = [...frames].sort((a, b) => {
    const depthDelta = a.path.length - b.path.length;
    if (depthDelta !== 0) {
      return depthDelta;
    }
    return a.path.join(".").localeCompare(b.path.join("."));
  });

  const boundsAccumulator = new Map();

  const extendBounds = (key, rect) => {
    const x1 = rect.x;
    const y1 = rect.y;
    const x2 = rect.x + rect.width;
    const y2 = rect.y + rect.height;
    const existing = boundsAccumulator.get(key);
    if (existing) {
      existing.minX = Math.min(existing.minX, x1);
      existing.minY = Math.min(existing.minY, y1);
      existing.maxX = Math.max(existing.maxX, x2);
      existing.maxY = Math.max(existing.maxY, y2);
    } else {
      boundsAccumulator.set(key, { minX: x1, minY: y1, maxX: x2, maxY: y2 });
    }
  };

  orderedFrames.forEach((frame) => {
    const parts = frame.path;
    const rect = frame.rect;
    for (let depth = 1; depth <= parts.length; depth += 1) {
      const key = parts.slice(0, depth).join(".");
      extendBounds(key, rect);
    }
  });

  const boundsByChannel = new Map();
  boundsAccumulator.forEach((acc, key) => {
    boundsByChannel.set(key, {
      x: acc.minX,
      y: acc.minY,
      width: Math.max(0, acc.maxX - acc.minX),
      height: Math.max(0, acc.maxY - acc.minY),
    });
  });

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

  const normaliseRect = (rect, parentRect) => {
    const width = parentRect.width || 1;
    const height = parentRect.height || 1;
    const relative = {
      x: width === 0 ? 0 : (rect.x - parentRect.x) / width,
      y: height === 0 ? 0 : (rect.y - parentRect.y) / height,
      width: width === 0 ? 0 : rect.width / width,
      height: height === 0 ? 0 : rect.height / height,
    };

    const clampedX = clamp(relative.x, 0, 1);
    const clampedY = clamp(relative.y, 0, 1);
    const maxWidth = 1 - clampedX;
    const maxHeight = 1 - clampedY;

    return {
      x: clampedX,
      y: clampedY,
      width: clamp(relative.width, 0, maxWidth),
      height: clamp(relative.height, 0, maxHeight),
    };
  };

  const cellRegistry = new Map();
  const rootRect = { x: 0, y: 0, width: 1, height: 1 };

  orderedFrames.forEach((frame) => {
    const channel = frame.path.join(".");
    const depth = frame.path.length - 1;
    const parentPath = frame.path.slice(0, -1);
    const parentChannel = parentPath.join(".");
    const parentRect = parentChannel ? boundsByChannel.get(parentChannel) || rootRect : rootRect;
    const displayRect = boundsByChannel.get(channel) || frame.rect;
    const relativeRect = normaliseRect(displayRect, parentRect);

    const cell = document.createElement("div");
    cell.className = `layout-cell state-${frame.state.toLowerCase()}`;
    cell.dataset.depth = String(depth);
    cell.dataset.channel = channel;
    if (parentChannel) {
      cell.dataset.parent = parentChannel;
    }
    cell.style.zIndex = String(depth + 1);

    const gapPercent = depth === 0 ? 0 : 0.6;
    const widthPercent = Math.max(relativeRect.width * 100 - gapPercent * 2, 0);
    const heightPercent = Math.max(relativeRect.height * 100 - gapPercent * 2, 0);
    const leftPercent = relativeRect.x * 100 + gapPercent;
    const topPercent = relativeRect.y * 100 + gapPercent;

    cell.style.left = `${leftPercent}%`;
    cell.style.top = `${topPercent}%`;
    cell.style.width = `${widthPercent}%`;
    cell.style.height = `${heightPercent}%`;

    const content = document.createElement("div");
    content.className = "layout-content";

    const header = document.createElement("header");
    const pathSpan = document.createElement("span");
    pathSpan.className = "path";
    pathSpan.textContent = channel;
    const stateSpan = document.createElement("span");
    stateSpan.className = "state";
    stateSpan.textContent = frame.state;
    header.append(pathSpan, stateSpan);

    const divider = document.createElement("div");
    divider.className = "divider";

    const messagesContainer = document.createElement("div");
    messagesContainer.className = "messages";
    const messages = historyMap.get(channel) || [];
    if (messages.length) {
      const latest = messages[messages.length - 1];
      const snippet = document.createElement("div");
      snippet.className = "snippet";
      snippet.dataset.severity = latest.severity;
      const time = document.createElement("time");
      time.dateTime = latest.received_at;
      time.textContent = new Date(latest.received_at).toLocaleTimeString();
      const payload = document.createElement("div");
      payload.textContent = latest.payload;
      snippet.append(time, payload);
      messagesContainer.appendChild(snippet);
    }

    if (SHOW_DEBUG) {
      const metrics = document.createElement("div");
      metrics.className = "metrics";
      metrics.textContent = `w=${frame.weight.toFixed(2)} // ${frame.rect.width.toFixed(2)}×${frame.rect.height.toFixed(2)}`;
      content.append(header, metrics, divider, messagesContainer);
    } else {
      content.append(header, divider, messagesContainer);
    }

    const childrenHost = document.createElement("div");
    childrenHost.className = "layout-children";
    childrenHost.hidden = true;

    cell.append(content, childrenHost);

    cellRegistry.set(channel, { cell, childrenHost, hasChildren: false });

    const parentEntry = cellRegistry.get(parentChannel);
    if (parentEntry) {
      parentEntry.childrenHost.append(cell);
      parentEntry.childrenHost.hidden = false;
      parentEntry.cell.classList.add("has-children");
      parentEntry.hasChildren = true;
    } else {
      layoutStage.appendChild(cell);
    }
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
