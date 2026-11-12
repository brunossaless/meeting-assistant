const state = { activeMeetingId: null, selectedMeetingId: null };

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || res.statusText);
  }
  return res.json();
}

function fmtDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("pt-BR");
}

function statusLabel(status) {
  const labels = {
    recording: "Gravando",
    transcribing: "Transcrevendo",
    analyzing: "Analisando",
    done: "Concluída",
    error: "Erro",
  };
  return labels[status] || status;
}

function setRecordingUI(isRecording) {
  document.getElementById("btn-start").disabled = isRecording;
  document.getElementById("btn-stop").disabled = !isRecording;
  const indicator = document.getElementById("status-indicator");
  indicator.textContent = isRecording ? "Gravando" : "Ocioso";
  indicator.className = isRecording ? "status-recording" : "status-idle";
}

async function refreshList() {
  const meetings = await api("/api/meetings");

  const recording = meetings.find((m) => m.status === "recording");
  state.activeMeetingId = recording ? recording.id : null;
  setRecordingUI(Boolean(recording));

  const list = document.getElementById("meeting-list");
  list.innerHTML = "";
  for (const m of meetings) {
    const item = document.createElement("div");
    item.className = "meeting-item" + (m.id === state.selectedMeetingId ? " selected" : "");
    item.innerHTML = `
      <div class="meeting-item-date">${fmtDate(m.started_at)}</div>
      <div class="meeting-item-summary">${m.summary ? m.summary.slice(0, 90) : statusLabel(m.status)}</div>
      ${m.project ? `<span class="badge">${m.project}</span>` : ""}
    `;
    item.addEventListener("click", () => selectMeeting(m.id));
    list.appendChild(item);
  }
}

async function selectMeeting(id) {
  state.selectedMeetingId = id;
  await refreshList();
  const m = await api(`/api/meetings/${id}`);
  renderDetail(m);
}

function renderDetail(m) {
  const detail = document.getElementById("meeting-detail");
  const transcriptHtml = (m.transcript || [])
    .map((s) => `<p><strong>${s.speaker}:</strong> ${s.text}</p>`)
    .join("");

  detail.innerHTML = `
    <h2>${fmtDate(m.started_at)}</h2>
    <p class="status-tag">${statusLabel(m.status)}</p>
    ${m.project ? `<p><strong>Projeto:</strong> ${m.project}</p>` : ""}
    ${m.modules && m.modules.length ? `<p><strong>Módulos:</strong> ${m.modules.join(", ")}</p>` : ""}
    ${m.summary ? `<h3>Resumo</h3><p>${m.summary}</p>` : ""}
    ${m.topics && m.topics.length ? `<h3>Tópicos</h3><ul>${m.topics.map((t) => `<li>${t}</li>`).join("")}</ul>` : ""}
    ${
      m.participants_mentioned && m.participants_mentioned.length
        ? `<h3>Pessoas citadas</h3><ul>${m.participants_mentioned.map((p) => `<li>${p}</li>`).join("")}</ul>`
        : ""
    }
    ${
      m.action_items && m.action_items.length
        ? `<h3>Ações combinadas</h3><ul>${m.action_items.map((a) => `<li>${a}</li>`).join("")}</ul>`
        : ""
    }
    ${m.error_message ? `<p class="error">${m.error_message}</p>` : ""}
    <h3>Transcrição</h3>
    <div class="transcript">${transcriptHtml || "<p>Ainda não disponível.</p>"}</div>
    ${m.closing_summary ? `<h3>Resumo final</h3><p>${m.closing_summary}</p>` : ""}
  `;
}

async function startMeeting() {
  const res = await api("/api/meetings/start", { method: "POST" });
  state.activeMeetingId = res.id;
  setRecordingUI(true);
  await refreshList();
}

async function stopMeeting() {
  if (!state.activeMeetingId) return;
  await api(`/api/meetings/${state.activeMeetingId}/stop`, { method: "POST" });
  setRecordingUI(false);
  await refreshList();
}

document.getElementById("btn-start").addEventListener("click", () => startMeeting().catch((e) => alert(e.message)));
document.getElementById("btn-stop").addEventListener("click", () => stopMeeting().catch((e) => alert(e.message)));

refreshList();
setInterval(() => {
  refreshList();
  if (state.selectedMeetingId) {
    api(`/api/meetings/${state.selectedMeetingId}`).then(renderDetail).catch(() => {});
  }
}, 4000);
