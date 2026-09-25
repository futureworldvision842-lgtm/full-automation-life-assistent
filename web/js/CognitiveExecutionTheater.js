/**
 * web/js/CognitiveExecutionTheater.js — Live Cognitive Brain, CUA Browser & Task Execution Inspector
 * ==================================================================================================
 * Authoritative Glassmorphism Execution Theater for J.A.R.V.I.S.
 *
 * Capabilities:
 * 1. Live Headless Chrome CUA Viewport streaming from /api/cua/stream (~25 FPS MJPEG) with
 *    Set-of-Marks (SoM) visual DOM grounding overlay and direct action dispatch.
 * 2. Synchronized 5-Stage Execution DAG:
 *    [01 Directives Ingest] -> [02 NLP Parse] -> [03 Multi-Agent Consensus] ->
 *    [04 Sandbox Execution] -> [05 Voice Synthesis]
 *    updating dynamically in real-time with execution timings and stage statuses.
 * 3. Real-Time Subagent Communication Bus & Background Task Watcher Log Stream
 *    polling /api/subagents/logs with sub-second timestamps and level filtering.
 * ==================================================================================================
 */

class CognitiveExecutionTheater {
  constructor(options = {}) {
    this.containerId = options.containerId || 'cognitive-execution-theater';
    this.apiBase = options.apiBase || '';
    this.cuaStreamUrl = `${this.apiBase}/api/cua/stream`;
    this.dagStateUrl = `${this.apiBase}/api/dag/state`;
    this.dagExecuteUrl = `${this.apiBase}/api/dag/execute`;
    this.subagentLogsUrl = `${this.apiBase}/api/subagents/logs`;
    this.cuaActionUrl = `${this.apiBase}/api/cua/action`;
    this.cuaInspectUrl = `${this.apiBase}/api/cua/inspect`;

    this.pollIntervalMs = options.pollIntervalMs || 800;
    this.pollTimer = null;
    this.isPolling = false;
    this.somOverlayEnabled = true;
    this.somMarks = [];
    this.activeFilter = 'ALL';
    this.autoScrollLogs = true;
    this.lastLogTimestamp = 0;
    this.cachedLogs = [];

    this.stages = [
      { id: '01_DIRECTIVES_INGEST', index: 1, name: '01 Directives Ingest', subsystem: 'Ingress Orchestrator', status: 'IDLE', duration_ms: 0, details: '' },
      { id: '02_NLP_PARSE', index: 2, name: '02 NLP Parse', subsystem: 'RomanUrduParser', status: 'IDLE', duration_ms: 0, details: '' },
      { id: '03_MULTI_AGENT_CONSENSUS', index: 3, name: '03 Multi-Agent Consensus', subsystem: 'Consensus Chamber', status: 'IDLE', duration_ms: 0, details: '' },
      { id: '04_SANDBOX_EXECUTION', index: 4, name: '04 Sandbox Execution', subsystem: 'Command Router', status: 'IDLE', duration_ms: 0, details: '' },
      { id: '05_VOICE_SYNTHESIS', index: 5, name: '05 Voice Synthesis', subsystem: 'Voice Synthesizer', status: 'IDLE', duration_ms: 0, details: '' }
    ];

    this.init();
  }

  init() {
    this.injectStyles();
    this.render();
    this.bindEvents();
    this.startPolling();
  }

