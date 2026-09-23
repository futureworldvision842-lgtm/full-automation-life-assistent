# Project: J.A.R.V.I.S. Sovereign Platform Consolidation & Optimization

## Architecture
The J.A.R.V.I.S. Sovereign Platform is an integrated AI ecosystem fusing:
- **Master Operations Command Center (:8770)**: Central FastAPI Web HUD (`dashboard.py`, `web/universal_command_center.html`) & REPL console (`terminal.py`, `ui/rich_terminal_dashboard.py`).
- **World Monitor Live Engine (:3000)**: Native WebGL/DeckGL/MapLibre globe with 22 geospatial intelligence sync layers & maritime chokepoints.
- **Mobile Companion & Remote Gateway (:8765)**: WebSocket bridge (`mobile_control.py`), 24/7 telemetry reporting, and Wake-on-LAN power management.
- **MQ3 Institutional Trading Cockpit (:5050)**: Multi-account prop trading cockpit and telemetry API.
- **Odysseus Neural Brain (:7000)**: Multi-agent DAG reasoning & consensus engine (`bots/odysseus/app.py`).
- **Ollama Local LLM Node (:11434)**: Local inference engine for privacy and offline resilience.
- **24/7 Autonomous Multi-Account Trading Daemon**: Continuous position management, dynamic breakeven locks, Aladdin 1-Day 99% VaR compliance, and economic news blackouts.
- **Discord Dual-Channel Intelligence Bot**: Strict segregation between `#elite-trade` (`1541528931063177226`) and `#crypto-bot` (`1541529106074828890`), with neural voice broadcasting.
- **Central Supervisor & Lifecycle**: Self-healing process manager (`bootstrap/supervisor.py`, `bootstrap/lifecycle.py`) guaranteeing 0 orphan processes and 0 port conflicts, launched via `JARVIS - START ALL.cmd` and stopped via `JARVIS - STOP ALL.cmd`.

```
                  +-------------------------------------------------------+
                  |           J.A.R.V.I.S. Sovereign Supervisor           |
                  |     (bootstrap/supervisor.py / lifecycle.py)          |
                  +-------------------------------------------------------+
                     |           |           |           |           |
        +------------+     +-----+-----+     +-----+     +-----+     +------------+
        |                  |                 |                 |                  |
+---------------+  +---------------+  +---------------+  +---------------+  +---------------+
| Master Web HUD|  | World Monitor |  | Mobile Bridge |  | MQ3 Cockpit   |  | Odysseus Brain|
| & API Gateway |  |  Live Engine  |  |   & Gateway   |  | & Auto Daemon |  | & Ollama LLM  |
|  (:8770)      |  |   (:3000)     |  |   (:8765)     |  |   (:5050)     |  | (:7000/:11434)|
+---------------+  +---------------+  +---------------+  +---------------+  +---------------+
        |                                                              |
        +----------------------------+---------------------------------+
                                     |
                       +---------------------------+
                       | Discord Dual-Channel Bot  |
                       |  (#elite-trade / #crypto) |
                       +---------------------------+
```

