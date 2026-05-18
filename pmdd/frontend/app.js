/* ─────────────────────────────────────────────────────────
   PMDD — app.js  |  Frontend Logic & API Integration
───────────────────────────────────────────────────────── */
'use strict';

const AGENT_META = [
  { id: 1, name: 'Corpus Preprocessor', theory: 'Sinclair (1991) — Tokenization & Segmentation', icon: '⚙️' },
  { id: 2, name: 'Pragmatic Analyzer', theory: 'Grice (1975) · Austin/Searle · Brown & Levinson', icon: '🔍' },
  { id: 3, name: 'Semantic Detector', theory: 'Lyons (1977) · Halliday (1978)', icon: '🗺️' },
  { id: 4, name: 'Corpus Statistician', theory: 'Sinclair (1991) — MI · Keyness · TTR', icon: '📊' },
  { id: 5, name: 'Orchestrator', theory: 'Fairclough (1992) — CDA Synthesis', icon: '🧠' },
];

// ── State ─────────────────────────────────────────────────
let currentRunId = null;
let mdsChart = null;
let freqChart = null;
let miChart = null;

// ── DOM Refs ──────────────────────────────────────────────
const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

// ── Init ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  renderAgentCards();
  bindEvents();
});

function bindEvents() {
  // File picker
  $('browseBtn').addEventListener('click', () => $('fileInput').click());
  $('fileInput').addEventListener('change', onFileSelected);

  // Drag & drop
  const zone = $('uploadZone');
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dragover');
    const f = e.dataTransfer.files[0];
    if (f) attachFile(f);
  });

  // Analyze
  $('analyzeBtn').addEventListener('click', runAnalysis);
  $('newAnalysisBtn').addEventListener('click', resetUI);
  $('downloadBtn').addEventListener('click', downloadReport);
  $('historyBtn').addEventListener('click', showHistory);
  $('closeHistory').addEventListener('click', () => $('historyModal').classList.add('hidden'));

  // Tabs
  $$('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      $$('.tab-btn').forEach(b => b.classList.remove('active'));
      $$('.tab-panel').forEach(p => p.classList.add('hidden'));
      btn.classList.add('active');
      $(`tab-${btn.dataset.tab}`).classList.remove('hidden');
    });
  });
}

// ── Health Check ──────────────────────────────────────────
async function checkHealth() {
  try {
    const r = await fetch('/api/health');
    const d = await r.json();
    const dot = $('apiStatus').querySelector('.status-dot');
    const txt = $('apiStatus').querySelector('.status-text');
    if (d.api_configured) {
      dot.classList.add('ok'); txt.textContent = 'Gemini Connected';
    } else {
      dot.classList.add('error'); txt.textContent = 'API key not set';
    }
  } catch { }
}

// ── File Handling ─────────────────────────────────────────
function onFileSelected(e) { if (e.target.files[0]) attachFile(e.target.files[0]); }

function attachFile(file) {
  $('fileInput')._file = file;
  $('fileName').textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  $('fileSelected').classList.remove('hidden');
  $('analyzeBtn').disabled = false;
}

// ── Render Agent Cards ─────────────────────────────────────
function renderAgentCards() {
  $('agentsGrid').innerHTML = AGENT_META.map(a => `
    <div class="agent-card idle" id="agent-card-${a.id}">
      <div class="agent-num">AGENT ${a.id.toString().padStart(2, '0')}</div>
      <div class="agent-name">${a.name}</div>
      <div class="agent-theory">${a.theory}</div>
      <div class="agent-status-icon" id="agent-icon-${a.id}">${a.icon}</div>
    </div>`).join('');
}

function setAgentState(agentId, state) {
  const card = $(`agent-card-${agentId}`);
  if (!card) return;
  card.className = `agent-card ${state}`;
  const icon = $(`agent-icon-${agentId}`);
  if (!icon) return;
  const states = { running: '⏳', done: '✅', error: '❌' };
  icon.textContent = states[state] || AGENT_META.find(a => a.id === agentId)?.icon || '●';
}

// ── Terminal Logger ───────────────────────────────────────
function log(msg, type = 'info') {
  const body = $('terminalBody');
  const line = document.createElement('div');
  line.className = `log-line ${type}`;
  const ts = new Date().toLocaleTimeString();
  line.textContent = `[${ts}] ${msg}`;
  body.appendChild(line);
  body.scrollTop = body.scrollHeight;
}