  injectStyles() {
    if (document.getElementById('cognitive-execution-theater-styles')) return;

    const style = document.createElement('style');
    style.id = 'cognitive-execution-theater-styles';
    style.textContent = `
      .cet-container {
        font-family: 'Rajdhani', -apple-system, BlinkMacSystemFont, sans-serif;
        background: rgba(5, 12, 24, 0.92);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid #142f4c;
        border-radius: 12px;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.8), inset 0 0 24px rgba(0, 229, 255, 0.04);
        color: #e2e8f0;
        padding: 18px;
        margin: 14px 0;
        position: relative;
        overflow: hidden;
      }
      .cet-container::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent, #00e5ff, #f59e0b, transparent);
      }
      .cet-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
        padding-bottom: 12px;
        border-bottom: 1px solid rgba(20, 47, 76, 0.7);
        margin-bottom: 16px;
      }
      .cet-title {
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #00e5ff;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .cet-badge {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.72rem;
        padding: 2px 8px;
        border-radius: 4px;
        background: rgba(0, 229, 255, 0.12);
        border: 1px solid rgba(0, 229, 255, 0.35);
        color: #00e5ff;
        letter-spacing: 0.06em;
      }
      .cet-badge-live {
        background: rgba(16, 185, 129, 0.15);
        border-color: rgba(16, 185, 129, 0.45);
        color: #10b981;
      }
      .cet-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
      }
      @media (max-width: 980px) {
        .cet-grid { grid-template-columns: 1fr; }
      }
      .cet-panel {
        background: rgba(8, 18, 34, 0.85);
        border: 1px solid #143252;
        border-radius: 8px;
        padding: 14px;
        position: relative;
      }
      .cet-panel-title {
        font-size: 0.9rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #94a3b8;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      /* CUA Browser Viewport */
      .cet-viewport-box {
        position: relative;
        background: #020610;
        border: 1px solid #1a3c60;
        border-radius: 6px;
        overflow: hidden;
        min-height: 260px;
        max-height: 380px;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .cet-viewport-img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        display: block;
      }
      .cet-viewport-overlay {
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        pointer-events: none;
      }
      .cet-som-badge {
        position: absolute;
        background: rgba(245, 158, 11, 0.9);
        color: #000;
        font-size: 10px;
        font-weight: 800;
        font-family: 'Share Tech Mono', monospace;
        padding: 1px 4px;
        border-radius: 2px;
        border: 1px solid #fff;
        pointer-events: auto;
        cursor: pointer;
        transform: translate(-50%, -50%);
        box-shadow: 0 0 6px rgba(245, 158, 11, 0.8);
      }
      .cet-viewport-controls {
        display: flex;
        gap: 8px;
        margin-top: 10px;
        flex-wrap: wrap;
      }
      .cet-input {
        flex: 1;
        min-width: 160px;
        background: rgba(3, 8, 18, 0.8);
        border: 1px solid #1a3c60;
        border-radius: 4px;
        padding: 6px 10px;
        color: #f1f5f9;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.82rem;
      }
      .cet-input:focus {
        outline: none;
        border-color: #00e5ff;
        box-shadow: 0 0 8px rgba(0, 229, 255, 0.3);
      }
      .cet-btn {
        background: linear-gradient(180deg, #0b253e 0%, #06182c 100%);
        border: 1px solid #1e4a77;
        color: #00e5ff;
        padding: 6px 12px;
        border-radius: 4px;
        font-family: 'Rajdhani', sans-serif;
        font-weight: 700;
        font-size: 0.82rem;
        letter-spacing: 0.05em;
        cursor: pointer;
        transition: all 0.2s ease;
      }
      .cet-btn:hover {
        border-color: #00e5ff;
        box-shadow: 0 0 10px rgba(0, 229, 255, 0.35);
        color: #fff;
      }
      /* 5-Stage Execution DAG */
      .cet-dag-pipeline {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-top: 8px;
      }
      .cet-dag-stage {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(3, 8, 18, 0.7);
        border: 1px solid #142e4a;
        border-radius: 6px;
        padding: 8px 12px;
        transition: all 0.25s ease;
        position: relative;
        overflow: hidden;
      }
      .cet-dag-stage.status-COMPLETED {
        border-color: rgba(0, 229, 255, 0.5);
        background: rgba(0, 229, 255, 0.06);
      }
      .cet-dag-stage.status-IN_PROGRESS {
        border-color: #f59e0b;
        background: rgba(245, 158, 11, 0.1);
        box-shadow: 0 0 12px rgba(245, 158, 11, 0.25);
      }
      .cet-dag-stage.status-FAILED {
        border-color: #ef4444;
        background: rgba(239, 68, 68, 0.1);
      }
      .cet-dag-stage-left {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .cet-dag-stage-num {
        font-family: 'Share Tech Mono', monospace;
        font-weight: 700;
        font-size: 0.85rem;
        color: #00e5ff;
        background: rgba(0, 229, 255, 0.15);
        padding: 2px 6px;
        border-radius: 3px;
      }
      .cet-dag-stage-name {
        font-weight: 700;
        font-size: 0.9rem;
        color: #e2e8f0;
      }
      .cet-dag-stage-sub {
        font-size: 0.74rem;
        color: #7e9bb5;
        font-family: 'Share Tech Mono', monospace;
      }
      .cet-dag-stage-right {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .cet-stage-pill {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.7rem;
        padding: 2px 6px;
        border-radius: 3px;
        font-weight: 700;
      }
      .pill-IDLE { background: #1e293b; color: #64748b; }
      .pill-PENDING { background: #1e293b; color: #94a3b8; }
      .pill-IN_PROGRESS { background: rgba(245, 158, 11, 0.2); color: #f59e0b; animation: cet-pulse 1.2s infinite; }
      .pill-COMPLETED { background: rgba(16, 185, 129, 0.2); color: #10b981; }
      .pill-FAILED { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
      @keyframes cet-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
      }
      /* Subagent Communication Bus Logs */
      .cet-logs-box {
        background: #020712;
        border: 1px solid #142e4a;
        border-radius: 6px;
        padding: 8px;
        height: 200px;
        overflow-y: auto;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.75rem;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .cet-log-row {
        display: flex;
        gap: 8px;
        line-height: 1.4;
        word-break: break-all;
      }
      .cet-log-ts { color: #64748b; min-width: 75px; }
      .cet-log-agent { color: #00e5ff; font-weight: 700; min-width: 110px; }
      .cet-log-stage { color: #f59e0b; }
      .cet-log-msg { color: #cbd5e1; flex: 1; }
      .cet-log-level-INFO { color: #38bdf8; }
      .cet-log-level-WARN { color: #fbbf24; }
      .cet-log-level-ERROR { color: #f87171; }
    `;
    document.head.appendChild(style);
  }

