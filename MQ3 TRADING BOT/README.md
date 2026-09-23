# MQ3 Trading Research and Guarded Broker-Telemetry Platform

A bilingual trading-research, risk-governance, paper-execution, broker-demo telemetry, dashboard, and WhatsApp automation platform. It contains SMC-style heuristics, multi-timeframe analysis, public-feed adapters, fleet risk controls, MT5 integration, memory, and research tooling. The one-click launcher on this workstation uses the validated `FundingPips-Trial` account for **read-only broker-demo telemetry**; new orders, position mutation, real-money execution, unattended broadcasts, screen capture, and mouse/keyboard control remain disabled. This platform is not a promise of profit, capital preservation, institutional attribution, challenge passage, or unattended live readiness.

Read [AUDIT_AND_MISSION.md](AUDIT_AND_MISSION.md) and [FUNDING_PIPS_COMPLIANCE_AND_GO_LIVE.md](FUNDING_PIPS_COMPLIANCE_AND_GO_LIVE.md) before buying an evaluation or enabling external integrations. They explain what is real, simulated, unavailable, and still awaiting supervised acceptance testing.

---

## 🌟 Key Features

1. **Configurable Prop-Account Risk Governor (No Guarantee)**:
   - **Daily and total loss guards:** Local conservative defaults are configurable. The exact rule must be checked against the current terms for the specific prop-firm product before use.
   - **Dynamic Lot Sizing:** The Funding Pips internal cap is **0.25% per trade**. On a nominal $25K account this is at most $62.50 before correlation/open-risk constraints. Lot size is calculated from the broker symbol specification and stop distance; a minimum lot that exceeds budget must be rejected.
   - **Mandatory Stop-Loss (SL):** Every order is placed with a hard SL and minimum 1:2.0 Risk-to-Reward ratio (TP).
   - **Forbidden Strategy Filtering:** Strictly NO Martingale, NO Grid without SL, NO Arbitrage/HFT.

2. **Smart Money Concepts (SMC / ICT) Strategy Engine**:
   - **Fair Value Gaps (FVG):** Detects 3-candle imbalance gaps for institutional entry liquidity.
   - **Order Blocks (OB):** Identifies bullish and bearish order blocks on lower timeframes.
   - **Trend Alignment:** H1 EMA 50/200 trend filter + M15 execution.
   - **Trailing Stop capability:** Can propose or apply a breakeven shift after 1:1 R:R, but automatic broker-position mutation is disabled in the current broker-demo telemetry configuration.

3. **Macroeconomic News Guard Interface**:
   - Can pause entries around configured high-impact events when an approved, current calendar feed is available.
   - An unavailable feed must be treated as degraded; it is not silently replaced with invented events.

4. **Modern Glassmorphism Web Dashboard**:
   - Interactive UI running on `http://localhost:5000`.
   - MT5 account statistics only when broker telemetry is verified; simulation values are explicitly hidden from the broker-balance cards.
   - Funding Pips drawdown visual progress gauges.
   - Live Equity Curve Chart (Chart.js).
   - Active Trades table & Terminal System Logs.
   - **Emergency Kill Switch** control. Broker-side closure must be confirmed from the returned execution receipt and reconciled positions.

---

## 📁 Repository Structure

```
MQ3 TRADING BOT/
├── config.json               # Central configuration & prop firm rule parameters
├── run.py                    # Master launcher script for Bot & Web Dashboard
├── test_system.py            # Component unit and integration test suite
├── src/                      # Source modules
│   ├── __init__.py
│   ├── mt5_connector.py      # MetaTrader 5 API interface & order execution
│   ├── risk_manager.py       # Funding Pips 25k rule shield & dynamic lot sizer
│   ├── news_filter.py        # Global economic news guard
│   ├── market_analyzer.py    # Technical & SMC (FVG/OB/Trend/RSI/ATR) engine
│   ├── strategy.py           # Signal generator with mandatory 1:2 R:R
│   ├── bot_engine.py         # Main continuous execution & trailing stop loop
│   └── backtester.py         # Historical backtest engine
└── dashboard/                # Web Dashboard Application
    ├── app.py                # Flask REST server
    ├── templates/
    │   └── index.html        # Glassmorphism HTML dashboard
    └── static/
        ├── style.css         # Dark-mode styling tokens
        └── script.js         # REST polling, Chart.js, kill switch logic
```

