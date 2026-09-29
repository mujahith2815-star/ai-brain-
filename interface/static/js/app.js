/**
 * P.H.A.S.S SPHERE — Main Dashboard Controller Application.
 * Handles WebSocket telemetry sync, Goal trees, Memory inspection,
 * Learning analytics, Chat interaction, and Emergency Controls.
 */

let sim3d = null;
let ws = null;
let activeTab = "overview";

document.addEventListener("DOMContentLoaded", () => {
  // 1. Initialize 3D Simulation
  sim3d = new PHASSSimulation3D("canvas-container");

  // 2. Connect WebSocket
  connectWebSocket();

  // 3. Setup UI Event Listeners
  setupEventListeners();
});

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("[P.H.A.S.S WS] Connected to Telemetry Stream");
    updateConnectionBadge(true);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "TELEMETRY_FRAME") {
        handleTelemetryFrame(data);
      } else if (data.type === "NLU_RESPONSE") {
        handleNLUResponse(data.directive_result);
      }
    } catch (e) {
      console.error("[P.H.A.S.S WS] Parsing error:", e);
    }
  };

  ws.onclose = () => {
    console.warn("[P.H.A.S.S WS] Connection closed. Retrying in 2s...");
    updateConnectionBadge(false);
    setTimeout(connectWebSocket, 2000);
  };

  ws.onerror = (err) => {
    console.error("[P.H.A.S.S WS] Error:", err);
  };
}

function updateConnectionBadge(connected) {
  const badge = document.getElementById("connection-badge");
  if (!badge) return;
  if (connected) {
    badge.className = "status-pill";
    badge.innerHTML = `<span class="status-dot"></span> LINK ACTIVE`;
  } else {
    badge.className = "status-pill";
    badge.style.borderColor = "rgba(244, 63, 94, 0.4)";
    badge.style.color = "#f43f5e";
    badge.innerHTML = `<span class="status-dot" style="background:#f43f5e"></span> DISCONNECTED`;
  }
}

function handleTelemetryFrame(frame) {
  // 1. Update 3D Simulation
  if (sim3d) {
    sim3d.updateRobotPose(frame.robot_state);
    sim3d.updateLidarCloud(frame.lidar);
    sim3d.syncArenaObstacles(frame.arena ? frame.arena.obstacles : []);
  }

  // 2. Update HUD Telemetry
  const hud = frame.hud;
  const robot = frame.robot_state;
  const env = frame.environment;

  document.getElementById("hud-ai-status").innerText = hud.ai_status;
  document.getElementById("hud-state").innerText = hud.cognitive_state;
  document.getElementById("hud-goal").innerText = hud.current_goal;
  document.getElementById("hud-task").innerText = hud.current_task;
  document.getElementById("hud-confidence").innerText = hud.confidence_score;
  document.getElementById("hud-progress-bar").style.width = `${hud.goal_progress_pct}%`;
  document.getElementById("hud-progress-text").innerText = `${hud.goal_progress_pct}%`;

  document.getElementById("hud-battery").innerText = `${robot.battery_percentage}%`;
  document.getElementById("hud-battery-voltage").innerText = `${robot.battery_voltage}V`;
  document.getElementById("hud-battery-temp").innerText = `${robot.battery_temperature_c}°C`;
  document.getElementById("hud-internal-temp").innerText = `${robot.internal_temp_c}°C`;
  document.getElementById("hud-cpu").innerText = `${robot.cpu_usage_pct}%`;

  // Radar coordinates
  document.getElementById("radar-pos").innerText = `X: ${robot.position.x} | Y: ${robot.position.y} | H: ${robot.heading_deg}°`;
  document.getElementById("radar-lidar-min").innerText = `Min Clearance: ${frame.lidar ? frame.lidar.min_distance_m : '--'}m`;

  // 3. Render Active Goal & Subtask Tree
  renderGoalTree(frame.active_goals);

  // 4. Render Learning & Evaluation Metrics
  renderLearningMetrics(frame.learning_metrics, frame.evaluation_metrics);

  // 5. Render Logs
  renderEventLogs(frame.recent_events);
}