// ── Run Analysis ──────────────────────────────────────────
async function runAnalysis() {
  const fileInput = $('fileInput');
  const file = fileInput._file || fileInput.files[0];
  if (!file) return;

  resetForRun();
  $('heroSection').style.opacity = '0.3';
  $('heroSection').style.pointerEvents = 'none';
  $('analysisPanel').classList.remove('hidden');
  $('analysisPanel').scrollIntoView({ behavior: 'smooth' });

  const fd = new FormData();
  fd.append('file', file);
  fd.append('keywords', $('keywords').value);
  fd.append('corpus_name', $('corpusName').value);

  log('Starting PMDD 5-Agent Analysis pipeline...', 'info');

  const evtSrc = new EventSourcePolyfill('/api/analyze', fd);

  evtSrc.on('progress', d => {
    const { agent, status, message, data } = d;
    if (agent && agent > 0) {
      setAgentState(agent, status);
      log(message, status === 'done' ? 'success' : 'info');
    } else {
      log(message, 'info');
    }
  });

  evtSrc.on('complete', d => {
    currentRunId = d.run_id;
    log('Analysis complete! Rendering results...', 'success');
    renderResults(d);
  });

  evtSrc.on('error', d => {
    log(`Error: ${d.message}`, 'error');
  });
}

// ── SSE via fetch (polyfill for POST streaming) ───────────
function EventSourcePolyfill(url, formData) {
  const handlers = {};
  this.on = (ev, fn) => { handlers[ev] = fn; };

  fetch(url, { method: 'POST', body: formData })
    .then(async res => {
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });

        const parts = buf.split('\n\n');
        buf = parts.pop();

        for (const part of parts) {
          const lines = part.split('\n');
          let eventName = 'message', dataStr = '';
          for (const l of lines) {
            if (l.startsWith('event:')) eventName = l.slice(6).trim();
            if (l.startsWith('data:')) dataStr = l.slice(5).trim();
          }
          if (dataStr && handlers[eventName]) {
            try { handlers[eventName](JSON.parse(dataStr)); } catch { }
          }
        }
      }
    })
    .catch(e => { if (handlers['error']) handlers['error']({ message: e.message }); });

  return this;
}

// ── Render Results ────────────────────────────────────────
function renderResults(data) {
  const { report, corpus_stats, agent4_stats, agent3_data } = data;
  const scores = report.scores || {};
  const mds = Number(scores.overall_mds || 50);

  // Show results section
  $('resultsSection').classList.remove('hidden');

  // Animate MDS gauge
  animateMDS(mds, scores.drift_level || 'Moderate');

  // Sub-score bars
  animateBar('pragmaticBar', 'pragmaticScore', scores.pragmatic_drift);
  animateBar('semanticBar', 'semanticScore', scores.semantic_drift);
  animateBar('registerBar', 'registerScore', scores.register_drift);

  // Executive summary
  $('executiveSummary').textContent = report.executive_summary || '—';

  // Stats row
  renderStatsRow(corpus_stats, agent4_stats);

  // Charts
  renderFreqChart(agent4_stats?.global_top_30 || []);
  renderMIChart(agent4_stats?.collocations || {});

  // Section stats table
  renderSectionStats(agent4_stats?.section_stats || {});

  // Statistical findings
  renderStatFindings(report.corpus_statistics_summary || {});

  // Pragmatic evidence
  renderPragmaticEvidence(report.pragmatic_drift_evidence || []);

  // Register
  renderRegisterAnalysis(report.register_analysis || {});

  // CDA
  $('cdaCard').innerHTML = `<h3>Discourse Interpretation</h3><p>${report.discourse_interpretation || '—'}</p>`;

  // Semantic shifts
  renderSemanticShifts(report.semantic_field_shifts || []);
  renderSectionFields(agent3_data?.section_summaries || []);

  // Reflection log
  renderReflectionLog(report.agent_reflection_log || []);

  // Conclusions
  $('conclusionsText').textContent = report.conclusions || '—';
  const recList = $('recommendationsList');
  recList.innerHTML = (report.recommendations || []).map(r => `<li>${r}</li>`).join('');
}

// ── MDS Gauge ─────────────────────────────────────────────
function animateMDS(target, level) {
  const canvas = $('mdsGauge');
  const ctx = canvas.getContext('2d');
  const cx = 110, cy = 120, r = 90;
  const start = Math.PI * 0.75, end = Math.PI * 2.25;
  let current = 0;

  const color = target >= 75 ? '#ef4444' : target >= 50 ? '#f59e0b' : '#10b981';

  const numEl = $('mdsNumber');
  numEl.style.color = color;

  const lvlEl = $('mdsLevel');
  lvlEl.textContent = `${level} DRIFT`;
  lvlEl.className = `mds-level ${level}`;

  function draw(val) {
    ctx.clearRect(0, 0, 220, 220);
    // Track
    ctx.beginPath(); ctx.arc(cx, cy, r, start, end);
    ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth = 14;
    ctx.lineCap = 'round'; ctx.stroke();
    // Fill
    const prog = start + (end - start) * (val / 100);
    const grad = ctx.createLinearGradient(cx - r, cy, cx + r, cy);
    grad.addColorStop(0, '#3b82f6'); grad.addColorStop(1, color);
    ctx.beginPath(); ctx.arc(cx, cy, r, start, prog);
    ctx.strokeStyle = grad; ctx.lineWidth = 14; ctx.stroke();
    numEl.textContent = Math.round(val);
  }

  const dur = 1500, steps = 60;
  let step = 0;
  const timer = setInterval(() => {
    step++;
    current = target * (step / steps);
    draw(current);
    if (step >= steps) { clearInterval(timer); draw(target); }
  }, dur / steps);
}

