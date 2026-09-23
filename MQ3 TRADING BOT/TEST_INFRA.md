# Test Infrastructure & Methodology: MQ3 Trading Bot E2E Opaque-Box Test Suite

## 1. Test Philosophy & Architecture

The MQ3 Trading Bot End-to-End (E2E) Test Infrastructure is engineered according to institutional quantitative software verification standards. The test suite is **strictly requirement-driven and opaque-box**, derived directly from the authoritative specifications in `ORIGINAL_REQUEST.md` (R1–R3) and the 12 core features in `PROJECT.md` (F01–F12).

### Core Methodological Principles:
1. **Opaque-Box Independence**: Test cases validate public contracts, observable HTTP/REST endpoints, domain logic invariants, and external system behaviors without coupling to internal private implementation details.
2. **Progressive Testability**: Verification mechanics do not depend on features more complex than what is being tested.
3. **Deterministic Fixtures & Isolation**: Every test sets up isolated state, uses unique identifiers or temporary test files where necessary, and executes independently without order dependence.
4. **4-Tier Institutional Testing Hierarchy**:
   - **Tier 1: Canonical Feature Coverage**: Verifies happy-path execution for all 12 core features in isolation ($\ge 5$ test cases per feature $\to \ge 60$ tests).
   - **Tier 2: Boundary & Corner Cases**: Exercises extreme limits, zero/negative balances, max drawdowns, extreme ATR values, malformed inputs, and rapid burst requests ($\ge 5$ test cases per feature $\to \ge 60$ tests).
   - **Tier 3: Cross-Feature Combinations**: Validates pairwise feature interactions, multi-module coordination, and cascading state transitions ($\ge 15$ interaction tests).
   - **Tier 4: Real-World Application Scenarios**: Executes complete end-to-end multi-account quantitative trading workflows imitating institutional operational cycles ($\ge 6$ multi-account scenarios).

---

## 2. 12 Core Feature Inventory & Mapping

| Feature ID | Feature Name | Description | Source Requirement | Milestone | Tier 1 (Min 5) | Tier 2 (Min 5) | Tier 3 (Pairwise) | Tier 4 (Workflow) |
|---|---|---|---|:---:|:---:|:---:|:---:|:---:|
| **F01** | Zero-Overflow Responsive CSS Grid | Fluid `100vw`, `box-sizing: border-box`, `min-width: 0`, zero horizontal scrollbars at 1920x1080, 1440x900, 1280x720 | R1, Survey | M1 | 6 | 6 | ✓ | ✓ |
| **F02** | Cyber/Ice-Blue Design System | Color palette (`#0a1128`, `#0e1e38`, `#142952`, `#00d2ff`, `#38bdf8`, `#67e8f9`), crisp typography, glassmorphic styling | R1, Survey | M1 | 6 | 6 | ✓ | ✓ |
| **F03** | 1-Screen Command Center Layout | Unified navigation, top ticker, TradingView charts, AI Future Forecast overlays, Market Weather, Big Shark cards, Maritime Radar | R1, Survey | M1 | 6 | 6 | ✓ | ✓ |
| **F04** | Maritime Threat Radar Viewport Fit | Responsive chokepoint cards & CII bars without right-side clipping or horizontal overflow | R1, Survey | M1 | 6 | 6 | ✓ | ✓ |
| **F05** | Prop Firm Start-of-Day 2.5% Drawdown Shield | Instant order lockout upon 2.5% intraday equity drawdown across $5k, $25k, $50k, $100k accounts | R2, Survey | M2 | 6 | 6 | ✓ | ✓ |
| **F06** | Trailing HWM Floor Guard & Pacing | Trailing HWM floor clamping at starting balance, 5-stage consistency pacing | R2, Survey | M2 | 6 | 6 | ✓ | ✓ |
| **F07** | Dynamic Lot Sizing & 3.5x ATR Stops | Risk-calibrated lot sizing (<0.75% per setup, 1:2.0 min R:R, 3.5x ATR stops for crypto & forex) | R2, Survey | M2 | 6 | 6 | ✓ | ✓ |
| **F08** | Crypto Micro-Balance Scaling | Perpetual scaling ($100-$10k) with Hyperliquid funding rate and Lee-Ready CVD delta confirmation | R2, Survey | M2 | 6 | 6 | ✓ | ✓ |
| **F09** | Muhammad's Jarvis & Hermes Delegation | Autonomous trade delegation, `/api/hermes_delegate`, 70.5% OTE level synthesis, cognitive reflection | R3, Survey | M3 | 6 | 6 | ✓ | ✓ |
| **F10** | WorldMonitor Geopolitical Radar API | Live 5 chokepoints tracking, 4-pillar CII calculation, DEFCON mapping, `/api/world_monitor` | R3, Survey | M3 | 6 | 6 | ✓ | ✓ |
| **F11** | Live WhatsApp Sovereign Copilot | Whitelisted 2-way directives (`/api/whatsapp_command`), 3-tier voice processing (`/api/whatsapp_audio`), trade cards | R3, Survey | M3 | 6 | 6 | ✓ | ✓ |
| **F12** | Tri-Pillar Explainable Forensics | Who (Whale), Why (SMC/CVD/FVG), Where (Target pool/invalidation), `/api/chart_data/<symbol>` | R3, Survey | M3 | 6 | 6 | ✓ | ✓ |

---

## 3. Test Runner & Execution Guide

### Primary Test Runner Command:
```bash
pytest tests/test_e2e_opaque_box.py -v
```

### Targeted Tier Execution:
- **Run Tier 1 Feature Coverage Tests**:
  ```bash
  pytest tests/test_e2e_opaque_box.py -k "Tier1" -v
  ```