function renderGoalTree(activeGoals) {
  const container = document.getElementById("goals-container");
  if (!container) return;

  if (!activeGoals || activeGoals.length === 0) {
    container.innerHTML = `<div style="color:var(--text-dim); font-size:12px; font-style:italic;">No active goals in queue. System in standby monitoring mode.</div>`;
    return;
  }

  let html = "";
  activeGoals.forEach((goal) => {
    html += `
      <div class="hud-card" style="border-left: 3px solid var(--cyan-neon);">
        <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
          <span style="font-weight:700; font-size:13px; color:#ffffff;">${escapeHtml(goal.title)}</span>
          <span class="status-pill" style="font-size:10px; padding:2px 8px;">${goal.state}</span>
        </div>
        <div class="hud-label">Subtasks Breakdown (${goal.completion_percentage}%):</div>
        <div style="margin-top:6px;">
    `;

    (goal.subtasks || []).forEach((st, idx) => {
      html += `
        <div class="subtask-card ${st.state}">
          <div style="display:flex; justify-content:space-between;">
            <span style="font-weight:600;">[${idx + 1}] ${escapeHtml(st.title)}</span>
            <span style="font-family:var(--font-mono); color:var(--cyan-neon); font-size:10px;">${st.state}</span>
          </div>
          <div style="color:var(--text-muted); font-size:11px; margin-top:2px;">Tool: <code>${st.tool_name}</code></div>
          ${st.error ? `<div style="color:var(--rose-neon); font-size:10px; margin-top:2px;">Err: ${escapeHtml(st.error)}</div>` : ''}
        </div>
      `;
    });

    html += `</div></div>`;
  });

  container.innerHTML = html;
}

function renderLearningMetrics(learning, evalMetrics) {
  if (!learning || !evalMetrics) return;

  const rateEl = document.getElementById("metric-success-rate");
  if (rateEl) rateEl.innerText = `${evalMetrics.goal_success_rate_pct}%`;

  const qualityEl = document.getElementById("metric-plan-quality");
  if (qualityEl) qualityEl.innerText = `${Math.round(evalMetrics.planning_quality_score * 100)}%`;

  const recoveryEl = document.getElementById("metric-error-recovery");
  if (recoveryEl) recoveryEl.innerText = `${evalMetrics.error_recovery_rate_pct}%`;

  const autonomyEl = document.getElementById("metric-autonomy");
  if (autonomyEl) autonomyEl.innerText = `${evalMetrics.autonomy_index_pct}%`;

  const lessonsEl = document.getElementById("metric-total-lessons");
  if (lessonsEl) lessonsEl.innerText = learning.total_lessons_learned;
}

function renderEventLogs(events) {
  const container = document.getElementById("log-terminal");
  if (!container || !events) return;

  let html = "";
  events.forEach((ev) => {
    const timeStr = ev.timestamp ? ev.timestamp.substring(11, 19) : "";
    html += `
      <div class="log-entry">
        <span class="ts">[${timeStr}]</span>
        <span class="src">&lt;${escapeHtml(ev.source)}&gt;</span>
        <span class="type">[${escapeHtml(ev.type)}]</span>
        <span>${escapeHtml(JSON.stringify(ev.data).substring(0, 100))}</span>
      </div>
    `;
  });
  container.innerHTML = html;
}