---

## 🚀 Quick Start Guide

### One-click Windows start/stop

The managed launcher starts three local services together in **BROKER_DEMO telemetry-only** mode on this workstation:

- WhatsApp bridge on `127.0.0.1:3001` with a memory-only mutation token;
- validated FundingPips Trial telemetry plus dashboard on `127.0.0.1:5000`, with demo order entry and position mutation locked;
- Jarvis safe orchestrator with unattended WhatsApp broadcasts, remote Higgsfield inference, IBKR replication, screen capture, and mouse/keyboard control not claimed or disabled unless separately configured and verified.

Use the Desktop buttons:

- `MQ3 Bot - START.cmd` — idempotently starts the stack and opens the dashboard;
- `MQ3 Bot - STOP.cmd` — stops only the PIDs recorded by the managed launcher;
- `MQ3 Bot - STATUS.cmd` — displays process and HTTP health.

Workspace copies are [MQ3_START.cmd](MQ3_START.cmd), [MQ3_STOP.cmd](MQ3_STOP.cmd), and [MQ3_STATUS.cmd](MQ3_STATUS.cmd). Runtime PIDs and timestamped log paths are recorded in the ignored `runtime/mq3_stack_state.json` file. The controller accepts only paper or locked broker-demo telemetry, removes demo/live confirmation variables, and refuses startup if real-money execution, demo-order execution, or unattended broadcasts are enabled, required ports are owned by another process, or another unmanaged MQ3/Jarvis process is detected.

### 1. Prerequisites
- **Python 3.10+** installed.
- **MetaTrader 5 (MT5)** desktop terminal installed on Windows.
- Log into your Funding Pips Demo / Evaluation / Master account in MT5.
- Enable Algo Trading in MT5: Go to `Tools -> Options -> Expert Advisors -> Allow Algo Trading`.

### 2. Run in Simulation / Dry-Run Mode (testing without live trades)
To test the bot engine, web dashboard, and strategy without touching MT5:
```bash
python run.py --sim
```
Open your browser and navigate to: `http://localhost:5000`

To launch the validated demo account as read-only live-market telemetry:

```bash
python run.py --demo
```

This does not authorize a demo or real-money order. The managed Desktop launcher is preferred because it also starts the authenticated WhatsApp bridge and Jarvis under one PID-controlled stack.

### 3. Live MT5 remains locked by default

`python run.py --live` is now refused: `run.py` is the paper dashboard launcher, not a funded-account bypass. New live orders require the centralized executor plus per-account readiness, exact broker/account validation, fresh broker quotes, verified news clearance, risk and signal-quality gates, an explicit approval receipt, and a time-bounded live arm. Direct live WhatsApp entry remains locked because chat text is not an execution admission receipt.

Do not enable live mode until paper, shadow, broker-preflight, reconciliation, kill-switch, and prop-rule acceptance tests pass under supervision.

---

## ⚙️ Configuration Customization (`config.json`)

You can customize risk limits and symbols in `config.json`:

```json
{
  "account_info": {
    "target_account_size": 25000.0,
    "currency": "USD"
  },
  "risk_management": {
    "max_daily_loss_pct": 1.5,
    "max_total_loss_pct": 4.0,
    "risk_per_trade_pct": 0.25,
    "max_open_trades": 3,
    "min_rr_ratio": 2.0
  },
  "symbols": [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "XAUUSD"
  ]
}
```

---

## 📊 Running Historical Backtests

To evaluate strategy behavior on synthetic sample candles:
```bash
python -m src.backtester
```

---

The backtester now validates candle data, prevents overlapping positions, applies a conservative same-bar stop-first rule, estimates spread/slippage/commission costs, and exposes walk-forward folds. These controls reduce common errors but do not prove an edge. Use licensed historical data with documented timestamps and keep an untouched holdout.

---

## 🛡️ Emergency Safeguards

If market conditions become unstable or high volatility occurs:
1. Open the Web Dashboard at `http://localhost:5000`.
2. Click the glowing **🚨 KILL SWITCH** button in the top right corner.
3. Verify the broker receipt and re-query open positions. A UI message alone is not proof that every venue is flat.
