# Funding Pips compliance and staged go-live standard

Last rules review: **2026-08-19**. This document is an engineering control, not legal, tax, investment, or Funding Pips advice. The operator must re-check the current product page, dashboard, and emails before buying an account and before every phase transition because the firm can change its rules.

## Mission translated into safe system requirements

The platform's legitimate mission is to be a bilingual trading-research, risk-governance, paper/demo automation, account telemetry, and WhatsApp control system. It may analyze public market data, produce uncertainty-labelled scenarios, enforce prop rules, route orders after explicit authorization, and learn from a broker-reconciled ledger.

It must never claim risk-free trading, guaranteed profit, guaranteed challenge passage, named institutional activity without attributable evidence, insider information, or a future event as fact. Passing repository tests is not evidence that a strategy is profitable or ready for funded accounts.

All Funding Pips balances are simulated capital. Four account sizes represent **$180,000 nominal simulated size**, not cash owned by the operator and not a profit guarantee.

## Current Funding Pips model profiles

The implementation stores these as versioned profiles in `src/prop_rules.py`:

- **2 Step Standard:** Phase 1 target 8%, Phase 2 target 5%, minimum three trading days in each phase, 5% hard daily loss, and 10% hard static overall loss. The daily calculation uses the higher of opening-day balance or equity and resets at 00:00 platform time (UTC+3). Source: <https://help.fundingpips.com/hc/en-us/articles/34501809112081-2-Step-Standard>
- **2 Step Pro:** 6% target in each phase, minimum one trading day in each phase, 3% hard daily loss, and 6% hard static overall loss. Source: <https://help.fundingpips.com/hc/en-us/articles/34502027344017-2-Step-Pro-Model>
- **2 Step Flex:** 10% Phase 1 target, 6% Phase 2 target, 4% hard daily loss, and 12% hard static overall loss. Reward-cycle choices can add profitable-day requirements. Source: <https://help.fundingpips.com/hc/en-us/articles/47835196271249-2-Step-Flex>
- **1 Step Flex:** 12% evaluation target, 3% hard daily loss, and 12% hard static overall loss. Source: <https://help.fundingpips.com/hc/en-us/articles/34501697434385-1-Step-Flex>
- **FundingPips Zero:** 3% hard daily loss, 5% trailing maximum loss, and 1% maximum open risk, with stricter news/weekend restrictions. Source: <https://help.fundingpips.com/hc/en-us/articles/34502157694865-FundingPips-Zero>

The official model comparison is at <https://help.fundingpips.com/hc/en-us/articles/48368490585105-Compare-Account-Models>.

For current 8%-target Standard accounts, the published legacy 3%/2% Risk Per Trade Idea rule must **not** be treated as the current universal limit: Funding Pips says it applies only to legacy 10%-target Master Accounts. Current Standard Master Accounts use the Striking System where applicable. The standard warning trigger is 1.2% for Master Accounts above $25K on Weekly, Bi-Weekly, and On Demand cycles; the Monthly cycle changes the trigger to 1% at every account size. Four cumulative warnings cause a breach, and warnings do not reset after rewards. The exact reward cycle is therefore a required Master live-readiness input. The bot's much tighter 0.35% internal same-idea cap remains in force regardless.

## Automation and conduct controls

Funding Pips' published conduct standards must be treated as hard compliance constraints:

- A personally developed fully automated EA may be permitted, but the trader can be required to prove ownership with source code, version history, and an explanation of its behavior. A third-party EA is limited to risk/trade management. Store this repository's version history and audit evidence. Source: <https://help.fundingpips.com/hc/en-us/articles/34505029138449-Trading-Conduct-and-Security-Standards>
- Inbound copying from external accounts is prohibited. Copying between Funding Pips accounts belonging to the same individual is described as permitted, but every account and current rule must still be verified.
- HFT, latency arbitrage, tick scalping, gap exploitation, server spam, toxic flow, coordinated hedging/arbitrage, churning, and third-party account management are prohibited.
- The published standard says VPN/VPS use is not permitted. Do not deploy the terminal workers to a VPS unless Funding Pips gives the operator specific written permission.
- Evaluation accounts may hold over news/weekends under the applicable conditions, but intentional news hunting is prohibited. Master accounts have tighter red-folder-event restrictions, and weekend holding has been temporarily disallowed according to the current notice. The bot uses a stricter internal 15-minute news blackout and no-weekend-hold policy. Source: <https://help.fundingpips.com/hc/en-us/articles/34504137479441-News-Trading-Weekend-Holding>
- Follow the firm's responsible trading policy and do not use purchased account access to perform deceptive, manipulative, or rule-evasion behavior. Source: <https://help.fundingpips.com/hc/en-us/articles/47328410434065-Responsible-Trading-Policy>