function animateBar(barId, scoreId, value) {
  const v = Number(value || 0);
  setTimeout(() => {
    $(barId).style.width = `${v}%`;
    $(scoreId).textContent = `${v}`;
  }, 300);
}

// ── Stats Row ─────────────────────────────────────────────
function renderStatsRow(cs, a4) {
  const items = [
    { label: 'Total Segments', value: cs?.total_segments ?? '—', sub: 'Corpus units analyzed' },
    { label: 'Total Words', value: (cs?.total_words ?? 0).toLocaleString(), sub: 'Running token count' },
    { label: 'Unique Words', value: (cs?.unique_words ?? 0).toLocaleString(), sub: 'Type diversity' },
    { label: 'Type-Token Ratio', value: cs?.type_token_ratio ?? '—', sub: 'Lexical richness index' },
  ];
  $('statsRow').innerHTML = items.map(it => `
    <div class="stat-card">
      <div class="stat-label">${it.label}</div>
      <div class="stat-value">${it.value}</div>
      <div class="stat-sub">${it.sub}</div>
    </div>`).join('');
}

// ── Charts ────────────────────────────────────────────────
function renderFreqChart(words) {
  if (freqChart) freqChart.destroy();
  const top = words.slice(0, 12);
  const ctx = $('freqChart').getContext('2d');
  freqChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: top.map(w => w.word),
      datasets: [{
        data: top.map(w => w.frequency),
        backgroundColor: top.map((_, i) => `hsl(${215 + i * 8},70%,55%)`),
        borderRadius: 6, borderSkipped: false
      }]
    },
    options: {
      responsive: true, plugins: { legend: { display: false } },
      scales: { x: { ticks: { color: '#64748b', font: { size: 10 } } }, y: { ticks: { color: '#64748b', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.04)' } } }
    }
  });
}

function renderMIChart(collocations) {
  if (miChart) miChart.destroy();
  const entries = Object.entries(collocations).slice(0, 3);
  const datasets = entries.map(([word, colls], i) => ({
    label: word,
    data: colls.slice(0, 5).map(c => c.mi_score),
    backgroundColor: `hsl(${215 + i * 40},70%,55%)`,
    borderRadius: 4
  }));
  const labels = entries[0]?.[1]?.slice(0, 5).map(c => c.collocate) || [];
  const ctx = $('miChart').getContext('2d');
  miChart = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true, plugins: { legend: { labels: { color: '#94a3b8', font: { size: 10 } } } },
      scales: { x: { ticks: { color: '#64748b', font: { size: 10 } } }, y: { ticks: { color: '#64748b', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.04)' } } }
    }
  });
}

// ── Section Stats Table ───────────────────────────────────
function renderSectionStats(secStats) {
  const rows = Object.values(secStats).map((s, i) => {
    const top = (s.top_20_words || []).slice(0, 4).map(w => w.word).join(', ');
    return `<tr>
      <td>Section ${(s.section ?? i) + 1}</td>
      <td>${(s.total_words || 0).toLocaleString()}</td>
      <td>${s.unique_words || 0}</td>
      <td>${s.type_token_ratio || 0}</td>
      <td class="text-muted">${top}</td>
    </tr>`;
  }).join('');
  $('sectionStatsTable').innerHTML = `
    <table class="semantic-table" style="width:100%">
      <thead><tr><th>Section</th><th>Words</th><th>Unique</th><th>TTR</th><th>Top Keywords</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="5" class="empty-state">No section data</td></tr>'}</tbody>
    </table>`;
}

function renderStatFindings(summary) {
  const findings = summary.key_findings || [];
  const ttr = summary.ttr_interpretation || '';
  $('statFindings').innerHTML = `
    ${ttr ? `<p style="color:#94a3b8;font-size:.85rem;margin-bottom:1rem;line-height:1.7">${ttr}</p>` : ''}
    ${findings.map(f => `<div class="evidence-card"><p class="finding">• ${f}</p></div>`).join('')}
    ${!findings.length && !ttr ? '<p class="empty-state">No statistical findings generated.</p>' : ''}`;
}