function setupEventListeners() {
  // 1. Directive Submission
  const directiveInput = document.getElementById("directive-input");
  const sendBtn = document.getElementById("btn-send-directive");

  const sendDirective = () => {
    const text = directiveInput.value.trim();
    if (!text || !ws) return;

    appendChatMessage("user", text);
    ws.send(JSON.stringify({ type: "USER_DIRECTIVE", text: text }));
    directiveInput.value = "";

    // Simulated acknowledgement
    setTimeout(() => {
      appendChatMessage("phass", `Goal registered: "${text}". Formulating reasoning and plan.`);
    }, 400);
  };

  sendBtn.addEventListener("click", sendDirective);
  directiveInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendDirective();
  });

  // 2. Feedback Modal / Input
  const btnPositive = document.getElementById("btn-fb-positive");
  const btnCorrection = document.getElementById("btn-fb-correction");

  if (btnPositive) {
    btnPositive.addEventListener("click", () => {
      sendFeedback("Good job, the task was completed accurately.");
    });
  }

  if (btnCorrection) {
    btnCorrection.addEventListener("click", () => {
      const correction = prompt("Enter corrective instruction or rule for P.H.A.S.S to learn:");
      if (correction) {
        sendFeedback(correction);
      }
    });
  }

  // 3. Quick Action Buttons
  document.getElementById("btn-action-diagnose").addEventListener("click", () => {
    sendDirectiveCommand("Analyze the system and find the reason for the failure.");
  });

  document.getElementById("btn-action-scan").addEventListener("click", () => {
    sendDirectiveCommand("Inspect the environment and update the World Model.");
  });

  document.getElementById("btn-action-dock").addEventListener("click", () => {
    sendDirectiveCommand("Navigate to the Magnetic Charging Dock and recharge.");
  });

  // 4. Emergency Stop
  document.getElementById("btn-emergency-stop").addEventListener("click", () => {
    if (ws) {
      ws.send(JSON.stringify({ type: "EMERGENCY_STOP" }));
      appendChatMessage("phass", "EMERGENCY BRAKE ENGAGED. Autonomous motion halted.");
    }
  });

  document.getElementById("btn-resume-system").addEventListener("click", () => {
    if (ws) {
      ws.send(JSON.stringify({ type: "RESUME_SYSTEM" }));
      appendChatMessage("phass", "System emergency stop disengaged. Operational standby.");
    }
  });

  // 5. Spawn Dynamic Hazard
  document.getElementById("btn-spawn-hazard").addEventListener("click", () => {
    if (ws) {
      ws.send(JSON.stringify({ type: "SPAWN_HAZARD" }));
    }
  });

  // 6. Tab Navigation
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const tabName = btn.getAttribute("data-tab");
      showTabContent(tabName);
    });
  });

  // 7. Manual Teleop Keys (WASD)
  window.addEventListener("keydown", (e) => {
    if (document.activeElement === directiveInput) return;
    let vx = 0, vy = 0, omega = 0;
    if (e.key === "w" || e.key === "ArrowUp") vy = 1.0;
    if (e.key === "s" || e.key === "ArrowDown") vy = -1.0;
    if (e.key === "a" || e.key === "ArrowLeft") omega = 0.5;
    if (e.key === "d" || e.key === "ArrowRight") omega = -0.5;

    if (vx !== 0 || vy !== 0 || omega !== 0) {
      if (ws) {
        ws.send(JSON.stringify({ type: "TELEOP_COMMAND", vx, vy, omega }));
      }
    }
  });
}

function sendDirectiveCommand(text) {
  if (!ws) return;
  appendChatMessage("user", text);
  ws.send(JSON.stringify({ type: "USER_DIRECTIVE", text: text }));
  setTimeout(() => {
    appendChatMessage("phass", `Goal registered: "${text}". Formulating reasoning and plan.`);
  }, 400);
}

function sendFeedback(text) {
  if (!ws) return;
  appendChatMessage("user", `[Feedback]: ${text}`);
  ws.send(JSON.stringify({ type: "USER_FEEDBACK", text: text }));
  setTimeout(() => {
    appendChatMessage("phass", `Feedback ingested. Learning engine updated knowledge & strategies.`);
  }, 400);
}

