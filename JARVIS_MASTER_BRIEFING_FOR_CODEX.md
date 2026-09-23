# ⚡ J.A.R.V.I.S. SOVEREIGN PLATFORM // MASTER TECHNICAL BRIEF FOR CODEX
========================================================================================
**Classification:** Sovereign AI Platform Architecture & Operational Specification  
**Author:** Antigravity AI (Pair Programming with Founder Muhammad)  
**Primary SSD Workspace:** `F:\Jarvis Command Center`  
**Target Audience:** OpenAI Codex, Autonomous Subagents & Senior Platform Engineers  
**System Status:** 100% Operational & Live on SSD `F:\` (All 5 Endpoints Active @ HTTP 200)  
========================================================================================

---

## 1. EXECUTIVE PLATFORM ARCHITECTURE

J.A.R.V.I.S. is a unified, sovereign, **"Real-Life Iron Man"** cognitive operating system that fuses:
1. **OS-Level Computer-Use & Multi-Drive Mastery:** Unrestricted read, write, edit, screen vision, and command execution across all storage partitions (`C:\`, `F:\`, `P:\`, `W:\`).
2. **MQ3 Institutional Quantitative Trading Engine:** 24/7 autonomous multi-account scanner and risk execution for Prop Firm challenges (**Pipdance $1k** & **FTMO $100k**).
3. **World Monitor Tactical Vector Globe:** Real-time 22-layer geospatial situational awareness engine with maritime chokepoint flow telemetry tied into commodity pricing.
4. **Autonomous Dual-Mode AI Cascade (API + Zero-API Fallback):** Ultra-low latency API intelligence backed by an autonomous human-like web browser agent that opens ChatGPT/Claude visually when APIs are unavailable.
5. **Durable 3,315 Dense Vector Memory Hub:** SQLite-backed 384-dimensional semantic knowledge store containing 85 world-class financial/psychology books, Muhammad's personal manuscripts, and GAIGS platform blueprints.

```
+---------------------------------------------------------------------------------------+
|                       J.A.R.V.I.S. MASTER COMMAND CENTER (Port 8770)                   |
|                   [22-Layer Vector Map + Real-Time Telemetry + Voice HUD]             |
+---------------------------------------------------------------------------------------+
            |                                  |                                  |
            v                                  v                                  v
+-----------------------+          +-----------------------+          +-----------------------+
|  WORLD MONITOR (:3000)|          |  MQ3 COCKPIT (:5050)  |          |  ODYSSEUS AI (:7000)  |
|  Geospatial Vectors   |          |  Multi-Account Bot    |          |  Neural Reasoning     |
|  Maritime Chokepoints |          |  Aladdin Governance   |          |  Bilingual STT/TTS    |
+-----------------------+          +-----------------------+          +-----------------------+
            |                                  |                                  |
            +----------------------------------+----------------------------------+
                                               |
                                               v
+---------------------------------------------------------------------------------------+
|                             SUPERVISOR KERNEL & DISPATCHER                            |
|                            (F:\Jarvis Command Center\bootstrap)                       |
+---------------------------------------------------------------------------------------+
            |                                  |                                  |
            v                                  v                                  v
