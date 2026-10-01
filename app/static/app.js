const state = { context: null };
const byId = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function renderTrust(payload) {
  const section = document.querySelector(".trust-band");
  const trusted = payload.trustStatus.trusted;
  section.classList.add(trusted ? "trusted" : "failed");
  byId("trust-title").textContent = trusted ? "Verified analytics ready" : "Trusted finance validation failed";
  byId("trust-details").innerHTML = [
    `Data quality: ${payload.trustStatus.dataQuality.passed ? "PASS" : "FAIL"}`,
    `Reconciliation: ${payload.trustStatus.reconciliation.passed ? "PASS" : "FAIL"}`,
    `AI provider: ${payload.aiConfigured ? "CONFIGURED" : "NOT CONFIGURED"}`,
  ].map((item) => `<span class="status-label">${escapeHtml(item)}</span>`).join("");
  byId("generate").disabled = !trusted;
}

function renderKpis(items) {
  byId("kpis").innerHTML = items.slice(0, 10).map((item) => {
    const magnitude = item.unit === "percentage" ? Math.min(Math.abs(item.value) * 100, 100) : item.unit === "ratio" ? Math.min(Math.abs(item.value) * 80, 100) : 68;
    return `<article class="kpi-card"><div class="metric">${escapeHtml(item.metric)}</div><div class="value">${escapeHtml(item.display_value)}</div><div class="metric-bar" aria-hidden="true"><span style="width:${magnitude}%"></span></div></article>`;
  }).join("");
}

function formatIssueValue(issue) {
  const evidence = state.context.developerView.evidence.find((item) => item.evidence_id === issue.evidence_ids[0]);
  return evidence ? evidence.display_value : "Verified";
}

function renderIssues(items) {
  byId("issue-count").textContent = `${items.length} selected issues`;
  byId("issues").innerHTML = items.map((issue) => `<tr>
    <td class="priority-${issue.minimum_priority}">${escapeHtml(issue.minimum_priority.toUpperCase())}</td>
    <td><strong>${escapeHtml(issue.issue_type)}</strong><br><span class="section-meta">${escapeHtml(issue.issue_id)}</span></td>
    <td>${escapeHtml(issue.entity_name)}</td><td class="metric-number">${escapeHtml(formatIssueValue(issue))}</td>
    <td><div class="score-track" title="Priority score ${issue.priority_score}"><span style="width:${Math.min(issue.priority_score, 100)}%"></span></div></td>
  </tr>`).join("");
}

function renderList(id, items) { byId(id).innerHTML = items.map((item) => `<li>${escapeHtml(item)}</li>`).join(""); }

function renderAi(payload) {
  const ai = payload.aiInsights;
  byId("ai-empty").hidden = true;
  byId("ai-error").hidden = true;
  byId("ai-output").hidden = false;
  byId("ai-status").textContent = "Validated";
  byId("executive-summary").textContent = ai.executive_summary;
  byId("top-insights").innerHTML = ai.top_insights.map((insight) => `<article class="insight">
    <div class="insight-head"><h3>${escapeHtml(insight.title)}</h3><span class="priority-${insight.priority}">${escapeHtml(insight.priority.toUpperCase())}</span></div>
    <p>${escapeHtml(insight.summary)}</p>
    <div class="evidence-list">${insight.evidence.map((item) => `<div class="evidence-item"><span>${escapeHtml(item.metric)}</span><strong>${escapeHtml(item.display_value)}</strong></div>`).join("")}</div>
    <p><strong>Business implication:</strong> ${escapeHtml(insight.business_implication)}</p><p><strong>Recommended follow-up:</strong></p>
    <ul>${insight.recommended_follow_up.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></article>`).join("");
  renderList("questions", ai.unresolved_questions);
  renderList("actions", ai.recommended_actions);
}

async function loadContext() {
  const response = await fetch("/api/context", { headers: { Accept: "application/json" } });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error?.message || "Context unavailable");
  state.context = payload;
  byId("period").textContent = `Through ${payload.period}`;
  renderTrust(payload);
  renderKpis(payload.executiveKpis);
  renderIssues(payload.priorityIssues);
  byId("developer").textContent = JSON.stringify(payload.developerView, null, 2);
}

async function generateInsights() {
  const button = byId("generate");
  const error = byId("ai-error");
  button.disabled = true;
  button.textContent = "Generating...";
  byId("ai-status").textContent = "Validating response";
  error.hidden = true;
  try {
    const response = await fetch("/api/insights", { method: "POST", headers: { Accept: "application/json" } });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error?.message || "Generation failed");
    renderAi(payload);
  } catch (failure) {
    error.textContent = failure.message;
    error.hidden = false;
    byId("ai-status").textContent = "Unavailable";
  } finally {
    button.disabled = !state.context?.trustStatus.trusted;
    button.textContent = "Generate AI Executive Insights";
  }
}

byId("generate").addEventListener("click", generateInsights);
loadContext().catch((failure) => {
  byId("trust-title").textContent = failure.message;
  document.querySelector(".trust-band").classList.add("failed");
  byId("generate").disabled = true;
});
