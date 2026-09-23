# Project: MQ3 Trading Bot — Futuristic Command Cockpit & Autonomous Multi-Account Platform

## Architecture
The platform is an institutional-grade quantitative trading system and web command cockpit composed of:
1. **Frontend Cockpit Layer**:
   - `dashboard/templates/index.html`: Unified single-screen glassmorphic cockpit with cyber/ice-blue theme (`#0a1128`, `#0e1e38`, `#142952`, `#00d2ff`, `#38bdf8`, `#67e8f9`).
   - Responsive Fluid CSS Grid & Flexbox containers with zero horizontal overflow at 1920x1080, 1440x900, 1280x720 viewports.
   - Core Panels: Top Ticker Ribbon, Market Weather Barometer, TradingView Chart with SMC/CVD overlays & 4 AI Future Projected Ghost Candles, Trade Cards, Fleet Hub Table, Maritime Threat Radar & Chokepoints Grid, Institutional Shark Forensics.
   - `dashboard/templates/whatsapp.html`: Sovereign WhatsApp Copilot interactive command web interface.
   - `dashboard/app.py`: Flask REST API serving cockpit endpoints, live chart streams, account telemetry, and AI delegation.

2. **Risk & Multi-Account Governance Engine**:
   - `src/fleet_risk_manager.py`: Live multi-account risk management, 00:00 UTC Start-of-Day 2.5% daily drawdown shield, trailing HWM floor ratchets with profit locking, 5-stage consistency pacing, 3.5x ATR stops, dynamic lot sizing (<0.75% risk).
   - `src/funding_pips_expert.py`: Prop firm tier rule profiles ($5k, $25k, $50k, $100k, Funding Pips, FTMO) and 2-phase evaluation progression.
   - `src/multi_account_auto_onboarder.py`: Auto-onboarding for 10 account types (Funding Pips, FTMO, Binance, Bitget, Hyperliquid, MT5) via Web Cockpit & WhatsApp NLP.
   - `src/aladdin_risk_engine.py`: Parametric 99%/95% 1-Day VaR/CVaR, Fractional Kelly sizing, 3-sigma gap stress testing.
   - `src/autonomous_fleet_executor.py`: Multi-venue execution routing (MT5 Forex/Metals, Bitget Crypto Futures), 50% scale-out, BE+1 pip spread buffer, 50% FVG CE trailing.

3. **Intelligence Unification & Forensics Layer**:
   - `src/jarvis_agent_intel.py` & `repos/Muhammad-s-Jarvis/skills/hermes.py`: Autonomous trade delegation, 70.5% OTE level synthesis, subconscious cognitive reflection.
   - `src/world_monitor_intelligence_engine.py`: 5 strategic maritime chokepoints tracking, 4-pillar Country Instability Index (CII), DEFCON 1-5 classification, risk multipliers.
   - `src/whatsapp_copilot.py`, `src/whatsapp_qr_manager.py`, `src/whatsapp_voice_transcriber.py`: Whitelisted 2-way directives, 3-tier multimodal audio processing, 4-pillar trade cards, execution alerts.
   - `src/order_flow_quant.py` & `src/smc_forensics.py`: Tri-pillar explainable forensics (Who/Whale, Why/SMC/CVD/Wyckoff, Where/target pool & invalidation).

---

## Feature Inventory
Every feature from ORIGINAL_REQUEST.md and Survey Phase is cataloged below:

| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| F01 | Zero-Overflow Responsive CSS Grid | Fluid `100vw`, `box-sizing: border-box`, `min-width: 0`, zero horizontal scrollbars at 1920x1080, 1440x900, 1280x720 | M1 | R1, Survey | DONE |
| F02 | Cyber/Ice-Blue Design System | Color palette (`#0a1128`, `#0e1e38`, `#142952`, `#00d2ff`, `#38bdf8`, `#67e8f9`), crisp typography, glassmorphism | M1 | R1, Survey | DONE |
| F03 | 1-Screen Command Center Layout | Unified navigation, top ticker, TradingView charts, AI Future Forecast overlays, Market Weather, Big Shark cards, Maritime Radar | M1 | R1, Survey | DONE |
| F04 | Maritime Threat Radar Viewport Fit | Responsive chokepoint cards & CII bars without right-side clipping or horizontal overflow | M1 | R1, Survey | DONE |
| F05 | Prop Firm Start-of-Day 2.5% Drawdown Shield | Instant order lockout upon 2.5% intraday equity drawdown across $5k, $25k, $50k, $100k accounts | M2 | R2, Survey | DONE |
| F06 | Trailing HWM Floor Guard & Pacing | Trailing HWM floor clamping at starting balance, 5-stage consistency pacing | M2 | R2, Survey | DONE |
| F07 | Dynamic Lot Sizing & 3.5x ATR Stops | Risk-calibrated lot sizing (<0.75% per setup, 1:2.0 min R:R, 3.5x ATR stops for crypto) | M2 | R2, Survey | DONE |
| F08 | Crypto Micro-Balance Scaling | Perpetual scaling ($100-$10k) with Hyperliquid funding rate and Lee-Ready CVD delta confirmation | M2 | R2, Survey | DONE |
| F09 | Muhammad's Jarvis & Hermes Delegation | Autonomous trade delegation, `/api/hermes_delegate`, 70.5% OTE level synthesis, cognitive reflection | M3 | R3, Survey | DONE |
| F10 | WorldMonitor Geopolitical Radar API | Live 5 chokepoints tracking, 4-pillar CII calculation, DEFCON mapping, `/api/world_monitor` | M3 | R3, Survey | DONE |
| F11 | Live WhatsApp Sovereign Copilot | Whitelisted 2-way directives (`/api/whatsapp_command`), 3-tier voice processing (`/api/whatsapp_audio`), trade cards | M3 | R3, Survey | DONE |
| F12 | Tri-Pillar Explainable Forensics | Who (Whale), Why (SMC/CVD/FVG), Where (Target pool/invalidation), `/api/chart_data/<symbol>` | M3 | R3, Survey | DONE |
| F13 | Master Operational Test Pass | 100% pass on `verify_all_24_features.py` and `test_full_automation_scenarios.py` | M4 | AC, Survey | DONE |
| F14 | Comprehensive E2E Test Suite (Tiers 1-4) | Requirements-driven test suite with 170 test cases covering all features, boundaries, pairwise combinations, real-world workloads | M4 | Dual Track | DONE |
| F15 | Adversarial Coverage Hardening (Tier 5) | White-box stress testing, boundary fuzzing, and defect hardening | M4 | Dual Track | DONE |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | UI Redesign & Viewport Overflow Elimination | Overhaul `dashboard/templates/index.html` and related CSS/JS for zero overflow at 1920x1080, 1440x900, 1280x720, Cyber/Ice-Blue theme, glassmorphic styling, and Maritime Threat Radar fit | None | DONE |
| M2 | Risk Governance & Prop Firm Auto-Calibrator Verification | Verify & harden 2.5% SOD daily drawdown locks, dynamic lot sizing, HWM floor guards, crypto micro-balance scaling | None | DONE |
| M3 | Intelligence Unification & REST Endpoints Hardening | Verify & harden Jarvis/Hermes delegation, WorldMonitor radar, WhatsApp copilot, Explainable Forensics APIs | None | DONE |
| M4 | E2E Testing Suite & Master Acceptance Gate | Phase 1: 100% pass on E2E Test Suite (Tiers 1-4). Phase 2: Tier 5 adversarial stress testing & master suites pass | M1, M2, M3 | DONE |

---

## Interface Contracts

