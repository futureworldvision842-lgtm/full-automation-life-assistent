let equityChart = null;
let equityDataPoints = [];
let timeLabels = [];

document.addEventListener("DOMContentLoaded", () => {
  initChart();
  fetchStatus();
  setInterval(fetchStatus, 3000);
});

async function saveWhatsAppCredentials() {
  const phone = document.getElementById("wa-phone-input").value;
  const key = document.getElementById("wa-key-input").value;

  if (!phone) {
    alert("Please enter your phone number");
    return;
  }

  const res = await fetch("/api/whatsapp_save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, key })
  });
  const data = await res.json();
  if (data.success) {
    alert(`✅ WhatsApp credentials saved for ${phone}! Test alert dispatched.`);
    fetchStatus();
  } else {
    alert(`Error: ${data.error}`);
  }
}

async function fetchStatus() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) return;
    const data = await res.json();

    // 1. Bot & Server Status
    const statusDot = document.getElementById("status-dot");
    const statusTxt = document.getElementById("bot-status-text");
    const pauseBtn = document.getElementById("pause-btn");

    if (data.bot_paused) {
      statusDot.className = "status-dot yellow";
      statusTxt.innerText = "PAUSED";
      pauseBtn.innerText = "Resume Bot";
    } else if (data.bot_running) {
      statusDot.className = "status-dot green";
      statusTxt.innerText = "ACTIVE";
      pauseBtn.innerText = "Pause Bot";
    } else {
      statusDot.className = "status-dot red";
      statusTxt.innerText = "STOPPED";
    }

    document.getElementById("server-text").innerText = data.account.server || "FundingPips";

    // 2. Account Overview
    document.getElementById("val-balance").innerText = `$${data.account.balance.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById("val-equity").innerText = `$${data.account.equity.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById("val-profit").innerText = `$${data.account.profit.toFixed(2)}`;
    document.getElementById("val-margin").innerText = `$${data.account.margin_free.toLocaleString('en-US', {minimumFractionDigits: 2})}`;

    // 3. AI Learning & WhatsApp Status
    if (data.ai_summary) {
      document.getElementById("ai-status").innerText = data.ai_summary.ai_status;
      document.getElementById("ai-trades-count").innerText = data.ai_summary.total_trades_logged;
      document.getElementById("ai-win-rate").innerText = `${data.ai_summary.overall_win_rate_pct}%`;
      document.getElementById("ai-best-session").innerText = data.ai_summary.best_trading_session;
    }

    if (data.whatsapp_phone && document.getElementById("wa-phone-input")) {
      document.getElementById("wa-phone-input").value = data.whatsapp_phone;
    }
    if (data.whatsapp_key && document.getElementById("wa-key-input")) {
      document.getElementById("wa-key-input").value = data.whatsapp_key;
    }

    // 4. Funding Pips Rules Gauges
    const gauges = data.prop_firm_gauges;

    document.getElementById("daily-loss-val").innerText = `$${gauges.daily_loss_dollars.toFixed(2)} / $${gauges.daily_limit_dollars.toFixed(2)}`;
    const dailyPct = Math.min(100, (gauges.daily_loss_pct / gauges.daily_limit_pct) * 100);
    const dailyBar = document.getElementById("daily-progress-bar");
    dailyBar.style.width = `${dailyPct}%`;
    dailyBar.className = dailyPct > 80 ? "progress-bar-fill red" : (dailyPct > 50 ? "progress-bar-fill yellow" : "progress-bar-fill green");

    document.getElementById("total-loss-val").innerText = `$${gauges.total_loss_dollars.toFixed(2)} / $${gauges.total_limit_dollars.toFixed(2)}`;
    const totalPct = Math.min(100, (gauges.total_loss_pct / gauges.total_limit_pct) * 100);
    const totalBar = document.getElementById("total-progress-bar");
    totalBar.style.width = `${totalPct}%`;
    totalBar.className = totalPct > 80 ? "progress-bar-fill red" : (totalPct > 50 ? "progress-bar-fill yellow" : "progress-bar-fill green");

    // 5. Equity Chart Update
    const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    if (timeLabels.length > 20) {
      timeLabels.shift();
      equityDataPoints.shift();
    }
    timeLabels.push(nowStr);
    equityDataPoints.push(data.account.equity);
    equityChart.update();

    // 6. Positions Table
    const tbody = document.getElementById("positions-tbody");
    document.getElementById("pos-count").innerText = data.positions.length;

    if (data.positions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">No open positions. AI scanning for SMC setups...</td></tr>`;
    } else {
      tbody.innerHTML = data.positions.map(p => `
        <tr>
          <td>#${p.ticket}</td>
          <td><strong>${p.symbol}</strong></td>
          <td><span class="badge ${p.type === 'BUY' ? 'green' : 'red'}">${p.type}</span></td>
          <td>${p.volume}</td>
          <td>${p.price_open.toFixed(5)}</td>
          <td>${p.sl.toFixed(5)}</td>
          <td>${p.tp.toFixed(5)}</td>
          <td style="color: ${p.profit >= 0 ? '#10b981' : '#ef4444'}; font-weight: bold;">$${p.profit.toFixed(2)}</td>
        </tr>
      `).join("");
    }

    // 7. Terminal Logs
    const logBox = document.getElementById("terminal-logs");
    logBox.innerHTML = data.logs.map(l => `
      <div class="log-entry ${l.level.toLowerCase()}">
        [${l.timestamp}] ${l.message}
      </div>
    `).join("");
    logBox.scrollTop = logBox.scrollHeight;

  } catch (err) {
    console.error("Error fetching status:", err);
  }
}

function initChart() {
  const ctx = document.getElementById("equityChart").getContext("2d");
  equityChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: timeLabels,
      datasets: [{
        label: "Equity ($)",
        data: equityDataPoints,
        borderColor: "#00f2fe",
        backgroundColor: "rgba(0, 242, 254, 0.08)",
        fill: true,
        tension: 0.3,
        pointRadius: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8" } },
        y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8" } }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

async function togglePause() {
  const pauseBtn = document.getElementById("pause-btn");
  const isPaused = pauseBtn.innerText.includes("Resume");
  const action = isPaused ? "resume" : "pause";

  await fetch("/api/control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action })
  });
  fetchStatus();
}

async function triggerKillSwitch() {
  if (confirm("⚠️ EMERGENCY KILL SWITCH! Are you sure you want to close ALL positions and pause the bot immediately?")) {
    await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "kill_switch" })
    });
    fetchStatus();
  }
}