  render() {
    let container = document.getElementById(this.containerId);
    if (!container) {
      container = document.createElement('div');
      container.id = this.containerId;
      document.body.appendChild(container);
    }

    container.className = 'cet-container';
    container.innerHTML = `
      <div class="cet-header">
        <div class="cet-title">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#00e5ff;box-shadow:0 0 8px #00e5ff;"></span>
          J.A.R.V.I.S. Cognitive Execution Theater & CUA Inspector
        </div>
        <div style="display:flex;gap:6px;align-items:center;">
          <span class="cet-badge cet-badge-live">CUA: ACTIVE (~25 FPS)</span>
          <span class="cet-badge">DAG: SYNCHRONIZED</span>
          <span class="cet-badge">BUS: REAL-TIME</span>
        </div>
      </div>

      <div class="cet-grid">
        <!-- Panel 1: Live CUA Browser Viewport -->
        <div class="cet-panel">
          <div class="cet-panel-title">
            <span>LIVE HEADLESS CHROME CUA VIEWPORT (SET-OF-MARKS)</span>
            <button class="cet-btn" id="cet-toggle-som" style="padding:2px 8px;font-size:0.7rem;">SoM: ON</button>
          </div>
          <div class="cet-viewport-box" id="cet-viewport-box">
            <img class="cet-viewport-img" id="cet-stream-img" src="${this.cuaStreamUrl}" alt="Live CUA Viewport Stream" />
            <div class="cet-viewport-overlay" id="cet-viewport-overlay"></div>
          </div>
          <div class="cet-viewport-controls">
            <input type="text" class="cet-input" id="cet-url-input" placeholder="Enter target URL (e.g. https://dexscreener.com)" />
            <button class="cet-btn" id="cet-nav-btn">NAVIGATE</button>
            <button class="cet-btn" id="cet-inspect-btn">INSPECT DOM</button>
          </div>
        </div>

        <!-- Panel 2: 5-Stage Execution DAG & Dispatch -->
        <div class="cet-panel">
          <div class="cet-panel-title">
            <span>SYNCHRONIZED 5-STAGE EXECUTION DAG</span>
            <span class="cet-badge" id="cet-dag-status-badge">STATUS: IDLE</span>
          </div>
          
          <div style="display:flex;gap:8px;margin-bottom:10px;">
            <input type="text" class="cet-input" id="cet-directive-input" placeholder="Inject directive (e.g. 'lock workstation', 'status batao')" />
            <button class="cet-btn" id="cet-exec-btn">DISPATCH DIRECTIVE</button>
          </div>

          <div class="cet-dag-pipeline" id="cet-dag-pipeline">
            ${this.renderStagesHtml()}
          </div>
        </div>
      </div>

      <!-- Bottom Panel: Subagent Communication Bus Logs -->
      <div class="cet-panel" style="margin-top:14px;">
        <div class="cet-panel-title">
          <span>REAL-TIME SUBAGENT COMMUNICATION BUS & TASK WATCHER LOGS</span>
          <div style="display:flex;gap:6px;">
            <button class="cet-btn" id="cet-clear-logs" style="padding:2px 8px;font-size:0.7rem;">CLEAR</button>
            <button class="cet-btn" id="cet-autoscroll" style="padding:2px 8px;font-size:0.7rem;">AUTOSCROLL: ON</button>
          </div>
        </div>
        <div class="cet-logs-box" id="cet-logs-box">
          <div class="cet-log-row">
            <span class="cet-log-ts">[00:00:00.000]</span>
            <span class="cet-log-agent">[SystemWatchdog]</span>
            <span class="cet-log-stage">[INIT]</span>
            <span class="cet-log-msg">Subagent Communication Bus and Execution DAG initialized. Ready for sovereign directives.</span>
          </div>
        </div>
      </div>
    `;
  }