### Cockpit UI ↔ Backend REST APIs
- `GET /api/chart_data/<symbol>?tf=<timeframe>`: Returns `{status: "success", count: N, candles: [...], future_projected_candles: [...], smc_structures: [...]}`
- `GET /api/world_monitor`: Returns `{status: "success", defcon_level: int, chokepoints: {...}, country_instability: {...}, risk_multiplier: float}`
- `GET /api/market_weather`: Returns `{status: "success", barometer_score: float, regime: string, win_probability: float, ...}`
- `GET /api/accounts`: Returns `{status: "success", accounts: [...]}`
- `POST /api/onboard_account`: Payload `{account_id: string, broker: string, balance: number, tier: string, ...}` -> Returns `{status: "success", account: {...}}`
- `POST /api/whatsapp_command`: Payload `{from: string, body: string}` -> Returns `{reply: string}`
- `POST /api/whatsapp_audio`: Payload `{audio_base64: string, sender: string}` -> Returns `{status: "success", text: string, command_result: {...}}`
- `POST /api/hermes_delegate`: Payload `{task: string}` -> Returns `{status: "success", agent: "Hermes-Autonomous-Agent", execution_log: string}`

### Risk Manager ↔ Order Execution
- `FleetRiskManager.check_daily_loss_shield(account_id, current_equity)` -> `bool` (False if intraday loss >= 2.5% SOD equity)
- `FleetRiskManager.calculate_dynamic_lot_size(account_id, symbol, sl_distance, current_equity)` -> `float` lots (<0.75% equity risk)
- `FleetRiskManager.check_trailing_hwm_floor(account_id, current_equity)` -> `bool` (False if current equity <= locked floor)

---

## Code Layout
- `dashboard/`:
  - `app.py`: Main Flask application and REST API controllers.
  - `templates/index.html`: Main Cockpit UI template with embedded CSS styling and JavaScript client app.
  - `templates/whatsapp.html`: WhatsApp Web Copilot UI.
- `src/`:
  - `fleet_risk_manager.py`: Core multi-account risk management engine.
  - `funding_pips_expert.py`: Prop firm evaluation rules and tier definitions.
  - `multi_account_auto_onboarder.py`: Account onboarding and WhatsApp directive parsing.
  - `aladdin_risk_engine.py`: VaR/CVaR, Fractional Kelly, and stress testing.
  - `autonomous_fleet_executor.py`: Multi-broker routing and trade lifecycle manager.
  - `world_monitor_intelligence_engine.py`: Geopolitical radar, chokepoints, and CII.
  - `jarvis_agent_intel.py`: Muhammad's Jarvis integration and Hermes delegator.
  - `whatsapp_copilot.py`: Live WhatsApp sovereign copilot and whitelist manager.
  - `whatsapp_qr_manager.py`: WhatsApp 2-way command router.
  - `whatsapp_voice_transcriber.py`: 3-tier multimodal audio STT pipeline.
  - `order_flow_quant.py`: CVD, Lee-Ready trade classification, and OTE levels.
  - `smc_forensics.py`: Smart Money Concepts forensics engine.
- `tests/`:
  - `verify_all_24_features.py`: Master 24-feature operational verification script.
  - `test_full_automation_scenarios.py`: Master automation scenario verification script.
  - `test_dashboard_m3.py`: Dashboard REST and DOM integrity test suite.
  - `test_frontend_chart_smc_cvd.py`: Frontend chart and SMC/CVD calculation test suite.
  - `test_risk_calculations.py`: Aladdin VaR, CVaR, and floor ratchet unit tests.
  - `test_fleet_risk_manager.py`: Fleet risk manager integration tests.
  - `test_fleet_risk_empirical.py`: Multi-account empirical stress tests.
  - `test_smc_cvd_engine.py`: SMC and CVD calculation tests.
  - `test_whatsapp_copilot_m4.py`: WhatsApp copilot tests.
  - `test_world_monitor_suite.py`: WorldMonitor radar tests.
  - `test_higgsfield_publicapis_jarvis_integrations.py`: Public feeds & Jarvis tests.
  - `test_e2e_opaque_box.py`: Requirements-driven opaque-box E2E test suite (Tiers 1-4).