## Internal controls (deliberately tighter than firm breach lines)

For the planned $5K, $25K, $50K, and $100K 2 Step Standard evaluations:

- Maximum risk per new trade: **0.25% of current equity**.
- Maximum total open risk per account: **0.50%**.
- Maximum same-symbol/same-direction idea risk per account: **0.35%**.
- Internal daily stop: **1.50%**; the 5% firm line is an emergency breach line, not a trading budget.
- Internal overall stop: **4.00%** against starting balance; the Standard model's 10% hard limit is static, not trailing.
- Maximum three new trades per server day and a daily lock after three consecutive losses.
- Minimum configured R:R 2.0 in the main strategy; live signal admission separately requires a positive cost-adjusted expectancy and at least 1.5 estimated R:R after costs.
- No live entry with a missing/stale quote, unverified calendar clearance, high spread, market closure, missing Friday-close telemetry, stale signal, unsupported regime, duplicate signal, or unversioned validation record.

These limits reduce risk; they cannot eliminate gaps, slippage, commissions, platform outages, model error, or losses.

## Four-account terminal architecture

The MetaTrader5 Python library has process-global terminal state. One Python process cannot safely pretend to be four independent MT5 logins. Each account therefore needs:

1. Its own locally installed MT5 terminal directory.
2. Its own `MT5TerminalWorkerProxy` process.
3. An exact expected login and server.
4. A password supplied through an account-specific environment variable, never JSON or chat.
5. Broker symbol specifications verified for tick size, tick value, minimum volume, volume step, stop level, and filling mode.
6. A connector receipt whose reported login matches the target account.

`data/mt5_terminals.example.json` is a no-secret example. `src/mt5_terminal_worker.py` implements process isolation. `src/multi_terminal_copier.py` refuses unbound or mismatched accounts and never fabricates slave fills.

## Evidence-based promotion path

Live promotion is manual and fail-closed:

1. **PAPER:** unit, integration, security, property, and failure-injection tests. No broker orders.
2. **SHADOW:** at least 20 trading days and 100 timestamped forward signals compared with executable broker quotes.
3. **DEMO / Funding Pips Free Trial:** at least 10 trading days and 50 broker-demo executions, including spread, commission, slippage, partial-close, restart, stale-feed, disconnect, and kill-switch evidence. Free Trial information: <https://help.fundingpips.com/hc/en-us/articles/45363484760209-Free-Trial>
4. **CANARY:** only after every operational gate passes, with one smallest account, reduced exposure, an explicit time-limited arm, and active human monitoring.
5. **LIVE:** only after at least 30 reconciled canary trades and explicit autonomous-live approval. Add larger accounts one at a time; do not activate four simultaneously.

The machine-readable checklist is `data/live_readiness.json`. The dashboard exposes it at `/api/readiness`. No code path may promote an account automatically.

## Before purchasing any evaluation

- Rotate every credential ever pasted into chat, `.env`, logs, or Git history. Deleting a working-tree file does not invalidate an exposed key.
- Confirm the exact product model and stage; do not rely on the generic label “Funding Pips.”
- Obtain written clarification from Funding Pips for the personal EA, multi-account copying, local terminal arrangement, and any ambiguity affecting the intended workflow.
- Complete the free trial and demo evidence first. If the system cannot pass the evidence gates, do not spend money on four evaluations.
- Start with the smallest account only. Add another account only after reconciled results show the execution and risk system behave as designed.

## Strategy research standard

Public or owner-authorized data may be used. Do not copy paid courses, proprietary repositories, paywalled research, leaked signals, credentials, or code without a compatible license. Public filings can be analyzed only after publication; material non-public information must never be solicited or used.

Every production strategy version must have walk-forward/out-of-sample evidence, a timestamped dataset hash, realistic spread/commission/slippage assumptions, regime and sensitivity tests, calibrated probability metrics, drawdown and tail-loss reporting, and a broker-reconciled forward record. Backtest selection alone is not sufficient.