  renderStagesHtml() {
    return this.stages.map(st => `
      <div class="cet-dag-stage status-${st.status}" id="cet-stage-${st.id}">
        <div class="cet-dag-stage-left">
          <span class="cet-dag-stage-num">${st.index < 10 ? '0' + st.index : st.index}</span>
          <div>
            <div class="cet-dag-stage-name">${st.name}</div>
            <div class="cet-dag-stage-sub">${st.subsystem} ${st.details ? '— ' + st.details : ''}</div>
          </div>
        </div>
        <div class="cet-dag-stage-right">
          ${st.duration_ms > 0 ? `<span style="font-family:'Share Tech Mono';font-size:0.75rem;color:#94a3b8;">${st.duration_ms}ms</span>` : ''}
          <span class="cet-stage-pill pill-${st.status}">${st.status}</span>
        </div>
      </div>
    `).join('');
  }

  bindEvents() {
    // Dispatch Directive
    const execBtn = document.getElementById('cet-exec-btn');
    const dirInput = document.getElementById('cet-directive-input');
    if (execBtn && dirInput) {
      execBtn.addEventListener('click', () => {
        const text = dirInput.value.trim();
        if (text) {
          this.executeDirective(text);
          dirInput.value = '';
        }
      });
      dirInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          const text = dirInput.value.trim();
          if (text) {
            this.executeDirective(text);
            dirInput.value = '';
          }
        }
      });
    }

    // Navigate CUA
    const navBtn = document.getElementById('cet-nav-btn');
    const urlInput = document.getElementById('cet-url-input');
    if (navBtn && urlInput) {
      navBtn.addEventListener('click', () => {
        const url = urlInput.value.trim();
        if (url) {
          this.dispatchCuaAction('navigate', { text: url });
        }
      });
    }

    // Inspect DOM / SoM
    const inspectBtn = document.getElementById('cet-inspect-btn');
    if (inspectBtn) {
      inspectBtn.addEventListener('click', () => {
        this.inspectCuaViewport();
      });
    }

    // Toggle SoM
    const somToggle = document.getElementById('cet-toggle-som');
    if (somToggle) {
      somToggle.addEventListener('click', () => {
        this.somOverlayEnabled = !this.somOverlayEnabled;
        somToggle.textContent = `SoM: ${this.somOverlayEnabled ? 'ON' : 'OFF'}`;
        const overlay = document.getElementById('cet-viewport-overlay');
        if (overlay) overlay.style.display = this.somOverlayEnabled ? 'block' : 'none';
      });
    }

    // Log Controls
    const clearBtn = document.getElementById('cet-clear-logs');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        const box = document.getElementById('cet-logs-box');
        if (box) box.innerHTML = '';
      });
    }

    const scrollBtn = document.getElementById('cet-autoscroll');
    if (scrollBtn) {
      scrollBtn.addEventListener('click', () => {
        this.autoScrollLogs = !this.autoScrollLogs;
        scrollBtn.textContent = `AUTOSCROLL: ${this.autoScrollLogs ? 'ON' : 'OFF'}`;
      });
    }

    // Handle stream reconnect on error
    const streamImg = document.getElementById('cet-stream-img');
    if (streamImg) {
      streamImg.addEventListener('error', () => {
        setTimeout(() => {
          streamImg.src = `${this.cuaStreamUrl}?ts=${Date.now()}`;
        }, 2000);
      });
    }
  }

  startPolling() {
    if (this.isPolling) return;
    this.isPolling = true;
    this.pollTimer = setInterval(() => {
      this.pollDagState();
      this.pollSubagentLogs();
    }, this.pollIntervalMs);
  }

  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    this.isPolling = false;
  }

  async pollDagState() {
    try {
      const res = await fetch(this.dagStateUrl, { cache: 'no-store' });
      if (!res.ok) return;
      const data = await res.json();
      if (!data || !data.ok) return;

      this.updateDagView(data);
    } catch (err) {
      // Quiet fail during transient restarts
    }
  }

  async pollSubagentLogs() {
    try {
      const url = `${this.subagentLogsUrl}?since_ts=${this.lastLogTimestamp}&limit=30`;
      const res = await fetch(url, { cache: 'no-store' });
      if (!res.ok) return;
      const data = await res.json();
      if (!data || !data.ok || !data.logs || !data.logs.length) return;

      const newLogs = data.logs.filter(l => l.timestamp > this.lastLogTimestamp);
      if (newLogs.length > 0) {
        this.lastLogTimestamp = newLogs[newLogs.length - 1].timestamp;
        this.appendSubagentLogs(newLogs);
      }
    } catch (err) {
      // Quiet fail
    }
  }

  updateDagView(data) {
    const statusBadge = document.getElementById('cet-dag-status-badge');
    if (statusBadge) {
      statusBadge.textContent = `STATUS: ${data.status || 'IDLE'}`;
      statusBadge.className = `cet-badge ${data.status === 'IN_PROGRESS' ? 'cet-badge-live' : ''}`;
    }

    if (data.stages && Array.isArray(data.stages)) {
      this.stages = data.stages;
      const pipelineEl = document.getElementById('cet-dag-pipeline');
      if (pipelineEl) {
        pipelineEl.innerHTML = this.renderStagesHtml();
      }
    }
  }

  appendSubagentLogs(logs) {
    const box = document.getElementById('cet-logs-box');
    if (!box) return;

    logs.forEach(log => {
      const row = document.createElement('div');
      row.className = 'cet-log-row';

      const d = new Date(log.timestamp * 1000);
      const timeStr = d.toTimeString().split(' ')[0] + '.' + String(d.getMilliseconds()).padStart(3, '0');

      row.innerHTML = `
        <span class="cet-log-ts">[${timeStr}]</span>
        <span class="cet-log-agent">[${this.escapeHtml(log.subagent_id)}]</span>
        <span class="cet-log-stage">[${this.escapeHtml(log.stage)}]</span>
        <span class="cet-log-msg cet-log-level-${log.level}">${this.escapeHtml(log.message)}</span>
      `;
      box.appendChild(row);
    });

    if (this.autoScrollLogs) {
      box.scrollTop = box.scrollHeight;
    }
  }

  async executeDirective(directive) {
    try {
      this.appendSubagentLogs([{
        timestamp: Date.now() / 1000,
        subagent_id: 'OperatorIngress',
        stage: '01_DIRECTIVES_INGEST',
        level: 'INFO',
        message: `Dispatching directive: "${directive}"`
      }]);

      const res = await fetch(this.dagExecuteUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ directive, channel: 'dashboard' })
      });
      const data = await res.json();
      if (data && data.ok) {
        this.updateDagView(data);
      }
    } catch (err) {
      this.appendSubagentLogs([{
        timestamp: Date.now() / 1000,
        subagent_id: 'DispatchError',
        stage: '01_DIRECTIVES_INGEST',
        level: 'ERROR',
        message: `Failed to dispatch directive: ${err.message}`
      }]);
    }
  }

  async dispatchCuaAction(actionType, params = {}) {
    try {
      const payload = { action_type: actionType, ...params };
      const res = await fetch(this.cuaActionUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      this.appendSubagentLogs([{
        timestamp: Date.now() / 1000,
        subagent_id: 'CUAEngine',
        stage: '04_SANDBOX_EXECUTION',
        level: data.success ? 'INFO' : 'WARN',
        message: `Action [${actionType}] dispatched: ${data.message || JSON.stringify(data)}`
      }]);
    } catch (err) {
      console.warn('CUA Action error:', err);
    }
  }

  async inspectCuaViewport() {
    try {
      const res = await fetch(this.cuaInspectUrl, { method: 'POST' });
      const data = await res.json();
      if (data && data.elements) {
        this.renderSetOfMarks(data.elements);
      }
    } catch (err) {
      console.warn('CUA Inspect error:', err);
    }
  }

  renderSetOfMarks(elements) {
    const overlay = document.getElementById('cet-viewport-overlay');
    if (!overlay) return;
    overlay.innerHTML = '';

    elements.forEach(el => {
      if (!el.coordinates) return;
      const [x, y] = el.coordinates;
      const badge = document.createElement('div');
      badge.className = 'cet-som-badge';
      badge.style.left = `${x}px`;
      badge.style.top = `${y}px`;
      badge.textContent = el.id || '#';
      badge.title = `${el.tag}: ${el.text || ''}`;
      badge.addEventListener('click', (e) => {
        e.stopPropagation();
        this.dispatchCuaAction('click', { element_id: el.id, coordinates: [x, y] });
      });
      overlay.appendChild(badge);
    });
  }

  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

// Universal module export (ES module + global script support)
if (typeof window !== 'undefined') {
  window.CognitiveExecutionTheater = CognitiveExecutionTheater;
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { CognitiveExecutionTheater };
}