## Feature Inventory
Every feature from the Survey phase is mapped below with its assigned milestone:
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 8 Core Services Port Architecture | Strict segregation across ports 8770, 3000, 8765, 5050, 7000, 11434, trading daemon, Discord bot | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Unified Process Supervisor & Self-Healing | Dynamic registration, silent background spawn, auto-restart loop | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Scoped Teardown & 0-Zombie Lifecycle | Clean SIGTERM -> SIGKILL tree termination, port freeing (8770, 8765, 5050, 7000, 3000) | M1 | ORIGINAL_REQUEST §R1 |
| 4 | 1-Click Startup & Teardown Scripts | `JARVIS - START ALL.cmd` and `JARVIS - STOP ALL.cmd` root launchers | M1 | ORIGINAL_REQUEST §R1 |
| 5 | Master Command Center Web HUD | Dark Cyberpunk HUD (:8770) with Arc Reactor, DEFCON alert badge, 1-click controls | M2 | ORIGINAL_REQUEST §R2 |
| 6 | 22 Geospatial Intelligence Layers | Real-time multi-source data sync with zero watermark and curved geodesic bezier subsea arcs | M2 | ORIGINAL_REQUEST §R2 |
| 7 | World Monitor Live Embed | 1-click native iframe embed of World Monitor (:3000) in Master Web HUD (:8770) | M2 | ORIGINAL_REQUEST §R2 |
| 8 | Maritime Chokepoints Telemetry | 6 chokepoints with live flow rates, disruption multipliers, and DEFCON sensitivity scores | M2 | ORIGINAL_REQUEST §R2 |
| 9 | Bilingual Neural Voice Loop (<400ms) | Roman Urdu & English Edge-TTS (`RyanNeural`, `AsadNeural`) + SAPI5 fallback + S2S cascade | M3 | ORIGINAL_REQUEST §R3 |
| 10 | Roman Urdu NLP Tokenizer | Marker word classification (<3ms) for trading, OS commands, and intelligence queries | M3 | ORIGINAL_REQUEST §R3 |
| 11 | Desktop Screen Vision (Sub-35ms) | Win32 GDI BitBlt frame capture (<25ms observed) with live stream and fullscreen expander | M3 | ORIGINAL_REQUEST §R3 |
| 12 | 3-Tier UI Coordinate Locator | Tier 1 UIA (<10ms), Tier 2 OCR (<50ms), Tier 3 Multimodal VL (<1.5s) | M3 | ORIGINAL_REQUEST §R3 |
| 13 | Bi-Directional Mobile Bridge (:8765) | WebSocket telemetry stream, remote command execution, and push notifications | M3 | ORIGINAL_REQUEST §R3 |
| 14 | Remote Wake-on-LAN Management | Dual-MAC UDP magic packet broadcaster for out-of-band power-on | M3 | ORIGINAL_REQUEST §R3 |
| 15 | Pipdance $1,000 Fast-Track Challenge | Account #5054542 @ Vebson-Server: 0.75% risk ($7.50 max cap), 1:2.5-3.0 RR, 1.5x ATR SL | M4 | ORIGINAL_REQUEST §R4 |
| 16 | Dynamic Breakeven Lock (+1.0R) | Automatic shift to entry at +1.0R gain ($7.50 profit on Pipdance) for $0 Zero Drawdown | M4 | ORIGINAL_REQUEST §R4 |
| 17 | FTMO $100k Institutional Challenge | Account #1514382598 @ FTMO-Demo: institutional swing, $90k floor, $5k daily cap | M4 | ORIGINAL_REQUEST §R4 |
| 18 | BlackRock Aladdin 1-Day 99% VaR | Parametric/Historical 99% VaR <= 2.50%, CVaR, quarter-Kelly, 3-sigma gap stress test | M4 | ORIGINAL_REQUEST §R4 |
| 19 | 15-Minute Economic News Blackout | Pre-freeze and post-cooldown on high-impact events (CPI, FOMC, NFP, ECB, BOE) | M4 | ORIGINAL_REQUEST §R4 |
| 20 | Discord Dual-Channel Streaming | Strict segregation: `#crypto-bot` (`1541529106074828890`) and `#elite-trade` (`1541528931063177226`) | M4 | ORIGINAL_REQUEST §R4 |
| 21 | Chokepoints-to-Commodity Pricing | 1.35x-1.45x Gold multiplier & $8.50/bbl risk premium wired into trading engine | M4 | ORIGINAL_REQUEST §R4 |
| 22 | MQ3 Institutional Cockpit (:5050) | Flask telemetry dashboard, 24/7 daemon loop, MT5 multi-account connector | M4 | ORIGINAL_REQUEST §R4 |
| 23 | Comprehensive E2E Verification | 100% test pass across Tiers 1-4 & Tier 5 adversarial coverage hardening | M5 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Master Sovereign Hierarchy & Clean Process Architecture | R1: `JARVIS - START ALL.cmd`, `JARVIS - STOP ALL.cmd`, 8 core service bindings, supervisor & lifecycle verification | none | DONE |
| M2 | Live World Monitor & Geospatial Intelligence Fusion | R2: 22-layer vector HUD with geodesic arcs, :3000 native embed, 6 chokepoints live flow & DEFCON telemetry | M1 | DONE |
| M3 | Real-Life Iron Man OS Control, Vision & Neural Voice | R3: <400ms bilingual voice loop, sub-35ms GDI screen capture, 3-tier UI locator, mobile bridge :8765 & WoL | M1 | DONE |
| M4 | Institutional Multi-Account Autonomous Trading Engine | R4: Pipdance $1k fast-track (+1.0R BE lock), FTMO $100k demo (Aladdin VaR & news blackout), Discord dual-channel streaming, :5050 cockpit | M1, M2 | DONE |
| M5 | E2E Testing Verification & Adversarial Hardening | Phase 1: 100% E2E Pass (Tiers 1-4); Phase 2: Adversarial Coverage Hardening (Tier 5) | M1, M2, M3, M4 | IN_PROGRESS |