function appendChatMessage(sender, text) {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  const bubble = document.createElement("div");
  bubble.className = `msg-bubble ${sender}`;
  bubble.innerHTML = `<strong>${sender === 'user' ? 'OPERATOR' : 'P.H.A.S.S SPHERE'}:</strong> ${escapeHtml(text)}`;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

function showTabContent(tabName) {
  document.getElementById("tab-content-overview").style.display = tabName === "overview" ? "block" : "none";
  document.getElementById("tab-content-memory").style.display = tabName === "memory" ? "block" : "none";
  document.getElementById("tab-content-learning").style.display = tabName === "learning" ? "block" : "none";
  document.getElementById("tab-content-tools").style.display = tabName === "tools" ? "block" : "none";

  if (tabName === "memory") fetchMemoryData();
  if (tabName === "tools") fetchToolsData();
}

async function fetchMemoryData() {
  try {
    const res = await fetch("/api/memory");
    const data = await res.json();
    const container = document.getElementById("memory-list-view");
    if (!container) return;

    let html = "";
    (data.long_term_knowledge || []).forEach((k) => {
      html += `
        <div class="hud-card">
          <div style="color:var(--cyan-neon); font-size:11px; font-weight:700;">[KNOWLEDGE] ID: ${k.id}</div>
          <div style="font-size:12px; margin-top:4px;">${escapeHtml(k.content)}</div>
          <div style="font-size:10px; color:var(--text-dim); margin-top:4px;">Tags: ${k.tags.join(', ')} | Importance: ${k.importance}</div>
        </div>
      `;
    });
    container.innerHTML = html || "No memory records found.";
  } catch (e) {
    console.error("Error fetching memory:", e);
  }
}

async function fetchToolsData() {
  try {
    const res = await fetch("/api/tools");
    const data = await res.json();
    const container = document.getElementById("tools-list-view");
    if (!container) return;

    let html = "";
    (data.tools || []).forEach((t) => {
      html += `
        <div class="hud-card">
          <div style="display:flex; justify-content:space-between;">
            <span style="font-weight:700; color:var(--cyan-neon); font-family:var(--font-mono);">${t.name}</span>
            <span class="status-pill" style="font-size:10px;">${t.permission_level}</span>
          </div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">${escapeHtml(t.description)}</div>
          <div style="font-size:10px; color:var(--text-dim); margin-top:4px;">Risk Level: ${t.risk_level}</div>
        </div>
      `;
    });
    container.innerHTML = html;
  } catch (e) {
    console.error("Error fetching tools:", e);
  }
}

function handleNLUResponse(res) {
  if (!res) return;
  const nlg = res.nlg_response || "Directive processed.";
  const nlu = res.nlu || {};
  const intent = nlu.intent || "GENERAL";
  const entities = nlu.entities || [];

  let entityTags = "";
  if (entities.length > 0) {
    entityTags = `<div style="margin-top:4px; font-size:10px; color:var(--cyan-neon);">` +
      entities.map(e => `[${e.category}: ${escapeHtml(e.entity_name)}]`).join(" ") +
      `</div>`;
  }

  const container = document.getElementById("chat-messages");
  if (container) {
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble phass";
    bubble.innerHTML = `
      <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
        <strong>P.H.A.S.S SPHERE</strong>
        <span class="status-pill" style="font-size:9px; padding:1px 6px;">NLU: ${escapeHtml(intent)}</span>
      </div>
      <div>${escapeHtml(nlg)}</div>
      ${entityTags}
    `;
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
  }

  // Voice output (TTS)
  speakText(nlg);
}

function speakText(text) {
  const ttsCheckbox = document.getElementById("toggle-tts");
  if (!ttsCheckbox || !ttsCheckbox.checked) return;
  if (!('speechSynthesis' in window)) return;

  window.speechSynthesis.cancel(); // Stop any overlapping audio
  const cleanText = text.replace(/\[.*?\]/g, '').replace(/https?:\/\/\S+/g, '');
  const utterance = new SpeechSynthesisUtterance(cleanText);
  utterance.rate = 1.05;
  utterance.pitch = 0.95; // Slightly deeper robotic tone
  window.speechSynthesis.speak(utterance);
}

function setupVoiceRecognition() {
  const micBtn = document.getElementById("btn-voice-input");
  const input = document.getElementById("directive-input");
  if (!micBtn || !input) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    micBtn.style.display = "none";
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = "en-US";

  let isListening = false;

  micBtn.addEventListener("click", () => {
    if (!isListening) {
      recognition.start();
      micBtn.style.background = "rgba(244, 63, 94, 0.4)";
      micBtn.style.borderColor = "var(--rose-neon)";
      micBtn.innerText = "🔴 LISTENING";
      isListening = true;
    } else {
      recognition.stop();
      isListening = false;
    }
  });

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    input.value = transcript;
    document.getElementById("btn-send-directive").click();
  };

  recognition.onend = () => {
    isListening = false;
    micBtn.style.background = "";
    micBtn.style.borderColor = "";
    micBtn.innerText = "🎙 MIC";
  };

  recognition.onerror = (e) => {
    console.warn("Speech recognition error:", e);
    isListening = false;
    micBtn.style.background = "";
    micBtn.style.borderColor = "";
    micBtn.innerText = "🎙 MIC";
  };
}

// Attach voice recognition during setup
const origSetupEventListeners = setupEventListeners;
setupEventListeners = function() {
  origSetupEventListeners();
  setupVoiceRecognition();
};

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