// ── Pragmatic Evidence ────────────────────────────────────
function renderPragmaticEvidence(evidence) {
  $('pragmaticEvidence').innerHTML = evidence.map(ev => {
    const segs = (ev.segment_ids || []).map(s => `<span class="seg-id">[Seg #${s}]</span>`).join('');
    return `<div class="evidence-card">
      <div class="finding">${ev.finding || ''}</div>
      <div class="theory-link">📚 ${ev.theory || ''}</div>
      ${segs ? `<div class="seg-ids">${segs}</div>` : ''}
      ${ev.corpus_quote ? `<div class="corpus-quote">"${ev.corpus_quote}"</div>` : ''}
    </div>`;
  }).join('') || '<p class="empty-state">No pragmatic evidence generated.</p>';
}

function renderRegisterAnalysis(reg) {
  const events = (reg.borrowing_events || []).map(e => `<div class="evidence-card"><p class="finding">• ${e}</p></div>`).join('');
  $('registerAnalysis').innerHTML = `
    <div class="evidence-card">
      <div class="finding">Register Summary</div>
      <div class="theory-link">📚 ${reg.theory_link || 'Halliday (1978)'}</div>
      <p style="font-size:.85rem;color:#94a3b8;margin-top:.5rem;line-height:1.7">${reg.summary || 'No register summary available.'}</p>
    </div>
    ${events}`;
}

// ── Semantic Shifts ───────────────────────────────────────
function renderSemanticShifts(shifts) {
  const rows = shifts.map(s => `<tr>
    <td><strong>${s.keyword || ''}</strong></td>
    <td>${s.before || '—'}</td>
    <td>${s.after || '—'}</td>
    <td class="text-muted" style="font-size:.75rem">${s.theory_link || ''}</td>
    <td><span class="drift-badge yes">DRIFT</span></td>
  </tr>`).join('');
  $('semanticShifts').innerHTML = `
    <table class="semantic-table" style="width:100%">
      <thead><tr><th>Keyword</th><th>Period A Field</th><th>Period B Field</th><th>Theory</th><th>Status</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="5" class="empty-state">No semantic shifts detected.</td></tr>'}</tbody>
    </table>`;
}

function renderSectionFields(sections) {
  $('sectionFields').innerHTML = sections.map(s => `
    <div class="section-field-card">
      <div>
        <div style="font-weight:600;font-size:.9rem">${s.label || `Section ${s.section + 1}`}</div>
        <div style="font-size:.75rem;color:#64748b;margin-top:.2rem">Register: ${s.dominant_register || '—'} · Borrowing events: ${s.register_borrowing_count || 0}</div>
      </div>
      <span class="field-badge">${s.dominant_field || 'UNKNOWN'}</span>
    </div>`).join('') || '<p class="empty-state">No section field data available.</p>';
}

// ── Reflection Log ────────────────────────────────────────
function renderReflectionLog(log_entries) {
  $('reflectionLog').innerHTML = log_entries.map(e => `
    <div class="log-entry">
      <span class="log-agent-badge">${e.agent || 'Agent ?'}</span>
      <div class="log-event">${e.event || ''}</div>
    </div>`).join('') || '<p class="empty-state">No self-correction events recorded.</p>';
}

// ── History ───────────────────────────────────────────────
async function showHistory() {
  $('historyModal').classList.remove('hidden');
  try {
    const r = await fetch('/api/history');
    const d = await r.json();
    $('historyList').innerHTML = (d.runs || []).map(run => `
      <div class="history-item">
        <div class="run-name">${run.corpus_name || 'Unknown'}</div>
        <div class="run-meta">MDS: ${run.drift_score ?? '—'}/100 · ${run.created_at?.slice(0, 16) || ''} · Run ID: ${run.run_id}</div>
      </div>`).join('') || '<p class="empty-state">No previous runs found.</p>';
  } catch { $('historyList').innerHTML = '<p class="empty-state">Could not load history.</p>'; }
}

// ── Download ──────────────────────────────────────────────
function downloadReport() {
  if (!currentRunId) return;
  window.open(`/api/report/${currentRunId}`, '_blank');
}

// ── Reset ─────────────────────────────────────────────────
function resetUI() {
  currentRunId = null;
  $('heroSection').style.opacity = '1';
  $('heroSection').style.pointerEvents = '';
  $('analysisPanel').classList.add('hidden');
  $('resultsSection').classList.add('hidden');
  $('fileSelected').classList.add('hidden');
  $('analyzeBtn').disabled = true;
  $('fileInput')._file = null;
  $('fileInput').value = '';
  $('terminalBody').innerHTML = '';
  renderAgentCards();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function resetForRun() {
  $('resultsSection').classList.add('hidden');
  $('terminalBody').innerHTML = '';
  renderAgentCards();
}