+-----------------------+          +-----------------------+          +-----------------------+
|   OS COMPUTER-USE     |          |  3,315 VECTOR MEMORY  |          | ZERO-API BROWSER BOT  |
|  Multi-Drive C/F/P/W  |          |  mission_memory.db    |          | Playwright ChatGPT    |
|  Screen OCR & PyAuto  |          |  85 Books + Missions  |          | Session Cookie State  |
+-----------------------+          +-----------------------+          +-----------------------+
```

---

## 2. WORKSPACE DIRECTORY STRUCTURE (`F:\Jarvis Command Center`)

All future code modifications, model weights, databases, and logs **MUST** reside within `F:\Jarvis Command Center`:

```
F:\Jarvis Command Center\
 ├── 🌐 dashboard.py                     ➔ Master Command Center backend (Flask/WebSocket @ :8770)
 ├── 📈 MQ3 TRADING BOT/                 ➔ Institutional Trading Engine (Port :5050)
 │    ├── run.py                         ➔ Dashboard telemetry server
 │    ├── config.json                    ➔ Risk boundaries & account safety gates
 │    ├── src/
 │    │    ├── autonomous_live_daemon.py ➔ Multi-account 24/7 scanning & execution daemon
 │    │    ├── multi_account_risk_manager.py ➔ Aladdin 1-Day 99% VaR & drawdown limits
 │    │    └── cloud_memory_sync.py      ➔ SQLite pattern & document stores
 │    └── data/trade_memory.db           ➔ SMC, Order Blocks & Liquidity sweeps
 ├── 🛰️ worldmonitor-main/               ➔ WebGL / DeckGL Vector Globe engine (Port :3000)
 ├── 🧠 memory/                          ➔ Dense Vector Memory & Dynamic Learning Store
 │    ├── mission_memory.py              ➔ 384-dimensional cosine vector retrieval engine
 │    ├── mission_memory.db              ➔ SQLite database storing 3,315 dense knowledge vectors
 │    ├── books_knowledge_index.json     ➔ Metadata index of 85 ingested world books
 │    ├── muhammad_personal_missions_index.json ➔ Personal manuscripts & GAIGS index
 │    └── dynamic_skill_registry/        ➔ 1-Shot dynamically synthesized Python skills
 ├── 🍪 data/                            ➔ Persistent State & Local Caches
 │    ├── browser_profile/storage_state.json ➔ Persistent ChatGPT/Claude web cookies (21 saved)
 │    └── ollama/models/                 ➔ Dedicated SSD LLM weights & context store
 ├── ⚙️ config/                          ➔ System configurations & API mappings
 ├── 🛠️ actions/ (50 modules)            ➔ OS automation, App launchers, Multi-drive search
 │    ├── os_automation.py               ➔ App launch/kill, Desktop .lnk scanner, Screen capture
 │    ├── knowledge_ingestion_engine.py  ➔ High-speed PDF/DOCX multi-book vector feeder
 │    └── workspace_tools.py             ➔ Recursive multi-drive search, edit, backup
 ├── 👁️ perception/                      ➔ Vision & Web Navigation Suite
 │    ├── screen_capture.py              ➔ Sub-35ms live screen grabber & OCR element finder
 │    └── web_navigator.py               ➔ Playwright Chromium zero-API web LLM navigator
 ├── 🤖 ai_engine.py                     ➔ 6-Tier Cascade (API + Local + Autonomous Browser)
 ├── 📱 mobile_control.py                ➔ Mobile Remote Gateway & WoL Bridge (Port :8765)
 ├── ⚡ START_JARVIS_SOVEREIGN.bat        ➔ Master 1-Click Startup Daemon
 ├── 🛑 STOP_JARVIS_SOVEREIGN.bat         ➔ Master 1-Click Graceful Shutdown
 └── 🔐 .env                             ➔ Root environment & live API keys