- **Run Tier 2 Boundary & Corner Case Tests**:
  ```bash
  pytest tests/test_e2e_opaque_box.py -k "Tier2" -v
  ```
- **Run Tier 3 Cross-Feature Combination Tests**:
  ```bash
  pytest tests/test_e2e_opaque_box.py -k "Tier3" -v
  ```
- **Run Tier 4 Real-World Application Scenario Tests**:
  ```bash
  pytest tests/test_e2e_opaque_box.py -k "Tier4" -v
  ```

---

## 4. Real-World Application Scenarios (Tier 4)

1. **Scenario 1: London Killzone Liquidity Sweep & OTE 70.5% Multi-Account Execution**
   - *Flow*: London Open 07:00 UTC $\to$ Asian Range liquidity sweep (Turtle Soup) $\to$ Retracement into 70.5% OTE Discount zone $\to$ Lee-Ready CVD positive delta absorption $\to$ Pre-trade risk audit across $5k, $25k, $50k accounts $\to$ Dynamic lot sizing computed ($<0.75\%$ risk) $\to$ Orders routed to MT5 & Bitget $\to$ Trade cards & execution receipts emitted.
2. **Scenario 2: High-Impact Geopolitical Shock & Gold Safe-Haven Rally**
   - *Flow*: WorldMonitor detects maritime anomaly in Strait of Hormuz $\to$ DEFCON status escalates $\to$ Geopolitical multiplier adjusts XAUUSD risk $\to$ Aladdin VaR computes revised risk budget $\to$ Jarvis Gold Advisor generates institutional bullish setup $\to$ Fleet scales position into 70.5% OTE pullback with 3.5x ATR stop $\to$ TP1 50% scale-out executed $\to$ Breakeven +1 pip buffer locked $\to$ Trailing HWM floor ratchets.
3. **Scenario 3: Prop Firm Start-of-Day 2.5% Drawdown Defense & Lockout**
   - *Flow*: Account suffers intraday equity drawdown exceeding 2.5% SOD baseline $\to$ Start-of-Day Drawdown Shield instantly locks out account $\to$ Autonomous Fleet Executor blocks new order entries $\to$ WhatsApp alert dispatched to operator $\to$ Telemetry reflects lockout $\to$ 00:00 UTC SOD reset cycle restores safe trading state.
4. **Scenario 4: Hands-Free Voice Copilot Directives in Roman Urdu & English**
   - *Flow*: WhatsApp voice note audio (base64) received with Roman Urdu / English intent $\to$ `WhatsAppVoiceTranscriber` ingests buffer $\to$ Speech-to-text transcription executed $\to$ Intent parsed into structured trading command (BUY XAUUSD, BE Lock, or Consult) $\to$ Command routed to execution/consultant engine $\to$ WhatsApp confirmation returned.
5. **Scenario 5: Multi-Account Fleet Onboarding & Cross-Venue Rebalancing**
   - *Flow*: Multi-account onboarding request submitted via `POST /api/onboard_account` ($10k Personal MT5, $50k FTMO, $1k Hyperliquid Crypto) $\to$ Auto-onboarder dynamically calibrates risk rules, loss caps, and allowed assets $\to$ Config persists $\to$ Multi-venue execution engine simultaneously routes trades to MT5 and Bitget/Hyperliquid.
6. **Scenario 6: Friday MT5 Session Close & 24/7 Weekend Crypto Transition**
   - *Flow*: Friday 21:55 UTC market close approaching $\to$ Fleet Risk Manager audits open Forex/Metals positions $\to$ 50% profits banked and remaining volume locked at Breakeven $\to$ Forex trading paused $\to$ System transitions to Weekend 24/7 Crypto Mode $\to$ Binance & Hyperliquid perpetual funding rate monitoring activated $\to$ Micro-scalp strategies deployed with CVD delta confirmation.
7. **Scenario 7: Full Cockpit Telemetry & Interactive 1-Click Execution Lifecycle**
   - *Flow*: Cockpit frontend polls `/api/status`, `/api/market_weather`, `/api/world_monitor`, `/api/trade_cards`, `/api/chart_data/XAUUSD` $\to$ User triggers 1-click action `POST /api/execution/action` (action="SCALE_50") $\to$ Position halved $\to$ 1-click action (action="BREAKEVEN") $\to$ SL moved to Entry + 1 pip $\to$ Telemetry updates in real time.
8. **Scenario 8: Aladdin 3-Sigma Gap Stress Test & Panic Emergency Kill Switch**
   - *Flow*: Extreme 3-sigma price shock simulated across portfolio $\to$ Aladdin Risk Engine evaluates portfolio VaR and CVaR limits $\to$ Panic Kill Switch triggered via `POST /api/control` (`KILL_SWITCH`) $\to$ All fleet positions atomically closed $\to$ System enters emergency safety lockdown.

---

## 5. Coverage Thresholds & Delivered Metrics

| Tier | Required Minimum | Delivered Count | Status | Description |
|---|:---:|:---:|:---:|---|
| **Tier 1: Feature Coverage** | $\ge 60$ ($\ge 5$ / feature) | **72** | **PASS** | 6 isolated tests per feature across all 12 core features (F01–F12) |
| **Tier 2: Boundary & Corner** | $\ge 60$ ($\ge 5$ / feature) | **72** | **PASS** | 6 boundary/stress tests per feature across all 12 core features |
| **Tier 3: Pairwise Interactions** | $\ge 15$ combinations | **18** | **PASS** | Cross-feature state transitions and multi-module coordination |
| **Tier 4: Real-World Scenarios** | $\ge 6$ workflows | **8** | **PASS** | Full multi-account end-to-end operational trading workflows |
| **Total Test Suite Volume** | $\ge 141$ tests | **170** | **PASS** | Complete institutional opaque-box E2E test suite |
