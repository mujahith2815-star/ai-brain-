// Orvix Sphere Dashboard WebSocket & API Client
let ws = null;

function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("[WS] Connected to Orvix Sphere Server");
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "MESSAGE") {
        removeTypingIndicator();
        appendMessage(data.role, data.content);
      } else if (data.type === "STATUS") {
        showTypingIndicator(data.message);
      }
    } catch (e) {
      console.log("[WS] Message:", event.data);
    }
  };

  ws.onclose = () => {
    console.log("[WS] Disconnected. Reconnecting in 3s...");
    setTimeout(initWebSocket, 3000);
  };
}

function appendMessage(role, content) {
  const container = document.getElementById("chat-messages");
  const isUser = role === "user";
  const div = document.createElement("div");
  div.className = "flex items-start space-x-3";

  const badge = isUser
    ? `<div class="w-8 h-8 rounded-lg bg-cyan-500 text-slate-950 flex items-center justify-center text-xs font-bold shrink-0">YOU</div>`
    : `<div class="w-8 h-8 rounded-lg bg-cyan-950 border border-cyan-500/40 flex items-center justify-center text-cyan-300 text-xs font-bold shrink-0">OS</div>`;

  const bubbleClass = isUser
    ? "bg-cyan-950/40 border border-cyan-500/30 text-cyan-100 rounded-tr-none"
    : "bg-slate-850 border border-slate-800 text-slate-200 rounded-tl-none";

  const renderedContent = marked.parse(content);

  div.innerHTML = `
    ${badge}
    <div class="flex-1 ${bubbleClass} p-3.5 rounded-xl shadow-md prose prose-invert max-w-none text-sm">
      ${renderedContent}
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function showTypingIndicator(text) {
  removeTypingIndicator();
  const container = document.getElementById("chat-messages");
  const ind = document.createElement("div");
  ind.id = "typing-indicator";
  ind.className = "flex items-center space-x-2 text-cyan-400 text-xs italic pl-11";
  ind.innerHTML = `<span>⚙️</span><span>${text}</span>`;
  container.appendChild(ind);
  container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
  const ind = document.getElementById("typing-indicator");
  if (ind) ind.remove();
}

async function handleSend(e) {
  e.preventDefault();
  const input = document.getElementById("chat-input");
  const msg = input.value.trim();
  if (!msg) return;

  appendMessage("user", msg);
  input.value = "";
  showTypingIndicator("Thinking...");

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ message: msg }));
  } else {
    // Fallback REST POST
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg })
      });
      const data = await res.json();
      removeTypingIndicator();
      appendMessage("assistant", data.response || "No response.");
    } catch (err) {
      removeTypingIndicator();
      appendMessage("assistant", "Communication error connecting to core agent.");
    }
  }
}

async function fetchTelemetry() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();

    // Primary model
    const primaryName = data.primary_model || (data.models && data.models.primary) || "Gemini 2.0 Flash";
    const headerPrimary = document.getElementById("header-primary-model");
    if (headerPrimary) headerPrimary.innerText = primaryName;
    const statusPrimary = document.getElementById("status-primary");
    if (statusPrimary) statusPrimary.innerText = primaryName;

    // Fallback model
    const fallbackName = data.fallback_model || (data.models && data.models.fallback) || "Qwen2.5-7B";
    const headerFallback = document.getElementById("header-fallback-model");
    if (headerFallback) headerFallback.innerText = fallbackName;
    const statusFallback = document.getElementById("status-fallback");
    if (statusFallback) statusFallback.innerText = fallbackName;
    const statusSecondary = document.getElementById("status-secondary");
    if (statusSecondary) statusSecondary.innerText = fallbackName;

    // Router mode
    const routerMode = data.router_mode || (data.models && data.models.mode) || "cloud_first";
    const headerMode = document.getElementById("header-router-mode");
    if (headerMode) headerMode.innerText = routerMode;
    const statusMode = document.getElementById("status-mode");
    if (statusMode) statusMode.innerText = `Mode: ${routerMode}`;

    // MCP
    const online = data.mcp_servers_online !== undefined ? data.mcp_servers_online : (data.mcp ? data.mcp.connected : 0);
    const total = data.mcp_servers_total !== undefined ? data.mcp_servers_total : (data.mcp ? data.mcp.total : 0);
    const mcpText = `${online}/${total} Active`;
    const headerMcp = document.getElementById("header-mcp-status");
    if (headerMcp) headerMcp.innerText = mcpText;
    const statusMcp = document.getElementById("status-mcp");
    if (statusMcp) statusMcp.innerText = mcpText;

    // Proactive
    if (data.proactive) {
      const pState = data.proactive.state || (data.proactive_enabled ? "ENABLED" : "DISABLED");
      const headerProactive = document.getElementById("header-proactive-status");
      if (headerProactive) headerProactive.innerText = pState;
      const statusProactive = document.getElementById("status-proactive");
      if (statusProactive) statusProactive.innerText = pState;
    }
  } catch (e) {
    console.error("Telemetry fetch error:", e);
  }
}

async function fetchApprovals() {
  try {
    const res = await fetch("/api/queue");
    const data = await res.json();
    const list = document.getElementById("approval-queue-list");
    const badge = document.getElementById("queue-count-badge");
    const queue = data.queue || [];
    badge.innerText = `${queue.length} PENDING`;

    if (queue.length === 0) {
      list.innerHTML = `<div class="text-slate-500 text-center py-2 text-[11px]">No actions awaiting approval.</div>`;
      return;
    }

    list.innerHTML = queue.map(q => `
      <div class="bg-slate-950 p-2.5 rounded border border-yellow-500/30 flex items-center justify-between">
        <div class="truncate mr-2">
          <div class="font-bold text-yellow-300">#${q.id} ${q.action_name}</div>
          <div class="text-[10px] text-slate-400 truncate">${q.tool} | ${q.reason}</div>
        </div>
        <div class="flex space-x-1 shrink-0">
          <button onclick="resolveAction(${q.id}, true)" class="px-2 py-1 bg-emerald-950 hover:bg-emerald-900 border border-emerald-500/40 text-emerald-300 rounded text-[10px]">Approve</button>
          <button onclick="resolveAction(${q.id}, false)" class="px-2 py-1 bg-rose-950 hover:bg-rose-900 border border-rose-500/40 text-rose-300 rounded text-[10px]">Reject</button>
        </div>
      </div>
    `).join("");
  } catch (e) {}
}

async function fetchAudit() {
  try {
    const res = await fetch("/api/audit");
    const data = await res.json();
    const list = document.getElementById("audit-log-list");
    const logs = data.logs || [];
    if (logs.length === 0) {
      list.innerHTML = `<div class="text-slate-500 text-center py-4">No audit events yet.</div>`;
      return;
    }
    list.innerHTML = logs.slice(0, 10).map(l => `
      <div class="p-1.5 rounded bg-slate-950/60 border border-slate-800/80 flex items-center justify-between text-[10px]">
        <span class="text-slate-300 font-semibold truncate max-w-[180px]">${l.task_name}</span>
        <span class="${l.approved_by_user ? 'text-emerald-400' : 'text-slate-500'} shrink-0">${l.approved_by_user ? 'APPROVED' : 'AUTO'}</span>
      </div>
    `).join("");
  } catch (e) {}
}

async function resolveAction(id, approve) {
  const endpoint = approve ? `/api/approve/${id}` : `/api/reject/${id}`;
  await fetch(endpoint, { method: "POST" });
  fetchApprovals();
  fetchAudit();
}

async function checkHealth() {
  const res = await fetch("/api/health");
  const data = await res.json();
  alert(`Doctor Health Report:
Healthy: ${data.healthy}
Passed Checks: ${data.checks ? data.checks.length : 'All'}`);
}

function clearChat() {
  document.getElementById("chat-messages").innerHTML = "";
}

function toggleVoiceInput() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    alert("Speech recognition not supported in this browser. You can type commands in the input box.");
    return;
  }
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRec();
  recognition.lang = "en-US";
  recognition.start();

  const vBtn = document.getElementById("voice-btn");
  vBtn.classList.add("bg-rose-900", "animate-pulse");

  recognition.onresult = (evt) => {
    vBtn.classList.remove("bg-rose-900", "animate-pulse");
    const transcript = evt.results[0][0].transcript;
    document.getElementById("chat-input").value = transcript;
    document.getElementById("chat-form").dispatchEvent(new Event("submit"));
  };

  recognition.onerror = () => {
    vBtn.classList.remove("bg-rose-900", "animate-pulse");
  };
}

// Auto-refresh telemetry & approvals every 5s
window.addEventListener("DOMContentLoaded", () => {
  initWebSocket();
  fetchTelemetry();
  fetchApprovals();
  fetchAudit();
  setInterval(() => {
    fetchTelemetry();
    fetchApprovals();
    fetchAudit();
  }, 5000);
});