```

---

## 3. ACTIVE FLEET ENDPOINTS & TELEMETRY PORTS

All 5 core web services run simultaneously on `localhost` without port collisions:

| Port | Service Name | Entry Script | Purpose & Functionality |
|---|---|---|---|
| **`8770`** | **Master Operations Center** | `dashboard.py` | Unified Cyberpunk Tactical HUD, 22-layer World Map, live vitals, speech console. |
| **`5050`** | **MQ3 Trading Cockpit** | `MQ3 TRADING BOT/run.py` | MT5 multi-account dashboard, real-time equity charts, signal radar, PnL analytics. |
| **`3000`** | **World Monitor Vector Engine** | `worldmonitor-main (npm dev)` | WebGL 22-layer global conflict, submarine cable, vessel, and infrastructure tracker. |
| **`7000`** | **Odysseus Neural Brain** | `bots/odysseus/app.py` | Local AI reasoning server, STT speech-to-text, and neural TTS synthesis. |
| **`8765`** | **Mobile Remote Gateway** | `mobile_control.py` | Android APK bridge, remote PC terminal, screen streaming, and Wake-on-LAN. |

---

## 4. MQ3 QUANTITATIVE MULTI-ACCOUNT TRADING ENGINE

### Active Funded & Evaluation Accounts:
1. **Account 1 — Pipdance / Fortex $1,000 Challenge:**
   - **Login ID:** `5054542` | **Server:** `Vebson-Server`
   - **Risk Cap:** Exact **0.75% risk per trade ($7.50 max risk)**.
   - **Target RR:** 1:2.5 to 1:3.0.
   - **Dynamic Breakeven Lock:** At **+1.0R profit ($7.50 gain)**, Stop Loss instantly shifts to entry price + spread ($0 risk guarantee).
   - **Rules:** Enforce 2-Day Fast-Track evaluation rules and max 4% daily drawdown limit.
2. **Account 2 — FTMO $100,000 Free Trial Demo:**
   - **Login ID:** `1514382598` | **Server:** `FTMO-Demo`
   - **Strategy:** Institutional swing execution, BlackRock Aladdin 1-Day 99% VaR governance.
   - **News Filter:** 15-minute high-impact economic calendar news blackout.

### Architecture & Database:
- **Daemon:** `MQ3 TRADING BOT/src/autonomous_live_daemon.py` scans symbols (`XAUUSD`, `EURUSD`, `GBPUSD`, `BTCUSD`) every 60s.
- **Memory Store:** `data/trade_memory.db` indexes Fair Value Gaps (FVG), Liquidity Sweeps, and Order Block patterns.

---

## 5. WORLD MONITOR REAL API KEYS & GEOPOLITICAL FUSION

The World Monitor system is configured with active live API keys in `F:\Jarvis Command Center\.env`:

```env
GEMINI_API_KEY=AIzaSy_YOUR_GEMINI_API_KEY
WORLD_MONITOR_API_KEY=wm_master_pro_key
WORLD_MONITOR_URL=http://127.0.0.1:3000
FINNHUB_API_KEY=YOUR_FINNHUB_API_KEY
FRED_API_KEY=YOUR_FRED_API_KEY
EIA_API_KEY=YOUR_EIA_API_KEY
NASA_FIRMS_API_KEY=YOUR_NASA_FIRMS_API_KEY
OPENSKY_CLIENT_ID=YOUR_OPENSKY_CLIENT_ID
OPENSKY_CLIENT_SECRET=YOUR_OPENSKY_CLIENT_SECRET
AVIATIONSTACK_API=YOUR_AVIATIONSTACK_API_KEY
AISSTREAM_API_KEY=YOUR_AISSTREAM_API_KEY
OPENAQ_API_KEY=YOUR_OPENAQ_API_KEY
GROQ_API_KEY=gsk_YOUR_GROQ_API_KEY
```

### Geospatial Layers & Maritime Chokepoint Telemetry:
- Tracks live disruptions across: **Strait of Hormuz, Bab el-Mandeb, Suez Canal, Malacca Strait, Panama Canal, and Bosporus**.
- Flow rate disruption multiplier is directly piped into MQ3's Gold (`XAUUSD`) and Energy pricing models.

---

## 6. DUAL INTELLIGENCE: API MODE VS. ZERO-API BROWSER AGENT

J.A.R.V.I.S. operates under a **6-Tier Intelligent Cascade** (`ai_engine.py`):

1. **Tier 1 (Gemini API):** Google Gemini 2.5 Flash (`google-genai` SDK).
2. **Tier 2 (Groq Ultra-Fast API):** LLaMA 3.3 70B Versatile (<300ms inference).
3. **Tier 3 (Local Ollama Node):** Local LLM server running on `http://127.0.0.1:11434`.
4. **Tier 4 (Odysseus AI Brain):** Local reasoning server running on `http://127.0.0.1:7000`.
5. **Tier 5 (Autonomous Web Browser Agent — Zero-API Fallback):**
   - Implemented in `perception/web_navigator.py`.
   - Launches Playwright Chromium with persistent session cookies (`data/browser_profile/storage_state.json`).
   - Automatically navigates to **ChatGPT (`chatgpt.com`)**, Claude, or DeepSeek.
   - Types user prompts into the web textarea, waits for the streaming response to complete, and extracts the plain markdown answer.
   - **Zero API keys required** — behaves exactly like a human user sitting at the computer.
6. **Tier 6 (Bilingual Local Intent Engine):** Deterministic regex/vector intent parser in Roman Urdu and English for instant offline command execution.

---

## 7. FULL-PC MULTI-DRIVE CONTROL & OS AUTOMATION