## Interface Contracts
### Dashboard (:8770) ↔ Supervisor & Subsystems
- `GET /`: Serves `web/universal_command_center.html`.
- `GET /api/platform/status`: Returns JSON status of all 8 core services and system vitals.
- `GET /api/world/layers`: Returns JSON GeoJSON-compatible payload of all 22 geospatial intelligence layers.
- `GET /api/world/chokepoints/telemetry`: Returns list of 6 maritime chokepoints with flow rates, disruption % and DEFCON multipliers.
- `POST /api/terminal/exec`: `{ "command": string }` -> `JarvisExecutionEnvelope` (result, latency_ms, telemetry_card).
- `GET /api/screenshot`: Returns binary JPEG frame (HMAC token protected or loopback verified).

### Mobile Bridge (:8765) ↔ Mobile Companion App
- `WS /ws/mobile`: Auth message `{ "type": "AUTH", "token": "..." }`, sends `{ "type": "STATUS_UPDATE", ... }`, receives `{ "type": "CMD_EXEC", "command": "..." }`.
- `POST /api/wol`: `{ "target": "wifi" | "ethernet" }` -> triggers dual-MAC broadcast on port 9.

### MQ3 Cockpit (:5050) & Autonomous Daemon ↔ Prop Accounts & MT5
- `PipdanceFastTrackEngine`: `check_breakeven_trigger(pos)` -> returns `"shift_sl_to_entry"` when profit >= $7.50 (+1.0R).
- `AladdinRiskEngine`: `compute_aladdin_var_99(positions)` -> returns `{ "var_pct": float, "cvar_pct": float, "status": "COMPLIANT" | "BREACH" }`.
- `EconomicCalendarService`: `is_blackout_active()` -> returns `{ "active": bool, "minutes_to_next": int, "event": string }`.

### Discord Bot Gateway ↔ Discord API v10
- `#crypto-bot` (`1541529106074828890`): Crypto analysis, meme audits, structured embed cards.
- `#elite-trade` (`1541528931063177226`): Forex/Gold trade tickets, +1.0R BE lock alerts, 5-min account telemetry.

## Code Layout
- `bootstrap/`: Process lifecycle, supervisor, startup/shutdown logic (`supervisor.py`, `lifecycle.py`, `stop_all.py`).
- `dashboard.py`: Master Operations Command Center server (:8770).
- `web/`: Web HUD and frontend assets (`universal_command_center.html`).
- `mobile_control.py`: Mobile companion gateway & WebSocket server (:8765).
- `actions/`: Action execution modules (`geospatial_intelligence.py`, `voice_synthesizer.py`, `send_discord_intelligence_suite.py`, `computer_control.py`, etc.).
- `perception/`: Screen capture, vision engine, UI automation, speech-to-speech (`screen_capture.py`, `vision_engine.py`, `speech_to_speech_engine.py`).
- `core/`: NLP tokenizers, prompt routers, command execution pipeline (`roman_urdu_parser.py`, `command_router.py`).
- `MQ3 TRADING BOT/`: Institutional quantitative trading engine (`src/pipdance_fast_track_engine.py`, `src/portfolio_risk_service.py`, `src/aladdin_risk_engine.py`, `src/economic_calendar_service.py`, `src/world_monitor_intelligence_engine.py`, `src/autonomous_live_daemon.py`, `src/mt5_connector.py`, `dashboard/app.py`).
- `bots/`: Odysseus neural brain (:7000) and Discord bot (`odysseus/app.py`, `discord_bot.py`).
- `tests/`: Automated test suites across all tiers.