J.A.R.V.I.S. uses `F:\` as its processing brain, but maintains administrative reach across **all Windows drives**:

| Partition | Capacity | Sovereign Capabilities |
|---|---|---|
| **`C:\`** | 243.5 GB | Windows OS, Desktop, User AppData, Registry, Installed Application binaries. |
| **`F:\`** | 232.8 GB | J.A.R.V.I.S. Core Hub, Memory SQLite DB, Trading Pattern Store, Model Weights. |
| **`P:\`** | 393.7 GB | Vision Point Work, Code Repositories, Historical Projects. |
| **`W:\`** | 537.3 GB | Mass Storage, Educational Books, Master Datasets, Video Archives. |

### OS Automation Handlers (`actions/os_automation.py` & `workspace_tools.py`):
- **App Management:** Launch, switch focus (`AppActivate`), inspect (`psutil`), and gracefully terminate apps (CapCut, Tor, UrbanVPN, Chrome, MT5, VS Code).
- **Desktop `.lnk` Scanner:** Scans both `OneDrive\Desktop` and `Desktop` to launch any installed program by name or Roman Urdu alias (e.g. *"CapCut kholo"*).
- **Computer-Use Vision:** Live screen capture (35ms interval) with PyAutoGUI click/type automation.
- **PowerShell Execution:** Administrative command shell accessible via `!` prefix.

---

## 8. DENSE VECTOR MEMORY MATRIX (3,315 TOTAL VECTORS)

All vector knowledge is indexed in `F:\Jarvis Command Center\memory\mission_memory.db` with 384-dimensional dense semantic projections:

```
=== J.A.R.V.I.S. VECTOR MEMORY BREAKDOWN ===
• book_knowledge             (1,810 chunks) -> 85 World Books (Dalio, Graham, Kahneman, Clear)
• muhammad_personal_work     (  922 chunks) -> Muhammad's Personal Books, Research & Past Work
• muhammad_missions_gaigs    (  455 chunks) -> GAIGS Platform Plans, Civilization OS, Pitch Decks
• Core Rules & Boundaries    (  128 chunks) -> GAIGS Ethics, Risk Limits, Boundary Rules
------------------------------------------------------------------------------------------------
TOTAL DENSE VECTORS          = 3,315 VECTORS (<50ms Sub-Second Cosine Recall)
```

### Knowledge Ingestion Catalog:
1. **85 Educational Books (`W:\desktop deta`):**
   - *Bridgewater Principles* (Ray Dalio), *The Intelligent Investor* (Benjamin Graham), *The Psychology of Money* (Morgan Housel), *Thinking, Fast and Slow* (Daniel Kahneman), *Atomic Habits* (James Clear), *Zero to One* (Peter Thiel), *A Brief History of Time* (Stephen Hawking).
2. **Founder Personal Works & Missions (`P:\Vision Point Work` & `F:\Muhammad's platforms`):**
   - *A New Dawn for Humanity (MUHAMMAD'S BOOK)*
   - *The Last System: A Global Blueprint for Humanity's Future*
   - *THE LAST HOPE: Humanity's Final Chance Before World War III*
   - *Ancient Wisdom: The Masjid-e-Nabawi Governance Model*
   - *GAIGS Full Interactive Technical Plan v3 & Investor Pitch Decks*
   - *Civilization Upgrade: A New Operating System*

---

## 9. MASTER 1-CLICK DESKTOP BUTTONS

Two master buttons are deployed directly on Windows Desktop (`C:\Users\user\OneDrive\Desktop`):

- ⚡ **`JARVIS - START ALL.cmd` (`.lnk`)**: 1-Click boots all 5 web servers, launches background trading daemons, and opens `http://127.0.0.1:8770` in browser.
- 🛑 **`JARVIS - STOP ALL.cmd` (`.lnk`)**: 1-Click gracefully terminates all background daemons and frees ports 8770, 5050, 3000, 7000, 8765.

---

## 10. GUIDELINES FOR CODEX & FUTURE AGENT COLLABORATION

When extending or modifying the J.A.R.V.I.S. platform:
1. **Absolute Workspace Anchor:** Never create or modify project code outside `F:\Jarvis Command Center`.
2. **Preserve Dual-Mode Compatibility:** If building features requiring LLM intelligence, ensure both API calls (`ai_engine.py`) and Zero-API browser fallback (`web_navigator.py`) work cleanly.
3. **Multi-Drive File Operations:** When user references files on `C:\`, `P:\`, or `W:\`, use absolute paths or `actions/workspace_tools.py` for resolution.
4. **Trading Risk Inviolability:** Never modify the 0.75% Pipdance risk cap ($7.50 max risk) or remove the +1.0R dynamic breakeven lock without explicit founder confirmation.
5. **Vector Memory Integration:** When user teaches a new skill or workflow, compile it into `memory/dynamic_skill_registry/` and compute its vector in `memory/mission_memory.py`.
